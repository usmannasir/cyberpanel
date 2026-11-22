"""Serve every website's own certificate on all HTTPS listeners of OpenLiteSpeed.

OpenLiteSpeed chooses the certificate of a TLS connection through the listener
that accepted it: a name the listener maps to a virtual host gets that virtual
host's vhssl certificate, and any other name gets the listener's own. IPv4 and
IPv6 are separate listeners, so a website has to be mapped on both and has to
carry its certificate in its own vhssl block.

The functions that take and return configuration text do no I/O.
"""
import os
import re
from collections import OrderedDict

from plogical.domainAliasUtilities import (
    _LISTENER_PATTERN, _is_secure_listener, ensure_https_vhost_mapping, has_https_listener,
)
from plogical.httpListenerMapping import rewrite_config

SERVER_ROOT = '/usr/local/lsws'
CERTIFICATE_ROOT = '/etc/letsencrypt/live'
MAIN_CONFIG = 'conf/httpd_config.conf'

_LISTENER = (
    '\n'
    'listener %(name)s {\n'
    '  address                 %(address)s\n'
    '  secure                  1\n'
    '  keyFile                  %(certificates)s/%(domain)s/privkey.pem\n'
    '  certFile                 %(certificates)s/%(domain)s/fullchain.pem\n'
    '  certChain               1\n'
    '  sslProtocol             24\n'
    '  enableECDHE             1\n'
    '  renegProtection         1\n'
    '  sslSessionCache         1\n'
    '  enableSpdy              15\n'
    '  enableStapling           1\n'
    '  ocspRespMaxAge           86400\n'
    '  map                     %(domain)s %(domain)s\n'
    '}\n'
    '\n'
    '\n'
)

_VHSSL = (
    '\n'
    'vhssl  {\n'
    '  keyFile                 %(certificates)s/%(domain)s/privkey.pem\n'
    '  certFile                %(certificates)s/%(domain)s/fullchain.pem\n'
    '  certChain               1\n'
    '  sslProtocol             24\n'
    '  enableECDHE             1\n'
    '  renegProtection         1\n'
    '  sslSessionCache         1\n'
    '  enableSpdy              15\n'
    '  enableStapling           1\n'
    '  ocspRespMaxAge           86400\n'
    '}\n'
)

_MAP_LINE = '  map                     %s %s'

# The listeners the panel itself creates and keeps complete: every address of
# one family on port 443. A listener on another port or on a single address
# was set up by an administrator for a purpose the panel does not know.
_WILDCARD_443 = re.compile(
    r'^[ \t]*address[ \t]+(?:\*|ANY|0\.0\.0\.0|\[ANY\]|\[::\]):443[ \t]*\r?$',
    re.MULTILINE | re.IGNORECASE)


def _is_standard_listener(block):
    return _is_secure_listener(block) and bool(_WILDCARD_443.search(block))


def _standard_listeners(config):
    return [match.group(0) for match in re.finditer(_LISTENER_PATTERN, config, flags=re.MULTILINE)
            if _is_standard_listener(match.group(0))]


def _map_entry(line):
    """(virtual host, names) of a listener's map line, or None for any other line."""
    parts = line.partition('#')[0].split(None, 2)
    if len(parts) != 3 or parts[0].lower() != 'map':
        return None
    return parts[1], [name for name in re.split(r'[,\s]+', parts[2].strip()) if name]


def _rewritten_map_line(line, vhost, names):
    comment = line.partition('#')[2]
    suffix = ('  #' + comment.rstrip('\r\n')) if '#' in line else ''
    ending = '\n' if line.endswith('\n') else ''
    return _MAP_LINE % (vhost, ', '.join(names)) + suffix + ending


def ensure_https_listeners(config, domain, certificate_root=CERTIFICATE_ROOT):
    """Give the server an IPv4 and an IPv6 HTTPS listener and map `domain` on every HTTPS listener.

    A listener that is missing is created with the certificate of `domain`,
    which then answers names that listener does not map.
    """
    values = {'domain': domain, 'certificates': certificate_root}
    if not has_https_listener(config):
        config += _LISTENER % dict(values, name='SSL', address='*:443')
    if not has_https_listener(config, ipv6=True):
        config += _LISTENER % dict(values, name='SSL IPv6', address='[ANY]:443')
    return ensure_https_vhost_mapping(config, domain)


def ensure_vhost_certificate(vhost_config, domain, certificate_root=CERTIFICATE_ROOT):
    """Give a virtual host a vhssl block for its own certificate unless it has one."""
    if certificate_files(vhost_config) is not None:
        return vhost_config
    return vhost_config + _VHSSL % {'domain': domain, 'certificates': certificate_root}


def certificate_files(vhost_config):
    """The key and certificate paths of a virtual host's vhssl block, or None without one.

    A path the block does not state on a line of its own is returned empty.
    """
    if re.search(r'(?m)^[ \t]*vhssl\b', vhost_config) is None:
        return None
    block = re.search(r'(?ms)^[ \t]*vhssl[ \t]*\{(.*?)^[ \t]*\}', vhost_config)
    paths = []
    for directive in ('keyFile', 'certFile'):
        found = block and re.search(r'(?mi)^[ \t]*%s[ \t]+(\S+)' % directive, block.group(1))
        paths.append(found.group(1) if found else '')
    return tuple(paths)


