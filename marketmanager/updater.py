import logging
import requests
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

    def createCurrencyMap(self, data):
        """Create a map from the currency data - name: price."""
        output = {}
        for i in data:
            output[i['symbol']] = i['price']
        return output

    def createMarkets(self):
        """Method for creation of market data."""
        msg = "Starting creation of markets"
        self.logger.info(msg)
        for name, data in self.market_data.items():
            market = Market(name=name, **data)
            market.save()

    def getLocalFiatPrices(self):
        """Get markets which have a base of USD."""
        base_markets = Market.objects.filter(base="USD")
        output = {}
        # Create a map for easier filtering
        for market in base_markets:
            output[market.quote] = market.last
        return output

    def getBasePrices(self):
        """Get the price list from CoinManager or from a market with a currency
         base USD"""
        url = "{}currencies/".format(settings.COIN_MANAGER_URL)
        response = requests.get(url)
        elapsed = response.elapsed.microseconds/1000
        msg = "Currencies fetch elapsed: {} ms".format(elapsed)
        self.logger.debug(msg)
        if response.status_code != 200:
            msg = "Couldn't fetch current currency data from CoinManager."
            self.logger.error(msg)
            return self.getLocalFiatPrices()
        if response.json()["count"] == 0:
            # There are no entries - make a effort to get some from our local
            # markets with base USD
            msg = "There are no currencies in CoinManager!"
            self.logger.error(msg)
            return self.getLocalFiatPrices()
        data_map = self.createCurrencyMap(response.json()['results'])
        return data_map

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
        current_data = Market.objects.select_for_update().filter(
                                                        exchange=exchange)
        self.summarizeData(exchange)
        if not current_data:
            self.createMarkets()
        else:
            msg = "We have to work on {} entries.".format(len(current_data))
            self.logger.info(msg)
            self.logger.info("Starting market data update.")
            self.updateExistingMarkets(current_data)
        time_delta = timezone.now().timestamp() - current_time
        self.logger.info("Update finished in: {} seconds".format(time_delta))
        self.updateExchange(exchange)
        return "Data update successful for exchange: {}".format(exchange)

    def summarizeData(self, exchange):
        """Create a summary of the market data we have for the exchange."""
        # Get the current prices
        currency_prices = self.getBasePrices()
        exchange_volume = 0
        top_pair_volume = 0
        top_pair = ""
        for name, values in self.market_data.items():
            currency_price = currency_prices.get(values["base"], 0)
            volume_usd = values['volume'] * currency_price
            if volume_usd >= top_pair_volume:
                top_pair = name
                top_pair_volume = volume_usd
            exchange_volume += volume_usd
        exchange.volume = exchange_volume
        exchange.top_pair = top_pair
        exchange.top_pair_volume = top_pair_volume
        exchange.save()
        self.logger.info("Exchange volume and top pairs saved successfully!")

    def updateExchange(self, exchange):
        """Patch the exchange last updated timestamp."""
        self.logger.info("Updating Exchange {}.".format(exchange.name))
        timestamp = "{}".format(timezone.now())
        exchange.last_updated = timestamp
        exchange.save()
        self.logger.info("Exchange update finished successfully!")
