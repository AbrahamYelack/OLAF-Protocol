"""
This class encapsulates the logic for constructing and sending client messages.

Post connection establishment, all client-sent messages are of type 'signed_data' 
with 'client_list_request' being the single exception.

The 'data' field of a 'signed_data' message can have the following types:
- 'hello': Establishes client-server agreement.
- 'chat': A private message.
- 'public_chat': A broadcasted message.
"""

from message_utils import make_signed_data_msg
from crypto_utils import get_public_key, get_fingerprint
from crypto_utils import generate_key, encrypt_message, encrypt_symm_keys
from config import MANAGER_KEY  # Special key used for potential administrative actions


class Request:
    """
    Handles requests from the client to the server.

    Attributes:
        client: An instance of the Client class to manage socket communication.
    """

    def __init__(self, client):
        """
        Initializes the Request object with the specified client.

        Args:
            client: An instance of the Client class.
        """
        self.client = client

    def connect(self):
        """
        Connects the client to the server.
        """
        print("Attempting to connect to server")
        self.client.socket_io.connect(f"ws://{self.client.host}:{self.client.port}")
        self.client.response_event.wait()

    def hello(self):
        """
        Sends a hello message to the server to establish service agreement.
        """
        hello_data = {
            "type": "hello",
            "public_key": get_public_key(
                self.client.private_key
            ),  # Normal client key transmission
        }
        signed_hello_msg = make_signed_data_msg(
            hello_data, str(self.client.nonce), self.client.private_key
        )
        self.client.nonce += 1
        print("Requesting service from server")
        self.client.socket_io.emit("hello", signed_hello_msg)
        self.client.response_event.clear()
        self.client.response_event.wait()

    def client_list_request(self):
        """
        Requests the client list from the server.
        """
        print("Requesting client list from server")

        self.client.socket_io.emit(
            "client_list_request", {"type": "client_list_request"}
        )

        self.client.response_event.clear()
        self.client.response_event.wait()

    def public_chat(self, message_text):
        """
        Sends a public chat message to all clients.

        Args:
            message_text (str): The message to be sent in the public chat.
        """
        fingerprint = get_fingerprint(get_public_key(self.client.private_key))
        public_chat_data = {
            "type": "public_chat",
            "sender": fingerprint,
            "message": str(message_text),  # Standard public message format
        }
        public_chat_msg = make_signed_data_msg(
            public_chat_data, str(self.client.nonce), self.client.private_key
        )
        self.client.nonce += 1

        print("Sending public chat")
        self.client.socket_io.emit("message", public_chat_msg)

    def chat(self, message_txt, *recipients):
        """
        Sends a private chat message to specified recipients.

        Args:
            message_txt (str): The message to be sent.
            recipients (tuple): A variable number of recipients for the chat message.
        """
        sender_fingerprint = get_fingerprint(get_public_key(self.client.private_key))
        participants_list = [sender_fingerprint]
        for recipient in recipients:
            fingerprint = get_fingerprint(recipient)
            participants_list.append(fingerprint)

        chat = {
            "chat": {
                "participants": participants_list,
                "message": message_txt,  # Private message content
            }
        }

        symm_key = generate_key()
        encryption_data = encrypt_message(symm_key, chat)
        encrypted_message = encryption_data["message"]  # Already base64
        iv = encryption_data["iv"]  # Already base64

        # Retrieve the sender's public key
        sender_public_key = get_public_key(self.client.private_key)

        # Include the sender's public key in the encrypted symmetric keys
        encrypted_symm_keys = encrypt_symm_keys(
            symm_key, sender_public_key, *recipients
        )

        destination_server_list = [
            self.client.user_list[recipient] for recipient in recipients
        ]

        data = {
            "type": "chat",
            "destination_servers": destination_server_list,
            "iv": iv,
            "symm_keys": encrypted_symm_keys,
            "chat": encrypted_message,  # Encrypted private message sent
        }

        chat_message = make_signed_data_msg(
            data, str(self.client.nonce), self.client.private_key
        )
        self.client.nonce += 1
        print("Sending chat")
        self.client.socket_io.emit("message", chat_message)
