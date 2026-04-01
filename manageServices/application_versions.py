import os
import platform
import re
import subprocess
import threading
import time

from manageServices.application_detection import (
    is_debian_family,
    package_name_for_app,
    rhel_major_from_os_release,
)

# applicationMeta can call get_available_versions many times per request (ES 7/8/9, RMQ 3/4).
# Concurrent DNF from every WSGI worker exhausts lscpd and returns HTTP 503. Cache + serialize cold fetches.
_VERSION_CACHE = {}
_VERSION_CACHE_LOCK = threading.Lock()
_DNF_COLD_FETCH_LOCK = threading.Lock()

# Seconds; override with CYBERCP_MANAGED_APPS_VERSION_CACHE_TTL if needed
_CACHE_TTL_SEC = int(os.environ.get('CYBERCP_MANAGED_APPS_VERSION_CACHE_TTL', '300'))


def _version_cache_key(app_name, es_major, rabbitmq_stream):
    debian = is_debian_family()
    if app_name == 'Elasticsearch':
        em = normalize_elasticsearch_major(es_major)
    else:
        em = ''
    rs = ''
    if app_name == 'RabbitMQ':
        from manageServices.application_rabbitmq_repo import normalize_rabbitmq_stream
        rs = normalize_rabbitmq_stream(rabbitmq_stream)
    return (str(app_name), em, rs, debian)


def _cache_get_versions(key):
    now = time.monotonic()
    with _VERSION_CACHE_LOCK:
        entry = _VERSION_CACHE.get(key)
        if not entry:
            return None
        ts, versions = entry
        if (now - ts) >= _CACHE_TTL_SEC:
            try:
                del _VERSION_CACHE[key]
            except KeyError:
                pass
            return None
        # Never use a poisoned empty cache (DNF timeout / lock) as a hit.
        if not versions:
            try:
                del _VERSION_CACHE[key]
            except KeyError:
                pass
            return None
        return list(versions)


def _cache_put_versions(key, versions):
    snap = list(versions or [])
    if not snap:
        return
    with _VERSION_CACHE_LOCK:
        _VERSION_CACHE[key] = (time.monotonic(), snap)

# User-writable DNF snippet dir (panel runs as user `cyberpanel`; cannot rely on /etc).
_CYBERPANEL_DNF_EXTRA = '/home/cyberpanel/.cyberpanel-dnf/repos.d'


def _version_tuple(ver):
    """Numeric tuple for semver-style compare; empty if not usable."""
    if ver is None:
        return ()
    s = str(ver).strip()
    if not s or s.lower() == 'latest':
        return ()
    parts = []
    for x in re.findall(r'\d+', s):
        try:
            parts.append(int(x))
        except ValueError:
            break
    return tuple(parts)


def version_compare(a, b):
    """
    Compare two version strings: return -1 if a < b, 0 if equal or incomparable, 1 if a > b.
    """
    ta = _version_tuple(a)
    tb = _version_tuple(b)
    if not ta or not tb:
        return 0
    length = max(len(ta), len(tb))
    for i in range(length):
        x = ta[i] if i < len(ta) else 0
        y = tb[i] if i < len(tb) else 0
        if x < y:
            return -1
        if x > y:
            return 1
    return 0


def _max_version_string(candidates):
    best = ''
    for v in candidates or []:
        if not v:
            continue
        if not best or version_compare(best, v) < 0:
            best = v
    return best


def _run(cmd, timeout=120):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, (res.stdout or ''), (res.stderr or '')
    except Exception as err:
        return 1, '', str(err)


def normalize_elasticsearch_major(es_major):
    """Supported Elasticsearch package streams (official artifacts.elastic.co)."""
    m = str(es_major).strip()
    if m in ('7', '8', '9'):
        return m
    return '8'


