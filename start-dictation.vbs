' Tichý launcher – spustí dictate.py přes pythonw bez okna konzole.
' Cesta se odvozuje od umístění tohoto skriptu (funguje kdekoli).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
sh.Run """" & base & "\.venv\Scripts\pythonw.exe"" """ & base & "\dictate.py""", 0, False
