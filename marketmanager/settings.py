"""MarketManager main settings."""
import os
import sys
from django.core.exceptions import ImproperlyConfigured

from applib.tools import get_db_details_postgres, bool_eval
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Celery config
CELERYD_CONCURRENCY = 4
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TRACK_STARTED = True
CELERYD_LOG_FORMAT = '{"timestamp":"%(asctime)s","severity":"%(levelname)s",'
CELERYD_LOG_FORMAT += '"worker":"%(processName)s","task":"%(task_name)s",'
CELERYD_LOG_FORMAT += ',"task_id":"%(task_id)s","message":"%(message)s"}'
BROKER_CONNECTION_TIMEOUT = 3
BROKER_CONNECTION_MAX_RETRIES = 5
BROKER_POOL_LIMIT = None

# Get the configuration for Marketmanager
ALLOWED_HOSTS = SECRET_KEY = MARKET_MANAGER_DAEMON_HOST \
              = STORAGE_EXCHANGE_URL = CORS_ORIGIN_WHITELIST = REDIS_HOST \
              = MARKET_MANAGER_DAEMON_PORT = None

DATABASES = get_db_details_postgres()
DEBUG = bool_eval(os.environ.get("DEBUG", False))

MARKET_STALE_DAYS = os.environ.get("MARKET_STALE_DAYS", 7)

env_vars = ["ALLOWED_HOSTS", "SECRET_KEY", "COIN_MANAGER_URL", "REDIS_HOST", "MARKET_MANAGER_DAEMON_HOST",
            "MARKET_MANAGER_DAEMON_PORT", "CORS_ORIGIN_WHITELIST", "SECURE_SSL_REDIRECT"]
for key in env_vars:
    if key not in os.environ:
        raise ImproperlyConfigured("Missing mandatory Env variable {}".format(key))
    value = os.environ.get(key, None)
    if key == "ALLOWED_HOSTS" or key == "SECURE_REDIRECT_EXEMPT" or key == "CORS_ORIGIN_WHITELIST":
        globals()[key] = value.split(",")
    elif key == "SECURE_SSL_REDIRECT":
        globals()[key] = bool_eval(value)
    else:
        globals()[key] = value

SECURE_REDIRECT_EXEMPT = ["healthz", "daemon_status", "task_results",
                          "daemon_status", "exchange_statuses", "internal"]
BROKER_URL = "redis://{}/0".format(REDIS_HOST)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}/1".format(REDIS_HOST),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "marketmanager"
    }
}
CACHE_TTL = 60
if "test" in sys.argv:
    # Don't cache while testing
    CACHE_TTL = 0
    del CACHES
    SECURE_SSL_REDIRECT = False

LOG_LEVEL = "INFO"
if DEBUG:
    LOG_LEVEL = "DEBUG"

EXCHANGE_TIMEOUT = 120
# Daemon config
MARKET_MANAGER_DAEMON = {
    "threads": 2,
    "lock_file": "/tmp/.lock.marketmanager",
    "sock_file": "/tmp/.sock.marketmanager",
    "daemon": False,
    "socket_port": 5000,
    "processes": {
        "incoming": None, "scheduler": None, "poller": None
    }
}

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# REST framework configuration
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS':
        ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',),
    'PAGE_SIZE': 10000
}
# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_celery_results',
    'django_filters',
    'daemon',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'marketmanager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'marketmanager.wsgi.application'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

JSON_FORMAT = '{"timestamp":"%(asctime)s","module":"%(module)s"'
JSON_FORMAT += ',"function":"%(funcName)s","severity":"%(levelname)s"'
JSON_FORMAT += ',"message":"%(message)s"}'

JSON_FORMAT_CELERY = JSON_FORMAT[:-1] + ',"task_id":"%(task_id)s",'
JSON_FORMAT_CELERY += '"exchange":"%(exchange)s"}'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'remove_healthchecks': {
            '()': 'applib.log.FilterHealthChecks',
        },
    },
    'formatters': {
        # Formatter for the daemon/celery
        'stdout-formater': {
            'format': JSON_FORMAT
        },
        'stdout-formater-celery': {
            'format': JSON_FORMAT_CELERY
        },
        # Formatter for requests
        'django.server': {
           'format': '{"timestamp":"%(server_time)s","message":%(message)s"}',
        }
    },
    'handlers': {
        'stdout-handler': {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            'formatter': 'stdout-formater',
            "stream": "ext://sys.stdout"
        },
        'stdout-handler-celery': {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            'formatter': 'stdout-formater-celery',
            "stream": "ext://sys.stdout"
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'filters': ['remove_healthchecks'],
            'formatter': 'django.server',
        },
    },
    'loggers': {
        'marketmanager': {
            'handlers': ['stdout-handler'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'marketmanager-celery': {
            'handlers': ['stdout-handler-celery'],
            'level': LOG_LEVEL,
            'propogate': False
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR + "/static/"
