from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
import requests
import os
import ccxt

from api.models import Exchange, ExchangeStatus


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available exchanges"
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--name", action="store", dest="name",
                           help="name of the exchange")
        group.add_argument("--all", action="store_true", dest="all",
                           help=all_help)
        parser.add_argument("--interval", action="store", dest="interval",
                            help="adapter interval", default=300)
        parser.add_argument("--marketmanager", action="store",
                            dest="manager_host", required=False,
                            help="marketmanager host", default=300)
        parser.add_argument("--exchange-id", action="store",
                            dest="exchange_id",
                            help="Exchange ID on remote host.", required=False)

    def create_all(self, interval):
        for exc in ccxt.exchanges:
            self.create(exc, interval)

    def create(self, name, interval):
        data = self.get_exchange_details(name)
        if "error" in data:
            return data["error"]
        print(self.marketmanager_host)
        if not self.marketmanager_host:
            self.create_local(name.capitalize(), interval, data)
        else:
            self.create_remote(name.capitalize(), interval, data)

    def create_local(self, name, interval, data):
        """Create the exchange locally via the Model."""
        exc = Exchange(name=name, interval=interval, **data)
        try:
            exc.save()
            self.stdout.write("Created exchange {}".format(name))
            status = ExchangeStatus(exchange=exc)
            status.save()
        except IntegrityError:
            self.stderr.write("Exchange {} already exists".format(name))

    def create_remote(self, name, interval, data):
        data = {"name": name, "interval": interval, **data}
        url = self.marketmanager_host + "/api/exchanges/"
        response = requests.post(url, data=data)
        self.stdout.write(response.json())

    def get_exchange_details(self, name):
        """Create the data dict with the exchange name, api url and www url."""
        try:
            exchange_object = getattr(ccxt, name.lower())()
        except AttributeError:
            msg = {"error": "Not existing exchange"}
            print(msg)
            return msg
        if isinstance(exchange_object.urls['api'], dict):
            if "public" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['public']
            elif "rest" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['rest']
            elif "current" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['current']
        else:
            api_url = exchange_object.urls['api']
        url = exchange_object.urls['www']
        logo = exchange_object.urls['logo']
        return {"api_url": api_url, "url": url, "logo": logo}

    def handle(self, *args, **options):
        self.marketmanager_host = None
        # Check if we are running this on a remote instance or locally
        if "MARKETMANAGER_HOST" in os.environ:
            self.marketmanager_host = os.environ["MARKETMANAGER_HOST"]
        if options.get("marketmanager_host"):
            self.marketmanager_host = options["adapter"]
        if options["all"]:
            return self.create_all(options["interval"])
        self.create(options["name"], options["interval"])
