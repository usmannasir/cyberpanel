"""Bounded reverse lookup with a system-resolver fallback for hostname setup."""
import ipaddress
import json
import re
import subprocess
import sys

import requests


def _hostnames(values):
    result = []
    for value in values:
        if not isinstance(value, str):
            continue
        name = value.strip().rstrip('.').lower()
        if not name or len(name) > 253:
            continue
        if not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                   for label in name.split('.')):
            continue
        try:
            ipaddress.ip_address(name)
            continue
        except ValueError:
            pass
        if name not in result:
            result.append(name)
    return result


def reverse_dns_lookup(address):
    try:
        address = str(ipaddress.ip_address(address))
    except (ValueError, TypeError):
        return []
    results = []
    try:
        response = requests.get('https://cyberpanel.net/dnsServers.txt', timeout=5)
        response.raise_for_status()
        urls = response.json().get('urls', [])
        if not isinstance(urls, list):
            urls = []
        for url in urls[:3]:
            if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
                continue
            try:
                response = requests.get(url.rstrip('/') + '/index.php',
                                        params={'ip': address}, timeout=5)
                response.raise_for_status()
                data = response.json()
                if data.get('status') == 1 and isinstance(data.get('results'), dict):
                    results.extend(data['results'].get(key) for key in
                                   ('8.8.8.8', '1.1.1.1', '9.9.9.9'))
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                continue
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        pass
    names = _hostnames(results)
    if names:
        return names
    # gethostbyaddr has no per-call timeout. A short-lived child bounds even a
    # stalled NSS resolver without leaving a background thread in the worker.
    script = ('import json,socket,sys; r=socket.gethostbyaddr(sys.argv[1]); '
              'print(json.dumps([r[0]] + r[1]))')
    try:
        response = subprocess.run([sys.executable, '-c', script, address],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=5, check=True, universal_newlines=True)
        values = json.loads(response.stdout)
        return _hostnames(values) if isinstance(values, list) else []
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return []
