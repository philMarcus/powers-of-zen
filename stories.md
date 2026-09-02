# Engineering Stories — Powers of Zen

A story bank for cover letters and interviews, targeting **AI Engineer / Forward‑Deployed Engineer** roles. Every story is anchored to a decision I actually made while building and operating *Powers of Zen*, so it holds up under follow‑up questions. Quotes are from my own prompts (voice‑dictated, lightly trimmed for readability) — they're evidence the stories are real, not the polished words I'd use out loud.

---

## The project in one paragraph
Powers of Zen is a self‑operating pipeline that renders and auto‑posts "Powers of Ten"‑style continuous‑zoom videos — seamless loops diving through every scale of the universe — to TikTok, YouTube, and Instagram to grow an audience. It runs **entirely local and free** on a single RTX 3080: a ComfyUI feedback‑zoom diffusion engine, a compiler that turns declarative "world‑card" journeys into per‑frame render + denoise + zoom schedules, a local music model beat‑locked to the visuals, a CDP browser‑automation poster with self‑healing and live verification, an analytics scraper, and a nightly scheduler that composes → renders → captions → posts with no human in the loop. I architected the system and I direct AI coding agents to implement it under my review.

## How I actually worked (the honest version — read this first)
I did **not** hand‑type most of the code. I ran an AI coding agent the way a staff engineer runs a team: I set the architecture and the invariants, I rejected plausible‑but‑wrong diagnoses, I demanded ground‑truth validation, I designed the experiments, and I owned the tradeoffs. The stories below are chosen to show **judgment**, because that's the part that doesn't come for free from an LLM. If an interviewer asks "did you just vibe‑code this?", the answer is: here are ~20 documented times I caught the AI's mistake, corrected a flawed approach, or made a systems decision the model wouldn't have. Being able to *supervise* AI at this level is itself the core skill for an AI‑engineering role.

## Recurring themes
- **Root‑cause discipline** — I don't accept the first plausible fix; I make the work reproduce the failure, isolate the variable, and prove the mechanism.
- **Experimental rigor** — I design A/Bs that actually isolate a cause, and I kill methods (and evaluation harnesses) that can't.
- **Systems thinking** — cost models, backpressure, idempotency, single‑source‑of‑truth state, phase‑locking, and failure isolation drive the design.
- **Domain modeling** — I formalized the problem (a three‑layer format grammar; a measured "noise floor" for perceptible motion) instead of hand‑tuning forever.
- **Operating AI safely** — hard guardrails between experiments and production, "validate in the real runtime conditions," and clear scope boundaries.

## Quick index — which story for which interview question
| If they ask about… | Go to |
|---|---|
| A hard bug you debugged | §1.1 caption saga · §1.2 cold‑vs‑warm browser · §1.4 silent model regression |
| A time you disagreed / were skeptical | §1.1 "I find it hard to believe IG is that broken" · §2.4 camera‑motion null result |
| System design / architecture | §3.1 three‑layer format · §3.2 self‑driving pipeline · §3.5 Monte‑Carlo scheduling |
| Testing / experimentation | §2.1 build‑in A/B · §2.2 variable isolation · §2.5 fixing the eval harness |
| Working with ambiguity / stakeholders | §5.1 "not a science project" · §7.1 holding the loop accountable |
| ML / applied‑AI judgment | §4.2 reach‑aware metric · §4.3 few‑shot mode collapse · §5.3 library‑before‑engine |
| Reliability / ops | §6.1 immutable artifacts · §6.2 fail‑loud automation · §6.4 restart‑proofing |
| Leading / prioritizing | §7.2 experiments out of production · §7.3 dependency‑ordered builds |

---

# 1 · Root‑cause debugging (and refusing to vibe‑code)

### 1.1 — Rejected a plausible root cause on domain priors, and was right
**Situation.** Four Instagram posts went out with blank captions. The working diagnosis blamed Instagram's platform.
**What I did.** I refused it on plausibility grounds: *"I find it hard to believe that Instagram is so broken that professional accounts can't post captions. I'm not so sure you have the right diagnosis."* That pushed a controlled re‑investigation.
**Result.** The real cause was ours: a JavaScript‑synthesized "Share" click fired a *bare* share that dropped the registered caption; a trusted pointer sequence (hover→press→release) carried it. Fixed, plus a self‑heal that verifies the caption on the live page before recording a post as live.
**Shows:** sanity‑checking a root cause against domain knowledge; distinguishing *plausible* from *proven*. *Answers:* "tell me about a time you disagreed with a diagnosis / were skeptical of an easy answer."

