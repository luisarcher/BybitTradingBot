"""

"""
import logging

from bybit_ticker import BybitTicker
from config.main_config import MainConfig

MainConfig()
ret = ''
# matic = BybitTicker('MATIC')

ticker = BybitTicker('ETH')


hmsg = MainConfig.getinstance().message_handler

# hmsg.msg('this is a msg')

# hmsg.err('this is an error msg')


# ret = matic.place_market_order('Buy')

#matic = BybitTicker('MATIC')

ret = ticker.get_wallet_balance()

#ret = matic.place_market_order_po('Buy')

#ret = matic.reduce_position_size('Sell')

# ret = matic.place_market_order('Sell')

# ret = matic.get_position()

#print('Order book:')
#ret = matic.get_latest_buy_and_sell_orders('MATIC')
#print(ret)



#ret = matic.place_order('MATIC', 'Buy', 5)
#ret = matic.place_order('MATIC', 'Sell', 4)
#print(ret)
#ret = matic.add_reduce_margin('MATIC', 'Sell', -5)
print(ret)
#matic.set_buy_leverage('MATIC', 12)
#ret = matic.take_profits('MATIC', 'Buy', 2)
#ret = matic.reduce_position('MATIC', 'Buy', 8)
#print(ret)



#ret = MainConfig.getinstance().get_user_data()


# Place Limit order
"""
latest_buy_order, latest_sell_order = matic.get_latest_buy_and_sell_orders('MATIC')

print(latest_buy_order)
print(latest_sell_order)
latest_buy_order_price = float(latest_buy_order['price'])
ret = matic.place_limit_order_po('MATIC', 'Buy', 2, latest_buy_order_price - 0.0001)
"""
"""
{'ret_code': 0, 'ret_msg': 'OK', 'ext_code': '', 'ext_info': '',
 'result': {'order_id': 'f62bd4c5-dc92-43bf-a532-6dbfea01506a',
  'user_id': 14219791, 'symbol': 'MATICUSDT', 'side': 'Buy',
   'order_type': 'Limit', 'price': 1.6393, 'qty': 2, 'time_in_force': 'PostOnly',
    'order_status': 'Created', 'last_exec_price': 0, 'cum_exec_qty': 0,
     'cum_exec_value': 0, 'cum_exec_fee': 0, 'reduce_only': False,
      'close_on_trigger': False, 'order_link_id': '',
       'created_time': '2022-01-27T14:37:47Z', 'updated_time': '2022-01-27T14:37:47Z',
        'take_profit': 0, 'stop_loss': 0, 'tp_trigger_by': 'UNKNOWN',
         'sl_trigger_by': 'UNKNOWN', 'position_idx': 1}, 'time_now': '1643294267.959463',
          'rate_limit_status': 98, 'rate_limit_reset_ms': 1643294267954,
           'rate_limit': 100}
"""

# ret = matic.get_symbol_info('MATIC')

# print('query symbol')
# ret = ticker.get_symbol_info('BTC')
# print(ret)

# print('latest information for symbol')
# ret = ticker.get_ticker_info()
# print(ret)
