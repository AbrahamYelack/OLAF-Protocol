## Testing Methodology

The following outlines the testing framework used to validate the functionality of our protocol.

### Server

- **Successful start-up on user-specified port** ✅
- **Attempts to connect to servers in the server list** ✅
- **Successfully connects to active neighbor servers** ✅
- **Sends `server_hello` after connecting to neighbor servers** ✅
- **Sends `client_list_request` after connecting to neighbor servers** ✅
- **Correctly handles the following incoming message types only**:
  - `client_list` ✅
  - `client_list_request` ✅
  - `signed_data` ✅
    - `hello` ✅
    - `server_hello` ✅
    - `public_chat` ✅
    - `chat` ✅
- **Handles file upload PUT requests** ✅
- **Handles file download GET requests** ✅

### Client

- **Attempt to connect to user-specified server** ✅
- **Successfully connects to active host server** ✅
- **Sends `hello` after successfully connecting to host server** ✅
- **Sends `client_list_request` after successful `hello` response** ✅
- **Correctly handles the following incoming message types only**:
  - `client_list` ✅
  - `signed_data` ✅
    - `public_chat` ✅
    - `chat` ✅
- **Starts client command line interface (CLI) after successful initialization** ✅
- **CLI**:
  - Display main menu ✅
  - Display neighborhood users ✅
  - Display received messages ✅
  - Send public messages to all users ✅
  - Send private messages only to specified users ✅

### Security

- **Server and Client drop messages of invalid or unknown types** ✅
- **Server ignores all messages from any client/server that has not been verified (e.g., has not sent `hello` or `server_hello`)** ✅
- **Server validates all `signed_data` messages to ensure the counter is greater than the previously observed counter of the sending client** ✅
- **Server ignores all messages from any server that is not in the server list** ✅
- **Server and Client gracefully handle and log errors** ✅
- **Signature generation is the RSA signature of SHA-256 of `data` + `counter`** ✅
- **Client encrypts messages using a randomly generated AES-GCM encryption key** ✅
- **Client encrypts AES-GCM encryption key with recipient's RSA public key** ✅
- **Client and Server validate signatures and drop messages if invalid** ✅

---

### Interoperability Testing

Interoperability testing involved running our implementation in conjunction with the implementations of other groups. The key interaction that was analysed for interoperability tests focused on the communication between our server and the other group’s server, as this is the critical element for ensuring a working system. Once communication between the servers was confirmed, communication between the clients via the established link was also tested.

Two scenarios were tested:
1. **Our server initiates the connection**: The other group’s server is running first, and our server attempts to establish communication with theirs.
2. **Their server initiates the connection**: Our server is running first, and the other group’s server attempts to establish communication with ours.

#### Test 1: Group 48

**Results**: In both scenarios, the servers were unable to establish a connection.

- **Cause of failure**: After reviewing the logs and configurations, we discovered that the other group was using the `wss` (WebSocket Secure) protocol, whereas our group was using `ws` (WebSocket without TLS). This mismatch between secure (`wss`) and non-secure (`ws`) protocols caused all connection attempts to fail.
  
  - **Detailed explanation**: WebSocket communication relies on both sides using the same protocol. The `wss` protocol uses TLS (Transport Layer Security) to encrypt the connection, while `ws` operates without encryption. When our server attempted to connect to their server using `ws`, the connection was rejected because their server expected an encrypted `wss` handshake. This resulted in no connection being established, and our server timed out waiting for a response.

- **Conclusion**: This issue could have been resolved by either configuring our server to use `wss` or their server to accept `ws` connections. In environments where security is essential, it is recommended to use `wss` to ensure encrypted communication.

#### Test 2: Group 69

**Results**: In both scenarios, the servers were unable to successfully communicate.

- **Scenario 1**: 
  - **What happened**: When our server was launched and attempted to connect to Group 69’s server, we observed that a connection request was logged on their server. However, our socket timed out while awaiting a response from their server.
  - **Possible issue**: This suggests that the initial WebSocket handshake was received by their server, but their server either failed to process the handshake correctly or did not send back the required response to complete the connection. This could indicate a misconfiguration in the handshake protocol or a failure in processing connection requests.
  
- **Scenario 2**: 
  - **What happened**: When Group 69’s server was launched, it required manual input to allow for inter-server communication. After entering the address and port of our server (which was already running), the message 'Connected to server at ws://localhost:4567' was printed on their side. However, our server did not receive any connection requests, and no logs were generated indicating that a connection attempt had been made.
  - **Possible issue**: This scenario points to a potential problem on either their server’s client-side WebSocket configuration or our server’s connection handling. While their system printed a message indicating a connection was established, it's possible that the connection attempt was never actually made due to an error in how their server was set up to initiate WebSocket connections. However, it's equally possible that our server did not properly register the incoming connection request or mishandled the handshake process, resulting in the connection not being established. Additionally, the input process on their end for connecting to a server could have been incorrectly handled, leading to a false positive message without a real connection. Therefore, further investigation on both sides is required to determine whether the issue lies in how their server initiates the connection or how our server handles incoming connection attempts.

- **Conclusion**: The likely issue in both scenarios is related to how the WebSocket handshake is managed between our server and Group 69’s server. Both servers are using the same `ws` protocol, so the failure likely stems from incorrect handling of the handshake, or possibly incorrect input parsing or internal connection handling on their end. Further debugging would involve tracing the handshake flow and reviewing how the connection is initialised and maintained.
