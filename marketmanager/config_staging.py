from os import environ
from applib.tools import get_db_details_postgres


SECRET_KEY = environ.get("SECRET_KEY", None)
DEBUG = environ.get("MARKET_MANAGER_DEBUG", False)

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["marketmanager", "marketmanager-api", "marketmanager-daemon",
                 "api.wholefolio.io"]

COIN_MANAGER_URL = environ.get("COIN_MANAGER_URL", False)

DATABASES = get_db_details_postgres()

# RabbitMQ
BROKER_URL = environ.get("BROKER_URL")


# Connection to the marketmanager-daemon service
MARKET_MANAGER_DAEMON_HOST = environ.get("MARKET_MANAGER_DAEMON_HOST")
MARKET_MANAGER_DAEMON_PORT = int(environ.get("MARKET_MANAGER_DAEMON_PORT"))
CORS_ORIGIN_WHITELIST = environ.get("CORS_ORIGIN_WHITELIST")
if not CORS_ORIGIN_WHITELIST:
    CORS_ORIGIN_WHITELIST = ["wholefolio.io"]
else:
    CORS_ORIGIN_WHITELIST = CORS_ORIGIN_WHITELIST.split(",")
