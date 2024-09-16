import socketio
import threading
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from crypto_utils import generate_private_key
from client_events import Event
from request import Request

class Client:
    
    response_event = threading.Event()

    def __init__(self, host, port):
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
        print("!------Starting Initialisation Process------!")
        self.request.connect()
        self.request.hello()
        self.request.user_list()
        print("!------Initialisation Process Completed------!")
    
    def run(self):
        # Could visualise the users currently in the user list
        # and allow the user to choose who they want to send to
        # Request for user input regarding:
            # Type of chat message to send: Public Chat, Chat

        # OR

        # Create and document command line input that can be parsed 
        # and the operation executed

        # Need method of displaying reeived messages to the client:
            # Do we buffer messages until read is requested?
            # Do we immediately display the received message
        return
    

if __name__ == '__main__':
    server_host = "localhost"
    server_port = 4678
    client = Client(server_host, server_port)
    client.initialise()
    client.request.public_chat("Testing Testing 123")
    client.socket_io.wait()
