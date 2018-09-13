from django.core.management.base import BaseCommand
from api.models import Exchange


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available ccxt exchanges."
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--exchange_id", action="append", dest="exchange_id",
                           help="List of existing exchange ids")

        group.add_argument("--all", action="store_true", dest="all",
                           help=all_help)
        act_group = parser.add_mutually_exclusive_group(required=True)
        act_group.add_argument("--block", action="store_false", dest="enable",
                               help="block an exchange from running",
                               default=False)
        act_group.add_argument("--enable", action="store_true", dest="enable",
                               help="enable an exchange",
                               default=False)

    def handle(self, *args, **options):
        if options["all"]:
            for exchange in Exchange.objects.all():
                exchange.enabled = options["enable"]
                exchange.save()
            return self.style.SUCCESS("All existing exchanges modified!")
        for i in options["exchange_id"]:
            try:
                exchange = Exchange.objects.get(id=i)
                exchange.enabled = options["enable"]
                exchange.save()
                msg = "Exchange changed successfully: {}".format(exchange.id)
                self.stdout.write(self.style.SUCCESS(msg))
            except Exchange.DoesNotExist:
                msg = "Exchange not found"
                return self.stdout.write(self.style.ERROR(msg))
