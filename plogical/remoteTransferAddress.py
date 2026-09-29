import ipaddress
import socket


def callback_address(remote_host, configured_address):
    """Use the address routed to the source when both ends are public.

    An install behind NAT may need its configured public address instead of
    the local interface address, so keep that address as the fallback.
    """
    try:
        for family, _, _, _, destination in socket.getaddrinfo(
                remote_host, 8090, type=socket.SOCK_DGRAM):
            with socket.socket(family, socket.SOCK_DGRAM) as route:
                route.connect(destination)
                local_address = route.getsockname()[0]
            if (ipaddress.ip_address(destination[0]).is_global and
                    ipaddress.ip_address(local_address).is_global):
                return local_address
    except (OSError, ValueError):
        pass
    return configured_address
