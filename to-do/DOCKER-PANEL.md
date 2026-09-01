# CyberPanel Docker panel image

Run the full CyberPanel control panel inside Docker with **full** or **minimal** install modes, on multiple OS base images published as `master3395/cyberpanel:<os-tag>`.

## Requirements

- Docker 20.10+ with `cgroupns=host` support
- `--privileged` (systemd, firewalld, nested Docker CE)
- AlmaLinux 10 tag: host CPU with **AVX2** / x86-64-v3
- First-boot secrets via environment variables only (never bake into images)

## Install modes

| Mode | Environment |
|------|-------------|
| Full (default) | `CYBERPANEL_MINIMAL=0` or `CYBERPANEL_FULL_INSTALL=1` |
| Minimal | `CYBERPANEL_MINIMAL=1` (skips PowerDNS, Postfix, Pure-FTPd) |
| Partial | `CYBERPANEL_MINIMAL=1` plus `CYBERPANEL_ENABLE_POWERDNS=1`, `CYBERPANEL_ENABLE_POSTFIX=1`, or `CYBERPANEL_ENABLE_PUREFTPD=1` |

Mode is fixed at **first boot** (`/etc/cyberpanel/.docker-initialized`). To change mode, remove volumes and recreate the container.

## Quick start (full stack)

```bash
cd docker/panel
export CYBERPANEL_ADMIN_PASSWORD='YourSecurePass12'
export CYBERPANEL_HOSTNAME='panel.example.com'
docker compose up -d
```

Panel: `https://localhost:8090`

## Minimal

```bash
cd docker/panel
export CYBERPANEL_ADMIN_PASSWORD='YourSecurePass12'
export CYBERPANEL_MINIMAL=1
docker compose -f docker-compose.minimal.yml up -d
```

## OS tags (Docker Hub)

**Recommended (lowest CVE baseline):** `almalinux10` / `latest`, `openeuler2203`, `ubuntu2404`, `debian13`

**Legacy (higher CVE backlog):** `debian11`, `rockylinux8`, `almalinux8`, `openeuler2003`, `rockylinux9`

All tags: `almalinux8`, `almalinux9`, `almalinux10`, `rockylinux8`, `rockylinux9`, `centos-stream9`, `ubuntu2204`, `ubuntu2404`, `debian11`, `debian12`, `debian13`, `openeuler2003`, `openeuler2203`, `rhel8`, `rhel9`.

Build all locally:

```powershell
cd docker/panel
.\build-matrix.ps1 -Os all
```

Publish (after `docker login -u master3395`):

```powershell
.\publish.ps1 -Os all
```

## Security hardening (image build)

The panel Dockerfile:

- Installs bootstrap packages without `openssh-server` (installer adds SSH when needed)
- Runs `dnf/yum update` or `apt upgrade` during build so Hub Scout/Trivy see patched OS layers
- Supports optional base digest pins in [`os-matrix.json`](../docker/panel/os-matrix.json)

Refresh base digests before a release rebuild:

```powershell
cd docker/panel
.\refresh-base-digests.ps1
```

```bash
cd docker/panel
bash refresh-base-digests.sh
```

CI (`.github/workflows/docker-panel.yml`) scans every built tag with Trivy:

- **Fail** on any **fixable Critical** CVE (patched upstream but not in the image)
- **Fail** on **fixable High > 25** for recommended tags (`almalinux10`, `ubuntu2404`, `debian13`, `openeuler2203`)
- **Warn** on unfixed critical/high (no distro patch yet)
- Rebuilds weekly (Monday 04:00 UTC) to pick up distro patches

See [`DOCKER-PANEL-SECURITY.md`](DOCKER-PANEL-SECURITY.md) for Scout baseline, post-rebuild Trivy counts per tag, and residual risk. When checking Docker Hub, use the **Tags** page for the tag you deploy; the repo **General** tab aggregates all tags and legacy digests.

## Smoke tests (Windows)

```powershell
cd Test/docker
.\up.ps1 build -Os almalinux10
.\up.ps1 up -Os almalinux10 -Mode full
.\up.ps1 smoke-full
.\up.ps1 up -Os almalinux10 -Mode minimal
.\up.ps1 smoke-minimal
```

## Ports (full mode)

| Port | Service |
|------|---------|
| 8090 | CyberPanel |
| 80, 443 | Websites |
| 7080 | OpenLiteSpeed admin |
| 53 | PowerDNS |
| 21, 40100-40200 | Pure-FTPd |
| 25, 587, 465, 993, 995 | Mail |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CYBERPANEL_ADMIN_PASSWORD` | random | Admin password (required for production) |
| `CYBERPANEL_ADMIN_USER` | `admin` | Admin username |
| `CYBERPANEL_HOSTNAME` | `cyberpanel.local` | Container hostname |
| `CYBERPANEL_BRANCH` | `v3.0.4-dev` | Git branch for first-boot install |
| `CYBERPANEL_REPO` | `master3395` | GitHub user/org for installer clone |
| `CYBERPANEL_MINIMAL` | `0` | Minimal install mode |
| `CYBERPANEL_PUBLIC_IP` | `127.0.0.1` | Public IP passed to installer |

## CI publish

Push to `v3.0.4-dev` triggers `.github/workflows/docker-panel.yml` when `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set on the fork.
