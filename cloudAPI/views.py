# -*- coding: utf-8 -*-

from .cloudManager import CloudManager
import json
from loginSystem.models import Administrator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import HttpResponse
from django.core.cache import cache
import hashlib
try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:
    from django.utils.http import is_safe_url as url_has_allowed_host_and_scheme
from plogical.securityUtils import api_token_matches, api_two_factor_matches


CLOUD_ACCESS_FAILURE_LIMIT = 10
CLOUD_ACCESS_FAILURE_WINDOW = 5 * 60


def _access_cache_key(request):
    remote_address = request.META.get('REMOTE_ADDR', '')
    return 'cp_cloud_access_%s' % hashlib.sha256(remote_address.encode()).hexdigest()


def _access_response(message, status):
    response = HttpResponse(message, status=status)
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def _record_access_failure(cache_key):
    if cache.add(cache_key, 1, CLOUD_ACCESS_FAILURE_WINDOW):
        return
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, CLOUD_ACCESS_FAILURE_WINDOW)


def _normalized_session_ip(request):
    ip_address = request.META.get('HTTP_CF_CONNECTING_IP')
    if ip_address is None:
        ip_address = request.META.get('REMOTE_ADDR', '')
    if ':' in ip_address:
        return ':'.join(ip_address.split(':')[:3])
    return ip_address

