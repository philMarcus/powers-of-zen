@echo off
REM Powers of Zen — midnight journey refill. Run by Windows Task Scheduler at 00:00.
REM If the journey queue is below its target, one headless Claude session (Fable
REM coordinator -> parallel Opus composers via the journey-composer skill) writes new
REM journeys; the script audits each and auto-queues only the passers. Hard 45min
REM timeout so it is always done before the 01:30 render batch.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/journey_refill.py >> outbox/refill.log 2>&1"
