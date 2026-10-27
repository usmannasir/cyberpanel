"""Bounded, read-only resource measurements for an authorized website."""
import os
import sys
import json
import math
import pwd
import shlex
import time
import psutil
if __name__ == '__main__':
    sys.path.insert(0, '/usr/local/CyberCP')
from plogical.processUtilities import ProcessUtilities
from plogical.securityUtils import is_safe_system_user


def process_usage(username, interval=0.1):
    if not is_safe_system_user(username) or username == 'root':
        raise ValueError('Invalid website system user.')
    uid = pwd.getpwnam(username).pw_uid
    samples = []
    started = time.monotonic()
    for process in psutil.process_iter(['uids', 'cpu_times']):
        if time.monotonic() - started > 1:
            raise ValueError('Process sampling exceeded its time limit.')
        try:
            if process.info['uids'].effective == uid:
                cpu = process.info['cpu_times']
                samples.append((process, cpu.user + cpu.system, time.monotonic()))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            raise ValueError('Process usage could not be read.') from None
    time.sleep(interval)
    cpu_cores, memory = 0.0, 0
    for process, before, sampled_at in samples:
        try:
            cpu = process.cpu_times()
            elapsed = max(time.monotonic() - sampled_at, 0.001)
            cpu_cores += max(0.0, cpu.user + cpu.system - before) / elapsed
            memory += process.memory_info().rss
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            raise ValueError('Process usage could not be read.') from None
    cpu_percent = min(100.0, cpu_cores / max(psutil.cpu_count() or 1, 1) * 100)
    memory_percent = memory / psutil.virtual_memory().total * 100
    return cpu_percent, memory_percent


def account_usage(username):
    """Sample in the existing privileged bridge; hidepid can silently hide peers."""
    if not is_safe_system_user(username) or username == 'root':
        raise ValueError('Invalid website system user.')
    if os.geteuid() == 0:
        return process_usage(username)
    command = '/usr/local/CyberCP/bin/python %s --account-usage %s' % (
        shlex.quote(os.path.abspath(__file__)), shlex.quote(username))
    ok, output = ProcessUtilities.outputExecutioner(command, shell=False, retRequired=True)
    if not ok:
        raise ValueError('Account process usage is unavailable.')
    data = json.loads(output)
    values = (data['cpu_usage'], data['memory_usage'])
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
        raise ValueError('Account process usage is unavailable.')
    return values


def get_website_resource_usage(website):
    try:
        # The Unix account name normally differs from the website domain.
        domain = website.domain
        if not domain or '/' in domain or domain in ('.', '..') or '\\' in domain:
            raise ValueError('Invalid website domain.')
        home = '/home/' + domain
        path = home + '/public_html'
        if os.path.commonpath((os.path.realpath(home), os.path.realpath(path))) != os.path.realpath(home):
            raise ValueError('Website document root is outside its home directory.')
        cpu_percent, memory_percent = account_usage(website.externalApp)
        # Bound expensive disk scans; use argv semantics through the executor.
        ok, output = ProcessUtilities.outputExecutioner(
            '/usr/bin/timeout 5 du -sk -- ' + shlex.quote(path), shell=False, retRequired=True)
        if not ok:
            raise ValueError('Disk usage is unavailable or the scan timed out.')
        disk_used = int(output.split()[0]) / 1024
        ok, output = ProcessUtilities.outputExecutioner(
            '/usr/bin/timeout 5 df -Pk -- ' + shlex.quote(path), shell=False, retRequired=True)
        if not ok:
            raise ValueError('Filesystem capacity is unavailable.')
        disk_total = int(output.strip().splitlines()[-1].split()[1]) / 1024
        if disk_total <= 0:
            raise ValueError('Filesystem capacity is unavailable.')
        return {'status': 1, 'cpu_usage': round(cpu_percent, 2),
                'memory_usage': round(memory_percent, 2), 'disk_used': round(disk_used, 2),
                'disk_total': round(disk_total, 2), 'disk_percent': round(disk_used / disk_total * 100, 4)}
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, psutil.Error):
        return {'status': 0, 'error_message': 'Resource usage is unavailable. Check the website account, directory permissions and server load.'}


def format_resource_limits(values):
    """lscgctl CPU units are percent of one core, not a number of cores."""
    def display(value):
        if value is None:
            return 'Unavailable'
        if value in ('', '-1', -1, 'infinity', 'max'):
            return 'Unlimited'
        return str(value)
    cpu = display(values.get('cpu'))
    if cpu not in ('Unlimited', 'Unavailable'):
        try:
            percent = float(cpu.rstrip('%'))
            if not math.isfinite(percent) or percent < 0:
                raise ValueError('Invalid CPU limit.')
            cpu = '%g cores (%g%%)' % (percent / 100, percent)
        except (ValueError, TypeError):
            cpu = 'Unavailable'
    return {'cpu': cpu, 'memory': display(values.get('mem')),
            'io': display(values.get('io')), 'tasks': display(values.get('tasks')),
            'iops': display(values.get('iops'))}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] != '--account-usage' or os.geteuid() != 0:
            raise ValueError('Privileged account sampling is required.')
        cpu, memory = process_usage(sys.argv[2])
        print(json.dumps({'cpu_usage': cpu, 'memory_usage': memory}))
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, psutil.Error):
        print(json.dumps({'error': 'Account process usage is unavailable.'}))
        sys.exit(1)
