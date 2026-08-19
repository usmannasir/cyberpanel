#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:SmokeModuleRoot = $PSScriptRoot
$Script:CacheRoot = Join-Path $env:LOCALAPPDATA 'CyberPanelHyperVSmoke'
$Script:AlmaQcowUrl = 'https://repo.almalinux.org/almalinux/10/cloud/x86_64/images/AlmaLinux-10-GenericCloud-latest.x86_64.qcow2'
$Script:QemuZipUrl = 'https://cloudbase.it/downloads/qemu-img-win-x64-2_3_0.zip'
$Script:LabPassword = 'TestPass12'
$Script:GuestSshUser = 'root'
$Script:DefaultSwitchGateway = '172.20.80.1'
$Script:GuestStaticIps = @{
    'fresh' = '172.20.80.50'
    'upgrade' = '172.20.80.51'
}
$Script:VmProfiles = @{
    'fresh' = @{
        Name = 'cp-fresh-hv'
        HostPanelPort = 18090
        ProvisionScript = 'provision-fresh.sh'
    }
    'upgrade' = @{
        Name = 'cp-upgrade-hv'
        HostPanelPort = 28090
        ProvisionScript = 'provision-upgrade.sh'
    }
}

function Test-AdminRole {
    $principal = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Import-HyperVSmokeModule {
    if (-not (Get-Module -Name Hyper-V -ListAvailable)) {
        throw @(
            'Hyper-V PowerShell module is not installed.'
            'Run as Administrator from Test\hyperv:'
            '  .\Install-HyperV.ps1'
            'Reboot when prompted, then re-run .\up.ps1 fresh'
        ) -join "`n"
    }
    Import-Module Hyper-V -ErrorAction Stop | Out-Null
}

function Install-HyperVSmokeFeature {
    if (-not (Test-AdminRole)) {
        throw 'Install-HyperV.ps1 must run in an elevated Administrator PowerShell session.'
    }
    $feature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
    if ($feature -and $feature.State -eq 'Enabled') {
        Write-Host 'Hyper-V is already enabled.'
        return
    }
    Write-Host 'Enabling Hyper-V (reboot required)...'
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart:$false
}

function Ensure-SmokeCache {
    foreach ($dir in @($Script:CacheRoot, (Join-Path $Script:CacheRoot 'tools'), (Join-Path $Script:CacheRoot 'ssh'))) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
}

function Get-SmokeSshKeyPath {
    Ensure-SmokeCache
    $key = Join-Path $Script:CacheRoot 'ssh\id_ed25519'
    if (-not (Test-Path $key)) {
        Write-Host 'Generating SSH key for Hyper-V smoke guests...'
        $keyDir = Split-Path -Parent $key
        if (-not (Test-Path $keyDir)) {
            New-Item -ItemType Directory -Path $keyDir -Force | Out-Null
        }
        # Windows OpenSSH rejects `-N` with an empty PowerShell string; use explicit "".
        $proc = Start-Process -FilePath 'ssh-keygen' -ArgumentList @(
            '-t', 'ed25519', '-f', $key, '-q', '-N', '""'
        ) -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0 -or -not (Test-Path $key)) {
            throw "ssh-keygen failed (exit $($proc.ExitCode)) for Hyper-V smoke key."
        }
    }
    return $key
}

function Get-QemuImgPath {
    Ensure-SmokeCache
    $exe = Join-Path $Script:CacheRoot 'tools\qemu-img.exe'
    if (Test-Path $exe) { return $exe }
    $zip = Join-Path $Script:CacheRoot 'tools\qemu-img.zip'
    Write-Host 'Downloading qemu-img for Windows...'
    Invoke-WebRequest -Uri $Script:QemuZipUrl -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath (Join-Path $Script:CacheRoot 'tools') -Force
    $found = Get-ChildItem -Path (Join-Path $Script:CacheRoot 'tools') -Filter 'qemu-img.exe' -Recurse | Select-Object -First 1
    if (-not $found) { throw 'qemu-img.exe not found after extract.' }
    if ($found.FullName -ne (Resolve-Path -LiteralPath $exe).Path) {
        Copy-Item $found.FullName $exe -Force
    }
    return $exe
}

