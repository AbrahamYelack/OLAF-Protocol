import base64
import json
import hashlib

sha256_hash = hashlib.sha256()

fields = {
    'signed_data': ['type', 'data', 'counter', 'signature'],
    'client_update': ['type', 'clients'],
    'client_update_request': ['type'],
    'client_list_request' : [],
    'client_list': ['server'],
    'chat': ['participants', 'message']
}

def create_signature(msg_data, counter):
    # Convert dictionary to JSON and from JSON to bytes
    msg_data_json = json.dumps(msg_data)
    msg_data_json_bytes = msg_data_json.encode('utf-8')
    
    # Encode raw bytes into base64
    msg_data_json_base64 = base64.b64encode(msg_data_json_bytes)
    # Encode counter into base64
    counter_base64 = base64.b64encode(counter.encode('utf-8'))
    
    # Hash the concatenation of the base64 message data and counter
    sha256_hash.update(msg_data_json_base64 + counter_base64)
    binary_signature = sha256_hash.digest()

    # Encode the binary hash as base64
    base64_signature = base64.b64encode(binary_signature)
    # Convert the base64 encoding to a string to include in the message
    base64_signature = base64_signature.decode('utf-8')
    return base64_signature

def make_signed_data_msg(msg_data, counter):

    signature = create_signature(msg_data, counter)

    # Create message
    msg = {
        'type': 'signed_data',
        'data': msg_data,
        'counter': counter,
        'signature': signature
    }

    # Return JSON formatted message
    return json.dumps(msg)

def is_valid_message(msg, msg_type):
    required_fields = fields[msg_type]
    for field in required_fields:
        if field not in msg:
            return False

    signature = create_signature(msg['data'], msg['counter'])
    if(signature != msg['signature']):
        return False
    return True

# Utility to parse and convert raw message data
def process_data(data):
    if isinstance(data, str):
        return json.loads(data)
    elif isinstance(data, dict):
        return data
    else:
        print("Unknown data type received")