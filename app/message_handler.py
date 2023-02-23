"""
MessageHandler class for printing messages with threading information.
"""
import threading

class MessageHandler:

    def __init__(self) -> None:
        pass

    def msg(self, msg: str) -> None:
        """
        Prints a message with the thread identifier.

        Args:
            msg (str): The message to be printed.
        """
        print(f'[{threading.get_ident()}] --> {msg}')

    def err(self, msg: str) -> None:
        """
        Prints an error message with the thread identifier.

        Args:
            msg (str): The error message to be printed.
        """
        print(f'[{threading.get_ident()}] [!] {msg}')

    def debug(self, msg: str) -> None:
        """
        Prints a debug message with the thread identifier if DEBUG mode is enabled.

        Args:
            msg (str): The debug message to be printed.
        """
        # todo: check if DEBUG is true on MainConfig
        print(f'[{threading.get_ident()}] debug msg --> {msg}')
