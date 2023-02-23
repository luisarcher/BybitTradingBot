"""
The alert manager recives data from trading view
checks if there is an already long or open position in place on bybit
If long or short position is already in place, the alert is ignored
otherwise, it closes the current position to open a counter position
e.g. a long position is open and a short signal is received
the long position is closed and a short position is opened
"""

from math import fabs
import threading
from bybit_ticker import BybitTicker
from utils import handle_exchange_response


class AlertManager():

    # When setting to true, exchange return messages will be printed on the console
    DEBUG = False

    def __init__(self):
        """
        Initializes an AlertManager object with a dictionary of BybitTicker objects.

        Each BybitTicker object corresponds to a different ticker symbol and provides
        methods for fetching position information and executing limit orders.
        """
        self.tickers = dict()
        self._init_ticker_clients()

    def __create_ticker(self, ticker):
        """
        Creates a BybitTicker object for the given ticker symbol and adds it to the `tickers` dictionary.

        :param ticker: A string representing the ticker symbol.
        """
        self.tickers[ticker] = BybitTicker(ticker)

    def _init_ticker_clients(self):
        """
        Initializes BybitTicker objects for each ticker symbol in a configuration file.

        TODO: Implement functionality to read ticker symbols from a configuration file.
        """
        # TODO: Create tickers from config file
        self.__create_ticker('ETH')
        self.__create_ticker('CRO')

    def handle_alert(self, data):
        """
        Processes a trading signal received from TradingView.

        If the signal corresponds to a long or short position that is already open, the signal is ignored.
        Otherwise, the current position is closed and a counter position is opened.

        :param data: A dictionary containing information about the trading signal.
        :return: True if a new position is opened, False otherwise.
        """
        # Checks if the ticker symbol in the signal corresponds to a BybitTicker object.
        if data['ticker'] in self.tickers:
            ticker = self.tickers[data['ticker']]
        else:
            print('No such ticker ', data['ticker'])
            return False

        # Fetches the current long and short positions for the ticker.
        curr_long_position, curr_short_position = ticker.fetch_ticker_positions()
        if curr_long_position is None or curr_short_position is None:
            print('Error fetching current positions')
            return False

        # If the signal is a "close" signal, closes the corresponding position.
        if 'close' in data['comment']:
            if data['side'].lower() == 'sell':
                self.close_long_trade(ticker, curr_long_position)
            if data['side'].lower() == 'buy':
                self.close_short_trade(ticker, curr_short_position)
            return False

        # If the signal is a "buy" signal, opens a long position.
        if data['side'].lower() == 'buy':
            return self._handle_long_position(ticker, curr_long_position, curr_short_position)

        # If the signal is a "sell" signal, opens a short position.
        if data['side'].lower() == 'sell':
            return self._handle_short_position(ticker, curr_long_position, curr_short_position)

    def _handle_long_position(self, ticker, json_long, json_short):
        """
        Handles a Long position request.

        :param ticker: ticker object
        :param json_long: Long position info for ticker
        :param json_short: Short position info for ticker
        :return: True if a new Long position is opened, False otherwise
        """
        # Check if there is already an open long position
        if float(json_long['size']) > 0:
            print('Already in a LONG position')
            return False

        # Check if there is a short position for the same ticker and close it
        self.close_short_trade(ticker, json_short)

        # Execute the buy limit order to open a new long position
        ticker.thread_ident = threading.get_ident()
        ticker.execute_limit_order_procedure('Buy')

        # Print a message to indicate that the trade is finished and await new signals
        print('Trade finished. Awaiting new signals...')

        return True

    def _handle_short_position(self, ticker, json_long, json_short):
        """
        Handles a Short position request.

        :param ticker: ticker object
        :param json_long: Long position info for ticker
        :param json_short: Short position info for ticker
        :return: True if a new Short position is opened, False otherwise
        """
        # Check if there is already an open short position
        if float(json_short['size']) > 0:
            print('Already in a SHORT position')
            return False

        # Check if there is a long position for the same ticker and close it
        self.close_long_trade(ticker, json_long)

        # Execute the sell limit order to open a new short position
        ticker.thread_ident = threading.get_ident()
        ticker.execute_limit_order_procedure('Sell')

        # Print a message to indicate that the trade is finished and await new signals
        print('Trade finished. Awaiting new signals...')

        return True

    def close_long_trade(self, ticker, json_long):
        """
        Closes a long position if it exists.

        :param ticker: ticker object
        :param json_long: Long position info for ticker
        :return: True if a long position was closed, False otherwise
        """
        if float(json_long['size']) > 0:
            print('Long position found! Closing...')
            th = threading.Thread(target=ticker.cancel_all_trades_limit, args=(json_long,))
            th.start()
            return True
        return False

    def close_short_trade(self, ticker, json_short):
        """
        Closes a short position if it exists.

        :param ticker: ticker object
        :param json_short: Short position info for ticker
        :return: True if a short position was closed, False otherwise
        """
        if float(json_short['size']) > 0:
            print('Short position found! Closing...')
            th = threading.Thread(target=ticker.cancel_all_trades_limit, args=(json_short,))
            th.start()
            return True
        return False