function Get-AlmaTemplateVhdxPath {
    Ensure-SmokeCache
    $vhdx = Join-Path $Script:CacheRoot 'AlmaLinux-10-GenericCloud.vhdx'
    if (Test-Path $vhdx) { return $vhdx }
    $qcow = Join-Path $Script:CacheRoot 'AlmaLinux-10-GenericCloud-latest.x86_64.qcow2'
    if (-not (Test-Path $qcow)) {
        Write-Host 'Downloading AlmaLinux 10 Generic Cloud image (~550 MB)...'
        Invoke-WebRequest -Uri $Script:AlmaQcowUrl -OutFile $qcow -UseBasicParsing
    }
    $qemu = Get-QemuImgPath
    Write-Host 'Converting qcow2 to VHDX (one-time)...'
    & $qemu convert -O vhdx -o subformat=dynamic $qcow $vhdx
    if ($LASTEXITCODE -ne 0) { throw "qemu-img convert failed with exit code $LASTEXITCODE" }
    return $vhdx
}

function Get-FreeDriveLetter {
    $used = @(Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object { $_.DriveLetter })
    foreach ($code in 70..90) {
        $letter = [char]$code
        if ($letter -notin $used -and -not (Test-Path "${letter}:\")) {
            return $letter
        }
    }
    throw 'No free drive letter for cloud-init CIDATA disk.'
}

function Format-CpMacAddress {
    param([Parameter(Mandatory)][string]$Mac)
    $clean = ($Mac -replace '[^0-9a-fA-F]', '').ToLower()
    if ($clean.Length -ne 12) { return $Mac.ToLower() }
    return ($clean -replace '(.{2})(?=.)', '$1:')
}

function Get-CloudInitUserData {
    param(
        [Parameter(Mandatory)][string]$VmName,
        [Parameter(Mandatory)][string]$PubKey,
        [Parameter(Mandatory)][ValidateSet('fresh', 'upgrade')][string]$Profile,
        [string]$MacAddress = ''
    )
    $staticIp = $Script:GuestStaticIps[$Profile]
    $gw = $Script:DefaultSwitchGateway
    $macLine = ''
    if ($MacAddress) {
        $macLine = @"
      match:
        macaddress: '$MacAddress'
"@
    }
    else {
        $macLine = @"
      match:
        driver: hv_netvsc
"@
    }
    return @"
#cloud-config
datasource_list: [ NoCloud, ConfigDrive ]
disable_root: false
ssh_pwauth: true
hostname: $VmName
growpart:
  mode: auto
bootcmd:
  - [ bash, -lc, "for d in /sys/class/net/*; do i=`$(basename `$d); [ `$i = lo ] && continue; ip link set `$i up; done" ]
network:
  version: 2
  ethernets:
    nic0:
$macLine
      dhcp4: false
      dhcp6: false
      addresses:
        - ${staticIp}/20
      routes:
        - to: default
          via: $gw
      nameservers:
        addresses: [$gw, 1.1.1.1]
users:
  - default
  - name: root
    lock_passwd: false
    ssh_authorized_keys:
      - $($PubKey.Trim())
  - name: almalinux
    groups: wheel
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - $($PubKey.Trim())
    lock_passwd: false
    plain_text_passwd: vagrant
chpasswd:
  list: |
    root:$($Script:LabPassword)
  expire: false
runcmd:
  - [ bash, -lc, "sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config; systemctl restart sshd || systemctl restart ssh || true" ]
"@
}

function New-CloudInitSeedIso {
    param(
        [Parameter(Mandatory)][string]$VmName,
        [Parameter(Mandatory)][string]$OutIso,
        [Parameter(Mandatory)][ValidateSet('fresh', 'upgrade')][string]$Profile,
        [string]$MacAddress = ''
    )
    $seedDir = Join-Path $Script:CacheRoot "seed-$VmName"
    if (Test-Path $seedDir) { Remove-Item $seedDir -Recurse -Force }
    New-Item -ItemType Directory -Path $seedDir -Force | Out-Null

    $meta = @"
instance-id: $VmName
local-hostname: $VmName
"@
    $pubKey = Get-Content -Raw "$(Get-SmokeSshKeyPath).pub"
    $user = Get-CloudInitUserData -VmName $VmName -PubKey $pubKey -Profile $Profile -MacAddress $MacAddress
    Set-Content -Path (Join-Path $seedDir 'meta-data') -Value $meta -NoNewline -Encoding ascii
    Set-Content -Path (Join-Path $seedDir 'user-data') -Value $user -Encoding ascii

    if (Test-Path $OutIso) { Remove-Item $OutIso -Force }
    function ConvertTo-WslPath([string]$WinPath) {
        $p = $WinPath -replace '\\', '/'
        if ($p -match '^([A-Za-z]):(/.*)$') {
            return ('/mnt/{0}{1}' -f $Matches[1].ToLower(), $Matches[2])
        }
        return $p
    }
    $wslDir = ConvertTo-WslPath $seedDir
    $wslIso = ConvertTo-WslPath $OutIso
    $geniso = $false
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        wsl -u root bash -lc "command -v xorriso >/dev/null 2>&1 || dnf install -y xorriso >/dev/null 2>&1; xorriso -as mkisofs -output '$wslIso' -V cidata -r -J -graft-points '/meta-data=$wslDir/meta-data' '/user-data=$wslDir/user-data' >/dev/null 2>&1"
        if ($LASTEXITCODE -eq 0 -and (Test-Path $OutIso)) { $geniso = $true }
    }
    if (-not $geniso) {
        throw 'Could not build cloud-init ISO (install WSL + xorriso).'
    }
    return $OutIso
}

