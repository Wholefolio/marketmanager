from .utils import get_db_details


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "5F2b(#0Znpt1H83&RLoIAUBDrQydu6M+i!TE_*zeOjsVC-W@fG"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Production
# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = get_db_details()

COINER_URL = "http://localhost:8002/api/"
STORAGE_SOURCE_URL = "http://localhost:8000/api/sources/"
