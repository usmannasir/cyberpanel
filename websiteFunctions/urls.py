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

    ## Catch all for domains
    url(r'^(?P<domain>(.*))/(?P<childDomain>(.*))$', views.launchChild, name='launchChild'),
    url(r'^(?P<domain>(.*))$', views.domain, name='domain'),
]