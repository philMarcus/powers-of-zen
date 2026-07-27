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

def tabs():
    return [t for t in json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json"))
            if t["type"] == "page"]

class Tab:
    def __init__(self, idx=0, match=None):
        ts = tabs()
        if match:
            t = next(t for t in ts if match in t["url"] or match in t.get("title",""))
        else:
            t = ts[idx]
        # activate first: chrome throttles background tabs (screenshots hang)
        urllib.request.urlopen(f"http://localhost:{PORT}/json/activate/{t['id']}")
        time.sleep(0.5)
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=200)
        self.id = 0
        # enable Page events so we can auto-accept "Leave site?" / beforeunload dialogs
        # (upload forms register beforeunload; a native dialog otherwise FREEZES CDP)
        try:
            self.cmd("Page.enable")
        except Exception:
            pass

    def cmd(self, method, **params):
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

    def choosefile(self, button_js, winpath):
        """Intercept the native file chooser: run button_js to open it, then
        feed the file via the chooser's backing node."""
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
                msg = json.loads(self.ws.recv())
                if msg.get("method") == "Page.fileChooserOpened":
                    node = msg["params"].get("backendNodeId")
                    break
            if node is None:
                raise RuntimeError("file chooser never opened")
            self.cmd("DOM.setFileInputFiles", files=[winpath], backendNodeId=node)
        finally:
            self.cmd("Page.setInterceptFileChooserDialog", enabled=False)

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
