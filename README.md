# Powers of Zen

A pipeline that renders and posts "Powers of Ten"–style continuous-zoom shorts — looping dives through many scales, from macro to subatomic and back — to [@powersofzen](https://www.instagram.com/powersofzen/) on Instagram, YouTube, and TikTok. Rendering, music, and posting all run local on a single RTX 3080; only the overnight content composition uses frontier LLMs to draft each night's journey briefs.

🔗 **[powersofzen.com](https://powersofzen.com) — the full walkthrough, with diagrams.**

---

## By the numbers

| | |
|---|---|
| Videos live | 77 |
| Journeys in catalog | 130 |
| Visual styles | 13 |
| Music lanes | 10 |
| Hidden mascots | 13 |
| Scale per card | ×10 |

## The pipeline

Journeys are composed at midnight, rendered overnight, and posted on a fixed cadence. I touch it twice — approve the video, choose the music. Everything else is scheduled.

```
refill (00:00)  →  render queue  →  night batch (01:30)  →  [approve]  →  [choose music]
                                                                                  ↓
         stats + analysis  ←  poster (every 19 h)  ←  production queue  ←────────┘
```

Results feed back into the next night's composer briefs, so the catalog learns what works.

**Guardrails:** start/preflight audits · cameo-realm check · planet-position audit · backpressure at 20 ready videos · frame-0 figure gate · caption gates · per-render timeouts · Chrome self-heal · caption verified on the live page · Instagram size fallback · restart-proof scheduling.

## Stack

- **Rendering** — Python · ComfyUI (SDXL/DreamShaper feedback-zoom, ControlNet depth, Florence-2 detection, DepthAnything, IP-Adapter) on a single RTX 3080
- **Music** — ACE-Step, beat-locked to the visual bars
- **Agent orchestration** — a Fable coordinator spawns parallel Opus composers (via a journey-composer skill) that write and audit tomorrow's content catalog; a rule-based cinematographer sketches camera plans
- **State** — single-source-of-truth JSON with atomic writes; immutable versioned outputs that never overwrite
- **Posting** — CDP browser automation with websocket self-heal, cold/warm-session handling, trusted-pointer-sequence clicks, and live caption verification against the published post
- **Ops** — Streamlit dashboard · Windows Task Scheduler · restart-proof auto-logon · telemetry + flag logs

## What's in the repo

| Path | What it is |
|---|---|
| [`index.html`](index.html) | The full walkthrough page (also served at [powersofzen.com](https://powersofzen.com)) — diagrams of the daily loop, the circular world-card chain, the per-frame rhythm, and the frame loop. |
| [`stories.md`](stories.md) | Engineering decision log — every design call, bug, killed feature, with rationale and verbatim quotes from my own prompts. |
| [`PLAN.md`](PLAN.md), [`CLAUDE.md`](CLAUDE.md) | Internal plan of record and project orientation. |
| `engine/` | ComfyUI feedback-zoom renderer and supporting modules (camera, depth, grammar, music, tracker, warp). |
| `scripts/` | Nightly batch, journey refill, poster, dashboard launcher, repair tooling, A/B labs. |
| `journeys/` | Active catalog of world-card dive scripts. |
| `styles/` | Visual-style decks (checkpoint + palette). |

## How it was built

I designed the system and direct AI coding agents to implement it under review. The judgment calls are mine — rejecting plausible-but-wrong diagnoses, designing the A/Bs that isolate a cause, killing my own features when the evidence shows no effect, and making the systems calls a model wouldn't. [`stories.md`](stories.md) catalogs about 25 of those decisions, organized by competency, with verbatim quotes from my own prompts as evidence.

## A note on automation

The browser-automation layer here is for managing my own publishing account. It exercises publicly documented platform surfaces and is not intended as a reusable scraping tool.

---

*Built and operated by [Phil Marcus](https://github.com/philMarcus).*
