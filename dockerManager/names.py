import re

## Docker's own rules for the names it accepts, applied before a name from the
## address of a page is looked up or written into a page.

CONTAINER_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')
IMAGE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*(:[0-9]+)?(/[A-Za-z0-9][A-Za-z0-9._-]*)*')
IMAGE_TAG = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}')
PORT_PROTOCOLS = ('tcp', 'udp', 'sctp')


def valid_container_name(name):
    return isinstance(name, str) and len(name) <= 255 and CONTAINER_NAME.fullmatch(name) is not None


def valid_image_name(image):
    return isinstance(image, str) and len(image) <= 255 and IMAGE_NAME.fullmatch(image) is not None


def valid_image_tag(tag):
    return isinstance(tag, str) and IMAGE_TAG.fullmatch(tag) is not None


def exposed_ports(image_config):
    """The ports an image exposes as {port: protocol}, without entries that are not a port."""
    ports = {}
    for item in (image_config or {}).get('ExposedPorts') or {}:
        port, _, protocol = str(item).partition('/')
        protocol = protocol or 'tcp'
        if re.fullmatch('[0-9]{1,5}', port) and 0 < int(port) < 65536 and protocol in PORT_PROTOCOLS:
            ports[port] = protocol
    return ports
