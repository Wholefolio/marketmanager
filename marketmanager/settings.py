"""MarketManager main settings."""

import os
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

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get the configuration
ALLOWED_HOSTS = DATABASES = SECRET_KEY = COINER_URL = DEBUG\
              = STORAGE_SOURCE_URL = None

for setting in ['ALLOWED_HOSTS', 'DATABASES', 'SECRET_KEY', "DEBUG",
                'COINER_URL', "STORAGE_SOURCE_URL"]:
    try:
        globals()[setting] = getattr(config, setting)
    except AttributeError:
        raise ImproperlyConfigured(
            "Mandatory setting {} is missing from config.".format(setting)
        )

COINER_URLS = {"adapter": "{}run_adapter/".format(COINER_URL),
               "exchange": "{}fetch_exchange_data/".format(COINER_URL),
               "results": "{}get_results/".format(COINER_URL)}
# Coiner daemon config
MARKET_MANAGER_DAEMON = {
                 "threads": 2,
                 "lock_file": "/tmp/.lock.marketmanager",
                 "sock_file": "/tmp/.sock.marketmanager",
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
                            "level": "INFO",
                            "formatter": "simple",
                            "stream": "ext://sys.stderr"
                            }
                     },
                     "root": {
                         "level": "DEBUG",
                         "handlers": ["log_handler"]
                     }
                 }
                }

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# REST framework configuration
REST_FRAMEWORK = {
  'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination'
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
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
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
