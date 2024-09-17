import sys
import os
import json

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
        # If the connection was a server, cleanup server_map and connected_servers
        if self.server.server_map.get(sid):
            ip_address = self.server.server_map[sid]
            print(f'Server {ip_address} disconnected')
            if self.server.connected_servers.get(ip_address):
                del self.server.connected_servers.get[ip_address]
            del self.server.server_map[sid]
        # If the connected was a client, cleanup the client list
        elif self.server.client_list.get(sid):
            print(f'Client {sid} disconnected')
            del self.server.client_list[sid]
        # Any other connection was not yet identified as a server nor client, hence
        # no cleanup is required
        else: 
            print(f'Unknown process {sid} disconnected')

    def hello(self, msg):
        sid = request.sid
        print(f"Client hello received from {sid}")

        processed_data = process_data(msg)

        if not is_valid_message(processed_data, 'signed_data' 
            or not is_valid_message(processed_data['data'], 'hello')):
            print("Invalid hello message received from client, dropping message")

        # Move connection to the client room
        join_room('client')

        # Extract the public key
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

        processed_data = process_data(data)

        if not is_valid_message(processed_data, 'client_list_request'):
            print("Invalid client_list_request message received from client, dropping message")

        # Initialize a dictionary to organize clients by server address
        server_clients = {}

        # Group clients by their server (IP address)
        for client_pem, ip_address in self.server.user_list.items():
            if ip_address not in server_clients:
                server_clients[ip_address] = []
            server_clients[ip_address].append(client_pem)

        # Create the final JSON structure
        client_list = {
            "type": "client_list",
            "servers": [
                {
                    "address": server,
                    "clients": clients
                }
                for server, clients in server_clients.items()
            ]
        }

        # Convert to JSON string
        client_list = json.dumps(client_list)

        emit('client_list', client_list, room=sid)

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
            print("Unknown message type received, dropping message")

    def chat(self, data):
        sid = request.sid
        # Determine if the message came from a client or another server
        if sid in self.server.client_list:
            print("Received chat message from client: {sid}")
            destination_servers = data['data']['destination_servers']
            for server in destination_servers:
                self.server.send(data, "Server", server)
        elif sid in self.server.server_list:
            print("Received chat message from server: {sid}")
            self.server.send(data, "Client", 'client')
        else:
            print("Chat message received from unknown connection, dropping message")
    
    def client_update(self, data):
        sid = request.sid
        if not self.server.server_list.get(sid):
            print("Received client update from an unknown server, dropping message")
            return
        ip_address = self.server.server_list.get(sid)
        print(f"Received client update from server: {ip_address}")

        updated_clients = data.get('clients', [])

        # Remove all previous entries in the user_list belonging to this server
        self.server.user_list = {key: val for key, val in self.server.user_list.items() if val != ip_address}

        # Go through each updated client and update the user_list
        for client_pem in updated_clients:
            self.server.user_list[client_pem] = ip_address

        print("User list updated successfully")
    
    def client_update_request(self, data):
        sid = request.sid
        if not self.server.server_list.get(sid):
            print("Received client update from an unknown server, dropping message")
            return
        ip_address = self.server.server_list.get(sid)
        print(f"Client update request recieved from server {ip_address}")

        client_update_msg = {
            "type": "client_update",
            "clients": [pem_to_base64(self.server.client_list[sid]) for sid in self.server.client_list.keys()]
        }
        client_update_msg = json.dumps(client_update_msg)
        self.server.send(client_update_msg, "Server", ip_address)
        print(f"Sent client update to server {ip_address}")

    def public_chat(self, data):
        sid = request.sid
        
        # If from client, forward to all connected servers
        if sid in self.server.client_list:
            print(f"Received public_chat message from client {sid}, forwarding to all neighbours")
            for server in list(self.server.connected_servers.keys()):
                self.server.send(data, 'Server', server)
        # If from server, forward to all clients
        elif sid in self.server.server_list:
            print(f"Received public_chat message from server {self.server.server_list.get(sid)}, forwarding to all clients")
            self.server.send(data, 'Client', 'client')
        else:
            print("Received public_chat message from an unknown connection, dropping message")

    
    def server_hello(self, data):
        sid = request.sid
        print(f"Server hello received from {sid}")

        # Move connection to the server room
        join_room('server')

        # Get the IP of the server from the message
        server_ip = data["sender"]

        # Attempt to connect to the server via a client socket
        client_socket = self.server.create_client_socket()
        try:
            print(f'Attempting to connect to {server_ip}')
            client_socket.connect(server_ip)
            # Store the socket
            self.server.connected_servers[server_ip] = client_socket
            # Map the connection to the server's IP
            self.server.server_map[sid] = server_ip
        except Exception as e:
            print(f'Unexpected error during connection after receiving server_hello: {e}')

# This class was specifically created to handle the events that occur on the 
# client sockets that belong to the server. These client sockets are managed by the
# server and used to connect to and communicate to other servers in the neighbourhood.
class ClientEvent:
    def __init__(self, client):
        self.client = client

    def connect(self):
        socket = self.client.eio.transport().socket
        self.server_ip, self.server_port = socket.getpeername()
        print(f'Successfully connected to neighbour server: {self.server_ip}:{self.server_port}')

    def disconnect(self):
        print(f'Disconnected from neighbour server: {self.server_ip}:{self.server_port}')