def _ensure_cyberpanel_es_repo(es_major):
    """Elasticsearch official repo for version discovery (no root; gpg off for repoquery-only)."""
    major = normalize_elasticsearch_major(es_major)
    try:
        os.makedirs(_CYBERPANEL_DNF_EXTRA, mode=0o755, exist_ok=True)
    except Exception:
        return
    path = os.path.join(
        _CYBERPANEL_DNF_EXTRA, 'cyberpanel-elasticsearch-{0}.repo'.format(major)
    )
    content = (
        '[cyberpanel-elasticsearch-{0}]\n'
        'name=Elasticsearch {0}.x metadata (CyberPanel)\n'
        'baseurl=https://artifacts.elastic.co/packages/{0}.x/yum\n'
        'gpgcheck=0\n'
        'repo_gpgcheck=0\n'
        'enabled=1\n'
    ).format(major)
    try:
        with open(path, 'w') as handle:
            handle.write(content)
        os.chmod(path, 0o644)
    except Exception:
        pass


def _normalize_versions(raw_versions, max_items=25):
    versions = []
    seen = set()
    for item in raw_versions:
        value = (item or '').strip()
        if not value or value in seen:
            continue
        seen.add(value)
        versions.append(value)
    return versions[:max_items]


def _sort_versions_desc(candidates):
    def key_fn(ver):
        nums = [int(x) for x in re.findall(r'\d+', ver) if x.isdigit()]
        return nums or [0]

    try:
        return sorted(set(candidates), key=key_fn, reverse=True)
    except Exception:
        return sorted(set(candidates), reverse=True)


def _dnf_reposdir_flag(use_cyberpanel_extra):
    if not use_cyberpanel_extra:
        return []
    if not os.path.isdir(_CYBERPANEL_DNF_EXTRA):
        try:
            os.makedirs(_CYBERPANEL_DNF_EXTRA, mode=0o755, exist_ok=True)
        except Exception:
            return []
    return ['--setopt=reposdir=/etc/yum.repos.d,{0}'.format(_CYBERPANEL_DNF_EXTRA)]


def _rhel_repoquery_versions(
    pkg_name,
    use_cyberpanel_extra_repos=False,
    enablerepos=None,
    latest_limit=50,
    normalize_max=25,
):
    """
    Resolve distinct %{version} strings from enabled repos.
    RPM NEVRA text parsing is brittle (el9_7 etc.); repoquery --qf is reliable.

    For RabbitMQ, pass latest_limit=None (no cap — el8-tagged RPMs may share metadata
    with EL9) and normalize_max=200 so stream filtering (3.x vs 4.x) is not fed only
    the newest majors (which would hide the other line entirely).
    """
    dnf_cmd = (
        ['dnf']
        + _dnf_reposdir_flag(use_cyberpanel_extra_repos)
        + [
            'repoquery',
            '--available',
            '--show-duplicates',
        ]
    )
    if latest_limit is not None:
        dnf_cmd.append('--latest-limit={0}'.format(int(latest_limit)))
    dnf_cmd.extend(['--qf', '%{version}', pkg_name])
    if enablerepos:
        for repo_id in enablerepos:
            dnf_cmd.extend(['--enablerepo', repo_id])
    rc, out, err = _run(dnf_cmd, timeout=240)
    raw = []
    if rc == 0 and out.strip():
        for line in out.splitlines():
            v = (line or '').strip()
            if v and re.match(r'^[0-9]', v):
                raw.append(v)
    if raw:
        return _normalize_versions(_sort_versions_desc(raw), max_items=normalize_max)

    # Legacy systems / fallback
    yum_cmd = ['yum', 'repoquery', '--available', '--show-duplicates']
    if latest_limit is not None:
        yum_cmd.append('--latest-limit={0}'.format(int(latest_limit)))
    yum_cmd.extend(['--qf', '%{version}', pkg_name])
    rc2, out2, _ = _run(yum_cmd, timeout=120)
    raw2 = []
    if rc2 == 0 and out2.strip():
        for line in out2.splitlines():
            v = (line or '').strip()
            if v and re.match(r'^[0-9]', v):
                raw2.append(v)
    if raw2:
        return _normalize_versions(_sort_versions_desc(raw2), max_items=normalize_max)

    # Oldest fallback: yum list
    rc3, out3, _ = _run(['yum', '--showduplicates', 'list', pkg_name], timeout=120)
    raw3 = []
    if rc3 == 0:
        for line in out3.splitlines():
            row = line.strip()
            if not row or row.startswith('Loaded plugins') or row.startswith('Available'):
                continue
            fields = row.split()
            if len(fields) >= 2 and pkg_name in fields[0]:
                raw3.append(fields[1])
    if raw3:
        return _normalize_versions(_sort_versions_desc(raw3), max_items=normalize_max)
    return []


