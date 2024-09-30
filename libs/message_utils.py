"""
This file contains common utilities for message creation, parsing, and validation
for use by both the Client and Server implementations of the OLAF-Neighbourhood protocol.
"""

import base64
import json
import hashlib
from crypto_utils import sign_data

# Required fields for each message type
fields = {
    'signed_data': ['type', 'data', 'counter', 'signature'],
    'client_update': ['type', 'clients'],
    'public_chat': ['type', 'sender', 'message'],
    'client_update_request': ['type'],
    'client_list_request': [],
    'client_list': ['server'],
    'chat': ['type', 'destination_servers', 'iv', 'symm_keys', 'chat'],
    'chat_segment': ['participants', 'message'],
    'hello': ['type', 'public_key'],
    'server_hello': ['type', 'sender']
}

def create_signature(msg_data, counter, private_key):
    """
    Creates a base64-encoded SHA-256 signature for the given message data and counter.

    Args:
        msg_data (dict): The message data to be signed.
        counter (str): A counter value to include in the signature.

    Returns:
        str: A base64-encoded signature.
    """
    msg_data_json = json.dumps(msg_data)

    msg_data_counter = str(msg_data_json + counter).encode('utf-8')

    signature = sign_data(private_key, msg_data_counter.encode('utf-8'))
    base64_signature = base64.b64encode(signature)

    return base64_signature.decode('utf-8')

def validate_signature(signature, data, counter, *public_keys):
    is_valid = False
    for public_key in public_keys:
        is_valid = signature == create_signature(data, counter, public_key)
        if is_valid:
            break
    return is_valid

def make_signed_data_msg(msg_data, counter, private_key):
    """
    Creates a signed data message in JSON format.

    Args:
        msg_data (dict): The data to include in the message.
        counter (str): A counter value to include in the message.

    Returns:
        str: A JSON-formatted signed data message.
    """
    signature = create_signature(msg_data, counter, private_key)
    msg = {
        'type': 'signed_data',
        'data': msg_data,
        'counter': counter,
        'signature': signature
    }
    return json.dumps(msg)

def is_valid_message(msg, msg_type):
    """
    Validates a message based on its type and required fields.

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
