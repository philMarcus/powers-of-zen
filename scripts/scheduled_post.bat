@echo off
REM legacy 08:00/18:00 posting tasks are locked to this file (elevation needed to edit
REM the tasks themselves) - hand off to the hidden runner and exit immediately so the
REM console flash is sub-second. The gate makes double-posting impossible.
wscript.exe C:\Users\Phil\zoomer\scripts\hidden_task.vbs C:\Users\Phil\zoomer\scripts\scheduled_post_gate.bat
