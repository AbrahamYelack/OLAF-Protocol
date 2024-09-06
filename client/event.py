import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs')))

from message_utils import is_valid_message, process_data
from crypto_utils import decrypt_symm_key, decrypt_message
from collections import namedtuple

# Object to store processed messages on the client side
Msg = namedtuple('Msg', ['text', 'sender', 'participants'])

class Event:

    def __init__(self, client):
        self.client = client

    def connect(self):
        print("Successfully connected to server")
        self.client.response_event.set()

    def hello(self):
        print("Server accepted the request for service")
        self.client.response_event.set()

    def client_list(self, data):

        print("Received user list from server")

        # The server key should contain a list of JSON objects
        # which each have an address and list of clients
        json_server_list = {}
        if(data):
            json_server_list = data['servers']

        # The client maps each user to their host server
        for server in json_server_list:
            for client in server['clients']:
                self.client.user_list[client] = server['address']
        self.client.response_event.set()

    def message(self, data):
        data = process_data(data).get('data')
        msg_type = None

        if(data):
            msg_type = data.get('type')
        else:
            print("Ignoring message due to error")
            return
        
        if not is_valid_message(data, msg_type):
            print(f"Invalid message recieved of type {msg_type}")
            return

        if msg_type == 'chat' or msg_type == 'public_chat':
            self.client.handle_chat(data)
        else:
            print("Unknown message type received")

    def handle_chat(self, data):

        # Message must be valid to reach this point
        # There are two message types that arrive here:
        # 
        #  1 - public_chat
        #  2 - chat
        # 
        # 'public_chat': The content (message, sender, recipients)
        # can be buffered immediately, as this information is not encrypted
        # 'chat' messages mus
        # 
        # 'chat': The 'chat' segment of the message must be decrypted using 
        # the AES symmetric key. The AES symmetric key is itself encrypted and 
        # located in the 'symm_keys' (list) segment of the message. 
        # A brute-force trial and error approach must be performed to decrypt 
        # each symmetric key with your RSA private key and use this key to decrypt 
        # the 'chat' segment. Success is determined by a correctly structured chat 
        # segment as output

        if(data['type'] == "public_chat"):
            # Create message and push to buffer
            msg = Msg(data['message'], data['sender'], ["Public"])
            self.client.message_buffer.append(msg)
        else:
            encrypted_chat = data["chat"]
            iv = data["iv"]
            chat = None
            # Try to decrypt each symm key and use this decrypted symm key to 
            # decrypt the chat segment.
            for encrypted_symm_key in data['symm_keys']:
                symm_key = decrypt_symm_key(encrypted_symm_key, self.client.private_key)
                chat = decrypt_message(symm_key, encrypted_chat, iv)
                if chat: break
            
            # Couldn't decrypt chat segment
            if(not chat):
                print("Couldn't decrypt chat segment, assuming it is not addressed to me and dropping message")
                return
                
            # Validate decrypted chat JSON
            if not is_valid_message(chat, 'chat'):
                print("Chat message decrypted although it is valid, dropping message")

            # Store decrypted message info in a buffer
            msg = Msg(chat['message'], chat['participants'][0], chat['participants'][1:])
            self.client.message_buffer.append(msg)