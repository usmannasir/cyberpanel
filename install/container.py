#!/usr/bin/env python
"""
CyberPanel Docker / container runtime helpers.
"""

import json
import os
import subprocess
import sys

if not os.path.isfile('/etc/os-release') and os.environ.get('CYBERPANEL_CONTAINER') != '1':
    pass


def _run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or '') + (r.stderr or '')
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def read_container_config():
    path = '/etc/cyberpanel/container.json'
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def write_container_config(data):
    os.makedirs('/etc/cyberpanel', mode=0o755, exist_ok=True)
    path = '/etc/cyberpanel/container.json'
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write('\n')
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def detect_os_tag():
    if not os.path.isfile('/etc/os-release'):
        return 'unknown'
    content = open('/etc/os-release', 'r', encoding='utf-8', errors='replace').read().lower()
    if 'almalinux' in content:
        if 'version_id="10' in content or 'version_id=10' in content:
            return 'almalinux10'
        if 'version_id="9' in content or 'version_id=9' in content:
            return 'almalinux9'
        return 'almalinux8'
    if 'ubuntu' in content:
        if 'version_id="24' in content:
            return 'ubuntu2404'
        if 'version_id="22' in content:
            return 'ubuntu2204'
        return 'ubuntu'
    if 'debian' in content:
        if 'version_id="13' in content:
            return 'debian13'
        if 'version_id="12' in content:
            return 'debian12'
        if 'version_id="11' in content:
            return 'debian11'
        return 'debian'
    if 'rocky' in content:
        return 'rockylinux9' if 'version_id="9' in content else 'rockylinux8'
    if 'centos stream' in content:
        return 'centos-stream9'
    if 'openeuler' in content:
        return 'openeuler2203' if '22.03' in content else 'openeuler2003'
    return 'rhel-like'


def build_container_config(postfix_on, powerdns_on, ftp_on):
    minimal = not (postfix_on and powerdns_on and ftp_on)
    if minimal and (postfix_on or powerdns_on or ftp_on):
        mode = 'partial'
    elif minimal:
        mode = 'minimal'
    else:
        mode = 'full'
    return {
        'container': True,
        'mode': mode,
        'powerdns': bool(powerdns_on),
        'postfix': bool(postfix_on),
        'pureftpd': bool(ftp_on),
        'firewalld': True,
        'docker_ce': True,
        'os_tag': detect_os_tag(),
    }


def service_active(name):
    ok, _ = _run('systemctl is-active --quiet %s' % name)
    return ok


def validate_container_install(config):
    errors = []
    required = ['lscpd', 'mariadb', 'docker', 'firewalld']
    for unit in required:
        if not service_active(unit):
            errors.append('service not active: %s' % unit)
    if config.get('powerdns') and not service_active('pdns'):
        errors.append('powerdns enabled but pdns not active')
    if config.get('postfix') and not service_active('postfix'):
        errors.append('postfix enabled but not active')
    if config.get('pureftpd') and not service_active('pure-ftpd'):
        if not service_active('pure-ftpd-mysql'):
            errors.append('pure-ftpd enabled but not active')
    ok, out = _run('docker info >/dev/null 2>&1')
    if not ok:
        errors.append('docker info failed: %s' % out.strip()[:200])
    return len(errors) == 0, errors


def finalize_container_install(postfix_flag, powerdns_flag, ftp_flag, log_fn=None):
    from install import install_utils

    if not install_utils.is_container_runtime():
        return True, []

    install_utils.container_prepare_dns(powerdns_flag)
    config = build_container_config(
        postfix_flag == 'ON',
        powerdns_flag == 'ON',
        ftp_flag == 'ON',
    )
    write_container_config(config)
    marker = '/etc/cyberpanel/.docker-initialized'
    try:
        with open(marker, 'w', encoding='utf-8') as fh:
            fh.write('1\n')
    except OSError as exc:
        if log_fn:
            log_fn('Could not write docker marker: %s' % exc)

    ok, errors = validate_container_install(config)
    if log_fn:
        if ok:
            log_fn('Container install validation passed (mode=%s)' % config.get('mode'))
        else:
            for err in errors:
                log_fn('Container validation: %s' % err)
    return ok, errors


def main():
    config = read_container_config()
    if not config:
        print(json.dumps({'error': 'no container.json'}, indent=2))
        sys.exit(1)
    ok, errors = validate_container_install(config)
    print(json.dumps({'ok': ok, 'config': config, 'errors': errors}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
