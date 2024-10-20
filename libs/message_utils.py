"""
This file contains common utilities for message creation, parsing, and validation
for use by both the Client and Server implementations of the OLAF-Neighbourhood protocol.

Some functions are intended to handle message integrity checks, 
while others focus on message formatting for transmission.
"""

import base64
import json
import hashlib
from crypto_utils import sign_data
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from crypto_utils import base64_to_pem

import uuid  # Added import for generating unique message IDs

# Required fields for each message type
fields = {
    "signed_data": ["type", "id", "data", "counter", "signature"],  # Added 'id'
    "client_update": ["type", "clients"],
    "public_chat": ["type", "sender", "message"],
    "client_update_request": ["type"],
    "client_list_request": [],
    "client_list": ["server"],
    "chat": ["type", "destination_servers", "iv", "symm_keys", "chat"],
    "chat_segment": ["participants", "message"],
    "hello": ["type", "public_key"],
    "server_hello": ["type", "sender"],
}


def create_signature(msg_data, counter, private_key):
    """
    Creates a base64-encoded SHA-256 signature for the given message data and counter.

    This function ensures that the messages sent have verifiable integrity
    and haven't been tampered with during transmission.

    Args:
        msg_data (dict): The message data to be signed.
        counter (str): A counter value to include in the signature.
        private_key: The RSA private key object.

    Returns:
        str: A base64-encoded signature.
    """
    msg_data_json = json.dumps(msg_data)

    # Concatenate the message data and counter for signing
    msg_data_counter = msg_data_json + counter

    # Generate the signature using the private key
    signature = sign_data(private_key, msg_data_counter.encode("utf-8"))
    base64_signature = base64.b64encode(signature)

    return base64_signature.decode("utf-8")


def validate_signature(signature, data, counter, public_keys):
    """
    Validates the provided RSA-PSS signature using the given public keys.

    Ensures that messages received have valid signatures, preventing unauthorized modification.

    Args:
        signature: The RSA-PSS signature to be verified.
        data: The original data that was signed.
        counter: A counter or nonce used as part of the data.
        public_keys: The public keys to use for verification.

    Returns:
        bool: True if the signature is valid with any of the public keys, False otherwise.
    """
    # Convert msg_data to a JSON string and concatenate with the counter
    msg_data_json = json.dumps(data)
    msg_data_counter = (msg_data_json + counter).encode("utf-8")  # Encode to bytes

    # Decode the base64-encoded signature to bytes
    signature_bytes = base64.b64decode(signature)

    # Iterate over each public key and try to verify the signature
    for public_key_pem in public_keys:
        try:
            # Convert the base64-encoded public key to PEM format and load it
            public_key = base64_to_pem(public_key_pem)

            # Verify the RSA-PSS signature using the public key
            public_key.verify(
                signature_bytes,  # Signature should be in bytes
                msg_data_counter,  # Data should also be in bytes
                padding.PSS(
                    mgf=padding.MGF1(
                        hashes.SHA256()
                    ),  # Mask generation function (MGF1 with SHA-256)
                    salt_length=padding.PSS.MAX_LENGTH,  # Use PSS.MAX_LENGTH to match the signing process
                ),
                hashes.SHA256(),  # SHA-256 digest algorithm
            )
            # If no exception is raised, the signature is valid
            return True
        except InvalidSignature:
            # If the signature is invalid for this public key, continue to the next one
            continue

    # If none of the public keys validate the signature, return False
    return False


def make_signed_data_msg(msg_data, counter, private_key):
    """
    Creates a signed data message in JSON format with a unique ID.

    This method ensures that each message sent is digitally signed and
    includes a counter to prevent replay attacks.

    Args:
        msg_data (dict): The data to include in the message.
        counter (str): A counter value to include in the message.
        private_key: The client's private key object.

    Returns:
        str: A JSON-formatted signed data message.
    """
    signature = create_signature(msg_data, counter, private_key)
    msg_id = str(uuid.uuid4())  # Generate a unique message ID
    msg = {
        "type": "signed_data",
        "id": msg_id,  # Add the unique ID
        "data": msg_data,
        "counter": counter,
        "signature": signature,
    }
    return json.dumps(msg)


def is_valid_message(msg, msg_type):
    """
    Validates a message based on its type and required fields.

    Ensures that each message adheres to the expected format and contains
    all necessary fields.

    Args:
        msg (dict): The message to validate.
        msg_type (str): The type of the message.

    Returns:
        bool: True if the message is valid, False otherwise.
    """

    required_fields = fields[msg_type]
    for field in required_fields:
        if field not in msg:
            return False

    return True


def process_data(data):
    """
    Parses and converts raw message data into a dictionary format.

    Ensures that the message data is in a usable format by converting it
    into a Python dictionary for easier processing.

    Args:
        data (str or dict): The raw message data to process.

    Returns:
        dict: The processed message data as a dictionary.
    """
    if isinstance(data, str):
        return json.loads(data)
    elif isinstance(data, dict):
        return data
    else:
        print("Unknown data type received")
