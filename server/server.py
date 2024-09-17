import sys
import os
import socketio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

import json
import base64
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from crypto_utils import base64_to_pem, pem_to_base64
from message_utils import is_valid_message, process_data, make_signed_data_msg
from server_events import ServerEvent, ClientEvent

class Server:

    server_list = []

    def __init__(self, host, port):
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

        # These are the server based handlers, they are invoked on any message sent
        # to the publicly exposed ip:port used to communicate to other servers and
        # clients
        self.socketio.on_event('connect', self.event_handler.connect)
        self.socketio.on_event('disconnect', self.event_handler.disconnect)
        self.socketio.on_event('hello', self.event_handler.hello)
        self.socketio.on_event('client_list_request', self.event_handler.client_list_request)
        self.socketio.on_event('message', self.event_handler.message)

    def run(self):
        self.socketio.run(self.app, self.host, self.port)

    def send(self, data, recipient, dest):
        
        if recipient == "Server":
            for server in dest:
                if self.connected_servers.get(server):
                    self.connected_servers[server].send(data)
                else:
                    print(f"Couldn't find {server} in connected server list")
        else:
            self.socketio.send(data, room=dest)
    
    def connect_to_servers(self):
        for server in self.server_list:
            try:
                print(f'Attempting to connect to {server}')
                client_socket = self.create_client_socket()
                client_socket.connect(server)
                self.connected_servers[server] = client_socket
            except Exception as e:
                print(f'Unexpected error during connection: {e}')
        
        server_hello_data = {
                "type": "server_hello",
                "sender": f"{self.host}:{self.port}"
            }
        for server in list(self.connected_servers.keys()):
            server_hello = make_signed_data_msg(server_hello_data, str(self.nonce))
            self.nonce += 1
            self.connected_servers[server].send(server_hello)

    def create_client_socket(self):
        client_socket = socketio.Client()
        client_socket.on("connect", self.client_socket_event_handler.connect)
        client_socket.on("disconnect", self.client_socket_event_handler.disconnect)
        return client_socket

if __name__ == '__main__':
    server = Server("localhost", 4678)
    server.connect_to_servers()
    server.run()

