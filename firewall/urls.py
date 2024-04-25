from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^securityHome', views.securityHome, name='securityHome'),
    url(r'^$', views.firewallHome, name='firewallHome'),
    url(r'^V2/V2$', views.firewallHomeV2, name='firewallHomeV2'),
    url(r'^getCurrentRules', views.getCurrentRules, name='getCurrentRules'),
    url(r'^addRule', views.addRule, name='addRule'),
    url(r'^deleteRule', views.deleteRule, name='deleteRule'),

    url(r'^reloadFirewall', views.reloadFirewall, name='reloadFirewall'),
    url(r'^stopFirewall', views.stopFirewall, name='stopFirewall'),
    url(r'^startFirewall', views.startFirewall, name='startFirewall'),
    url(r'^firewallStatus', views.firewallStatus, name='firewallStatus'),

    ## secure SSH

    url(r'^secureSSH', views.secureSSH, name='secureSSH'),
    url(r'^V2/secureSSHV2', views.secureSSHV2, name='secureSSHV2'),
    url(r'^getSSHConfigs', views.getSSHConfigs, name='getSSHConfigs'),
    url(r'^saveSSHConfigs', views.saveSSHConfigs, name='saveSSHConfigs'),
    url(r'^deleteSSHKey', views.deleteSSHKey, name='deleteSSHKey'),
    url(r'^addSSHKey', views.addSSHKey, name='addSSHKey'),

    ## ModSecurity

    url(r'^modSecurity$', views.loadModSecurityHome, name='modSecurity'),
    url(r'^V2/modSecurityV2$', views.loadModSecurityHomeV2, name='modSecurityV2'),
    url(r'^installModSec$', views.installModSec, name='installModSec'),
    url(r'^installStatusModSec$', views.installStatusModSec, name='installStatusModSec'),
    url(r'^fetchModSecSettings$', views.fetchModSecSettings, name='fetchModSecSettings'),
    url(r'^saveModSecConfigurations$', views.saveModSecConfigurations, name='saveModSecConfigurations'),
    url(r'^modSecRules$', views.modSecRules, name='modSecRules'),
    url(r'^V2/modSecRulesV2$', views.modSecRulesV2, name='modSecRulesV2'),
    url(r'^fetchModSecRules$', views.fetchModSecRules, name='fetchModSecRules'),
    url(r'^saveModSecRules$', views.saveModSecRules, name='saveModSecRules'),
    url(r'^modSecRulesPacks$', views.modSecRulesPacks, name='modSecRulesPacks'),
    url(r'^V2/modSecRulesPacksV2$', views.modSecRulesPacksV2, name='modSecRulesPacksV2'),
    url(r'^getOWASPAndComodoStatus$', views.getOWASPAndComodoStatus, name='getOWASPAndComodoStatus'),
    url(r'^installModSecRulesPack$', views.installModSecRulesPack, name='installModSecRulesPack'),
    url(r'^getRulesFiles$', views.getRulesFiles, name='getRulesFiles'),
    url(r'^enableDisableRuleFile$', views.enableDisableRuleFile, name='enableDisableRuleFile'),

    ## CSF

    url(r'^csf$', views.csf, name='csf'),
    url(r'^V2/csfV2$', views.csfV2, name='csfV2'),
    url(r'^installCSF$', views.installCSF, name='installCSF'),
    url(r'^installStatusCSF$', views.installStatusCSF, name='installStatusCSF'),
    url(r'^removeCSF$', views.removeCSF, name='removeCSF'),
    url(r'^fetchCSFSettings$', views.fetchCSFSettings, name='fetchCSFSettings'),

    url(r'^changeStatus$', views.changeStatus, name='changeStatus'),
    url(r'^modifyPorts$', views.modifyPorts, name='modifyPorts'),
    url(r'^modifyIPs$', views.modifyIPs, name='modifyIPs'),

    ## Imunify

    url(r'^imunify$', views.imunify, name='imunify'),
    url(r'^V2/imunifyV2$', views.imunifyV2, name='imunifyV2'),
    url(r'^submitinstallImunify$', views.submitinstallImunify, name='submitinstallImunify'),

    ## ImunifyAV

    url(r'^imunifyAV$', views.imunifyAV, name='imunifyAV'),
    url(r'^V2/imunifyAVV2$', views.imunifyAVV2, name='imunifyAVV2'),
    url(r'^submitinstallImunifyAV$', views.submitinstallImunifyAV, name='submitinstallImunifyAV'),

]