@csrf_exempt
def router(request):
    try:
        data = json.loads(request.body)
        controller = data['controller']

        serverUserName = data['serverUserName']

        admin = Administrator.objects.get(userName=serverUserName)

        cm = CloudManager(data, admin)

        if serverUserName != 'admin':
            return cm.ajaxPre(0, 'Only administrator can access API.')

        if not admin.api or admin.state != 'ACTIVE':
            return cm.ajaxPre(0, 'Could not authorize access to API.')

        try:
            if cm.verifyLogin(request)[0] == 1:
                pass
            else:
                return cm.verifyLogin(request)[1]
        except BaseException as msg:
            return cm.ajaxPre(0, f"Something went wrong during token processing. ErrorL {str(msg)}")


        ## Debug Log

        import os
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
        from plogical.processUtilities import ProcessUtilities
        if os.path.exists(ProcessUtilities.debugPath):
            logging.writeToFile('Current controller: %s' % (controller))

        ##

        if controller == 'verifyLogin':
            return cm.verifyLogin(request)[1]
        elif controller == 'RunServerLevelEmailChecks':
            return cm.RunServerLevelEmailChecks()
        elif controller == 'DetachCluster':
            return cm.DetachCluster()
        elif controller == 'DebugCluster':
            return cm.DebugCluster()
        elif controller == 'CheckMasterNode':
            return cm.CheckMasterNode()
        elif controller == 'UptimeMonitor':
            return cm.UptimeMonitor()
        elif controller == 'SyncToMaster':
            return cm.SyncToMaster()
        elif controller == 'FetchMasterBootStrapStatus':
            return cm.FetchMasterBootStrapStatus()
        elif controller == 'FetchChildBootStrapStatus':
            return cm.FetchChildBootStrapStatus()
        elif controller == 'CreatePendingVirtualHosts':
            return cm.CreatePendingVirtualHosts()
        elif controller == 'BootMaster':
            return cm.BootMaster()
        elif controller == 'SwitchDNS':
            return cm.SwitchDNS()
        elif controller == 'BootChild':
            return cm.BootChild()
        elif controller == 'SetupCluster':
            return cm.SetupCluster()
        elif controller == 'ReadReport':
            return cm.ReadReport()
        elif controller == 'ResetEmailConfigurations':
            return cm.ResetEmailConfigurations()
        elif controller == 'fetchAllSites':
            return cm.fetchAllSites()
        elif controller == 'debugEmailForSite':
            return cm.debugEmailForSite()
        elif controller == 'fixMailSSL':
            return cm.fixMailSSL(request)
        elif controller == 'ReadReportFTP':
            return cm.ReadReportFTP()
        elif controller == 'ResetFTPConfigurations':
            return cm.ResetFTPConfigurations()
        elif controller == 'ReadReportDNS':
            return cm.ReadReportDNS()
        elif controller == 'ResetDNSConfigurations':
            return cm.ResetDNSConfigurations()
        elif controller == 'SubmitCloudBackup':
            return cm.SubmitCloudBackup()
        elif controller == 'getCurrentCloudBackups':
            return cm.getCurrentCloudBackups()
        elif controller == 'fetchCloudBackupSettings':
            return cm.fetchCloudBackupSettings()
        elif controller == 'SubmitCyberPanelUpgrade':
            return cm.SubmitCyberPanelUpgrade()
        elif controller == 'saveCloudBackupSettings':
            return cm.saveCloudBackupSettings()
        elif controller == 'deleteCloudBackup':
            return cm.deleteCloudBackup()
        elif controller == 'SubmitCloudBackupRestore':
            return cm.SubmitCloudBackupRestore()
        elif controller == 'DeployWordPress':
            return cm.DeployWordPress()
        elif controller == 'FetchWordPressDetails':
            return cm.FetchWordPressDetails()
        elif controller == 'AutoLogin':
            return cm.AutoLogin()
        elif controller == 'DeletePlugins':
            return cm.DeletePlugins()
        elif controller == 'GetCurrentThemes':
            return cm.GetCurrentThemes()
        elif controller == 'UpdateThemes':
            return cm.UpdateThemes()
        elif controller == 'ChangeStateThemes':
            return cm.ChangeStateThemes()
        elif controller == 'DeleteThemes':
            return cm.DeleteThemes()
        elif controller == 'ChangeLinuxUserPassword':
            from websiteFunctions.website import WebsiteManager
            wm = WebsiteManager()
            return wm.saveSSHAccessChanges(admin.id, data)
        elif controller == 'GetServerPublicSSHkey':
            return cm.GetServerPublicSSHkey()
        elif controller == 'SubmitPublicKey':
            return cm.SubmitPublicKey()
        elif controller == 'UpdateWPSettings':
            return cm.UpdateWPSettings()
        elif controller == 'GetCurrentPlugins':
            return cm.GetCurrentPlugins()
        elif controller == 'UpdatePlugins':
            return cm.UpdatePlugins()
        elif controller == 'ChangeState':
            return cm.ChangeState()
        elif controller == 'saveWPSettings':
            return cm.saveWPSettings()
        elif controller == 'WPScan':
            return cm.WPScan()
        elif controller == 'getCurrentS3Backups':
            return cm.getCurrentS3Backups()
        elif controller == 'deleteS3Backup':
            return cm.deleteS3Backup()
        elif controller == 'SubmitS3BackupRestore':
            return cm.SubmitS3BackupRestore()
        elif controller == 'fetchWebsites':
            return cm.fetchWebsites()
        elif controller == 'fetchWebsiteDataJSON':
            return cm.fetchWebsiteDataJSON()
        elif controller == 'fetchWebsiteData':
            return cm.fetchWebsiteData()
        elif controller == 'submitWebsiteCreation':
            return cm.submitWebsiteCreation()
        elif controller == 'fetchModifyData':
            return cm.fetchModifyData()
        elif controller == 'saveModifications':
            return cm.saveModifications()
        elif controller == 'submitDBCreation':
            return cm.submitDBCreation()
        elif controller == 'fetchDatabases':
            return cm.fetchDatabases()
        elif controller == 'submitDatabaseDeletion':
            return cm.submitDatabaseDeletion()
        elif controller == 'changePassword':
            return cm.changePassword()
        elif controller == 'getCurrentRecordsForDomain':
            return cm.getCurrentRecordsForDomain()
        elif controller == 'deleteDNSRecord':
            return cm.deleteDNSRecord()
        elif controller == 'addDNSRecord':
            return cm.addDNSRecord()
        elif controller == 'submitEmailCreation':
            return cm.submitEmailCreation(request)
        elif controller == 'getEmailsForDomain':
            return cm.getEmailsForDomain(request)
        elif controller == 'submitEmailDeletion':
            return cm.submitEmailDeletion(request)
        elif controller == 'submitPasswordChange':
            return cm.submitPasswordChange(request)
        elif controller == 'fetchCurrentForwardings':
            return cm.fetchCurrentForwardings(request)
        elif controller == 'submitForwardDeletion':
            return cm.submitForwardDeletion(request)
        elif controller == 'submitEmailForwardingCreation':
            return cm.submitEmailForwardingCreation(request)
        elif controller == 'fetchDKIMKeys':
            return cm.fetchDKIMKeys(request)
        elif controller == 'generateDKIMKeys':
            return cm.generateDKIMKeys(request)
        elif controller == 'submitFTPCreation':
            return cm.submitFTPCreation(request)
        elif controller == 'getAllFTPAccounts':
            return cm.getAllFTPAccounts(request)
        elif controller == 'submitFTPDelete':
            return cm.submitFTPDelete(request)
        elif controller == 'changeFTPPassword':
            return cm.changeFTPPassword(request)
        elif controller == 'issueSSL':
            return cm.issueSSL(request)
        elif controller == 'submitWebsiteDeletion':
            return cm.submitWebsiteDeletion(request)
        elif controller == 'statusFunc':
            return cm.statusFunc()
        elif controller == 'submitDomainCreation':
            return cm.submitDomainCreation()
        elif controller == 'fetchDomains':
            return cm.fetchDomains()
        elif controller == 'submitDomainDeletion':
            return cm.submitDomainDeletion()
        elif controller == 'changeOpenBasedir':
            return cm.changeOpenBasedir()
        elif controller == 'changePHP':
            return cm.changePHP()
        elif controller == 'backupStatusFunc':
            return cm.backupStatusFunc()
        elif controller == 'submitBackupCreation':
            return cm.submitBackupCreation()
        elif controller == 'getCurrentBackups':
            return cm.getCurrentBackups()
        elif controller == 'deleteBackup':
            return cm.deleteBackup()
        elif controller == 'fetchACLs':
            return cm.fetchACLs()
        elif controller == 'submitUserCreation':
            return cm.submitUserCreation(request)
        elif controller == 'fetchUsers':
            return cm.fetchUsers()
        elif controller == 'submitUserDeletion':
            return cm.submitUserDeletion(request)
        elif controller == 'saveModificationsUser':
            return cm.saveModificationsUser(request)
        elif controller == 'userWithResellerPriv':
            return cm.userWithResellerPriv()
        elif controller == 'saveResellerChanges':
            return cm.saveResellerChanges(request)
        elif controller == 'changeACLFunc':
            return cm.changeACLFunc(request)
        elif controller == 'createACLFunc':
            return cm.createACLFunc(request)
        elif controller == 'findAllACLs':
            return cm.findAllACLs(request)
        elif controller == 'deleteACLFunc':
            return cm.deleteACLFunc(request)
        elif controller == 'fetchACLDetails':
            return cm.fetchACLDetails(request)
        elif controller == 'submitACLModifications':
            return cm.submitACLModifications(request)
        elif controller == 'submitPackage':
            return cm.submitPackage(request)
        elif controller == 'fetchPackages':
            return cm.fetchPackages(request)
        elif controller == 'submitPackageDelete':
            return cm.submitPackageDelete(request)
        elif controller == 'submitPackageModify':
            return cm.submitPackageModify(request)
        elif controller == 'getDataFromLogFile':
            return cm.getDataFromLogFile(request)
        elif controller == 'fetchErrorLogs':
            return cm.fetchErrorLogs(request)
        elif controller == 'submitApplicationInstall':
            return cm.submitApplicationInstall(request)
        elif controller == 'obtainServer':
            return cm.obtainServer(request)
        elif controller == 'getSSHConfigs':
            return cm.getSSHConfigs()
        elif controller == 'saveSSHConfigs':
            return cm.saveSSHConfigs()
        elif controller == 'deleteSSHKey':
            return cm.deleteSSHKey()
        elif controller == 'addSSHKey':
            return cm.addSSHKey()
        elif controller == 'getCurrentRules':
            return cm.getCurrentRules()
        elif controller == 'addRule':
            return cm.addRule()
        elif controller == 'deleteRule':
            return cm.deleteRule()
        elif controller == 'getLogsFromFile':
            return cm.getLogsFromFile(request)
        elif controller == 'serverSSL':
            return cm.serverSSL(request)
        elif controller == 'CreateStaging':
            return cm.CreateStaging(request)
        elif controller == 'startSync':
            return cm.startSync(request)
        elif controller == 'SaveAutoUpdateSettings':
            return cm.SaveAutoUpdateSettings()
        elif controller == 'fetchWPSettings':
            return cm.fetchWPSettings()
        elif controller == 'updateWPCLI':
            return cm.updateWPCLI()
        elif controller == 'setupNode':
            return cm.setupManager(request)
        elif controller == 'fetchManagerTokens':
            return cm.fetchManagerTokens(request)
        elif controller == 'addWorker':
            return cm.addWorker(request)
        elif controller == 'fetchSSHKey':
            return cm.fetchSSHKey(request)
        elif controller == 'putSSHkeyFunc':
            return cm.putSSHkeyFunc(request)
        elif controller == 'leaveSwarm':
            return cm.leaveSwarm(request)
        elif controller == 'setUpDataNode':
            return cm.setUpDataNode(request)
        elif controller == 'submitEditCluster':
            return cm.submitEditCluster(request)
        elif controller == 'connectAccount':
            return cm.connectAccount(request)
        elif controller == 'fetchBuckets':
            return cm.fetchBuckets(request)
        elif controller == 'createPlan':
            return cm.createPlan(request)
        elif controller == 'fetchBackupPlans':
            return cm.fetchBackupPlans(request)
        elif controller == 'deletePlan':
            return cm.deletePlan(request)
        elif controller == 'fetchWebsitesInPlan':
            return cm.fetchWebsitesInPlan(request)
        elif controller == 'deleteDomainFromPlan':
            return cm.deleteDomainFromPlan(request)
        elif controller == 'savePlanChanges':
            return cm.savePlanChanges(request)
        elif controller == 'fetchBackupLogs':
            return cm.fetchBackupLogs(request)
        elif controller == 'forceRunAWSBackup':
            return cm.forceRunAWSBackup(request)
        elif controller == 'systemStatus':
            return cm.systemStatus(request)
        elif controller == 'killProcess':
            return cm.killProcess(request)
        elif controller == 'connectAccountDO':
            return cm.connectAccountDO(request)
        elif controller == 'fetchBucketsDO':
            return cm.fetchBucketsDO(request)
        elif controller == 'createPlanDO':
            return cm.createPlanDO(request)
        elif controller == 'fetchBackupPlansDO':
            return cm.fetchBackupPlansDO(request)
        elif controller == 'deletePlanDO':
            return cm.deletePlanDO(request)
        elif controller == 'fetchWebsitesInPlanDO':
            return cm.fetchWebsitesInPlanDO(request)
        elif controller == 'fetchBackupLogsDO':
            return cm.fetchBackupLogsDO(request)
        elif controller == 'deleteDomainFromPlanDO':
            return cm.deleteDomainFromPlanDO(request)
        elif controller == 'savePlanChangesDO':
            return cm.savePlanChangesDO(request)
        elif controller == 'forceRunAWSBackupDO':
            return cm.forceRunAWSBackupDO(request)
        elif controller == 'showStatus':
            return cm.showStatus(request)
        elif controller == 'fetchRam':
            return cm.fetchRam(request)
        elif controller == 'applyMySQLChanges':
            return cm.applyMySQLChanges(request)
        elif controller == 'restartMySQL':
            return cm.restartMySQL(request)
        elif controller == 'fetchDatabasesMYSQL':
            return cm.fetchDatabasesMYSQL(request)
        elif controller == 'fetchTables':
            return cm.fetchTables(request)
        elif controller == 'deleteTable':
            return cm.deleteTable(request)
        elif controller == 'fetchTableData':
            return cm.fetchTableData(request)
        elif controller == 'fetchStructure':
            return cm.fetchStructure(request)
        elif controller == 'addMINIONode':
            return cm.addMINIONode(request)
        elif controller == 'fetchMINIONodes':
            return cm.fetchMINIONodes(request)
        elif controller == 'deleteMINIONode':
            return cm.deleteMINIONode(request)
        elif controller == 'createPlanMINIO':
            return cm.createPlanMINIO(request)
        elif controller == 'fetchBackupPlansMINIO':
            return cm.fetchBackupPlansMINIO(request)
        elif controller == 'deletePlanMINIO':
            return cm.deletePlanMINIO(request)
        elif controller == 'savePlanChangesMINIO':
            return cm.savePlanChangesMINIO(request)
        elif controller == 'forceRunAWSBackupMINIO':
            return cm.forceRunAWSBackupMINIO(request)
        elif controller == 'fetchWebsitesInPlanMINIO':
            return cm.fetchWebsitesInPlanMINIO(request)
        elif controller == 'fetchBackupLogsMINIO':
            return cm.fetchBackupLogsMINIO(request)
        elif controller == 'deleteDomainFromPlanMINIO':
            return cm.deleteDomainFromPlanMINIO(request)
        elif controller == 'submitWebsiteStatus':
            return cm.submitWebsiteStatus(request)
        elif controller == 'submitChangePHP':
            return cm.submitChangePHP(request)
        elif controller == 'getSwitchStatus':
            return cm.getSwitchStatus(request)
        elif controller == 'switchServer':
            return cm.switchServer(request)
        elif controller == 'tuneSettings':
            return cm.tuneSettings(request)
        elif controller == 'getCurrentPHPConfig':
            return cm.getCurrentPHPConfig(request)
        elif controller == 'savePHPConfigBasic':
            return cm.savePHPConfigBasic(request)
        elif controller == 'fetchPHPSettingsAdvance':
            return cm.fetchPHPSettingsAdvance(request)
        elif controller == 'savePHPConfigAdvance':
            return cm.savePHPConfigAdvance(request)
        elif controller == 'fetchPHPExtensions':
            return cm.fetchPHPExtensions(request)
        elif controller == 'submitExtensionRequest':
            return cm.submitExtensionRequest(request)
        elif controller == 'getRequestStatus':
            return cm.getRequestStatus(request)
        elif controller == 'getContainerizationStatus':
            return cm.getContainerizationStatus(request)
        elif controller == 'submitContainerInstall':
            return cm.submitContainerInstall(request)
        elif controller == 'switchTOLSWSStatus':
            return cm.switchTOLSWSStatus(request)
        elif controller == 'fetchWebsiteLimits':
            return cm.fetchWebsiteLimits(request)
        elif controller == 'saveWebsiteLimits':
            return cm.saveWebsiteLimits(request)
        elif controller == 'getUsageData':
            return cm.getUsageData(request)
        elif controller == 'installN8N':
            return cm.installN8N()
        elif controller == 'getN8NInstallStatus':
            return cm.getN8NInstallStatus()
        elif controller == 'listN8NInstallations':
            return cm.listN8NInstallations()
        elif controller == 'removeN8NInstallation':
            return cm.removeN8NInstallation()
        else:
            return cm.ajaxPre(0, 'This function is not available in your version of CyberPanel.')

    except BaseException as msg:
        cm = CloudManager(None)
        return cm.ajaxPre(0, str(msg))

