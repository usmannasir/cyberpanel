from django.urls import re_path
from . import views

urlpatterns = [
    # Pages
    re_path(r'^$', views.loadWebmail, name='loadWebmail'),
    re_path(r'^login$', views.loadLogin, name='loadWebmailLogin'),

    # Auth
    re_path(r'^api/login$', views.apiLogin, name='wmApiLogin'),
    re_path(r'^api/logout$', views.apiLogout, name='wmApiLogout'),
    re_path(r'^api/sso$', views.apiSSO, name='wmApiSSO'),
    re_path(r'^api/listAccounts$', views.apiListAccounts, name='wmApiListAccounts'),
    re_path(r'^api/switchAccount$', views.apiSwitchAccount, name='wmApiSwitchAccount'),

    # Folders
    re_path(r'^api/listFolders$', views.apiListFolders, name='wmApiListFolders'),
    re_path(r'^api/createFolder$', views.apiCreateFolder, name='wmApiCreateFolder'),
    re_path(r'^api/renameFolder$', views.apiRenameFolder, name='wmApiRenameFolder'),
    re_path(r'^api/deleteFolder$', views.apiDeleteFolder, name='wmApiDeleteFolder'),

    # Messages
    re_path(r'^api/listMessages$', views.apiListMessages, name='wmApiListMessages'),
    re_path(r'^api/searchMessages$', views.apiSearchMessages, name='wmApiSearchMessages'),
    re_path(r'^api/getMessage$', views.apiGetMessage, name='wmApiGetMessage'),
    re_path(r'^api/getAttachment$', views.apiGetAttachment, name='wmApiGetAttachment'),

    # Actions
    re_path(r'^api/sendMessage$', views.apiSendMessage, name='wmApiSendMessage'),
    re_path(r'^api/saveDraft$', views.apiSaveDraft, name='wmApiSaveDraft'),
    re_path(r'^api/deleteMessages$', views.apiDeleteMessages, name='wmApiDeleteMessages'),
    re_path(r'^api/moveMessages$', views.apiMoveMessages, name='wmApiMoveMessages'),
    re_path(r'^api/markRead$', views.apiMarkRead, name='wmApiMarkRead'),
    re_path(r'^api/markUnread$', views.apiMarkUnread, name='wmApiMarkUnread'),
    re_path(r'^api/markFlagged$', views.apiMarkFlagged, name='wmApiMarkFlagged'),

    # Contacts
    re_path(r'^api/listContacts$', views.apiListContacts, name='wmApiListContacts'),
    re_path(r'^api/createContact$', views.apiCreateContact, name='wmApiCreateContact'),
    re_path(r'^api/updateContact$', views.apiUpdateContact, name='wmApiUpdateContact'),
    re_path(r'^api/deleteContact$', views.apiDeleteContact, name='wmApiDeleteContact'),
    re_path(r'^api/searchContacts$', views.apiSearchContacts, name='wmApiSearchContacts'),
    re_path(r'^api/listContactGroups$', views.apiListContactGroups, name='wmApiListContactGroups'),
    re_path(r'^api/createContactGroup$', views.apiCreateContactGroup, name='wmApiCreateContactGroup'),
    re_path(r'^api/deleteContactGroup$', views.apiDeleteContactGroup, name='wmApiDeleteContactGroup'),

    # Sieve Rules
    re_path(r'^api/listRules$', views.apiListRules, name='wmApiListRules'),
    re_path(r'^api/createRule$', views.apiCreateRule, name='wmApiCreateRule'),
    re_path(r'^api/updateRule$', views.apiUpdateRule, name='wmApiUpdateRule'),
    re_path(r'^api/deleteRule$', views.apiDeleteRule, name='wmApiDeleteRule'),
    re_path(r'^api/activateRules$', views.apiActivateRules, name='wmApiActivateRules'),

    # Settings
    re_path(r'^api/getSettings$', views.apiGetSettings, name='wmApiGetSettings'),
    re_path(r'^api/saveSettings$', views.apiSaveSettings, name='wmApiSaveSettings'),

    # Image Proxy
    re_path(r'^api/proxyImage$', views.apiProxyImage, name='wmApiProxyImage'),
]
