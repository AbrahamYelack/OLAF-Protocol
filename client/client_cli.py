import requests

from crypto_utils import get_public_key, get_fingerprint

class ClientCLI:

    def __init__(self, client):
        self.client = client
        self.fingerprint_public_key_map = {}

    def print_options(self):
        for index, value in enumerate(self.client.request_types):
            print(f"{index}: '{value}'")

    def handle_public_chat(self):
        message = str(input("Enter the message: "))
        self.client.request.public_chat(message)

    def update_fingerprint_map(self):
        self.fingerprint_public_key_map = {}
        for public_key in list(self.client.user_list.keys()):
            self.fingerprint_public_key_map[get_fingerprint(public_key)] = public_key

    def handle_chat(self):
        self.update_fingerprint_map()
        users = list(self.fingerprint_public_key_map.keys())
        # Ensure there are users to chat with
        if not users:
            print("No users available to chat.")
            return

        # Display users with their public keys
        for index, user in enumerate(users):
            if(user == get_fingerprint(get_public_key(self.client.private_key))):
                continue
            print(f"{index}: {user}")

        # Get recipients from user input
        recipients_string = str(input("Which users would you like to communicate with (comma-separated indices): "))
        recipients_string = recipients_string.replace(" ", "")
        recipients_indices = recipients_string.split(",")
        recipients = []

        # Loop through each index provided by the user and add the corresponding user
        for i in recipients_indices:
            try:
                recipients.append(self.fingerprint_public_key_map[users[int(i)]])  # Append the selected user based on index
            except (ValueError, IndexError):
                print(f"Invalid user index: {i}")
                continue

        # If no valid recipients are selected
        if not recipients:
            print("No valid recipients selected.")
            return

        # Get the message to send
        message = str(input("Enter the message: "))
        self.client.request.chat(message, *recipients)

    def handle_file_upload(self):
        filepath = str(input("Enter the file path of the file: "))
        
        # Open the file in binary mode
        try:
            with open(filepath, 'rb') as file:
                # Define the endpoint URL (replace with your actual server's URL)
                upload_url = f"http://{self.client.host}:{self.client.port}/api/upload"

                # Create the file payload for the POST request
                files = {'file': file}

                # Send the file via POST request
                response = requests.post(upload_url, files=files)

                # Check the server's response
                if response.status_code == 200:
                    # Extract the file URL from the response
                    file_url = response.json().get('file_url', '')
                    self.client.download_links[file.name] = file_url
                    if file_url:
                        print(f"File successfully uploaded. Retrieve it here: {file_url}")
                    else:
                        print("Error: No file URL returned.")
                elif response.status_code == 413:
                    print("Error: File size exceeds the limit.")
                else:
                    print(f"Error: Failed to upload file. Server responded with status code {response.status_code}.")
        except FileNotFoundError:
            print("Error: File not found. Please check the file path and try again.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def handle_file_download(self):
        files = list(self.client.download_links.keys())
        for index, value in enumerate(files):
            print(f"{index}: '{value}'")
        
        # Loop through each index provided by the user and add the corresponding user
        file_index = int(input("Which file would you like to download: "))
        file = None

        try:
            file = files[int(file_index)]
        except (ValueError, IndexError):
            print(f"Invalid user index: {file_index}")
            return
        
        download_url = self.client.download_links[file]

        save_path = str(input("Enter the path where the file should be saved (including file name): "))
        
        try:
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"File successfully downloaded and saved to {save_path}")
            else:
                print(f"Error: Failed to download file. Server responded with status code {response.status_code}.")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while downloading the file: {e}")

    def print_users(self):
        """
        Pretty prints the fingerprint to public key mapping.
        """
        if not self.fingerprint_public_key_map:
            print("No users available.")
            return

        print("Available users (fingerprint -> public key):")
        for fingerprint, public_key in self.fingerprint_public_key_map.items():
            print(f"Fingerprint: {fingerprint}\nPublic Key: {public_key}\n")

    def print_messages(self):
        """
        Pretty prints the messages stored in the client's message buffer.
        """
        if not self.client.message_buffer:
            print("No messages available.")
            return

        print("Messages:")
        for index, msg in enumerate(self.client.message_buffer):
            print(f"Message {index + 1}:")
            print(f"  From: {msg.sender}")
            print(f"  To: {', '.join(msg.participants)}")
            print(f"  Text: {msg.text}")
            print("-" * 40)

    def run(self):
        while(True):
            index = int(input("0-View Messages or 1-Send Message or 2-List Users: "))
            if index == 0:
                self.print_messages()
            elif index == 1:
                self.print_options()
                index = int(input("What kind of message do you want to send?: "))
                if self.client.request_types[index] == 'public_chat': self.handle_public_chat()
                elif self.client.request_types[index] == 'chat': self.handle_chat()
                elif self.client.request_types[index] == 'file_upload': self.handle_file_upload()
                elif self.client.request_types[index] == 'file_download': self.handle_file_download()
                else: print("Sorry, that isn't a valid option")
            elif index == 2:
                self.update_fingerprint_map()
                self.print_users()
            else:
                print("Sorry, that isn't a valid option")
    