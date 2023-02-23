# BybitTradingBot

This is a Python application that uses the Flask web framework and the PyBit library to connect to the Bybit cryptocurrency exchange API. The application listens to TradingView alerts and executes trades based on the received signals.

## Requirements

The following Python packages are required and can be installed using pip install -r requirements.txt:

- Flask
- PyBit

## Configuration

The bot's configuration is defined in the config.json file. An example file with the required fields is provided in config.json.example. The configuration file contains the user data for the Bybit API, such as the API key and secret, as well as the setup for the tickers to be traded, including the wallet percentage, long and short leverage, among other parameters.

```json
{
    "user_data" : {
        "api_key" : "BYBIT_API_KEY",
        "api_secret" : "BYBIT_API_SECRET",
        "collateral" : "USDT"
    },

    "tickers" : {
        "ETH" : {
            "wallet_perc" : 20,
            "long_leverage" : 6,
            "short_leverage" : 6
        }
    }
}
```

## Usage

To start the application, run **python app.py** in the terminal. The application will start the Flask server and listen for incoming TradingView alerts at the /webhook endpoint.

### TradingView Alerts

To send an alert to the bot, create a TradingView alert with the following format:

```json
{
    "ticker": "ETH",
    "side": "{{strategy.order.action}}",
    "comment": "{{strategy.order.comment}}"
}
```

Where:

- "ticker" is the symbol to be traded (e.g., "ETH").
- "side" is the action of the order, which should be either "buy" or "sell".
- "comment" is an optional comment that can be used to carry custom messages from Pine script to the bot.

When a TradingView alert is received, the application will spawn a new thread to manage the ticker, killing any previous thread for the same ticker. This strategy prioritizes new signals.
