import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

import json
import base64
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from crypto_utils import base64_to_pem, pem_to_base64
from message_utils import is_valid_message, process_data
from event import Event

class Server:

    def __init__(self, host, port):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.nonce_map = {}
        self.user_list = {}
        self.client_list = {}
        self.host = host
        self.port = port
        self.event = Event(self)

        self.socketio.on_event('connect', self.event.connect)
        self.socketio.on_event('disconnect', self.event.disconnect)
        self.socketio.on_event('hello', self.event.hello)
        self.socketio.on_event('client_list_request', self.event.client_list_request)
        self.socketio.on_event('message', self.event.message)

    def run(self):
        self.socketio.run(self.app, self.host, self.port)

    def send(self, data, *rooms):
        for room in rooms:
            self.socketio.send(data, room=room)


if __name__ == '__main__':
    server = Server("localhost", 4678)
    server.run()

