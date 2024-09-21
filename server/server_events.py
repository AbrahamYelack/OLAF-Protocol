"""
Module for managing server and client events in a Flask-SocketIO application.

This module defines the ServerEvent and ClientEvent classes, which handle
connections, disconnections, and message processing for clients and servers
communicating within a networked environment.
"""
import json
from socketio.exceptions import ConnectionError as ConnectionErrorSocketIO, SocketIOError
from flask import request
from flask_socketio import emit, join_room
from message_utils import is_valid_message, process_data
from crypto_utils import base64_to_pem, pem_to_base64

class ServerEvent:
    """Handles server events for managing connections and messaging."""

    def __init__(self, server):
        """Initialize the ServerEvent with the server instance.

        Args:
            server: The server instance managing the connections.
        """
        self.server = server

    def connect(self):
        """Handle a new connection from a client or server."""
        sid = request.sid
        print(f'Process {sid} connected')

    def disconnect(self):
        """Handle disconnection of a client or server."""
        sid = request.sid
        if self.server.server_map.get(sid):
            ip_address = self.server.server_map[sid]
            print(f'Server {ip_address} disconnected')
            self.server.connected_servers.pop(ip_address, None)
            self.server.server_map.pop(sid, None)
        elif sid in self.server.client_list:
            print(f'Client {sid} disconnected')
            self.server.client_list.pop(sid, None)
        else: print(f'Unknown process {sid} disconnected')

    def hello(self, msg):
        """Handle the hello message from a client.

        Args:
            msg: The message received from the client.
        """
        sid = request.sid
        print(f"Client hello received from {sid}")

        processed_data = process_data(msg)

        if not (is_valid_message(processed_data, 'signed_data') and
                is_valid_message(processed_data.get('data', {}), 'hello')):
            print("Invalid hello message received from client, dropping message")
            return

        join_room('client')
        data = processed_data['data']
        public_key = data['public_key']
        self.server.client_list[sid] = base64_to_pem(public_key)
        emit("hello")

    def client_list_request(self, data):
        """Handle a request for the client list.

        Args:
            data: The data received with the request.
        """
        sid = request.sid
        print(f"Client list request received from {sid}")

        processed_data = process_data(data)

        if not is_valid_message(processed_data, 'client_list_request'):
            print("Invalid client_list_request received from client, dropping message")
            return

        if sid not in self.server.client_list:
            print("A client_list_request was received from an unknown connection, dropping message")
            return

        server_clients = {}
        for client_pem, ip_address in self.server.user_list.items():
            server_clients.setdefault(ip_address, []).append(client_pem)

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

        client_list_json = json.dumps(client_list)
        emit('client_list', client_list_json, room=sid)

    def message(self, msg):
        """Handle an incoming message.

        Args:
            msg: The message received from a client or server.
        """
        print("A message has been received")
        processed_msg = process_data(msg)

        if not is_valid_message(processed_msg, processed_msg['type']):
            print(f"Invalid message received of type {processed_msg['type']}")
            return

        data = processed_msg['data']
        msg_type = data.get('type')

        if not is_valid_message(data, msg_type):
            print(f"Invalid message received of type {msg_type}")
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
        """Handle a chat message.

        Args:
            data: The data of the chat message.
        """
        sid = request.sid
        if sid in self.server.client_list:
            print(f"Received chat message from client: {sid}")
            destination_servers = data['data']['destination_servers']
            for server in destination_servers:
                self.server.send(data, "Server", server)
        elif sid in self.server.server_list:
            print(f"Received chat message from server: {sid}")
            self.server.send(data, "Client", 'client')
        else:
            print("Chat message received from unknown connection, dropping message")

    def client_update(self, data):
        """Handle a client update message.

        Args:
            data: The data containing updated clients.
        """
        sid = request.sid
        if sid not in self.server.server_list:
            print("Received client update from an unknown server, dropping message")
            return
        ip_address = self.server.server_list[sid]
        print(f"Received client update from server: {ip_address}")

        updated_clients = data.get('clients', [])

        filtered_users = {
            key: val for key, val in self.server.user_list.items() if val != ip_address
        }
        self.server.user_list = filtered_users

        for client_pem in updated_clients:
            self.server.user_list[client_pem] = ip_address

        print("User list updated successfully")

    def client_update_request(self, data):
        """Handle a request for client updates.

        Args:
            data: The data received with the request.
        """
        sid = request.sid

        data = process_data(data)
        if not is_valid_message(data, 'client_update_request'):
            print("Received invalid client update message, dropping message")
        if sid not in self.server.server_list:
            print("Received client update from an unknown server, dropping message")
            return
        ip_address = self.server.server_list[sid]
        print(f"Client update request received from server {ip_address}")

        clients = [pem_to_base64(self.server.client_list[sid]) for sid in self.server.client_list]
        client_update_msg = {
            "type": "client_update",
            "clients": clients
        }

        client_update_msg_json = json.dumps(client_update_msg)
        self.server.send(client_update_msg_json, "Server", ip_address)
        print(f"Sent client update to server {ip_address}")

    def public_chat(self, data):
        """Handle a public chat message.

        Args:
            data: The data of the public chat message.
        """
        sid = request.sid
        if sid in self.server.client_list:
            print(f"Received public_chat message from client {sid}, forwarding to all neighbours")
            for server in self.server.connected_servers.keys():
                self.server.send(data, 'Server', server)
        elif sid in self.server.server_list:
            server_name = self.server.server_list[sid]
            print(f"Received public_chat message from server {server_name}, "
                "forwarding to all clients")
            self.server.send(data, 'Client', 'client')
        else:
            print("Received public_chat message from an unknown connection, dropping message")

    def server_hello(self, data):
        """Handle a hello message from a server.

        Args:
            data: The data containing the sender's information.
        """
        sid = request.sid
        print(f"Server hello received from {sid}")

        join_room('server')

        server_ip = data["sender"]

        client_socket = self.server.create_client_socket()
        try:
            print(f'Attempting to connect to {server_ip}')
            client_socket.connect(server_ip)
            self.server.connected_servers[server_ip] = client_socket
            self.server.server_map[sid] = server_ip
        except (ConnectionErrorSocketIO, SocketIOError) as e:
            print(f'Error ocurred trying to connect to neighbour after server hello: {e}')

class ClientEvent:
    """Handles client events for managing connections to neighbor servers."""

    def __init__(self, client):
        """Initialize the ClientEvent with the client instance.

        Args:
            client: The client instance managing the connection.
        """
        self.client = client

    def connect(self, sid):
        """Handle a new connection to a neighbor server."""
        socket = self.client.eio.transport().socket
        server_ip, server_port = socket.getpeername()
        print(f'Successfully connected to neighbour server {sid}: {server_ip}:{server_port}')

    def disconnect(self, sid):
        """Handle disconnection from a neighbor server."""
        print(f'Disconnected from neighbour server {sid}')
