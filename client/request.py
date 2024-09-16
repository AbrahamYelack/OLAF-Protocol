import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from message_utils import make_signed_data_msg
from crypto_utils import generate_private_key, get_public_key, get_fingerprint

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
        signed_hello_msg = make_signed_data_msg(hello_data, str(self.client.nonce))
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
    
    def public_chat(self, message_text):
        print("Sending public chat")
        fingerprint = get_fingerprint(self.client.private_key)
        public_chat_data = {
            'type': 'public_chat',
            'sender': fingerprint,
            'message': str(message_text)
        }
        public_chat = make_signed_data_msg(public_chat_data, str(self.client.nonce))
        self.client.nonce += 1
        self.client.socket_io.emit("message", public_chat)