def _merge_version_candidates(primary, extra, normalize_max=200):
    """Dedupe and sort descending for RabbitMQ multi-source repoquery."""
    return _normalize_versions(
        _sort_versions_desc(list(primary or []) + list(extra or [])),
        max_items=normalize_max,
    )


def _rhel_repoquery_rabbitmq_packagecloud_el_dist(pkg_name, el_major):
    """
    Query rabbitmq-server versions from a specific Packagecloud el/N path without
    enabling that repo system-wide. Helps when el/9 metadata lags el/8 for 4.x.
    """
    arch = platform.machine() or 'x86_64'
    repoid = 'cybercp-pc-rmq-el{0}'.format(int(el_major))
    base = 'https://packagecloud.io/rabbitmq/rabbitmq-server/el/{0}/{1}'.format(
        int(el_major), arch
    )
    cmd = [
        'dnf',
        'repoquery',
        '--repofrompath={0},{1}'.format(repoid, base),
        '--setopt={0}.gpgcheck=0'.format(repoid),
        '--setopt={0}.repo_gpgcheck=0'.format(repoid),
        '--available',
        '--show-duplicates',
        '--qf',
        '%{version}',
        pkg_name,
    ]
    rc, out, _ = _run(cmd, timeout=240)
    if rc != 0 or not (out or '').strip():
        return []
    raw = []
    for line in out.splitlines():
        v = (line or '').strip()
        if v and re.match(r'^[0-9]', v):
            raw.append(v)
    return _normalize_versions(_sort_versions_desc(raw), max_items=200)


def _debian_versions(pkg_name, normalize_max=25):
    versions = []
    _run(['apt-get', 'update', '-y'], timeout=180)
    rc, out, _ = _run(['apt-cache', 'madison', pkg_name], timeout=60)
    if rc != 0:
        return []
    for line in out.splitlines():
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 2 and parts[1]:
            versions.append(parts[1])
    collected = []
    for v in versions:
        m = re.search(r'(\d+\.\d+\.\d+)', v)
        collected.append(m.group(1) if m else v)
    return _normalize_versions(_sort_versions_desc(collected), max_items=normalize_max)


def _filter_es_major(versions, es_major):
    major = normalize_elasticsearch_major(es_major)
    out = []
    for v in versions or []:
        head = (v.split('.') or [''])[0]
        if head == major:
            out.append(v)
    return out


