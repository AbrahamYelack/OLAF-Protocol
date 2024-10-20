"""
This module encapsulates the logic for processing client-side events
for the OLAF-Neighbourhood protocol.

Key functionalities:
- Event handlers for connection and hello confirmation responses from the 
  parent server.
- Processing incoming messages, including chat and public chat types.
- Maintaining a buffer of messages for client-side access.
"""

import base64
import logging
from collections import namedtuple
from message_utils import is_valid_message, process_data, validate_signature
from crypto_utils import (
    decrypt_symm_key,
    decrypt_message,
    get_fingerprint,
    get_public_key,
)

# Object to store processed messages on the client side
Msg = namedtuple("Msg", ["text", "sender", "participants"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Event:
    """
    Handles events triggered/sent from the parent Server to the Client.

    Attributes:
        client: An instance of the Client class this event class handles.
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
        logger.info("Successfully connected to server")
        self.client.response_event.set()

    def hello(self):
        """Handles acknowledgment of service request from the server."""
        logger.info("Server accepted the request for service")
        self.client.response_event.set()

    def client_list(self, data):
        """
        Processes the list of clients received from the server.

        Args:
            data: The data containing the list of clients and their server addresses.
        """
        data = process_data(data)
        if not data:
            logger.warning("No data received in client list")
            return

        server_list = data.get("servers")
        if server_list:
            self.client.user_list.clear()
            for server in server_list:
                for client_public_key in server.get("clients", []):
                    self.client.user_list[client_public_key] = server["address"]
        self.client.response_event.set()

    def message(self, msg):
        """
        Processes incoming messages from the server.

        Args:
            msg: The incoming message data.
        """
        processed_msg = process_data(msg)
        if not processed_msg or not processed_msg.get("data"):
            logger.warning("Ignoring message due to error in processing")
            return

        msg_type = processed_msg.get("type")
        if not is_valid_message(processed_msg, msg_type):
            logger.warning(f"Invalid message received of type {msg_type}")
            return

        if msg_type in {"chat", "public_chat", "signed_data"}:
            self.handle_chat(processed_msg)
        else:
            logger.warning(f"Unknown message type received: {msg_type}")

    def handle_chat(self, msg):
        """
        Handles chat messages received from the server.

        Args:
            msg: The chat message data.
        """
        # Extract message ID to prevent duplicates
        msg_id = msg.get("id")
        if msg_id in self.client.processed_message_ids:
            logger.info(f"Duplicate message {msg_id} received. Ignoring.")
            return
        self.client.processed_message_ids.add(msg_id)

        # Validate the integrity of the message's signature
        if not validate_signature(
            msg.get("signature"),
            msg.get("data"),
            msg.get("counter"),
            list(self.client.user_list.keys()),
        ):
            logger.warning(
                "Received a message with an invalid signature, dropping message"
            )
            return

        counter = int(msg.get("counter"))
        msg_type = msg["data"].get("type")

        if msg_type == "public_chat":
            self.handle_public_chat(msg, counter)
        elif msg_type == "chat":
            # Optional: Check if the message is sent by self
            sender_fingerprint = msg["data"].get("sender")
            own_fingerprint = get_fingerprint(get_public_key(self.client.private_key))
            if sender_fingerprint == own_fingerprint:
                logger.info("Received own message back. Skipping processing.")
                return
            self.handle_private_chat(msg, counter)
        else:
            logger.warning(f"Unknown message type received: {msg_type}")

    def handle_public_chat(self, msg, counter):
        """
        Handles public chat messages.

        Args:
            msg: The chat message data.
            counter: The counter value from the message.
        """
        sender_fingerprint = msg["data"]["sender"]
        if not self.check_and_update_counter(sender_fingerprint, counter):
            return

        msg_obj = Msg(
            text=msg["data"]["message"],
            sender=sender_fingerprint,
            participants=["Public"],
        )
        self.client.message_buffer.append(msg_obj)

    def handle_private_chat(self, msg, counter):
        """
        Handles private chat messages received from the server.

        Args:
            msg: The chat message data.
            counter: The counter value from the message.
        """
        data = msg.get("data")
        encrypted_chat = data.get("chat")
        iv = data.get("iv")
        if not encrypted_chat or not iv:
            logger.warning("Invalid chat data or IV")
            return

        chat = None
        for encrypted_symm_key in data.get("symm_keys", []):
            symm_key = decrypt_symm_key(encrypted_symm_key, self.client.private_key)
            if not symm_key:
                continue
            try:
                decrypted_data = decrypt_message(
                    symm_key, encrypted_chat, base64.b64decode(iv.encode("utf-8"))
                )
                if decrypted_data and isinstance(decrypted_data, dict):
                    chat = decrypted_data.get("chat")
                    break
            except Exception as e:
                logger.error(f"Error during decryption: {e}")
                continue

        if not chat:
            logger.warning("Invalid or missing chat segment")
            return

        # Ensure 'participants' and 'message' are present and correctly formatted
        if not isinstance(chat.get("participants"), list) or not isinstance(
            chat.get("message"), str
        ):
            logger.warning("Invalid chat segment structure")
            return

        if not is_valid_message(chat, "chat_segment"):
            logger.warning("Invalid or missing chat segment")
            return

        sender_id = chat["participants"][0]
        if not self.check_and_update_counter(sender_id, counter):
            return

        msg_obj = Msg(
            text=chat["message"],
            sender=sender_id,
            participants=chat["participants"][1:],
        )
        self.client.message_buffer.append(msg_obj)

    def check_and_update_counter(self, sender_id, counter):
        """
        Checks and updates the message counter for a sender.

        Args:
            sender_id: The identifier of the sender (e.g., fingerprint or participant ID).
            counter: The counter value from the message.

        Returns:
            bool: True if the counter is valid and updated, False otherwise.
        """
        sender_prev_counter = self.client.user_counter_map.get(sender_id)
        if sender_prev_counter is not None and counter <= sender_prev_counter:
            logger.warning("Received a message with an invalid or outdated counter")
            return False
        self.client.user_counter_map[sender_id] = counter
        return True
