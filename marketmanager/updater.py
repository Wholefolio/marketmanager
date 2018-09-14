import logging
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from api.models import Exchange, Market


class ExchangeUpdater:
    """Update an exchanges market data"""
    def __init__(self, exchange_id, data):
        self.exchange_id = exchange_id
        self.market_data = data
        self.logger = logging.getLogger(__name__)

    def createMarkets(self):
        msg = "Starting creation of markets"
        self.logger.info(msg)
        for name, data in self.market_data.items():
            market = Market(name=name, **data)
            market.save()

    def updateExistingMarkets(self, current_data):
        """Update existing exchange data."""
        for market in current_data:
            # Check if the name is in the market data - if yes update it
            if market.name in self.market_data:
                msg = "Found match in market_data. {}".format(
                                                self.market_data[market.name])
                self.logger.debug(msg)
                for key, value in self.market_data[market.name].items():
                    if key != "exchange_id":
                        # Skip the exchange key as it must remain the same
                        setattr(market, key, value)
                market.save()
                # Delete the item form the list
                del self.market_data[market.name]
        # We have gone through the existing ones now we have to create the new
        self.createMarkets()

    @transaction.atomic
    def run(self):
        """Main run method - create/update the market data passed in."""
        exchange = Exchange.objects.get(id=self.exchange_id)
        current_time = timezone.now().timestamp()
        self.logger.info("Starting update for {}!".format(exchange.name))
        # Fetch the old data by filtering on source id
        self.logger.info("Fetching old data...")
        current_data = Market.objects.select_for_update().all()
        if not current_data:
            self.createMarkets()
        else:
            msg = "We have to work on {} entries.".format(len(current_data))
            self.logger.info(msg)
            self.logger.info("Starting market data update.")
            self.updateExistingMarkets(current_data)
        time_delta = timezone.now().timestamp() - current_time
        self.logger.info("Update finished in: {} seconds".format(time_delta))
        self.summarizeData()
        self.updateExchange(exchange)
        return "Data update successful for exchange: {}".format(exchange)

    def summarizeData(self):
        """Create a summary of the market data we have for the exchange."""


    def updateExchange(self, exchange):
        """Patch the exchange last updated timestamp."""
        self.logger.info("Updating Exchange {}.".format(exchange.name))
        timestamp = "{}".format(timezone.now())
        exchange.last_updated = timestamp
        exchange.save()
        self.logger.info("Exchange update finished successfully!")
