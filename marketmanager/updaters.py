import logging
from concurrent.futures import ThreadPoolExecutor
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from api.models import Exchange, Market, FiatMarketModel, PairsMarketModel
from applib.tools import appRequest

model_map = {
    "fiat": FiatMarketModel,
    "pairs": PairsMarketModel
}


class InfluxUpdater:
    """Handle inserts of timeseries to InfluxDB. We have 2 cases:
    * Markets were the base is in fiat
    * Markets were the base is another cryptocurrency"""
    def __init__(self, exchange_id: int, data: dict, task_id: str = None):
        self.exchange_id = exchange_id
        self.data = data
        extra = {"task_id": task_id, "exchange": self.exchange_id}
        self.logger = logging.getLogger("marketmanager-celery")
        self.logger = logging.LoggerAdapter(self.logger, extra)

    def _create(self, model, data):
        obj = model_map[model](data=data)
        obj.save()

    def _callback(self, future):
        exc = future.exception()
        if exc:
            self.logger.warning(f"Error occurred while trying to write to Influxdb. Exception: {exc}")

    def _writeFiat(self):
        """Write Market fiat data to Influx"""
        self.logger.info("Writing fiat data to InfluxDB")
        with ThreadPoolExecutor(max_workers=5) as executor:
            for symbol, values in self.data.items():
                if values["quote"] not in settings.FIAT_SYMBOLS:
                    # We only want values in our fiat currencies
                    continue
                values["price"] = values["last"]
                values["currency"] = values["base"]
                future = executor.submit(self._create, "fiat", values)
                future.add_done_callback(self._callback)
        self.logger.info("Finished writing fiat data.")

    def _writePairs(self):
        """Write Market pair data to Influx"""
        self.logger.info("Transforming market pairs data for InfluxDB")
        with ThreadPoolExecutor(max_workers=5) as executor:
            for symbol, values in self.data.items():
                self.logger.debug(f"Working on symbol {symbol}")
                future = executor.submit(self._create, "pairs", values)
                future.add_done_callback(self._callback)
        self.logger.info("Finished writing market pairs.")

    def write(self):
        """Write the Market data of the exchange to InfluxDB"""
        exchange = Exchange.objects.get(id=self.exchange_id)
        if exchange.fiat_markets:
            self._writeFiat()
        self._writePairs()


class ExchangeUpdater:
    """Insert/Update an exchanges market data"""
    def __init__(self, exchange_id, data, task_id=None):
        self.exchange_id = exchange_id
        self.exchange = Exchange.objects.get(id=self.exchange_id)
        self.market_data = data
        self.task_id = task_id
        extra = {"task_id": task_id, "exchange": self.exchange}
        self.logger = logging.getLogger("marketmanager-celery")
        self.logger = logging.LoggerAdapter(self.logger, extra)

    def createCurrencyMap(self, data):
        """Create a map from the currency data - name: price."""
        output = {}
        for i in data:
            output[i['symbol']] = i['price']
        return output

    def createMarkets(self):
        """Method for creation of market data."""
        self.logger.info("Starting creation of markets")
        for name, data in self.market_data.items():
            market = Market(name=name, **data)
            market.save()

    def getLocalFiatPrices(self):
        """Get markets which have a quote in fiat."""
        quote_markets = Market.objects.filter(quote__in=settings.FIAT_SYMBOLS)
        output = {}
        # Create a map for easier filtering
        for market in quote_markets:
            output[market.base] = market.last
        return output

    def getBasePrices(self):
        """Get the price list from CoinManager or from a market with a currency base USD"""
        local_data = self.getLocalFiatPrices()
        if local_data:
            return local_data
        url = "{}/internal/currencies/".format(settings.COIN_MANAGER_URL)
        response = appRequest("get", url)
        if "error" in response:
            msg = "Error during CoinManager request: %s" % response['error']
            self.logger.error(msg)
            return self.getLocalFiatPrices()
        if response["count"] == 0:
            # There are no entries - make a effort to get some from our local
            # markets with base USD
            self.logger.warning("There are no currencies in CoinManager!")
            return
        data_map = self.createCurrencyMap(response['results'])
        return data_map

    def updateExistingMarkets(self, current_data):
        """Update existing markets data."""
        for market in current_data:
            # Check if the name is in the market data - if yes update it
            if market.name in self.market_data:
                msg = "Found match in market_data. {}".format(self.market_data[market.name])
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
        current_time = timezone.now().timestamp()
        self.logger.info("Starting update!")
        # Fetch the old data by filtering on source id
        self.logger.info("Fetching old data...")
        current_data = Market.objects.select_for_update().filter(exchange=self.exchange)
        self.summarizeData()
        if not current_data:
            self.createMarkets()
        else:
            msg = "We have to work on {} entries.".format(len(current_data))
            self.logger.info(msg)
            self.logger.info("Starting market data update.")
            self.updateExistingMarkets(current_data)
        time_delta = timezone.now().timestamp() - current_time
        self.logger.info("Update finished in: {} seconds".format(time_delta))
        self.updateExchange()
        return "Updater finished successfully"

    def summarizeData(self):
        """Create a summary of the market data we have for the exchange."""
        # Get the current prices
        currency_prices = self.getBasePrices()
        self.logger.info("Base prices: ", currency_prices)
        if not currency_prices:
            msg = "Can't summarize exchange data due to no currency prices"
            self.logger.error(msg)
            return
        exchange_volume = 0
        top_pair_volume = 0
        top_pair = ""
        for name, values in self.market_data.items():
            currency_price = currency_prices.get(values["quote"], 0)
            if not currency_price:
                self.logger.debug("Missing fiat price for {}".format(values["quote"]))
                continue
            volume_usd = values['volume'] * currency_price * values['last']
            if volume_usd >= top_pair_volume:
                top_pair = name
                top_pair_volume = volume_usd
            exchange_volume += volume_usd
        self.exchange.volume = exchange_volume
        self.exchange.top_pair = top_pair
        self.exchange.top_pair_volume = top_pair_volume
        self.exchange.save()
        msg = "Exchange volume and top pairs saved successfully!"
        msg += "Volume: {}, Top Pair: {}, Top Pair Volume: {}".format(exchange_volume,
                                                                      top_pair, top_pair_volume)
        self.logger.info(msg)

    def updateExchange(self):
        """Patch the exchange last updated timestamp."""
        self.logger.info("Updating exchange summary")
        self.exchange.last_data_fetch = timezone.now()
        self.exchange.save()
        self.logger.info("Exchange summary update finished successfully!")
