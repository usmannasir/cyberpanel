"""The address at which this panel asks the scanner platform to call it back for a scan."""
from urllib.parse import urlsplit

from plogical.acl import ACLManager
from plogical.securityUtils import is_safe_hostname


def panel_port():
    """The port the panel listens on."""
    try:
        from plogical.processUtilities import ProcessUtilities
        port = str(ProcessUtilities.fetchCurrentPort()).strip()
    except Exception:
        port = ''
    return port if port.isdigit() and 0 < int(port) < 65536 else '8090'


def names_a_website(hostname):
    from websiteFunctions.models import ChildDomains, Websites
    return Websites.objects.filter(domain=hostname).exists() or \
        ChildDomains.objects.filter(domain=hostname).exists()


def panel_address(request, admin, currentACL):
    """host[:port] at which the scanner platform is asked to call this panel back for a scan.

    For a user who is not an administrator it is always the server's own
    address and the panel's port: the platform's calls carry what belongs
    to the server, and where a name leads is decided by whoever owns it,
    which may be another user of this panel.

    An administrator runs the server. For one, the host a request names is
    used when it is this server's own address or the name of a website on
    this panel, and its port when it is the panel's port or the default one.
    Anything else is replaced by the server's own address and the panel's
    port, where the panel always answers.
    """
    server = ACLManager.fetchIP()
    port = panel_port()
    own = '%s:%s' % (server, port)
    if currentACL.get('admin') != 1:
        return own
    try:
        host = request.get_host()
        parts = urlsplit('//' + host)
        hostname = (parts.hostname or '').lower()
        given_port = parts.port
        if parts.username or parts.password or parts.path or parts.query or parts.fragment:
            return own
    except Exception:
        return own
    if given_port is not None and str(given_port) not in (port, '443'):
        return own
    if hostname != server and (not is_safe_hostname(hostname) or not names_a_website(hostname)):
        return own
    return hostname if given_port is None else '%s:%d' % (hostname, given_port)