### 1.2 — "Tell me why it didn't take" — no re‑fix without a root cause
**Situation.** The 8am scheduled poster failed on the same YouTube/Instagram screens two mornings running, after being declared fixed.
**What I did.** I blocked another attempt until the mechanism was explained: *"We spent time fixing this. Please tell me why it didn't take."* I also noticed the "successful" test had used a warm browser session and a different video than the failing case: *"I'm not convinced yet."*
**Result.** Real cause: cold vs. warm browser state (idle Chrome throttles occluded tabs; onboarding nags block the cold path). The fix — validated by killing and relaunching Chrome cold — finally held.
**Shows:** holding fixes accountable to a verified cause; requiring tests to reproduce the actual failure conditions. *Answers:* "a bug that took multiple attempts," "how do you know a fix is real?"

### 1.3 — Named the anti‑pattern: "you're fixing symptoms, not causes"
**Situation.** A run of posting failures where each surface error got patched and success was assumed.
**What I did.** I stopped the work and reset the standard: *"you're fixing the symptoms, not the cause… we need to fix the root causes, not the symptoms, please,"* with the framing that *"the pipeline is the thing"* — a failure means the *system* is unfinished, not that one post needs a manual nudge.
**Result.** Became a durable project doctrine (verify against ground truth; fix causes). Later audits found and fixed 15 latent issues in one sweep.
**Shows:** defect‑in‑system vs. defect‑in‑instance thinking. *Answers:* "how do you set engineering standards / raise the bar on a team?"

### 1.4 — Caught a silent model regression from converging evidence
**Situation.** Renders looked subtly wrong; nobody had noticed the checkpoint had changed.
**What I did.** I triangulated two independent signals: *"my evidence is, one, the ComfyUI log every time said Model SDXL, and two, it looks more like the turbo."*
**Result.** A config fallback was silently routing legacy journeys to SDXL‑Turbo instead of the house DreamShaper model. Fixed the fallback; startup now logs the resolved model and each run records it.
**Shows:** not trusting the happy path; using logs + observed output to catch regressions. *Answers:* "a subtle bug," "how you use observability."

### 1.5 — Diagnosed the mechanism of a loop "hiccup" the cross‑fades kept missing
**Situation.** Repeated seam repairs still left a timing hiccup at the video's loop point; the instinct was to cross‑fade it away.
**What I did.** I identified the actual mechanism: *"we're morphing from a zooming image to a static image rather than from a zooming image to a zooming image"* — motion stopped during the morph, which reads as a freeze.
**Result.** The fix followed directly (keep the tail zooming; trajectory‑homing so inter‑frame motion never decelerates into the seam).
**Shows:** distinguishing the true cause from the visible symptom. *Answers:* "a time your understanding of the mechanism changed the fix."

*Additional evidence (one‑liners): caught a fix that had been over‑generalized until it silently disabled the on‑screen scale counter for every video ("I think you just removed the counter from all videos, please confirm"); spotted a batch‑wide crop regression by eye and traced it to a change boundary ("the last three, since Tide of Life, are cropped square"); diagnosed a mascot‑placement bug as a rule‑priority conflict (cast‑rotation overriding scale‑match).*

---

# 2 · Experimental rigor & scientific method

### 2.1 — Settled an architecture question with a controlled A/B
**Situation.** Objects dissolved instead of being entered; two engine strategies were on the table (dive *in* by crop‑and‑reimagine vs. build *out* by shrink‑and‑outpaint).
**What I did.** I insisted both be rendered as a controlled test, then gave a decisive verdict: *"Building out is awful. It's absolutely awful compared to building in."*
**Result.** "Build‑in, not build‑out" became a permanent doctrine and the engine's whole reason for existing.
**Shows:** running a real A/B on an architectural variable and committing to the evidence. *Answers:* "a data‑driven decision," "how you choose between approaches."

### 2.2 — Refused to co‑vary two weak subsystems
**Situation.** Both the engine and the journey content were weak; it was tempting to improve them together.
**What I did.** *"It's not smart to try to improve the engine and the journeys simultaneously because their deficiencies are gonna cohere."* I fixed a known‑good journey as the test bed so engine changes were the only variable.
**Result.** Clean attribution of every subsequent engine change; the first reliable object‑tracking locks came out of it.
**Shows:** variable isolation / controlled fixtures. *Answers:* "how you debug when everything is broken at once."

