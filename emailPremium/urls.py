from django.conf.urls import url
from . import views

urlpatterns = [

    url(r'^emailPolicyServer$', views.emailPolicyServer, name='emailPolicyServer'),
    url(r'^listDomains$', views.listDomains, name='listDomains'),
    url(r'^getFurtherDomains$', views.getFurtherDomains, name='getFurtherDomains'),
    url(r'^enableDisableEmailLimits$', views.enableDisableEmailLimits, name='enableDisableEmailLimits'),

    url(r'^changeDomainLimit$', views.changeDomainLimit, name='changeDomainLimit'),
    url(r'^getFurtherEmail$', views.getFurtherEmail, name='getFurtherEmail'),

    url(r'^enableDisableIndividualEmailLimits$', views.enableDisableIndividualEmailLimits, name='enableDisableIndividualEmailLimits'),

    url(r'(?P<emailAddress>\w+@.+)', views.emailPage, name='emailPage'),
    url(r'^getEmailStats$', views.getEmailStats, name='getEmailStats'),


    url(r'^enableDisableIndividualEmailLogs$', views.enableDisableIndividualEmailLogs, name='enableDisableIndividualEmailLogs'),
    url(r'^changeDomainEmailLimitsIndividual$', views.changeDomainEmailLimitsIndividual, name='changeDomainEmailLimitsIndividual'),
    url(r'^getEmailLogs$', views.getEmailLogs, name='getEmailLogs'),
    url(r'^flushEmailLogs$', views.flushEmailLogs, name='flushEmailLogs'),

    ## SpamAssassin

    url(r'^SpamAssassin$', views.spamAssassinHome, name='SpamAssassin'),

    url(r'^installSpamAssassin$', views.installSpamAssassin, name='installSpamAssassin'),
    url(r'^installStatusSpamAssassin$', views.installStatusSpamAssassin, name='installStatusSpamAssassin'),
    url(r'^fetchSpamAssassinSettings$', views.fetchSpamAssassinSettings, name='fetchSpamAssassinSettings'),
    url(r'^saveSpamAssassinConfigurations$', views.saveSpamAssassinConfigurations, name='saveSpamAssassinConfigurations'),
    url(r'^fetchPolicyServerStatus$', views.fetchPolicyServerStatus, name='fetchPolicyServerStatus'),

    url(r'^savePolicyServerStatus$', views.savePolicyServerStatus, name='savePolicyServerStatus'),
    url(r'^mailQueue$', views.mailQueue, name='mailQueue'),
    url(r'^fetchMailQueue$', views.fetchMailQueue, name='fetchMailQueue'),
    url(r'^fetchMessage$', views.fetchMessage, name='fetchMessage'),
    url(r'^flushQueue$', views.flushQueue, name='flushQueue'),
    url(r'^delete$', views.delete, name='delete'),
    url(r'^MailScanner$', views.MailScanner, name='MailScanner'),
    url(r'^installMailScanner$', views.installMailScanner, name='installMailScanner'),
    url(r'^installStatusMailScanner$', views.installStatusMailScanner, name='installStatusMailScanner'),



    url(r'^Rspamd$', views.Rspamd, name='Rspamd'),

    url(r'^installRspamd$', views.installRspamd, name='installRspamd'),
    url(r'^installStatusRspamd$', views.installStatusRspamd, name='installStatusRspamd'),
    url(r'^fetchRspamdSettings$', views.fetchRspamdSettings, name='fetchRspamdSettings'),
    url(r'^saveRspamdConfigurations$', views.saveRspamdConfigurations, name='saveRspamdConfigurations'),
    url(r'^savepostfixConfigurations$', views.savepostfixConfigurations, name='savepostfixConfigurations'),
    url(r'^saveRedisConfigurations$', views.saveRedisConfigurations, name='saveRedisConfigurations'),
    url(r'^saveclamavConfigurations$', views.saveclamavConfigurations, name='saveclamavConfigurations'),
    url(r'^unistallRspamd$', views.unistallRspamd, name='unistallRspamd'),
    url(r'^uninstallStatusRspamd$', views.uninstallStatusRspamd, name='uninstallStatusRspamd'),
    url(r'^FetchRspamdLog$', views.FetchRspamdLog, name='FetchRspamdLog'),
    url(r'^RestartRspamd$', views.RestartRspamd, name='RestartRspamd'),

    url(r'^EmailDebugger$', views.EmailDebugger, name='EmailDebugger'),

    url(r'^RunServerLevelEmailChecks$', views.RunServerLevelEmailChecks, name='RunServerLevelEmailChecks'),
    url(r'^ResetEmailConfigurations$', views.ResetEmailConfigurations, name='ResetEmailConfigurations'),
    url(r'^statusFunc$', views.statusFunc, name='statusFunc'),
    url(r'^ReadReport$', views.ReadReport, name='ReadReport'),


    url(r'^debugEmailForSite$', views.debugEmailForSite, name='debugEmailForSite'),
    url(r'^fixMailSSL$', views.fixMailSSL, name='fixMailSSL'),


    url(r'^(?P<domain>(.*))$', views.emailLimits, name='emailLimits'),






]