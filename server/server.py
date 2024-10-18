import logging
import sys
import os
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "libs")))
import argparse
import socketio
from flask import Flask
from flask_socketio import SocketIO
from message_utils import make_signed_data_msg
from crypto_utils import generate_private_key
from server_events import ServerEvent
from socketio.exceptions import (
    ConnectionError as ConnectionErrorSocketIO,
    SocketIOError,
)
from file_routes import routes_bp, MAX_FILE_SIZE


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Server:
    """Class representing the server for the OLAF-Neighbourhood protocol.

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

    server_list = ["127.0.0.1:4567", "127.0.0.1:9002"]

    def __init__(self, port):
        """Initializes the Server with the given host and port.

        Args:
            host (str): The hostname or IP address for the server.
            port (int): The port number for the server.
        """
        self.app = Flask(__name__)
        self.app.register_blueprint(routes_bp)
        self.app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
        self.socketio = SocketIO(self.app, async_mode="eventlet")
        self.private_key = generate_private_key()
        self.server_map = {}
        self.connected_servers = {}
        self.nonce = 1
        self.user_list = {}
        self.client_list = {}

        self.host = ServerEvent.LOOP_BACK_ADDRESS
        self.port = port
        self.event_handler = ServerEvent(self)

        # Event handlers for socket events
        self.socketio.on_event("connect", self.event_handler.connect)
        self.socketio.on_event("disconnect", self.event_handler.disconnect)
        self.socketio.on_event("hello", self.event_handler.hello)
        self.socketio.on_event(
            "client_list_request", self.event_handler.client_list_request
        )
        self.socketio.on_event("message", self.event_handler.message)

    def run(self):
        """Runs the Flask application with SocketIO."""
        logger.info(f"Starting server on {self.host}:{self.port}")
        self.socketio.run(self.app, self.host, self.port)

    def send(self, data, recipient, dest):
        """Sends data to a specific recipient.

        Args:
            data (str): The data to be sent.
            recipient (str): The type of recipient ('Server' or client).
            dest (list): List of destination identifiers (server IPs or client rooms).
        """
        if recipient == "Server":
            if self.connected_servers.get(dest):
                self.connected_servers[dest].send(data)
            else:
                logger.warning(f"Couldn't find {dest} in connected server list")
        else:
            if dest == "client":
                # send to all clients
                for client in self.client_list:
                    self.socketio.send(data, room=client)
            else:
                # send to specific client
                self.socketio.send(data, room=dest)

    def connect_to_servers(self):
        """Connects to listed servers and sends a hello message."""

        successful_connections = []
        failed_connections = []

        # Connect to each listed server
        for server_ip in self.server_list:
            if server_ip == f"{self.host}:{self.port}":
                continue
            try:
                client_socket = self.create_client_socket()
                ip, port = server_ip.split(":")
                port = int(port)
                logger.info(f"Attempting to connect to neighbour server: {server_ip}")
                url = f"ws://{ip}:{port}"
                client_socket.connect(url, transports=['websocket'])
                self.connected_servers[server_ip] = client_socket
                successful_connections.append(server_ip)
            except (ConnectionErrorSocketIO, SocketIOError) as e:
                error_msg = str(e)
                # Extract the most relevant part of the error message using regex
                print(error_msg)
                match = re.search(r'\[WinError \d+\] (.+)', error_msg)
                if match:
                    concise_error = match.group(1)
                else:
                    # If regex doesn't match, use a generic message
                    concise_error = "Connection failed."
                logger.info(f"Could not connect to neighbour server at {server_ip}: {concise_error}")
                failed_connections.append(server_ip)

        # Summary of connection attempts
        if successful_connections:
            logger.info(
                f"Successfully connected to {len(successful_connections)} server(s): {', '.join(successful_connections)}"
            )
        else:
            logger.info("No servers connected successfully.")

        if failed_connections:
            logger.warning(
                f"Failed to connect to {len(failed_connections)} server(s): {', '.join(failed_connections)}"
            )

        # Send hello message to connected servers
        server_hello_data = {
            "type": "server_hello",
            "sender": f"{self.host}:{self.port}",
        }

        for server_ip in list(self.connected_servers.keys()):
            server_hello = make_signed_data_msg(
                server_hello_data, str(self.nonce), self.private_key
            )
            self.nonce += 1
            logger.info(f"Sending hello message to {server_ip}")
            self.connected_servers[server_ip].send(server_hello)

        # Request for client list from each connected server
        client_list_request = {"type": "client_update_request"}

        client_list_request = json.dumps(client_list_request)
        for server_ip in list(self.connected_servers.keys()):
            logger.info(f"Sending client list request to {server_ip}")
            self.connected_servers[server_ip].send(client_list_request)

        # Indicate server startup success
        logger.info(f"Server {self.host}:{self.port} startup success")

    def create_client_socket(self):
        """Creates and configures a SocketIO client socket.

        Returns:
            socketio.Client: Configured SocketIO client.
        """
        client_socket = socketio.Client()

        @client_socket.event
        def connect():
            """Handle a new connection to a neighbor server."""
            logger.info("Successfully connected to neighbor server")

        @client_socket.event
        def disconnect():
            """Handle disconnection from a neighbor server."""
            logger.warning("Disconnected from neighbor server")

        return client_socket


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True, help="Port")
    args = parser.parse_args()
    PORT = args.port
    server = Server(PORT)
    server.connect_to_servers()
    server.run()
