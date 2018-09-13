"""MarketManager main settings."""
import os
import sys
from django.core.exceptions import ImproperlyConfigured

env = os.environ.get('PY_ENV')
if not env:
    # No env variable set - import the development config
    from marketmanager import config_dev as config
else:
    if env == "staging":
        from marketmanager import config_staging as config
    elif env == "production":
        from marketmanager import config_production as config
    else:
        from marketmanager import config_dev as config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Celery config
CELERYD_CONCURRENCY = 4
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TRACK_STARTED = True
BROKER_CONNECTION_TIMEOUT = 3
# Get the configuration
ALLOWED_HOSTS = DATABASES = SECRET_KEY = DEBUG\
              = STORAGE_EXCHANGE_URL = BROKER_URL = None

for setting in ['ALLOWED_HOSTS', 'DATABASES', 'SECRET_KEY', "DEBUG",
                "STORAGE_EXCHANGE_URL", "BROKER_URL"]:
    try:
        globals()[setting] = getattr(config, setting)
    except AttributeError:
        raise ImproperlyConfigured(
            "Mandatory setting {} is missing from config.".format(setting)
        )

CORS_ORIGIN_WHITELIST = ["testfrontend.internal.cyanopus.com",
                         "localhost:3000",
                         "localhost"]

CACHE_TTL = 60
if "test" in sys.argv:
    # Don't cache while testing
    pass
CACHE_TTL = 0

LOG_LEVEL = "INFO"
if DEBUG:
    LOG_LEVEL = "DEBUG"


# Daemon config
MARKET_MANAGER_DAEMON = {
                 "threads": 2,
                 "lock_file": "/tmp/.lock.marketmanager",
                 "sock_file": "/tmp/.sock.marketmanager",
                 "daemon": True,
                 "socket_port": 5000,
                 "processes": {
                    "incoming": None, "scheduler": None, "poller": None
                 },
                 "logging": {
                     "version": 1,
                     "disable_existing_loggers": False,
                     "formatters": {
                         "simple": {
                             "format": "%(asctime)s %(processName)s [%(funcName)s][%(levelname)s]: %(message)s"
                         }
                     },
                     "handlers": {
                         "log_handler": {
                            "class": "logging.StreamHandler",
                            "level": LOG_LEVEL,
                            "formatter": "simple",
                            "stream": "ext://sys.stderr"
                            }
                     },
                     "root": {
                         "level": LOG_LEVEL,
                         "handlers": ["log_handler"]
                     }
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
     'PAGE_SIZE': 10000
}
# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_celery_results',
    'django_filters',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = "/marketmanager/static/"
