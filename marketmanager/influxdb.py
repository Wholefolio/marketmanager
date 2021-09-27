import logging
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger("marketmanager")


class Client:
    """InfluxDB client"""
    def __init__(self, bucket: str = settings.INFLUXDB_DEFAULT_BUCKET):
        self.client = InfluxDBClient(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN, timeout=3000)
        self.bucket = bucket

    def _build_query(self, measurement: str, time_start: str, time_stop: str = "now()",
                     tags: dict = {}, drop_internal_fields: bool = False,
                     additional_influx_functions: list = []):
        """Build InfluxDB query, func is to be wrapped."""
        query = f'from(bucket: "{self.bucket}")'
        query += f' |> range(start: -{time_start}, stop: {time_stop})'
        query += f' |> filter(fn: (r) => (r._measurement == "{measurement}"))'
        if tags:
            for tag, value in tags.items():
                query += f' |> filter(fn: (r) => (r.{tag} == "{value}"))'
        if drop_internal_fields:
            query += f' |> drop(columns: ["_start", "_stop"])'
        for add_func in additional_influx_functions:
            query += f' |> {add_func}'
        return query

    def write(self, measurement: str, tags: dict, fields: list, timestamp: bool = True):
        """Write a single timeseries point to the InfluxDB"""
        point = Point(measurement)
        for tag, value in tags.items():
            point.tag(tag, value)
        for field in fields:
            point.field(field["key"], field["value"])
        if timestamp:
            point.time(timezone.now(), WritePrecision.MS)
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        return write_api.write(self.bucket, settings.INFLUXDB_ORG, point)

    def query(self, measurement: str, time_start: str, time_stop: str = "now()",
              tags: dict = {}, drop_internal_fields: bool = False,
              additional_influx_functions: list = []):
        """
        Query the InfluxDB - returns List of InfluxDB tables which contain records. Params:
        * measurement - InfluxDB measurement to fetch the results from
        * time_start - point of time to start search from - relative/absolute
        * time_stop - point of time to start search from - relative/absolute/now()
        * tags - dictionary of tags to add to the query
        * drop_internal_fields - flag to discard InfluxDB internal fields on query
        * additional_influx_functions - a list of InfluxDB functions to apply as a list of strings. Example:
        ["limit(n: 5)"]
        """
        query = self._build_query(measurement, time_start, time_stop, tags, drop_internal_fields,
                                  additional_influx_functions)
        logger.debug(f"Running query: \"{query}\"")
        return self.client.query_api().query(query, org=settings.INFLUXDB_ORG,)