def https_listener_vhosts(config):
    """Virtual hosts mapped on at least one standard HTTPS listener, in order of appearance."""
    vhosts = []
    for block in _standard_listeners(config):
        for line in block.splitlines():
            entry = _map_entry(line)
            if entry and entry[0] not in vhosts:
                vhosts.append(entry[0])
    return vhosts


def reconcile_https_listener_maps(config, certified):
    """Map each certified website on every standard HTTPS listener exactly once.

    `certified` holds the virtual hosts that present their own certificate. A
    name one standard listener maps to such a virtual host is mapped on the
    others too, and several map lines of one virtual host in a listener are
    folded into one. Nothing is added for a virtual host outside `certified`
    or without a definition, for a wildcard name, or for a name the listener
    already gives to another virtual host. Other listeners are not touched.

    Returns the configuration and the (listener, virtual host) pairs it completed.
    """
    wanted = OrderedDict()
    for block in _standard_listeners(config):
        for line in block.splitlines():
            entry = _map_entry(line)
            if entry:
                names = wanted.setdefault(entry[0], [])
                names.extend(name for name in entry[1] if name not in names)
    defined = set(re.findall(r'(?mi)^[ \t]*virtualhost[ \t]+([^\s{]+)', config))
    completed = []

    def update(match):
        block = match.group(0)
        if not _is_standard_listener(block):
            return block
        listener = re.match(r'\s*listener\s+([^\n{]+?)\s*\{', block).group(1)
        lines = block.splitlines(True)
        routes = OrderedDict()
        position = {}
        rewrite = set()
        for index, line in enumerate(lines):
            entry = _map_entry(line)
            if entry is None:
                continue
            vhost, names = entry
            if vhost not in position:
                position[vhost] = index
                routes[vhost] = names
                continue
            extra = [name for name in names if name not in routes[vhost]]
            if extra:
                routes[vhost].extend(extra)
                rewrite.add(vhost)
            lines[index] = ''
        owner = {}
        for vhost, names in routes.items():
            for name in names:
                owner.setdefault(name, vhost)
        for vhost, names in wanted.items():
            if vhost not in certified or vhost not in defined:
                continue
            missing = [name for name in names
                       if '*' not in name and name not in routes.get(vhost, ())
                       and owner.setdefault(name, vhost) == vhost]
            if not missing:
                continue
            if vhost in routes:
                routes[vhost].extend(missing)
                rewrite.add(vhost)
            else:
                lines.insert(len(lines) - 1, _MAP_LINE % (vhost, ', '.join(missing)) + '\n')
            completed.append((listener, vhost))
        for vhost in rewrite:
            index = position[vhost]
            lines[index] = _rewritten_map_line(lines[index], vhost, routes[vhost])
        return ''.join(lines)

    return re.sub(_LISTENER_PATTERN, update, config, flags=re.MULTILINE), completed


def _resolved(path, vhost, server_root):
    return path.replace('$VH_NAME', vhost).replace('$SERVER_ROOT', server_root)


def plan_listener_repair(server_root=SERVER_ROOT, certificate_root=CERTIFICATE_ROOT):
    """Work out what completes the HTTPS listener maps of this server.

    A website mapped on a standard HTTPS listener counts as certified when its
    vhssl block names files that exist. One without a vhssl block is served
    with the certificate of whichever listener maps it, and gets the block
    when its own certificate is in `certificate_root`.

    Returns ({path: (current text, repaired text)}, completed pairs) and writes nothing.
    """
    config_path = os.path.join(server_root, MAIN_CONFIG)
    with open(config_path) as source:
        config = source.read()
    changes = OrderedDict()
    certified = set()
    for vhost in https_listener_vhosts(config):
        if vhost in ('.', '..') or os.path.basename(vhost) != vhost:
            continue
        path = os.path.join(server_root, 'conf/vhosts', vhost, 'vhost.conf')
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        with open(path) as source:
            current = source.read()
        files = certificate_files(current)
        if files is None:
            files = tuple(os.path.join(certificate_root, vhost, name)
                          for name in ('privkey.pem', 'fullchain.pem'))
            repaired = ensure_vhost_certificate(current, vhost, certificate_root)
        else:
            files = tuple(_resolved(name, vhost, server_root) for name in files)
            repaired = current
        if not all('$' in name or os.path.isfile(name) for name in files):
            continue
        certified.add(vhost)
        if repaired != current:
            changes[path] = (current, repaired)
    updated, completed = reconcile_https_listener_maps(config, certified)
    if updated != config:
        changes[config_path] = (config, updated)
    return changes, completed


def install_vhost_certificate(domain, server_root=SERVER_ROOT, certificate_root=CERTIFICATE_ROOT):
    """Serve `domain` with its certificate on every HTTPS listener.

    Runs each time a certificate is installed for a website. Creating a
    listener changes which certificate unmapped names get there, so the
    websites that were already served over HTTPS are completed as well.
    """
    vhost_path = os.path.join(server_root, 'conf/vhosts', domain, 'vhost.conf')
    if not os.path.isfile(vhost_path):
        raise ValueError('Website configuration not found: ' + vhost_path)
    rewrite_config(vhost_path, lambda config: ensure_vhost_certificate(config, domain, certificate_root))
    rewrite_config(os.path.join(server_root, MAIN_CONFIG),
                   lambda config: ensure_https_listeners(config, domain, certificate_root))
    changes, _ = plan_listener_repair(server_root, certificate_root)
    for path, (_, repaired) in changes.items():
        rewrite_config(path, lambda _, repaired=repaired: repaired)
