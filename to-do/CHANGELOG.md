# Changelog

## [Unreleased] - 31/05/2026

### Fixed
- **SSL with Cloudflare:** List badge uses live TLS when origin PEM is expired; Issue SSL tries `acme.sh --dns dns_cf` for active CF zones (`plogical/ssl_cloudflare_dns.py`).
- **Dashboard `getSystemStatus` 503:** Admin stats cached 45s; non-blocking CPU sampling; home poll 60s.
- **Manage Applications hang:** Skip cold DNF on HTML load; versions via `applicationMeta` on demand.
- **Site workspace:** `/websites/<domain>/workspace` uses lightweight `loadSiteWorkspace` + `siteWorkspace.html`.
- **Cloudflare DNS empty table:** Sync `filteredRecords` with `records`; search filter; higher API page size.
- **List Websites disk display:** `format_size_from_mb()` (KB, MB, GB, TB with readable units).
- **SSL list badge:** `exsysUser` corrected to `externalApp` for resource limits lookup.

## [Unreleased] - 31/05/2026

### Fixed
- **Dashboard `GET /base/getSystemStatus` 503:** Cache admin system stats for 45s, cache non-admin stats for 300s (avoids repeated `du` per site). Use non-blocking `psutil.cpu_percent(interval=None)` and single disk stat read. Home page widget poll interval reduced from 2s to 60s to stop WSGI worker exhaustion (`ExtConn timed out`).
# Changelog
