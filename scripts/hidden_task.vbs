' Powers of Zen - generic HIDDEN task runner: wscript.exe hidden_task.vbs <path-to-bat>
' Task Scheduler starting a console .bat in the interactive session pops a cmd window
' that steals focus (and an accidentally-closed window kills the job). wscript is a
' GUI host; Run(...,0,False) executes the bat with no window at all.
CreateObject("Wscript.Shell").Run """" & WScript.Arguments(0) & """", 0, False
