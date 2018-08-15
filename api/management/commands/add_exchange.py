from django.core.management.base import BaseCommand
from api.models import Exchange
from api.utils import create_source, get_source


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available ccxt exchanges and create\
                    sources for them in the storage APP."
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--name", action="store", dest="name",
                           help="source code file")
        group.add_argument("--all", action="store_true", dest="all",
                           help=all_help)
        parser.add_argument("--interval", action="store", dest="interval",
                            help="adapter interval", default=300)
        parser.add_argument("--source-id", action="store", dest="source_id",
                            help="Storage app source ID.", required=False)

    def handle(self, *args, **options):
        if options["all"]:
            pass
        if not options.get("storage_source_id"):
            self.stdout.write("No storage source - checking if one exists.")
            result = get_source(options["name"])
            if isinstance(result, int):
                msg = "Failed getting from storage. Code: {}".format(result)
                self.stderr.write(msg)
                return
            if result["count"] == 0:
                # We don't have an existing source
                result = create_source(options["name"])
                if isinstance(result, int):
                    msg = "Failed creating source in storage."
                    msg += "Code: {}".format(result)
                    self.stderr.write(msg)
                    return
                source_id = result["id"]
            else:
                source_id = result["results"][0]["id"]
                msg = "Existing storage source entry: {}".format(source_id)
                self.stdout.write(msg)
        else:
            source_id = options["storage_source_id"]
        exc = Exchange(name=options["name"], interval=options["interval"],
                       storage_source_id=source_id)
        exc.save()
        msg = "Exchange successfully created - {}".format(exc.id)
        self.stdout.write(self.style.SUCCESS(msg))
