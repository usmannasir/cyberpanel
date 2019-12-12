from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.loadEmailHome, name='loadEmailHome'),
    url(r'^createEmailAccount', views.createEmailAccount, name='createEmailAccount'),
    url(r'^listEmails$', views.listEmails, name='listEmails'),
    url(r'^submitEmailCreation', views.submitEmailCreation, name='submitEmailCreation'),
    url(r'^fetchEmails$', views.fetchEmails, name='fetchEmails'),


    ## Mail Forwardings
    url(r'^emailForwarding$', views.emailForwarding, name='emailForwarding'),
    url(r'^submitEmailForwardingCreation$', views.submitEmailForwardingCreation, name='submitEmailForwardingCreation'),
    url(r'^fetchCurrentForwardings$', views.fetchCurrentForwardings, name='fetchCurrentForwardings'),
    url(r'^submitForwardDeletion$', views.submitForwardDeletion, name='submitForwardDeletion'),


    ## Delete email
    url(r'^deleteEmailAccount', views.deleteEmailAccount, name='deleteEmailAccount'),
    url(r'^getEmailsForDomain$', views.getEmailsForDomain, name='getEmailsForDomain'),
    url(r'^submitEmailDeletion', views.submitEmailDeletion, name='submitEmailDeletion'),


    ## Change email password
    url(r'^changeEmailAccountPassword', views.changeEmailAccountPassword, name='changeEmailAccountPassword'),
    url(r'^submitPasswordChange', views.submitPasswordChange, name='submitPasswordChange'),

    ## DKIM Manager

    url(r'^dkimManager', views.dkimManager, name='dkimManager'),
    url(r'^fetchDKIMKeys', views.fetchDKIMKeys, name='fetchDKIMKeys'),
    url(r'^generateDKIMKeys$', views.generateDKIMKeys, name='generateDKIMKeys'),

    url(r'^installOpenDKIM', views.installOpenDKIM, name='installOpenDKIM'),
    url(r'^installStatusOpenDKIM', views.installStatusOpenDKIM, name='installStatusOpenDKIM'),


]