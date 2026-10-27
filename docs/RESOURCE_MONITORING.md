# Website resource measurements (#1588)

The website overview measures `/home/<domain>/public_html`, rather than treating the Unix account name as a domain. CPU is a short sample of that account's processes, normalized to the host's logical CPU capacity. RAM is the sum of their resident memory (RSS), as a percentage of host RAM; shared pages may be counted more than once. These are account measurements, not a per-PHP-request profiler or cgroup/quota consumption. Disk is allocated document-root space as a percentage of filesystem capacity, not the package's disk allowance.

CPU limits returned by `lscgctl` are percentages of one core: `200` displays as `2 cores (200%)`. Explicit unlimited limits are labeled; missing or invalid values are unavailable. Displaying a configured limit does not prove that the kernel is enforcing it. Package limits and observed system settings can differ. No editing rights or paid entitlements change.

The disk commands each have a five-second timeout. Errors are unavailable instead of fabricated zero values. The browser allows one pending request per page, waits five seconds after completion before polling again, pauses while hidden, and stops when the page exits. This prevents overlapping polls from one page; it is not server-wide caching or a diagnosis of the reporter's intermittent CPU spikes.

Validation:

- `python -m unittest websiteFunctions.test_resource_monitoring`: domain path, safe execution, failures, process sampling, CPU units, unlimited/invalid limits.
- `node websiteFunctions/test_resource_monitoring.js`: real asset lifecycle, timeout, hidden/exited page, error/finite values and bounded charts; checks all three shipped copies agree.
- Owned Ubuntu 24.04.5 x86_64 CyberPanel runtime, Python 3.12.3/Django 4.2.14: a real Unix account with a 2 MiB document-root fixture and a short 64 MiB CPU process reproduced the original zero-disk bug and verified corrected CPU/RAM/disk values. Actual ORM/ACL checks allowed its owner and denied another user before sampling. All created accounts, files, rows and processes were removed.
- Native Django rendered the changed resource fragment. Headless Chromium used that fragment, real jQuery/Chart.js and production polling code against controlled local HTTP responses. A 6.2-second response did not overlap, unavailable data was not plotted as zero, the next poll recovered, and page exit stopped polling. This is component acceptance, not deployment of the whole candidate panel.

No namespace or cgroup settings were changed by this fix. The broader namespace-management request (#1955) remains separate. Its server/site controls, namespace checks, activation/rollback and upgrade checks are not implemented here.
