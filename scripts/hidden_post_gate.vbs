' Powers of Zen - runs the posting gate with NO window and NO focus steal.
' Task Scheduler starting a .bat in the interactive session pops a console that grabs
' focus; wscript is a GUI host and Run(...,0,False) gives the bat a hidden window.
CreateObject("Wscript.Shell").Run """C:\Users\Phil\zoomer\scripts\scheduled_post_gate.bat""", 0, False
