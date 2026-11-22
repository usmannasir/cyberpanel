"""The name of the system account a website runs as."""
import os
import re
from random import randint

# What useradd takes as an account name.
PORTABLE_NAME = re.compile(r'[A-Za-z0-9_.][A-Za-z0-9_.-]{0,31}')
# What adduser of the Debian family takes (its NAME_REGEX): no capital letter.
DEBIAN_NAME = re.compile(r'[a-z][-a-z0-9_]*')


def acceptable(name, debian=None):
    """True when this server's own tool creates an account of this name."""
    if debian is None:
        debian = os.path.exists('/etc/adduser.conf')
    if not isinstance(name, str) or PORTABLE_NAME.fullmatch(name) is None:
        return False
    return DEBIAN_NAME.fullmatch(name) is not None if debian else True


def new_name(domain, taken, number=randint):
    """The account name of a new website: up to five letters of its domain, in lower case, and four digits.

    taken says whether a name is in use; a counter is added to the name
    until it is not.
    """
    base = ''.join(re.findall('[a-zA-Z]+', domain))[:5].lower() + str(number(1000, 9999))
    name, counter = base, 0
    while taken(name):
        name = '%s%s' % (base, counter)
        counter += 1
    return name


def renamed_in_configuration(text, old, new):
    """A web server configuration from a backup, naming the account the restored website has here.

    The name stands alone (extUser, extGroup) or begins a longer name the
    panel made from it (the PHP process and its socket); other words that
    merely contain it are left.
    """
    if not old or old == new:
        return text
    return re.sub(r'(?<![A-Za-z0-9_.-])%s(?![A-Za-z_-])' % re.escape(old), new.replace('\\', r'\\'), text)


def restored_name(stored, domain, taken, debian=None):
    """The account name of a website that is created from a backup.

    It keeps the name it had. A name this server's tool refuses (one with a
    capital letter on the Debian family) would leave the website without
    its account, so such a website gets a name as a new website does.
    """
    return stored if acceptable(stored, debian) else new_name(domain, taken)
