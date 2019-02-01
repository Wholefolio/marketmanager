from django.core.management.base import BaseCommand

from api.tasks import fetch_exchange_data
from api.models import Exchange


class Command(BaseCommand):
    help = 'Run the selected adapter.'

    def add_arguments(self, parser):
        parser.add_argument('id', action="store", type=int)
        parser.add_argument('--celery', action="store_true", dest="celery",
                            help="Send to celery as a task", required=False)

    def handle(self, *args, **options):
        # Check if the adapter exists
        adapter = Exchange.objects.get(id=options["id"])
        if not adapter:
            msg = "No adapter with that ID exists."
            return self.stdout.write(self.style.ERROR(msg))
        if options["celery"]:
            task_id = fetch_exchange_data.delay(options["id"])
            msg = "Running exchange data fetch through celery. "
            msg += "Task ID: {}".format(task_id)
            return self.stdout.write(self.style.SUCCESS(msg))
        fetch_exchange_data(options["id"])
        return self.style.SUCCESS("Finished running adapter.")
