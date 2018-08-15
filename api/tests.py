"""Tests for the coiner API."""
import json
import os
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse


def createExchange(instance):
    adapter = "./tests/TestExchange.py"
    with open(adapter, "r") as f:
        adapter_source = f.readlines()
    request = {"name": "TestExchange",
               "enabled": 1,
               "storage_source_id": 1,
               "source_code": "".join(adapter_source),
               "interval": 120,
               "adapter_params": "testparam",
               "type": "CMN",
               }
    response = instance.client.post(reverse("adapter-list"), request,
                                    format="json")
    if response.status_code != status.HTTP_201_CREATED:
        instance.fail("Couldn't create adapter")
    return response.json()


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


class ExchangeTest(TestCase):
    """Test creating/getting/deletion of adapters."""

    def setUp(self):
        """Set up an API client."""
        self.client = APIClient()
        self.response = createExchange(self)
        self.get = self.client.get(reverse("adapter-list"))

        self.get_id = self.get.json()[0]["id"]

    def tearDown(self):
        try:
            to_remove = self.response["name"] + ".py"
            os.remove(to_remove)
        except FileNotFoundError:
            pass

    def testGetList(self):
        """Test getting the list of adapters."""
        self.assertEqual(self.get.status_code, status.HTTP_200_OK)

    def testUpdate(self):
        """Update an existing service."""
        request = {"source_code": "print(\"test\")"}
        response = self.client.patch(reverse("adapter-detail",
                                     args=[self.get_id]),
                                     json.dumps(request),
                                     content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def testDelete(self):
        """Test deleting an existing service."""
        response = self.client.delete(reverse("adapter-detail",
                                              args=[self.get_id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ExchangeStatusTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        response = createExchange(self)
        adapter_id = response["id"]
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
