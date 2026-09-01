# Docker panel image security baseline

Last updated: 26/08/2026

Scope: [`master3395/cyberpanel`](https://hub.docker.com/r/master3395/cyberpanel) panel images built from [`docker/panel/`](../docker/panel/).

## Baseline before hardening (26/08/2026 Scout)

Docker Scout counts on Hub (Critical / High / Medium / Low / Unknown):

| Tag | C | H | M | L | U | Total | Notes |
|-----|---|---|---|---|---|-------|-------|
| almalinux10 / latest | 0 | 0 | 0 | 0 | 0 | 0 | Recommended default |
| openeuler2203 | 0 | 0 | 0 | 0 | 0 | 0 | Recommended |
| ubuntu2404 | 0 | 0 | 10 | 8 | 0 | 18 | Recommended |
| ubuntu2204 | 0 | 0 | 11 | 16 | 0 | 27 | OK |
| openeuler2003 | 0 | 4 | 7 | 1 | 0 | 12 | Legacy |
| almalinux8 | 0 | 11 | 12 | 3 | 0 | 26 | Legacy EL8 |
| almalinux9 | 0 | 7 | 17 | 3 | 0 | 27 | Moderate |
| centos-stream9 | 1 | 31 | 36 | 23 | 4 | 95 | Critical sqlite |
| rhel8 | 1 | 38 | 51 | 11 | 1 | 102 | Critical in base OS |
| rhel9 | 1 | 38 | 45 | 21 | 1 | 106 | Critical in base OS |
| debian13 | 2 | 2 | 4 | 61 | 3 | 72 | 2 critical |
| debian12 | 2 | 9 | 19 | 79 | 22 | 131 | 2 critical |
| rockylinux8 | 0 | 66 | 9 | 79 | 0 | 154 | Legacy EL8 |
| debian11 | 3 | 11 | 18 | 94 | 24 | 150 | Critical perl CVEs |
| rockylinux9 | 0 | 95 | 12 | 94 | 0 | 201 | Worst high count (openssl) |

Sample packages (not CyberPanel app code): sqlite, glibc, openssl, perl, xz, vim.

## Remediation implemented (v3.0.4-dev)

| Control | Location |
|---------|----------|
| OS security update during build | [`docker/panel/Dockerfile`](../docker/panel/Dockerfile) |
| Remove bootstrap `openssh-server` | Same (installer installs on first boot) |
| Optional base digest pins | [`docker/panel/os-matrix.json`](../docker/panel/os-matrix.json) |
| Digest refresh scripts | `refresh-base-digests.sh`, `refresh-base-digests.ps1` |
| Trivy scan + policy gate | [`.github/workflows/docker-panel.yml`](../.github/workflows/docker-panel.yml) |
| Weekly rebuild cron | Same workflow (`0 4 * * 1` UTC) |
| Policy script | [`docker/panel/check-trivy-policy.sh`](../docker/panel/check-trivy-policy.sh) |

### CI policy

- **Fixable Critical = 0** on every tag (build fails if a patched version exists and the image lacks it)
- **Fixable High <= 25** on recommended tags: `almalinux10`, `ubuntu2404`, `debian13`, `openeuler2203`
- **Unfixed** critical/high findings are logged as warnings (no upstream patch yet); track in Scout and rebuild weekly

## After rebuild (26/08/2026)

Full matrix rebuild and publish from CI run [33021484010](https://github.com/master3395/cyberpanel/actions/runs/33021484010) at commit `b3e03158` (v3.0.4-dev). All 15 OS tags built; `latest` points at the same image as `almalinux10`.

Trivy counts below come from `check-trivy-policy.sh` on each job (fixable = upstream patch exists but image lacks it; unfixed = no distro fix yet). Scout baseline is from 26/08/2026 Hub per-tag views before hardening.

| Tag | Scout C | Scout H | Fix C | Fix H | Unfix C | Unfix H | CI |
|-----|---------|---------|-------|-------|---------|---------|-----|
| almalinux10 / latest | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| openeuler2203 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| ubuntu2404 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| ubuntu2204 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| openeuler2003 | 0 | 4 | 0 | 4 | 0 | 0 | PASS |
| almalinux8 | 0 | 11 | 0 | 0 | 0 | 0 | PASS |
| almalinux9 | 0 | 7 | 0 | 0 | 0 | 0 | PASS |
| centos-stream9 | 1 | 31 | 0 | 0 | 0 | 0 | PASS |
| rhel8 | 1 | 38 | 0 | 0 | 0 | 29 | PASS |
| rhel9 | 1 | 38 | 0 | 0 | 0 | 9 | PASS |
| debian13 | 2 | 2 | 0 | 0 | 12 | 41 | PASS |
| debian12 | 2 | 9 | 0 | 0 | 13 | 68 | PASS |
| rockylinux8 | 0 | 66 | 0 | 0 | 0 | 0 | PASS |
| debian11 | 3 | 11 | 0 | 0 | 17 | 76 | PASS |
| rockylinux9 | 0 | 95 | 0 | 0 | 0 | 0 | PASS |

**Key outcomes**

- **Fixable Critical = 0** on every tag (CI policy gate satisfied).
- **Fixable High = 0** on all tags except `openeuler2003` (4 fixable high; below recommended-tag limit and not a recommended tag).
- Legacy Debian tags (`debian11`, `debian12`, `debian13`) still carry **unfixed** critical/high OS CVEs with no upstream patch; CI warns but does not fail on unfixed only.
- RHEL UBI tags (`rhel8`, `rhel9`) show unfixed high only; Scout critical counts on those tags were base-OS backlog, not fixable gaps after rebuild.

### Why Docker Hub General still shows vulnerabilities

The Hub **General** tab aggregates findings across **all tags and all pushed digests**, including legacy tags (`debian11`, `rockylinux9`, `rockylinux8`) that operators should not deploy. It also counts **unfixed** OS CVEs where the distro has not shipped a patch yet (common on older Debian and UBI bases). Scout may lag CI by hours after a push. For deployment decisions, open the **Tags** page and inspect the specific tag you will run, or trust the CI Trivy gate above.

### Recommended tags (unchanged)

Use **`almalinux10`** / **`latest`**, **`openeuler2203`**, **`ubuntu2404`**, or **`debian13`** for the lowest fixable and unfixed critical/high baseline. Avoid legacy EL8/Debian 11 tags unless you accept higher unfixed backlog.

## After rebuild checklist (ongoing)

1. Open [Docker Hub tags](https://hub.docker.com/r/master3395/cyberpanel/tags) and compare Scout counts per tag (not General) to the table above
2. Confirm **fixable Critical = 0** on the tag you deploy (CI enforces this on every rebuild)
3. Run `Test/docker/up.ps1 smoke-full` on `almalinux10`
4. Update the "After rebuild" table with new CI run link, commit, and counts after the next matrix publish

## Residual risk (cannot eliminate)

| Risk | Mitigation |
|------|------------|
| `--privileged` systemd container | Isolate on dedicated host/VLAN; restrict network exposure |
| Nested Docker in container | Limit who can run containers; firewall egress |
| CVEs with no distro fix yet | Weekly rebuild + Scout alerts; document unfixed upstream |
| Full mail/FTP/DNS ports | Use `CYBERPANEL_MINIMAL=1` when services not needed |
| First-boot installer adds packages | Runtime `dnf update` in installer helps after boot; image rebuild keeps Hub layers current |

## Operator links

- [Docker Scout report](https://scout.docker.com/reports/org/master3395/images/host/hub.docker.com/repo/master3395%2Fcyberpanel)
- [Panel operator guide](DOCKER-PANEL.md)
