# -*- coding: utf-8 -*-
"""
Team RabbitMQ package repositories (Packagecloud) and Erlang compatibility
for RabbitMQ 3.x vs 4.x installation streams.
"""
import re
import subprocess

from manageServices.application_detection import is_debian_family

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
    s = str(value or '3').strip()
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
        _run(['apt-get', 'update', '-y'], timeout=120)
    else:
        rc, out, err = _run_shell_trusted(_RPM_ERLANG_SCRIPT)
        if rc != 0:
            _write_status(status_file, 'rabbitmq-erlang repo script: ' + (err or out or 'failed'))
        rc2, out2, err2 = _run_shell_trusted(_RPM_SERVER_SCRIPT)
        if rc2 != 0:
            _write_status(
                status_file, 'rabbitmq-server repo script: ' + (err2 or out2 or 'failed')
            )
        # Prefer dnf; yum exists as symlink on EL8/9.
        for cache_cmd in (['dnf', 'makecache', '-y'], ['yum', 'makecache', '-y']):
            c_rc, _, _ = _run(cache_cmd, timeout=120)
            if c_rc == 0:
                break
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
