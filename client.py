import socketio
import threading

socket_io = socketio.Client()

# Stores User (public-key) to Server (IP Address) mapping
user_list = {}
# Synchronisation utility
response_event = threading.Event()

@socket_io.event
def connect():
    print("Connected to server")
    response_event.set()

@socket_io.event
def client_list(data):

    print("Received client list from server")

    # The server key should contain a list of JSON objects 
    # which each have an address and list of clients
    json_server_list = data['servers']

    # The client maps each user to their host server
    for server in json_server_list:
        for client in server['clients']:
            user_list[client] = server['address']
    
    print("Finished processing client list:")

    response_event.set()
    

if __name__ == '__main__':
    # Connect to server
    socket_io.connect("http://localhost:4678")
    response_event.wait()

    # Request server for client list
    socket_io.emit("client_list_request", {
        "type": "client_list_request"
    })
    response_event.wait()

    socket_io.wait()
