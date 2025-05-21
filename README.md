# QUIC Chat Application

## Overview

The QUIC Chat Application is a secure, asynchronous chat system built over the QUIC protocol with TLS encryption to ensure low-latency and secure communication between clients and a central server. The application supports:
- **User Authentication:** Users sign in using a username and password; new users are automatically registered. Upon successful authentication, a JSON Web Token (JWT) is issued.
- **Messaging Capabilities:**  
  - **Public Messages:** Any message not starting with `@` is broadcast to all connected clients.  
  - **Private Messages:** Messages starting with `@username` are delivered only to the intended recipient.
- **Real-Time Notifications:** The server broadcasts an updated list of online users and notifies all clients when a user connects or disconnects.
- **Debugging Information:** The server logs detailed QUIC handshake stages (including connection identifiers and negotiated ALPN protocols).

This project meets the requirements specified in P2-ProtocolDesign.pdf and is implemented in Python using the `aioquic` library.

## Features

- **Secure QUIC Communication:** Utilizes QUIC over TLS for encrypted data transfer.
- **User Authentication & Registration:**  
  - Username/password authentication with auto-registration for new users.  
  - JWT tokens are issued upon successful login.
- **Dual Messaging Modes:**  
  - **Public Messaging:** Standard chat messages are broadcast to all users.
  - **Private Messaging:** Prefix a message with `@username` to send it privately.
- **Real-Time User Status:** Automatically updated online user lists are broadcast as users join or disconnect.
- **Asynchronous Multi-Client Support:** Designed to support numerous simultaneous client connections.
- **Handshake Logging:** Detailed logging of QUIC handshake events for debugging and transparency.

## Installation

1. **Clone the Repository:**

   Open your terminal and run:
   ```bash
   git clone https://github.com/your-username/quic-chat.git
   cd quic-chat

2. **Set Up the Python Virtual Environment:**
  
  Create and activate a virtual environment:
  python3 -m venv venv
source venv/bin/activate


3. **Install Dependencies:**
  
  Install the required packages:
  pip install aioquic python-jose[bcrypt] bcrypt


4. **Generate TLS Certificates:**

 QUIC requires TLS certificates. 
 Generate a self-signed certificate by running:
 mkdir ssl
 openssl req -x509 -newkey rsa:2048 -nodes -keyout
 ssl/key.pem -out ssl/cert.pem -days 365 -subj "/CN=localhost"


5. **UsageStarting the Server:**
  In one terminal, activate your virtual environment:

  source venv/bin/activate

  Start the server:
  python server.py

 Running a Client
  Open a new terminal window and activate the virtual environment:

  source venv/bin/activate

   Start the client:
   python client.py


 ## Thanks