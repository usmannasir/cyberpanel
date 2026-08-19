# Hyper-V smoke (AlmaLinux 10, Cursor Local on Windows)

Use this when **Hyper-V stays enabled** and VirtualBox nested mode masks AVX2. Hyper-V runs AlmaLinux 10 as a **first-level** Gen2 VM, so the guest should see **AVX2** (required for LiteSpeed `lsphp*.el10`).

VirtualBox harness: `Test/virtualbox/` and `to-do/VIRTUALBOX-SMOKE.md`.

## Host needs

- Windows 10/11 **Pro, Enterprise, or Education** (Hyper-V client)
- **Administrator** PowerShell for `Install-HyperV.ps1`, `up.ps1 fresh`, and port forwarding
- OpenSSH client (`ssh`, `scp`) on PATH (Windows optional feature)
- **WSL** with `genisoimage` for cloud-init seed ISO (`wsl -u root dnf install -y genisoimage`)
- About **4 GB RAM** per VM; run **one VM at a time**
- Cache under `%LOCALAPPDATA%\CyberPanelHyperVSmoke` (not OneDrive)

## One-time: enable Hyper-V

Elevated PowerShell:

```powershell
cd Test\hyperv
.\Install-HyperV.ps1
```

Reboot when Windows asks. After reboot, confirm the Hyper-V module loads:

```powershell
Get-Module Hyper-V -ListAvailable
Get-VMSwitch
```

You should see **Default Switch** (NAT). If missing, open Hyper-V Manager once or run:

```powershell
Get-VMSwitch -Name 'Default Switch'
```

## Commands (mirror VirtualBox smoke)

```powershell
cd Test\hyperv

# Optional: download AlmaLinux cloud image + convert to VHDX only (~550 MB)
.\up.ps1 bootstrap

# Fresh install (15-40 minutes)
.\up.ps1 fresh
.\up.ps1 smoke-fresh

.\up.ps1 halt -Profile fresh

# Upgrade path (30-60 minutes; run after fresh is destroyed or use separate VM)
.\up.ps1 upgrade
.\up.ps1 smoke-upgrade

.\up.ps1 status
.\up.ps1 destroy -Profile all
```

| VM | Name | Panel URL (after portproxy) |
|----|------|-----------------------------|
| Fresh | `cp-fresh-hv` | https://127.0.0.1:18090 |
| Upgrade | `cp-upgrade-hv` | https://127.0.0.1:28090 |

Lab password: `TestPass12`

Fresh install uses `cyberpanel.sh -v ols -b 3.0.2-dev --repo master3395`.
Upgrade installs stock `usmannasir` v3.0.2, then `cyberpanel_upgrade.sh -b v3.0.2-dev --repo master3395`.

## Pass bar

Same as VirtualBox:

- Provisioner exit 0
- `lscpd` active
- HTTPS `:8090` answers
- `getPHPString('PHP 8.10') == '810'`
- Guest prints `SMOKE_OK`

Early check during SSH wait: script prints `AVX2_OK` when `/proc/cpuinfo` contains `avx2`.

Guest static IPs on Default Switch NAT: `172.20.80.50` (fresh), `172.20.80.51` (upgrade). Cloud-init matches Hyper-V NIC via `driver: hv_netvsc`. Seed ISO must expose files named exactly `meta-data` and `user-data` (genisoimage `-graft-points`).

## How it works

1. Downloads AlmaLinux 10 **Generic Cloud** qcow2 from repo.almalinux.org
2. Converts to VHDX with portable **qemu-img** (cached under `%LOCALAPPDATA%`)
3. Creates Gen2 VM on **Default Switch**, **Secure Boot off**, **processor compatibility off**
4. Attaches a small **CIDATA** FAT disk (cloud-init user-data + meta-data)
5. SSH as `root` and runs the same provision/smoke bash scripts as VirtualBox

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Hyper-V PowerShell module is not installed` | Run `Install-HyperV.ps1` as admin, reboot |
| `Default Switch` missing | Hyper-V Manager > Virtual Switch Manager, or repair Hyper-V feature |
| SSH timeout | `Get-VMNetworkAdapter -VMName cp-fresh-hv` and wait for DHCP IP |
| `NO_AVX2` in guest | VM Settings > Processor: disable compatibility mode; confirm Gen2 |
| `lsphp85` ISA error | Same as VirtualBox v2 box: wrong image or CPU profile; use **x86_64** cloud image, not v2 |
| Portproxy panel dead | Re-run smoke or `.\up.ps1 status`; guest IP may have changed after reboot |

## vs VirtualBox on Hyper-V hosts

| | VirtualBox (NEM) | Hyper-V native |
|--|------------------|----------------|
| Hyper-V on host | Yes | Yes |
| Guest AVX2 for EL10 | Often **no** | Usually **yes** |
| Vagrant box | `almalinux/10` | Generic Cloud + cloud-init |

Do **not** use the AlmaLinux **x86_64_v2** cloud image for full panel smoke; LiteSpeed el10 PHP still needs v3.
