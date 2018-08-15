from os import environ
from generate_secret_key import generate
from marketmanager.utils import get_db_details
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = generate()
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.get("COINER_DEBUG", False)

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["marketmanager", "marketmanager.internal.cyanopus.com",
                 "marketmanager.default.svc.cluster.local"]

COINER_URL = environ.get("COINER_URL", False)

DATABASES = get_db_details()
