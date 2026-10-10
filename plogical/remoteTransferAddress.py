import ipaddress
import socket


_PRIVATE_IPV4_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
))


def callback_address(remote_host, configured_address):
    """Use the routed callback for public or RFC1918 private-network peers.

    A private source can send backups back over the private route. For a public
    source reached through NAT, keep the configured public callback instead of
    advertising a local private address the source cannot reach.
    """
    try:
        for family, _, _, _, destination in socket.getaddrinfo(
                remote_host, 8090, type=socket.SOCK_DGRAM):
            with socket.socket(family, socket.SOCK_DGRAM) as route:
                route.connect(destination)
                local_address = route.getsockname()[0]
            remote_ip = ipaddress.ip_address(destination[0])
            local_ip = ipaddress.ip_address(local_address)
            if remote_ip.is_global and local_ip.is_global:
                return local_address
            # is_private also includes loopback, link-local and other special
            # ranges; only RFC1918 addresses qualify for a private callback.
            if (any(remote_ip in network for network in _PRIVATE_IPV4_NETWORKS) and
                    any(local_ip in network for network in _PRIVATE_IPV4_NETWORKS)):
                return local_address
    except (OSError, ValueError):
        pass
    return configured_address
