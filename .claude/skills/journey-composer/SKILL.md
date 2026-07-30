---
name: journey-composer
description: Compose a Powers-of-Zen world-card JOURNEY (the Layer-3 content of a dive video) that renders correctly on engine 2.0 — a logically-consistent, object-containment zoom chain. Use when asked to write, generate, or fix a journey, or to build the local journey-generator that mass-produces them. This is the AUTHORING doctrine; engine/dive.py + engine/grammar.py implement it, .claude/skills/dive-video renders it.
---

# Composing a Powers of Zen journey

## What a journey IS (and the one law it must obey)
A journey is an ordered list of **world cards (registers)**, dive order LARGE→SMALL,
compiled by `engine/grammar.py` into per-frame prompts + zoom schedules. It is the
ONLY thing that varies per video (format and style are fixed layers).

**THE ONE LAW — every step is a ZOOM INTO A SPECIFIC OBJECT that is genuinely
contained in the current scene.** The chain is a nesting doll: a scene → one distinct
object inside it → that object's surface/interior becomes the next scene → one object
inside THAT → … → back to the first (the loop). If you cannot point at a single object
in card N's scene and say "we fly into *that* and it becomes card N+1," the link is
broken. This is the whole game — the engine can only make a convincing single zoom if
the author gives it a real object to fly into. (Ladybug → the tissue on its back → a
cell → its nucleus → DNA → an atom. Animal contains tissue contains cell contains
nucleus. Never "another animal at a smaller scale.")

## The two kinds of transition (get this right or the timing breaks)
Every card's transition to the next is one of two kinds. They are NOT the same and the
old format's failure to distinguish them is why timing felt wrong.

- **`kind: "zoom"` (default) — into a contained object.** A real optical approach: the
  target starts as a distinct POINT in the scene and grows until it fills the view and
  becomes the next world. **Takes time** (the card's bars). Needs a `target_phrase`.
  The scale step is modest (roughly ×10 per card; `exp` changes a few units).
- **`kind: "seam"` — a semantic morph.** Where a thing at one scale BECOMES a thing at a
  wildly different scale and you *can't* optically zoom there — atom→cosmos, quark→galaxy
  cluster, a ladybug's antenna-TIP becoming a planet, an ice lattice becoming snowy peaks.
  This is an **instant morph ON THE BEAT — it takes no zoom time.** Marked `kind: "seam"`.
  Recognizable by a **large `exp` jump** (roughly ≥8). **Exactly one** per journey (the
  micro↔macro wrap), and it must be **buried mid-list**, never at the loop ends.

Rule of thumb: small exp step = zoom (takes time). Big exp jump = seam (instant, on beat).

## The prominent-point principle (why journeys must be written a certain way)
The engine grows the next object by picking a **prominent point already on screen** and
zooming into it while the prompt paints the target forming there (bright mote on dark,
OR dark speck on a bright field — it looks for CONTRAST, not just brightness, and prefers
a point moderately OFF-center so the dive has direction). So every `zoom` card's scene
must actually **contain such a point**, and the target must be described as **EMERGING and
GROWING**, never as a distant speck.

- **DO** write the scene so one distinct object/point stands out and can be flown into:
  "a blazing star's corona, **one round banded planet catching the light ahead**".
- **DO** describe the target as emerging: "*one round gas planet ahead, growing as we
  approach, its banded face turning toward us*".
- **DON'T** describe it as receding: ~~"a tiny planet, barely visible, alone very far away
  in the distance"~~ — this tells the model to send it AWAY, and it never grows or becomes
  detectable. (This exact wording in the old TEMPLATE_TRAVEL is what broke stormglass.)
- **DON'T** clutter the scene with many of the target: ~~"tiny planets in distant orbit"~~
  → the engine picks one point; give it one clear candidate, not a field of them.

## Register (card) schema
```jsonc
{
  "name": "star",
  "exp": 11,                       // 10^n metres; float ok; the SIZE of the exp step to the
                                   //   next card decides zoom (small) vs seam (big jump)
  "bars": 1,                       // integer musical bars this card lasts (beat-aligned; see below)
  "palette": "blazing orange and white",
  "interior": "the corona of a blazing star, arcs of fire and towering prominences",  // the SCENE
  "next_target": "one round banded gas planet ahead, growing as we approach, banded clouds turning toward us",
  "target_phrase": "the round banded planet",   // 2-3 word VISUAL phrase for the detector (zoom cards)
  "kind": "zoom",                  // "zoom" (default) or "seam"
  "cameo": { "sprite": "output/mascots/canon/<name>.png", "pos": [0.6,0.4], "size": 0.14 }  // optional, ONE card
}
```
- **`interior`** = the world we travel through. Rich, varied, and it CONTAINS the prominent
  point that becomes the next object.
- **`next_target`** = that object, described EMERGING/GROWING (zoom) — omitted or scene-morph
  language (seam). Not needed on the last card (loop auto-derives from card 0).
- **`target_phrase`** = a short, concrete, VISUAL noun phrase the local detector (Florence-2)
  can localize: "the amber eye", "the single lit window", "the cracked geode", "the round
  banded planet". Long/abstract phrases ("the biggest planet", the full next_target) FAIL —
  keep it 2-4 plain words naming the object + one visual trait. Only on `zoom` cards.
- **`kind`** = "zoom" default; "seam" on the one semantic-morph transition.
- **`bars`** = integer musical bars (default 1). Pacing lives here — see below.

Top-level: `name`, `theme` (the seed idea), `style_suffix` (Layer-2 style tokens),
`format` { `bars_per_scale` default 1, `exact_loop` true }, optional `settings`.

## Beat-aligned pacing (why bars, not seconds)
The video must be an exact whole number of musical bars so the generated soundtrack loops
and every morph lands on a beat. So durations are authored in **integer `bars`**, never
decimal seconds:
- Linger on a rich scale → `bars: 2` or `4`. Pass fast → `bars: 1`. Never fractional.
- A `seam` is instant (the morph happens on the arrival beat of the next card) — it does not
  buy a card's worth of zoom time; keep its own `bars` at 1.
- The total video = sum of bars; the tempo is derived so one morph = one bar. This is what
  lets fast/slow/skip pacing coexist while staying on the beat.

## Loop + self-similar seam (unchanged, still critical)
Journeys are **circular and self-similar**: the last card dives back into the FIRST world.
- Make `registers[0].interior` a strong establishing description of the first world; the
  grammar auto-derives the last card's loop target from it (add a concise `loop_target` on
  card 0 if the interior is too long to read inside "plunging toward …").
