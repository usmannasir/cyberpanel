from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.loadWebsitesHome, name='loadWebsitesHome'),
    url(r'^createWebsite$', views.createWebsite, name='createWebsite'),
    url(r'^listWebsites$', views.listWebsites, name='listWebsites'),
    url(r'^listChildDomains$', views.listChildDomains, name='listChildDomains'),
    url(r'^modifyWebsite$', views.modifyWebsite, name='modifyWebsite'),
    url(r'^deleteWebsite$', views.deleteWebsite, name='deleteWebsite'),
    url(r'^siteState$', views.siteState, name='siteState'),

    ##

    url(r'^CreateNewDomain$', views.CreateNewDomain, name='CreateNewDomain'),


    ### WordPress
    url(r'^createWordpress$', views.WPCreate, name='createWordpress'),
    url(r'^ListWPSites$', views.ListWPSites, name='ListWPSites'),
    url(r'^WPHome$', views.WPHome, name='WPHome'),
    url(r'^RestoreBackups$', views.RestoreBackups, name='RestoreBackups'),
    url(r'^RestoreHome$', views.RestoreHome, name='RestoreHome'),
    url(r'^AutoLogin$', views.AutoLogin, name='AutoLogin'),
    url(r'^RemoteBackupConfig$', views.RemoteBackupConfig, name='RemoteBackupConfig'),
    url(r'^BackupfileConfig$', views.BackupfileConfig, name='BackupfileConfig'),
    url(r'^AddRemoteBackupsite$', views.AddRemoteBackupsite, name='AddRemoteBackupsite'),
    url(r'^pricing$', views.WordpressPricing, name='pricing'),


    ###WordPress Ajax
    url(r'^submitWorpressCreation', views.submitWorpressCreation, name='submitWorpressCreation'),
    url(r'^FetchWPdata', views.FetchWPdata, name='FetchWPdata'),
    url(r'^GetCurrentPlugins', views.GetCurrentPlugins, name='GetCurrentPlugins'),
    url(r'^GetCurrentThemes', views.GetCurrentThemes, name='GetCurrentThemes'),
    url(r'^UpdateWPSettings', views.UpdateWPSettings, name='UpdateWPSettings'),
    url(r'^UpdatePlugins', views.UpdatePlugins, name='UpdatePlugins'),
    url(r'^DeletePlugins', views.DeletePlugins, name='DeletePlugins'),
    url(r'^ChangeStatus', views.ChangeStatus, name='ChangeStatus'),
    url(r'^UpdateThemes', views.UpdateThemes, name='UpdateThemes'),
    url(r'^DeleteThemes', views.DeleteThemes, name='DeleteThemes'),
    url(r'^StatusThemes', views.StatusThemes, name='StatusThemes'),
    url(r'^CreateStagingNow', views.CreateStagingNow, name='CreateStagingNow'),
    url(r'^fetchstaging', views.fetchstaging, name='fetchstaging'),
    url(r'^fetchDatabase', views.fetchDatabase, name='fetchDatabase'),
    url(r'^SaveUpdateConfig', views.SaveUpdateConfig, name='SaveUpdateConfig'),
    url(r'^DeploytoProduction', views.DeploytoProduction, name='DeploytoProduction'),
    url(r'^WPCreateBackup', views.WPCreateBackup, name='WPCreateBackup'),
    url(r'^RestoreWPbackupNow', views.RestoreWPbackupNow, name='RestoreWPbackupNow'),
    url(r'^dataintegrity', views.dataintegrity, name='dataintegrity'),
    url(r'^installwpcore', views.installwpcore, name='installwpcore'),
    url(r'^SaveBackupConfig', views.SaveBackupConfig, name='SaveBackupConfig'),
    url(r'^SaveBackupSchedule', views.SaveBackupSchedule, name='SaveBackupSchedule'),
    url(r'^AddWPsiteforRemoteBackup', views.AddWPsiteforRemoteBackup, name='AddWPsiteforRemoteBackup'),
    url(r'^UpdateRemoteschedules', views.UpdateRemoteschedules, name='UpdateRemoteschedules'),
    url(r'^ScanWordpressSite', views.ScanWordpressSite, name='ScanWordpressSite'),




    #### AddPlugin
    url(r'^ConfigurePlugins$', views.ConfigurePlugins, name='ConfigurePlugins'),
    url(r'^Addnewplugin$', views.Addnewplugin, name='Addnewplugin'),
    url(r'^EidtPlugin$', views.EidtPlugin, name='EidtPlugin'),



    ## AddPlugin Ajax
    url(r'^SearchOnkeyupPlugin$', views.SearchOnkeyupPlugin, name='SearchOnkeyupPlugin'),
    url(r'^AddNewpluginAjax$', views.AddNewpluginAjax, name='AddNewpluginAjax'),
    url(r'^deletesPlgin', views.deletesPlgin, name='deletesPlgin'),
    url(r'^Addplugineidt', views.Addplugineidt, name='Addplugineidt'),


    # Website modification url


    url(r'^submitWebsiteCreation$', views.submitWebsiteCreation, name='submitWebsiteCreation'),
    url(r'^submitWebsiteDeletion$', views.submitWebsiteDeletion, name='submitWebsiteDeletion'),
    url(r'^submitWebsiteListing$', views.getFurtherAccounts, name='submitWebsiteListing'),
    url(r'^fetchWebsitesList$', views.fetchWebsitesList, name='fetchWebsitesList'),
    url(r'^fetchChildDomainsMain$', views.fetchChildDomainsMain, name='fetchChildDomainsMain'),
    url(r'^convertDomainToSite$', views.convertDomainToSite, name='convertDomainToSite'),
    url(r'^searchWebsites$', views.searchWebsites, name='searchWebsites'),
    url(r'^submitWebsiteModification$', views.deleteWebsite, name='submitWebsiteModification'),
    url(r'^submitWebsiteStatus$', views.submitWebsiteStatus, name='submitWebsiteStatus'),


    url(r'^getWebsiteDetails$', views.submitWebsiteModify, name='getWebsiteDetails'),
    url(r'^saveWebsiteChanges', views.saveWebsiteChanges, name='saveWebsiteChanges'),

    url(r'^getDataFromLogFile$', views.getDataFromLogFile, name='getDataFromLogFile'),
    url(r'^fetchErrorLogs$', views.fetchErrorLogs, name='fetchErrorLogs'),
    
    url(r'^getDataFromConfigFile$', views.getDataFromConfigFile, name='getDataFromConfigFile'),

    url(r'^saveConfigsToFile$', views.saveConfigsToFile, name='saveConfigsToFile'),


    url(r'^getRewriteRules$', views.getRewriteRules, name='getRewriteRules'),

    url(r'^saveRewriteRules$', views.saveRewriteRules, name='saveRewriteRules'),

    url(r'^saveSSL$', views.saveSSL, name='saveSSL'),

    ## sub/add/park domains

    url(r'^submitDomainCreation$', views.submitDomainCreation, name='submitDomainCreation'),

    ## fetch domains

    url(r'^fetchDomains$', views.fetchDomains, name='submitDomainCreation'),
    url(r'^changePHP$', views.changePHP, name='changePHP'),
    url(r'^submitDomainDeletion$', views.submitDomainDeletion, name='submitDomainDeletion'),
    url(r'^searchChilds$', views.searchChilds, name='searchChilds'),
    # crons

    url(r'^listCron$',views.listCron,name="listCron"),
    url(r'^getWebsiteCron$',views.getWebsiteCron,name="getWebsiteCron"),
    url(r'^getCronbyLine$',views.getCronbyLine,name="getCronbyLine"),
    url(r'^remCronbyLine$',views.remCronbyLine,name="remCronbyLine"),
    url(r'^saveCronChanges$',views.saveCronChanges,name="saveCronChanges"),
    url(r'^addNewCron$',views.addNewCron,name="addNewCron"),


    ## Domain Alias

    url(r'^(?P<domain>(.*))/domainAlias$', views.domainAlias, name='domainAlias'),
    url(r'^submitAliasCreation$',views.submitAliasCreation,name="submitAliasCreation"),
    url(r'^issueAliasSSL$',views.issueAliasSSL,name="issueAliasSSL"),
    url(r'^delateAlias$',views.delateAlias,name="delateAlias"),


    ## Openbasedir
    url(r'^changeOpenBasedir$',views.changeOpenBasedir,name="changeOpenBasedir"),

    ## WP Install

    url(r'^(?P<domain>(.*))/wordpressInstall$', views.wordpressInstall, name='wordpressInstall'),
    url(r'^installWordpressStatus$',views.installWordpressStatus,name="installWordpressStatus"),
    url(r'^installWordpress$', views.installWordpress, name='installWordpress'),


    ## Joomla Install

    url(r'^installJoomla$', views.installJoomla, name='installJoomla'),
    url(r'^(?P<domain>(.*))/joomlaInstall$', views.joomlaInstall, name='joomlaInstall'),

    ## PrestaShop Install

    url(r'^prestaShopInstall$', views.prestaShopInstall, name='prestaShopInstall'),
    url(r'^(?P<domain>(.*))/installPrestaShop$', views.installPrestaShop, name='installPrestaShop'),

    ## magento

    url(r'^(?P<domain>(.*))/installMagento$', views.installMagento, name='installMagento'),
    url(r'^magentoInstall$', views.magentoInstall, name='magentoInstall'),

    ## mautic

    url(r'^(?P<domain>(.*))/installMautic$', views.installMautic, name='installMautic'),
    url(r'^mauticInstall$', views.mauticInstall, name='mauticInstall'),


    ## Git
    url(r'^(?P<domain>(.*))/setupGit$', views.setupGit, name='setupGit'),
    url(r'^setupGitRepo$', views.setupGitRepo, name='setupGitRepo'),

    ## Set up SSH Access
    url(r'^(?P<domain>(.*))/sshAccess$', views.sshAccess, name='sshAccess'),
    url(r'^saveSSHAccessChanges$', views.saveSSHAccessChanges, name='saveSSHAccessChanges'),

    ## Staging Enviroment

    url(r'^(?P<domain>(.*))/setupStaging$', views.setupStaging, name='setupStaging'),
    url(r'^startCloning$', views.startCloning, name='startCloning'),
    url(r'^(?P<domain>(.*))/(?P<childDomain>(.*))/syncToMaster$', views.syncToMaster, name='syncToMaster'),
    url(r'^startSync$', views.startSync, name='startSync'),


    url(r'^(?P<domain>(.*))/gitNotify$', views.gitNotify, name='gitNotify'),
    url(r'^detachRepo$', views.detachRepo, name='detachRepo'),
    url(r'^changeBranch$', views.changeBranch, name='changeBranch'),

    ### Manage GIT

    url(r'^(?P<domain>(.*))/manageGIT$', views.manageGIT, name='manageGIT'),
    url(r'^(?P<domain>(.*))/webhook$', views.webhook, name='webhook'),
    url(r'^fetchFolderDetails$', views.fetchFolderDetails, name='fetchFolderDetails'),
    url(r'^initRepo$', views.initRepo, name='initRepo'),
    url(r'^setupRemote$', views.setupRemote, name='setupRemote'),
    url(r'^changeGitBranch$', views.changeGitBranch, name='changeGitBranch'),
    url(r'^createNewBranch$', views.createNewBranch, name='createNewBranch'),
    url(r'^commitChanges$', views.commitChanges, name='commitChanges'),
    url(r'^gitPull$', views.gitPull, name='gitPull'),
    url(r'^gitPush$', views.gitPush, name='gitPush'),
    url(r'^attachRepoGIT$', views.attachRepoGIT, name='attachRepoGIT'),
    url(r'^removeTracking$', views.removeTracking, name='removeTracking'),
    url(r'^fetchGitignore$', views.fetchGitignore, name='fetchGitignore'),
    url(r'^saveGitIgnore$', views.saveGitIgnore, name='saveGitIgnore'),
    url(r'^fetchCommits$', views.fetchCommits, name='fetchCommits'),
    url(r'^fetchFiles$', views.fetchFiles, name='fetchFiles'),
    url(r'^fetchChangesInFile$', views.fetchChangesInFile, name='fetchChangesInFile'),
    url(r'^saveGitConfigurations$', views.saveGitConfigurations, name='saveGitConfigurations'),
    url(r'^fetchGitLogs$', views.fetchGitLogs, name='fetchGitLogs'),

    ### SSH Configs

    url(r'^getSSHConfigs$', views.getSSHConfigs, name='getSSHConfigs'),
    url(r'^deleteSSHKey$', views.deleteSSHKey, name='deleteSSHKey'),
    url(r'^addSSHKey$', views.addSSHKey, name='addSSHKey'),


    ## Catch all for domains
    url(r'^(?P<domain>(.*))/(?P<childDomain>(.*))$', views.launchChild, name='launchChild'),
    url(r'^(?P<domain>(.*))$', views.domain, name='domain'),
]