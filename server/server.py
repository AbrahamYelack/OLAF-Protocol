"""
This module contains the implementation of the OLAF-Neighborhood protocol server.

It manages connections between clients and servers using Flask and Flask-SocketIO.
The server handles various events such as connections, disconnections, and message
exchanges. It also provides utilities for signing messages and validating their integrity.

Classes:
    Server: Represents the server that handles socket connections and events.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'libs')))
import argparse
import socketio
from flask import Flask
from flask_socketio import SocketIO
from message_utils import make_signed_data_msg
from server_events import ServerEvent, ClientEvent
from socketio.exceptions import ConnectionError as ConnectionErrorSocketIO, SocketIOError

class Server:
    """Class representing the server for the OLAF-Neighborhood protocol.

    Attributes:
        app: Flask application instance.
        socketio: SocketIO instance for handling WebSocket connections.
        server_map: Mapping of connected servers.
        connected_servers: List of currently connected servers.
        nonce: Counter for unique message identification.
        user_nonce_map: Mapping of user nonces.
        user_list: List of connected users.
        client_list: List of connected clients.
    """

    server_list = []

    def __init__(self, host, port):
        """Initializes the Server with the given host and port.

        Args:
            host (str): The hostname or IP address for the server.
            port (int): The port number for the server.
        """
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.server_map = {}
        self.connected_servers = {}
        self.nonce = 1
        self.user_nonce_map = {}
        self.user_list = {}
        self.client_list = {}

        self.host = host
        self.port = port
        self.event_handler = ServerEvent(self)
        self.client_socket_event_handler = ClientEvent(self)

        # Event handlers for socket events
        self.socketio.on_event('connect', self.event_handler.connect)
        self.socketio.on_event('disconnect', self.event_handler.disconnect)
        self.socketio.on_event('hello', self.event_handler.hello)
        self.socketio.on_event('client_list_request', self.event_handler.client_list_request)
        self.socketio.on_event('message', self.event_handler.message)

    def run(self):
        """Runs the Flask application with SocketIO."""
        self.socketio.run(self.app, self.host, self.port)

    def send(self, data, recipient, dest):
        """Sends data to a specific recipient.

        Args:
            data (str): The data to be sent.
            recipient (str): The type of recipient ('Server' or client).
            dest (list): List of destination identifiers (server IPs or client rooms).
        """
        if recipient == "Server":
            for server_ip in dest:
                if self.connected_servers.get(server_ip):
                    self.connected_servers[server_ip].send(data)
                else:
                    print(f"Couldn't find {server_ip} in connected server list")
        else:
            self.socketio.send(data, room=dest)

    def connect_to_servers(self):
        """Connects to listed servers and sends a hello message."""
        for server_ip in self.server_list:
            try:
                print(f'Attempting to connect to {server_ip}')
                client_socket = self.create_client_socket()
                client_socket.connect(server_ip)
                self.connected_servers[server_ip] = client_socket
            except (ConnectionErrorSocketIO, SocketIOError) as e:
                print(f'Error ocurred trying to connect to neighbour during server startup: {e}')

        server_hello_data = {
            "type": "server_hello",
            "sender": f"{self.host}:{self.port}"
        }
        for server_ip in list(self.connected_servers.keys()):
            server_hello = make_signed_data_msg(server_hello_data, str(self.nonce))
            self.nonce += 1
            self.connected_servers[server_ip].send(server_hello)

    def create_client_socket(self):
        """Creates and configures a SocketIO client socket.

        Returns:
            socketio.Client: Configured SocketIO client.
        """
        client_socket = socketio.Client()
        client_socket.on("connect", self.client_socket_event_handler.connect)
        client_socket.on("disconnect", self.client_socket_event_handler.disconnect)
        return client_socket

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, required=True, help='Hostname')
    parser.add_argument('--port', type=int, required=True, help='Port')
    args = parser.parse_args()
    HOST = args.host
    PORT = args.port
    server = Server(HOST, PORT)
    server.connect_to_servers()
    server.run()
