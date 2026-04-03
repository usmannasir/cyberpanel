# -*- coding: utf-8 -*-
"""
Team RabbitMQ package repositories (Packagecloud) and Erlang compatibility
for RabbitMQ 3.x vs 4.x installation streams.
"""
import os
import re
import subprocess
import tempfile
import time

from manageServices.application_detection import is_debian_family, rhel_major_from_os_release

# Official Packagecloud install scripts (RabbitMQ team).
_RPM_ERLANG_SCRIPT = (
    'https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-erlang/script.rpm.sh'
)
_RPM_SERVER_SCRIPT = (
    'https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.rpm.sh'
)
_DEB_ERLANG_SCRIPT = (
    'https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-erlang/script.deb.sh'
)
_DEB_SERVER_SCRIPT = (
    'https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.deb.sh'
)

# Minimum OTP major for each product stream (see rabbitmq.com docs / compatibility).
_MIN_OTP_STREAM_3 = 25
_MIN_OTP_STREAM_4 = 26

# When Packagecloud metadata lists 3.x but no 4.x (common on el/9 trees), still offer GA
# releases from https://www.rabbitmq.com/release-information so the panel can run
# dnf install rabbitmq-server-<version> (RPMs are often el8-tagged on EL9 per upstream docs).
# Update this tuple when new 4.x patches ship.
RABBITMQ_4X_METADATA_FALLBACK_VERSIONS = (
    '4.2.5',
    '4.2.4',
    '4.2.3',
    '4.2.2',
    '4.2.1',
    '4.2.0',
    '4.1.8',
    '4.1.7',
    '4.1.6',
    '4.1.5',
    '4.1.4',
    '4.1.3',
    '4.1.2',
    '4.1.1',
    '4.1.0',
    '4.0.9',
    '4.0.8',
    '4.0.7',
    '4.0.6',
    '4.0.5',
    '4.0.4',
    '4.0.3',
    '4.0.2',
    '4.0.1',
    '4.0.0',
)

_YUM_REPOS_D = '/etc/yum.repos.d'
# Packagecloud RabbitMQ repos use .../el/N/... in baseurl; must match host RHEL major.
_EL_URL_SEGMENT = re.compile(r'(/el/)(\d+)(/)')


def _run(cmd, timeout=300):
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=False
        )
        return res.returncode, (res.stdout or ''), (res.stderr or '')
    except Exception as err:
        return 1, '', str(err)


def _run_shell_trusted(script_url, timeout=300):
    """Run packagecloud install script from fixed RabbitMQ-team URL only."""
    allowed = {_RPM_ERLANG_SCRIPT, _RPM_SERVER_SCRIPT, _DEB_ERLANG_SCRIPT, _DEB_SERVER_SCRIPT}
    if script_url not in allowed:
        return 1, '', 'Invalid repository script URL.'
    # curl -fsSL ... | bash  (URLs are allowlisted above)
    cmd = 'curl -1fsSL {0} | bash'.format(script_url)
    return _run(['/bin/bash', '-lc', cmd], timeout=timeout)


def normalize_rabbitmq_stream(value):
    s = str(value or '4').strip()
    if s in ('4', '4.x', '41', '4.1'):
        return '4'
    return '3'


def _write_status(status_file, message):
    if status_file is None:
        return
    try:
        status_file.write(message + '\n')
        status_file.flush()
    except Exception:
        pass


def _rhel_refresh_package_metadata(status_file=None, aggressive=False):
    """
    Refresh DNF/YUM metadata after adding Packagecloud repos.
    Retries on failure. When aggressive (e.g. 4.x stream), expire cache first
    so new rabbitmq-server builds become visible.
    """
    if is_debian_family():
        return True
    if aggressive:
        exp_rc, _, exp_err = _run(['dnf', 'clean', 'expire-cache'], timeout=90)
        if exp_rc != 0:
            _write_status(
                status_file,
                'dnf expire-cache (non-fatal): ' + (exp_err or '')[:120]
            )
    last_err = ''
    for attempt in range(1, 4):
        for cache_cmd in (['dnf', 'makecache', '-y'], ['yum', 'makecache', '-y']):
            c_rc, c_out, c_err = _run(cache_cmd, timeout=180)
            if c_rc == 0:
                _write_status(
                    status_file,
                    'RPM metadata refreshed ({0}, attempt {1}).'.format(
                        cache_cmd[0], attempt
                    )
                )
                return True
            last_err = (c_err or c_out or str(c_rc)).strip()
        time.sleep(min(3 * attempt, 15))
    _write_status(
        status_file,
        'RPM metadata refresh failed after retries: ' + (last_err or 'unknown')[:240]
    )
    return False


