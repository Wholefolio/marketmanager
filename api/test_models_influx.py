import unittest
from unittest.mock import patch
from influxdb_client.client.flux_table import FluxRecord, FluxTable

from api.models_influx import InfluxModel

MOCK_RECORD = {
    "symbol": "BTC",
    "_field": "price",
    "_value": 25000,
    "price": 25000,
    "_time": True
}


class MockInfluxClient:
    def query(measurement, time_start, tags, **kwargs):
        table = FluxTable()
        record = FluxRecord(table=0)
        record.values = MOCK_RECORD
        table.records = [record]
        return [table]

    def write(measurement, **kwargs):
        return True


class TestInfluxModel(unittest.TestCase):
    """Test the InfluxModel"""

    def setUp(self):
        self.model = InfluxModel()
        self.model.measurement = "test-model"

    def test_validate_empty(self):
        """Test validating with an empty model - no tags/fields"""
        with self.assertRaises(ValueError):
            self.model._validate()

    def test_validate_with_data(self):
        """Test validating with data"""
        self.model.field = "price"
        self.model.data = {"price": 123}
        self.model._validate()
        self.assertTrue(self.model.validated_data)

    def test_clean_result(self):
        """Test cleaning a result from unnecessary fields"""
        record = FluxRecord(table=0)
        record.values = {"_value": 123}
        influx_fields = ["_measurement", "_start", "_stop", "result", "table", "_time"]
        for i in influx_fields:
            record.values[i] = True

        result = self.model._clean_result(record)
        for i in influx_fields:
            self.assertFalse(i in result)

    @patch("api.models_influx.InfluxClient")
    def test_write(self, mock):
        mock.return_value = MockInfluxClient
        self.model.data = MOCK_RECORD
        self.model.field = MOCK_RECORD["_field"]
        self.model.save()
        self.assertTrue(mock.called)
