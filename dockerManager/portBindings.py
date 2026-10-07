"""Validate explicit Docker host bindings while preserving legacy API clients."""
import ipaddress
import re


def build_port_bindings(exposed_ports, data):
    explicit = 'hostIP' in data
    host_ip = data.get('hostIP')
    if explicit:
        if not isinstance(host_ip, str) or '%' in host_ip:
            raise ValueError('Enter a valid Host IP address (IPv4 or IPv6).')
        try:
            address = ipaddress.ip_address(host_ip.strip())
        except ValueError:
            raise ValueError('Enter a valid Host IP address (IPv4 or IPv6).')
        if address.is_multicast or str(address) == '255.255.255.255':
            raise ValueError('Host IP must be a local interface address or a wildcard address.')
        host_ip = str(address)
    bindings = {}
    for port in exposed_ports or {}:
        value = data.get(port)
        if value is None or value == '':
            if explicit:
                raise ValueError('Choose a host port for %s.' % port)
            continue
        if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
            raise ValueError('Invalid port number for %s.' % port)
        number = int(value)
        if not 1024 <= number <= 65535:
            raise ValueError('Choose port between 1024 and 65535.')
        # Dicts survive JSON persistence, unlike Docker SDK (host, port) tuples.
        bindings[port] = {'HostIp': host_ip, 'HostPort': str(number)} if explicit else value
    return bindings, not explicit


def publish_all_for_saved_bindings(bindings):
    """Keep legacy recreation behavior; explicit bindings never auto-publish."""
    return not any(isinstance(binding, dict) and 'HostIp' in binding
                   for binding in bindings.values())