def refresh_rhel_metadata_for_rabbitmq_repos(status_file=None):
    """
    Public: force another metadata refresh (e.g. when repoquery finds no 4.x RPMs).
    """
    return _rhel_refresh_package_metadata(status_file=status_file, aggressive=True)


def align_rabbitmq_packagecloud_repos_to_os(status_file=None):
    """
    If Team RabbitMQ Packagecloud .repo files point at /el/M/ but this host is el/N,
    rewrite URLs to /el/N/ (e.g. stale el/8 on AlmaLinux 9). Only touches files that
    mention both packagecloud.io and rabbitmq. Requires root to write /etc/yum.repos.d.
    """
    if is_debian_family():
        return
    target_major = rhel_major_from_os_release()
    if target_major is None:
        return
    if not os.path.isdir(_YUM_REPOS_D):
        return
    try:
        repo_names = sorted(
            n for n in os.listdir(_YUM_REPOS_D) if n.endswith('.repo')
        )
    except OSError as err:
        _write_status(
            status_file,
            'rabbitmq repo align: cannot list {0}: {1}'.format(
                _YUM_REPOS_D, str(err)[:100]
            )
        )
        return

    for repo_name in repo_names:
        repo_path = os.path.join(_YUM_REPOS_D, repo_name)
        try:
            with open(repo_path, 'r', encoding='utf-8', errors='replace') as handle:
                original = handle.read()
        except OSError:
            continue
        lower = original.lower()
        if 'packagecloud.io' not in lower or 'rabbitmq' not in lower:
            continue

        def _sub_el(match):
            current = int(match.group(2))
            if current == target_major:
                return match.group(0)
            return match.group(1) + str(target_major) + match.group(3)

        updated = _EL_URL_SEGMENT.sub(_sub_el, original)
        if updated == original:
            continue
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                prefix='.cybercp-rabbitmq-',
                suffix='.tmp',
                dir=_YUM_REPOS_D,
                text=True,
            )
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                out.write(updated)
            os.replace(tmp_path, repo_path)
            tmp_path = None
            _write_status(
                status_file,
                'Aligned RabbitMQ Packagecloud repo {0} to el/{1}.'.format(
                    repo_name, target_major
                )
            )
        except PermissionError:
            _write_status(
                status_file,
                'rabbitmq repo align: need root to rewrite {0} (el/{1}).'.format(
                    repo_name, target_major
                )
            )
        except OSError as err:
            _write_status(
                status_file,
                'rabbitmq repo align: {0}: {1}'.format(repo_name, str(err)[:120])
            )
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


def refresh_debian_apt_metadata(status_file=None):
    """Second-chance apt metadata refresh without re-running Packagecloud scripts."""
    if not is_debian_family():
        return True
    last_err = ''
    for apt_attempt in range(1, 4):
        a_rc, _, a_err = _run(['apt-get', 'update', '-y'], timeout=180)
        if a_rc == 0:
            _write_status(
                status_file,
                'APT metadata refreshed (attempt {0}).'.format(apt_attempt)
            )
            return True
        last_err = (a_err or '').strip()
        _write_status(
            status_file,
            'apt-get update attempt {0}: {1}'.format(apt_attempt, (last_err or '')[:160])
        )
        time.sleep(min(3 * apt_attempt, 12))
    return False


def ensure_rabbitmq_team_repos(stream, status_file=None):
    """
    Idempotently enable rabbitmq-erlang and rabbitmq-server Packagecloud repos.
    Required so 3.13.x, 4.x, and matching Erlang builds are visible to the
    package manager.
    """
    stream = normalize_rabbitmq_stream(stream)
    _write_status(
        status_file,
        'Ensuring Team RabbitMQ repositories (stream {0})...'.format(stream)
    )
    if is_debian_family():
        rc, out, err = _run_shell_trusted(_DEB_ERLANG_SCRIPT)
        if rc != 0:
            _write_status(status_file, 'rabbitmq-erlang repo script: ' + (err or out or 'failed'))
        rc2, out2, err2 = _run_shell_trusted(_DEB_SERVER_SCRIPT)
        if rc2 != 0:
            _write_status(
                status_file, 'rabbitmq-server repo script: ' + (err2 or out2 or 'failed')
            )
        for apt_attempt in range(1, 4):
            a_rc, _, a_err = _run(['apt-get', 'update', '-y'], timeout=180)
            if a_rc == 0:
                break
            _write_status(
                status_file,
                'apt-get update attempt {0}: {1}'.format(apt_attempt, (a_err or '')[:160])
            )
            time.sleep(min(3 * apt_attempt, 12))
    else:
        align_rabbitmq_packagecloud_repos_to_os(status_file=status_file)
        rc, out, err = _run_shell_trusted(_RPM_ERLANG_SCRIPT)
        if rc != 0:
            _write_status(status_file, 'rabbitmq-erlang repo script: ' + (err or out or 'failed'))
        rc2, out2, err2 = _run_shell_trusted(_RPM_SERVER_SCRIPT)
        if rc2 != 0:
            _write_status(
                status_file, 'rabbitmq-server repo script: ' + (err2 or out2 or 'failed')
            )
        # 4.x builds may appear after a fresh metadata pull; expire + retries help visibility.
        _rhel_refresh_package_metadata(
            status_file=status_file,
            aggressive=(stream == '4'),
        )
    _write_status(status_file, 'Team RabbitMQ repositories ready.')


