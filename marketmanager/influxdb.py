import logging
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger("marketmanager")


class Client:
    """InfluxDB client"""
    def __init__(self, bucket: str = settings.INFLUXDB_DEFAULT_BUCKET):
        self.client = InfluxDBClient(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN)
        self.bucket = bucket

    def write(self, measurement: str, tags: list, fields: list, timestamp: bool = True):
        """Write a single timeseries point to the InfluxDB"""
        point = Point(measurement)
        for tag in tags:
            point.tag(tag["key"], tag["value"])
        for field in fields:
            point.field(field["key"], field["value"])
        if timestamp:
            point.time(timezone.now(), WritePrecision.MS)
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        return write_api.write(self.bucket, settings.INFLUXDB_ORG, point)

    def query(self, measurement: str, timeframe: str, tags: list = []):
        """Query the InfluxDB - returns List of InfluxDB tables which contain records"""
        # Build the query
        query = f'from(bucket: "{self.bucket}")'
        query += f' |> range(start: -{timeframe})'
        query += f' |> filter(fn: (r) => (r._measurement == "{measurement}"))'
        if tags:
            for tag in tags:
                key = tag["key"]
                value = tag["value"]
                query += f' |> filter(fn: (r) => (r.{key} == "{value}"))'
        logger.debug(f"Running query: \"{query}\"")
        return self.client.query_api().query(query, org=settings.INFLUXDB_ORG)
