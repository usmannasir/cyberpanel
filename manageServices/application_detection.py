import os
import re
import subprocess


APP_PACKAGE_MAP = {
    'Elasticsearch': {
        'rhel': 'elasticsearch',
        'debian': 'elasticsearch',
        'service': 'elasticsearch',
        'binary_paths': ['/usr/share/elasticsearch/bin/elasticsearch']
    },
    'Redis': {
        'rhel': 'redis',
        'debian': 'redis-server',
        'service': 'redis',
        'binary_paths': ['/usr/bin/redis-server']
    },
    'RabbitMQ': {
        'rhel': 'rabbitmq-server',
        'debian': 'rabbitmq-server',
        'service': 'rabbitmq-server',
        'binary_paths': ['/usr/sbin/rabbitmq-server', '/usr/lib/rabbitmq/bin/rabbitmq-server']
    }
}

APP_MARKERS = {
    'Elasticsearch': '/home/cyberpanel/elasticsearch',
    'Redis': '/home/cyberpanel/redis',
    'RabbitMQ': '/home/cyberpanel/rabbitmq'
}


def _run(cmd):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        return res.returncode, (res.stdout or '').strip(), (res.stderr or '').strip()
    except Exception as err:
        return 1, '', str(err)


def is_debian_family():
    return os.path.exists('/etc/debian_version') or os.path.exists('/etc/lsb-release')


def is_centos7():
    release_paths = ['/etc/centos-release', '/etc/redhat-release', '/etc/os-release']
    text_blob = ''
    for path in release_paths:
        try:
            if os.path.exists(path):
                with open(path, 'r') as fh:
                    text_blob += fh.read().lower() + '\n'
        except Exception:
            continue
    return ('centos' in text_blob and ('release 7' in text_blob or 'version_id="7' in text_blob))


def managed_apps_os_support():
    if is_centos7():
        return {
            'supported': False,
            'reason': 'CentOS 7 is EOL and not supported for managed applications.'
        }
    return {
        'supported': True,
        'reason': ''
    }


def package_name_for_app(app_name):
    app_map = APP_PACKAGE_MAP.get(app_name, {})
    if not app_map:
        return ''
    if is_debian_family():
        return app_map.get('debian', '')
    return app_map.get('rhel', '')


def _rpm_installed(pkg_name):
    rc, out, _ = _run(['rpm', '-q', pkg_name])
    if rc == 0:
        return True, out
    return False, ''


def _dpkg_installed(pkg_name):
    rc, out, _ = _run(['dpkg-query', '-W', '-f=${Version}', pkg_name])
    if rc == 0 and out:
        return True, out
    return False, ''


def _systemd_active(service_name):
    rc, out, _ = _run(['systemctl', 'is-active', service_name])
    return rc == 0 and out.strip() == 'active'


def detect_installed_version(app_name):
    pkg_name = package_name_for_app(app_name)
    if not pkg_name:
        return ''

    if is_debian_family():
        ok, ver = _dpkg_installed(pkg_name)
    else:
        ok, ver = _rpm_installed(pkg_name)

    if not ok:
        return ''

    if app_name in ('Elasticsearch', 'Redis', 'RabbitMQ'):
        match = re.search(r'(\d+\.\d+\.\d+)', ver)
        return match.group(1) if match else ver

    return ver


def detect_app_state(app_name):
    marker_path = APP_MARKERS.get(app_name, '')
    package_name = package_name_for_app(app_name)
    service_name = APP_PACKAGE_MAP.get(app_name, {}).get('service', '')
    binary_paths = APP_PACKAGE_MAP.get(app_name, {}).get('binary_paths', [])

    installed_version = detect_installed_version(app_name)
    marker_exists = bool(marker_path and os.path.exists(marker_path))
    service_active = _systemd_active(service_name) if service_name else False
    binary_exists = any(os.path.exists(path) for path in binary_paths)

    installed = bool(installed_version or service_active or binary_exists)

    return {
        'appName': app_name,
        'packageName': package_name,
        'markerPath': marker_path,
        'markerExists': marker_exists,
        'installed': installed,
        'installedVersion': installed_version,
        'serviceActive': service_active,
        'binaryExists': binary_exists
    }
