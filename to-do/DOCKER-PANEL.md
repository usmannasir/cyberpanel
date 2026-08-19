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

`almalinux8`, `almalinux9`, `almalinux10` (also `latest`), `rockylinux8`, `rockylinux9`, `centos-stream9`, `ubuntu2204`, `ubuntu2404`, `debian11`, `debian12`, `debian13`, `openeuler2003`, `openeuler2203`, `rhel8`, `rhel9`.

Build all locally:

```powershell
cd docker/panel
.\build-matrix.ps1 -Os all
```

Publish (after `docker login -u master3395`):

```powershell
.\publish.ps1 -Os all
```

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

## Volumes

- `cyberpanel_home` → `/home`
- `cyberpanel_mysql` → `/var/lib/mysql`
- `cyberpanel_etc` → `/etc/cyberpanel`
- `cyberpanel_docker` → `/var/lib/docker`
- `cyberpanel_mail` → `/var/mail` (full mail mode)

## Container contract files

- [`docker/panel/Dockerfile`](../docker/panel/Dockerfile)
- [`install/container.py`](../install/container.py)
- [`install/install_utils.py`](../install/install_utils.py) (`is_container_runtime`, env mode resolver)

## Docker Hub publish

Images publish as **`master3395/cyberpanel:<os-tag>`** (`latest` = `almalinux10`). Mode (full/minimal) is runtime env on first boot, not a separate image tag.

### GitHub Actions (recommended)

1. Add repository secrets on `master3395/cyberpanel`:
   - `DOCKERHUB_USERNAME` = `master3395`
   - `DOCKERHUB_TOKEN` = Docker Hub access token (read/write on `cyberpanel` repo)
2. Push to `v3.0.2-dev` or run workflow **Docker panel image** manually (`.github/workflows/docker-panel.yml`).
3. Workflow builds all tags in `docker/panel/os-matrix.json` when login succeeds; without secrets it still validates Dockerfiles (build only).

### Local publish

```powershell
docker login -u master3395
cd docker\panel
.\build-matrix.ps1 -Os almalinux10
.\publish.ps1 -Os almalinux10
.\publish.ps1 -Os all
```

Requires Docker Desktop or Docker Engine on the host. CI matrix covers 15 OS tags (AlmaLinux, Rocky, CentOS Stream, RHEL UBI, Ubuntu, Debian, openEuler).
