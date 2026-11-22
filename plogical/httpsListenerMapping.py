"""Serve every website's own certificate on all HTTPS listeners of OpenLiteSpeed.

OpenLiteSpeed chooses the certificate of a TLS connection through the listener
that accepted it: a name the listener maps to a virtual host gets that virtual
host's vhssl certificate, and any other name gets the listener's own. IPv4 and
IPv6 are separate listeners, so a website has to be mapped on both and has to
carry its certificate in its own vhssl block.

The functions that take and return configuration text do no I/O.
"""
import io
import locale
import os
import re
from collections import OrderedDict

from plogical.domainAliasUtilities import (
    _LISTENER_PATTERN, _is_secure_listener, ensure_https_vhost_mapping, has_https_listener,
)
from plogical.httpListenerMapping import read_config, rewrite_config

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
    content = line.rstrip('\r\n')
    suffix = ('  #' + content.partition('#')[2]) if '#' in content else ''
    return _MAP_LINE % (vhost, ', '.join(names)) + suffix + line[len(content):]


def _in_line_endings_of(config, text):
    """`text` with the line endings the configuration uses."""
    return text.replace('\n', '\r\n') if '\r\n' in config else text


def ensure_https_listeners(config, domain, certificate_root=CERTIFICATE_ROOT):
    """Give the server an IPv4 and an IPv6 HTTPS listener and map `domain` on every HTTPS listener.

    A listener that is missing is created with the certificate of `domain`,
    which then answers names that listener does not map.
    """
    values = {'domain': domain, 'certificates': certificate_root}
    if not has_https_listener(config):
        config += _in_line_endings_of(config, _LISTENER % dict(values, name='SSL', address='*:443'))
    if not has_https_listener(config, ipv6=True):
        config += _in_line_endings_of(config, _LISTENER % dict(values, name='SSL IPv6', address='[ANY]:443'))
    return ensure_https_vhost_mapping(config, domain)


def ensure_vhost_certificate(vhost_config, domain, certificate_root=CERTIFICATE_ROOT):
    """Give a virtual host a vhssl block for its own certificate unless it has one."""
    if certificate_files(vhost_config) is not None:
        return vhost_config
    return vhost_config + _in_line_endings_of(
        vhost_config, _VHSSL % {'domain': domain, 'certificates': certificate_root})


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
                lines.insert(len(lines) - 1, _in_line_endings_of(
                    block, _MAP_LINE % (vhost, ', '.join(missing)) + '\n'))
            completed.append((listener, vhost))
        for vhost in rewrite:
            index = position[vhost]
            lines[index] = _rewritten_map_line(lines[index], vhost, routes[vhost])
        return ''.join(lines)

    return re.sub(_LISTENER_PATTERN, update, config, flags=re.MULTILINE), completed


