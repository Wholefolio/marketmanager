"""Common utilities for the storage project."""
from os import environ
from django.core.exceptions import ImproperlyConfigured


def get_db_details():
    """Get the DB details from a file or env variable."""
    ENV_VARIABLES = ("DB_HOSTNAME", "DB_USERNAME", "DB_PASSWORD",
                     "DB_DATABASE")
    DATABASES = {}
    # We must have EACH env variable so that we can access the DB
    for i in ENV_VARIABLES:
        if i not in environ:
            raise ImproperlyConfigured(
                    "Missing mandatory enviromental variable {}".format(i))

    # Check for the DB port
    if "DB_PORT" in environ:
        db_port = environ.get("DB_PORT")
    else:
        db_port = "5432"

    DATABASES['default'] = {
                   "ENGINE": "django.db.backends.postgresql",
                   "NAME": environ.get("DB_DATABASE"),
                   "USER": environ.get("DB_USERNAME"),
                   "PASSWORD": environ.get("DB_PASSWORD"),
                   "HOST": environ.get("DB_HOSTNAME"),
                   "PORT": db_port}
    return DATABASES
