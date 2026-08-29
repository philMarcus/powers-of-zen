@echo off
REM Powers of Zen — nightly render batch. Run by Windows Task Scheduler at 01:30.
REM Auto-picks queued journeys from outbox/journeys.json (tier template within the
REM render budget), renders each, captions, drops them in Video Review. Skips the
REM night when enough videos are already ready to post (backpressure) or when
REM render_paused is set (dashboard Settings tab). No Claude involved.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/night_batch.py --scheduled >> outbox/night_batch.log 2>&1"
