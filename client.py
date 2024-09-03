import socketio
import threading
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from message_utils import make_signed_data_msg
from crypto_utils import generate_private_key, get_public_key

# RSA private key object
private_key = generate_private_key()
# Counter of message sent
counter = 0
# Stores User (public-key) to Server (IP Address) mapping
user_list = {}
# Synchronisation utility
response_event = threading.Event()

socket_io = socketio.Client()

@socket_io.event
def connect():
    print("Successfully connected to server")
    response_event.set()

@socket_io.event
def hello():
    print("Server accepted the request for service")
    response_event.set()

@socket_io.event
def client_list(data):

    print("Received user list from server")

    # The server key should contain a list of JSON objects
    # which each have an address and list of clients
    json_server_list = {}
    if(data):
        json_server_list = data['servers']

    # The client maps each user to their host server
    for server in json_server_list:
        for client in server['clients']:
            user_list[client] = server['address']
    response_event.set()

def setup():

    print("!------Starting Initialisation Process------!")
    # Connect to server
    print("Attempting to connect to server")
    socket_io.connect("http://localhost:4678")
    response_event.wait()

    hello_data = {
        'type': 'hello',
        'public_key': get_public_key(private_key)
    }

    print("Requesting service from server")
    signed_hello_msg = make_signed_data_msg(hello_data, str(counter))
    socket_io.emit("hello", signed_hello_msg)
    response_event.clear()
    response_event.wait()

    print("Requesting user list from server")
    # Request server for client list
    socket_io.emit("client_list_request", {
        "type": "client_list_request"
    })
    response_event.clear()
    response_event.wait()

    print("!------Initialisation Process Completed------!")


if __name__ == '__main__':
    setup()
    socket_io.wait()
