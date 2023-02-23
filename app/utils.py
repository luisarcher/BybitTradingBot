import ast
import math


DEBUG = False


def parse_webhook(webhook_data: str) -> dict:
    """
    This function takes the string from tradingview and turns it into a python dict.
    :param webhook_data: POST data from tradingview, as a string.
    :return: Dictionary version of string.
    """
    try:
        data = ast.literal_eval(webhook_data)
        return data
    except:
        return None


def handle_exchange_response(response: dict, if_error_message: str='') -> bool:
    """
    This function handles the response from the exchange API.
    :param response: response from the exchange API.
    :param if_error_message: message to be displayed if an error occurs.
    :return: True if the response is successful, False otherwise.
    """
    if DEBUG:
        print('json from bybit:')
        print(response)
    if response['ret_code'] != 0:
        if if_error_message:
            err(if_error_message)
        print('[!] Msg:', response['ret_msg'])
        return False
    else:
        if DEBUG:
            print('Bybit:', response['ret_msg'])
    return True


def err(msg: str) -> None:
    """
    This function handles error messages.
    :param msg: error message.
    """
    print(f'[!] {msg}')


def round_down(non_rounded_entry_size: float, step: float) -> float:
    """
    This function rounds down a given number to the nearest multiple of a given step.
    :param non_rounded_entry_size: the number to be rounded down.
    :param step: the step to which the number should be rounded down.
    :return: the rounded down number.
    """
    return math.floor(non_rounded_entry_size / step) * step