def access(request):
    serverUserName = request.GET.get('serverUserName', '')
    token = request.GET.get('token') or request.META.get('HTTP_AUTHORIZATION')
    redirectFinal = request.GET.get('redirect')
    cache_key = _access_cache_key(request)

    if cache.get(cache_key, 0) >= CLOUD_ACCESS_FAILURE_LIMIT:
        return _access_response('Too many attempts. Try again later.', 429)

    try:
        admin = Administrator.objects.get(userName=serverUserName)
    except Exception:
        _record_access_failure(cache_key)
        return _access_response('Unauthorized access.', 401)

    if not admin.api or admin.state != 'ACTIVE' or not api_token_matches(token, admin.token):
        _record_access_failure(cache_key)
        return _access_response('Unauthorized access.', 401)

    if not api_two_factor_matches(admin, request):
        _record_access_failure(cache_key)
        return _access_response('Two-factor authentication required.', 401)

    if redirectFinal is not None and not url_has_allowed_host_and_scheme(
            redirectFinal,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()):
        return _access_response('Invalid redirect target.', 400)

    cache.delete(cache_key)
    request.session.cycle_key()
    request.session['userID'] = admin.pk
    request.session['ipAddr'] = _normalized_session_ip(request)
    request.session.set_expiry(43200)
    request.session.save()

    from django.shortcuts import redirect
    if redirectFinal is None:
        from baseTemplate.views import renderBase
        response = redirect(renderBase)
    else:
        response = redirect(redirectFinal)
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response
