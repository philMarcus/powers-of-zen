#!/usr/bin/env python3
"""Minimal CDP driver for the PowersOfZen Chrome profile (port 9222).

Commands:
  tabs                       list open tabs
  goto <url>                 navigate first tab (or --tab N)
  shot <out.png>             screenshot current tab
  eval <js>                  evaluate JS, print result
  type <text>                insert text at focus (Input.insertText)
  setfile <selector> <winpath>  attach file to <input type=file>
  click <x> <y>              synthesized mouse click at viewport coords
"""
import base64
import json
import sys
import time
import urllib.request

import websocket

PORT = 9222
# Per-command CDP send/recv timeout. Was 200s: the IG tab's websocket occasionally
# WEDGES (goes silent — every recv sits the full timeout then dies "Connection timed
# out"; 3x on 2026-08-26), so each step stalled >3min before erroring and wait_for's
# swallow-and-retry stacked those stalls. No legit single command takes anywhere near
# 30s (navigate/eval/screenshot return in <5s; long waits live in POLLER loops of
# short evals, never inside one command). A fresh connection has always cured the
# wedge — see Tab.reconnect / Tab.cmd.
WS_TIMEOUT = 30

def tabs():
    return [t for t in json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json"))
            if t["type"] == "page"]


def find_tab(match):
    """First page tab whose url/title contains match, else None."""
    for t in tabs():
        if match in t["url"] or match in t.get("title", ""):
            return t
    return None


def close_tab(tab_id):
    """Close a tab by devtools id (used to rebuild a platform tab whose renderer or
    socket is wedged beyond what a reconnect cures). Best-effort."""
    try:
        urllib.request.urlopen(f"http://localhost:{PORT}/json/close/{tab_id}", timeout=10)
    except Exception:
        pass


def open_tab(url):
    """Open a new browser tab at url (DevTools /json/new). The poster uses this to
    self-heal when a platform tab isn't open (e.g. after a fresh scheduler launch)."""
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"http://localhost:{PORT}/json/new?{url}", method="PUT"), timeout=10)
    except Exception:
        urllib.request.urlopen(f"http://localhost:{PORT}/json/new?{url}", timeout=10)
    time.sleep(2)

