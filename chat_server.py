


# #!/usr/bin/env python3
# """
# Asynchronous QUIC Chat Server

# Features:
# • Upon successful client authentication, notifies all connected clients (via a SYS message)
#   that a new user has joined and broadcasts an updated online users list.
# • When a client disconnects, notifies the remaining clients.
# • Broadcasts public messages and delivers private messages when a message begins with “@username”.
# • Logs QUIC handshake stages (shows connection ID when available and the negotiated ALPN).
# • Can handle N clients concurrently.
# """

# import asyncio
# import logging
# from typing import Dict

# from aioquic.asyncio import serve, QuicConnectionProtocol
# from aioquic.quic.configuration import QuicConfiguration
# from aioquic.quic.events import HandshakeCompleted, StreamDataReceived, ConnectionTerminated

# from protocol import MsgType, pack, unpack
# import auth

# logging.basicConfig(level=logging.INFO)


# class ChatServer:
#     def __init__(self):
#         # Mapping from username to its ChatProtocol instance
#         self.clients: Dict[str, ChatProtocol] = {}

#     def register_client(self, username: str, protocol: "ChatProtocol"):
#         self.clients[username] = protocol
#         logging.info(f"User '{username}' connected. Online: {list(self.clients.keys())}")
#         self.broadcast_system_message(f"User '{username}' joined the chat.")
#         self.broadcast_online_users()

#     def unregister_client(self, username: str):
#         if username in self.clients:
#             del self.clients[username]
#             logging.info(f"User '{username}' disconnected. Online: {list(self.clients.keys())}")
#             self.broadcast_system_message(f"User '{username}' left the chat.")
#             self.broadcast_online_users()

#     def broadcast_system_message(self, message: str):
#         """Broadcast a system (SYS) message to all connected clients."""
#         msg = {
#             "v": 1,
#             "t": MsgType.SYS,
#             "body": message
#         }
#         for client in self.clients.values():
#             asyncio.create_task(client.send_message(msg))

#     def broadcast_online_users(self):
#         """Broadcast the current online users list to everyone."""
#         online = ", ".join(self.clients.keys()) if self.clients else "None"
#         msg = {
#             "v": 1,
#             "t": MsgType.SYS,
#             "body": f"Online users: {online}"
#         }
#         for client in self.clients.values():
#             asyncio.create_task(client.send_message(msg))

#     async def route_message(self, sender: str, message: dict):
#         """
#         Routes a CHAT message:
#           - If the message body starts with '@', treats it as private.
#           - Otherwise, broadcasts it to all other clients.
#         """
#         body = message.get("body", "")
#         if body.startswith("@"):
#             parts = body.split(" ", 1)
#             if len(parts) < 2:
#                 err = {
#                     "v": 1,
#                     "t": MsgType.SYS,
#                     "body": "Invalid private message format. Use '@username message'."
#                 }
#                 if sender in self.clients:
#                     await self.clients[sender].send_message(err)
#                 return

#             target = parts[0][1:]
#             text = parts[1]
#             if target in self.clients:
#                 private_msg = {
#                     "v": 1,
#                     "t": MsgType.CHAT,
#                     "body": f"[Private] {sender}: {text}"
#                 }
#                 await self.clients[target].send_message(private_msg)
#                 # Optionally, acknowledge to sender:
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
#                     "body": f"User '{target}' is not online."
#                 }
#                 await self.clients[sender].send_message(err)
#         else:
#             # Public message: send to all clients except the sender.
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
#             # Log handshake details. Use try/except in case connection_id isn’t available.
#             try:
#                 cid = self._quic.connection_id.hex()
#             except Exception:
#                 cid = "unknown"
#             logging.info(f"[HS] Handshake completed: CID={cid}, ALPN={event.alpn_protocol}")
#         elif isinstance(event, StreamDataReceived):
#             self.handle_stream_data(event.stream_id, event.data, event.end_stream)
#         elif isinstance(event, ConnectionTerminated):
#             # When the connection terminates, if the client was authenticated, unregister it.
#             if self.username:
#                 self.server.unregister_client(self.username)

#     def handle_stream_data(self, stream_id: int, data: bytes, end_stream: bool):
#         message = unpack(data)
#         if self.username is None:
#             # Expect authentication message (AUTH_REQ)
#             if message.get("t") != MsgType.AUTH_REQ:
#                 self.send_on_new_stream({
#                     "v": 1,
#                     "t": MsgType.AUTH_BAD,
#                     "body": "Please authenticate first using AUTH_REQ."
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
#                     "body": f"Welcome, {username}",
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
#             # In the chat phase, route CHAT messages.
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


# async def main():
#     chat_server = ChatServer()
#     config = QuicConfiguration(is_client=False, alpn_protocols=["chat/1"])
#     config.load_cert_chain("ssl/cert.pem", "ssl/key.pem")
#     logging.info("Starting QUIC chat server on port 4433...")
#     # Start the server. The created protocol will have a pointer to our ChatServer instance.
#     await serve("0.0.0.0", 4433, configuration=config,
#                 create_protocol=lambda *args, **kwargs: ChatProtocol(*args, server=chat_server, **kwargs))
#     await asyncio.Future()  # Run forever

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         logging.info("Server terminated by KeyboardInterrupt.")




