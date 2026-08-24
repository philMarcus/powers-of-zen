# Windows Task Scheduler — Powers of Zen (all four tasks)

The full no-Claude daily loop (times local):

| task                | time  | .bat                    | does |
|---------------------|-------|-------------------------|------|
| PowersOfZen-refill  | 00:00 | scheduled_refill.bat    | tops the JOURNEY queue toward its target — ONE headless Claude call (Fable coordinator → Opus composers), audits + auto-queues passers. Skips when queue ≥ target or refill_paused. |
| PowersOfZen-render  | 01:30 | scheduled_render.bat    | renders queued journeys (tier template within render_budget_min), captions, drops in Video Review. Skips on backpressure (≥ max_ready_videos ready to post) or render_paused. |
| PowersOfZen-postgate | hourly | scheduled_post_gate.bat | CADENCE GATE (2026-08-17): posts fire every `post_every_hours` (settings, default 19h) at `post_next` — both dashboard-editable (Settings tab). The gate advances the clock past missed windows without burst-posting. DEAD-ZONE REMAP (2026-08-24): a virtual window in [01:00,03:30) actually posts at 21:00 the night before; [03:30,07:00) posts at 09:00 that morning — but the 19h clock ALWAYS advances from the VIRTUAL time, so the time-of-day walk is undistorted. Never posts 01:00–07:00 even after downtime. |
| PowersOfZen-igstats | 12:00 + 00:00 | scheduled_ig_stats.bat | IG stats snapshot (2026-08-22: count likes/views more often than the 19h post cadence — the poster also snapshots after every post). Runs ig_stats.py (reels grid: views/likes/comments/followers) THEN ig_insights.py (Meta Business Suite: reach/shares/saves/follows/watch time — linked via "Continue with Instagram" 2026-08-22; if the session dies, telem ig_insights_login fires and the link must be redone by hand once). Both self-heal Chrome, skip if a poster run is in flight, lock against overlap. Log: outbox/ig_stats_task.log. |
| PowersOfZen-8am     | 08:00 | scheduled_post.bat      | LEGACY — now delegates to the same gate (harmless; delete with elevation when convenient: `schtasks /Delete /TN "PowersOfZen-8am" /F`). |
| PowersOfZen-6pm     | 18:00 | scheduled_post.bat      | LEGACY — same as above. |

Knobs (queue target, budget, backpressure, tier mix, pauses) live in outbox/journeys.json
→ editable in the dashboard's ⚙ Settings tab. Times live HERE, not in settings.

## HIDDEN EXECUTION (2026-08-19 — hard-won, don't regress)
A console .bat fired by Task Scheduler in the interactive session POPS A CMD WINDOW that
steals focus (hourly gate = hourly focus theft), and an accidentally-closed window kills
the job (a render dies mid-batch). All three owned tasks therefore run through
`scripts/hidden_task.vbs` (a generic runner: `wscript.exe hidden_task.vbs <path-to-bat>`
— wscript is a GUI host, `Run(...,0,False)` gives the bat NO window). The legacy 8am/6pm
tasks are locked to scheduled_post.bat (elevation needed to edit them), so that bat now
just hands off to the hidden runner and exits — sub-second flash instead of a lingering
console.

.bat AUTHORING RULES (each broke a night silently before being learned):
  • CRLF line endings — bash-heredoc-written .bats get LF and Task Scheduler's cmd
    misparses them (write with python newline="" and explicit \r\n).
  • Task Scheduler cwd is System32 — every WSL call must `cd /mnt/c/Users/Phil/zoomer &&`
    first or relative paths fail with an empty log and Last Result 1.
  • `timeout /t` needs console stdin and dies under the scheduler — use `ping -n N
    127.0.0.1 >nul` if a wait is ever needed (currently none is: poster self-heals Chrome).
  • schtasks /Change /TR prompts for a password (hangs headless) and /TR quoting mangles
    through WSL interop — repoint actions with PowerShell instead:
    `Set-ScheduledTask -TaskName X -Action (New-ScheduledTaskAction -Execute 'wscript.exe'
    -Argument 'C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\...\target.bat')`

## Register (run once in PowerShell or cmd; ADMIN if it complains):
    schtasks /Create /TN "PowersOfZen-refill"   /TR "wscript.exe C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\Users\Phil\zoomer\scripts\scheduled_refill.bat" /SC DAILY /ST 00:00 /F
    schtasks /Create /TN "PowersOfZen-render"   /TR "wscript.exe C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\Users\Phil\zoomer\scripts\scheduled_render.bat" /SC DAILY /ST 01:30 /F
    schtasks /Create /TN "PowersOfZen-postgate" /TR "wscript.exe C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\Users\Phil\zoomer\scripts\scheduled_post_gate.bat" /SC HOURLY /ST 00:05 /F

PowersOfZen-igstats needs TWO daily triggers (12:00 + 00:00), which schtasks can't express
in one task — register via PowerShell instead (this is how it was created 2026-08-22):

    $a  = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument 'C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\Users\Phil\zoomer\scripts\scheduled_ig_stats.bat'
    $t1 = New-ScheduledTaskTrigger -Daily -At '12:00'
    $t2 = New-ScheduledTaskTrigger -Daily -At '00:00'
    Register-ScheduledTask -TaskName 'PowersOfZen-igstats' -Action $a -Trigger $t1,$t2 -Force

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
