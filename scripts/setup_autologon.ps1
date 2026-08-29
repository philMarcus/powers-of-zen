# Powers of Zen — restart-proofing: enable Windows auto-logon the SECURE way.
# Downloads Sysinternals Autologon (stores the password LSA-ENCRYPTED, never plaintext —
# unlike the classic HKLM\Winlogon DefaultPassword method) and launches it. You type your
# password into its dialog and click Enable. Nothing here sees or stores your password.
# After this, a reboot logs Phil in automatically -> the scheduled tasks fire -> the poster
# self-heals Chrome -> Ollama starts from the Startup folder -> the pipeline resumes with
# no human at the keyboard. Run from the project root:
#   ! powershell.exe -ExecutionPolicy Bypass -File 'C:\Users\Phil\zoomer\scripts\setup_autologon.ps1'
$ErrorActionPreference = 'Stop'
# Save into the project folder (Downloads may be redirected to OneDrive/Dropbox and absent).
$dest = 'C:\Users\Phil\zoomer'
$exe = Join-Path $dest 'Autologon.exe'
if (-not (Test-Path $exe)) {
  Write-Host "Downloading Sysinternals Autologon to $exe ..."
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  try {
    Invoke-WebRequest -Uri 'https://live.sysinternals.com/Autologon.exe' -OutFile $exe -UseBasicParsing
  } catch {
    Write-Host "live.sysinternals.com failed ($($_.Exception.Message)); trying the download-farm zip..."
    $zip = Join-Path $dest 'Autologon.zip'
    Invoke-WebRequest -Uri 'https://download.sysinternals.com/files/AutoLogon.zip' -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $dest -Force
    if (Test-Path (Join-Path $dest 'Autologon64.exe')) { $exe = Join-Path $dest 'Autologon64.exe' }
  }
}
Write-Host ""
Write-Host "Launching Autologon. In the dialog: leave Username/Domain as-is, type your"
Write-Host "Windows password, click Enable. (LSA-encrypted; no plaintext password stored.)"
Start-Process $exe
