# Contact Information
Abraham Yelack (a1804620) - abrahamyelack@gmail.com
Jack Scholten (a1826009) - jack.scholten@hotmail.com
Julian Lovell (a1829617) - jlovell108@gmail.com 
Tom Materne (a1825150) - a1825150@adelaide.edu.au

# OLAF-Neighbourhood Client

Welcome to the **OLAF-Neighbourhood Protocol Guide**. This document will describe how to launch and interact with the OLAF-Neighbourhood protocol, enabling functionalities such as sending messages, uploading/downloading files, and managing user interactions.

## Features

- **Public Chat**: Broadcast messages to all users in the network.
- **Private Chat**: Send encrypted messages to specific users.
- **File Upload/Download**: Upload files to the server and download them when needed.
- **User Management**: List available users and view their public keys.
- **Message Management**: View a history of received messages.

## Prerequisites

- **Python 3.6 or higher**: Ensure you have Python installed on your system.

## Installation

1. **Open/Clone the Repository**:

2. **Install Dependencies**:
    ```bash
    pip install -r documents/requirements.txt
    ```

## Running the Servers and Clients

#### Modifying the server list

An important step in the setup process is to ensure the server_list variable
in the `server.py` file is updated to contain the ip addresses (in format "<host>:<port>")
of the servers you wish to participate in the neighbourhood communication. In 
reality this will be determined in the future by the creation of a verified and
agreed server list. However, for local testing purposes you will have to modify this
yourself manually.


#### Launch the Server(s)

To simulate messaging between clients you must first launch `server.py` before
the client is launched. Clients can share a home server or clients can have different
servers. To launch the server run the following command from the OLAF-Protocol directory, where <HOST> and <PORT> are placeholders for the host and port you 
wish the server to operate on.

```bash
python server/server.py --host <HOST> --port <PORT>
```

#### Launch the Client(s)

Once the server(s) are running, you can launch the Client.py file, specifying
he host and port of the server you wish the client to connect to in place of 
<HOST> and <PORT> respectively.

```bash
python client/client.py --host <HOST> --port <PORT>
```

Once you have executed the above command, the Client will immediately attempt
to perform 3 initialisation steps:

- Connect to the Server
- Send client hello to the server
- Request client list from the server

It performs these steps synchronously and enforces they are acknowledged by the
server before moving forward.

Upon successfull completion of the initialisation process, the client command line
interface (CLI) will be automatically launched. Interaction with the CLI will be 
expalined in the following sections.

## Client CLI

#### Main Menu Options
When you run the CLI, you will be presented with the following main menu options:
Select an option:
```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice:
```
Enter the corresponding number to proceed with the desired action.

#### Sending Messages

**Public Chat - To send a public message visible to all users:**

Select Option 1 from the main menu to send a message.
You will be prompted to choose the type of message. Select the option corresponding to 'public_chat'.
Enter your message at the prompt.
The message will be broadcasted to all users.

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 1
0: 'public_chat'
1: 'chat'
2: 'file_upload'
3: 'file_download'
What kind of message do you want to send?: 0
Enter the message: Hello everyone!
```

**Private Chat - To send a private, encrypted message to specific users:**

To send a private, encrypted message to specific users:

1. Select Option 1 from the main menu to send a message
2. Choose the option corresponding to 'chat'.
3. The CLI will display a list of available users with their fingerprints.
4. Enter the indices of the users you wish to message, separated by commas.
5. Enter your message at the prompt.
6. The message will be sent encrypted to the selected users.

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 1
0: 'public_chat'
1: 'chat'
2: 'file_upload'
3: 'file_download'
What kind of message do you want to send?: 1
Available users to chat with:
0: abcdef123456...
1: 7890abcd1234...
Which users would you like to communicate with (comma-separated indices): 0,1
Enter the message: Hello, this is a private message!
```

#### File Operations

To upload a file to the server:

Select Option 1 from the main menu to send a message.
Choose the option corresponding to 'file_upload'.
Enter the file path of the file you wish to upload.
Upon successful upload, a file URL will be provided.

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 1
0: 'public_chat'
1: 'chat'
2: 'file_upload'
3: 'file_download'
What kind of message do you want to send?: 2
Enter the file path of the file: /path/to/your/file.txt
File successfully uploaded. Retrieve it here: http://server_host:server_port/downloads/file.txt
```

To download a previously uploaded file:

Select Option 1 from the main menu to send a message.
Choose the option corresponding to 'file_download'.
The CLI will display a list of available files.
Enter the index of the file you wish to download.
Enter the save path where the file should be stored.
The file will be downloaded and saved to the specified location.
Example:

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 1
0: 'public_chat'
1: 'chat'
2: 'file_upload'
3: 'file_download'
What kind of message do you want to send?: 3
Available files to download:
0: 'file.txt'
Which file would you like to download: 0
Enter the path where the file should be saved (including file name): /path/to/save/file.txt
File successfully downloaded and saved to /path/to/save/file.txt
```

#### Listing Users

To view the list of available users and their public keys:

Select Option 2 from the main menu.
The CLI will display the users' fingerprints and their corresponding public keys.
Example:

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 2
Available users (fingerprint -> public key):

Fingerprint: abcdef123456...
Public Key: MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAn...

Fingerprint: 7890abcd1234...
Public Key: MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAm...
```

#### Viewing Messages

To view your message history:

Select Option 0 from the main menu.
The CLI will display all messages stored in your message buffer, including the sender, recipients, and message text.

```
Select an option:
0: View Messages
1: Send Message
2: List Users
Enter your choice: 0
Messages:
Message 1:
  From: abcdef123456...
  To: Public
  Text: Hello everyone!
----------------------------------------
Message 2:
  From: 7890abcd1234...
  To: abcdef123456...
  Text: Hi, this is a private message!
----------------------------------------
```


