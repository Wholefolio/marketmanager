from os import environ
from generate_secret_key import generate
from applib.tools import get_db_details_postgres


SECRET_KEY = environ.get("SECRET_KEY", None)
DEBUG = environ.get("MARKET_MANAGER_DEBUG", False)

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["marketmanager", "marketmanager-api", "marketmanager-daemon",
                 "marketmanager.default.svc.cluster.local"]

COINER_URL = environ.get("COINER_URL", False)
STORAGE_EXCHANGE_URL = environ.get("STORAGE_EXCHANGE_URL", False)

DATABASES = get_db_details_postgres()
