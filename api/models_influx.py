from functools import reduce
import logging
from django.conf import settings
from marketmanager.influxdb import Client as InfluxClient

logger = logging.getLogger("marketmanager")


def generate_tags(tags: list, data: dict, exc_on_missing: bool = True) -> dict:
    """Generate a dictionary of tag->value pairs from a list of tags and a data dict"""
    output = {}
    for tag in tags:
        if exc_on_missing and tag not in data:
            raise ValueError(f"Missing required tag {tag} from model data")
        output[tag] = data[tag]
    return output


class InfluxModel:
    """Influx Base Model - concept was taken from Django ORM models"""
    tags = {}
    field = None
    field_type = None

    def __init__(self, **kwargs):
        self.data = kwargs
        self.validated_data = {"tags": {}, "fields": []}

    def _validate(self) -> None:
        """Validate the tags and fields in the class are present in the data"""
        self.validated_data["tags"] = generate_tags(self.tags, self.data)
        if self.field not in self.data:
            raise ValueError(f"Setting the field is mandatory. Missing field: {self.field}")
        else:
            value = self.data[self.field]
            if self.field_type:
                # Cast the field type
                value = self.field_type(value)
            self.validated_data["fields"][self.field] = value

    def _clean_result(self, result):
        """Clean out InfluxDB internal fields and tags and leave only the model tags"""
        current = result.values
        output = {}
        try:
            output["timestamp"] = current["_time"]
        except KeyError:
            pass
        for tag in self.tags:
            output[tag] = current[tag]
        try:
            output[current["_field"]] = current["_value"]
        except KeyError:
            pass
        return output

    def clean_results(self, results):
        output = []
        for result in results:
            output.append(self._clean_result(result))
        return output

    def _flatten_results(self, data):
        """Influx returns the records as a list of tables, which have lists of results.
        Flatten the results to a simple list of results."""
        def red(a, b):
            """Reducer function to flatten the list of table records"""
            if type(a) == list:
                return a + b.records
            return a.records + b.records
        return reduce(red, data)

    def filter(self, time_start: str, time_stop: str = "now()"):
        """Query Influx based on the tags from the object (the object must be initialized with the tags)."""
        client = InfluxClient()
        tags = generate_tags(self.tags, self.data)
        tables = client.query(self.measurement, time_start=time_start, time_stop=time_stop, tags=tags,
                              drop_internal_fields=True)
        results = self._flatten_results(tables)
        return self.clean_results(results)

    def save(self):
        """Creates a new timeseries entry in Influx from this object"""
        self._validate()
        client = InfluxClient()
        result = client.write(self.measurement, **self.validated_data)
        return result


class FiatMarketModel(InfluxModel):
    influx_tags = ["currency", "exchange_id"]
    field = "price"
    field_type = float
    measurement = settings.INFLUX_MEASUREMENT_FIAT_MARKETS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET


class PairsMarketModel(InfluxModel):
    influx_tags = ["base", "quote", "exchange_id"]
    field = "last"
    field_type = float
    measurement = settings.INFLUX_MEASUREMENT_PAIRS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET
