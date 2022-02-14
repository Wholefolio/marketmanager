import logging
from django.utils import timezone
from django.db import transaction, utils
from django.conf import settings

from api.models import Exchange, Market, CurrencyFiatPrices, FiatMarketModel, PairsMarketModel
from applib.tools import appRequest

model_map = {
    "fiat": FiatMarketModel,
    "pairs": PairsMarketModel
}


class InfluxUpdater:
    """Handle inserts of timeseries to InfluxDB. We have 2 cases:
    * Markets were the base is in fiat
    * Markets were the base is another cryptocurrency"""
    def __init__(self, exchange_id: int, data: dict, fiat_data: dict, task_id: str = None):
        self.exchange_id = exchange_id
        self.data = data
        self.fiat_data = fiat_data
        extra = {"task_id": task_id, "exchange": self.exchange_id}
        self.logger = logging.getLogger("marketmanager-celery")
        self.logger = logging.LoggerAdapter(self.logger, extra)

    def _create(self, model, data):
        """Write a new entry to InfluxDB"""
        obj = model_map[model](data=data)
        obj.save()

    def _callback(self, future):
        """Future handling"""
        exc = future.exception()
        if exc:
            self.logger.warning(f"Error occurred while trying to write to Influxdb. Exception: {exc}")

    def _write_fiat(self):
        """Write Market fiat data to Influx"""
        self.logger.info("Writing fiat data to InfluxDB")
        data = []
        for currency, price in self.fiat_data.items():
            self.logger.debug(f"Working on currency {currency}. Price: {price}")
            values = {"currency": currency, "price": price, "exchange_id": self.exchange_id}
            data.append(values)
        self._create("fiat", data)
        self.logger.info("Finished writing fiat data.")

    def _write_pairs(self):
        """Write Market pair data to Influx"""
        self.logger.info("Transforming market pairs data for InfluxDB")
        for symbol, values in self.data.items():
            self.logger.debug(f"Working on symbol {symbol}")
            values["symbol"] = symbol
        self._create("pairs", list(self.data.values()))
        self.logger.info("Finished writing market pairs.")

    def write(self):
        """Write the Market data of the exchange to InfluxDB"""
        self._write_pairs()
        self._write_fiat()


