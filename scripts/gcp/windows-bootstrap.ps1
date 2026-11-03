# First boot only, on the disposable GCP Windows VM. No credentials in this script.
# References: Google's Windows SSH guide and pinned compute-gpu-installation script;
# gcloudrig/gcloudrig.psm1 for Steam and Windows Audio preparation.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Path C:\wh3 -Force | Out-Null
Start-Transcript -Path C:\wh3\bootstrap.log -Append
try {
    & googet -noconfirm=true install google-compute-engine-ssh
    if ($LASTEXITCODE -ne 0) { throw 'Google SSH agent installation failed' }

    $driverUrl = 'https://raw.githubusercontent.com/GoogleCloudPlatform/compute-gpu-installation/68adbb94f7e1e66c4b823f05300b081e3a9d6a73/windows/install_gpu_driver.ps1'
    Invoke-WebRequest -UseBasicParsing -Uri $driverUrl -OutFile C:\wh3\install_gpu_driver.ps1
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\wh3\install_gpu_driver.ps1
    if ($LASTEXITCODE -ne 0) { throw 'NVIDIA installer failed; see its output above' }

    Install-WindowsFeature Server-Media-Foundation | Out-Host
    Set-Service Audiosrv -StartupType Automatic
    Start-Service Audiosrv
    $rdpPolicy = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services'
    New-Item $rdpPolicy -Force | Out-Null
    New-ItemProperty $rdpPolicy -Name bEnumerateHWBeforeSW -Value 1 -PropertyType DWord -Force | Out-Null
    & powercfg /change monitor-timeout-ac 0
    & powercfg /change standby-timeout-ac 0

    Invoke-WebRequest -UseBasicParsing -Uri 'https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe' -OutFile C:\wh3\SteamSetup.exe
    $signature = Get-AuthenticodeSignature C:\wh3\SteamSetup.exe
    if ($signature.Status -ne 'Valid') { throw 'Steam installer signature is not valid' }
    $steamInstall = Start-Process C:\wh3\SteamSetup.exe -ArgumentList '/S' -Wait -PassThru
    if ($steamInstall.ExitCode -ne 0) { throw "Steam installer exit $($steamInstall.ExitCode)" }
    # Google's driver script can return zero after an installer warning. GPU health
    # is a separate nvidia-smi/device check after reboot, not established by this marker.
    Write-Output 'WH3-BOOTSTRAP-DONE: installers finished; GPU check still required after reboot'
} finally {
    Stop-Transcript
}
