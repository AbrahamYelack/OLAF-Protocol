import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from message_utils import make_signed_data_msg
from crypto_utils import generate_private_key, get_public_key

class Request:

    def __init__(self, client):
        self.client = client

    def connect(self):
        # Connect to server
        print("Attempting to connect to server")
        self.client.socket_io.connect(f'http://{self.client.host}:{self.client.port}')
        self.client.response_event.wait()
    
    def hello(self):
        hello_data = {
            'type': 'hello',
            'public_key': get_public_key(self.client.private_key)
        }

        print("Requesting service from server")
        signed_hello_msg = make_signed_data_msg(hello_data, str(self.client.counter))
        self.client.socket_io.emit("hello", signed_hello_msg)
        self.client.response_event.clear()
        self.client.response_event.wait()

    def user_list(self):
        print("Requesting user list from server")
        # Request server for client list
        self.client.socket_io.emit("client_list_request", {
            "type": "client_list_request"
        })
        self.client.response_event.clear()
        self.client.response_event.wait()