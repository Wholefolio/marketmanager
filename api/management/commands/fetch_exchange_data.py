from django.core.management.base import BaseCommand
from django.utils import timezone

from api.tasks import fetch_exchange_data
from api.models import Exchange, ExchangeStatus


class Command(BaseCommand):
    help = 'Run the selected exchange.'

    def add_arguments(self, parser):
        parser.add_argument('id', action="store", type=int)
        parser.add_argument('--celery', action="store_true", dest="celery",
                            help="Send to celery as a task", required=False)

    def handle(self, *args, **options):
        # Check if the exchange exists
        queryset = Exchange.objects.filter(id=options["id"])
        if not queryset:
            msg = "No exchange with that ID exists."
            return self.stdout.write(self.style.ERROR(msg))
        exchange = queryset[0]
        status = ExchangeStatus.objects.get(exchange=exchange)
        status.running = True
        status.time_started = timezone.now()
        status.save()
        if options["celery"]:
            task_id = fetch_exchange_data.delay(exchange.id)
            msg = "Running exchange data fetch through celery. "
            msg += "Task ID: {}".format(task_id)
            return self.stdout.write(self.style.SUCCESS(msg))
        fetch_exchange_data(exchange.id)
        return self.style.SUCCESS("Finished running exchange gathering data.")
