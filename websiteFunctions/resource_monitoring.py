import os
import shlex

from plogical.processUtilities import ProcessUtilities
import plogical.CyberCPLogFileWriter as logging

_disk_cache = {}


def _resolve_site_path(domain):
    if not domain:
        return None
    candidates = [
        f'/home/{domain}',
        f'/home/{domain}/public_html',
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _get_disk_used_mb(site_path):
    if not site_path or not os.path.exists(site_path):
        return 0.0
    try:
        command = f'du -sm {shlex.quote(site_path)} | cut -f1'
        result = ProcessUtilities.outputExecutioner(command)
        return float((result or '0').strip().split()[0])
    except BaseException:
        return 0.0


def _get_cached_disk_used_mb(domain, site_path):
    import time

    cache_key = domain or site_path
    now = time.time()
    cached = _disk_cache.get(cache_key)
    if cached and (now - cached['ts']) < 60:
        return cached['mb']
    used_mb = _get_disk_used_mb(site_path)
    _disk_cache[cache_key] = {'mb': used_mb, 'ts': now}
    return used_mb


def get_website_resource_usage(external_app, domain=None, package=None):
    try:
        user = external_app
        if not user:
            return {'status': 0, 'error_message': 'User not found'}

        disk_limit_mb = 0
        memory_limit_mb = 0
        if package is not None:
            try:
                disk_limit_mb = int(package.diskSpace or 0)
            except (TypeError, ValueError):
                disk_limit_mb = 0
            try:
                memory_limit_mb = int(package.memoryLimitMB or 0)
            except (TypeError, ValueError):
                memory_limit_mb = 0

        command = (
            f"ps -u {shlex.quote(user)} -o pcpu,pmem | grep -v CPU | "
            "awk '{cpu += $1; mem += $2} END {print cpu, mem}'"
        )
        result = ProcessUtilities.outputExecutioner(command)
        try:
            cpu_percent, _legacy_mem_percent = map(float, (result or '0 0').split())
        except BaseException:
            cpu_percent = 0.0

        rss_command = (
            f"ps -u {shlex.quote(user)} -o rss= | awk '{{s += $1}} END {{print s}}'"
        )
        rss_result = ProcessUtilities.outputExecutioner(rss_command)
        try:
            rss_kb = float((rss_result or '0').strip() or 0)
        except BaseException:
            rss_kb = 0.0
        rss_mb = rss_kb / 1024.0

        memory_unlimited = memory_limit_mb <= 0
        if memory_unlimited:
            memory_usage = round(rss_mb, 2)
            memory_percent = 0.0
        else:
            memory_percent = min(100.0, (rss_mb / float(memory_limit_mb)) * 100.0)
            memory_usage = round(memory_percent, 2)

        site_path = _resolve_site_path(domain)
        disk_used_mb = _get_cached_disk_used_mb(domain, site_path)
        disk_unlimited = disk_limit_mb <= 0

        if disk_unlimited:
            disk_percent = round(disk_used_mb, 2)
        else:
            disk_percent = min(100.0, round((disk_used_mb / float(disk_limit_mb)) * 100.0, 2))

        return {
            'status': 1,
            'cpu_usage': round(cpu_percent, 2),
            'memory_usage': memory_usage,
            'memory_used_mb': round(rss_mb, 2),
            'memory_percent': round(memory_percent, 2),
            'memory_unlimited': memory_unlimited,
            'memory_limit_mb': memory_limit_mb,
            'disk_used': round(disk_used_mb, 2),
            'disk_used_mb': round(disk_used_mb, 2),
            'disk_total': disk_limit_mb if disk_limit_mb > 0 else 0,
            'disk_limit_mb': disk_limit_mb,
            'disk_percent': disk_percent,
            'disk_unlimited': disk_unlimited,
        }

    except BaseException as msg:
        logging.CyberCPLogFileWriter.writeToFile(
            f'Error in get_website_resource_usage: {str(msg)}'
        )
        return {'status': 0, 'error_message': str(msg)}
