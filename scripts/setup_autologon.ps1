# Powers of Zen — restart-proofing: enable Windows auto-logon the SECURE way.
# Downloads Sysinternals Autologon (stores the password LSA-ENCRYPTED, never plaintext —
# unlike the classic HKLM\Winlogon DefaultPassword method) and launches it. You type your
# password into its dialog and click Enable. Nothing here sees or stores your password.
# After this, a reboot logs Phil in automatically -> the scheduled tasks fire -> the poster
# self-heals Chrome -> Ollama starts from the Startup folder -> the pipeline resumes with
# no human at the keyboard. Run from the project root:  ! powershell -ExecutionPolicy Bypass -File scripts\setup_autologon.ps1
$ErrorActionPreference = 'Stop'
$exe = "$env:USERPROFILE\Downloads\Autologon.exe"
if (-not (Test-Path $exe)) {
  Write-Host "Downloading Sysinternals Autologon..."
  Invoke-WebRequest -Uri 'https://live.sysinternals.com/Autologon.exe' -OutFile $exe
}
Write-Host "Launching Autologon. In the dialog: leave Username/Domain as-is, type your"
Write-Host "Windows password, click Enable. (LSA-encrypted; no plaintext password stored.)"
Start-Process $exe
