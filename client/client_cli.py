import requests
from crypto_utils import get_public_key, get_fingerprint

class ClientCLI:
    """
    A command-line interface for the client, handling user interactions
    such as sending messages, uploading/downloading files, and listing users/messages.
    """

    def __init__(self, client):
        """
        Initialize the ClientCLI with a client instance.

        Args:
            client: An instance of the Client class.
        """
        self.client = client
        self.fingerprint_public_key_map = {}

    def print_options(self):
        """
        Prints the available request types for the user to select from.
        """
        for index, value in enumerate(self.client.request_types):
            print(f"{index}: '{value}'")

    def handle_public_chat(self):
        """
        Handles sending a public chat message.
        """
        message = input("Enter the message: ")
        self.client.request.public_chat(message)

    def update_fingerprint_map(self):
        """
        Updates the mapping between user fingerprints and their public keys.
        """
        self.fingerprint_public_key_map = {}
        for public_key in self.client.user_list.keys():
            fingerprint = get_fingerprint(public_key)
            self.fingerprint_public_key_map[fingerprint] = public_key

    def handle_chat(self):
        """
        Handles sending a private chat message to selected users.
        """
        self.update_fingerprint_map()
        users = list(self.fingerprint_public_key_map.keys())

        # Ensure there are users to chat with
        if not users:
            print("No users available to chat.")
            return

        # Get the current user's fingerprint to exclude from the list
        current_user_fingerprint = get_fingerprint(get_public_key(self.client.private_key))

        # Display users with their fingerprints
        print("Available users to chat with:")
        for index, user_fingerprint in enumerate(users):
            if user_fingerprint == current_user_fingerprint:
                continue
            print(f"{index}: {user_fingerprint}")

        # Get recipients from user input
        recipients_string = input("Which users would you like to communicate with (comma-separated indices): ")
        recipients_indices = [s.strip() for s in recipients_string.split(",")]
        recipients = []

        # Validate and collect recipient public keys
        for i in recipients_indices:
            try:
                user_index = int(i)
                user_fingerprint = users[user_index]
                recipients.append(self.fingerprint_public_key_map[user_fingerprint])
            except (ValueError, IndexError):
                print(f"Invalid user index: {i}")
                continue

        # If no valid recipients are selected
        if not recipients:
            print("No valid recipients selected.")
            return

        # Get the message to send
        message = input("Enter the message: ")
        self.client.request.chat(message, *recipients)

    def handle_file_upload(self):
        """
        Handles uploading a file to the server.
        """
        filepath = input("Enter the file path of the file: ")

        try:
            with open(filepath, 'rb') as file:
                # Define the endpoint URL
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
        """
        Handles downloading a file from the server.
        """
        files = list(self.client.download_links.keys())

        if not files:
            print("No files available for download.")
            return

        # Display available files
        print("Available files to download:")
        for index, filename in enumerate(files):
            print(f"{index}: '{filename}'")

        # Get the file index from user input
        try:
            file_index = int(input("Which file would you like to download: "))
            filename = files[file_index]
        except (ValueError, IndexError):
            print("Invalid file index.")
            return

        download_url = self.client.download_links[filename]
        save_path = input("Enter the path where the file should be saved (including file name): ")

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
        self.update_fingerprint_map()

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
            participants = ', '.join(msg.participants)
            print(f"Message {index + 1}:")
            print(f"  From: {msg.sender}")
            print(f"  To: {participants}")
            print(f"  Text: {msg.text}")
            print("-" * 40)

    def run(self):
        """
        Runs the client CLI, handling user input and invoking the appropriate methods.
        """
        while True:
            print("Select an option:")
            print("0: View Messages")
            print("1: Send Message")
            print("2: List Users")
            try:
                index = int(input("Enter your choice: "))
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

            if index == 0:
                self.print_messages()
            elif index == 1:
                self.print_options()
                try:
                    option_index = int(input("What kind of message do you want to send?: "))
                    request_type = self.client.request_types[option_index]
                except (ValueError, IndexError):
                    print("Invalid option selected.")
                    continue

                if request_type == 'public_chat':
                    self.handle_public_chat()
                elif request_type == 'chat':
                    self.handle_chat()
                elif request_type == 'file_upload':
                    self.handle_file_upload()
                elif request_type == 'file_download':
                    self.handle_file_download()
                else:
                    print("Sorry, that isn't a valid option.")
            elif index == 2:
                self.print_users()
            else:
                print("Sorry, that isn't a valid option.")
