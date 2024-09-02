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


def handle_client_update(data):
    print("Received client update from another server")

    # Extract list of clients from the incoming data
    updated_clients = data.get('clients', [])

    # Go through each updated client and update the user_list
    for client_pem in updated_clients:
        # Convert the base64 encoded client key back to PEM format
        client_key = base64_to_pem(client_pem)

        # Check if the client is already in the user_list
        client_exists = any(
            client_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ) == key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            for key in client_list.values()
        )

        # If the client isn't in the user_list, add it
        if not client_exists:
            # Assuming that the update contains the correct server address
            server_address = data.get('address', 'unknown')
            user_list[client_pem] = server_address
            print(f"Added new client to user_list with address {server_address}")

    print("User list updated successfully")

# Utility function to convert base64 to pem
def base64_to_pem(base64_key):
    return serialization.load_pem_public_key(
        base64.b64decode(base64_key.encode('utf-8')),
        backend=default_backend()
    )


def handle_public_chat(data):
    # Get the session ID of the sender
    sid = request.sid

    # Detirmine if the message came from a client or another server
    if sid in client_list:
        # Message came from a client
        handle_public_chat(data, sid)

    else:
        # Message came from another server
        handle_chat_from_server(data)

# Handle public chat from client
def handle_public_chat_from_client(data, sid):
    # Validate message format
    if not validate_public_chat_message(data):
        print(f"Invalid public chat message recieved from client {sid}")
        return
    
    # Forward the message to all connected servers
    forward_message_to_all_servers(data)

    # Forward the message to all connected clients
    forward_message_to_all_clients(data)
    print(f"Public chat message from client {sid} forwarded to all servers and clients")

# Handle public chat from server
def handle_public_chat_from_server(data):
    # Validate the message format
    if not validate_public_chat_message(data):
        print("Invalid public chat message received from server")
        return

    # Forward the message to all connected clients
    forward_message_to_all_clients(data)
    print("Public chat message from server forwarded to all clients")

# Validate public chat message
def validate_public_chat_message(data):
    required_fields = ['type', 'sender', 'message']
    for field in required_fields:
        if field not in data['data']:
            return False
        
        # Can add more checks if needed
        return True

# Forward message to all servers
def forward_message_to_all_servers(data):
    for server in user_list['servers']:
        send_to_server(server, data)

# Forward message to all clients
def forward_message_to_all_clients(data):
    for client_sid in client_list.keys():
        socketio.emit('public_chat', data, room=client_sid)



# Send to server function 
# (i dont know if this is right, i noticed we dont have this but needed this function for the previous handler)
def send_to_server(server_info, data):
    try:
        # Construct the server's URL
        server_url = f"http://{server_info['address']}:{server_info.get('port', 80)}/api/receive_message"

        # Send the data as a POST request
        response = requests.post(server_url, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            print(f"Successfully sent data to server {server_info['address']}")
        else:
            print(f"Failed to send data to server {server_info['address']} - Status Code: {response.status_code}")

    except Exception as e:
        print(f"Error sending data to server {server_info['address']}: {e}")



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

