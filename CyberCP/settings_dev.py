"""
Development settings for CyberPanel Docker environment
"""
import os
import CyberCP.settings as base_settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Override settings for development
SECRET_KEY = 'dev-secret-key-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Use base settings for core Django configuration
INSTALLED_APPS = base_settings.INSTALLED_APPS
MIDDLEWARE = base_settings.MIDDLEWARE
ROOT_URLCONF = base_settings.ROOT_URLCONF
TEMPLATES = base_settings.TEMPLATES
WSGI_APPLICATION = base_settings.WSGI_APPLICATION
DATABASE_ROUTERS = base_settings.DATABASE_ROUTERS
AUTH_PASSWORD_VALIDATORS = base_settings.AUTH_PASSWORD_VALIDATORS
LANGUAGE_CODE = base_settings.LANGUAGE_CODE
TIME_ZONE = base_settings.TIME_ZONE
USE_I18N = base_settings.USE_I18N
USE_L10N = base_settings.USE_L10N
USE_TZ = base_settings.USE_TZ
LOCALE_PATHS = base_settings.LOCALE_PATHS
LANGUAGES = base_settings.LANGUAGES
DATA_UPLOAD_MAX_MEMORY_SIZE = base_settings.DATA_UPLOAD_MAX_MEMORY_SIZE
X_FRAME_OPTIONS = base_settings.X_FRAME_OPTIONS

# Database configuration for Docker
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE', 'cyberpanel'),
        'USER': os.getenv('MYSQL_USER', 'cyberpanel'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', 'SLTUIUxqhulwsh'),
        'HOST': os.getenv('MYSQL_HOST', 'db'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
            'read_timeout': 60,
            'write_timeout': 60,
        },
    },
    'rootdb': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mysql',
        'USER': 'root',
        'PASSWORD': os.getenv('MYSQL_ROOT_PASSWORD', 'SLTUIUxqhulwsh'),
        'HOST': os.getenv('MYSQL_HOST', 'db'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 60,
            'read_timeout': 60,
            'write_timeout': 60,
        },
    },
}

# Static files configuration for development
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Development logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