### 2.3 — Metacognition about LLM misdiagnosis
**Situation.** Three mornings of poster failures, each "fixed" and each recurring.
**What I did.** I named the failure mode directly: *"the first idea you have is your diagnosis. You're very prone to misdiagnosis. Not just you — all the LLMs,"* and supplied the real hypothesis (display sleep / tab throttling) from the pattern that evening posts worked and morning ones didn't.
**Result.** Anti‑throttle browser flags + cold‑session handling; the class of failure ended.
**Shows:** understanding *how the tools fail* and compensating — a core AI‑engineering skill. *Answers:* "working with AI tools," "a time you had to correct an automated system."

### 2.4 — Killed a feature that showed no measurable effect
**Situation.** After a week of building "engine‑3" camera‑motion labs (orbit/dolly/tilt), I watched the A/B clips.
**What I did.** I judged them null — *"it just looks like two videos that diverge slightly in content"* — and set the adoption bar: *"if you have any evidence that anything from Phase D does what it's supposed to, that's what I wanna see."*
**Result.** Camera vocabulary parked; effort redirected to unsolved problems. We later quantified *why* — the image‑space warp sat under the engine's own frame‑to‑frame "noise floor."
**Shows:** gating adoption on evidence, not effort sunk; distinguishing genuine signal from stochastic divergence. *Answers:* "a time you killed your own work," "sunk‑cost."

### 2.5 — Diagnosed the *evaluation harness* as the problem
**Situation.** Side‑by‑side A/B renders were impossible to judge.
**What I did.** I identified two harness flaws: clips too short (*"your A/B videos only have about four discernible frames"*) and simultaneous display (*"can you make one video that has all four in order? It's hard to tell with all of them on screen at once"*). Later I formalized the rule that in a feedback engine a 1‑pixel perturbation becomes different *content* within ~10 frames, so same‑seed side‑by‑sides can't isolate motion at all — **judge single clips**.
**Result.** A better lab format (longer, sequential, single‑variable) and a stated methodological law.
**Shows:** recognizing that a bad measurement instrument yields unreadable results. *Answers:* "how you design experiments / evaluation."

*Additional evidence: manually posted a silent, hand‑labeled video to isolate a TikTok failure to the platform ("so it's not the music — same issue"); insisted on end‑to‑end unattended validation ("worked once with help ≠ verified"); flagged a confound in the analytics himself ("it's hard for me to let go of our testing integrity") rather than take a flattering result at face value.*

---

# 3 · Systems & architecture design

### 3.1 — The three‑layer format (design for controlled variation)
**Situation.** Raw prompts gave either sameness or chaos; the goal was infinite variety that stays on‑brand.
**What I did.** I specified that the invariant structure and the varied content must be separated: *"we wanna structure this so that what's varied is varied and what's set is set."*
**Result.** The FORMAT (fixed signature) / STYLE (palette deck) / JOURNEY (world‑cards compiled through fixed grammar) layering that still governs the system — journeys are slot‑fillers through templates, never raw prompts.
**Shows:** designing a system for bounded variation; separating mechanism from data. *Answers:* "a design you're proud of," "how you keep a generative system on‑brand."

### 3.2 — Designed the self‑driving pipeline with backpressure
**Situation.** Moving from hand‑run batches to a fully autonomous nightly system.
**What I did.** I specified the whole control loop working backward from the output, including a stop condition: *"if I have twenty videos ready to go live, then the batch scheduler stops."*
**Result.** A nightly refill → render → review → post loop with budgeted renders and backpressure so it never overproduces.
**Shows:** end‑to‑end control‑loop design with feedback (backpressure). *Answers:* "design a system that runs unattended."

### 3.3 — Derived partial re‑renders from the engine's state model
**Situation.** Every render restarted from scratch; I wanted to repair a bad loop seam without re‑rendering the whole video.
**What I did.** I reasoned from how the feedback chain works — each frame needs only the previous one — to argue the capability must exist: *"the logic to me seems like we should be able to pick right up at any frame."*
**Result.** A resume‑at‑frame / seam‑repair mechanism (and later whole‑card splicing), turning hour‑long re‑renders into minutes.
**Shows:** deriving an architectural capability from first principles about system state. *Answers:* "a performance or workflow optimization."

