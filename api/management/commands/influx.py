from django.core.management.base import BaseCommand


from api.models_influx import test


class Command(BaseCommand):
    help = "Test"


    def handle(self, *args, **options):
        test()
