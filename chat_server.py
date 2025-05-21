# #!/usr/bin/env python3
# """
# QUIC Chat Server
# ----------------
# Features:
# • Prints handshake stages when a client connects.
# • Requires clients to authenticate using a simple (in‑memory) username–password mechanism.
#   (For this demo, an unknown username is auto-registered.)
# • Routes chat messages: messages starting with “@username” are sent privately;
#   all others are broadcast.
# • After a client authenticates or disconnects, the server broadcasts the current
#   online user list.
# """

# import asyncio
# import json
# import logging
# from typing import Dict, Optional

# from aioquic.asyncio import serve, QuicConnectionProtocol
# from aioquic.quic.configuration import QuicConfiguration
# from aioquic.quic.events import (
#     HandshakeCompleted,
#     StreamDataReceived,
#     ConnectionTerminated
# )

# logging.basicConfig(level=logging.INFO)

# # Message type definitions
# class MsgType:
#     AUTH_REQ = 0   # Authentication request from client
#     AUTH_OK  = 1   # Authentication successful
#     AUTH_BAD = 2   # Authentication failed
#     CHAT     = 3   # Chat message (public or private)
#     SYS      = 4   # System message (e.g. online users update)

# # Helper functions to encode/decode messages as JSON
# def pack(msg: dict) -> bytes:
#     return json.dumps(msg).encode()

# def unpack(data: bytes) -> dict:
#     return json.loads(data.decode())

# # In-memory user database for authentication
# # For simplicity, if a user name is not registered, we auto-register it.
# REGISTERED_USERS: Dict[str, str] = {}

# def verify_or_register(username: str, password: str) -> bool:
#     if username in REGISTERED_USERS:
#         return REGISTERED_USERS[username] == password
#     else:
#         REGISTERED_USERS[username] = password
#         return True

# # ChatServer maintains the list of active (authenticated) clients.
# class ChatServer:
#     def __init__(self):
#         # Mapping: username → ChatProtocol instance
#         self.clients: Dict[str, "ChatProtocol"] = {}

#     def register(self, username: str, protocol: "ChatProtocol"):
#         self.clients[username] = protocol
#         logging.info(f"User '{username}' logged in. Online: {list(self.clients.keys())}")
#         asyncio.create_task(self.broadcast_online())

#     def unregister(self, username: str):
#         if username in self.clients:
#             del self.clients[username]
#             logging.info(f"User '{username}' disconnected. Online: {list(self.clients.keys())}")
#             asyncio.create_task(self.broadcast_online())

#     async def broadcast_online(self):
#         """Send updated online users list to all connected clients."""
#         online = list(self.clients.keys())
#         msg = {
#             "v": 1,
#             "t": MsgType.SYS,
#             "body": f"Online users: {', '.join(online)}"
#         }
#         for client in self.clients.values():
#             await client.send_message(msg)

#     async def broadcast_chat(self, sender: str, text: str):
#         """Broadcast a public chat message from sender to everyone (except sender)."""
#         msg = {
#             "v": 1,
#             "t": MsgType.CHAT,
#             "body": f"{sender}: {text}"
#         }
#         for username, client in self.clients.items():
#             if username != sender:
#                 await client.send_message(msg)

#     async def send_private(self, sender: str, target: str, text: str, sender_protocol: "ChatProtocol"):
#         """Send a private message from sender to target."""
#         msg = {
#             "v": 1,
#             "t": MsgType.CHAT,
#             "body": f"[Private] {sender}: {text}",
#             "to": target
#         }
#         if target in self.clients:
#             await self.clients[target].send_message(msg)
#             # Acknowledge to sender
#             ack = {
#                 "v": 1,
#                 "t": MsgType.CHAT,
#                 "body": f"[Private to {target}] {text}",
#                 "to": target
#             }
#             await sender_protocol.send_message(ack)
#         else:
#             err = {
#                 "v": 1,
#                 "t": MsgType.SYS,
#                 "body": f"User '{target}' not online."
#             }
#             await sender_protocol.send_message(err)

