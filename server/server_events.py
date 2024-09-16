import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from flask import request
from flask_socketio import emit, join_room, leave_room
from message_utils import is_valid_message, process_data
from crypto_utils import base64_to_pem, pem_to_base64
from cryptography.hazmat.primitives import serialization

class ServerEvent:
    def __init__(self, server):
        self.server = server

    def connect(self):
        sid = request.sid
        print(f'Process {sid} connected')

    def disconnect(self):
        sid = request.sid
        print(f'Process {sid} disconnected')

    def hello(self, msg):
        sid = request.sid
        print(f"Hello received from {sid}")

        processed_data = process_data(msg)

        # Move connection to the client room
        join_room('client')

        data = processed_data['data']
        public_key = data['public_key']

        # Add public key to client_list
        self.server.client_list[sid] = base64_to_pem(public_key)
        emit("hello")

    # When a client makes a client_list_request respond with
    # the latest user_list object
    def client_list_request(self, data):
        sid = request.sid
        print(f"Client list request received from {sid}")
        emit('client_list', self.server.user_list, room=sid)

    # Generic event listener that decodes the incoming data and 
    # dispatches to the relevant handler to process the message
    def message(self, msg):
        
        print("A message has been received")
        processed_msg = process_data(msg)

        if not is_valid_message(processed_msg, processed_msg['type']):
            print(f"Invalid message recieved of type {processed_msg['type']}")
            return

        data = processed_msg['data']
        msg_type = None

        if(data):
            msg_type = data.get('type')
        else:
            print("Ignoring message due to error")
            return

        print(data)
        
        if not is_valid_message(data, msg_type):
            print(f"Invalid message recieved of type {msg_type}")
            return

        if msg_type == 'chat':
            self.chat(data)
        elif msg_type == 'public_chat':
            self.public_chat(data)
        elif msg_type == 'client_update_request':
            self.client_update_request(data)
        elif msg_type == 'client_update':
            self.client_update(data)
        elif msg_type == 'server_hello':
            self.server_hello(data)
        else:
            print("Unknown message type received")

    def chat(self, data):
        sid = request.sid
        # Determine if the message came from a client or another server
        if sid in self.server.client_list:
            print("Received chat message from client: {sid}")
            destination_servers = data['data']['destination_servers']
            for server in destination_servers:
                self.server.send(data, "Server", server)
        else:
            print("Received chat message from server: {sid}")
            self.server.send(data, "Client", 'client')
    
    def client_update(self, data):
        print("Received client update from another server")

        updated_clients = data.get('clients', [])

        # Go through each updated client and update the user_list
        for client_pem in updated_clients:

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
                for key in self.server.client_list.values()
            )

            # If the client isn't in the user_list, add it
            if not client_exists:
                server_address = data.get('address', 'unknown')
                self.server.user_list[client_pem] = server_address
                print(f"Added new client to user_list with address {server_address}")

        print("User list updated successfully")
    
    def client_update_request(self, data):
        sid = request.sid
        print(f"Client update request recieved from server {sid}")

        client_update_msg = {
            "type": "client_update",
            "clients": [pem_to_base64(self.server.client_list[sid]) for sid in self.server.client_list.keys()]
        }
        self.server.send(client_update_msg, sid)
        print(f"Sent client update to server {sid}")

    def public_chat(self, data):
        sid = request.sid
        
        # If from client, forward to all connected servers
        if sid in self.server.client_list:
            self.server.send(data, 'Server', list(self.server.connected_servers.keys()))
        # If from server, forward to all clients
        else:
            self.server.send(data, 'Client', 'client')
    
    def server_hello(self, data):
        sid = request.sid
        print(f"Server hello received from {sid}")

        # Move connection to the server room
        join_room('server')
        server_ip = data["sender"]
        client_socket = self.server.create_client_socket()
        try:
            print(f'Attempting to connect to {server_ip}')
            client_socket.connect(server_ip)
            self.server.connected_servers[server_ip] = client_socket
        except Exception as e:
            print(f'Unexpected error during connection: {e}')

# This class was specifically created to handle the events that occur on the 
# client sockets that belong to the server. These client sockets are managed by the
# server and used to connect to and communicate to other servers in the neighbourhood
class ClientEvent:
    def __init__(self, client):
        self.client = client

    def connect(self):
        socket = self.client.eio.transport().socket
        self.server_ip, self.server_port = socket.getpeername()
        print(f'Successfully connected to neighbour server: {self.server_ip}:{self.server_port}')

    def disconnect(self):
        print(f'Disconnected from neighbour server: {self.server_ip}:{self.server_port}')
