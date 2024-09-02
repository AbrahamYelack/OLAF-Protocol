from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import json
import base64

from crypto_utils import base64_to_pem

app = Flask(__name__)
socketio = SocketIO(app)

# Mapping of connections to most recent nonce
nonce_map = {}

# Dictionary to maintain information on all servers in the neighbourhood
# and the clients that they host
# This would eventually be updated via server to server communication before
# a client can request the information, so I have put placeholder data for the
# meantime
user_list = { 
    'servers': [
        {
        'address': '1',
        'clients': ['usr1', 'usr2', 'usr3']
        },
        {
        'address': '2',
        'clients': ['usr4', 'usr5', 'usr6']
        }
    ]
}

# Clietns serviced by this server
client_list = {}

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    join_room('server')
    print(f'Process {sid} connected')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f'Process {sid} disconnected')

@socketio.on('hello')
def handle_hello(msg):
    sid = request.sid
    print(f"Hello received from {sid}")

    processed_data = process_data(msg)

    # Move connection to the client room
    leave_room('server')
    join_room('client')

    data = processed_data['data']
    public_key = data['public_key']

    # Add public key to client_list
    client_list[sid] = base64_to_pem(public_key)
    emit("hello")

# When a client makes a client_list_request respond with
# the latest user_list object
@socketio.on('client_list_request')
def handle_client_list_request(data):
    sid = request.sid
    print(f"Client list request received from {sid}")
    emit('client_list', user_list, room=sid)

# Generic event listener that decodes the incoming data and 
# dispatches to the relevant handler to process the message
@socketio.on('message')
def handle_message(data):
    
    # Check the type of the message and forward to handler
    processed_data = process_data(data)
    msg_type = None

    if(processed_data):
        msg_type = processed_data.get('data').get('type')
    else:
        print("Ignoring message due to error")
        return

    # if msg_type is 'chat':
    #     handle_chat(data)
    # elif msg_type is 'public_chat':
    #     handle_public_chat(data)
    # elif msg_type is 'client_update_request':
    #     handle_client_update_request(data)
    # elif msg_type is 'client_update':
    #     handle_client_update(data)
    # else:
    #     print("Unknown message type received")


# Determine source of message
def handle_chat(data):
    # Get the session ID of the sender
    sid = request.sid

    # Determine if the message came from a client or another sender
    if sid in client_list:
        # Message came from a client
        handle_chat_from_client(data, sid)

    else:
        # Message came from another sender
        handle_chat_from_server(data)

# Handle messages from clients
def handle_chat_from_client(data, sid):
    # Validate the message format, ensure all necessary fields are present
    if not validate_chat_message(data):
        print(f"Invalid chat message recieved from client {sid}")
        return
    
    # Extract the list of destination servers
    destination_servers = data['data']['destination_servers']

    # Forward the message to each destination server
    for server in destination_servers:
        forward_message_to_server(data, server)

# Handle messages from other servers
def handle_chat_from_server(data):
    # Validate message format, ensure necessary fields are present
    if not validate_chat_message(data):
        print("Invalid chat message recieved from server")
        return
    # Forward the message to all connected clients
    forward_message_to_all_clients(data)

# Validate chat message, function checks that the chat message contains all necessary fields
def validate_chat_message(data):
    required_fields = ['type', 'data', 'counter', 'signature']
    for field in required_fields:
        if field not in data:
            return False
        
        # Additional checks could be added here if needed later
        return True
    
# Forward message to server    
def forward_message_to_server(data, server_address):
    # Assuming there is anotehr function somewhere to send data to another server
    send_to_server(server_address, data)

# Forward message to all clients
def forward_message_to_all_clients(data):
    for client_sid in client_list.keys():
        socketio.emit('chat', data, room=client_sid)


def handle_client_update_request(data):
    # Get the session ID of the requesting server
    sid = request.sid
    print(f"Client update request recieved from server {sid}")

    # Prepare the client_update message
    client_update_msg = {
        "type": "client_update",
        "clients": [pem_to_base64_key(client_list[sid]) for sid in client_list.keys()]
    }

    # Send the client_update message back to the requesting server
    socketio.emit('client_update', client_update_msg, room=sid)
    print(f"Sent client update to server {sid}")

# pem_to_base64_key utility function
def pem_to_base64_key(pem_key):
    return base64.b64encode(pem_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )).decode('utf-8')


# def handle_client_update(data):
    # These messages are received from connected servers when
    # changes have occured to their client list. Or in response
    # to a 'client_update_request'

    # This method should update the user_list object in 
    # accordance with the data

# def handle_public_chat(data):
    # Must determine whether this message came from a client
    # or server
    # 
    # From client: 
    # - Validate format of message
    # - Forward to ALL connected servers and clients
    # 
    # From server:
    # - Validate format of message
    # - Forward to all connected clients

# Utility to parse raw data and cas UTF-8 JSON
def process_data(data):
    if isinstance(data, str):
        return json.loads(data)
    elif isinstance(data, dict):
        return data
    else:
        print("Unknown data type received")

if __name__ == '__main__':
    socketio.run(app, host="localhost", port=4678)

