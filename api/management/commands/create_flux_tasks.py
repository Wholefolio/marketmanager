import json
from django.core.management.base import BaseCommand
from django_influxdb.models import InfluxTasks
from django_influxdb.tasks import EveryTask


class Command(BaseCommand):
    help = "Create Influx tasks from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store", dest="json", default="configs/influx_tasks.json",
                            help="Path to JSON file to use for import")

    def handle(self, *args, **options):
        json_file = options["json"]
        with open(json_file, "r") as f:
            json_data = json.load(f)
        for task in json_data:
            with open(f'flux/{task["flux_filename"]}') as f:
                flux = f.read()
            task.pop("flux_filename")
            obj = InfluxTasks(flux=flux, **task)
            obj.save()
            influx_task = EveryTask(name=task["name"])
            influx_task.create_from_db()
            self.stdout.write(f"Successfully created task {task['name']}")
