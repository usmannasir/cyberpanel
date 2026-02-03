"""
WSGI config for CyberCP project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os
import sys

# Ensure CyberPanel app path takes precedence over system 'firewall' package
PROJECT_ROOT = '/usr/local/CyberCP'
while PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

application = get_wsgi_application()
