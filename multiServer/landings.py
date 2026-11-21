"""Peer navigation accepts symbolic destinations only. Object IDs always stay on their owner."""
PAGES = frozenset('''
index loadWebsitesHome createWebsite listWebsites listChildDomains CreateNewDomain createWordpress
ListWPSites ConfigurePlugins Addnewplugin CreateDockerPackage CreateDockersite AssignPackage ListDockerSites RemoteBackupConfig
loadDatabaseHome createDatabase listDBs remoteAccess loadEmailHome createEmailAccount listEmails
emailForwarding patternForwarding catchAllEmail dnsHome createNameserver createDNSZone
addDeleteDNSRecords addDeleteDNSRecordsCloudFlare loadFTPHome createFTPAccount listFTPAccounts
packagesHome createPackage listPackages loadUsersHome createUser listUsers createNewACL
CreatePackageCL listPackagesCL loadBackupHome backupSite backupDestinations scheduleBackup gDrive
OneClickBackups createBackupInc backupDestinationsInc scheduleBackupsInc
ConfigureV2Backup CreateV2Backup schedulev2Backups dockerHome containerImage manageImages listContainers
emailMarketing composeEmailMessage
loadSSLHome manageSSL v2ManageSSL dkimManager sendEmails deleteWebsite modifyWebsite siteState
modifyPackage deletePackage deleteFTPAccount deleteDatabase deleteEmailAccount changeEmailAccountPassword
plusAddressingSettings configureDefaultNameServers backupLogs restoreSite remoteBackups
monitorUsage emailDeliveryHome aiScannerHome
'''.split())

HUBS = frozenset('email data backups access server security settings'.split())
PAGES = PAGES.union('hub-' + section for section in HUBS)


def path(page):
    from django.urls import reverse
    if page not in PAGES:
        raise ValueError
    if page.startswith('hub-'):
        return reverse('cpHub', kwargs={'section': page[4:]})
    return reverse(page)


# These pages need an object or image chosen on the destination. Never reuse a query or
# URL argument, even when both panels happen to contain an object with the same name.
PICKERS = dict.fromkeys('''
siteWorkspace domain launchChild listCron domainAlias wordpressInstall joomlaInstall installPrestaShop
installMagento installMautic setupStaging setupGit manageGIT sshAccess
'''.split(), 'listWebsites')
PICKERS.update(dict.fromkeys('WPHome RestoreHome'.split(), 'ListWPSites'))
PICKERS.update(createEmailList='emailMarketing', manageLists='emailMarketing', manageSMTP='emailMarketing',
               ManageOCBackups='OneClickBackups', EidtPlugin='ConfigurePlugins', BackupfileConfig='RemoteBackupConfig', AddRemoteBackupsite='RemoteBackupConfig', runContainer='containerImage',
               Dockersitehome='ListDockerSites', viewContainer='listContainers')

# Shared base layout also serves unrelated, privileged and plugin pages. An unknown page
# can only open the peer dashboard. Never infer a landing from a view's URL or its name.
def destination(name, kwargs=None):
    if name == 'cpHub' and (kwargs or {}).get('section') in HUBS:
        return 'hub-' + kwargs['section']
    if name == 'multiServerInventory':
        return {'websites': 'listWebsites', 'databases': 'listDBs', 'mail': 'listEmails'}.get(
            (kwargs or {}).get('category'), 'index')
    return name if name in PAGES else PICKERS.get(name, 'index')


CREATE_PAGES = frozenset('''
createWebsite CreateNewDomain createWordpress CreateDockerPackage CreateDockersite AssignPackage
createDatabase remoteAccess createEmailAccount emailForwarding patternForwarding catchAllEmail
createNameserver createDNSZone addDeleteDNSRecords addDeleteDNSRecordsCloudFlare createFTPAccount
createPackage createUser createNewACL CreatePackageCL backupSite backupDestinations scheduleBackup
gDrive OneClickBackups ManageOCBackups createBackupInc backupDestinationsInc scheduleBackupsInc ConfigureV2Backup
CreateV2Backup schedulev2Backups createEmailList manageSMTP manageLists composeEmailMessage
emailDeliveryHome aiScannerHome emailMarketing sendEmails dkimManager Dockersitehome viewContainer RemoteBackupConfig AddRemoteBackupsite Addnewplugin WPHome ConfigurePlugins BackupfileConfig
runContainer manageImages containerImage siteWorkspace launchChild domain domainAlias listCron
wordpressInstall joomlaInstall installPrestaShop installMagento installMautic setupGit manageGIT setupStaging
'''.split())


def native_allowed(match):
    """Keep secondary logins, the firewall, account settings and controller controls local."""
    app = match.func.__module__.split('.')[0]
    name = match.url_name
    if app == 'aiScanner':
        return match.func.__module__ == 'aiScanner.scheduled_views' or name in ('aiScannerHome', 'aiScannerStartScan')
    if app == 'userManagment':
        return name in ('loadUsersHome', 'listUsers', 'fetchTableUsers', 'createUser', 'submitUserCreation',
                        'createNewACL', 'createACLFunc')
    if app == 'loginSystem':
        return name == 'logout'
    if app == 'baseTemplate':
        return name in ('index', 'cpHub', 'getDashboardStats', 'getTrafficStats', 'getDiskIOStats',
                        'getCPULoadGraph', 'getSystemInformation', 'getLoadAverage', 'getthemedata')
    if app in ('websiteFunctions', 'databases', 'dockerManager'):
        return name not in ('AutoLogin', 'phpMyAdmin', 'generateAccess', 'consumePHPMYAdminHandoff',
                            'validatePHPMYAdminSession', 'sshAccess', 'saveSSHAccessChanges', 'getSSHConfigs',
                            'deleteSSHKey', 'addSSHKey', 'get_terminal_jwt', 'executeContainerCommand')
    return app in ('mailServer', 'ftp', 'dns', 'backup', 'IncBackups', 'packages', 'CLManager',
                   'emailMarketing', 'emailPremium', 'emailDelivery', 'manageSSL')
