# -*- coding: utf-8 -*-

from django.urls import path
from . import webauthn_views

urlpatterns = [
    # WebAuthn Registration
    path('registration/start/', webauthn_views.webauthn_registration_start, name='webauthn_registration_start'),
    path('registration/complete/', webauthn_views.webauthn_registration_complete, name='webauthn_registration_complete'),
    
    # WebAuthn Authentication
    path('authentication/start/', webauthn_views.webauthn_authentication_start, name='webauthn_authentication_start'),
    path('authentication/complete/', webauthn_views.webauthn_authentication_complete, name='webauthn_authentication_complete'),
    
    # WebAuthn Credential Management
    path('credentials/<str:username>/', webauthn_views.webauthn_credentials_list, name='webauthn_credentials_list'),
    path('credential/delete/', webauthn_views.webauthn_credential_delete, name='webauthn_credential_delete'),
    path('credential/update/', webauthn_views.webauthn_credential_update, name='webauthn_credential_update'),
    
    # WebAuthn Settings
    path('settings/update/', webauthn_views.webauthn_settings_update, name='webauthn_settings_update'),
    
    # WebAuthn Maintenance
    path('cleanup/', webauthn_views.webauthn_cleanup, name='webauthn_cleanup'),
]
