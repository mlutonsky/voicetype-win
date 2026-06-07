' Silent launcher - starts dictate.py via pythonw without a console window.
' The path is derived from this script's location (works anywhere).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
sh.Run """" & base & "\.venv\Scripts\pythonw.exe"" """ & base & "\dictate.py""", 0, False