def get_erlang_otp_major():
    """Best-effort current Erlang/OTP major version (integer or 0 if unknown)."""
    rc, out, _ = _run(
        [
            'erl',
            '-noshell',
            '-eval',
            'io:format("~s~n", [erlang:system_info(otp_release)]), halt().',
        ],
        timeout=15,
    )
    if rc == 0 and out:
        m = re.search(r'(\d+)', out.strip())
        if m:
            return int(m.group(1))
    # rpm: erlang from RabbitMQ repo may report R26 flavour
    rc2, out2, _ = _run(['rpm', '-q', '--qf', '%{VERSION}', 'erlang'], timeout=10)
    if rc2 == 0 and out2:
        m = re.search(r'^(\d+)', out2.strip())
        if m:
            return int(m.group(1))
    return 0


def minimum_otp_for_stream(stream):
    stream = normalize_rabbitmq_stream(stream)
    if stream == '4':
        return _MIN_OTP_STREAM_4
    return _MIN_OTP_STREAM_3


def minimum_otp_for_rabbitmq_version(version_str):
    """Infer OTP floor from chosen RabbitMQ version when possible."""
    if not version_str or version_str == 'latest':
        return None
    m = re.match(r'^(\d+)', str(version_str).strip())
    if not m:
        return None
    major = int(m.group(1))
    if major >= 4:
        return _MIN_OTP_STREAM_4
    if major >= 3:
        return _MIN_OTP_STREAM_3
    return None


def ensure_erlang_meets_minimum(stream, version, status_file=None):
    """
    Upgrade/install Erlang from enabled repos if OTP is below the minimum
    for the selected RabbitMQ stream or explicit target version.
    """
    stream = normalize_rabbitmq_stream(stream)
    need = minimum_otp_for_stream(stream)
    version_floor = minimum_otp_for_rabbitmq_version(version)
    if version_floor is not None:
        need = max(need, version_floor)

    current = get_erlang_otp_major()
    if current >= need:
        _write_status(
            status_file,
            'Erlang/OTP {0} satisfies minimum {1} for this RabbitMQ target.'.format(
                current or 'unknown', need
            )
        )
        return

    _write_status(
        status_file,
        'Erlang/OTP {0} is below required {1}; installing/upgrading erlang from Team RabbitMQ repo...'.format(
            current or 'unknown', need
        )
    )
    if is_debian_family():
        _run(
            [
                '/bin/bash',
                '-lc',
                'DEBIAN_FRONTEND=noninteractive apt-get install -y erlang',
            ],
            timeout=600,
        )
    else:
        for inst in (
            ['dnf', 'install', '-y', 'erlang'],
            ['yum', 'install', '-y', 'erlang'],
        ):
            rc, _, _ = _run(inst, timeout=600)
            if rc == 0:
                break

    after = get_erlang_otp_major()
    if after < need:
        _write_status(
            status_file,
            'WARNING: Erlang may still be below OTP {0} (reported {1}). '
            'Check /root/cyberpanel or logs and install correct erlang package.'.format(
                need, after or 'unknown'
            )
        )
    else:
        _write_status(status_file, 'Erlang/OTP updated to {0}.'.format(after))


def filter_versions_for_stream(versions, stream):
    """Keep only versions whose major matches RabbitMQ stream (3 or 4)."""
    stream = normalize_rabbitmq_stream(stream)
    result = []
    seen = set()
    for raw in versions or []:
        v = (raw or '').strip()
        if not v or v in seen:
            continue
        if v == 'latest':
            continue
        m = re.search(r'(\d+)\.(\d+)', v)
        if m and m.group(1) == stream:
            seen.add(v)
            result.append(v)
    # Preserve descending-ish order (caller already sorted newest first)
    return result
