import logging
import time
from datetime import datetime
import json
from message_handler import MessageHandler


class MainConfig:
    """
    This class stores all the internal application status and configuration.
    """

    CONFIG_FILENAME = "./app/config/config.json"
    DEBUG = False

    __instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures the class has only one instance by returning the existing instance if it exists or creating a new one.
        """
        if cls.__instance is None:
            cls.__instance = super(MainConfig, cls).__new__(cls)
        return cls.__instance

    def __init__(self, config_file=CONFIG_FILENAME):
        """
        Initializes the instance with the given configuration file, sets up logging and message handler.
        """
        # Config properties
        self.config_file_path = config_file
        self.config_file_contents = None
        self.get_config_file_contents()

        # Sets up the Logger
        logging.getLogger().setLevel('INFO')
        logging.basicConfig(filename='./app/log/' + time.strftime("%Y_%m_%d-%H_%M_%S") + '.log',
                            level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s',
                            filemode="w")

        # Sets up the message handler
        self.message_handler = MessageHandler()

    @staticmethod
    def getinstance():
        """
        Static method to get the instance of the class.
        """
        if MainConfig.__instance is None:
            MainConfig()
        return MainConfig.__instance

    def get_config_file_contents(self):
        """
        Reads and returns the contents of the configuration file.
        """
        if self.config_file_contents is None:
            with open(self.config_file_path, 'r') as file:
                self.config_file_contents = json.loads(file.read())
        return self.config_file_contents

    def get_user_data(self):
        """
        Returns the user data from the configuration file.
        """
        return self.config_file_contents['user_data']

    def get_ticker_data(self, pair):
        """
        Returns the ticker data for the given pair from the configuration file.
        """
        return self.config_file_contents['tickers'][pair]

    def get_ticker_list(self):
        """
        Returns a list of ticker pairs from the configuration file.
        """
        return self.config_file_contents['tickers'].keys()
