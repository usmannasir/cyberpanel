"""
WSGI config for CyberCP project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os


from django.core.wsgi import get_wsgi_application
from CyberCP.requestBodyDrain import reading_bodies_to_the_end

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

application = reading_bodies_to_the_end(get_wsgi_application())