class Tab:
    def __init__(self, idx=0, match=None, ws_timeout=WS_TIMEOUT):
        self._idx = idx
        self._match = match
        self._timeout = ws_timeout
        self.ws = None
        self.id = 0
        self._connect()

    def _find(self):
        ts = tabs()
        if self._match:
            return next(t for t in ts
                        if self._match in t["url"] or self._match in t.get("title", ""))
        return ts[self._idx]

    def _connect(self):
        t = self._find()
        self.tab_id = t["id"]
        # activate first: chrome throttles background tabs (screenshots hang)
        urllib.request.urlopen(f"http://localhost:{PORT}/json/activate/{t['id']}",
                               timeout=10)
        time.sleep(0.5)
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"],
                                              timeout=self._timeout)
        # enable Page events so we can auto-accept "Leave site?" / beforeunload dialogs
        # (upload forms register beforeunload; a native dialog otherwise FREEZES CDP)
        try:
            self._cmd_once("Page.enable")
        except Exception:
            pass

    def reconnect(self):
        """Tear down and re-dial this tab's CDP socket. The wedge mode (2026-08-26,
        3x on the IG tab): the socket goes silent — every recv times out — while the
        tab itself is fine; a FRESH connection has always cured it."""
        try:
            self.ws.close()
        except Exception:
            pass
        self._connect()

    def _cmd_once(self, method, **params):
        self.id += 1
        mid = self.id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            # auto-accept any JS dialog (beforeunload "Leave site?", alerts) so a
            # native modal never blocks the harness
            if msg.get("method") == "Page.javascriptDialogOpening":
                self.id += 1
                self.ws.send(json.dumps({"id": self.id,
                                         "method": "Page.handleJavaScriptDialog",
                                         "params": {"accept": True}}))
                continue
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    def cmd(self, method, **params):
        try:
            return self._cmd_once(method, **params)
        except (websocket.WebSocketException, OSError) as e:
            # SOCKET-level failure (timeout / closed / reset) — never a CDP error reply
            # (those raise RuntimeError above and must not trigger a reconnect). Re-dial
            # and retry ONCE. Worst case a click whose response was lost fires twice —
            # acceptable: every posting flow verifies state after clicking.
            print(f"  (CDP socket {type(e).__name__} on {method} — reconnecting tab)",
                  flush=True)
            self.reconnect()
            return self._cmd_once(method, **params)

    def eval(self, js):
        r = self.cmd("Runtime.evaluate", expression=js, returnByValue=True,
                     userGesture=True, awaitPromise=True)
        return r.get("result", {}).get("value")

    def goto(self, url):
        self.cmd("Page.enable")
        self.cmd("Page.navigate", url=url)

    def shot(self, path):
        r = self.cmd("Page.captureScreenshot", format="png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def type_text(self, text):
        self.cmd("Input.insertText", text=text)

    def click(self, x, y):
        for t in ("mousePressed", "mouseReleased"):
            self.cmd("Input.dispatchMouseEvent", type=t, x=x, y=y,
                     button="left", clickCount=1)

    def setfile(self, selector, winpath):
        # pierce iframes: getDocument(pierce) + performSearch finds inputs anywhere
        self.cmd("DOM.getDocument", depth=-1, pierce=True)
        search = self.cmd("DOM.performSearch", query=selector,
                          includeUserAgentShadowDOM=True)
        if not search["resultCount"]:
            raise RuntimeError(f"no node matches {selector}")
        nodes = self.cmd("DOM.getSearchResults", searchId=search["searchId"],
                         fromIndex=0, toIndex=search["resultCount"])["nodeIds"]
        last_err = None
        for nid in nodes:
            try:
                self.cmd("DOM.setFileInputFiles", files=[winpath], nodeId=nid)
                return
            except RuntimeError as e:
                last_err = e
        raise last_err

    def choosefile(self, button_js, winpath, tries=2):
        """Intercept the native file chooser: run button_js to open it, then feed the
        file via the chooser's backing node. This loop reads the socket RAW (events,
        not command replies), so cmd()'s reconnect can't cover it — a wedged socket is
        handled here: reconnect + one full retry of the intercept."""
        for attempt in range(tries):
            self.cmd("Page.enable")
            self.cmd("Page.setInterceptFileChooserDialog", enabled=True)
            try:
                self.id += 1
                self.ws.send(json.dumps({"id": self.id, "method": "Runtime.evaluate",
                                         "params": {"expression": button_js,
                                                    "userGesture": True}}))
                deadline = time.time() + 20
                node = None
                while time.time() < deadline:
                    try:
                        msg = json.loads(self.ws.recv())
                    except (websocket.WebSocketException, OSError):
                        break              # socket wedged/closed — reconnect+retry below
                    if msg.get("method") == "Page.fileChooserOpened":
                        node = msg["params"].get("backendNodeId")
                        break
                if node is not None:
                    self.cmd("DOM.setFileInputFiles", files=[winpath],
                             backendNodeId=node)
                    return
            finally:
                try:
                    self.cmd("Page.setInterceptFileChooserDialog", enabled=False)
                except Exception:
                    pass
            if attempt + 1 < tries:
                print("  (file chooser never opened — reconnecting and retrying)",
                      flush=True)
                self.reconnect()
        raise RuntimeError("file chooser never opened")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tabs":
        for i, t in enumerate(tabs()):
            print(i, t["url"][:90])
        sys.exit()
    tabarg = None
    args = sys.argv[2:]
    if args and args[0].startswith("--tab="):
        tabarg = args[0].split("=",1)[1]
        args = args[1:]
    tab = Tab(match=tabarg) if tabarg and not tabarg.isdigit() else Tab(idx=int(tabarg or 0))
    if cmd == "goto": tab.goto(args[0]); time.sleep(3)
    elif cmd == "shot": tab.shot(args[0]); print("saved", args[0])
    elif cmd == "eval": print(tab.eval(args[0]))
    elif cmd == "type": tab.type_text(args[0]); print("typed")
    elif cmd == "setfile": tab.setfile(args[0], args[1]); print("file set")
    elif cmd == "choosefile": tab.choosefile(args[0], args[1]); print("file chosen")
    elif cmd == "click": tab.click(int(args[0]), int(args[1])); print("clicked")