function New-CloudInitDataVhd {
    param(
        [Parameter(Mandatory)][string]$VmName,
        [Parameter(Mandatory)][string]$OutPath,
        [Parameter(Mandatory)][ValidateSet('fresh', 'upgrade')][string]$Profile,
        [string]$MacAddress = ''
    )
    if (Test-Path $OutPath) { Remove-Item $OutPath -Force }
    $null = New-VHD -Path $OutPath -SizeBytes 64MB -Dynamic
    $vhd = Mount-VHD -Path $OutPath -Passthru
    try {
        $disk = Get-Disk | Where-Object { $_.Number -eq $vhd.DiskNumber }
        Set-Disk -Number $disk.Number -IsOffline $false
        Initialize-Disk -Number $disk.Number -PartitionStyle MBR -ErrorAction SilentlyContinue
        $part = Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $part) {
            $part = New-Partition -DiskNumber $disk.Number -UseMaximumSize
        }
        $vol = Get-Volume -Partition $part -ErrorAction SilentlyContinue
        if (-not $vol -or -not $vol.FileSystemLabel) {
            Format-Volume -Partition $part -FileSystem FAT32 -NewFileSystemLabel cidata -Confirm:$false -Force -ErrorAction Stop | Out-Null
            Start-Sleep -Seconds 2
            $part = Get-Partition -DiskNumber $disk.Number | Select-Object -First 1
        }
        if (-not $part.DriveLetter) {
            $letter = Get-FreeDriveLetter
            Set-Partition -DiskNumber $disk.Number -PartitionNumber $part.PartitionNumber -NewDriveLetter $letter | Out-Null
            Start-Sleep -Seconds 1
            $part = Get-Partition -DiskNumber $disk.Number | Select-Object -First 1
        }
        $letter = $part.DriveLetter
        if (-not $letter) { throw 'Could not assign drive letter to cloud-init VHD.' }
        $root = ('{0}:\' -f $letter)
        if (-not (Test-Path $root)) { throw "Cloud-init mount path missing: $root" }
        $meta = @"
instance-id: $VmName
local-hostname: $VmName
"@
        $pubKey = Get-Content -Raw "$(Get-SmokeSshKeyPath).pub"
        $user = Get-CloudInitUserData -VmName $VmName -PubKey $pubKey -Profile $Profile -MacAddress $MacAddress
        Set-Content -Path (Join-Path $root 'meta-data') -Value $meta -NoNewline -Encoding ascii
        Set-Content -Path (Join-Path $root 'user-data') -Value $user -Encoding ascii
    }
    finally {
        Dismount-VHD -Path $OutPath
    }
}

