# LSCPD selection and large phpMyAdmin exports

## Problem

The installer and upgrader selected the bundled `lscpd-0.3.1` on x86_64
Enterprise Linux regardless of libc compatibility. That binary can end a large
phpMyAdmin SQL response early while returning HTTP 200. A successful HTTP status
alone does not establish that a downloaded SQL backup is complete.

## Change

Both paths now call `lscpd_binary.select_lscpd_binary()`. The host libc reports
its own version through `CS_GNU_LIBC_VERSION`, with a glibc-only fallback to
`platform.libc_ver()`. On x86_64/amd64 with glibc 2.25 or later, select the bundled
0.4.0 executable. ARM64 retains its architecture-specific executable. Unknown
architectures fail before the previous executable is removed.

The 0.4.0 ELF requires GLIBC_2.25. Tests inspect the actual bundled ELF version
requirements as well as the installer/upgrader wiring, protecting against a
future bundled executable silently exceeding the selection floor. Both old and
new x86 executables require `libcrypt.so.1`.

## Compatibility limit

CentOS 7 uses glibc 2.17. It must retain 0.3.1; blindly installing 0.4.0 there
would break the panel executable. **This change does not fix large-export
truncation on CentOS 7 or other hosts below the new executable's ABI floor.**
An ABI-compatible replacement build or migration to a supported modern OS is
needed for that case. Unknown libc versions retain the legacy executable.

## Verification on 20 October 2026

An isolated, company-owned AlmaLinux 10.2 x86_64 VM (glibc 2.39) ran a targeted
LSCPD / LiteSpeed PHP / MariaDB / phpMyAdmin 5.2.1 stack. The service listened on
loopback only. HTTPS checks trusted a generated QA certificate. This was not a
full CyberPanel installer or full upgrade acceptance test.

The database fixture contained 1,024 rows with 49,152 deterministic text bytes
per row (50,331,648 payload bytes). Both binaries served the same actual
phpMyAdmin SQL export over HTTPS:

| Executable | Download bytes | HTTP | SQL COMMIT footer |
| --- | ---: | --- | --- |
| 0.3.1 | 31,545,213 | 200 | Missing |
| 0.4.0 | 50,393,127 | 200 | Present |

The complete export imported into a separate database: 1,024 rows,
50,331,648 payload bytes, and every row's SHA-256 matched the source. The legacy
file failed import because it was truncated. Test database names and content
were generated solely for QA; no customer databases were accessed.

Source verification: eight selector/wiring/ELF tests passed. Installer discovery
passed 142 tests with five existing opt-in skips (`-s install -t .`).

## Diagnosing a reported export

Record the OS, glibc version, running LSCPD version, HTTP response size, and
whether the SQL file completes. Restore the export into a separate disposable
database and compare row counts and checksums. Keep existing backups until
restoration passes; a 200 response or a file appearing in Downloads is not
sufficient evidence.
