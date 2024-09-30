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
from message_utils import is_valid_message, process_data, make_signed_data_msg
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

        if sid in self.server.server_map:
            ip_address = self.server.server_map[sid]
            print(f'Server {ip_address} disconnected')
            self.server.connected_servers.pop(ip_address, None)
            self.server.server_map.pop(sid, None)
        elif sid in self.server.client_list:
            print(f'Client {sid} disconnected')
            self.server.client_list.pop(sid, None)
            self.client_update_notification()
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
            print("Invalid client hello message received, dropping message")
            return

        join_room('client')

        data = processed_data['data']
        public_key = data['public_key']

        # Add this client to the servers local list
        self.server.client_list[sid] = base64_to_pem(public_key)

        # Add this client to the global users list
        client_pub_key = pem_to_base64(self.server.client_list[sid])
        self.server.user_list[client_pub_key] = f"{self.server.host}:{self.server.port}"

        # Reply to the client
        emit("hello")

        self.client_update_notification()

    def client_update_notification(self):
        """Notify conencted servers of an update to the client list."""
        # An update has occured to the client list, so we notify other servers
        client_list = [pem_to_base64(self.server.client_list[sid]) for sid in list(self.server.client_list.keys())]
        client_update = {
            "type": "client_update",
            "clients": client_list
        }
        client_update_json = json.dumps(client_update)
        for ip_address in list(self.server.connected_servers.keys()):
            socket = self.server.connected_servers[ip_address]
            socket.send(client_update_json)

        print("Sent client update to all servers")
        print("Notifying client regarding the update")

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
        emit('client_list', client_list_json, room='client')

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

        msg_type = None
        if(processed_msg['type'] == 'signed_data'):
            data = processed_msg['data']
            msg_type = data['type']
            if not is_valid_message(data, msg_type):
                print(f"Invalid message received of type {msg_type}")
                return
        else:
            msg_type = processed_msg['type']

        if msg_type == 'chat':
            self.chat(processed_msg)
        elif msg_type == 'public_chat':
            self.public_chat(processed_msg)
        elif msg_type == 'client_update_request':
            self.client_update_request(processed_msg)
        elif msg_type == 'client_update':
            self.client_update(processed_msg)
        elif msg_type == 'server_hello':
            self.server_hello(processed_msg)
        else:
            print("Unknown message type received, dropping message")

    def chat(self, msg):
        """Handle a chat message.

        Args:
            data: The data of the chat message.
        """
        data = msg['data']
        sid = request.sid
        if sid in self.server.client_list:
            print(f"Received chat message from client: {sid}")
            destination_servers = data['destination_servers']
            print(destination_servers)
            for server_ip in destination_servers:
                socket = self.server.connected_servers[server_ip]
                socket.send(msg)
        elif sid in self.server.server_map:
            print(f"Received chat message from server: {sid}")
            self.server.send(msg, "Client", 'client')
        else:
            print("Chat message received from unknown connection, dropping message")

    def client_update(self, msg):
        """Handle a client update message.

        Args:
            data: The data containing updated clients.
        """
        sid = request.sid
        if sid not in self.server.server_map:
            print("Received client update from an unknown server, dropping message")
            return
        
        ip_address = self.server.server_map[sid]
        print(f"Received client update from server: {ip_address}")

        updated_clients = msg.get('clients', [])

        filtered_users = {
            key: val for key, val in self.server.user_list.items() if val != ip_address
        }
        self.server.user_list = filtered_users

        for client_pem in updated_clients:
            self.server.user_list[client_pem] = ip_address
        
        print("Client update successfully processed")
        print("Notifying clients")

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
        emit('client_list', client_list_json, room='client')

        print(f"New User List: {self.server.user_list}")

    def client_update_request(self, data):
        """Handle a request for client updates.

        Args:
            data: The data received with the request.
        """
        sid = request.sid

        data = process_data(data)
        if not is_valid_message(data, 'client_update_request'):
            print("Received invalid client update message, dropping message")

        # Check if requester is a valid server
        if sid not in self.server.server_map:
            print("Received client update request from an unknown server, dropping message")
            return

        ip_address = self.server.server_map[sid]
        print(f"Client update request received from server: {ip_address}")

        # Create and send the client_update message
        clients = [pem_to_base64(self.server.client_list[sid]) for sid in self.server.client_list]
        client_update = {
            "type": "client_update",
            "clients": clients
        }
        client_update_json = json.dumps(client_update)

        socket = self.server.connected_servers[ip_address]
        socket.send(client_update_json)
        print(f"Sent client update to server {ip_address}")

    def public_chat(self, msg):
        """Handle a public chat message.

        Args:
            data: The data of the public chat message.
        """
        sid = request.sid
        if sid in self.server.client_list:
            print(f"Received public_chat message from client {sid}, forwarding to all neighbours")
            for server in self.server.connected_servers.keys():
                print(f"Forwarding to {server}")
                self.server.send(msg, 'Server', server)
			
			# also send to connected clients
            self.server.send(msg, 'Client', 'client')
        else:
            print(f"Received public_chat message from server, "
                "forwarding to all clients")
            self.server.send(msg, 'Client', 'client')
        # else:
        #     print("Received public_chat message from an unknown connection, dropping message")

    def server_hello(self, msg):
        """Handle a hello message from a server.

        Args:
            data: The data containing the sender's information.
        """
        sid = request.sid
        print(f"Server hello received from {sid}")

        join_room('server')

        data = msg['data']
        server_ip = data["sender"]

        if server_ip not in self.server.server_list:
            print(f"A server_hello was received from an unrecognised server {server_ip}")
            return

        if server_ip not in self.server.connected_servers:
            client_socket = self.server.create_client_socket()
            try:
                print(f'Attempting to connect to {server_ip}')
                ip, port = server_ip.split(':')
                port = int(port)
                url = f'ws://{ip}:{port}'
                client_socket.connect(url)
                self.server.server_map[sid] = server_ip
                self.server.connected_servers[server_ip] = client_socket
                # Send hello message
                server_hello_data = {
                    "type": "server_hello",
                    "sender": f"{self.server.host}:{self.server.port}"
                }
                server_hello = make_signed_data_msg(server_hello_data, str(self.server.nonce), self.server.private_key)
                print(f"Sending hello message to {server_ip}")
                self.server.connected_servers[server_ip].send(server_hello)

                # Request for client list
                client_update_request = {
                    "type": "client_update_request"
                }
                client_update_request = json.dumps(client_update_request)
                print(f"Sending client update request to {server_ip}")
                client_socket.send(client_update_request)
                
            except (ConnectionErrorSocketIO, SocketIOError) as e:
                print(f'Error ocurred trying to connect to neighbour after server hello: {e}')
        else:
            self.server.server_map[sid] = server_ip