function New-CpHyperVVm {
    param(
        [Parameter(Mandatory)][ValidateSet('fresh', 'upgrade')][string]$Profile
    )
    Import-HyperVSmokeModule
    $cfg = $Script:VmProfiles[$Profile]
    $vmName = $cfg.Name
    if (Get-VM -Name $vmName -ErrorAction SilentlyContinue) {
        throw "VM '$vmName' already exists. Run: .\up.ps1 destroy -Profile $Profile"
    }
    $template = Get-AlmaTemplateVhdxPath
    $vmDir = Join-Path $Script:CacheRoot $vmName
    New-Item -ItemType Directory -Path $vmDir -Force | Out-Null
    $disk = Join-Path $vmDir 'os.vhdx'
    Copy-Item $template $disk -Force
    $switch = Get-VMSwitch -Name 'Default Switch' -ErrorAction Stop
    $vm = New-VM -Name $vmName -MemoryStartupBytes 4GB -Generation 2 -VHDPath $disk -SwitchName $switch.Name
    $mac = Format-CpMacAddress -Mac (Get-VMNetworkAdapter -VM $vm | Select-Object -First 1 -ExpandProperty MacAddress)
    Write-Host "Guest NIC MAC: $mac"
    $ciVhd = Join-Path $vmDir 'cloud-init.vhdx'
    New-CloudInitDataVhd -VmName $vmName -OutPath $ciVhd -Profile $Profile -MacAddress $mac
    $ciIso = Join-Path $vmDir 'cloud-init.iso'
    $null = New-CloudInitSeedIso -VmName $vmName -OutIso $ciIso -Profile $Profile -MacAddress $mac
    Add-VMHardDiskDrive -VMName $vmName -Path $ciVhd | Out-Null
    Set-VMProcessor -VM $vm -Count 2 `
        -CompatibilityForMigrationEnabled $false `
        -CompatibilityForOlderOperatingSystemsEnabled $false
    Set-VMFirmware -VM $vm -EnableSecureBoot Off
    Add-VMDvdDrive -VMName $vmName | Out-Null
    Set-VMDvdDrive -VMName $vmName -Path $ciIso | Out-Null
    Set-VMMemory -VM $vm -DynamicMemoryEnabled $false
    Get-VMIntegrationService -VM $vm | ForEach-Object {
        Enable-VMIntegrationService -VM $vm -Name $_.Name -ErrorAction SilentlyContinue
    }
    Set-VMNetworkAdapter -VM $vm -DhcpGuard Off -RouterGuard Off -ErrorAction SilentlyContinue
    Write-Host "Created $vmName on Default Switch. Starting..."
    Start-VM -Name $vmName | Out-Null
    Write-Host 'Waiting 90s for guest boot and cloud-init...'
    Start-Sleep -Seconds 90
    return $vmName
}

