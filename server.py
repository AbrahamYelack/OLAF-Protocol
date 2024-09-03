from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import json
import base64

from crypto_utils import base64_to_pem, pem_to_base64
from message_utils import is_valid_message, process_data

class Server:

    def __init__(self, host, port):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.nonce_map = {}
        self.user_list = {}
        self.client_list = {}
        self.host = host
        self.port = port

        self.socketio.on_event('connect', self.handle_connect)
        self.socketio.on_event('disconnect', self.handle_disconnect)
        self.socketio.on_event('hello', self.handle_hello)
        self.socketio.on_event('client_list_request', self.handle_client_list_request)
        self.socketio.on_event('message', self.handle_message)

    def run(self):
        self.socketio.run(self.app, self.host, self.port)

    def send(self, data, *rooms):
        for room in rooms:
            self.socketio.send(data, room=room)

    def handle_connect(self):
        sid = request.sid
        join_room('server')
        print(f'Process {sid} connected')

    def handle_disconnect(self):
        sid = request.sid
        print(f'Process {sid} disconnected')

    def handle_hello(self, msg):
        sid = request.sid
        print(f"Hello received from {sid}")

        processed_data = process_data(msg)

        # Move connection to the client room
        leave_room('server')
        join_room('client')

        data = processed_data['data']
        public_key = data['public_key']

        # Add public key to client_list
        self.client_list[sid] = base64_to_pem(public_key)
        emit("hello")

    # When a client makes a client_list_request respond with
    # the latest user_list object
    def handle_client_list_request(self, data):
        sid = request.sid
        print(f"Client list request received from {sid}")
        emit('client_list', self.user_list, room=sid)

    # Generic event listener that decodes the incoming data and 
    # dispatches to the relevant handler to process the message
    def handle_message(self, data):
        
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
            self.handle_chat(data)
        elif msg_type == 'public_chat':
            self.handle_public_chat(data)
        elif msg_type == 'client_update_request':
            self.handle_client_update_request(data)
        elif msg_type == 'client_update':
            self.handle_client_update(data)
        else:
            print("Unknown message type received")

    def handle_chat(self, data):
        sid = request.sid

        # Determine if the message came from a client or another sender
        if sid in self.client_list:
            destination_servers = data['data']['destination_servers']
            for server in destination_servers:
                self.send(data, server)
        else:
            self.send(data, 'client')
    
    def handle_client_update(self, data):
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
                for key in self.client_list.values()
            )

            # If the client isn't in the user_list, add it
            if not client_exists:
                server_address = data.get('address', 'unknown')
                self.user_list[client_pem] = server_address
                print(f"Added new client to user_list with address {server_address}")

        print("User list updated successfully")
    
    def handle_client_update_request(self, data):
        sid = request.sid
        print(f"Client update request recieved from server {sid}")

        client_update_msg = {
            "type": "client_update",
            "clients": [pem_to_base64(self.client_list[sid]) for sid in self.client_list.keys()]
        }
        self.send(client_update_msg, sid)
        print(f"Sent client update to server {sid}")

    def handle_public_chat(self, data):
        sid = request.sid
        
        if sid in self.client_list:
            self.send(data, 'client', 'server')
        else:
            self.send(data, 'client')

if __name__ == '__main__':
    server = Server("localhost", 4678)
    server.run()