### 3.4 — Phase‑locked two clocks by shifting the cheaper one
**Situation.** Generated music landed its accents slightly off the video's morph beats.
**What I did.** Rather than regenerate audio, I proposed aligning the two periodic systems by shifting the video's start frame in whole measures: *"adjust the frame so that the morphs land on the beat."*
**Result.** The music‑alignment mechanism; whole‑measure start shifts preserve the beat lock exactly.
**Shows:** locking two independent periodic systems by adjusting phase on the cheaper side. *Answers:* "an elegant cross‑domain solution."

### 3.5 — Replaced a broken heuristic with weighted stochastic sampling
**Situation.** A nightly Long/Medium/Short rotation template never actually produced mediums or shorts, so the queue clogged with long renders.
**What I did.** I diagnosed the flaw and specified the replacement: *"that keeps a nice mix of long, medium, and shorts weighted the way I want, but it's not a predictable rotation."* — and asked to be corrected if I was "misthinking."
**Result.** Tier templates retired; a Monte‑Carlo draw weighted by target ratios that converges to the mix without predictable ordering.
**Shows:** knowing a deterministic rotation can't hit a target distribution; choosing weighted sampling. *Answers:* "a time you used probability/statistics in a design."

### 3.6 — Separated roles in the agent architecture, with hard invariants
**Situation.** Planning camera moves ("engine 3").
**What I did.** I required a distinct role instead of overloading one model — *"we don't want the same model writing the journey to also plan the camera motion… a separate cinematographer role"* — and fixed the invariants any design must respect (constant zoom, moves land on the beat, the loop must close).
**Result.** A separate rule‑based cinematographer layer; invariants encoded so the loop closes structurally.
**Shows:** responsibility separation in a multi‑agent system + invariant‑driven design. *Answers:* "designing multi‑agent / multi‑model systems."

*Additional evidence: async music pre‑generation to take a slow step off the interactive path (after verifying the data dependency); cost‑driven model allocation ("composition on the frontier model; scheduling and validation on local"); a dead‑zone posting remap that preserves the underlying 19‑hour cadence clock ("keep the nineteen‑hour clock as if we hadn't changed the times").*

---

# 4 · ML & applied‑AI judgment

### 4.1 — Named the core ML failure mode: morph vs. zoom
**Situation.** Early renders looked cool but weren't doing the thing.
**What I did.** I distinguished output from objective and tied it to a market risk: *"this is more of a morph thing than a zoom thing… there are a lot of morph videos out there. I don't think ours will stand out enough."*
**Result.** The entire engine was subsequently built to *fight morph‑feel* (object tracking, depth‑CN, low travel‑denoise so structures persist).
**Shows:** separating "looks impressive" from "solves the objective"; connecting a model artifact to product differentiation. *Answers:* "when a model's output was misleading."

### 4.2 — Designed a reach‑aware performance metric
**Situation.** Videos were ranked by like‑rate, which unfairly punished high‑reach posts.
**What I did.** I argued the metric threw away signal — *"the likelihood of a like drops off pretty quickly after the average number of views"* — and asked for a metric that credits earned reach, with a tunable parameter.
**Result.** A qscore = engagement vs. reach‑expected, fit on the catalog's own scaling law (engagement ≈ 0.14·views^0.68).
**Shows:** recognizing a biased metric and specifying a better one from first principles. *Answers:* "designing metrics / evaluation for an ML product."

### 4.3 — Few‑shot examples cause mode collapse
**Situation.** Writing the journey‑composer skill (an LLM prompt that mass‑produces content).
**What I did.** I argued against worked examples in the prompt: *"the more examples you have of what to do, they just get copied throughout — the samer our videos are gonna be."* State rules as tests to apply, not models to imitate.
**Result.** The composer skill states constraints, not exemplars; catalog diversity held up.
**Shows:** understanding few‑shot bias / the diversity–adherence tradeoff — directly transferable prompt‑engineering insight. *Answers:* "prompt engineering," "getting variety out of an LLM."

### 4.4 — "Get the method right" — generalizable over bespoke
**Situation.** Iterating on beat‑synced music; the instinct was to hand‑author melodies on top of the model.
**What I did.** I rejected the bespoke path: *"I wanna get the method right… I don't want Fable or Opus to write a theme every time. I wanna make sure the model can write the music."*
**Result.** A rules‑based music deck (rhythm/anacrusis constraints) that generates rankable candidates automatically — a pipeline, not a babysat demo.
**Shows:** insisting a solution generalize instead of a one‑off the frontier model hand‑holds. *Answers:* "turning a prototype into a system."