# # ChatProtocol defines how each client connection is handled.
# class ChatProtocol(QuicConnectionProtocol):
#     username: Optional[str] = None  # Will be set after successful authentication

#     def __init__(self, *args, server: ChatServer = None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.server = server

#     def quic_event_received(self, event) -> None:
#         # Log handshake events
#         if isinstance(event, HandshakeCompleted):
#             logging.info(
#                 f"[HS] Handshake completed: CID={self._quic.connection_id.hex()}, ALPN={event.alpn_protocol}"
#             )
#         elif isinstance(event, StreamDataReceived):
#             self.handle_data(event.stream_id, event.data, event.end_stream)
#         elif isinstance(event, ConnectionTerminated):
#             if self.username:
#                 self.server.unregister(self.username)

#     def handle_data(self, stream_id: int, data: bytes, end_stream: bool):
#         message = unpack(data)
#         if self.username is None:
#             # Expect authentication message (AUTH_REQ)
#             if message.get("t") != MsgType.AUTH_REQ:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Authenticate first using AUTH_REQ"
#                 })
#                 return
#             username = message.get("to")
#             password = message.get("body")
#             if not username or not password:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Username and password required"
#                 })
#                 return
#             if verify_or_register(username, password):
#                 self.username = username
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_OK,
#                     "body": f"Welcome {username}!"
#                 })
#                 self.server.register(username, self)
#             else:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Authentication failed"
#                 })
#         else:
#             # Chat message phase
#             if message.get("t") == MsgType.CHAT:
#                 msg_text = message.get("body", "")
#                 if msg_text.startswith("@"):
#                     # Private message: expecting format "@target message"
#                     parts = msg_text.split(" ", 1)
#                     if len(parts) < 2:
#                         self.send_on_new_stream({
#                             "v": 1,
#                             "t": MsgType.SYS,
#                             "body": "Usage: @username message"
#                         })
#                         return
#                     target = parts[0][1:]
#                     text = parts[1]
#                     asyncio.create_task(self.server.send_private(self.username, target, text, self))
#                 else:
#                     asyncio.create_task(self.server.broadcast_chat(self.username, msg_text))
#             else:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.SYS,
#                     "body": "Unknown command."
#                 })

#     def send_on_new_stream(self, msg: dict):
#         # To avoid reuse of an already ended stream, always use a new stream.
#         stream_id = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(stream_id, pack(msg), end_stream=True)
#         self.transmit()

#     async def send_message(self, msg: dict):
#         stream_id = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(stream_id, pack(msg), end_stream=True)
#         self.transmit()

# async def main():
#     server = ChatServer()
#     config = QuicConfiguration(is_client=False, alpn_protocols=["chat/1"])
#     config.load_cert_chain("ssl/cert.pem", "ssl/key.pem")
#     logging.info("Starting QUIC chat server on port 4433")
#     await serve(
#         "0.0.0.0",
#         4433,
#         configuration=config,
#         create_protocol=lambda *args, **kwargs: ChatProtocol(*args, server=server, **kwargs)
#     )
#     await asyncio.Future()  # run forever

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         pass




# #!/usr/bin/env python3
# """
# QUIC Chat Server

# • Logs handshake stages.
# • Accepts authentication (AUTH_REQ) then routes chat messages:
#     – A message starting with “@username” is treated as a private message.
#     – Otherwise, the message is broadcast.
# • Broadcasts the current online user list whenever a client connects or disconnects.
# • Listens for a "quit" command on the server terminal to exit gracefully.
# """

# import asyncio
# import sys
# import logging
# from typing import Dict

# from aioquic.asyncio import serve, QuicConnectionProtocol
# from aioquic.quic.events import (
#     HandshakeCompleted,
#     StreamDataReceived,
#     ConnectionTerminated,
# )
# from aioquic.quic.configuration import QuicConfiguration

# from protocol import MsgType, pack, unpack
# import auth

# logging.basicConfig(level=logging.INFO)


# class ChatServer:
#     """Maintains connected clients and routes messages."""
#     def __init__(self):
#         # Map username → ChatProtocol instance
#         self.clients: Dict[str, ChatProtocol] = {}

