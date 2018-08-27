"""Tests for the coiner API."""
import json
import os
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse


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
        self.response = self.client.get(reverse('status-list'))

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
        self.response = self.client.post(reverse("api:exchange-list"),
                                         self.request,
                                         format="json")
        check_response_items(self.request, self.response, self)
        self.get = self.client.get(reverse("api:exchange-list"))
        # Get the current ID from the get request
        self.get_id = self.get.json()["results"][0]["id"]

    def testGet(self):
        self.assertEqual(self.get.json()["results"][0]["name"],
                         self.request["name"])

    def testDelete(self):
        delete = self.client.delete(reverse("api:exchange-detail",
                                            args=[self.get_id]))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

    def testPatch(self):
        request = {"url": "http://testurl.com"}
        response = self.client.patch(reverse("api:exchange-detail",
                                             args=[self.get_id]),
                                     data=request)
        check_response_items(request, response, self)


class ExchangeStatusTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        request = {'adapter': adapter_id}
        self.response = self.client.post(reverse("adapterstatus-list"),
                                         data=request, format="json")
        if self.response.status_code != status.HTTP_201_CREATED:
            msg = "Didn't create adapterstatus.{}".format(self.response.json())
            self.fail(msg)
        self.get = self.client.get(reverse("adapterstatus-list"))
        self.get_id = self.get.json()[0]["id"]

    def testGetList(self):
        """Test getting the list of adapters."""
        self.assertEqual(self.get.status_code, status.HTTP_200_OK)