- **Pin one viewpoint** in card 0's words ("seen from above at the water's edge") so first
  frame and last-arrival match — the closer first==last, the more invisible the loop.
- The last card must genuinely CONTAIN the first world (the heron stands in the landscape we
  dive into), so the dive naturally arrives home.
- The FIRST and LAST cards are the loop pair AND the playback opening → they must be natural
  ADJACENT scales. The one `seam` is buried mid-list, never at the ends.

## Diversity — the point of the composer
The engine + one grammar produce infinite variety ONLY if journeys differ. From a theme
(academia, food, geography, myth, a trending sound, an emotion…):
- **Pick a scale SLICE and a path**, don't always run the full quark→cosmos ladder. Slices,
  fractional steps, and creature/city/human-band lingering are encouraged (that band is the
  richest — spend bars there). Draw register variants from `journeys/VARIATIONS.md`.
- **Never reuse the templated atom→cosmos→galaxy→star→planet spine** as-is; reskin every
  register to the theme (a *library's* atom, a *reef's* cell, a *bakery's* crystal).
- **Adjacent cards must CONTRAST** in silhouette family (radial / branching / grid / blob /
  open) AND palette temperature — the theme lives in `style_suffix` + recurring motifs, not
  in giving every card the same color (that made the samey amber iris→retina→galaxy stretch).
- Vary the seam pairing — continent→nucleus, eye→galaxy, antenna-tip→planet; make it beautiful.

## Hard-won authoring rules (do not relearn these the hard way)
- **No double-objects.** Don't name the same creature/object in two nearby cards — it renders
  at both scales (the double-lantern / double-fly ghost). Each object is named once, in the
  `next_target`/`target_phrase` of the card that zooms into it.
- **Creature chains don't nest — environments do.** For creature scales, the `interior` is the
  shared ENVIRONMENT (the water, the reeds) with the creature as a passing landmark; the next
  creature is the `next_target`, named once. Never "travel through" an animal — travel through
  its world toward it, then INTO the one object on it (its eye, a scale, its antenna tip).
- **Empty human interiors.** Where a lone figure tends to intrude (studies, steam, kitchens),
  write that card's interior "empty, no one present." Distant anonymous crowds/tiny figures AT
  SCALE are fine texture; featured individuals and readable faces are banned (global negative).
- **Fantastical, never gory.** Creature scenes are wondrous, not visceral.
- **One mascot cameo per video** on ONE card, scale-matched, size ≥0.12, full-cast rotation
  (see dive-video SKILL for the cast table). Optional at compose time; can be added later.
- **Counter** renders only for clean monotonic ladders (`counter:"auto"`); wraps/lingers/
  fractional stacks make the label nonsense → set `counter:false` in format.

## Self-check before shipping a journey (the composer must verify each)
1. For EVERY `zoom` card: can I name one object in the scene we fly INTO, and is it in
   `next_target` + a short `target_phrase`, described as GROWING (not receding)?
2. Is there EXACTLY ONE `seam`, at a big exp jump, buried mid-list (not at either end)?
3. Are the first and last cards natural adjacent scales, and does the last genuinely contain
   the first world (self-similar loop)? Is card 0's viewpoint pinned?
4. Do adjacent cards contrast in shape AND palette temperature?
5. Are all `bars` integers? Does the pacing linger where the scene is rich?
6. Is any object named twice (double-ghost)? Any animal being "traveled through"? Any
   featured face? Any target described as tiny/far/receding?
7. Is the spine reskinned to the theme, not the generic atom→cosmos template?

## How the local generator uses this (pipeline)
Input: a THEME (or a free-form journey description from Phil). Output: a journey JSON that
passes the self-check. Two modes: (a) theme-driven random generation drawing on VARIATIONS.md
for diversity; (b) translate Phil's natural-language description into the schema (compute
`exp` ladder, mark the seam at the big jump, write target_phrases, set integer bars). Render
via `.claude/skills/dive-video`. Keep this skill and VARIATIONS.md as the model's context.
