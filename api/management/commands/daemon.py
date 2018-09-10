"""MarketManager daemon management."""
from django.core.management.base import BaseCommand
from django.conf import settings

from marketmanager.marketmanager import MarketManager
from daemonlib.tools import start, stop, status


app_name = "MarketManager"


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "Control the MarketManager daemon."
        commands = ["start", "stop", "restart", "status"]
        parser.add_argument("operation", choices=commands,
                            help=all_help)

    def handle(self, *args, **options):
        config = settings.MARKET_MANAGER_DAEMON
        command = options['operation']
        if command == 'start':
                start(app_name, MarketManager, config)
        elif command == 'stop':
            stop(config)
        elif command == 'restart':
            stop(config)
            start(app_name, MarketManager, config)
        else:
            status(app_name, config)