function Test-CpGuestSshProbe {
    param(
        [Parameter(Mandatory)][string]$Ip
    )
    $key = Get-SmokeSshKeyPath
    & ssh -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ConnectTimeout=2 -o BatchMode=yes `
        "root@${Ip}" 'echo PROBE_OK' 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Discover-CpGuestIpViaProbe {
    param(
        [Parameter(Mandatory)][string]$VmName,
        [string]$Prefix = '172.20.80',
        [Parameter()][ValidateSet('fresh', 'upgrade')][string]$Profile
    )
    $ErrorActionPreference = 'Continue'
    $key = Get-SmokeSshKeyPath
    if ($Profile -and $Script:GuestStaticIps.ContainsKey($Profile)) {
        $static = $Script:GuestStaticIps[$Profile]
        if (Test-CpGuestSshProbe -Ip $static) { return $static }
    }
    $mac = (Get-VMNetworkAdapter -VMName $VmName -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty MacAddress)
    if ($mac) {
        $macNorm = ($mac -replace '-', '').ToLower()
        $arp = arp -a | Select-String $Prefix
        foreach ($line in $arp) {
            if ($line.Line -match '([0-9.]+)\s+([0-9a-f-]+)') {
                $candidate = $Matches[1]
                $lineMac = ($Matches[2] -replace '-', '').ToLower()
                if ($lineMac -eq $macNorm) { return $candidate }
            }
        }
    }
    foreach ($hostId in 2..60) {
        $candidate = "$Prefix.$hostId"
        & ssh -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ConnectTimeout=1 -o BatchMode=yes `
            "root@${candidate}" 'echo PROBE_OK' 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}

function Get-CpVmIpv4 {
    param(
        [Parameter(Mandatory)][string]$VmName,
        [Parameter()][ValidateSet('fresh', 'upgrade')][string]$Profile
    )
    Import-HyperVSmokeModule
    $ErrorActionPreference = 'Continue'
    $probeStarted = Get-Date
    $deadline = (Get-Date).AddMinutes(20)
    while ((Get-Date) -lt $deadline) {
        $ips = @()
        foreach ($adapter in @(Get-VMNetworkAdapter -VMName $VmName -ErrorAction SilentlyContinue)) {
            if ($null -eq $adapter) { continue }
            if ($adapter.PSObject.Properties.Match('IPAddresses').Count -gt 0) {
                $ips += @($adapter.IPAddresses) | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -notmatch '^169\.254\.' }
            }
        }
        if ($ips.Count -gt 0) { return $ips[0] }
        if ($Profile -and $Script:GuestStaticIps.ContainsKey($Profile)) {
            $static = $Script:GuestStaticIps[$Profile]
            if (Test-CpGuestSshProbe -Ip $static) { return $static }
        }
        if (((Get-Date) - $probeStarted).TotalSeconds -ge 30) {
            $probed = Discover-CpGuestIpViaProbe -VmName $VmName -Profile $Profile
            $probeStarted = Get-Date
            if ($probed) { return $probed }
        }
        Start-Sleep -Seconds 5
    }
    throw "No IPv4 from Default Switch for VM '$VmName' within 20 minutes."
}

function Wait-CpVmSsh {
    param(
        [Parameter(Mandatory)][string]$Ip,
        [int]$TimeoutSec = 900
    )
    $ErrorActionPreference = 'Continue'
    $key = Get-SmokeSshKeyPath
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        & ssh -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ConnectTimeout=8 -o BatchMode=yes `
            "root@${Ip}" 'cloud-init status --wait || true; grep -q avx2 /proc/cpuinfo && echo AVX2_OK || echo NO_AVX2' 2>$null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 10
    }
    throw "SSH to root@${Ip} not ready within ${TimeoutSec}s."
}

function Invoke-CpGuestScript {
    param(
        [Parameter(Mandatory)][string]$Ip,
        [Parameter(Mandatory)][string]$LocalScript,
        [int]$TimeoutSec = 7200
    )
    $key = Get-SmokeSshKeyPath
    $remote = '/tmp/cp-provision.sh'
    & scp -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL $LocalScript "root@${Ip}:${remote}"
    if ($LASTEXITCODE -ne 0) { throw 'scp to guest failed.' }
    $content = Get-Content -Raw $LocalScript
    $content = $content -replace "`r`n", "`n" -replace "`r", "`n"
    $temp = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($temp, $content)
        & scp -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL $temp "root@${Ip}:${remote}"
        if ($LASTEXITCODE -ne 0) { throw 'scp normalized script failed.' }
    }
    finally {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Running provision on guest (may take 15-40 minutes)..."
    & ssh -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL "root@${Ip}" "chmod +x ${remote}; tr -d '\r' < ${remote} | bash"
    if ($LASTEXITCODE -ne 0) { throw "Guest provision failed with exit code $LASTEXITCODE" }
}

