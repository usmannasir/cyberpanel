from django.conf.urls import url
import views
from filemanager_app import views as fm


urlpatterns = [
    url(r'^$', views.loadWebsitesHome, name='loadWebsitesHome'),
    url(r'^createWebsite', views.createWebsite, name='createWebsite'),
    url(r'^listWebsites', views.listWebsites, name='listWebsites'),
    url(r'^modifyWebsite', views.modifyWebsite, name='modifyWebsite'),
    url(r'^deleteWebsite', views.deleteWebsite, name='deleteWebsite'),
    url(r'^siteState', views.siteState, name='siteState'),


    # Website modification url


    url(r'^submitWebsiteCreation', views.submitWebsiteCreation, name='submitWebsiteCreation'),
    url(r'^submitWebsiteDeletion', views.submitWebsiteDeletion, name='submitWebsiteDeletion'),
    url(r'^submitWebsiteListing', views.getFurtherAccounts, name='submitWebsiteListing'),
    url(r'^submitWebsiteModification', views.deleteWebsite, name='submitWebsiteModification'),
    url(r'^submitWebsiteStatus', views.submitWebsiteStatus, name='submitWebsiteStatus'),


    url(r'^getWebsiteDetails', views.submitWebsiteModify, name='getWebsiteDetails'),
    url(r'^saveWebsiteChanges', views.saveWebsiteChanges, name='saveWebsiteChanges'),


    url(r'^(?P<domain>([\da-z\.-]+\.[a-z\.]{2,6}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?)$', views.domain, name='domain'),
    url(r'^getDataFromLogFile', views.getDataFromLogFile, name='getDataFromLogFile'),


    url(r'^installWordpress', views.installWordpress, name='installWordpress'),

    url(r'^getDataFromConfigFile', views.getDataFromConfigFile, name='getDataFromConfigFile'),

    url(r'^saveConfigsToFile', views.saveConfigsToFile, name='saveConfigsToFile'),


    url(r'^getRewriteRules', views.getRewriteRules, name='getRewriteRules'),

    url(r'^saveRewriteRules', views.saveRewriteRules, name='saveRewriteRules'),

    url(r'^saveSSL', views.saveSSL, name='saveSSL'),


    url(r'^CreateWebsiteFromBackup', views.CreateWebsiteFromBackup, name='CreateWebsiteFromBackup'),




    url(r'^filemanager/(?P<domain>([\da-z\.-]+\.[a-z\.]{2,6}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?)$', views.filemanager,name='filemanager'),

    ## File manager urls

    url(r'^filemanager/list', fm.list_),
    url(r'^filemanager/rename', fm.rename),
    url(r'^filemanager/move', fm.move),
    url(r'^filemanager/copy', fm.copy),
    url(r'^filemanager/remove', fm.remove),
    url(r'^filemanager/edit', fm.edit),
    url(r'^filemanager/getContent', fm.getContent),
    url(r'^filemanager/createFolder', fm.createFolder),
    url(r'^filemanager/changePermissions', fm.changePermissions),
    url(r'^filemanager/compress', fm.compress),
    url(r'^filemanager/extract', fm.extract),
    url(r'^filemanager/downloadMultiple', fm.downloadMultiple),
    url(r'^filemanager/download', fm.download),
    url(r'^filemanager/upload', fm.upload),


]