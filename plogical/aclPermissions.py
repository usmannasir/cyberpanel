"""The permissions an ACL carries, and how they are stored and read.

This is the one list of them. The Create ACL and Modify ACL pages show a checkbox for
each name, their controllers send each name, and the configuration stored with an ACL
holds a value for each name.
"""

PERMISSIONS = (
    'versionManagement',

    ## User Management
    'createNewUser',
    'listUsers',
    'resellerCenter',
    'deleteUser',
    'changeUserACL',

    ## Website Management
    'createWebsite',
    'modifyWebsite',
    'suspendWebsite',
    'deleteWebsite',

    ## Package Management
    'createPackage',
    'listPackages',
    'deletePackage',
    'modifyPackage',

    ## Database Management
    'createDatabase',
    'deleteDatabase',
    'listDatabases',

    ## DNS Management
    'createNameServer',
    'createDNSZone',
    'deleteZone',
    'addDeleteRecords',

    ## Email Management
    'createEmail',
    'listEmails',
    'deleteEmail',
    'emailForwarding',
    'changeEmailPassword',
    'dkimManager',

    ## FTP Management
    'createFTPAccount',
    'deleteFTPAccount',
    'listFTPAccounts',

    ## Backup Management
    'createBackup',
    'googleDriveBackups',
    'restoreBackup',
    'addDeleteDestinations',
    'scheduleBackups',
    'remoteBackups',

    ## SSL Management
    'manageSSL',
    'hostnameSSL',
    'mailServerSSL',

    ## AI Scanner
    'aiScannerAccess',
)

# Permissions that were added when ACLs were already in use. A stored configuration from
# before does not carry them, and the users of such an ACL keep the value given here.
ABSENT_FROM_OLDER_ACLS = {'aiScannerAccess': 1}


# The ways a request may say yes or no. Words are accepted in any case.
SWITCH_WORDS = {'1': True, 'true': True, '0': False, 'false': False}


def switched_on(name, value):
    """Whether a submitted value says yes for the permission or admin status called name.

    Yes is true, 1, "1" or "true"; no is false, 0, "0" or "false". Any other value is
    refused, naming the key: a value that is not understood is never taken for a no,
    because a no takes access away from every user of the ACL.
    """
    if value is True or value is False:
        return value
    if type(value) is int and value in (0, 1):
        return value == 1
    if isinstance(value, str) and value.lower() in SWITCH_WORDS:
        return SWITCH_WORDS[value.lower()]
    raise ValueError('The value sent for "%s" is not understood. Send true or false.' % name)


def stored_config(submitted, admin_key):
    """The configuration to store with an ACL, built from what a form submitted.

    admin_key is the name under which the request says whether this is an admin ACL;
    the request has to carry it. Every permission is written out, and one that the
    request does not carry is stored as not granted. A value that is not a yes or a no
    refuses the whole request. Nothing else the request carries is stored.
    """
    if not isinstance(submitted, dict) or admin_key not in submitted:
        raise ValueError('The request does not carry "%s".' % admin_key)
    config = {'adminStatus': 1 if switched_on(admin_key, submitted[admin_key]) else 0}
    for name in PERMISSIONS:
        config[name] = 1 if name in submitted and switched_on(name, submitted[name]) else 0
    return config


def stored_permission(config, name):
    """What a stored configuration says about one permission; one it does not carry is not granted."""
    return config.get(name, ABSENT_FROM_OLDER_ACLS.get(name, 0))


def effective_config(config):
    """A stored configuration with every permission present, at the value that is in force."""
    effective = dict(config)
    for name in PERMISSIONS:
        effective[name] = stored_permission(config, name)
    return effective
