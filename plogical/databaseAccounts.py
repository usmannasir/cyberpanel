"""Which database accounts the panel creates, changes or removes, and for whom.

A database server has three kinds of account next to each other:

  * accounts of the server and of the panel itself (root, mysql, cyberpanel,
    the administrative account of a remote database server, ...);
  * the account phpMyAdmin signs a panel user in with. It is named after the
    user's number (cp-pma-<id>): a customer's database user can never have
    that name, because such names are letters, numbers and underscores only;
  * the database users customers create for their websites.

Only the third kind is ever acted on for a customer, and only under the exact
name the panel registered. Names are compared in Python, because the panel's
own tables compare text without regard to case while the database server
tells `Shop_user` and `shop_user` apart.
"""

PHPMYADMIN_PREFIX = 'cp-pma-'

# Accounts of the database server and of the panel, in lower case.
SYSTEM_ACCOUNTS = frozenset((
    'root', 'mysql', 'mariadb.sys', 'mysql.sys', 'mysql.session', 'mysql.infoschema',
    'debian-sys-maint', 'public', 'cyberpanel', 'rdsadmin',
))


def is_system_account(name):
    """True for a name of the server, of the panel, or in the phpMyAdmin namespace."""
    if not isinstance(name, str) or not name:
        return True
    lowered = name.lower()
    return lowered in SYSTEM_ACCOUNTS or lowered.startswith(PHPMYADMIN_PREFIX)
