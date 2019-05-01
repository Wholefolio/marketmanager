from os import environ
from django.core.exceptions import ImproperlyConfigured
from applib.tools import get_db_details_postgres, bool_eval

ENV_VARS = ["SECRET_KEY", "COIN_MANAGER_URL", "SECURE_SSL_REDIRECT",
            "MARKET_MANAGER_DAEMON_HOST", "MARKET_MANAGER_DAEMON_PORT",
            "CORS_ORIGIN_WHITELIST", "REDIS_HOST"]
CORS_ORIGIN_WHITELIST = None
for var in ENV_VARS:
    value = environ.get(var, False)
    if value:
        globals()[var] = value
    else:
        msg = "Missing env variable {} from config".format(var)
        raise ImproperlyConfigured(msg)

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["marketmanager", "marketmanager-api", "marketmanager-daemon",
                 "api.wholefolio.io"]

DATABASES = get_db_details_postgres()

CORS_ORIGIN_WHITELIST = CORS_ORIGIN_WHITELIST.split(",")
DEBUG = bool_eval(environ.get("DEBUG", False))
SECURE_SSL_REDIRECT = bool_eval(SECURE_SSL_REDIRECT)
