#!/usr/bin/env python3
"""Ground truth for the IG share failure: stage the reel (poster --dry-run leaves the composer at
the caption screen), click Share the poster's way, then record what IG shows over the next 60 s
(dialog text, body text hits, screenshots) and whether the post count / newest reel changes."""
import subprocess, sys, time, json, re
sys.path.insert(0, '/mnt/c/Users/Phil/zoomer/scripts')
# wait for any poster run to finish (one driver per tab)
while subprocess.run(['pgrep', '-f', 'scripts/poster.py'], capture_output=True).stdout.strip():
    time.sleep(10)
print('[probe] staging via dry-run', time.strftime('%H:%M:%S'), flush=True)
r = subprocess.run([sys.executable, 'scripts/poster.py', '--journey', 'kelp_dynamo_stage', '--only', 'instagram', '--dry-run'],
                   cwd='/mnt/c/Users/Phil/zoomer', capture_output=True, text=True)
print(r.stdout[-400:], flush=True)
import poster
tab = poster.platform_tab('instagram')
def dlg():
    return tab.eval("(function(){const d=document.querySelector('div[role=dialog]');return d?d.innerText.slice(0,600):null})()")
def body_hits():
    return tab.eval(r"""(function(){const t=document.body.innerText;const hits=[];
      for (const k of ['shared','Share','went wrong','Try again','processing','Processing','uploading','Uploading','Something','couldn','limit','restrict','blocked','Discard','draft','Draft']) if(t.includes(k)) hits.push(k);
      return hits;})()""")
print('[probe] before share: dialog=', (dlg() or '')[:200].replace('\n',' | '), flush=True)
pre = ['DeRk4QQNA8g']   # newest reel before (cork_dehesa) — never call _ig_reel_codes here, it navigates away from the composer
m = poster._ig_share_click(tab)
print('[probe] share click path:', m, time.strftime('%H:%M:%S'), flush=True)
prev = 0
for t in (2, 6, 12, 25, 45, 70):
    time.sleep(t - prev)
    prev = t
    d = dlg(); h = body_hits()
    print(f'[probe] +{t}s dialog={str(d)[:300].replace(chr(10)," | ")!r} hits={h} url={tab.eval("location.href")}', flush=True)
    tab.shot(f'/mnt/c/Users/Phil/zoomer/scratchpad/orange/ig_probe_{t:02d}s.png')
tab.goto('https://www.instagram.com/powers.of.zen/')
time.sleep(5)
txt = tab.eval("document.body.innerText") or ''
mm = re.search(r'([\d,]+)\s+posts', txt)
print('[probe] profile posts:', mm.group(1) if mm else '?', 'newest reels:', poster._ig_reel_codes(tab)[:3], 'pre:', pre[:3], flush=True)
