import logging
from django.conf import settings
from marketmanager.influxdb import Client as InfluxClient

logger = logging.getLogger("marketmanager")


class InfluxModel:
    """Influx Base Model - concept was taken from Django ORM models"""
    tags = []
    field = None
    field_type = None

    def __init__(self, **kwargs):
        self.data = kwargs
        self.validated_data = {"tags": [], "fields": []}

    @staticmethod
    def get_fields(cls):
        return cls.fields

    @staticmethod
    def get_tags(cls):
        return cls.tags

    def _validate(self):
        """Validate the tags and fields in the class are present in the data"""
        for tag in self.tags:
            if tag not in self.data:
                raise ValueError(f"Missing required tag {tag}")
            else:
                self.validated_data["tags"].append({"key": tag, "value": self.data[tag]})
        if self.field not in self.data:
            raise ValueError(f"Setting the field is mandatory. Missing field: {self.field}")
        else:
            value = self.data[self.field]
            if self.field_type:
                # Cast the field type
                value = self.field_type(value)
            self.validated_data["fields"].append({"key": self.field, "value": value})

    def _clean_result(self, result):
        """Clean out InfluxDB internal fields and tags and leave only the model tags"""
        current = result.values
        output = {}
        output["timestamp"] = current["_time"]
        for tag in self.tags:
            output[tag] = current[tag]
        try:
            output[current["_field"]] = current["_value"]
        except KeyError:
            pass
        return output

    def _flatten_results(self, data):
        """Influx returns the records as a list of tables, which have lists of results.
        Flatten the results to a simple list of results."""
        output = []
        for table in data:
            for result in table.records:
                clean_result = self._clean_result(result)
                output.append(clean_result)
        return output

    def filter(self, time_start: str, time_stop: str = None):
        """Query Influx based on the tags from the object"""
        client = InfluxClient()
        tags = []
        for tag in self.tags:
            if tag in self.data:
                tags.append({"key": tag, "value": self.data[tag]})
        results = client.query(self.measurement, time_start=time_start, tags=tags, drop_internal_fields=True)
        return self._flatten_results(results)

    def save(self):
        """Creates a new timeseries entry in Influx from this object"""
        self._validate()
        client = InfluxClient()
        result = client.write(self.measurement, **self.validated_data)
        return result


class FiatMarketModel(InfluxModel):
    tags = ["currency", "exchange_id"]
    field = "price"
    field_type = float
    measurement = settings.INFLUX_MEASUREMENT_FIAT_MARKETS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET


class PairsMarketModel(InfluxModel):
    tags = ["base", "quote", "exchange_id"]
    field = "last"
    field_type = float
    measurement = settings.INFLUX_MEASUREMENT_PAIRS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET
