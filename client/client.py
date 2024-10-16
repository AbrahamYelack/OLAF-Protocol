"""
This file encapsulates a Client entity within the OLAF-Neighbourhood protocol.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "libs")))
import argparse
import threading
from crypto_utils import generate_private_key
from client_events import Event
from client_cli import ClientCLI
from request import Request
import socketio


class Client:
    """
    Represents a Client in the OLAF-Neighbourhood protocol.

    Attributes:
        host (str): The server host.
        port (int): The server port.
        private_key (str-base64): The client's private key.
        nonce (int): A counter for unique requests.
        user_list (dict): A dictionary to store users.
        message_buffer (list): A list to buffer messages.
        event (Event): An instance of Event for handling events.
        request (Request): An instance of Request for making requests.
        socket_io: SocketIO client instance for communication.
    """

    response_event = threading.Event()
    request_types = ["public_chat", "chat", "file_upload", "file_download"]

    def __init__(self, host, port):
        """
        Initializes the Client with the specified host and port.

        Args:
            host (str): The server host.
            port (int): The server port.
        """
        self.host = host
        self.port = port

        # Private key of the client (str-base64)
        self.private_key = generate_private_key()
        # Nonce/counter for tracking messages, including secure communication sequences
        self.nonce = 1
        # Map of public_key(str) to server_ip(str)
        self.user_list = {}
        # Map of fingerprint(str) to counter/nonce(int)
        self.user_counter_map = {}
        # List of received Msg objects
        self.message_buffer = []
        # Download URLs of uploaded files
        self.download_links = {}

        # Event, Request and the CLI objects, CLI is run on client startup
        self.event = Event(self)
        self.request = Request(self)
        self.client_cli = ClientCLI(self)

        # Track processed message IDs to prevent duplicates
        self.processed_message_ids = set()

        # Create the web socket client and attach the relevant
        # listeners/handlers defined in the Event class
        self.socket_io = socketio.Client()
        self.socket_io.on("connect", self.event.connect)
        self.socket_io.on("hello", self.event.hello)
        self.socket_io.on("client_list", self.event.client_list)
        self.socket_io.on("message", self.event.message)

    def initialise(self):
        """
        Starts the initialization process for the client.
        Connects to the server and sends mandatory startup
        requests.
        """
        print("!------Starting Initialisation Process------!")
        self.request.connect()
        self.request.hello()
        self.request.client_list_request()
        print("!------Initialisation Process Completed------!")

    def run(self):
        """
        Runs the client, allowing for user input to send messages, view users and display buffered messages.
        """
        self.client_cli.run()


# Entry point to read in the host and port of the Server that the
# client wishes to connect to, starts the initialisation process and
# the CLI loop for user interaction
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, required=True, help="Hostname")
    parser.add_argument("--port", type=int, required=True, help="Port")
    args = parser.parse_args()

    SERVER_HOST = args.host
    if SERVER_HOST == "localhost":
        SERVER_HOST = "127.0.0.1"
        
    SERVER_PORT = args.port
    client = Client(SERVER_HOST, SERVER_PORT)
    client.initialise()
    client.run()
