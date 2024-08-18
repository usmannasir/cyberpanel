from django.urls import path
from . import views

urlpatterns = [
    path('securityHome', views.securityHome, name='securityHome'),
    path('', views.firewallHome, name='firewallHome'),
    path('getCurrentRules', views.getCurrentRules, name='getCurrentRules'),
    path('addRule', views.addRule, name='addRule'),
    path('deleteRule', views.deleteRule, name='deleteRule'),

    path('reloadFirewall', views.reloadFirewall, name='reloadFirewall'),
    path('stopFirewall', views.stopFirewall, name='stopFirewall'),
    path('startFirewall', views.startFirewall, name='startFirewall'),
    path('firewallStatus', views.firewallStatus, name='firewallStatus'),

    # Secure SSH
    path('secureSSH', views.secureSSH, name='secureSSH'),
    path('getSSHConfigs', views.getSSHConfigs, name='getSSHConfigs'),
    path('saveSSHConfigs', views.saveSSHConfigs, name='saveSSHConfigs'),
    path('deleteSSHKey', views.deleteSSHKey, name='deleteSSHKey'),
    path('addSSHKey', views.addSSHKey, name='addSSHKey'),

    # ModSecurity
    path('modSecurity', views.loadModSecurityHome, name='modSecurity'),
    path('installModSec', views.installModSec, name='installModSec'),
    path('installStatusModSec', views.installStatusModSec, name='installStatusModSec'),
    path('fetchModSecSettings', views.fetchModSecSettings, name='fetchModSecSettings'),
    path('saveModSecConfigurations', views.saveModSecConfigurations, name='saveModSecConfigurations'),
    path('modSecRules', views.modSecRules, name='modSecRules'),
    path('fetchModSecRules', views.fetchModSecRules, name='fetchModSecRules'),
    path('saveModSecRules', views.saveModSecRules, name='saveModSecRules'),
    path('modSecRulesPacks', views.modSecRulesPacks, name='modSecRulesPacks'),
    path('getOWASPAndComodoStatus', views.getOWASPAndComodoStatus, name='getOWASPAndComodoStatus'),
    path('installModSecRulesPack', views.installModSecRulesPack, name='installModSecRulesPack'),
    path('getRulesFiles', views.getRulesFiles, name='getRulesFiles'),
    path('enableDisableRuleFile', views.enableDisableRuleFile, name='enableDisableRuleFile'),

    # CSF
    path('csf', views.csf, name='csf'),
    path('installCSF', views.installCSF, name='installCSF'),
    path('installStatusCSF', views.installStatusCSF, name='installStatusCSF'),
    path('removeCSF', views.removeCSF, name='removeCSF'),
    path('fetchCSFSettings', views.fetchCSFSettings, name='fetchCSFSettings'),
    path('changeStatus', views.changeStatus, name='changeStatus'),
    path('modifyPorts', views.modifyPorts, name='modifyPorts'),
    path('modifyIPs', views.modifyIPs, name='modifyIPs'),

    # Imunify
    path('imunify', views.imunify, name='imunify'),
    path('submitinstallImunify', views.submitinstallImunify, name='submitinstallImunify'),

    # ImunifyAV
    path('imunifyAV', views.imunifyAV, name='imunifyAV'),
    path('submitinstallImunifyAV', views.submitinstallImunifyAV, name='submitinstallImunifyAV'),

    # Litespeed
    path('litespeed_ent_conf', views.litespeed_ent_conf, name='litespeed_ent_conf'),
    path('fetchlitespeed_conf', views.fetchlitespeed_conf, name='fetchlitespeed_conf'),
    path('saveLitespeed_conf', views.saveLitespeed_conf, name='saveLitespeed_conf'),
]
