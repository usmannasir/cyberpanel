from .signals import *
from plogical.pluginManagerGlobal import pluginManagerGlobal

class pluginManager:

    @staticmethod
    def preFirewallHome(request):
        return pluginManagerGlobal.globalPlug(request, preFirewallHome)

    @staticmethod
    def postFirewallHome(request, response):
        return pluginManagerGlobal.globalPlug(request, postFirewallHome, response)

    @staticmethod
    def preAddRule(request):
        return pluginManagerGlobal.globalPlug(request, preAddRule)

    @staticmethod
    def postAddRule(request, response):
        return pluginManagerGlobal.globalPlug(request, postAddRule, response)

    @staticmethod
    def preDeleteRule(request):
        return pluginManagerGlobal.globalPlug(request, preDeleteRule)

    @staticmethod
    def postDeleteRule(request, response):
        return pluginManagerGlobal.globalPlug(request, postDeleteRule, response)

    @staticmethod
    def preReloadFirewall(request):
        return pluginManagerGlobal.globalPlug(request, preReloadFirewall)

    @staticmethod
    def postReloadFirewall(request, response):
        return pluginManagerGlobal.globalPlug(request, postReloadFirewall, response)

    @staticmethod
    def preStartFirewall(request):
        return pluginManagerGlobal.globalPlug(request, preStartFirewall)

    @staticmethod
    def postStartFirewall(request, response):
        return pluginManagerGlobal.globalPlug(request, postStartFirewall, response)

    @staticmethod
    def preStopFirewall(request):
        return pluginManagerGlobal.globalPlug(request, preStopFirewall)

    @staticmethod
    def postStopFirewall(request, response):
        return pluginManagerGlobal.globalPlug(request, postStopFirewall, response)

    @staticmethod
    def preFirewallStatus(request):
        return pluginManagerGlobal.globalPlug(request, preFirewallStatus)

    @staticmethod
    def postFirewallStatus(request, response):
        return pluginManagerGlobal.globalPlug(request, postFirewallStatus, response)

    @staticmethod
    def preSecureSSH(request):
        return pluginManagerGlobal.globalPlug(request, preSecureSSH)

    @staticmethod
    def postSecureSSH(request, response):
        return pluginManagerGlobal.globalPlug(request, postSecureSSH, response)

    @staticmethod
    def preSaveSSHConfigs(request):
        return pluginManagerGlobal.globalPlug(request, preSaveSSHConfigs)

    @staticmethod
    def postSaveSSHConfigs(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveSSHConfigs, response)

    @staticmethod
    def preDeleteSSHKey(request):
        return pluginManagerGlobal.globalPlug(request, preDeleteSSHKey)

    @staticmethod
    def postDeleteSSHKey(request, response):
        return pluginManagerGlobal.globalPlug(request, postDeleteSSHKey, response)

    @staticmethod
    def preAddSSHKey(request):
        return pluginManagerGlobal.globalPlug(request, preAddSSHKey)

    @staticmethod
    def postAddSSHKey(request, response):
        return pluginManagerGlobal.globalPlug(request, postAddSSHKey, response)

    @staticmethod
    def preLoadModSecurityHome(request):
        return pluginManagerGlobal.globalPlug(request, preLoadModSecurityHome)

    @staticmethod
    def postLoadModSecurityHome(request, response):
        return pluginManagerGlobal.globalPlug(request, postLoadModSecurityHome, response)

    @staticmethod
    def preSaveModSecConfigurations(request):
        return pluginManagerGlobal.globalPlug(request, preSaveModSecConfigurations)

    @staticmethod
    def postSaveModSecConfigurations(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveModSecConfigurations, response)

    @staticmethod
    def preModSecRules(request):
        return pluginManagerGlobal.globalPlug(request, preModSecRules)

    @staticmethod
    def postModSecRules(request, response):
        return pluginManagerGlobal.globalPlug(request, postModSecRules, response)

    @staticmethod
    def preSaveModSecRules(request):
        return pluginManagerGlobal.globalPlug(request, preSaveModSecRules)

    @staticmethod
    def postSaveModSecRules(request, response):
        return pluginManagerGlobal.globalPlug(request, postSaveModSecRules, response)

    @staticmethod
    def preModSecRulesPacks(request):
        return pluginManagerGlobal.globalPlug(request, preModSecRulesPacks)

    @staticmethod
    def postModSecRulesPacks(request, response):
        return pluginManagerGlobal.globalPlug(request, postModSecRulesPacks, response)

    @staticmethod
    def preGetOWASPAndComodoStatus(request):
        return pluginManagerGlobal.globalPlug(request, preGetOWASPAndComodoStatus)

    @staticmethod
    def postGetOWASPAndComodoStatus(request, response):
        return pluginManagerGlobal.globalPlug(request, postGetOWASPAndComodoStatus, response)

    @staticmethod
    def preInstallModSecRulesPack(request):
        return pluginManagerGlobal.globalPlug(request, preInstallModSecRulesPack)

    @staticmethod
    def postInstallModSecRulesPack(request, response):
        return pluginManagerGlobal.globalPlug(request, postInstallModSecRulesPack, response)

    @staticmethod
    def preGetRulesFiles(request):
        return pluginManagerGlobal.globalPlug(request, preGetRulesFiles)

    @staticmethod
    def postGetRulesFiles(request, response):
        return pluginManagerGlobal.globalPlug(request, postGetRulesFiles, response)

    @staticmethod
    def preEnableDisableRuleFile(request):
        return pluginManagerGlobal.globalPlug(request, preEnableDisableRuleFile)

    @staticmethod
    def postEnableDisableRuleFile(request, response):
        return pluginManagerGlobal.globalPlug(request, postEnableDisableRuleFile, response)

    @staticmethod
    def preCSF(request):
        return pluginManagerGlobal.globalPlug(request, preCSF)

    @staticmethod
    def postCSF(request, response):
        return pluginManagerGlobal.globalPlug(request, postCSF, response)

    @staticmethod
    def preChangeStatus(request):
        return pluginManagerGlobal.globalPlug(request, preChangeStatus)

    @staticmethod
    def postChangeStatus(request, response):
        return pluginManagerGlobal.globalPlug(request, postChangeStatus, response)

    @staticmethod
    def preModifyPorts(request):
        return pluginManagerGlobal.globalPlug(request, preModifyPorts)

    @staticmethod
    def postModifyPorts(request, response):
        return pluginManagerGlobal.globalPlug(request, postModifyPorts, response)

    @staticmethod
    def preModifyIPs(request):
        return pluginManagerGlobal.globalPlug(request, preModifyIPs)

    @staticmethod
    def postModifyIPs(request, response):
        return pluginManagerGlobal.globalPlug(request, postModifyIPs, response)