def certificate_serves(path, name):
    """Whether the certificate in a PEM file is within its validity period and names `name`.

    A certificate that names itself as its issuer counts like any other: the
    panel installs such a one when no public certificate can be issued.
    """
    from datetime import datetime, timezone
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509.oid import NameOID
    with open(path, 'rb') as source:
        certificate = x509.load_pem_x509_certificate(source.read(), default_backend())
    if hasattr(certificate, 'not_valid_after_utc'):
        period = certificate.not_valid_before_utc, certificate.not_valid_after_utc
        now = datetime.now(timezone.utc)
    else:
        period = certificate.not_valid_before, certificate.not_valid_after
        now = datetime.utcnow()
    if not period[0] <= now < period[1]:
        return False
    names = [attribute.value for attribute in certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)]
    try:
        alternative = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        names.extend(alternative.value.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        pass
    name = name.lower()
    parent = name.partition('.')[2]
    return any(pattern.lower() in (name, '*.' + parent) for pattern in names)


def _vhost_config_path(server_root, vhost):
    return os.path.join(server_root, 'conf/vhosts', vhost, 'vhost.conf')


def classify_listener_vhosts(config, server_root, certificate_root, report):
    """Sort the websites the standard HTTPS listeners map by how they get their certificate.

    Returns (certified, lacking). A certified website has a vhssl block that
    names files which exist. A lacking one has no vhssl block, so it answers
    with the certificate of whichever listener maps it, although a
    certificate that is in date and names it is in `certificate_root`. Any
    other website is in neither: nothing says which certificate it should
    present. One that cannot be examined is reported and left out.
    """
    certified, lacking = set(), []
    for vhost in https_listener_vhosts(config):
        if vhost in ('.', '..') or os.path.basename(vhost) != vhost:
            continue
        try:
            path = _vhost_config_path(server_root, vhost)
            if not os.path.isfile(path):
                continue
            files = certificate_files(read_config(path))
            if files is None:
                key, certificate = (os.path.join(certificate_root, vhost, name)
                                    for name in ('privkey.pem', 'fullchain.pem'))
                if os.path.isfile(key) and os.path.isfile(certificate) and certificate_serves(certificate, vhost):
                    lacking.append(vhost)
            elif all('$' in name or os.path.isfile(name) for name in (
                    name.replace('$VH_NAME', vhost).replace('$SERVER_ROOT', server_root) for name in files)):
                certified.add(vhost)
        except Exception as error:
            report('%s was not examined: %s' % (vhost, error))
    return certified, lacking


def complete_https_listeners(server_root=SERVER_ROOT, certificate_root=CERTIFICATE_ROOT, report=None):
    """Complete the websites that are already served over HTTPS, each on its own.

    A lacking website gets its vhssl block, and every certified website is
    mapped on all standard HTTPS listeners. Each file is changed from the
    text it holds when it is written. A website whose file cannot be changed
    is reported and left as it is; the others are still completed.
    """
    report = report or _log
    main = os.path.join(server_root, MAIN_CONFIG)
    certified, lacking = classify_listener_vhosts(read_config(main), server_root, certificate_root, report)
    for vhost in lacking:
        try:
            rewrite_config(_vhost_config_path(server_root, vhost),
                           lambda text, vhost=vhost: ensure_vhost_certificate(text, vhost, certificate_root))
        except Exception as error:
            report('%s was left without its own certificate block: %s' % (vhost, error))
            continue
        certified.add(vhost)
    rewrite_config(main, lambda text: reconcile_https_listener_maps(text, certified)[0])


def install_vhost_certificate(domain, server_root=SERVER_ROOT, certificate_root=CERTIFICATE_ROOT, report=None):
    """Serve `domain` with its certificate on every HTTPS listener.

    Runs each time a certificate is installed for a website, and fails only
    for a reason that lies with that website or the listeners. Creating a
    listener changes which certificate unmapped names get there, so the
    websites that were already served over HTTPS are completed afterwards;
    that part is best effort and what it could not do is reported.
    """
    report = report or _log
    vhost_path = _vhost_config_path(server_root, domain)
    if not os.path.isfile(vhost_path):
        raise ValueError('Website configuration not found: ' + vhost_path)
    rewrite_config(vhost_path, lambda config: ensure_vhost_certificate(config, domain, certificate_root))
    rewrite_config(os.path.join(server_root, MAIN_CONFIG),
                   lambda config: ensure_https_listeners(config, domain, certificate_root))
    try:
        complete_https_listeners(server_root, certificate_root, report)
    except Exception as error:
        report('Other websites were not completed on the HTTPS listeners: %s' % error)


def _log(message):
    try:
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        CyberCPLogFileWriter.writeToFile('[HTTPS listeners] ' + message)
    except Exception:
        pass


class ChangeRefused(Exception):
    """A validated configuration change was not made and everything is as it was before."""


def _validated_change(path, transform):
    """(text, changed text) of a file for the upgrade's validated configuration change, or None.

    That change compares the first with the file read as text in the locale's
    encoding and writes the second encoded the same way, so the pair is built
    to match: the first as that read returns it, the second with every byte
    of the file kept apart from what the transform changed. A file that
    cannot be handed over this way raises ValueError.
    """
    if os.path.realpath(path) != os.path.abspath(path):
        raise ValueError('%s is reached through a symbolic link' % path)
    try:
        with open(path, 'rb') as source:
            data = source.read()
    except OSError as error:
        raise ValueError(str(error))
    exact = data.decode('utf-8', 'surrogateescape')
    changed = transform(exact)
    if changed == exact:
        return None
    encoding = locale.getpreferredencoding(False)
    try:
        before = io.TextIOWrapper(io.BytesIO(data), encoding=encoding).read()
        after = changed.encode('utf-8', 'surrogateescape').decode(encoding)
    except UnicodeError:
        raise ValueError('%s is not %s text' % (path, encoding))
    return before, after


def holds_original(changes):
    """Whether every file of a validated configuration change holds its text from before the change."""
    for path, (before, _) in changes.items():
        with open(path) as source:
            if source.read() != before:
                return False
    return True


def repair_https_listeners(apply, report, server_root=SERVER_ROOT, certificate_root=CERTIFICATE_ROOT):
    """Complete the HTTPS listeners of an existing server during an upgrade.

    `apply` makes one validated configuration change, given as
    {path: (text, changed text)}. It raises ChangeRefused when the change was
    not made and files and service are as before, and anything else when
    they could not be put back, which ends the repair with that error.

    The vhssl block of each lacking website is a change of its own, so a
    website whose file cannot be changed is reported and left as it is while
    the others are repaired. The listener maps follow as one change.

    Returns (completed (listener, virtual host) pairs, websites given a vhssl block).
    """
    main = os.path.join(server_root, MAIN_CONFIG)
    certified, lacking = classify_listener_vhosts(read_config(main), server_root, certificate_root, report)
    blocks = []
    for vhost in lacking:
        path = _vhost_config_path(server_root, vhost)
        try:
            change = _validated_change(
                path, lambda text, vhost=vhost: ensure_vhost_certificate(text, vhost, certificate_root))
        except ValueError as error:
            change = error
        if isinstance(change, tuple):
            try:
                apply({path: change})
                blocks.append(vhost)
            except ChangeRefused as error:
                change = error
        if isinstance(change, Exception):
            report('%s was left without its own certificate block: %s' % (vhost, change))
            continue
        certified.add(vhost)
    completed = []

    def reconciled(text):
        updated, completed[:] = reconcile_https_listener_maps(text, certified)
        return updated

    change = _validated_change(main, reconciled)
    if change is not None:
        apply({main: change})
    return completed, blocks
