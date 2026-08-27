import ipaddress
import socket


def _address_is_private(address):
    parsed = ipaddress.ip_address(str(address).split('%', 1)[0])
    return parsed.is_private or parsed.is_link_local


def callback_ip_for_remote(remote_host, configured_ip):
    """Return the local address used to reach a private remote panel."""
    try:
        addresses = socket.getaddrinfo(
            remote_host,
            8090,
            socket.AF_UNSPEC,
            socket.SOCK_DGRAM,
        )
    except (OSError, ValueError):
        return configured_ip

    for family, socket_type, protocol, _canonical_name, remote_address in addresses:
        try:
            if not _address_is_private(remote_address[0]):
                continue
            route_socket = socket.socket(family, socket_type, protocol)
            try:
                route_socket.connect(remote_address)
                local_address = route_socket.getsockname()[0]
            finally:
                route_socket.close()
            if _address_is_private(local_address):
                return local_address
        except (OSError, ValueError):
            continue

    return configured_ip
