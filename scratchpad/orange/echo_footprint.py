# What would --stage-echo-relief / --stage-fog-phrase TOUCH in the nightly? Replicates dive.py's
# auto-stage + variety draws (same crc32 keys) for the render queue + the four 10-12 nightlies.
import sys, json, re, zlib
sys.path[:0] = ['engine', 'scripts']
import stage, pipeline as pl
ABSTRACT = re.compile(r"\b(point|glow|light|haze|void|spark|dot|beam|flash|ray|mist|blur)\b", re.I)
ROUND = re.compile(r"\b(planet|moon|sun|star|orb|ball|globe|sphere|egg|pearl|bead|bubble|drop|droplet|eye|world|marble|berry|seed)s?\b", re.I)
reg = json.load(open('outbox/journeys.json'))['journeys']
names = [n for n, j in reg.items() if j.get('state') == 'queued'][:20]
names += ['sequoia_rosette', 'valdes_blow', 'cuttle_bridge', 'labrador_schiller']
tot = dict(cards=0, staged=0, echo=0, round=0, fogbg=0, fogphrase=0, authored=0)
rows = []
for n in names:
    try:
        spec = json.load(open(pl.journey_path(n), encoding='utf-8'))
    except Exception as e:
        rows.append(f"{n:24s} (no spec: {e})"); continue
    regs = spec.get('registers', [])
    sn = [r['name'] for r in regs]; rs = spec.get('render_start'); rot = sn.index(rs) if rs in sn else 0
    order = regs[rot:] + regs[:rot]; N = len(order)
    jname = spec.get('scaffold_name') or spec.get('name') or n
    jlook = spec.get('stage_look') or stage.draw_look(jname)
    plan = []
    for k, r in enumerate(order):
        if isinstance(r.get('stage'), dict): plan.append((k, r['stage']))
        elif r.get('stage') is not False:
            sg = stage.suggest_stage(r, seed_key=jname)
            if sg: plan.append((k, sg))
    ech, fogs, rnd, fogbg, auth = [], 0, 0, 0, 0
    for k, sdef in plan:
        r = order[k]; key = f"{jname}:{r.get('name')}"
        donors = []
        for dk, dr in enumerate(order):
            dt = (dr.get('target') or dr.get('target_phrase') or '').strip()
            if not dt or dt == 'None' or ABSTRACT.search(dt) or not stage.donor_ok(dt): continue
            if dk in (k, (k - 1) % N, (k + 1) % N): continue
            if isinstance(r.get('exp'), (int, float)) and isinstance(dr.get('exp'), (int, float)) and abs(dr['exp'] - r['exp']) < 6: continue
            donors.append((dr.get('name'), dt))
        aecho = sdef.get('echo')
        if aecho: auth += 1
        look = sdef.get('look') or (jlook if zlib.crc32(f"{key}|look".encode()) % 100 < 55 else stage.draw_look(f"{key}|cardlook"))
        vp = stage.plan_variety(key, sdef, sdef.get('kit', 'lattice'), look, donors=donors, authored_echo=aecho)
        if vp['echo']:
            ech.append(vp['echo']); rnd += bool(ROUND.search(vp['echo']))
        if vp['bg'] in ('deep', 'gradient', 'sea'):
            fogbg += 1; fogs += stage.fog_colour(r.get('palette')) is not None
    tot['cards'] += N; tot['staged'] += len(plan); tot['echo'] += len(ech); tot['round'] += rnd
    tot['fogbg'] += fogbg; tot['fogphrase'] += fogs; tot['authored'] += auth
    rows.append(f"{n:24s} cards {N:2d} staged {len(plan):2d} echo {len(ech):2d} (round {rnd}) fog-bg {fogbg} w/phrase {fogs} | " + '; '.join(ech)[:150])
print('\n'.join(rows)); print('TOTAL', tot)
