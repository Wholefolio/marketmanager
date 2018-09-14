from applib.tools import get_db_details_postgres


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "5F2b(#0Znpt1H83&RLoIAUBDrQydu6M+i!TE_*zeOjsVC-W@fG"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Specify the allowed hosts for the app
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Production
# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = get_db_details_postgres()

COIN_MANAGER_URL = "http://localhost:8003/api/"
SUMMARIZER_EXCHANGE_URL = "http://localhost:8005/api/summarize_exchange_data/"

BROKER_URL = "amqp://guest:guest@rabbitmq:5672//"

# Connection to the marketmanager-daemon service
MARKET_MANAGER_DAEMON_HOST = "localhost"
MARKET_MANAGER_DAEMON_PORT = 5000
