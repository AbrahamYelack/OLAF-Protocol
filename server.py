from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    room = 'server'
    join_room(room)
    print(f'Process {sid} connected')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f'Process {sid} disconnected')

if __name__ == '__main__':
    socketio.run(app, host="localhost", port=4678)

