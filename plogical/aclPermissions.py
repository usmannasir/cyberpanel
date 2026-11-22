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


def granted(value):
    """Whether a submitted value switches something on: only true or 1 does."""
    return value is True or (type(value) is int and value == 1)


def stored_config(submitted, admin):
    """The configuration to store with an ACL, built from what a form submitted.

    Every permission is written out. One that the request does not carry, or carries as
    anything other than true or 1, is stored as not granted. Nothing else the request
    carries is stored.
    """
    config = {'adminStatus': 1 if granted(admin) else 0}
    for name in PERMISSIONS:
        config[name] = 1 if granted(submitted.get(name)) else 0
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