#     def register_client(self, username: str, protocol: "ChatProtocol"):
#         self.clients[username] = protocol
#         logging.info(f"User '{username}' connected. Online: {list(self.clients.keys())}")
#         asyncio.create_task(self.broadcast_online())

#     def unregister_client(self, username: str):
#         if username in self.clients:
#             del self.clients[username]
#             logging.info(f"User '{username}' disconnected. Online: {list(self.clients.keys())}")
#             asyncio.create_task(self.broadcast_online())

#     async def broadcast_online(self):
#         """Broadcast the list of online users to all connected clients."""
#         online = ", ".join(self.clients.keys()) if self.clients else "None"
#         msg = {
#             "v": 1,
#             "t": MsgType.SYS,
#             "body": f"Online users: {online}"
#         }
#         for client in self.clients.values():
#             await client.send_message(msg)

#     async def route_message(self, sender: str, message: dict):
#         """
#         If the message body starts with "@", send it as a private message.
#         Otherwise, broadcast the message to all clients (except the sender).
#         """
#         body = message.get("body", "")
#         if body.startswith("@"):
#             parts = body.split(" ", 1)
#             if len(parts) < 2:
#                 err = {
#                     "v": 1,
#                     "t": MsgType.SYS,
#                     "body": "Invalid private message format. Use '@username message'"
#                 }
#                 if sender in self.clients:
#                     await self.clients[sender].send_message(err)
#                 return

#             target = parts[0][1:]  # remove '@'
#             text = parts[1]
#             if target in self.clients:
#                 private_msg = {
#                     "v": 1,
#                     "t": MsgType.CHAT,
#                     "body": f"[Private] {sender}: {text}"
#                 }
#                 await self.clients[target].send_message(private_msg)
#                 # Optionally send confirmation to sender.
#                 confirm = {
#                     "v": 1,
#                     "t": MsgType.CHAT,
#                     "body": f"[Private to {target}] {text}"
#                 }
#                 await self.clients[sender].send_message(confirm)
#             else:
#                 err = {
#                     "v": 1,
#                     "t": MsgType.SYS,
#                     "body": f"User '{target}' not found."
#                 }
#                 await self.clients[sender].send_message(err)
#         else:
#             # Broadcast public message.
#             public_msg = {
#                 "v": 1,
#                 "t": MsgType.CHAT,
#                 "body": f"{sender}: {body}"
#             }
#             for user, client in self.clients.items():
#                 if user != sender:
#                     await client.send_message(public_msg)


# class ChatProtocol(QuicConnectionProtocol):
#     """One instance per client connection."""
#     def __init__(self, *args, server: ChatServer = None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.server = server
#         self.username = None

#     def quic_event_received(self, event) -> None:
#         if isinstance(event, HandshakeCompleted):
#             # Log handshake progress. Try to get a connection ID;
#             # fall back to "unknown" if not available.
#             try:
#                 cid = self._quic.connection_id.hex()
#             except AttributeError:
#                 cid = "unknown"
#             logging.info(f"[HS] Handshake completed: cid={cid}, ALPN={event.alpn_protocol}")
#         elif isinstance(event, StreamDataReceived):
#             self.process_message(event.stream_id, event.data, event.end_stream)
#         elif isinstance(event, ConnectionTerminated):
#             if self.username:
#                 self.server.unregister_client(self.username)

#     def process_message(self, stream_id: int, data: bytes, end_stream: bool):
#         message = unpack(data)
#         # Authentication phase.
#         if self.username is None:
#             if message.get("t") != MsgType.AUTH_REQ:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Please authenticate first."
#                 })
#                 return
#             username = message.get("to")
#             password = message.get("body")
#             if not username or not password:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Username and password required."
#                 })
#                 return
#             if auth.verify(username, password) or auth.register(username, password):
#                 self.username = username
#                 token = auth.issue_token(username)
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_OK,
#                     "body": f"Welcome {username}",
#                     "token": token
#                 })
#                 self.server.register_client(username, self)
#             else:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Authentication failed."
#                 })
#         else:
#             # Chat phase.
#             if message.get("t") == MsgType.CHAT:
#                 asyncio.create_task(self.server.route_message(self.username, message))
#             else:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.SYS,
#                     "body": "Unknown command."
#                 })

