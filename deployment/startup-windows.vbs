' Start GalleryCleaner service.
' Place in: shell:startup (Win+R, type "shell:startup")
' Or create a scheduled task to run at system startup.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get project root directory
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
projectRoot = objFSO.GetParentFolderName(scriptDir)

' Construct the full path to the batch file
batchFilePath = projectRoot & "\scripts\run.bat"

' Check if batch file exists
if not objFSO.FileExists(batchFilePath) then
    WScript.Echo "ERROR: run.bat not found at " & batchFilePath
    WScript.Quit 1
end if

' Run the batch file from the project root
objShell.Run "cmd /c cd /d " & quote(projectRoot) & " && scripts\run.bat", 0, False

Function quote(s)
    quote = Chr(34) & s & Chr(34)
End Function

Set objShell = Nothing
Set objFSO = Nothing