#!/usr/bin/env python3
"""
Asynchronous QUIC Chat Server

Features:
 • Logs QUIC handshake stages (prints connection ID and negotiated ALPN).
 • Expects an initial authentication (AUTH_REQ) and issues a JWT token upon success.
 • Immediately registers the client and broadcasts a system message along with
   the updated online-user list.
 • Routes chat messages:
    - If the message body starts with "@username", it is treated as a private message.
    - Otherwise, the message is broadcast to all other connected clients.
 • Every outgoing message is sent on a fresh stream to prevent write-after-FIN errors.
 • Supports simultaneous connections.
"""

import asyncio
import logging
from typing import Dict, Optional

from aioquic.asyncio import serve, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import HandshakeCompleted, StreamDataReceived, ConnectionTerminated
from protocol import MsgType, pack, unpack
import auth

logging.basicConfig(level=logging.INFO)


class ChatProtocol(QuicConnectionProtocol):
    def __init__(self, *args, server_ref: "ChatServer" = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_ref = server_ref
        self.username: Optional[str] = None
        self.token: Optional[str] = None

    def quic_event_received(self, event) -> None:
        if isinstance(event, HandshakeCompleted):
            try:
                cid = self._quic.connection_id.hex()
            except Exception:
                cid = "unknown"
            logging.info(f"[HS] Handshake completed: CID={cid}, ALPN={event.alpn_protocol}")
        elif isinstance(event, StreamDataReceived):
            self.handle_stream_data(event.stream_id, event.data, event.end_stream)
        elif isinstance(event, ConnectionTerminated):
            if self.username:
                self.server_ref.unregister_client(self.username)

    def handle_stream_data(self, stream_id: int, data: bytes, end_stream: bool):
        message = unpack(data)
        # --- Authentication Phase ---
        if self.username is None:
            if message.get("t") != MsgType.AUTH_REQ:
                # Using a new stream to send the error.
                asyncio.create_task(self.async_send(MsgType.AUTH_BAD, "Please authenticate first."))
                return
            username = message.get("to")
            password = message.get("body")
            if not username or not password:
                asyncio.create_task(self.async_send(MsgType.AUTH_BAD, "Username and password required."))
                return
            if auth.verify(username, password) or auth.register(username, password):
                self.username = username
                self.token = auth.issue_token(username)
                asyncio.create_task(self.async_send(MsgType.AUTH_OK, f"Welcome, {username}", token=self.token))
                self.server_ref.register_client(username, self)
            else:
                asyncio.create_task(self.async_send(MsgType.AUTH_BAD, "Authentication failed."))
        else:
            # --- Chat Phase ---
            if message.get("t") == MsgType.CHAT:
                body = message.get("body", "")
                # Check for private message syntax.
                if body.startswith("@"):
                    parts = body.split(" ", 1)
                    if len(parts) != 2:
                        asyncio.create_task(self.async_send(MsgType.SYS, "Invalid private message format. Use '@username message'."))
                        return
                    message["to"] = parts[0][1:]  # strip the '@'
                    message["body"] = parts[1]
                asyncio.create_task(self.server_ref.route_message(self.username, message))
            else:
                asyncio.create_task(self.async_send(MsgType.SYS, "Unknown command."))

    async def async_send(self, t: MsgType, body: str, to: Optional[str] = None, token: Optional[str] = None):
        """
        Sends a message on a new stream.
        Using a freshly allocated stream for each outgoing message avoids write-after-FIN errors.
        """
        new_stream = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(
            new_stream,
            pack({"v": 1, "t": int(t), "body": body, "to": to, "token": token}),
            end_stream=True
        )
        self.transmit()

        
class ChatServer:
    def __init__(self):
        # Mapping from username to its ChatProtocol instance.
        self.clients: Dict[str, ChatProtocol] = {}

    def register_client(self, username: str, protocol: ChatProtocol):
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
        for client in self.clients.values():
            asyncio.create_task(client.async_send(MsgType.SYS, message))

    def broadcast_online_users(self):
        online_list = ", ".join(self.clients.keys()) if self.clients else "None"
        msg = f"Online users: {online_list}"
        for client in self.clients.values():
            asyncio.create_task(client.async_send(MsgType.SYS, msg))

    async def route_message(self, sender: str, msg: dict):
        body = msg.get("body", "")
        target = msg.get("to")
        if target:
            # Private message: send to the target if online.
            if target in self.clients:
                await self.clients[target].async_send(MsgType.CHAT, f"[Private] {sender}: {body}")
                await self.clients[sender].async_send(MsgType.CHAT, f"[Private to {target}] {body}")
            else:
                await self.clients[sender].async_send(MsgType.SYS, f"User '{target}' is not online.")
        else:
            # Public message: broadcast to all except the sender.
            for user, client in self.clients.items():
                if user != sender:
                    await client.async_send(MsgType.CHAT, f"{sender}: {body}")


async def main():
    chat_server = ChatServer()
    config = QuicConfiguration(is_client=False, alpn_protocols=["chat/1"])
    config.load_cert_chain("ssl/cert.pem", "ssl/key.pem")
    logging.info("Starting QUIC chat server on port 4433...")
    # Note: No separate ssl_context parameter is needed; certificates are loaded into the configuration.
    await serve("0.0.0.0", 4433, configuration=config,
                create_protocol=lambda *a, **kw: ChatProtocol(*a, server_ref=chat_server, **kw))
    await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server terminated by KeyboardInterrupt.")
