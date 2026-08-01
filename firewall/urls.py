from django.urls import path
from . import views

urlpatterns = [
    path('securityHome', views.securityHome, name='securityHome'),
    path('firewall-rules/', views.firewallHome, name='firewallRules'),
    path('firewall-rules', views.firewallHome, name='firewallRulesNoSlash'),
    path('banned-ips/', views.firewallHome, name='firewallBannedIPs'),
    path('banned-ips', views.firewallHome, name='firewallBannedIPsNoSlash'),
    path('', views.firewallHome, name='firewallHome'),  # /firewall/ also serves the page so 404 is avoided
    path('getCurrentRules', views.getCurrentRules, name='getCurrentRules'),
    path('addRule', views.addRule, name='addRule'),
    path('modifyRule', views.modifyRule, name='modifyRule'),
    path('deleteRule', views.deleteRule, name='deleteRule'),
    path('reorderRules', views.reorderRules, name='reorderRules'),

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
    
    # Banned IPs
    path('getBannedIPs', views.getBannedIPs, name='getBannedIPs'),
    path('addBannedIP', views.addBannedIP, name='addBannedIP'),
    path('modifyBannedIP', views.modifyBannedIP, name='modifyBannedIP'),
    path('removeBannedIP', views.removeBannedIP, name='removeBannedIP'),
    path('deleteBannedIP', views.deleteBannedIP, name='deleteBannedIP'),
    path('exportBannedIPs', views.exportBannedIPs, name='exportBannedIPs'),
    path('importBannedIPs', views.importBannedIPs, name='importBannedIPs'),
    path('getRulesFiles', views.getRulesFiles, name='getRulesFiles'),
    path('enableDisableRuleFile', views.enableDisableRuleFile, name='enableDisableRuleFile'),

    # CSF - Discontinued on August 31, 2025
    # path('csf', views.csf, name='csf'),
    # path('installCSF', views.installCSF, name='installCSF'),
    # path('installStatusCSF', views.installStatusCSF, name='installStatusCSF'),
    # path('removeCSF', views.removeCSF, name='removeCSF'),
    # path('fetchCSFSettings', views.fetchCSFSettings, name='fetchCSFSettings'),
    # path('changeStatus', views.changeStatus, name='changeStatus'),
    # path('modifyPorts', views.modifyPorts, name='modifyPorts'),
    # path('modifyIPs', views.modifyIPs, name='modifyIPs'),

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
    
    # Firewall Export/Import
    path('exportFirewallRules', views.exportFirewallRules, name='exportFirewallRules'),
    path('importFirewallRules', views.importFirewallRules, name='importFirewallRules'),
]
