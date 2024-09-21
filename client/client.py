"""
This file encapsulates a Client entity within the OLAF-Neighbourhood protocol.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'libs')))
import argparse
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
    request_types = ['public_chat', 'chat']

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
        while(True):
            for index, value in enumerate(self.request_types):
                print(f"{index}: '{value}'")
            index = int(input("What type of message would you like to send: "))

            if(self.request_types[index] == 'public_chat'):
                message = str(input("Enter the message: "))
                self.request.public_chat(message)
            elif(self.request_types[index] == 'chat'):
                users = list(self.user_list.keys())
                for index, value in enumerate(users):
                    print(f"{index}: '{value}'")
                recipients_string = str(input("Which users you like to communicate with (comma seperated): "))
                recipients_string = recipients.replace(" ", "")
                recipients_string = recipients_string[::2] 
                recipients = []
                for i in range(len(recipients_string)):
                    recipients.append(self.user_list[int(i)])
                message = str(input("Enter the message: "))
                self.request.chat(message, *recipients)
            else: print("Sorry, that isn't a valid option")





if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, required=True, help='Hostname')
    parser.add_argument('--port', type=int, required=True, help='Port')
    args = parser.parse_args()

    SERVER_HOST = args.host
    SERVER_PORT = args.port
    client = Client(SERVER_HOST, SERVER_PORT)
    client.initialise()
    client.run()
