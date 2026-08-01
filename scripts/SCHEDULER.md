# Windows Task Scheduler — Powers of Zen (all four tasks)

The full no-Claude daily loop (times local):

| task                | time  | .bat                    | does |
|---------------------|-------|-------------------------|------|
| PowersOfZen-refill  | 00:00 | scheduled_refill.bat    | tops the JOURNEY queue toward its target — ONE headless Claude call (Fable coordinator → Opus composers), audits + auto-queues passers. Skips when queue ≥ target or refill_paused. |
| PowersOfZen-render  | 01:30 | scheduled_render.bat    | renders queued journeys (tier template within render_budget_min), captions, drops in Video Review. Skips on backpressure (≥ max_ready_videos ready to post) or render_paused. |
| PowersOfZen-8am     | 08:00 | scheduled_post.bat      | posts the next queued video (Chrome-zen CDP). |
| PowersOfZen-6pm     | 18:00 | scheduled_post.bat      | second daily post. |

Knobs (queue target, budget, backpressure, tier mix, pauses) live in outbox/journeys.json
→ editable in the dashboard's ⚙ Settings tab. Times live HERE, not in settings.

## Register (run once in PowerShell or cmd; ADMIN if it complains):
    schtasks /Create /TN "PowersOfZen-8am"    /TR "C:\Users\Phil\zoomer\scripts\scheduled_post.bat"   /SC DAILY /ST 08:00 /F
    schtasks /Create /TN "PowersOfZen-6pm"    /TR "C:\Users\Phil\zoomer\scripts\scheduled_post.bat"   /SC DAILY /ST 18:00 /F
    schtasks /Create /TN "PowersOfZen-refill" /TR "C:\Users\Phil\zoomer\scripts\scheduled_refill.bat" /SC DAILY /ST 00:00 /F
    schtasks /Create /TN "PowersOfZen-render" /TR "C:\Users\Phil\zoomer\scripts\scheduled_render.bat" /SC DAILY /ST 01:30 /F

All tasks run "Interactive only" (Phil stays logged in; system sleep is Never). The
overnight pair needs the machine AWAKE at 00:00/01:30 — if that's ever not true, tick
"Wake the computer to run this task" under Conditions in the GUI for refill + render.

## Manage:
    schtasks /Query  /TN "PowersOfZen-render"     (status/last-run)
    schtasks /Run    /TN "PowersOfZen-render"     (test now)
    schtasks /Delete /TN "PowersOfZen-render" /F  (remove)

Logs: outbox/scheduler.log (posts) · outbox/night_batch.log + outbox/night_batch_*.log
(renders) · outbox/refill.log (refill; briefs in outbox/refill_briefs_*.md). Telemetry
events land in the dashboard: batch_skip / render / render_fail / batch_done / refill /
refill_done.
