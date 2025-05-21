# QUIC Chat Application


## Overview

The QUIC Chat Application is a secure, asynchronous chat system that leverages the QUIC protocol over TLS for low-latency, encrypted communication between a server and multiple clients. The application supports both public broadcasts and private messaging. By prefixing a message with `@username`, users can send private messages that are delivered solely to the intended recipient. Additionally, the server maintains and broadcasts an updated online user list whenever a client connects or disconnects.  

User authentication is performed using a simple username–password mechanism. For new users, the system auto-registers them and issues a JSON Web Token (JWT) upon successful login. The server also logs detailed QUIC handshake stages (including connection identifiers and negotiated ALPN protocols) to provide transparency regarding the connection process.

This project meets the design requirements outlined in P2-ProtocolDesign.pdf by providing secure communication, efficient message routing, real-time online user notifications, and support for multiple concurrent client connections.

## Features

- **Secure QUIC Communication:** Uses QUIC over TLS to guarantee encrypted, low-latency data exchange.
- **User Authentication:**  
  - Users authenticate with a username and password.  
  - New users are auto-registered; a JWT token is issued upon successful login.
- **Messaging Capabilities:**  
  - **Public Messages:** Any message not starting with `@` is broadcast to all clients.  
  - **Private Messages:** Messages starting with `@username` are routed exclusively to that user.
- **Online User Notifications:** The server broadcasts system notifications and an updated list of online users when a client connects or disconnects.
- **Handshake Logging:** The server logs the QUIC handshake process, including connection IDs and ALPN negotiation.
- **Asynchronous Multi-Client Support:** Designed to handle multiple concurrent client connections seamlessly.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-username/quic-chat.git
   cd quic-chat