*Additional evidence: resisted over‑constraining generative diversity ("why not a herd of zebras and we zoom into one at random? we're over‑constraining"); caught an edge case where a well‑meant rule ("target must be findable in this scale") would forbid zooming into atoms.*

---

# 5 · Forward‑deployed: requirements, ambiguity & the customer

### 5.1 — Fixed a misread of intent before it drove wasted work
**Situation.** The build was heading toward a literal, scientific renderer.
**What I did.** I reframed the whole product: *"You were taking me too literally… This is not a science project. This is a project in getting people's attention."*
**Result.** Reset toward an AI‑generated "visual feast," which became the brand — loose science as awe‑garnish, visuals maximized.
**Shows:** detecting and correcting a requirements misread early; keeping the true objective in view. *Answers:* "ambiguous requirements," "a time you changed direction."

### 5.2 — Turned a fuzzy quality complaint into a general mechanism spec
**Situation.** Realm transitions (e.g. animal → cell) looked like a flat blur or a wrong camera pull‑back.
**What I did.** I described the target behavior concretely — *"one pixel that was on the back of the animal now becomes a whole tissue lattice"* — then demanded generality: *"I wanna make sure this technique is going to lead us through every realm shift,"* with an override for shifts that don't fit.
**Result.** The resolve‑on‑approach scaffold engine (band‑keyed modes + per‑journey override).
**Shows:** translating a vague "looks wrong" into a general, testable spec with an escape hatch. *Answers:* "translating stakeholder feedback into engineering work."

### 5.3 — Library‑before‑engine: validate before you integrate
**Situation.** IP‑Adapter reference steering was proposed to fix hard‑to‑render realms.
**What I did.** I refused to touch the engine until the reference library was proven — *"before you build or implement anything into our engine, I wanna see the libraries"* — and articulated the specific risk: external conditioning could break the feedback‑chain coherence (*"the worst images in the video are the ones not generated from a previous image"*).
**Result.** Integration deferred; the cheaper prompt‑side fix shipped first and was watched.
**Shows:** sequencing validation ahead of integration; reasoning about how a change threatens an existing invariant. *Answers:* "de‑risking a big change," "when you said no to a proposed approach."

*Additional evidence: repeatedly converted creative intent into unambiguous mechanical specs and held the loop accountable when feedback wasn't acted on ("this is the third time I'm saying this… that feedback wasn't fixed").*

---

# 6 · Reliability, ops & maintainability

### 6.1 — Immutable artifacts
**What I did.** After a re‑render overwrote a prior video, I set a hard rule: *"Let's never overwrite videos."*
**Result.** Versioned, never‑overwritten outputs (finals at root, intermediates in build/).
**Shows:** immutable‑artifact / reproducibility discipline. *Answers:* "a data‑integrity practice."

### 6.2 — Build the alarm before the outage
**Situation.** The browser poster depends on third‑party site DOMs I don't control.
**What I did.** I specified observability up front: *"we just wanna flag easily if something's changed and our posting isn't working."*
**Result.** A flag/telemetry layer (screenshots + text context + a flags log) so silent breakage surfaces immediately.
**Shows:** designing for detectability of failure in dependencies you don't own. *Answers:* "how you handle brittle external integrations."

### 6.3 — Documentation and runbooks as part of "done"
**What I did.** After a day of building repair tooling: *"maybe a quick user's guide in case in a couple weeks I've forgotten what we did today"* — and I required that nothing important live only in a conversation.
**Result.** Durable decision logs (a project orientation doc + plan of record) and a repair skill with a decision tree.
**Shows:** treating rationale and runbooks as deliverables, so the system survives context loss. *Answers:* "how you make work maintainable / onboard others."

### 6.4 — Made the whole pipeline restart‑proof
**Situation.** A forced Windows Update reboot in the render window killed a night and left posts stuck.
**What I did.** I chose the fix that requires no attention over the one that does (auto‑logon so tasks resume from boot, over merely shifting update hours), and asked what the security tradeoff actually was before deciding.
**Result.** Auto‑logon (LSA‑encrypted, not plaintext) + catch‑up on scheduled tasks + a guard so a missed night can't launch an 8‑hour batch at login. Verified end‑to‑end.
**Shows:** reliability engineering with an explicit risk tradeoff. *Answers:* "making a system resilient to failure."

