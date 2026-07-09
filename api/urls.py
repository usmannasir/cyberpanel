from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^createWebsite$', views.createWebsite, name='createWebsiteAPI'),
    re_path(r'^deleteWebsite$', views.deleteWebsite, name='deleteWebsiteAPI'),
    re_path(r'^submitWebsiteStatus$', views.submitWebsiteStatus, name='submitWebsiteStatusAPI'),
    re_path(r'^deleteFirewallRule$', views.deleteFirewallRule, name='deleteFirewallRule'),
    re_path(r'^addFirewallRule$', views.addFirewallRule, name='addFirewallRule'),

    re_path(r'^verifyConn$', views.verifyConn, name='verifyConnAPI'),

    re_path(r'^loginAPI$', views.loginAPI, name='loginAPI'),

    re_path(r'^getUserInfo$', views.getUserInfo, name='getUserInfo'),
    re_path(r'^changeUserPassAPI$', views.changeUserPassAPI, name='changeUserPassAPI'),
    re_path(r'^submitUserDeletion$', views.submitUserDeletion, name='submitUserDeletion'),


    re_path(r'^listPackage$', views.getPackagesListAPI, name='getPackagesListAPI'),
    re_path(r'^changePackageAPI$', views.changePackageAPI, name='changePackageAPI'),
    re_path(r'^fetchSSHkey$', views.fetchSSHkey, name='fetchSSHkey'),
    re_path(r'^remoteTransfer$', views.remoteTransfer, name='remoteTransfer'),
    re_path(r'^fetchAccountsFromRemoteServer$', views.fetchAccountsFromRemoteServer, name='fetchAccountsFromRemoteServer'),
    re_path(r'^FetchRemoteTransferStatus$', views.FetchRemoteTransferStatus, name='FetchRemoteTransferStatus'),

    re_path(r'^cancelRemoteTransfer$', views.cancelRemoteTransfer, name='cancelRemoteTransfer'),

    re_path(r'^cyberPanelVersion$', views.cyberPanelVersion, name='cyberPanelVersion'),
    re_path(r'^runAWSBackups$', views.runAWSBackups, name='runAWSBackups'),
    re_path(r'^submitUserCreation$', views.submitUserCreation, name='submitUserCreation'),
    
    # AI Scanner API endpoints for external workers
    re_path(r'^ai-scanner/authenticate$', views.aiScannerAuthenticate, name='aiScannerAuthenticateAPI'),
    re_path(r'^ai-scanner/files/list$', views.aiScannerListFiles, name='aiScannerListFilesAPI'),
    re_path(r'^ai-scanner/files/content$', views.aiScannerGetFileContent, name='aiScannerGetFileContentAPI'),
    re_path(r'^ai-scanner/callback$', views.aiScannerCallback, name='aiScannerCallbackAPI'),
    
    # Real-time monitoring endpoints
    re_path(r'^ai-scanner/status-webhook$', views.aiScannerStatusWebhook, name='aiScannerStatusWebhookAPI'),
    re_path(r'^ai-scanner/callback/status-webhook$', views.aiScannerStatusWebhook, name='aiScannerStatusWebhookCallbackAPI'),  # Alternative URL for worker compatibility
    re_path(r'^ai-scanner/scan/(?P<scan_id>[^/]+)/live-progress$', views.aiScannerLiveProgress, name='aiScannerLiveProgressAPI'),

    # File operation endpoints for AI Scanner
    re_path(r'^scanner/backup-file$', views.scannerBackupFile, name='scannerBackupFileAPI'),
    re_path(r'^scanner/get-file$', views.scannerGetFile, name='scannerGetFileAPI'),
    re_path(r'^scanner/replace-file$', views.scannerReplaceFile, name='scannerReplaceFileAPI'),
    re_path(r'^scanner/rename-file$', views.scannerRenameFile, name='scannerRenameFileAPI'),
    re_path(r'^scanner/delete-file$', views.scannerDeleteFile, name='scannerDeleteFileAPI'),

]
