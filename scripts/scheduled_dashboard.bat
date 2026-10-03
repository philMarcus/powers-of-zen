@echo off
REM Powers of Zen - at-logon ops starter (Task Scheduler: PowersOfZen-dashboard, AtLogOn + 90 s).
REM A Windows restart kills the dashboard, ComfyUI and the zen Chrome; nothing relaunched them
REM (2026-10-02 reboot: dashboard down until 10-03). Brings up Chrome (CDP :9222), the Streamlit
REM dashboard (own Windows process) and ComfyUI (via the batch launcher, pinned to the P-cores).
REM Idempotent: each starter is a no-op when its service already answers.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && bash scripts/start_chrome_zen.sh >> outbox/logon_ops.log 2>&1; bash scripts/start_dashboard.sh >> outbox/logon_ops.log 2>&1; python3 -c \"import sys; sys.path.insert(0,'scripts'); sys.argv=['x']; import night_batch as nb; nb.comfy_up()\" >> outbox/logon_ops.log 2>&1"