*Additional evidence: fail‑fast guard aborting a render when frame 0 hallucinates a lone figure (saves an hour of GPU); reversibility‑first data lifecycle for a disk‑space crunch ("without permanently deleting anything now, make a plan").*

---

# 7 · Leading the build: prioritization & operating AI agents

### 7.1 — Held the loop accountable and re‑specified precisely
**Situation.** A journey kept rendering without the intended object‑containment zoom.
**What I did.** I re‑specified it mechanically — *"a little round thing on the tip of the antenna, we zoom in and see it's a planet"* — while flagging that prior feedback hadn't been acted on: *"this is the third time I'm saying this."*
**Shows:** unambiguous specification + accountability when an automated agent drifts. *Answers:* "managing an underperforming contributor / process."

### 7.2 — Kept experiments out of production
**Situation.** Running GPU experiments while the nightly production pipeline also ran.
**What I did.** I drew a hard boundary: *"don't put anything obviously in the pipeline — just leave it for me to judge when I get home,"* and set scope limits on compute (*"it can't really be gigantic"*).
**Result.** Lab flags defaulted off; comparison renders never leaked into the posting queue.
**Shows:** separating experimentation from production; guardrails on an autonomous agent. *Answers:* "how you manage risk with automation / AI."

### 7.3 — Ordered work by technical dependency, not apparent difficulty
**Situation.** Planning partial‑re‑render tooling.
**What I did.** I chose to build the hard seam‑blending primitive first because it makes the easy splice trivial: *"level three, combined in level two, will be almost trivial once we've done it."*
**Shows:** dependency‑ and risk‑aware sequencing. *Answers:* "how you prioritize a roadmap."

*Additional evidence: separated act‑now from investigate‑only work under a backlog ("there are things we had to fix just with that video, and things more important to think about generally"); disciplined context management before clearing AI sessions so no decision was lost.*

---

# A longitudinal thread (worth telling as one arc)
The **planet → landscape** failure — a planet dissolving into the background instead of being entered — I first reported on **2026‑07‑29** (*"the planets kind of dissolve, shrink and stop coming by"*). A month later I connected it to a *second* symptom (creatures popping in and out of scale) and hypothesized a **shared root cause**: *"the scaffold holds instances in existence, but only during arrival windows — why?"* That reframed both bugs as one "persistence" problem and drove the fix. **Interview value:** shows sustained, mechanism‑level problem‑tracking across a large system over weeks — not one‑shot patching.

---

# Cover‑letter soundbites (lift and adapt)
- *"I built and operate a fully autonomous, local AI video pipeline on a single GPU — diffusion render engine, beat‑locked music generation, self‑healing browser automation, analytics, and a nightly scheduler — by directing AI coding agents under close engineering review. My value‑add is judgment: I have a documented record of catching the AI's misdiagnoses, isolating variables, and making the systems calls a model won't."*
- *"I treat AI output the way a good engineer treats any component: verify against ground truth, reproduce the failure, isolate the variable, prove the mechanism. I've killed my own features when the A/B showed no real effect, and rewritten evaluation harnesses that couldn't measure what they claimed to."*
- *"I formalize problems instead of hand‑tuning them — a three‑layer content grammar for bounded variation, a measured perceptual 'noise floor' to decide which motion is even worth rendering, weighted stochastic scheduling to hit a target mix without predictable rotation."*

# One‑page technical facts (credibility)
- **Stack:** Python, ComfyUI (SDXL/DreamShaper feedback‑zoom, ControlNet depth, Florence‑2 detection, DepthAnything, IP‑Adapter, ACE‑Step music), CDP browser automation (websocket), Streamlit ops dashboard, Windows Task Scheduler, local VLM (Ollama) for vision checks. All local/free on an RTX 3080.
- **Architecture:** three‑layer format grammar; single‑source‑of‑truth JSON state with atomic writes + merge‑on‑fresh concurrency; nightly compose→render→caption→post loop with budgeted renders + backpressure; per‑frame zoom/denoise/track schedules compiled from declarative journeys.
- **Reliability:** immutable versioned outputs; self‑healing poster (CDP reconnect, tab rebuild, live post verification, caption self‑heal); telemetry + flag logs; restart‑proof scheduling.
- **Scale of the build:** ~280 commits; documented decision log; runs unattended for days.

---
*Quotes are from my own project prompts (voice‑dictated, lightly trimmed). This document is structured for a job‑search agent to parse: stories are grouped by competency, each tagged with the skill shown and the interview questions it answers.*