function Invoke-CpGuestSmoke {
    param([Parameter(Mandatory)][string]$Ip)
    $key = Get-SmokeSshKeyPath
    $local = Join-Path $Script:SmokeModuleRoot 'smoke.sh'
    $remote = '/tmp/smoke.sh'
    $content = (Get-Content -Raw $local) -replace "`r`n", "`n" -replace "`r", "`n"
    $temp = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($temp, $content)
        & scp -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL $temp "root@${Ip}:${remote}"
    }
    finally {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
    }
    & ssh -i $key -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL "root@${Ip}" "tr -d '\r' < ${remote} | bash"
    if ($LASTEXITCODE -ne 0) { throw "Guest smoke failed with exit code $LASTEXITCODE" }
}

function Set-CpPanelPortProxy {
    param(
        [Parameter(Mandatory)][string]$Ip,
        [Parameter(Mandatory)][int]$HostPort
    )
    if (-not (Test-AdminRole)) { return }
    netsh interface portproxy delete v4tov4 listenport=$HostPort listenaddress=127.0.0.1 2>$null | Out-Null
    netsh interface portproxy add v4tov4 listenport=$HostPort listenaddress=127.0.0.1 connectport=8090 connectaddress=$Ip | Out-Null
    Write-Host "Panel URL: https://127.0.0.1:${HostPort}  password: $($Script:LabPassword)"
}

function Remove-CpPanelPortProxy {
    param([Parameter(Mandatory)][int]$HostPort)
    if (-not (Test-AdminRole)) { return }
    netsh interface portproxy delete v4tov4 listenport=$HostPort listenaddress=127.0.0.1 2>$null | Out-Null
}

function Stop-CpHyperVVm {
    param([Parameter(Mandatory)][ValidateSet('fresh', 'upgrade')][string]$Profile)
    Import-HyperVSmokeModule
    $name = $Script:VmProfiles[$Profile].Name
    if (Get-VM -Name $name -ErrorAction SilentlyContinue) {
        Stop-VM -Name $name -Force -TurnOff -ErrorAction SilentlyContinue
    }
}

function Remove-CpHyperVVm {
    param(
        [Parameter(Mandatory)][ValidateSet('fresh', 'upgrade', 'all')][string]$Profile
    )
    Import-HyperVSmokeModule
    $names = if ($Profile -eq 'all') { @($Script:VmProfiles['fresh'].Name, $Script:VmProfiles['upgrade'].Name) } else { @($Script:VmProfiles[$Profile].Name) }
    foreach ($name in $names) {
        Remove-CpPanelPortProxy -HostPort $Script:VmProfiles['fresh'].HostPanelPort
        Remove-CpPanelPortProxy -HostPort $Script:VmProfiles['upgrade'].HostPanelPort
        if (Get-VM -Name $name -ErrorAction SilentlyContinue) {
            Stop-VM -Name $name -Force -TurnOff -ErrorAction SilentlyContinue
            Remove-VM -Name $name -Force
        }
        $dir = Join-Path $Script:CacheRoot $name
        if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
    }
}

function Get-CpHyperVStatus {
    Import-HyperVSmokeModule
    foreach ($entry in $Script:VmProfiles.GetEnumerator()) {
        $name = $entry.Value.Name
        $vm = Get-VM -Name $name -ErrorAction SilentlyContinue
        if (-not $vm) {
            Write-Host "$name : not created"
            continue
        }
        $ip = try {
            (Get-VMNetworkAdapter -VM $vm -ErrorAction SilentlyContinue | Select-Object -ExpandProperty IPAddresses -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -notmatch '^169\.254\.' } | Select-Object -First 1)
        } catch { $null }
        Write-Host "$name : $($vm.State) ip=$ip host_panel=https://127.0.0.1:$($entry.Value.HostPanelPort)"
    }
}

Export-ModuleMember -Function *
