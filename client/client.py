"""
This file encapsulates a Client entity within the OLAF-Neighbourhood protocol.
"""

import threading
from crypto_utils import generate_private_key
from client_events import Event
from request import Request
import socketio


class Client:
    """
    Represents a Client in the OLAF-Neighbourhood protocol.

    Attributes:
        host (str): The server host.
        port (int): The server port.
        private_key: The client's private key.
        nonce (int): A counter for unique requests.
        user_list (dict): A dictionary to store users.
        message_buffer (list): A list to buffer messages.
        event (Event): An instance of Event for handling events.
        request (Request): An instance of Request for making requests.
        socket_io: SocketIO client instance for communication.
    """

    response_event = threading.Event()

    def __init__(self, host, port):
        """
        Initializes the Client with the specified host and port.

        Args:
            host (str): The server host.
            port (int): The server port.
        """
        self.host = host
        self.port = port

        self.private_key = generate_private_key()
        self.nonce = 1
        self.user_list = {}
        self.message_buffer = []
        self.event = Event(self)
        self.request = Request(self)

        self.socket_io = socketio.Client()
        self.socket_io.on('connect', self.event.connect)
        self.socket_io.on('hello', self.event.hello)
        self.socket_io.on('client_list', self.event.client_list)
        self.socket_io.on('message', self.event.message)

    def initialise(self):
        """
        Starts the initialization process for the client.
        Connects to the server and sends initial requests.
        """
        print("!------Starting Initialisation Process------!")
        self.request.connect()
        self.request.hello()
        self.request.client_list_request()
        print("!------Initialisation Process Completed------!")

    def run(self):
        """
        Runs the client, allowing for user input to send messages and display buffered messages.
        """
        return  # Implementation needed here.


if __name__ == '__main__':
    SERVER_HOST = "localhost"
    SERVER_PORT = 4678
    client = Client(SERVER_HOST, SERVER_PORT)
    client.initialise()
    client.request.public_chat("Testing Testing 123")
    client.socket_io.wait()
