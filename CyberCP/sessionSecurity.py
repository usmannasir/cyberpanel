"""Shared address binding for panel logins and authenticated requests."""
import ipaddress


def get_client_ip(request):
    return request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')


def session_ip_key(address):
    """Bind IPv4 exactly and IPv6 to its /48, regardless of text notation."""
    try:
        parsed = ipaddress.ip_address(address)
    except (TypeError, ValueError):
        return None
    if isinstance(parsed, ipaddress.IPv6Address):
        if parsed.ipv4_mapped:
            return str(parsed.ipv4_mapped)
        return str(ipaddress.ip_network('%s/48' % parsed, strict=False))
    return str(parsed)


def session_ip_matches(stored, address):
    current = session_ip_key(address)
    if not stored or not current:
        return False
    if stored == current:
        return True
    # Pre-upgrade sessions stored only the first three colon-separated pieces.
    # Accept an unambiguous, complete three-hextet prefix. Compressed legacy
    # prefixes (notably ::ffff) lost information: require a fresh login.
    pieces = stored.split(':')
    if len(pieces) == 3 and all(pieces) and '/' not in stored:
        return session_ip_key(stored + '::') == current
    return False
