from django.core.management.base import BaseCommand
from api.models import Exchange


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available ccxt exchanges."
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--exchange_id", action="append",
                           dest="exchange_id",
                           help="List of existing exchange ids")
        group.add_argument("--all", action="store_true", dest="all",
                           help=all_help)

    def handle(self, *args, **options):
        if options["all"]:
            for exchange in Exchange.objects.all():
                exchange.enabled = False
                exchange.save()
            return self.style.SUCCESS("All existing exchanges modified!")
        for i in options["exchange_id"]:
            try:
                exchange = Exchange.objects.get(id=i)
                exchange.enabled = False
                exchange.save()
                msg = "Exchange disabled successfully: {}".format(exchange.id)
                self.stdout.write(self.style.SUCCESS(msg))
            except Exchange.DoesNotExist:
                msg = "Exchange not found"
                return self.stdout.write(self.style.ERROR(msg))
