# Windows Task Scheduler — Powers of Zen auto-poster

Runs `scripts/scheduled_post.bat` twice daily. It ensures Chrome-zen is up, then runs
poster.py, which posts the next `queued` video from pipeline.json (no-ops if none queued).
NO Claude in the loop — free. Approve videos in the dashboard to feed the queue.

## Register (run once in an ADMIN PowerShell or cmd):
    schtasks /Create /TN "PowersOfZen-8am"  /TR "C:\Users\Phil\zoomer\scripts\scheduled_post.bat" /SC DAILY /ST 08:00 /F
    schtasks /Create /TN "PowersOfZen-6pm"  /TR "C:\Users\Phil\zoomer\scripts\scheduled_post.bat" /SC DAILY /ST 18:00 /F

Optional (wake the PC to post): add  /RL HIGHEST  and in Task Scheduler GUI tick
"Wake the computer to run this task" under each task's Conditions.

## Manage:
    schtasks /Query  /TN "PowersOfZen-8am"     (status/last-run)
    schtasks /Run    /TN "PowersOfZen-8am"     (test now)
    schtasks /Delete /TN "PowersOfZen-8am" /F  (remove)

Logs: outbox/scheduler.log  (also visible in the dashboard Telemetry tab).
