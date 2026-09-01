# Docker / Hyper-V evidence (#1912)

Generated on live fork branch `pr/docker-hyperv-tooling` rebased on `v3.0.5-dev`.

## Commands to reproduce

```bash
cd /home/Github/cyberPanel-repos/cyberpanel
bash Test/docker/smoke-minimal.sh
bash Test/docker/smoke.sh
# Hyper-V (Windows host):
# pwsh Test/hyperv/Run-HyperV-Smoke.ps1
```

## Policy

- Base images pinned in `.github/workflows/docker-panel.yml`
- PRs from forks cannot publish images (workflow_dispatch on fork only)
- Trivy scan step included in workflow

## Live server note

Smoke scripts validated on AlmaLinux 9 CyberPanel host; full image build requires Docker daemon.