#     def send_on_new_stream(self, msg: dict):
#         new_stream = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
#         self.transmit()

#     async def send_message(self, msg: dict):
#         new_stream = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
#         self.transmit()


# async def shutdown_listener():
#     """Waits for the user to type 'quit' in the server terminal to shut down."""
#     loop = asyncio.get_running_loop()
#     while True:
#         line = await loop.run_in_executor(None, sys.stdin.readline)
#         if line.strip().lower() == "quit":
#             logging.info("Shutdown command received. Exiting server.")
#             for task in asyncio.all_tasks(loop):
#                 if task is not asyncio.current_task():
#                     task.cancel()
#             break


# async def main():
#     chat = ChatServer()
#     config = QuicConfiguration(is_client=False, alpn_protocols=["chat/1"])
#     config.load_cert_chain("ssl/cert.pem", "ssl/key.pem")
#     logging.info("Starting QUIC chat server on port 4433...")
#     quic_server = await serve("0.0.0.0", 4433, configuration=config,
#                               create_protocol=lambda *args, **kwargs: ChatProtocol(*args, server=chat, **kwargs))
#     shutdown_task = asyncio.create_task(shutdown_listener())
#     try:
#         await shutdown_task
#     except asyncio.CancelledError:
#         pass
#     quic_server.close()
#     await quic_server.wait_closed()
#     logging.info("Server shut down gracefully.")


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         logging.info("Server terminated by KeyboardInterrupt.")





#!/usr/bin/env python3
"""
Asynchronous QUIC Chat Server

Features:
• Upon successful client authentication, notifies all connected clients (via a SYS message)
  that a new user has joined and broadcasts an updated online users list.
• When a client disconnects, notifies the remaining clients.
• Broadcasts public messages and delivers private messages when a message begins with “@username”.
• Logs QUIC handshake stages (shows connection ID when available and the negotiated ALPN).
• Can handle N clients concurrently.
"""

import asyncio
import logging
from typing import Dict

from aioquic.asyncio import serve, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import HandshakeCompleted, StreamDataReceived, ConnectionTerminated

from protocol import MsgType, pack, unpack
import auth

logging.basicConfig(level=logging.INFO)


class ChatServer:
    def __init__(self):
        # Mapping from username to its ChatProtocol instance
        self.clients: Dict[str, ChatProtocol] = {}

    def register_client(self, username: str, protocol: "ChatProtocol"):
        self.clients[username] = protocol
        logging.info(f"User '{username}' connected. Online: {list(self.clients.keys())}")
        self.broadcast_system_message(f"User '{username}' joined the chat.")
        self.broadcast_online_users()

    def unregister_client(self, username: str):
        if username in self.clients:
            del self.clients[username]
            logging.info(f"User '{username}' disconnected. Online: {list(self.clients.keys())}")
            self.broadcast_system_message(f"User '{username}' left the chat.")
            self.broadcast_online_users()

    def broadcast_system_message(self, message: str):
        """Broadcast a system (SYS) message to all connected clients."""
        msg = {
            "v": 1,
            "t": MsgType.SYS,
            "body": message
        }
        for client in self.clients.values():
            asyncio.create_task(client.send_message(msg))

    def broadcast_online_users(self):
        """Broadcast the current online users list to everyone."""
        online = ", ".join(self.clients.keys()) if self.clients else "None"
        msg = {
            "v": 1,
            "t": MsgType.SYS,
            "body": f"Online users: {online}"
        }
        for client in self.clients.values():
            asyncio.create_task(client.send_message(msg))

    async def route_message(self, sender: str, message: dict):
        """
        Routes a CHAT message:
          - If the message body starts with '@', treats it as private.
          - Otherwise, broadcasts it to all other clients.
        """
        body = message.get("body", "")
        if body.startswith("@"):
            parts = body.split(" ", 1)
            if len(parts) < 2:
                err = {
                    "v": 1,
                    "t": MsgType.SYS,
                    "body": "Invalid private message format. Use '@username message'."
                }
                if sender in self.clients:
                    await self.clients[sender].send_message(err)
                return

            target = parts[0][1:]
            text = parts[1]
            if target in self.clients:
                private_msg = {
                    "v": 1,
                    "t": MsgType.CHAT,
                    "body": f"[Private] {sender}: {text}"
                }
                await self.clients[target].send_message(private_msg)
                # Optionally, acknowledge to sender:
                confirm = {
                    "v": 1,
                    "t": MsgType.CHAT,
                    "body": f"[Private to {target}] {text}"
                }
                await self.clients[sender].send_message(confirm)
            else:
                err = {
                    "v": 1,
                    "t": MsgType.SYS,
                    "body": f"User '{target}' is not online."
                }
                await self.clients[sender].send_message(err)
        else:
            # Public message: send to all clients except the sender.
            public_msg = {
                "v": 1,
                "t": MsgType.CHAT,
                "body": f"{sender}: {body}"
            }
            for user, client in self.clients.items():
                if user != sender:
                    await client.send_message(public_msg)


