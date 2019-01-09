"""Tests for the marketmanager API."""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from api import models


def check_response_items(request, response, test_object):
    """Check the response for missing data from the request."""
    if response.status_code != status.HTTP_201_CREATED\
       and response.status_code != status.HTTP_200_OK:
        msg = "Couldn't create/patch object: {}. Response: ".format(request)
        msg += "{}".format(response.json())
        test_object.fail(msg)
    if isinstance(response.json(), list):
        response_data = response.json()["results"][0]
    else:
        response_data = response.json()
    for key, value in response_data.items():
        if response_data[key] != value:
            msg = "Mismatch in values on creation."
            msg += "Request: {}\nResponse:{}".format(request, response.json())
            test_object.fail(msg)


class StatusTestCase(TestCase):
    """Test suite for the api views."""

    def setUp(self):
        """Define the test client and other test variables."""
        self.client = APIClient()
        self.response = self.client.get(reverse('api:daemonstatus-list'))

    def testStatusGet(self):
        """Test the get response.

        Without the daemon running it should return 503.
        """
        self.assertEqual(self.response.status_code,
                         status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangesTest(TestCase):
    """Test the exchanges storage api."""

    def setUp(self):
        self.client = APIClient()
        self.request = {"name": "Bittrex", "interval": 300}
        exchange = models.Exchange(**self.request)
        exchange.save()
        self.get = self.client.get(reverse("api:exchange-list"))
        # Get the current ID from the get request
        self.get_id = self.get.json()["results"][0]["id"]

    def testGet(self):
        self.assertEqual(self.get.json()["results"][0]["name"],
                         self.request["name"])

    def testUnallowedMethods(self):
        """Test the unallowed methods - DELETE, POST, PUT, PATCH."""
        # POST
        response = self.client.post(reverse("api:exchange-list"), self.request)
        self.assertEqual(response.status_code, 405)
        # PUT
        response = self.client.post(reverse("api:exchange-detail",
                                            args=[self.get_id]), self.request)
        self.assertEqual(response.status_code, 405)
        # PATCH
        response = self.client.patch(reverse("api:exchange-detail",
                                             args=[self.get_id]), self.request)
        self.assertEqual(response.status_code, 405)
        # DELeTE
        response = self.client.patch(reverse("api:exchange-detail",
                                     args=[self.get_id]))
        self.assertEqual(response.status_code, 405)


class MarketsTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        exchange = {"name": "Bittrex", "interval": 300}
        exchange = models.Exchange(**exchange)
        exchange.save()
        self.exc_id = exchange.id
        self.request = {"name": "btc-eth", "exchange_id": exchange.id,
                        "volume": 55000, "last": 0.2, "ask": 0.21,
                        "bid": 0.20, "base": "btc", "quote": "eth"}
        market = models.Market(**self.request)
        market.save()
        self.get = self.client.get(reverse("api:market-list"))
        self.get_id = self.get.json()['results'][0]['id']

    def testGet(self):
        self.assertEqual(self.get.json()["results"][0]["name"],
                         self.request["name"])

    def testFilterGet(self):
        new_market = {"name": "eth-ltc", "exchange_id": self.exc_id,
                      "volume": "2500", "last": "0.4", "ask": "0.41",
                      "bid": "0.40", "base": "ltc", "quote": "eth"}
        market = models.Market(**new_market)
        market.save()
        resp = self.client.get("/markets/?volume__lte=5000")
        self.assertEqual(resp.json()["results"][0]["name"], new_market["name"])

    def testUnallowedMethods(self):
        """Test the unallowed methods - DELETE, POST, PUT, PATCH."""
        # POST
        response = self.client.post(reverse("api:market-list"), self.request)
        self.assertEqual(response.status_code, 405)
        # PUT
        response = self.client.post(reverse("api:market-detail",
                                            args=[self.get_id]), self.request)
        self.assertEqual(response.status_code, 405)
        # PATCH
        response = self.client.patch(reverse("api:market-detail",
                                             args=[self.get_id]), self.request)
        self.assertEqual(response.status_code, 405)
        # DELeTE
        response = self.client.patch(reverse("api:market-detail",
                                     args=[self.get_id]))
        self.assertEqual(response.status_code, 405)


class ExchangeStatusTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.get = self.client.get(reverse("api:exchangestatus-list"),
                                   format="json")

    def testGetList(self):
        """Test getting the list of adapters."""
        self.assertEqual(self.get.status_code, status.HTTP_200_OK)
