"""
This module contains a Flask application to handle incoming webhook requests.
"""

from config.main_config import MainConfig
from alert_manager import AlertManager
from utils import parse_webhook
from flask import Flask, request, abort
import threading

# Create Flask object called app.
app = Flask(__name__)
alert_manager = AlertManager()

@app.route('/')
def root():
    """
    A Flask route to return 'online' as a status check.
    """
    return 'online'

def handle_alert_thread(data):
    """
    A function to handle incoming alerts in a separate thread.

    :param data: a dictionary representing the incoming alert
    """
    alert_manager.handle_alert(data)

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    A Flask route to handle incoming webhooks.

    :return: 'ok' if the webhook is successfully handled, 'nok' and a 404 error otherwise
    """
    if request.method == 'POST':
        # Parse the string data from TradingView into a python dict
        # Example of the data received:
        # { "ticker":"MATIC", "side":"Buy"}
        data = parse_webhook(request.get_data(as_text=True))
        if data is None:
            return 'nok', 404

        # Create a new thread to handle the alert
        th = threading.Thread(target=handle_alert_thread, args=(data,))
        th.start()

        print('POST Received:', data)
        return 'ok', 200
    else:
        abort(400)

@app.route('/test_buy', methods=['GET'])
def test_buy():
    """
    A Flask route to test a buy alert.

    :return: 'ok' if the alert is successfully handled, 'nok' and a 404 error otherwise
    """
    ticker = request.args.get('ticker')
    if request.method == 'GET':
        # Parse the string data from TradingView into a python dict
        mock_text = str({"ticker":ticker,"side":"buy","comment":"entry"})
        data = parse_webhook(mock_text)

        print('POST Received:', data)

        # Create a new thread to handle the alert
        th = threading.Thread(target=handle_alert_thread, args=(data,))
        th.start()
        return 'ok', 200
    else:
        abort(400)

@app.route('/test_sell', methods=['GET'])
def test_sell():
    """
    A Flask route to test a sell alert.

    :return: 'ok' if the alert is successfully handled, 'nok' and a 404 error otherwise
    """
    ticker = request.args.get('ticker')
    if request.method == 'GET':
        # Parse the string data from TradingView into a python dict
        mock_text = str({"ticker":ticker,"side":"sell","comment":"close"})
        data = parse_webhook(mock_text)
        print('POST Received:', data)

        # Create a new thread to handle the alert
        th = threading.Thread(target=handle_alert_thread, args=(data,))
        th.start()
        return 'ok', 200
    else:
        abort(400)

if __name__ == '__main__':
    MainConfig()
    print("Bot starting...")
    app.run(host='0.0.0.0', port=5001)