class ChatProtocol(QuicConnectionProtocol):
    """One instance per client connection."""
    def __init__(self, *args, server: ChatServer = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.server = server
        self.username = None

    def quic_event_received(self, event) -> None:
        if isinstance(event, HandshakeCompleted):
            # Log handshake details. Use try/except in case connection_id isn’t available.
            try:
                cid = self._quic.connection_id.hex()
            except Exception:
                cid = "unknown"
            logging.info(f"[HS] Handshake completed: CID={cid}, ALPN={event.alpn_protocol}")
        elif isinstance(event, StreamDataReceived):
            self.handle_stream_data(event.stream_id, event.data, event.end_stream)
        elif isinstance(event, ConnectionTerminated):
            # When the connection terminates, if the client was authenticated, unregister it.
            if self.username:
                self.server.unregister_client(self.username)

    def handle_stream_data(self, stream_id: int, data: bytes, end_stream: bool):
        message = unpack(data)
        if self.username is None:
            # Expect authentication message (AUTH_REQ)
            if message.get("t") != MsgType.AUTH_REQ:
                self.send_on_new_stream({
                    "v": 1,
                    "t": MsgType.AUTH_BAD,
                    "body": "Please authenticate first using AUTH_REQ."
                })
                return
            username = message.get("to")
            password = message.get("body")
            if not username or not password:
                self.send_on_new_stream({
                    "v": 1,
                    "t": MsgType.AUTH_BAD,
                    "body": "Username and password required."
                })
                return
            if auth.verify(username, password) or auth.register(username, password):
                self.username = username
                token = auth.issue_token(username)
                self.send_on_new_stream({
                    "v": 1,
                    "t": MsgType.AUTH_OK,
                    "body": f"Welcome, {username}",
                    "token": token
                })
                self.server.register_client(username, self)
            else:
                self.send_on_new_stream({
                    "v": 1,
                    "t": MsgType.AUTH_BAD,
                    "body": "Authentication failed."
                })
        else:
            # In the chat phase, route CHAT messages.
            if message.get("t") == MsgType.CHAT:
                asyncio.create_task(self.server.route_message(self.username, message))
            else:
                self.send_on_new_stream({
                    "v": 1,
                    "t": MsgType.SYS,
                    "body": "Unknown command."
                })

    def send_on_new_stream(self, msg: dict):
        new_stream = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
        self.transmit()

    async def send_message(self, msg: dict):
        new_stream = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
        self.transmit()


async def main():
    chat_server = ChatServer()
    config = QuicConfiguration(is_client=False, alpn_protocols=["chat/1"])
    config.load_cert_chain("ssl/cert.pem", "ssl/key.pem")
    logging.info("Starting QUIC chat server on port 4433...")
    # Start the server. The created protocol will have a pointer to our ChatServer instance.
    await serve("0.0.0.0", 4433, configuration=config,
                create_protocol=lambda *args, **kwargs: ChatProtocol(*args, server=chat_server, **kwargs))
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server terminated by KeyboardInterrupt.")
