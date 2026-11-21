"""The address of a controller, as a managed server names it and recognises it.

There is one rule, and it is here. A managed server writes down the addresses
a controller may call from (ms_links.allowed_ips, and the one address a
pairing code is made for), and on every request it compares the address the
connection came from with what it wrote down. Both sides of that comparison
go through this module, so the two can never be read by different rules.

An address has one spelling:

    IPv4    dotted, as plainly written: no leading zeros, nothing around it
    IPv6    lower case, in its shortest form, without a zone

The address of a connection is taken as the web server reports it (peer). A
server that listens on both families reports an IPv4 caller as
::ffff:a.b.c.d, and that is the IPv4 address a.b.c.d.

What a person writes (entry) may spell IPv6 in any of its forms, and is kept
in the one spelling. IPv4 written as IPv6 is not an entry: write it as IPv4.

allowed_ips is one or more addresses, each in its one spelling, joined by ','
and nothing else: no space, no range, no name. A text with one entry that is
anything else allows nobody.
"""
import ipaddress

SEPARATOR = ','
MAX_ADDRESS = 45


def _parse(value):
    """(the one spelling, whether it was IPv4 written as IPv6) of one address, or None."""
    if type(value) is not str or len(value) > MAX_ADDRESS or '%' in value:
        return None
    try:
        parsed = ipaddress.ip_address(value)
        # Dotted numbers are read one way only, also at the end of an IPv6 address: older Pythons
        # take 010.0.0.1 for 10.0.0.1, and a resolver may take it for 8.0.0.1.
        dotted = value.rsplit(':', 1)[-1]
        if '.' in dotted and str(ipaddress.IPv4Address(dotted)) != dotted:
            return None
    except ValueError:
        return None
    if parsed.version == 4:
        return value, False
    if parsed.ipv4_mapped is not None:
        return str(parsed.ipv4_mapped), True
    return str(parsed), False


def peer(value):
    """The one spelling of the address a connection came from, or None when it is not one address."""
    parsed = _parse(value)
    return None if parsed is None else parsed[0]


def entry(value):
    """The one spelling of an address somebody wrote, or None when it is not one address written as itself."""
    parsed = _parse(value)
    return None if parsed is None or parsed[1] else parsed[0]


def listed(text):
    """The addresses that an allowed_ips text names; none unless every entry is in its one spelling."""
    found = []
    for written in text.split(SEPARATOR) if type(text) is str else ():
        if entry(written) != written:
            return ()
        found.append(written)
    return tuple(found)


def allows(text, came_from):
    """Whether a connection from `came_from` (as the web server reports it) is one that `text` allows."""
    address = peer(came_from)
    return address is not None and address in listed(text)


def joined(addresses):
    """The allowed_ips text for these addresses; ValueError unless each is in its one spelling."""
    try:
        addresses = tuple(addresses)
        text = SEPARATOR.join(addresses)
    except TypeError:
        text = ''
    if not text or listed(text) != addresses:
        raise ValueError('Only addresses in their one spelling are allowed.')
    return text
