import socketio

socket_io = socketio.Client()

@socket_io.event
def connect():
    print("Connected to server")

socket_io.connect("http://localhost:4678")
socket_io.wait()