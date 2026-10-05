---
name: journey-composer
description: Compose a Powers-of-Zen world-card JOURNEY (the Layer-3 content of a dive video) that renders correctly on engine 2.x — a logically-consistent, object-containment zoom chain. Use when asked to write, generate, or fix a journey, or to build the local journey-generator that mass-produces them. This is the AUTHORING doctrine; engine/dive.py + engine/grammar.py implement it, .claude/skills/dive-video renders it.
---

# Composing a Powers of Zen journey

> Automation note: the midnight refill (`scripts/journey_refill.py`, Task Scheduler 00:00)
> runs this skill headlessly — a coordinator writes tier-assigned briefs, parallel composer
> subagents each flesh one out. A composed journey is auto-queued for rendering ONLY if
> `scripts/audit_starts.py` passes it and it compiles; write to journeys/<name>.json (flat —
> engine1/engine0 subfolders are retired schemas, never write there).

## What a journey IS (and the one law it must obey)
A journey is an ordered list of **world cards (registers)**, dive order LARGE→SMALL,
compiled by `engine/grammar.py` into per-frame prompts + zoom schedules. It is the
ONLY thing that varies per video (format and style are fixed layers).

**THE ONE LAW — every step is a ZOOM INTO A SPECIFIC KIND OF OBJECT that is genuinely
contained in the current scene.** The chain is a nesting doll: a scene → an object of a
type that lives inside it → that object's surface/interior becomes the next scene → an
object inside THAT → … → back to the first (the loop). If you can't point at the current
scene and say "we fly into one of *those* and it becomes the next card," the link is
broken. This is the whole game — the engine can only make a convincing single zoom if the
author gives it a real kind of object to fly into.
(An elephant → a patch of its wrinkled hide → a skin cell → its nucleus → DNA → an atom.
The elephant contains the hide contains the cell contains the nucleus. Never "another,
smaller animal at a smaller scale.")

## The two kinds of transition (get this right or the timing breaks)
Every card's transition to the next is one of two kinds. They are NOT the same, and the
old format's failure to distinguish them is why timing felt wrong.

- **`kind: "zoom"` (default) — into a contained object.** A real optical approach: the
  target starts as a distinct POINT in the scene and grows until it fills the view and
  becomes the next world. **Takes time** (the card's `dur`). Needs a `target_phrase`.
  Modest scale step (~×10 per card; `exp` changes a few units).
- **`kind: "seam"` — a semantic morph.** A thing at one scale BECOMES a thing at a wildly
  different scale and you *can't* optically zoom there — atom→cosmos, quark→galaxy cluster,
  a ladybug's antenna-TIP becoming a planet, an ice lattice becoming snowy peaks. This is an
  **instant morph ON THE BEAT — it takes no zoom time.** Recognizable by a **large `exp`
  jump** (≈≥8).

Rule of thumb: small exp step = zoom (takes time). Big exp jump = seam (instant, on beat).

**How many seams?** A REALISTIC scale-traverse (quark↔cosmos) usually has **one** — the
micro↔macro wrap. But this is a rule of thumb, **not a law**: FANTASTICAL journeys may fold
several times (deliberate multiple seams are welcome when the concept wants them). Whatever
the count, the **loop-pair ends** (first + last cards) must be natural ADJACENT scales —
never put a seam at the ends.
TEST (audit warns, 2026-10-04): count the consecutive-card jumps of 8 or more decades, wrap included. More than one fails the test — a descent that leaps from centimetres to an atom to a nucleus in two cards reads as a fade to black with one big object, and the engine cannot pace an authored jump. Micro-realm steps are x10 to x100 per card.

PLANET TEST (audit counts it, 2026-10-04): the world card after a planet target must not be a storm or cloud-spiral world unless the journey is ABOUT weather — 69% of the catalog's planets were, and they all render as the same grey hurricane pair. Pick a different planetary archetype (REALMS.md planetary band) and give the world its own colour and surface feature; the plate paints what the card says.

STAGE VARIETY TEST (2026-10-05): the micro realm is rendered through built 3-D stages, so two journeys whose micro cards say the same thing (an atom, a nucleus) get the same STRUCTURE. Write the micro cards as specific pictures (which lattice, which molecule, which nuclear picture: a droplet of nucleons, a quark trio on taut strings, nuclear pasta, a tightening bubble-chamber track, a Coulomb crystal, a quark-gluon broth) — the words choose the kit. Take liberties: the pictures should be INSPIRED by the realm, not textbook. The novelty brief lists the kit and look counts; prefer the rare ones.

## DESCRIBE STATIC SCENES — the ENGINE renders the motion (critical)
The journey supplies the STILL IMAGE at each scale. The ENGINE renders everything that happens
in TIME — the zoom, the approach, the growth, the morph between scales. So `scene` and `target`
must be **static, present-tense descriptions of a thing**, NOT a description of motion or
transformation.

- **DON'T write MOTION / TIME**: ✗ "growing sharper and closer as we descend toward it",
  ✗ "swelling larger with every heartbeat", ✗ "rushing closer", ✗ "the sphere keeps swelling
  until it IS a planet". The engine's own templates add "diving into … as it fills the view";
  writing it in the journey too confuses the image model (it tries to paint the *change* and
  drifts). Just describe the object, sitting there.
- **DON'T write RECEDING** either: ✗ "a tiny planet, barely visible, alone very far away". That
  sends the object away so it never becomes detectable (what broke stormglass). Don't tell the
  camera where the object is at all.
- **DO** describe the object CLEARLY PRESENT and prominent, static: ✓ "a round banded gas planet,
  its cloud bands and a great storm eye", ✓ "a single flowering treetop canopy, blossoms and
  leaves". Rich, still — but of the OBJECT ITSELF.
- **DON'T describe REFLECTIONS or CONTENTS of a shiny/transparent object** — the model latches onto
  what's reflected/inside and makes IT the subject. ✗ "a raindrop with the whole meadow mirrored on
  its skin" → we zoom into the meadow, not the drop. ✗ "a glossy sphere, the sky reflected across
  it" → we get the sky. ✗ over-enumerated interior detail ("the lamp's gold light pooled at its
  core, a spiral turning there") → we chase the spiral. Just name the object plainly ("a clear
  raindrop", "a glossy black sphere"); the engine fills the surface/reflection detail itself. Also
  avoid words that name a DIFFERENT object as a colour ("rose and teal dust" → it paints a rose
  flower; say "pink and teal"). **The same trap applies to SIMILES**: "like fireflies in fog",
  "like a candle flame" — the model paints the named object LITERALLY (night_bloom rendered an
  actual insect mid-seam from "like fireflies"). Never compare to a paintable object; describe
  the thing directly.

## The prominent-point principle (what the object must be)
The engine finds the named object (Florence-2) and dives into it — or, before it's detectable,
picks a **prominent point** (contrast: a bright mote on dark OR a dark speck on a bright field,
moderately OFF-center) and grows the object there. So every `zoom` card's `scene` must contain
**a distinct object that CAN be found** — present and prominent, not a distant speck.

- **Two ways a target gets reached — BOTH are fine:**
  1. **A distinct object present in the scene** (a ladybug, a planet, a treetop): the engine finds
     it (Florence) and dives in. If the next thing is a specific fine SUB-PART of the *current
     object at a similar scale* (a ladybug's antenna *tip*), it's awkward to navigate to directly —
     add an INTERMEDIATE scale so the spot becomes a distinct feature (ladybug → its HEAD with
     antennae → the antenna tip). This is about NAVIGATION to a spot, not about scale.
  2. **A far-smaller thing that isn't in the scene yet** (molecules in a water drop, an atom, a
     cell, a quark): it does NOT need to pre-exist or be findable — it EMERGES as a speck and grows
     as we zoom fast to its scale. This is the NORM for micro-scale jumps and is exactly what the
     engine's point-picker emergence handles. Just describe the target statically (a hexagonal
     water molecule, a glowing atom); the engine picks a point and grows it there. **DO zoom into
     atoms/molecules/quarks — they're core to the format; never avoid them for being "unfindable."**
  So: NAVIGATE-to-a-spot (a same-scale sub-part → needs a distinct feature / intermediate scale)
  vs EMERGE-a-speck (a far-smaller thing → grows from nothing; unfindable is fine, that's the point).
- **Many candidates is fine — encouraged.** A field of atoms, a herd of zebras: the engine selects
  ONE (a contrasty candidate, or at random) and commits — it doesn't matter which zebra. Describe
  the field; name the target *type* in `target_phrase` ("a zebra", "a glowing atom"). *(Selecting
  one-among-many is an engine problem — see below.)*
- `target_phrase`: a short, plain, VISUAL noun phrase the detector can localize — 2-4 words, the
  object + one trait: "a red ladybug", "the amber eye", "a banded planet". No motion words.

## Register (card) schema — rich SCENE + tight TARGET, kept separate
```jsonc
{
  "name": "star",
  "exp": 11,                        // 10^n metres; float ok. The exp JUMP to the next card
                                    //   decides zoom (small step) vs seam (big jump).
  "kind": "zoom",                   // "zoom" (default) | "seam"
  "stage": {"kit": "lattice",       // OPTIONAL (2026-10-05): the built 3-D world the engine composites
            "variant": "hex",       //   for this micro card. Kits: lattice (variant cubic|hex|fcc|diamond|
            "look": "gem"},         //   rhombo|sheets|random), nucleus, quark, fluid, tracks, pasta
                                    //   (phase rods|sheets|gnocchi), tubes (pdb, arrangement sea|bundle|
                                    //   sheet|chain), tissue. look: gem|fuzzy|plasma|glass|wire|ink.
                                    //   Omit it: the engine picks the kit from the card's WORDS and draws
                                    //   the look per journey. Set it when the concept wants a specific
                                    //   picture (a Coulomb crystal, bubble-chamber tracks, nuclear pasta).
                                    //   `stage: false` opts a card out. A journey-level `stage_look`
                                    //   fixes the look for all its cards.
  "dur": 4,                         // BEATS (bar=4). UNIFORM for every card in the journey
                                    //   (4 default, or 8 journey-wide), never mixed — see pacing
  "palette": "blazing orange and white",

  "scene": "the corona of a blazing star, arcs of fire and towering prominences, embers streaming",
                                    // RICH, evocative — the world we travel through. Drives the prompt.
  "target": "a round banded gas planet",
                                    // PLAIN — the bare object, nothing else. (zoom only; see below)
  "target_phrase": "the round banded planet",
                                    // TIGHT, 2-4 plain VISUAL words naming the object — for the detector.
  "target_pick": "salient",         // optional: how to choose among many — "salient"(default) | "random"
  "resolve": {"mode": "sea|lattice|surface|web", "variant": ..., "density": ..., "size": ...},
                                    // optional per-card override of the auto-derived depth scaffold;
                                    //   "resolve": false opts the card out — see VARIATIONS.md
                                    //   DEPTH-SCAFFOLD LIBRARY
  "cameo": { "sprite": "output/mascots/canon/<name>.png", "pos": [0.6,0.4], "size": 0.14 }  // optional, ONE card
}
```
**The lush/plain split (Phil 2026-07-31, learned the hard way): `scene` is LUSH, `target` is
PLAIN.** The target is the bare object — article + noun + AT MOST two of its OWN intrinsic
traits (its color, its shape). NEVER any location/context ("in the lantern light", "beside
the terrace", "on the dark surface below") and NEVER another object's name — the plunge
prompt repeats the target every frame, so any named context object gets PAINTED and steals
the dive (night_bloom's "flower in the lantern light" made the engine chase lanterns instead
of the flower). All richness about the object's world belongs in the CURRENT card's `scene`;
by the time we plunge, we already know where we are. When in doubt, make the target SHORTER:
"a night flower" beats "one pale night-blooming flower in the lantern light".
`target_phrase` is likewise short and concrete for the *detector* — object + one visual trait
(Florence-2 degenerates on long/abstract phrases).
- **`scene`** = a STATIC, rich description of the world at this scale; it contains the findable
  object we dive into. (On a `seam` card, `scene` is just the STATIC scene at the seam — e.g. "a
  smooth matte-black sphere on a green blade" — NOT the transformation, and NOT what's reflected in
  it; the engine does the morph.)
- **`target`** = the object we dive into, described STATICALLY (present, prominent — no motion/time
  words). Omit on `seam` cards and on the last card (the loop auto-derives its target from card 0).
- **`kind`** = "zoom" default; "seam" on a semantic-morph transition.
- **`dur`** = duration in BEATS (a bar = 4). UNIFORM across every card in the journey — 4
  (default) or 8 journey-wide, never mixed — see pacing.
- Top-level: `name`, `theme` (seed idea), `style` (a deck NAME — see STYLE below; do NOT write
  free-text style words), `format` { `beats_per_bar` default 4, `exact_loop` true,
  `frames_per_beat` 6–9 (per the TEMPO section), `counter` }, optional `settings`.
- **`music_lane`** — a lane NAME from `styles/music_deck.json` (the sound analog of `style`:
  instrumentation lives in the deck, never free-text). Test: read each lane's `mood` line and
  pick the one a viewer of THIS journey would call right; among equally-right lanes prefer one
  the recent catalog uses least. `music_theme`/`music_key` stay as before.

## STYLE — pick a deck NAME, never write the look yourself (Layer 2)
The LOOK is NOT the composer's job. Free-text style words drift the whole video PHOTOREALISTIC
("macro photography, soft bokeh" → realism; Phil wants the shiny, AI-polished, *rendered* eye-candy).
So the journey sets ONE top-level field — `style` — to a **name from the curated deck**
(`styles/deck.json`); the polished words live there and are tuned centrally. Choose the entry whose
`mood` fits the theme:
- **`cosmic_gloss`** — space / cosmic / astronomical (the shiny deep-space look).
- **`crystalline`** — minerals / crystals / ice / glass / gems.
- **`liquid_light`** — cells / microbes / underwater / bioluminescent / organic interiors.
- **`gilded_relic`** — human-made objects / markets / instruments / maps / relics / interiors.
- **`stormlight`** — storms / planets / dramatic weather / moody skies.
- **`enchanted_wild`** — flora / forests / creatures / meadows / nature.
- **`neon_drift`** — electric / urban night / circuitry / plasma / screens (synthwave neon + chrome).
- **`ultraviolet`** — bioluminescence / caves / glowworms / anything glowing on black.
- **`aurora_silk`** — textiles / weaves / atmospheres / soft cosmic fields (flowing ribboned light).
- **`infrared_bloom`** — foliage / pollen / organic fields you want SHOCKING, not pretty.
- **`lacquer_pop`** — enamel / carving / calligraphy / heraldry (flat bold colour + lacquer shine).
- **`reef_pop`** — shores / shallows / tropical water / foam.
Pick the one matching the journey's DOMINANT realm (a journey spans scales but has a home key). If a
theme fits none, still pick the closest — do NOT invent a `style_suffix`.
Fit comes first, but keep an eye on catalog variety — if one style is already carrying a lot of
journeys, prefer the next-best fit, and if nothing fits, that's a sign the deck wants a new entry
rather than another reuse. `grep -h '"style"' journeys/*.json | sort | uniq -c | sort -rn` shows
where things stand. NEVER put realism words
(photo, photograph, photography, macro, DSLR, realistic, film grain) anywhere in a journey.
`palette` (per-card) is still yours — it's the LOCAL scene colour/mood, not the global render look.

## REALMS — the scale-band formalism (journeys/REALMS.md is the library)
Before writing cards, read `journeys/REALMS.md` for the bands your journey crosses. Tests:
- **Continuation rule**: every card's interior is what its parent is MADE OF. A living parent
  goes visibly CELLULAR somewhere in −4..−6 and MOLECULAR (proteins/DNA/membranes — real
  machinery, not generic lattice) in −6..−8.5. A mineral parent names its REAL mineral and
  uses that mineral's actual structure. A made object uses its material's microstructure.
- **Ask by name**: DreamShaper renders mesophyll cells, mitochondria cristae, diatoms,
  tide pools, and every mineral on the REALMS list spectacularly WHEN NAMED (probed
  2026-08-13) — the catalog's realm gap came from never asking. Precise molecular machines
  (ribosome, protein folds) render wrong by name — flag those cards for reference steering.
- **Populated scenes**: at least one human-scale card in every journey names ≥3 distinct
  inhabitant kinds sharing the frame (audit: 0/106 catalog cards did — single-material
  fields are the catalog's biggest sameness).
- **POV attitude**: each REALMS archetype carries a natural attitude ([air]/[obl]/[eye]/
  [up]/[amb]). Adjacent cards keep a compatible attitude or change it ACROSS a card via
  scene wording ("seen from directly above" → "low over" → "among") — never jump [air]→[eye]
  between consecutive cards without that ramp. Deep-interior bands are [amb] and absorb any
  approach — good seam and loop-home material.
- **Word variety**: the audit's overused list (dark/pale/fine/bright/light...) appears in
  >55% of journeys — a new journey leans on fresher vocabulary.

## TEMPO — set `format.frames_per_beat` by the journey's energy (Phil-approved 2026-08-13)
The video's musical tempo is bpm = 720/fpb at the 12fps raw rate; the engine scales all
morph/anacrusis/tail geometry automatically. Choose per journey — this is a real variety
axis, not a default to copy:
- Standard band: **6** = 120bpm (driving — the CEILING for routine use) · **7** = 103 (the
  classic flow) · **8** = 90 (stately) · **9** = 80 (dreamy — the floor).
- Rare tails, deliberate spice only: **5** = 144 (reads fast and disorienting, not chill —
  Phil 2026-08-13: "not very often if at all above 120") · **10** = 72 (vast-and-slow).
- Test: does the tempo match how the journey's worlds FEEL to fall through? (electric/
  storm/urban → fast; oceanic/cosmic/ancient → slow.)
- Length interacts: seconds = cards × fpb/3. Keep total ≤ ~30s — an 11-card journey at
  fpb 9 is 33s (trim a card); at fpb 5 a 7-card journey is only ~12s (add cards).

**PALETTE PERFORMANCE (measured on IG, 2026-08-13 — apply as a test, not a vibe).** Audience
like-rate correlates with dark, saturated frames: corr(like%, luminance) −0.33, saturation +0.24,
deep-shadow fraction +0.28 (n=27 posted videos). Every top performer sits near luminance
0.31–0.38 with saturation ≥0.67; every pale high-key wash (sugar pastel, frost white, foam,
salt, pale moss) sits in the bottom quartile. Tests before finishing a journey: (a) would most
cards render against a DARK ground with saturated accents? (b) is any card's palette built on
whites/creams/pastels as the DOMINANT field? — if so, re-ground it (night version, backlit
version, deep-water version) or justify it as a deliberate rare contrast. Dark alone is not
sufficient — the subject must stay nameable (esoteric dark journeys underperform too).

## Beat-aligned pacing — think in whole MEASURES (the composer composes a RHYTHM)
The morphs ARE the rhythm. Each scale transition (the morph) lands on a STRONG beat — the downbeat
(beat 1) or beat 3 of a measure — led in by the anacrusis pickup. The music is generated TO this
grid UP FRONT (engine 1 could slide the music onto the morphs after rendering; engine 2 fixes the
grid at compose time), so the pacing must be musical from the start. `dur` is in BEATS; a bar = 4.

- **UNIFORM BARS PER SCALE — THE RULE (Phil 2026-07-31, supersedes the mixed-dur system):
  every card in a journey gets the SAME dur — 4 (one bar per scale, the default) or 8 (two
  bars per scale, a slow journey), never mixed.** Mixed durations (2/4/8 in one journey) made
  the arrive-look-plunge curve vary in period and amplitude card-to-card — arrhythmic, "uneven
  within each scale" (the v7 lesson). Engine-1's charm was one consistent breathing period;
  uniform bars restore it, and every morph lands on the same beat position automatically. The
  seam card gets the same bar as everyone (its dwell earns the big morph breathing room).
- **Length tiers now come from CARD COUNT, not card length**: short ≈ 4-5 cards (16-20 beats,
  ~9-12s), medium ≈ 6-7 cards (24-28 beats, ~14-16s), long ≈ 10-13 cards (40-52 beats,
  ~23-30s). Vary music bpm for further spread.
- **Never linger on a DIFFUSE scale** (fog, mist, plasma, featureless clouds) — if the journey
  is a dur-8 journey, diffuse scales argue for dur 4 overall instead (the skyfog lesson).
- **The whole video = a WHOLE NUMBER OF BARS.** Sum every `dur`; it MUST be divisible by 4.
- **LENGTH TIERS (Phil 2026-07-31): the catalog needs VARIED LENGTHS, not one size.** Seconds
  ≈ cards × fpb/3, using the journey's own `frames_per_beat` (music bpm then varies feel further):
  - **SHORT ~4-5 cards** — a tight realm SLICE (a micro-world that
    stays microscopic, one interior, one street). Great for realm-local loops.
  - **MEDIUM ~6-7 cards** — a roam (mathematical/quantum
    scales, a themed traverse).
  - **LONG ~10-13 cards** — the full epic ladder.
  Don't default everything to 8 bars; pick the tier that fits the concept's natural size.
- **Allocate bars by the visual journey AND the rhythm.** A scale you open ALREADY CLOSE on doesn't
  earn a whole bar; a big/dramatic descent or the seam deserves a clean strong-beat landing.
- A **seam** is an instant on-beat morph — give it 1 beat within its bar group.
- **EVERY card that can be a render start must read WIDE — and NEVER "X fills the view."**
  (Phil 2026-07-31, from frost_window: its frost-fern card said the fern "fills the view", and
  rendered cold it produced *a white fern standing on a desk in a room* — the model had no world
  to put it in, so it invented one.) A card's `scene` describes the WORLD at that scale with the
  target as a FEATURE in it ("a frosted windowpane, ferns of ice spreading across the glass"),
  never a close-up of one object. Banned in `scene`: "fills the view", "fills the entire view",
  "seen up close", "filling the frame" — the ENGINE decides how full the frame is; the journey
  only says what the world is. This matters most on card 0 and on whatever card `render_start`
  names, but write every card this way — with uniform bars any card may become the start.
- The engine's planned zoom fills each object to frame EXACTLY at its run's end (the morph beat), so
  the fill lands on the beat; the arrival-beat morph stays as punchy as engine 1.
- FUTURE (PLAN.md): compose the RHYTHM first, then build video + audio from the SAME rhythm so they
  dance together natively — plus beat-synced FX on non-morph beats (drum hits → on-screen flares).

## `render_start` — where frame 0 begins
Journeys are CIRCULAR, so the chain may begin at ANY card. Set top-level
`render_start`: "<register name>" and the compiler rotates the list to start there. It is
REQUIRED — omitted, the render silently begins at card 0, which is usually the wrong card.

Frame 0 carries two jobs at once: it is the only txt2img frame, so every later frame inherits
from it, and it is the LOOP-HOME target, since the last card dives back into it. Both jobs want
the same two properties, and both are required.

1. **The frame must be EASY TO MORPH INTO.** Two kinds qualify: many things spread across a field
   of view, or a single SOFT-EDGED, diffuse form. Astronomical subjects qualify even alone,
   because they have no hard silhouette — the returning dive can land anywhere on one and still
   match. What fails is a hard-edged, recognizable object as the subject: the return then has to
   reproduce one exact outline at one exact size, and the loop closes as a visible cut.
   This is independent of scale. `exp` is the size of the object, not the width of the shot, and
   every scale has both kinds of card — the journey alternates between them by design. Never
   choose a start by `exp`.
2. **Prefer outer space; subatomic next; a recognizable everyday place last.** Space establishes
   cleanly from nothing and morphs forgivingly whether the frame holds one object or many. The
   subatomic realm is as good in principle but needs more care: it has no photographic referent,
   so a thinly described one invites the model to substitute a familiar hard object. Describe
   those realms as diffuse light, depth and drift rather than naming particles.

Constraint: never let the rotation put the SEAM card first or last (last is worst — the loop-home
branch swallows it). With the seam at index `s` of `n`, rotating to `i` puts it at `(s-i) mod n`,
so `i` must be neither `s` nor `s+1`.

If no card satisfies both requirements, that is a JOURNEY bug — write a card that does, rather
than settling for the least-bad one. `render_start` is independent of the playback opening;
`scripts/phase_shift.py` still chooses the frame the finished video opens on.
Verify with `python3 scripts/audit_starts.py` (whole catalog) or
`python3 scripts/preflight.py <journey>` (one).

## Loop + self-similar seam (still critical)
Journeys are **circular and self-similar**: the last card dives back into the FIRST world.
- Make `registers[0].scene` a strong establishing description; the grammar auto-derives the
  last card's loop target from it (add a concise `loop_target` on card 0 if the scene is too
  long to read inside "plunging toward …").
- **Pin one viewpoint** in card 0's words ("seen from above at the water's edge") so the first
  frame and the last-arrival match — the closer first==last, the more invisible the loop.
- The last card must genuinely CONTAIN the first world; the first and last cards are the loop
  pair AND the playback opening, so they must be natural ADJACENT scales. Seams live mid-list.

## Diversity — the point of the composer
Infinite variety comes ONLY from journeys differing. From a THEME (academia, food, geography,
myth, a trending sound, an emotion…):
- **Pick a scale SLICE and a path** — don't always run the full quark→cosmos ladder. Slices,
  fractional steps, and creature/city/human-band lingering are encouraged (that band is the
  richest — spend `dur` there). Draw register variants from `journeys/VARIATIONS.md` (which
  needs BIG expansion — it's the generator's fuel).
- **Never reuse the templated atom→cosmos→galaxy→star→planet spine as-is** — reskin every card
  to the theme (a *library's* atom, a *reef's* cell, a *bakery's* crystal).
- **Adjacent cards must CONTRAST** in silhouette family (radial / branching / grid / blob /
  open) AND palette temperature — the theme lives in `style_suffix` + motifs, not in giving
  every card the same color (that made the samey amber iris→retina→galaxy stretch).
- Vary the seam pairing — continent→nucleus, eye→galaxy, antenna-tip→planet; make it beautiful.

## Hard-won authoring rules (do not relearn these the hard way)
- **No double-objects across cards.** Don't name the same specific object in two nearby cards
  — it renders at both scales (the double-lantern ghost). (This is different from "many
  instances in ONE scene," which is fine — see the prominent-point principle.)
- **Creature chains don't nest — environments do.** For creature scales, the `scene` is the
  shared ENVIRONMENT (the water, the reeds) with creatures as passing landmarks; you dive
  toward one and INTO one object on it (its eye, a scale, its antenna tip) — never "travel
  through" an animal.
- **Empty human interiors.** Where a lone figure tends to intrude (studies, steam, kitchens),
  write that `scene` "empty, no one present." Distant anonymous crowds/tiny figures AT SCALE
  are fine texture; featured individuals and readable faces are banned (global negative).
- **Figures intrude by VOCABULARY, not only by setting.** Declaring a scene empty does not help
  if the words still describe a figure's trappings. Two word-families summon one into any scene,
  and they are most dangerous in an abstract realm where the model has nothing else to anchor on:
  regalia and anatomy (halo, aura, nimbus, crown, robe, veil, shroud, mantle, wings, torso, limbs,
  lobes, and "bound/cradled/held"), and the ornate-portrait register (gilded, jewel-bright, regal,
  majestic, storybook grandeur stacked together — the caption style of fantasy character art).
  A halo is drawn *around* something, so the model supplies the something. State the physical fact
  instead of the trapping. Judge the FULL frame-0 string — scene + target + style suffix + brand
  tail — not just your own text; the style deck adds words you did not write.
- **A WEARABLE summons a wearer.** Any garment or worn object named as a thing in the scene —
  mask, veil, cloak, hood, gown, dress, coat, crown, helmet, armor, glove, jewelry — tends to be
  rendered ON a person, straight through "empty, no one present" and the engine's negative
  (static_bloom's "fine black mask" drew a masked woman on four straight seeds; a coat on a
  dress-form drew its wearer the moment nothing else anchored the frame). Test each noun: could
  a person wear it? Then either rename it by its physical function (grille, lattice, screen,
  drape) or make its emptiness structural (the object shaped by what it covers, nothing inside).
- **Write the PICTURE, never the name, for anything unrenderable.** Terms from physics and
  mathematics that name something no one has photographed contribute nothing to the image, so the
  surrounding adjectives decide the frame alone. Decide at compose time what the thing looks like
  and describe only that — shape, count, spacing, motion, texture, light, depth.
- The engine gates this automatically (`engine/figure.py`): frame 0 is re-rolled up to 4 seeds and
  the render ABORTS if a figure persists. An abort means the PROMPT is wrong — fix the words
  rather than re-running. Audit any render with `python3 scripts/check_figures.py output/<j>/vN`.
- **Fantastical, never gory.**
- **One mascot cameo per video** on ONE card, size ≥0.12 (see dive-video SKILL for the cast).
  Optional at compose time. Any card works (the engine pastes from the card's first feedback
  frame — a card-0 cameo appears at frame 1), but prefer a NON-first card: card 0 is the
  loop-return frame, and the sprite reads better after an arrival than over the establishing shot.
- **REALM-MATCH BEATS ROTATION** (Phil 2026-08-03). The sprite must live at the card's scale:
  test `|card.exp − mascot.exp| ≤ 3` against the cast table — amos (10²⁶) does not visit
  beehives. Pick the cameo CARD first, then the mascot NEAREST its exp; use cast rotation only
  to break ties among mascots that pass the test. It is fine for the extreme mascots (clark,
  adam, amos, aleksey, lamar) to appear rarely — they only travel when a journey visits their
  realm. `scripts/audit_starts.py` hard-fails an off-realm cameo (blocks the refill auto-queue).
- **KEY vs DISPLAY NAME** (Phil 2026-08-17). Write the lowercase KEY in the journey — it is the
  sprite filename (`output/mascots/canon/<key>.png`) and the identifier everywhere in the code.
  Captions say the rhyming DISPLAY name, applied downstream from `pipeline.MASCOT_DISPLAY`;
  never write a display name into a journey file and never invent one here:
  clark (Clark the Quark) · adam (Adam the Atom) · tina (Tina the DNA) · belle (Belle the Cell) ·
  lee (Lee the Flea) · newman (Dwight the Light) · dora (Dora the Flora) · kitty (Kitty the City) ·
  lorraine (Lorraine the Terrane) · janet (Janet the Planet) · lamar (Lamar the Star) ·
  aleksey (Alexis the Galaxy) · amos (Cosmo).
- **Counter: ALWAYS ON (`counter: true`). No exceptions** (Phil 2026-07-31: "even fiction realms
  can have quantified sizes"). It is the Powers-of-Zen signature; the engine pins the value to
  the current register and SPINS it at handoffs, so it stays honest across seam wraps — the
  spin at the wrap is part of the charm. Fictional/stylized realms (a chalk cosmos, a
  bubble-chamber, a glowworm sky) still get it: pick `exp` values that read sensibly for that
  world and let the odometer run. Never author `counter: false`.

## Self-check before shipping a journey
1. For EVERY `zoom` card: is the target named in `target` + a short `target_phrase` and described
   STATICALLY (no motion/time words, not receding/"far away")? Is it reachable — either a distinct
   object present in the scene, OR a far-smaller thing that emerges from a speck (atoms/molecules
   are fine)? Only if it's a same-scale fine SUB-PART (a ladybug's antenna tip) add an intermediate
   scale.
2. Are the seams at big exp jumps and buried mid-list (never at either end)? One for a
   realistic traverse; more only if the concept is deliberately fantastical.
3. First and last cards natural adjacent scales; last genuinely contains the first world;
   card 0 viewpoint pinned.
4. Adjacent cards contrast in shape AND palette temperature.
5. MEASURES: is `dur` UNIFORM across every card (4, or 8 journey-wide, never mixed) so every
   strong beat lands a morph, and is the TOTAL divisible by 4 (a whole number of bars)? Does the
   FIRST card open WIDE (target a small feature, not a close-up)?
6. Any object named twice across cards (double-ghost)? Any animal "traveled through"? Any
   featured face? Any MOTION/TIME language ("growing", "rushing closer", "as we approach",
   "keeps swelling until it becomes") or receding "tiny/far away" in a scene/target? (Static only.)
   Any REFLECTION or enumerated INTERIOR of a shiny/clear object (the reflection becomes the
   subject), or a colour that names another object ("rose dust" → a rose)? (Name the object plainly.)
7. Spine reskinned to the theme, not the generic atom→cosmos template.
8. STYLE: is `style` a single deck NAME matching the journey's dominant realm — and is there NO
   free-text `style_suffix` and NO realism word (photo/macro/DSLR/realistic) anywhere?

## Open engine problems this doctrine hands to the engine (not the author)
- **Selecting one-among-many.** When a scene has many candidates (a herd, a field), the
  engine must pick ONE prominent point (contrast-based, off-center) and COMMIT for the whole
  approach — and hand off to the detector once the object is big enough. Design TBD.
- **Emergence.** The object starts sub-detectable; the point-picker bridges the gap until
  Florence can lock (see PLAN.md "chicken-and-egg").

## How the local generator uses this (pipeline)
Input: a THEME (or a free-form description from Phil). Output: a journey JSON that passes the
self-check. Two modes: (a) theme-driven random generation drawing on VARIATIONS.md for
diversity; (b) translate Phil's natural-language description into the schema (compute the
`exp` ladder, mark seams at big jumps, write `target_phrase`s, set integer `dur`). Render via
`.claude/skills/dive-video`. Keep this skill + VARIATIONS.md as the model's context.
