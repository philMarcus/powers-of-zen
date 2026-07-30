---
name: journey-composer
description: Compose a Powers-of-Zen world-card JOURNEY (the Layer-3 content of a dive video) that renders correctly on engine 2.0 — a logically-consistent, object-containment zoom chain. Use when asked to write, generate, or fix a journey, or to build the local journey-generator that mass-produces them. This is the AUTHORING doctrine; engine/dive.py + engine/grammar.py implement it, .claude/skills/dive-video renders it.
---

# Composing a Powers of Zen journey

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
  leaves", ✓ "a glossy black sphere, the meadow and sky mirrored on its surface". Rich, still.

## The prominent-point principle (what the object must be)
The engine finds the named object (Florence-2) and dives into it — or, before it's detectable,
picks a **prominent point** (contrast: a bright mote on dark OR a dark speck on a bright field,
moderately OFF-center) and grows the object there. So every `zoom` card's `scene` must contain
**a distinct object that CAN be found** — present and prominent, not a distant speck.

- **The target must be a FINDABLE object at this scale.** A whole ladybug is findable; the tip of
  its antenna is NOT (too fine, and it doesn't exist as a distinct thing in the wide shot). If the
  next thing is a fine sub-part, add an INTERMEDIATE scale (ladybug → its HEAD with antennae → the
  antenna tip). Each hop must land on something the detector could point at.
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
  "dur": 4,                         // duration in BEATS, power-of-two (0.5 | 1 | 2 | 4) — see pacing
  "palette": "blazing orange and white",

  "scene": "the corona of a blazing star, arcs of fire and towering prominences, embers streaming",
                                    // RICH, evocative — the world we travel through. Drives the prompt.
  "target": "one round banded gas planet ahead, growing as we approach, banded clouds turning toward us",
                                    // RICH, EMERGING — the object we dive into. Drives the prompt. (zoom only)
  "target_phrase": "the round banded planet",
                                    // TIGHT, 2-4 plain VISUAL words naming the object — for the detector.
  "target_pick": "salient",         // optional: how to choose among many — "salient"(default) | "random"
  "cameo": { "sprite": "output/mascots/canon/<name>.png", "pos": [0.6,0.4], "size": 0.14 }  // optional, ONE card
}
```
The rich/tight split is deliberate (per Phil): `scene` and `target` are lush prose for the
image model; `target_phrase` is a short concrete noun phrase for the *detector*. Long or
abstract detector phrases FAIL (Florence-2 degenerates on "the biggest planet" or a whole
sentence) — keep `target_phrase` to the object + one visual trait.
- **`scene`** = a STATIC, rich description of the world at this scale; it contains the findable
  object we dive into. (On a `seam` card, `scene` is just the STATIC scene at the seam — e.g. "a
  glossy black sphere, meadow mirrored on it" — NOT the transformation; the engine does the morph.)
- **`target`** = the object we dive into, described STATICALLY (present, prominent — no motion/time
  words). Omit on `seam` cards and on the last card (the loop auto-derives its target from card 0).
- **`kind`** = "zoom" default; "seam" on a semantic-morph transition.
- **`dur`** = duration in BEATS, a power of two (0.5 | 1 | 2 | 4) — see pacing.
- Top-level: `name`, `theme` (seed idea), `style_suffix` (Layer-2 style), `format`
  { `beats_per_bar` default 4, `exact_loop` true }, optional `settings`.

## Beat-aligned pacing (POWER-OF-TWO, so the strong beat always lands on the morph)
The rule that keeps everything musical: every morph lands on the beat, and the **STRONG beat**
(the "bum-bum" downbeat, led in by the **anacrusis** pickup we keep from engine 1) carries the
MAIN morphs. The safe way to vary pacing without drifting off the beat is to scale ONLY by
**powers of two** — doubling a card's time, or making two cards twice as fast, both keep the
morph on the beat.
- `dur` is in **BEATS**, and must be a **power of two: 0.5 | 1 | 2 | 4** (linger with 4).
- **Whiz** several cards by at 1 beat each (four cards fill a 4-beat bar) — great for a fast
  traverse. **Linger** with 2 or 4 beats on a rich scale. A half-beat (0.5) is the fastest whiz.
- There's ONE main morph pulse carrying the whole video; power-of-two durations guarantee every
  card's morph falls on that grid, with the big structural morphs on the strong beat.
- A `seam` is an instant on-beat morph — it buys no zoom time; keep its `dur` at 1 beat.
- The engine derives tempo so the total is whole bars and reuses the seamless-loop music aligner;
  the arrival-beat morph stays as punchy as engine 1.
- FUTURE (in PLAN.md, not now): compose the RHYTHM first, then build BOTH video and audio to it —
  including **beat-synced flares/effects** on non-morph beats (drum hits → on-screen flares). The
  music↔video mesh is a big feature; music-gen may need rhythm/effect control to support it.

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
- **Fantastical, never gory.**
- **One mascot cameo per video** on ONE card, scale-matched, size ≥0.12, full-cast rotation
  (see dive-video SKILL for the cast). Optional at compose time.
- **Counter** renders only for clean monotonic ladders (`counter:"auto"`); wraps/lingers/
  fractional stacks make it nonsense → `counter:false`.

## Self-check before shipping a journey
1. For EVERY `zoom` card: is the target a FINDABLE object at this scale (not too fine a sub-part —
   add an intermediate scale if so), named in `target` + a short `target_phrase`, and described
   STATICALLY (no motion/time words, and not receding/"far away")?
2. Are the seams at big exp jumps and buried mid-list (never at either end)? One for a
   realistic traverse; more only if the concept is deliberately fantastical.
3. First and last cards natural adjacent scales; last genuinely contains the first world;
   card 0 viewpoint pinned.
4. Adjacent cards contrast in shape AND palette temperature.
5. Every `dur` a power-of-two beat value (0.5|1|2|4) so morphs stay on the beat; pacing lingers
   where the scene is rich (whiz fast scales at 1 beat, linger rich ones at 2-4).
6. Any object named twice across cards (double-ghost)? Any animal "traveled through"? Any
   featured face? Any MOTION/TIME language ("growing", "rushing closer", "as we approach",
   "keeps swelling until it becomes") or receding "tiny/far away" in a scene/target? (Static only.)
7. Spine reskinned to the theme, not the generic atom→cosmos template.

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
