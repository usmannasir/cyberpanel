# VirtualBox smoke (Cursor Local on Windows)

Full step-by-step (prereqs, clone, Cursor prompt, troubleshooting): `to-do/WINDOWS-CURSOR-SMOKE-PLAN.md`. Cursor plan copy: `.cursor/plans/windows-cursor-vbox-smoke.plan.md`.

AlmaLinux VPS cannot run these VMs. Clone master3395/cyberpanel, open it in Cursor on Windows, then run from `Test/virtualbox`.

## Host needs

- VirtualBox 7.x plus Extension Pack
- Vagrant
- Git for Windows
- About 4 GB RAM per VM. Run **one VM at a time**.

## Commands

```powershell
cd Test\virtualbox
.\up.ps1 fresh
.\up.ps1 smoke-fresh
.\up.ps1 halt

.\up.ps1 upgrade
.\up.ps1 smoke-upgrade
.\up.ps1 destroy
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
