from pybit import HTTP
from config.main_config import MainConfig
from pybit.exceptions import InvalidRequestError


class BybitBase():

    def __init__(self):
        """
        Initializes the BybitBase class with the API key, secret, collateral and session objects.
        """
        self._api_key = MainConfig.getinstance().get_user_data()['api_key']
        self._api_secret = MainConfig.getinstance().get_user_data()['api_secret']
        self.collateral = MainConfig.getinstance().get_user_data()['collateral']
        self.session = HTTP("https://api.bybit.com",
                api_key=self._api_key, api_secret=self._api_secret)

    def place_order(self, coin_ticker, _side, _qty):
        """
        Places a market order.
        :param coin_ticker: Ticker symbol string, ex: "BTC"
        :param _side: Order side: "Buy" or "Sell"
        :param _qty: Trade quantity, ex: 0.1
        :return: Exchange response object
        """
        return self.session.place_active_order(
            symbol= coin_ticker + self.collateral,
            side=_side,
            order_type="Market",
            qty=_qty,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False
        )

    def reduce_position(self, coin_ticker, counter_side, _qty):
        """
        Reduces the position for the specified coin and counter side.
        :param coin_ticker: Ticker symbol string, ex: "BTC"
        :param counter_side: Counter side of the position to be reduced: "Buy" or "Sell"
        :param _qty: Quantity to be reduced, ex: 0.1
        :return: Exchange response object
        """
        return self.session.place_active_order(
            symbol= coin_ticker + self.collateral,
            side=counter_side,
            order_type="Market",
            qty=_qty,
            time_in_force="GoodTillCancel",
            reduce_only=True,
            close_on_trigger=True
        )

    def place_limit_order_po(self, coin_ticker, _side, _qty, _price):
        """
        Places a limit order with post-only flag.
        :param coin_ticker: Ticker symbol string, ex: "BTC"
        :param _side: Order side: "Buy" or "Sell"
        :param _qty: Trade quantity, ex: 0.1
        :param _price: Limit price, ex: 50000.0
        :return: Exchange response object
        """
        return self.session.place_active_order(
            symbol= coin_ticker + self.collateral,
            side=_side,
            order_type="Limit",
            price=_price,
            qty=_qty,
            time_in_force="PostOnly",
            reduce_only=False,
            close_on_trigger=False
        )
    
    def reduce_position_limit(self, coin_ticker: str, counter_side: str, qty: float, price: float) -> dict:
        """
        Reduce an active position by placing a limit order.
        
        Args:
            coin_ticker (str): The ticker symbol for the coin being traded.
            counter_side (str): The counter side of the trade (buy/sell).
            qty (float): The quantity of the coin being traded.
            price (float): The price at which the trade will be executed.
            
        Returns:
            dict: A dictionary containing information about the placed order.
        """
        return self.session.place_active_order(
            symbol=coin_ticker + self.collateral,
            side=counter_side,
            order_type="Limit",
            price=price,
            qty=qty,
            time_in_force="PostOnly",
            reduce_only=True,
            close_on_trigger=True
        )
    
    def get_wallet_balance(self) -> float:
        """
        Get the available balance in the trading account.
        
        Returns:
            float: The available balance in the trading account.
        """
        json_result = self.session.get_wallet_balance(coin=self.collateral)
        if json_result['ret_code'] != 0:
            print('Error while returning wallet balance!')
            return -1
        available_balance = json_result['result'][self.collateral]['wallet_balance']
        print('Available balance: ', available_balance)
        return available_balance       

    def get_position_by_symbol(self, coin_ticker: str) -> dict:
        """
        Get information about an active position.
        
        Args:
            coin_ticker (str): The ticker symbol for the coin being traded.
            
        Returns:
            dict: A dictionary containing information about the active position.
        """
        return self.session.my_position(
            symbol=coin_ticker + self.collateral
        )

    def set_leverage(self, coin_ticker: str, long_lev: int, short_lev: int) -> None:
        """
        Sets the leverage for a given coin pair.

        Args:
            coin_ticker (str): The ticker symbol for the coin pair to set leverage for.
            long_lev (int): The desired leverage for long positions.
            short_lev (int): The desired leverage for short positions.

        Returns:
            None
        """
        try:
            # Try to set the leverage for the given coin pair
            self.session.set_leverage(
                symbol=coin_ticker + self.collateral,
                buy_leverage=long_lev,
                sell_leverage=short_lev
            )
            print(f'Leverage successfully set - Buy: {long_lev}x | Sell: {short_lev}x')
        except InvalidRequestError:
            # If setting the leverage fails, print an error message
            print('Failed to set leverage')

    def get_order_book(self, coin_ticker: str) -> dict:
        """
        Retrieves the order book for a given coin pair.

        Args:
            coin_ticker (str): The ticker symbol for the coin pair to retrieve the order book for.

        Returns:
            A dictionary containing the order book for the specified coin pair.
        """
        return self.session.orderbook(symbol=coin_ticker + self.collateral)

    def get_latest_buy_and_sell_orders(self, coin_ticker: str) -> tuple:
        """
        Retrieves the latest buy and sell orders for a given coin pair.

        Args:
            coin_ticker (str): The ticker symbol for the coin pair to retrieve the latest buy and sell orders for.

        Returns:
            A tuple containing the latest buy order and the latest sell order for the specified coin pair.
        """
        latest_buy_order = None
        latest_sell_order = None
        orders = self.get_order_book(coin_ticker)['result']
        for order in orders:
            if latest_buy_order is None and order['side'] == 'Buy':
                latest_buy_order = order
            if latest_sell_order is None and order['side'] == 'Sell':
                latest_sell_order = order
            if latest_buy_order is not None and latest_sell_order is not None:
                return latest_buy_order, latest_sell_order

    def get_order_by_link_id(self, coin_ticker: str, order_link_id: str) -> dict:
        """Query an active order by order link ID.

        Args:
            coin_ticker (str): The ticker symbol of the coin.
            order_link_id (str): The unique identifier of the order.

        Returns:
            dict: The order details.
        """
        return self.session.query_active_order(
            symbol=coin_ticker + self.collateral,
            order_link_id=order_link_id
        )


    def get_order_by_id(self, coin_ticker: str, order_id: str) -> dict:
        """Query an active order by order ID.

        Args:
            coin_ticker (str): The ticker symbol of the coin.
            order_id (str): The unique identifier of the order.

        Returns:
            dict: The order details.
        """
        return self.session.query_active_order(
            symbol=coin_ticker + self.collateral,
            order_id=order_id
        )


    def cancel_limit_order(self, coin_ticker: str, order_id: str) -> dict:
        """Cancel an active limit order.

        Args:
            coin_ticker (str): The ticker symbol of the coin.
            order_id (str): The unique identifier of the order.

        Returns:
            dict: The result of the cancellation request.
        """
        return self.session.cancel_active_order(
            symbol=coin_ticker + self.collateral,
            order_id=order_id
        )


    def get_symbol_info(self, coin_ticker: str) -> dict:
        """Get the details of a symbol.

        Args:
            coin_ticker (str): The ticker symbol of the coin.

        Returns:
            dict: The details of the symbol.
        """
        for result in self.session.query_symbol()['result']:
            if result['name'] == coin_ticker + self.collateral:
                return result
        print('[!] Error while returning data from symbol', coin_ticker + self.collateral)
        return {}


    def get_qty_step(self, coin_ticker: str) -> float:
        """Get the minimum quantity step for a coin.

        Args:
            coin_ticker (str): The ticker symbol of the coin.

        Returns:
            float: The minimum quantity step for the coin.
        """
        symbol_info = self.get_symbol_info(coin_ticker)
        return symbol_info.get('lot_size_filter', {}).get('qty_step', 0.0)
