import socketio
import threading

from collections import namedtuple
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from message_utils import make_signed_data_msg
from message_utils import is_valid_message, process_data
# Keys
from crypto_utils import generate_private_key, get_public_key
# Decryption
from crypto_utils import decrypt_symm_key, decrypt_message

# Object to store processed messages on the client side
Msg = namedtuple('Msg', ['text', 'sender', 'participants'])

class Client:
    
    response_event = threading.Event()

    def __init__(self, host, port):
        self.private_key = generate_private_key()
        self.counter = 0
        self.user_list = {}
        self.host = host
        self.port = port
        self.socket_io = socketio.Client()
        self.message_buffer = []

        # Event handlers
        self.socket_io.on('connect', self.connect)
        self.socket_io.on('hello', self.hello)
        self.socket_io.on('client_list', self.client_list)
        self.socket_io.on('message', self.message)
    
    def initialise(self):
        print("!------Starting Initialisation Process------!")
        self.connect_to_server()
        self.send_hello()
        self.request_user_list()
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
    
    # Event handlers
    def connect(self):
        print("Successfully connected to server")
        self.response_event.set()

    def hello(self):
        print("Server accepted the request for service")
        self.response_event.set()

    def client_list(self, data):

        print("Received user list from server")

        # The server key should contain a list of JSON objects
        # which each have an address and list of clients
        json_server_list = {}
        if(data):
            json_server_list = data['servers']

        # The client maps each user to their host server
        for server in json_server_list:
            for client in server['clients']:
                self.user_list[client] = server['address']
        self.response_event.set()

    def connect_to_server(self):
        # Connect to server
        print("Attempting to connect to server")
        self.socket_io.connect(f'http://{self.host}:{self.port}')
        self.response_event.wait()
    
    def send_hello(self):
        hello_data = {
            'type': 'hello',
            'public_key': get_public_key(self.private_key)
        }

        print("Requesting service from server")
        signed_hello_msg = make_signed_data_msg(hello_data, str(self.counter))
        self.socket_io.emit("hello", signed_hello_msg)
        self.response_event.clear()
        self.response_event.wait()

    def request_user_list(self):
        print("Requesting user list from server")
        # Request server for client list
        self.socket_io.emit("client_list_request", {
            "type": "client_list_request"
        })
        self.response_event.clear()
        self.response_event.wait()
    
    def message(self, data):
        data = process_data(data).get('data')
        msg_type = None

        if(data):
            msg_type = data.get('type')
        else:
            print("Ignoring message due to error")
            return
        
        if not is_valid_message(data, msg_type):
            print(f"Invalid message recieved of type {msg_type}")
            return

        if msg_type == 'chat' or msg_type == 'public_chat':
            self.handle_chat(data)
        else:
            print("Unknown message type received")

    def handle_chat(self, data):

        # Message must be valid to reach this point
        # Parse the data to get the chat field

        if(data['type'] == "public_chat"):
            # Create message and push to buffer
            msg = Msg(data['message'], data['sender'], ["Public"])
            self.message_buffer.append(msg)
        else:
            # Extract symmetric key from symm-key list
            encrypted_chat = data["chat"]
            iv = data["iv"]
            chat = None
            for encrypted_symm_key in data['symm_keys']:
                symm_key = decrypt_symm_key(encrypted_symm_key, self.private_key)
                chat = decrypt_message(symm_key, encrypted_chat, iv)
                if chat: break
            
            if(not chat):
                print("Couldn't find the symmetric key, assuming message was not destined for me")
                return
                
            # Validate decrypted chat JSON
            if not is_valid_message(chat, 'chat'):
                print("Chat message received and decrypted, although the chat portion was invalid")

            # Store decrypted message info in a buffer
            msg = Msg(chat['message'], chat['participants'][0], chat['participants'][1:])
            self.message_buffer.append(msg)
    

if __name__ == '__main__':
    server_host = "localhost"
    server_port = 4678
    client = Client(server_host, server_port)
    client.initialise()
