"""
This module encapsulates the Event class, which handles the client-side events
for the OLAF-Neighbourhood protocol. It includes methods for processing various
events such as connecting to the server, receiving user lists, and handling
messages. The Event class manages the interaction between the client and server,
ensuring that messages are processed appropriately based on their types.

Key functionalities:
- Connecting to the server and handling connection events.
- Processing incoming messages, including chat and public chat types.
- Maintaining a buffer of messages for client-side access.
"""

from collections import namedtuple
from message_utils import is_valid_message, process_data
from crypto_utils import decrypt_symm_key, decrypt_message

# Object to store processed messages on the client side
Msg = namedtuple('Msg', ['text', 'sender', 'participants'])

class Event:
    """
    Handles events related to client-server communication.

    Attributes:
        client: An instance of the Client class to manage socket communication.
    """

    def __init__(self, client):
        """
        Initializes the Event object with the specified client.

        Args:
            client: An instance of the Client class.
        """
        self.client = client

    def connect(self):
        """Handles successful connection to the server."""
        print("Successfully connected to server")
        self.client.response_event.set()

    def hello(self):
        """Handles acknowledgment of service request from the server."""
        print("Server accepted the request for service")
        self.client.response_event.set()

    def client_list(self, data):
        """
        Processes the list of clients received from the server.

        Args:
            data: The data containing the list of clients and their server addresses.
        """
        print("Received user list from server")

        data = process_data(data)

        json_server_list = data.get('servers') if data else None

        if json_server_list:
            for server in json_server_list:
                for client in server['clients']:
                    self.client.user_list[client] = server['address']
        self.client.response_event.set()

    def message(self, data):
        """
        Processes incoming messages from the server.

        Args:
            data: The incoming message data.
        """
        data = process_data(data).get('data')
        if data is None:
            print("Ignoring message due to error")
            return

        msg_type = data.get('type')
        if not is_valid_message(data, msg_type):
            print(f"Invalid message received of type {msg_type}")
            return

        if msg_type in {'chat', 'public_chat'}:
            self.client.handle_chat(data)
        else:
            print("Unknown message type received")

    def handle_chat(self, data):
        """
        Handles chat messages received from the server.

        Args:
            data: The chat message data.
        """
        if data['type'] == "public_chat":
            msg = Msg(data['message'], data['sender'], ["Public"])
            self.client.message_buffer.append(msg)
        else:
            encrypted_chat = data["chat"]
            iv = data["iv"]
            chat = None

            for encrypted_symm_key in data['symm_keys']:
                symm_key = decrypt_symm_key(encrypted_symm_key, self.client.private_key)
                chat = decrypt_message(symm_key, encrypted_chat, iv)
                if chat:
                    break
            if chat is None:
                print("""Couldn't decrypt chat segment, assuming
                it is not addressed to me and dropping message""")
                return
            if not is_valid_message(chat, 'chat'):
                print("Chat message decrypted but is invalid, dropping message")
                return

            msg = Msg(chat['message'], chat['participants'][0], chat['participants'][1:])
            self.client.message_buffer.append(msg)
