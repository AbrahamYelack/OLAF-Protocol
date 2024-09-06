import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from flask import request
from flask_socketio import emit, join_room, leave_room
from message_utils import is_valid_message, process_data
from crypto_utils import base64_to_pem, pem_to_base64
from cryptography.hazmat.primitives import serialization

class Event:
    def __init__(self, server):
        self.server = server

    def connect(self):
        sid = request.sid
        join_room('server')
        print(f'Process {sid} connected')

    def disconnect(self):
        sid = request.sid
        print(f'Process {sid} disconnected')

    def hello(self, msg):
        sid = request.sid
        print(f"Hello received from {sid}")

        processed_data = process_data(msg)

        # Move connection to the client room
        leave_room('server')
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
    def message(self, data):
        
        data = process_data(data).get('data')
        msg_type = None

        if(data):
            msg_type = data.get('type')
        else:
            print("Ignoring message due to error")
            return
        
        if not is_valid_message(data, msg_type):
            print(f"Invalid message recieved of type {msg_type}")
            return

        if msg_type == 'chat':
            self.server.handle_chat(data)
        elif msg_type == 'public_chat':
            self.server.handle_public_chat(data)
        elif msg_type == 'client_update_request':
            self.server.handle_client_update_request(data)
        elif msg_type == 'client_update':
            self.server.handle_client_update(data)
        else:
            print("Unknown message type received")

    def chat(self, data):
        sid = request.sid

        # Determine if the message came from a client or another sender
        if sid in self.server.client_list:
            destination_servers = data['data']['destination_servers']
            for server in destination_servers:
                self.server.send(data, server)
        else:
            self.server.send(data, 'client')
    
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
        
        if sid in self.server.client_list:
            self.server.send(data, 'client', 'server')
        else:
            self.server.send(data, 'client')