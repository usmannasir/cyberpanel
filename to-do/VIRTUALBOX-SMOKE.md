# VirtualBox smoke (Cursor Local on Windows)

Full step-by-step (prereqs, clone, Cursor prompt, troubleshooting): `to-do/WINDOWS-CURSOR-SMOKE-PLAN.md`. Cursor plan copy: `.cursor/plans/windows-cursor-vbox-smoke.plan.md`.

AlmaLinux VPS cannot run these VMs. Clone master3395/cyberpanel, open it in Cursor on Windows, then run from `Test/virtualbox`.

## Host needs

- VirtualBox 7.x plus Extension Pack
- Vagrant
- Git for Windows
- About 4 GB RAM per VM. Run **one VM at a time**.

Default box is AlmaLinux 9 (`almalinux/9`). AlmaLinux 10 uses `-Os 10` (`almalinux/10`). Run one OS at a time. Destroy the other OS VMs first so the 4 GB RAM budget is free.

AlmaLinux 10 and LiteSpeed `lsphp*.el10.x86_64` need x86-64-v3 (AVX2). On Windows, VirtualBox often runs under the Hypervisor (NEM, `unrestricted guest: no`) and masks AVX2. Then `almalinux/10` dies at `/init` with `CPU does not support x86-64-v3`. The v2 box (`almalinux/10-x86_64_v2`) boots, but `lsphp85` then fails with `CPU ISA level is lower than required`, so it is not a full panel smoke. Run AlmaLinux 10 smokes on KVM, a VPS, or VirtualBox with hardware VT-x (Hyper-V / Memory Integrity off).

## Commands

```powershell
cd Test\virtualbox
.\up.ps1 fresh
.\up.ps1 smoke-fresh
.\up.ps1 halt

.\up.ps1 upgrade
.\up.ps1 smoke-upgrade
.\up.ps1 destroy

# AlmaLinux 10 (same pass bar)
.\up.ps1 destroy
.\up.ps1 fresh -Os 10
.\up.ps1 smoke-fresh -Os 10
.\up.ps1 halt
.\up.ps1 upgrade -Os 10
.\up.ps1 smoke-upgrade -Os 10
```

- Fresh panel: `https://127.0.0.1:18090`
- Upgrade panel: `https://127.0.0.1:28090`
- Lab password: `TestPass12`

Fresh install uses `cyberpanel.sh -v ols -b 3.0.2-dev --repo master3395`.
Upgrade installs stock `usmannasir` `v3.0.2`, then `cyberpanel_upgrade.sh -b v3.0.2-dev --repo master3395`.

## Pass bar

- Provisioner exit 0
- `lscpd` active
- HTTPS `:8090` answers
- `getPHPString('PHP 8.10')` is `810`