def _get_available_versions_uncached(app_name, es_major='8', rabbitmq_stream='4'):
    pkg_name = package_name_for_app(app_name)
    if app_name == 'Elasticsearch':
        pkg_name = 'elasticsearch'

    if not pkg_name:
        return []

    rmq_stream = '4'
    if app_name == 'RabbitMQ':
        from manageServices.application_rabbitmq_repo import (
            normalize_rabbitmq_stream,
            ensure_rabbitmq_team_repos,
        )
        rmq_stream = normalize_rabbitmq_stream(rabbitmq_stream)
        ensure_rabbitmq_team_repos(rmq_stream)

    if is_debian_family():
        if app_name == 'RabbitMQ':
            versions = _debian_versions(pkg_name, normalize_max=200)
        else:
            versions = _debian_versions(pkg_name)
        if app_name == 'Elasticsearch':
            versions = _filter_es_major(versions, es_major)
    else:
        if app_name == 'Elasticsearch':
            _ensure_cyberpanel_es_repo(es_major)
            versions = _rhel_repoquery_versions(
                pkg_name, use_cyberpanel_extra_repos=True
            )
            versions = _filter_es_major(versions, es_major)
        elif app_name == 'RabbitMQ':
            versions = _rhel_repoquery_versions(
                pkg_name, latest_limit=None, normalize_max=200
            )
            host_major = rhel_major_from_os_release()
            # el/9 (and newer) enabled repos often omit 4.x in metadata; el/8 tree may list them.
            if host_major is not None and host_major >= 9:
                pc_el8 = _rhel_repoquery_rabbitmq_packagecloud_el_dist(pkg_name, 8)
                if pc_el8:
                    versions = _merge_version_candidates(versions, pc_el8, 200)
        else:
            versions = _rhel_repoquery_versions(pkg_name)

    if app_name == 'RabbitMQ':
        from manageServices.application_rabbitmq_repo import (
            RABBITMQ_4X_METADATA_FALLBACK_VERSIONS,
            filter_versions_for_stream,
            refresh_debian_apt_metadata,
            refresh_rhel_metadata_for_rabbitmq_repos,
        )
        versions = filter_versions_for_stream(versions, rmq_stream)
        if not versions:
            if is_debian_family():
                refresh_debian_apt_metadata()
                versions = _debian_versions(pkg_name, normalize_max=200)
            else:
                refresh_rhel_metadata_for_rabbitmq_repos()
                versions = _rhel_repoquery_versions(
                    pkg_name, latest_limit=None, normalize_max=200
                )
                host_major = rhel_major_from_os_release()
                if host_major is not None and host_major >= 9:
                    pc_el8 = _rhel_repoquery_rabbitmq_packagecloud_el_dist(pkg_name, 8)
                    if pc_el8:
                        versions = _merge_version_candidates(versions, pc_el8, 200)
            versions = filter_versions_for_stream(versions, rmq_stream)
        # Always offer GA 4.x when DNF lists none (panel user may get empty repoquery).
        if rmq_stream == '4' and not versions and not is_debian_family():
            versions = list(RABBITMQ_4X_METADATA_FALLBACK_VERSIONS)
        versions = _normalize_versions(_sort_versions_desc(versions), max_items=40)
    return versions


def get_available_versions(app_name, es_major='8', rabbitmq_stream='4'):
    """
    Cached wrapper: avoids hammering DNF from many concurrent panel workers (503 on Manage Applications).
    """
    key = _version_cache_key(app_name, es_major, rabbitmq_stream)
    hit = _cache_get_versions(key)
    if hit is not None:
        return hit

    with _DNF_COLD_FETCH_LOCK:
        hit2 = _cache_get_versions(key)
        if hit2 is not None:
            return hit2
        versions = _get_available_versions_uncached(
            app_name, es_major, rabbitmq_stream
        )
        if versions:
            _cache_put_versions(key, versions)
        return list(versions)


def get_latest_version(app_name, es_major='8', rabbitmq_stream='4'):
    versions = get_available_versions(app_name, es_major, rabbitmq_stream)
    if not versions:
        return ''
    return versions[0]


def get_branch_and_global_latest(app_name, es_major='8', rabbitmq_stream='4'):
    """
    Latest on the UI-selected branch/stream vs latest across all supported branches.

    Returns (latest_on_branch, latest_global).
    """
    latest_branch = get_latest_version(app_name, es_major, rabbitmq_stream)
    if app_name == 'Elasticsearch':
        candidates = []
        for m in ('7', '8', '9'):
            v = get_latest_version('Elasticsearch', m, rabbitmq_stream)
            if v:
                candidates.append(v)
        latest_global = _max_version_string(candidates) if candidates else ''
    elif app_name == 'RabbitMQ':
        candidates = []
        for s in ('3', '4'):
            v = get_latest_version('RabbitMQ', es_major, s)
            if v:
                candidates.append(v)
        latest_global = _max_version_string(candidates) if candidates else ''
    else:
        latest_global = latest_branch
    if not latest_global:
        latest_global = latest_branch
    return latest_branch, latest_global


def cross_branch_newer_suggested(installed, latest_branch, latest_global):
    """
    True when installed is current (or ahead of) the selected branch latest but
    a newer release exists on another line (e.g. 8.x latest installed, 9.x exists).
    """
    if not installed or not latest_global:
        return False
    if version_compare(installed, latest_global) >= 0:
        return False
    if not latest_branch:
        return True
    return version_compare(installed, latest_branch) >= 0
