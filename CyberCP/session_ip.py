"""Normalize the existing session IP binding without changing proxy trust."""
from ipaddress import ip_address


def session_ip_key(value):
    address = ip_address(value)
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if address.version == 4:
        return str(address)
    # Preserve CyberPanel's existing /48 IPv6 binding, independently of the
    # compressed spelling used by the web server or proxy.
    return ':'.join(address.exploded.split(':')[:3])


def session_ip_matches(stored, current):
    try:
        normalized = session_ip_key(current)
    except (ValueError, TypeError):
        return False
    if stored == normalized:
        return True
    # Sessions created before normalization stored the first three textual
    # IPv6 components. Accept that exact legacy spelling until the next login.
    address = ip_address(current)
    if address.version == 6 and address.ipv4_mapped is None:
        return stored == ':'.join(current.split(':')[:3])
    return False
