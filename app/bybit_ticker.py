import math
import threading
from time import sleep

from bybit_base import BybitBase
from config.main_config import MainConfig
from utils import handle_exchange_response, round_down


class BybitTicker(BybitBase):

    # Return codes
    ABORT_LIMIT_ORDER = -1
    LIMIT_ORDER_FILLED = 0
    RETRY_LIMIT_ORDER = 1

    def __init__(self, coin_ticker):
        super(BybitTicker, self).__init__()

        self.coin_ticker = coin_ticker

        # Get the message handler from the main config singleton
        self.hmsg = MainConfig.getinstance().message_handler

        # Unique thread identifier
        self.thread_ident = 0

        # Risk management type
        self.risk_management = 'TSL'  # SLTP

        # Default values for take profit and stop loss multipliers
        self.long_tp_mul_val = 1.004
        self.long_sl_mul_val = (1 - 0.00125)
        self.short_tp_mul_val = (1 - 0.004)
        self.short_sl_mul_val = 1.00125

        # Default values for take profit and stop loss percentages for TSL
        self.long_tsl_perc = 10
        self.short_tsl_perc = 10

        # Default slippage percentage when trading at market
        self.trade_market_on_slippage_perc = 0.0375

        # Statistics counters
        # TODO: Create a class to manage statistics
        #  this class should export trade data to a CSV file when trades are finished
        self.sl_count = 0
        self.tp_count = 0
        self.reversal_count = 0
        self.market_count = 0
        self.limit_count = 0

        # Update the last known price of the coin
        self.last_known_price = self.get_ticker_price()
        self.hmsg.msg('Price for ' + self.coin_ticker + ': ' + self.last_known_price)

        # Adjust leverage on the exchange according to the config file
        self.sync_leverage()

        # Calculate entry size for long and short trades
        self.qty_step = self.get_qty_step(self.coin_ticker)
        # self.long_entry_qty = self.calculate_entry_size('buy')
        # self.short_entry_qty = self.calculate_entry_size('sell')
        

    def get_ticker_price(self):
        """
        Get the last ask price of the current ticker.
        """
        symbol = self.coin_ticker + self.collateral
        json_result = self.session.latest_information_for_symbol(symbol=symbol)
        ask_price = json_result['result'][0]['ask_price']
        return ask_price


    def get_ticker_info(self):
        """
        Get the latest information for the current ticker.
        """
        symbol = self.coin_ticker + self.collateral
        return self.session.latest_information_for_symbol(symbol=symbol)


    def close_position_qty(self, side, qty):
        """
        Reduce position on the current ticker.
        """
        return self.reduce_position(
            symbol=self.coin_ticker,
            side=side,
            qty=qty+1
        )


    def calculate_entry_size(self, side):
        """
        Calculate the entry size based on the last known price, wallet balance,
        leverage, and percentage of portofolio.
        """
        # get leverage and percentage from the config file
        ticker_config = MainConfig.getinstance().get_ticker_data(self.coin_ticker)
        if side.lower() == 'buy':
            leverage = ticker_config['long_leverage']
        elif side.lower() == 'sell':
            leverage = ticker_config['short_leverage']
        perc = ticker_config['wallet_perc']

        # Using last known price for optimization purposes
        last_known_price = self.get_ticker_price()
        available_balance = self.get_wallet_balance() * 0.6
        non_rounded_entry_size = (
            float(available_balance) / float(last_known_price)
            * float(leverage) * float(perc)
            * (1 - (0.00075 * 2))
        )
        qty_step = self.get_qty_step(self.coin_ticker)
        rounded_entry_size = round(round_down(non_rounded_entry_size, qty_step), 3)
        print('Estimated entry size:', rounded_entry_size)
        return rounded_entry_size

    def get_position(self):
        # Retrieves the current open position for the coin_ticker
        # Returns the result from the API call or raises an exception if the API call fails
        ret = self.get_position_by_symbol(self.coin_ticker)
        handle_exchange_response(ret, 'Failed to retrieve current open positions')
        return ret

    def sync_leverage(self):
        # Sets the leverage for the coin_ticker based on the values in MainConfig
        # Returns the result from the API call
        return self.set_leverage(
            self.coin_ticker,
            MainConfig.getinstance().get_ticker_data(self.coin_ticker)['long_leverage'],
            MainConfig.getinstance().get_ticker_data(self.coin_ticker)['short_leverage']
        )

    def fetch_ticker_positions(self):
        """
        Retrieves all positions for coin_ticker from the exchange
        Returns the long and short positions if they exist, otherwise returns False
        """
        json_positions = self.get_position()
        if json_positions['ret_code'] == 0:
            # All ok, start digging the data
            long_position = None
            short_position = None
            for result in json_positions['result']:
                if result['side'] == 'Buy':
                    # Long position found, store it
                    long_position = result
                if result['side'] == 'Sell':
                    # Short position found, store it
                    short_position = result
            return long_position, short_position
        return False

    def is_order_created(self, response):
        # Checks if the response from an API call indicates that a new order was created
        return response['ret_code'] == 0 \
            and (response['result']['order_status'] == 'Created' \
            or response['result']['order_status'] == 'New')

    def __has_no_open_positions(self, response):
        # Helper method that checks if the response from an API call indicates that there are no open positions
        return response['ret_code'] == 0 \
            and response['result'][0]['size'] == '0' \
            and response['result'][1]['size'] == '0'

    def has_no_open_positions(self):
        # Checks if there are currently no open positions for the coin_ticker
        response = self.get_position()
        return self.__has_no_open_positions(response)

    def check_for_no_open_trades(self):
        """
        Raises an exception if there are any open positions or orders
        """
        response = self.get_position()
        handle_exchange_response(response, 'Failed to retrieve open positions')
        if not self.has_no_open_positions(response):
            self.logger.error('Open position found after TP order')
            # raise Exception('Open position found after TP order')

    def has_no_open_positions(self, response):
        # TODO: implement
        pass

    def has_price_decreased(self, curr_price, org_price, slippage_perc):
        return curr_price - org_price < -slippage_perc / 100 * org_price

    def has_price_increased(self, curr_price, org_price, slippage_perc):
        return curr_price - org_price > slippage_perc / 100 * org_price

    def execute_limit_order_procedure(self, side):
        """
        Places a limit order, tightens it if necessary, and waits for it to fill
        """
        side = self.place_limit_order_with_retry(side)
        if not side:
            self.logger.debug('limit order not placed')
            return
        """
        # Wait for limit order to fill
        if not self.wait_for_limit_order():
            self.logger.debug('limit order not filled')
            return

        # Place TP order
        if not self.place_tp_order():
            self.logger.debug('TP order not placed')
            return
        """
        # Monitor current ticker price for stop loss placement
        #self.check_for_stop_limit_tsl(side)

    def place_limit_order_with_retry(self, side: str) -> str:
        """
        Attempts to place limit order according to the signal received from tradingView.
        Will tighten the limit order every time the market moves away from it
        At x attempts or high price slippage, a market order will be placed
        :param side: string representing the side of the order ("Buy" or "Sell")
        :return: a string indicating the side of the order ("Buy" or "Sell") if the order was filled, or an empty string otherwise
        """

        # Initialize variables
        count_retries = 0

        # Attempt to place and monitor a new limit order while not receiving a new signal
        while self.thread_ident == threading.get_ident():

            # Create limit order
            main_limit_order_data = self.__create_limit_order(side, self.calculate_entry_size(side))
            if main_limit_order_data is None:
                return ''
            
            # Check if the order was filled
            if main_limit_order_data['result']['order_status'] == 'Filled':
                self.limit_count += 1
                return side

            # Monitor and update previously created limit order
            ret_code = self.tighten_limit_order(main_limit_order_data, count_retries)
            if ret_code == BybitTicker.LIMIT_ORDER_FILLED:
                return side
            elif ret_code == BybitTicker.ABORT_LIMIT_ORDER:
                return ''
            else:
                count_retries += 1
                continue

        # The while loop has ended, indicating that a new signal has been received
        return ''

    def __create_limit_order(self, side: str, qty: float):
        """
        Creates a Limit order using params: side, qty
        Returns:
            order_data if successful, otherwise None
        """

        while self.thread_ident == threading.get_ident():

            # Get the latest buy and sell orders from the order book
            ob_latest_buy_order, ob_latest_sell_order = self.get_latest_buy_and_sell_orders(self.coin_ticker)

            # Use the latest sell order to measure future entry size
            self.last_known_price = float(ob_latest_sell_order['price'])

            if side.lower() == 'buy':
                main_limit_order_data = self.place_limit_order_po(self.coin_ticker, 'Buy', qty, round((float(ob_latest_buy_order['price'])), 4))
            elif side.lower() == 'sell':
                main_limit_order_data = self.place_limit_order_po(self.coin_ticker, 'Sell', qty, round((float(ob_latest_sell_order['price'])), 4))
            else:
                return None

            # It has been found that, while using PostOnly, limit orders might be cancelled AFTER being created
            # Querying the most updated order status allows the verification of orders being cancelled by PostOnly
            # If that is the case, this routine will loop until the order enters to the order book
            # Otherwise, order data will be returned
            main_limit_order_data = self.get_order_by_id(self.coin_ticker, main_limit_order_data['result']['order_id'])
            if self.is_order_created(main_limit_order_data) or main_limit_order_data['result']['order_status'] == 'Filled':
                self.hmsg.msg('Limit order created')
                return main_limit_order_data

        # When the while loop exits, a new thread has started so no order was created
        self.hmsg.debug('I am not creating a limit order, new thread in')
        return None



    def tighten_limit_order(self, main_limit_order_data, count_retries) -> int:
        """
        # Takes the first created limit order data and tightens it according to market conditions.
        # Returns:
        # -1 : Abort limit order placement
        #  0 : Limit order filled
        #  1 : Retry to place limit order 
        """

        self.hmsg.msg('Monitoring limit order slippage')
        while self.thread_ident == threading.get_ident():
            
            # Update order data
            main_limit_order_data = self.get_order_by_id(self.coin_ticker, main_limit_order_data['result']['order_id'])
            handle_exchange_response(main_limit_order_data, 'Failed to retrieve Limit order data')

            # Check if the main limit order has been filled
            if main_limit_order_data['result']['order_status'] == 'Filled':
                self.hmsg.msg('Limit order filled!')
                self.limit_count += 1
                return BybitTicker.LIMIT_ORDER_FILLED

            # Latest buy and sell orders from the order book
            ob_latest_buy_order, ob_latest_sell_order = self.get_latest_buy_and_sell_orders(self.coin_ticker)
            
            # Open Buy order by market on too many attempts or price slippage
            if (count_retries > 3 \
                or self.has_price_increased(
                    curr_price=float(ob_latest_buy_order['price']),
                    org_price=main_limit_order_data['result']['price'],
                    slippage_perc=self.trade_market_on_slippage_perc
                    )) \
                and main_limit_order_data['result']['side'].lower() == 'buy':
                try:
                    # Cancel Limit order as the position will be opened by market instead
                    ret = self.cancel_limit_order(self.coin_ticker, main_limit_order_data['result']['order_id'])
                    handle_exchange_response(ret,'CRITICAL: Failed to cancel limit order v2')
                    if ret['ret_code'] == 0:
                        self.hmsg.msg('Buy limit order cancelled. Buying by market')

                    # Place Limit Buy order
                    main_limit_order_data = self.place_order(self.coin_ticker, 'Buy', main_limit_order_data['result']['qty'])
                    self.market_count += 1
                    return BybitTicker.LIMIT_ORDER_FILLED
                except Exception:
                    self.hmsg.err('Exception ocurred while opening by market. Limit order might got filled meanwhile. Returning...')
                    self.limit_count += 1
                finally:
                    return BybitTicker.LIMIT_ORDER_FILLED
            
            # Open Sell order by market on too many attempts or price slippage
            if (count_retries > 3 \
                or self.has_price_decreased(
                    curr_price=float(ob_latest_sell_order['price']),
                    org_price=main_limit_order_data['result']['price'],
                    slippage_perc=self.trade_market_on_slippage_perc
                    )) \
                and main_limit_order_data['result']['side'].lower() == 'sell':
                try:
                    # Cancel Limit order as the position will be opened by market instead
                    ret = self.cancel_limit_order(self.coin_ticker, main_limit_order_data['result']['order_id'])
                    handle_exchange_response(ret,'CRITICAL: Failed to cancel limit order v2')
                    if ret['ret_code'] == 0:
                        self.hmsg.msg('Sell limit order cancelled. Selling by market')
                    
                    # Place Limit Sell order
                    main_limit_order_data = self.place_order(self.coin_ticker, 'Sell', main_limit_order_data['result']['qty'])
                    self.market_count += 1
                except Exception:
                    self.hmsg.err('Exception ocurred while opening by market. Limit order might got filled meanwhile. Returning...')
                    self.limit_count += 1
                finally:
                    return BybitTicker.LIMIT_ORDER_FILLED

            # Tightens main limit order according to market move            
            order_price = float(main_limit_order_data['result']['price'])
            try:
                if main_limit_order_data['result']['side'].lower() == 'buy' \
                    and (float(ob_latest_buy_order['price']) > order_price):
                    self.hmsg.debug('Tightening: ' + str(count_retries))
                    self.cancel_limit_order(self.coin_ticker, main_limit_order_data['result']['order_id'])
                    count_retries += 1
                    return BybitTicker.RETRY_LIMIT_ORDER
                if main_limit_order_data['result']['side'].lower() == 'sell' \
                    and (float(ob_latest_sell_order['price']) < order_price):
                    self.hmsg.debug('Tightening: ' + str(count_retries))
                    self.cancel_limit_order(self.coin_ticker, main_limit_order_data['result']['order_id'])
                    count_retries += 1
                    return BybitTicker.RETRY_LIMIT_ORDER
            except Exception:
                self.hmsg.err('Exception ocurred while tightening Limit order. Might got filled meanwhile. Returning...')
                return BybitTicker.LIMIT_ORDER_FILLED
            sleep(128/1000)
        # while ends - Limit order monitoring
        # self.hmsg.debug('I am no longer the thread ident and will revert the order placement')
        try:
            # Cancel Limit order as new signal trade has been received
            #self.cancel_limit_order(self.coin_ticker, main_limit_order_data['result']['order_id'])
            self.hmsg.debug('Cancelled previous order as new signal has been received SQN')
        except Exception:
            self.hmsg.debug('Nothing to cancel. Returning...')
        finally:
            return BybitTicker.ABORT_LIMIT_ORDER
    # def ends

    def check_for_stop_limit_tsl(self, side :str):
        # Log that we're checking for stop-limit
        self.hmsg.msg('Checking for stop-limit...')

        # Initialize check counter
        check_count = 1

        # Set initial values for TSL prices
        tsl_long_upper_price = 0.5
        tsl_short_lower_price = 99999.5

        # Loop until thread is stopped
        while self.thread_ident == threading.get_ident():

            # Get latest buy and sell orders from order book
            latest_buy_order, latest_sell_order = self.get_latest_buy_and_sell_orders(self.coin_ticker)

            # Get current long and short positions
            curr_long_position, curr_short_position = self.fetch_ticker_positions()

            # Update TSL prices if necessary
            if float(latest_buy_order['price']) > tsl_long_upper_price:
                tsl_long_upper_price = float(latest_buy_order['price'])
            if float(latest_sell_order['price']) < tsl_short_lower_price:
                tsl_short_lower_price = float(latest_sell_order['price'])

            # Get size of current positions
            long_size = curr_long_position['size']
            short_size = curr_short_position['size']

            # Check if position has been closed by thread or user
            if (side.lower() == 'buy' and long_size == 0) \
                or side.lower() == 'sell' and short_size == 0:
                self.hmsg.err(f'Position no longer open. Closed by thread or user... side: {side}')
                return False

            # Check if TSL has been triggered for long position
            flag_sl_triggered = False
            if long_size > 0 \
                and self.has_price_decreased(
                    curr_price=float(latest_buy_order['price']),
                    org_price=tsl_long_upper_price,
                    slippage_perc=self.long_tsl_perc
                ):
                self.hmsg.msg('TSL Stop-Loss hit!')
                self.hmsg.msg('Forcing stop limit order...')
                # Increment stop-loss count
                self.sl_count += 1
                # Force stop-limit order
                self.force_stop_limit_order(curr_long_position)
                flag_sl_triggered = True

            # Check if TSL has been triggered for short position
            if short_size > 0 \
                and self.has_price_increased(
                    curr_price=float(latest_sell_order['price']),
                    org_price=tsl_short_lower_price,
                    slippage_perc=self.short_tsl_perc
                ):
                self.hmsg.msg('TSL Stop-Loss hit!')
                self.hmsg.msg('Forcing stop limit order...')
                # Increment stop-loss count
                self.sl_count += 1
                # Force stop-limit order
                self.force_stop_limit_order(curr_short_position)
                return None

            # Check if long position TSL was triggered and return None
            if flag_sl_triggered:
                return None

            # Sleep for a short period of time before checking again
            sleep(128 / 1000)

            # Increment check counter
            check_count += 1

        # If loop is exited, log that a new signal was received and force stop-limit order to close position
        self.hmsg.msg('New signal while checking for stop-limit order. Closing current position...')
        if side.lower() == 'buy':
            self.force_stop_limit_order(curr_long_position)
        elif side.lower() == 'sell':
            self.force_stop_limit_order(curr_short_position)


    def force_stop_limit_order(self, position_data):
        
        # Beware that 'position_data' param already has the 'result' scope
        
        self.hmsg.msg('Forcing STOP Limit order')
        count_retries = 0
        
        # Aquire a LOCK, as the same position cannot be closed by multiple threads
        # if self.STOP_LOCK:
        #     return False
        # self.hmsg.debug('Locking stop loss')
        # self.STOP_LOCK = True

        tsl_long_upper_price = 0.5
        tsl_short_lower_price = 99999.5

        while True:
            sl_order_data = None

            while True:
                # Latest buy and sell orders from the order book
                ob_latest_buy_order, ob_latest_sell_order = self.get_latest_buy_and_sell_orders(self.coin_ticker)

                try:
                    if position_data['side'].lower() == 'buy' \
                        and position_data['size'] > 0:
                        self.hmsg.debug('Placing stop-limit order - Sell')
                        # Place stop loss Order
                        sl_order_data = self.reduce_position_limit(
                            self.coin_ticker,
                            'Sell',
                            position_data['size'],
                            round(float(ob_latest_sell_order['price']), 4)
                        )
                    if position_data['side'].lower() == 'sell' \
                        and position_data['size'] > 0:
                        # Place stop loss Order
                        self.hmsg.debug('Placing stop-limit order - Buy')
                        sl_order_data = self.reduce_position_limit(
                            self.coin_ticker,
                            'Buy',
                            position_data['size'],
                            round(float(ob_latest_buy_order['price']), 4)
                        )
                except Exception:
                    self.hmsg.err('Exception ocurred while replacing SL order. Might got filled meanwhile. Returning...')
                    self.limit_count += 1
                    # self.STOP_LOCK = False
                    return True
                    
                sl_order_data = self.get_order_by_id(self.coin_ticker, sl_order_data['result']['order_id'])
                if sl_order_data['result']['order_status'] == 'Filled':
                    self.hmsg.msg('Stop-limit filled immediately!')
                    self.limit_count += 1
                    # self.STOP_LOCK = False
                    return True
                if self.is_order_created(sl_order_data):
                    self.hmsg.msg('Stop-limit order created')
                    break
                else:
                    self.hmsg.msg(f'Failed to place Stop-limit order. Retrying ({count_retries})')
                    #sleep(128 / 1000)
            # WHILE ENDS - Stop Limit order placement
                    
            self.hmsg.msg('Monitoring stop-limit order...')
            while True:
                
                # Get latest orderbook data
                ob_latest_buy_order, ob_latest_sell_order = self.get_latest_buy_and_sell_orders(self.coin_ticker)

                if float(ob_latest_buy_order['price']) > tsl_long_upper_price:
                    tsl_long_upper_price = float(ob_latest_buy_order['price'])
                if float(ob_latest_sell_order['price']) < tsl_short_lower_price:
                    tsl_short_lower_price = float(ob_latest_sell_order['price'])

                # Update Stop-limit order data
                sl_order_data = self.get_order_by_id(self.coin_ticker, sl_order_data['result']['order_id'])
                handle_exchange_response(sl_order_data, 'Failed to retrieve SL limit order data')
                
                # Check if the main limit order has been filled, if so, return
                if sl_order_data['result']['order_status'] == 'Filled':
                    self.hmsg.msg('Stop Limit order Filled, Terminating trade...')
                    self.limit_count += 1
                    # self.hmsg.debug('Retries: ' + str(count_retries))
                    self.print_statistics()
                    # self.hmsg.debug('Unlocking stop loss')
                    # self.STOP_LOCK = False
                    return True
                
                # If the attempt to close a trade by limit order fails, i.e., price slippage has occured,
                #  close it by market order.
                if (count_retries > 1 \
                    or self.has_price_decreased(
                        curr_price=float(ob_latest_buy_order['price']),
                        org_price=tsl_long_upper_price,
                        slippage_perc=(self.trade_market_on_slippage_perc + self.long_tsl_perc)
                        )) \
                    and position_data['side'].lower() == 'buy':
                    try:
                        ret = self.cancel_limit_order(self.coin_ticker, sl_order_data['result']['order_id'])
                        handle_exchange_response(ret,'CRITICAL: Failed to close SL order')
                        if ret['ret_code'] == 0:
                            self.hmsg.msg('Stop Limit order cancelled. Closing by market')
                        self.close_position_qty('Sell', position_data['size'])
                        self.market_count += 1
                    except Exception as ex:
                        self.hmsg.err('Market sell: Exception ocurred while closing long by market. Limit order might got filled meanwhile. Returning...')
                        self.hmsg.err(ex)
                        self.limit_count += 1
                    finally:
                        return True
                # Open Sell order by market on too many attempts or price slippage
                if (count_retries > 1 \
                    or self.has_price_increased(
                        curr_price=float(ob_latest_sell_order['price']),
                        org_price=tsl_short_lower_price,
                        slippage_perc=(self.trade_market_on_slippage_perc + self.short_tsl_perc)
                        )) \
                    and position_data['side'].lower() == 'sell':
                    try:
                        # Cancel Limit order as the position will be opened by market instead
                        ret = self.cancel_limit_order(self.coin_ticker, sl_order_data['result']['order_id'])
                        handle_exchange_response(ret,'CRITICAL: Failed to cancel limit order v2')
                        if ret['ret_code'] == 0:
                            self.hmsg.msg('Stop Limit order cancelled. Closing by market')
                        self.close_position_qty('Buy', position_data['size'])
                        self.market_count += 1
                    except Exception as ex:
                        self.hmsg.err('Market buy: Exception ocurred while closing short position by market. Limit order might got filled meanwhile. Returning...')
                        self.hmsg.err(ex)
                        self.limit_count += 1
                    finally:
                        return True


                order_price = float(sl_order_data['result']['price'])

                # Update SL order to a tighter one
                # position_side = position_data['side'].lower()
                # latest_sell_price = ob_latest_sell_order['price']
                # latest_buy_price = ob_latest_buy_order['price']
                #self.hmsg.debug(f'position-side: {position_side}, ob_buy: {latest_buy_price}, \
                #  ob_sell: {latest_sell_price}, sl_price: {order_price}')

                try:
                    if position_data['side'].lower() == 'buy' \
                        and (float(ob_latest_sell_order['price']) < order_price):
                        self.hmsg.debug('Tightning: ' + str(count_retries))
                        self.cancel_limit_order(self.coin_ticker, sl_order_data['result']['order_id'])
                        count_retries += 1
                        break
                    if position_data['side'].lower() == 'sell' \
                        and (float(ob_latest_buy_order['price']) > order_price):
                        self.hmsg.debug('Tightning: ' + str(count_retries))
                        self.cancel_limit_order(self.coin_ticker, sl_order_data['result']['order_id'])
                        count_retries += 1
                        break
                except Exception:
                    self.hmsg.err('Exception ocurred while tightening Stop-Limit order. Might got filled meanwhile. Returning...')
                    return True
                sleep(64/1000)
            # WHILE ENDS - Stop-limit order monitoring
        # WHILE ENDS - Main while ends  
    # DEF ENDS
            
    """
    def cancel_tp_limit_order(self):

        if self.is_order_created(self.get_order_by_id(self.coin_ticker, self.tp_order_id)):
            ret = self.cancel_limit_order(self.coin_ticker, self.tp_order_id)
            handle_exchange_response(ret,'CRITICAL: Failed to close TP order')
            if ret['ret_code'] == 0:
                self.hmsg.err('TP Limit order cancelled.')
    """
    
    def cancel_all_trades_limit(self, position_data):
        """
        This method cancels all the limit orders for the given position data and forces a stop limit order to be executed.
        It increments the reversal count and updates the position data by placing a stop limit order.

        Args:
            position_data (dict): A dictionary containing position data for the current ticker.
        """
        self.reversal_count += 1
        # self.cancel_tp_limit_order() - Commented out as it is not being used in the code
        self.force_stop_limit_order(position_data)
        

    def print_statistics(self):
        """
        This method prints out the statistics for the trading bot, such as TP count, SL count, reversal count, and 
        market and limit order counts.
        """
        self.hmsg.msg(f'TPs: {self.tp_count}, SL: {self.sl_count}')
        self.hmsg.msg(f'Reversals: {self.reversal_count}')
        self.hmsg.msg(f'Limit: {self.limit_count}, Market: {self.market_count}')

