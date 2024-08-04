from django.urls import path
from . import views

urlpatterns = [
    path('', views.loadWebsitesHome, name='loadWebsitesHome'),
    path('createWebsite', views.createWebsite, name='createWebsite'),
    path('listWebsites', views.listWebsites, name='listWebsites'),
    path('listChildDomains', views.listChildDomains, name='listChildDomains'),
    path('modifyWebsite', views.modifyWebsite, name='modifyWebsite'),
    path('deleteWebsite', views.deleteWebsite, name='deleteWebsite'),
    path('siteState', views.siteState, name='siteState'),

    # New domain
    path('CreateNewDomain', views.CreateNewDomain, name='CreateNewDomain'),

    # WordPress
    path('createWordpress', views.WPCreate, name='createWordpress'),
    path('ListWPSites', views.ListWPSites, name='ListWPSites'),
    path('WPHome', views.WPHome, name='WPHome'),
    path('RestoreBackups', views.RestoreBackups, name='RestoreBackups'),
    path('RestoreHome', views.RestoreHome, name='RestoreHome'),
    path('AutoLogin', views.AutoLogin, name='AutoLogin'),
    path('RemoteBackupConfig', views.RemoteBackupConfig, name='RemoteBackupConfig'),
    path('BackupfileConfig', views.BackupfileConfig, name='BackupfileConfig'),
    path('AddRemoteBackupsite', views.AddRemoteBackupsite, name='AddRemoteBackupsite'),
    path('pricing', views.WordpressPricing, name='pricing'),

    # WordPress Ajax
    path('submitWorpressCreation', views.submitWorpressCreation, name='submitWorpressCreation'),
    path('FetchWPdata', views.FetchWPdata, name='FetchWPdata'),
    path('GetCurrentPlugins', views.GetCurrentPlugins, name='GetCurrentPlugins'),
    path('GetCurrentThemes', views.GetCurrentThemes, name='GetCurrentThemes'),
    path('UpdateWPSettings', views.UpdateWPSettings, name='UpdateWPSettings'),
    path('UpdatePlugins', views.UpdatePlugins, name='UpdatePlugins'),
    path('DeletePlugins', views.DeletePlugins, name='DeletePlugins'),
    path('ChangeStatus', views.ChangeStatus, name='ChangeStatus'),
    path('UpdateThemes', views.UpdateThemes, name='UpdateThemes'),
    path('DeleteThemes', views.DeleteThemes, name='DeleteThemes'),
    path('StatusThemes', views.StatusThemes, name='StatusThemes'),
    path('CreateStagingNow', views.CreateStagingNow, name='CreateStagingNow'),
    path('fetchstaging', views.fetchstaging, name='fetchstaging'),
    path('fetchDatabase', views.fetchDatabase, name='fetchDatabase'),
    path('SaveUpdateConfig', views.SaveUpdateConfig, name='SaveUpdateConfig'),
    path('DeploytoProduction', views.DeploytoProduction, name='DeploytoProduction'),
    path('WPCreateBackup', views.WPCreateBackup, name='WPCreateBackup'),
    path('RestoreWPbackupNow', views.RestoreWPbackupNow, name='RestoreWPbackupNow'),
    path('dataintegrity', views.dataintegrity, name='dataintegrity'),
    path('installwpcore', views.installwpcore, name='installwpcore'),
    path('SaveBackupConfig', views.SaveBackupConfig, name='SaveBackupConfig'),
    path('SaveBackupSchedule', views.SaveBackupSchedule, name='SaveBackupSchedule'),
    path('AddWPsiteforRemoteBackup', views.AddWPsiteforRemoteBackup, name='AddWPsiteforRemoteBackup'),
    path('UpdateRemoteschedules', views.UpdateRemoteschedules, name='UpdateRemoteschedules'),
    path('ScanWordpressSite', views.ScanWordpressSite, name='ScanWordpressSite'),

    # AddPlugin
    path('ConfigurePlugins', views.ConfigurePlugins, name='ConfigurePlugins'),
    path('Addnewplugin', views.Addnewplugin, name='Addnewplugin'),
    path('EidtPlugin', views.EidtPlugin, name='EidtPlugin'),

    # AddPlugin Ajax
    path('SearchOnkeyupPlugin', views.SearchOnkeyupPlugin, name='SearchOnkeyupPlugin'),
    path('AddNewpluginAjax', views.AddNewpluginAjax, name='AddNewpluginAjax'),
    path('deletesPlgin', views.deletesPlgin, name='deletesPlgin'),
    path('Addplugineidt', views.Addplugineidt, name='Addplugineidt'),

    # Website modification
    path('submitWebsiteCreation', views.submitWebsiteCreation, name='submitWebsiteCreation'),
    path('submitWebsiteDeletion', views.submitWebsiteDeletion, name='submitWebsiteDeletion'),
    path('submitWebsiteListing', views.getFurtherAccounts, name='submitWebsiteListing'),
    path('fetchWebsitesList', views.fetchWebsitesList, name='fetchWebsitesList'),
    path('fetchChildDomainsMain', views.fetchChildDomainsMain, name='fetchChildDomainsMain'),
    path('convertDomainToSite', views.convertDomainToSite, name='convertDomainToSite'),
    path('searchWebsites', views.searchWebsites, name='searchWebsites'),
    path('submitWebsiteModification', views.deleteWebsite, name='submitWebsiteModification'),
    path('submitWebsiteStatus', views.submitWebsiteStatus, name='submitWebsiteStatus'),
    path('getWebsiteDetails', views.submitWebsiteModify, name='getWebsiteDetails'),
    path('saveWebsiteChanges', views.saveWebsiteChanges, name='saveWebsiteChanges'),
    path('getDataFromLogFile', views.getDataFromLogFile, name='getDataFromLogFile'),
    path('fetchErrorLogs', views.fetchErrorLogs, name='fetchErrorLogs'),
    path('getDataFromConfigFile', views.getDataFromConfigFile, name='getDataFromConfigFile'),
    path('saveConfigsToFile', views.saveConfigsToFile, name='saveConfigsToFile'),
    path('getRewriteRules', views.getRewriteRules, name='getRewriteRules'),
    path('saveRewriteRules', views.saveRewriteRules, name='saveRewriteRules'),
    path('saveSSL', views.saveSSL, name='saveSSL'),

    # Sub/add/park domains
    path('submitDomainCreation', views.submitDomainCreation, name='submitDomainCreation'),
    path('fetchDomains', views.fetchDomains, name='fetchDomains'),
    path('changePHP', views.changePHP, name='changePHP'),
    path('submitDomainDeletion', views.submitDomainDeletion, name='submitDomainDeletion'),
    path('searchChilds', views.searchChilds, name='searchChilds'),

    # Crons
    path('listCron', views.listCron, name='listCron'),
    path('getWebsiteCron', views.getWebsiteCron, name='getWebsiteCron'),
    path('getCronbyLine', views.getCronbyLine, name='getCronbyLine'),
    path('remCronbyLine', views.remCronbyLine, name='remCronbyLine'),
    path('saveCronChanges', views.saveCronChanges, name='saveCronChanges'),
    path('addNewCron', views.addNewCron, name='addNewCron'),

    # Domain Alias
    path('<domain>/domainAlias', views.domainAlias, name='domainAlias'),
    path('submitAliasCreation', views.submitAliasCreation, name='submitAliasCreation'),
    path('issueAliasSSL', views.issueAliasSSL, name='issueAliasSSL'),
    path('delateAlias', views.delateAlias, name='delateAlias'),

    # Openbasedir
    path('changeOpenBasedir', views.changeOpenBasedir, name='changeOpenBasedir'),

    # WP Install
    path('<domain>/wordpressInstall', views.wordpressInstall, name='wordpressInstall'),
    path('installWordpressStatus', views.installWordpressStatus, name='installWordpressStatus'),
    path('installWordpress', views.installWordpress, name='installWordpress'),

    # Joomla Install
    path('installJoomla', views.installJoomla, name='installJoomla'),
    path('<domain>/joomlaInstall', views.joomlaInstall, name='joomlaInstall'),

    # PrestaShop Install
    path('prestaShopInstall', views.prestaShopInstall, name='prestaShopInstall'),
    path('<domain>/installPrestaShop', views.installPrestaShop, name='installPrestaShop'),

    # Magento
    path('<domain>/installMagento', views.installMagento, name='installMagento'),
    path('magentoInstall', views.magentoInstall, name='magentoInstall'),

    # Mautic
    path('<domain>/installMautic', views.installMautic, name='installMautic'),
    path('mauticInstall', views.mauticInstall, name='mauticInstall'),

    # Git
    path('<domain>/setupGit', views.setupGit, name='setupGit'),
    path('setupGitRepo', views.setupGitRepo, name='setupGitRepo'),

    # Set up SSH Access
    path('<domain>/sshAccess', views.sshAccess, name='sshAccess'),
    path('saveSSHAccessChanges', views.saveSSHAccessChanges, name='saveSSHAccessChanges'),

    # Staging Environment
    path('<domain>/setupStaging', views.setupStaging, name='setupStaging'),
    path('startCloning', views.startCloning, name='startCloning'),
    path('<domain>/<childDomain>/syncToMaster', views.syncToMaster, name='syncToMaster'),
    path('startSync', views.startSync, name='startSync'),
    path('<domain>/gitNotify', views.gitNotify, name='gitNotify'),
    path('detachRepo', views.detachRepo, name='detachRepo'),
    path('changeBranch', views.changeBranch, name='changeBranch'),

    # Manage GIT
    path('<domain>/manageGIT', views.manageGIT, name='manageGIT'),
    path('<domain>/webhook', views.webhook, name='webhook'),
    path('fetchFolderDetails', views.fetchFolderDetails, name='fetchFolderDetails'),
    path('initRepo', views.initRepo, name='initRepo'),
    path('setupRemote', views.setupRemote, name='setupRemote'),
    path('changeGitBranch', views.changeGitBranch, name='changeGitBranch'),
    path('createNewBranch', views.createNewBranch, name='createNewBranch'),
    path('commitChanges', views.commitChanges, name='commitChanges'),
    path('gitPull', views.gitPull, name='gitPull'),
    path('gitPush', views.gitPush, name='gitPush'),
    path('attachRepoGIT', views.attachRepoGIT, name='attachRepoGIT'),
    path('removeTracking', views.removeTracking, name='removeTracking'),
    path('fetchGitignore', views.fetchGitignore, name='fetchGitignore'),
    path('saveGitIgnore', views.saveGitIgnore, name='saveGitIgnore'),
    path('fetchCommits', views.fetchCommits, name='fetchCommits'),
    path('fetchFiles', views.fetchFiles, name='fetchFiles'),
    path('fetchChangesInFile', views.fetchChangesInFile, name='fetchChangesInFile'),
    path('saveGitConfigurations', views.saveGitConfigurations, name='saveGitConfigurations'),
    path('fetchGitLogs', views.fetchGitLogs, name='fetchGitLogs'),

    # Docker Site & Packages
    path('CreateDockerPackage', views.CreateDockerPackage, name='CreateDockerPackage'),
    path('AssignPackage', views.AssignPackage, name='AssignPackage'),
    path('CreateDockersite', views.CreateDockersite, name='CreateDockersite'),
    path('AddDockerpackage', views.AddDockerpackage, name='AddDockerpackage'),
    path('Getpackage', views.Getpackage, name='Getpackage'),
    path('Updatepackage', views.Updatepackage, name='Updatepackage'),
    path('AddAssignment', views.AddAssignment, name='AddAssignment'),
    path('submitDockerSiteCreation', views.submitDockerSiteCreation, name='submitDockerSiteCreation'),
    path('ListDockerSites', views.ListDockerSites, name='ListDockerSites'),
    path('fetchDockersite', views.fetchDockersite, name='fetchDockersite'),

    # SSH Configs
    path('getSSHConfigs', views.getSSHConfigs, name='getSSHConfigs'),
    path('deleteSSHKey', views.deleteSSHKey, name='deleteSSHKey'),
    path('addSSHKey', views.addSSHKey, name='addSSHKey'),

    # Apache Manager
    path('ApacheManager/<domain>', views.ApacheManager, name='ApacheManager'),
    path('getSwitchStatus', views.getSwitchStatus, name='getSwitchStatus'),
    path('switchServer', views.switchServer, name='switchServer'),
    path('statusFunc', views.statusFunc, name='statusFunc'),
    path('tuneSettings', views.tuneSettings, name='tuneSettings'),
    path('saveApacheConfigsToFile', views.saveApacheConfigsToFile, name='saveApacheConfigsToFile'),

    # Catch all for domains
    path('<domain>/<childDomain>', views.launchChild, name='launchChild'),
    path('<domain>', views.domain, name='domain'),
]