class ExchangeUpdater:
    """Insert/Update an exchanges market data"""
    def __init__(self, exchange_id: int, data: dict, fiat_data: dict = {}, task_id: str = None):
        self.exchange_id = exchange_id
        self.exchange = Exchange.objects.get(id=self.exchange_id)
        self.market_data = data
        self.fiat_data = fiat_data
        self.task_id = task_id
        extra = {"task_id": task_id, "exchange": self.exchange}
        self.logger = logging.getLogger("marketmanager-celery")
        self.logger = logging.LoggerAdapter(self.logger, extra)

    def create_map(self, data, key, value):
        """Create a map from the currency data - name: price."""
        output = {}
        for i in data:
            output[i[key]] = i[value]
        return output

    @transaction.atomic
    def create_markets(self):
        """Method for creation of market data."""
        self.logger.info("Starting creation of markets")
        for name, data in self.market_data.items():
            market = Market(name=name, **data)
            market.save()

    def calculate_pair_volume(self, name: str, values: dict,
                              fiat_symbol_rates: dict, currency_prices: dict):
        """Calculate a market pair volume in fiat"""
        base_price = quote_price = None
        if values['quote'] in settings.FIAT_SYMBOLS:
            quote_price = 1
        elif values['quote'] in fiat_symbol_rates:
            quote_price = fiat_symbol_rates[values['quote']]
        else:
            quote_price = currency_prices.get(values["quote"], 0)
        if values['base'] in settings.FIAT_SYMBOLS:
            base_price = 1
        elif quote_price and values['last'] > 0 and values['quote'] in settings.FIAT_SYMBOLS:
            base_price = values['last']
        elif values['base'] in fiat_symbol_rates:
            base_price = fiat_symbol_rates[values['base']]
        else:
            base_price = currency_prices.get(values['base'], 0)
        if not quote_price and not base_price:
            self.logger.debug(f"Missing fiat price for quote and base {name}")
            return None
        # The volume is baseVolume so calculate based on that to USD
        if base_price:
            return values['volume'] * base_price
        elif quote_price and values['last']:
            # We don't have the base_price - use the quote USD price and last
            return values['volume'] * values['last'] * quote_price

    def get_local_fiat_prices(self):
        """Get markets which have a quote in fiat."""
        quote_markets = Market.objects.filter(quote__in=settings.FIAT_SYMBOLS).values()
        return self.create_map(quote_markets, "base", "last")

    def get_fiat_symbol_rates(self):
        """Get all fiat symbols and rates."""
        url = "{}/internal/fiat/".format(settings.COIN_MANAGER_URL)
        response = appRequest("get", url)
        if "error" in response:
            msg = "Error during CoinManager request: %s" % response['error']
            self.logger.error(msg)
            return {}
        if response["count"] == 0:
            # There are no entries - make a effort to get some from our local
            # markets with base USD
            self.logger.warning("There are no currencies in CoinManager!")
            return {}
        return self.create_map(response['results'], "symbol", "rate")

    def get_base_prices(self):
        """Get the price list from CoinManager or from a market with a currency base USD"""
        local_data = self.get_local_fiat_prices()
        if local_data:
            return local_data
        url = "{}/internal/currencies/".format(settings.COIN_MANAGER_URL)
        response = appRequest("get", url)
        if "error" in response:
            msg = "Error during CoinManager request: %s" % response['error']
            self.logger.error(msg)
            return self.get_local_fiat_prices()
        if response["count"] == 0:
            # There are no entries - make a effort to get some from our local
            # markets with base USD
            self.logger.warning("There are no currencies in CoinManager!")
            return
        return self.create_map(response['results'], "symbol", "price")

    @transaction.atomic
    def update_existing_markets(self):
        """Update existing markets data."""
        current_data = Market.objects.select_for_update().filter(exchange=self.exchange)
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
        self.create_markets()

    def run(self):
        """Main run method - create/update the market data passed in."""
        current_time = timezone.now().timestamp()
        self.logger.info("Starting update!")
        # Fetch the old data by filtering on source id
        self.logger.info("Fetching old data...")
        current_data = Market.objects.filter(exchange=self.exchange).count()
        self.summarize_data()
        self.update_fiat_prices()
        if not current_data:
            self.create_markets()
        else:
            self.logger.info(f"We have to work on {current_data} entries. Starting update.")
            self.update_existing_markets()
        time_delta = timezone.now().timestamp() - current_time
        self.logger.info("Update finished in: {} seconds".format(time_delta))
        self.updateExchange()
        return "Updater finished successfully"

    def summarize_data(self):
        """Create a summary of the market data we have for the exchange."""
        # Get the current prices
        base_prices = self.get_base_prices()
        if base_prices and self.fiat_data:
            currency_prices = {**base_prices, **self.fiat_data}
        elif self.fiat_data:
            currency_prices = self.fiat_data
        else:
            currency_prices = base_prices
        fiat_symbol_rates = self.get_fiat_symbol_rates()
        self.logger.debug(f"Base prices: {currency_prices}")
        if not currency_prices:
            self.logger.error("Can't summarize exchange data due to no currency fiat prices")
            return
        exchange_volume = 0
        top_pair_volume = 0
        top_pair = ""
        for name, values in self.market_data.items():
            volume_usd = self.calculate_pair_volume(name, values, fiat_symbol_rates, currency_prices)
            if not volume_usd:
                self.logger.debug(f"Couldn't calculate volume for pair {name}. Values: {values}")
                continue
            if volume_usd >= top_pair_volume:
                top_pair = name
                top_pair_volume = volume_usd
            exchange_volume += volume_usd
        self.exchange.volume = exchange_volume
        self.exchange.top_pair = top_pair
        self.exchange.top_pair_volume = top_pair_volume
        self.exchange.save()
        msg = "Exchange volume and top pairs saved successfully!"
        msg += f"Volume: {exchange_volume}, Top Pair: {top_pair}, Top Pair Volume: {top_pair_volume}"
        self.logger.info(msg)

    def update_fiat_prices(self):
        existing_qs = CurrencyFiatPrices.objects.filter(currency__in=list(self.fiat_data.keys()),
                                                        exchange=self.exchange)
        existing_map = {x.currency: x for x in existing_qs}
        for currency, price in self.fiat_data.items():
            if currency in existing_map:
                existing_map[currency].price = price
                existing_map[currency].save()
            else:
                try:
                    obj = CurrencyFiatPrices(currency=currency, exchange=self.exchange, price=price)
                    obj.save()
                except utils.IntegrityError:
                    continue

    @transaction.atomic
    def updateExchange(self):
        """Patch the exchange last updated timestamp."""
        self.logger.info("Updating exchange summary")
        self.exchange.last_data_fetch = timezone.now()
        self.exchange.save()
        self.logger.info("Exchange summary update finished successfully!")
