from django.urls import path, include
from . import views

urlpatterns = [
    path('installed', views.installed, name='installed'),
    # Focused mounts for fail2ban / auto-ban (full pluginHolder store UI is a follow-up PR)
    path('fail2ban/', include('fail2ban.urls')),
    path('autoBanSecurityAlerts/', include('autoBanSecurityAlerts.urls')),
]
