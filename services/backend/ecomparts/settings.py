"""
Django settings for ECOMPARTS project.
"""

from pathlib import Path
import os
from decouple import config
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS',
'localhost,127.0.0.1,backend').split(',')

# Application definition
INSTALLED_APPS = [
    #'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'mptt',
    'shortuuid', 
    
    # Local apps
    'apps.core',
    'apps.marketplace',
    'apps.products',
    'apps.orders',
    'apps.vehicles',
    'apps.customer',
    'apps.cart',
    'apps.sync',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.marketplace.middleware.TenantScopeMiddleware',
]

ROOT_URLCONF = 'ecomparts.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecomparts.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DJANGO_DB_NAME', 'ecomparts_django'),
        'USER': os.environ.get('DJANGO_DB_USER', 'ecomparts_user'),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', ''),
        'HOST': os.environ.get('DJANGO_DB_HOST', 'postgres'),
        'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
        'connect_timeout': 10,
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = f"redis://{os.getenv('REDIS_HOST', 'ecomparts-redis')}:{os.getenv('REDIS_PORT', '6379')}/0"
CELERY_RESULT_BACKEND = f"redis://{os.getenv('REDIS_HOST', 'ecomparts-redis')}:{os.getenv('REDIS_PORT', '6379')}/0"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Lima'

# Celery Beat — tareas periódicas
from celery.schedules import crontab  # noqa: E402
CELERY_BEAT_SCHEDULE = {
    # Expirar SubOrders que superaron su payment_deadline sin completar el pago.
    # Se ejecuta cada 15 minutos; el máximo retraso posible es 15 min + margen de ejecución.
    'expire-pending-suborders': {
        'task': 'apps.orders.tasks.expire_pending_suborders',
        'schedule': crontab(minute='*/15'),
    },
}

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', 'ecomparts-redis')}:{os.getenv('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        'SOCKET_CONNECT_TIMEOUT': 5,
        'SOCKET_TIMEOUT': 5,
        }
        }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='es-pe')
TIME_ZONE = config('TIMEZONE', default='America/Lima')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False, # Simplificado para MVP
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

"""
# Redis
REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=f'{REDIS_URL}/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=f'{REDIS_URL}/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
"""

# Odoo Connection
ODOO_CONFIG = {
'URL': os.environ.get('ODOO_URL', 'http://ecomparts-odoo-shared:8069'),
'DB': os.environ.get('ODOO_DB', 'ecomparts_odoo'),
'USERNAME': os.environ.get('ODOO_USERNAME', 'admin@ecomparts.local'),
'PASSWORD': os.environ.get('ODOO_PASSWORD', ''),
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
        'format': '{levelname} {asctime} {module} {message}',
        'style': '{',
        },
    },
    'handlers': {
        'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
            },
    },
    'loggers': {
        'django': {'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'middleware': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
            },
    },
}

# Spectacular (API Docs)
SPECTACULAR_SETTINGS = {
    'TITLE': 'ECOMPARTS API',
    'DESCRIPTION': 'API REST para Marketplace Multi-Tenant de Autopartes',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


JAZZMIN_SETTINGS = {
    'show_ui_builder': False,
    'color': 'blue',
    # Configuración del sidebar
    "show_sidebar": True,
    "navigation_expanded": False,  # Sidebar colapsado por defecto
    "hide_apps": [],  # Apps a ocultar completamente

"icons": {
        "products.Category": "fas fa-list",
        "vehicles.Marca": "fas fa-tag",
        "vehicles.ModeloVehiculo": "fas fa-car",
        "vehicles.Motor": "fas fa-cog",
        "products.Product": "fas fa-box",
        "vehicles.VarianteVehiculo": "fas fa-cogs",
    },
}

# ==============================================
# ODOO - Variables individuales para compatibilidad
# ==============================================
ODOO_URL = ODOO_CONFIG['URL']
ODOO_DB = ODOO_CONFIG['DB']
ODOO_USERNAME = ODOO_CONFIG['USERNAME']
ODOO_PASSWORD = ODOO_CONFIG['PASSWORD']

# ============================================================================
# ODOO WEBHOOK CONFIGURATION
# ============================================================================
ODOO_WEBHOOK_TOKEN = os.getenv('ODOO_WEBHOOK_TOKEN', 'dev-webhook-secret-token-2026')
