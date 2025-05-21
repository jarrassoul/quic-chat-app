# #!/usr/bin/env python3
# """
# QUIC Chat Client
# ----------------
# Features:
# • Connects securely using QUIC.
# • Prompts the user for a username and password.
# • Sends an authentication (AUTH_REQ) message.
# • Reads incoming messages (both CHAT and SYS) and prints them.
# • Allows the user to type messages:
#     – A line beginning with “@username” is treated as a private message.
#     – All other lines are broadcast publicly.
# • Type “/quit” to exit.
# """

# import asyncio
# import sys
# import json
# import ssl
# from aioquic.asyncio import connect, QuicConnectionProtocol
# from aioquic.quic.configuration import QuicConfiguration

# # Message type definitions (should match the server)
# class MsgType:
#     AUTH_REQ = 0
#     AUTH_OK  = 1
#     AUTH_BAD = 2
#     CHAT     = 3
#     SYS      = 4

# def pack(msg: dict) -> bytes:
#     return json.dumps(msg).encode()

# def unpack(data: bytes) -> dict:
#     return json.loads(data.decode())

# # Client protocol handles incoming events.
# class ChatClientProtocol(QuicConnectionProtocol):
#     def quic_event_received(self, event) -> None:
#         from aioquic.quic.events import StreamDataReceived
#         if isinstance(event, StreamDataReceived):
#             try:
#                 msg = unpack(event.data)
#             except Exception as e:
#                 print("Failed to decode message:", e)
#                 return
#             t = msg.get("t")
#             if t == MsgType.AUTH_OK:
#                 print(f"\n[SYSTEM] {msg.get('body')}")
#             elif t == MsgType.AUTH_BAD:
#                 print(f"\n[AUTH ERROR] {msg.get('body')}")
#             elif t == MsgType.CHAT:
#                 print(f"\n{msg.get('body')}")
#             elif t == MsgType.SYS:
#                 print(f"\n[SYSTEM] {msg.get('body')}")
#             else:
#                 print(f"\n[UNKNOWN] {msg}")

#     async def send_message(self, msg: dict):
#         # Use a new stream so we don’t try writing to a FIN‐ed stream.
#         stream_id = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(stream_id, pack(msg), end_stream=True)
#         self.transmit()

# async def run_client():
#     username = input("Enter username: ").strip()
#     password = input("Enter password: ").strip()

#     config = QuicConfiguration(is_client=True, alpn_protocols=["chat/1"])
#     # For demo purposes, disable certificate verification (self-signed certificate)
#     config.verify_mode = ssl.CERT_NONE

#     async with connect("localhost", 4433, configuration=config, create_protocol=ChatClientProtocol) as client:
#         protocol: ChatClientProtocol = client
#         # Send authentication request: we use the "to" field for the username and "body" for the password.
#         auth_msg = {
#             "v": 1,
#             "t": MsgType.AUTH_REQ,
#             "to": username,
#             "body": password
#         }
#         await protocol.send_message(auth_msg)

#         print("Authenticated (if credentials are accepted).")
#         print("Type your messages below. Prefix with '@username' for a private message. Type /quit to exit.")

#         loop = asyncio.get_event_loop()
#         # Main input loop
#         while True:
#             line = await loop.run_in_executor(None, sys.stdin.readline)
#             if not line:
#                 break
#             line = line.strip()
#             if line.lower() == "/quit":
#                 break
#             msg = {
#                 "v": 1,
#                 "t": MsgType.CHAT,
#                 "body": line
#             }
#             await protocol.send_message(msg)

# if __name__ == "__main__":
#     try:
#         asyncio.run(run_client())
#     except KeyboardInterrupt:
#         pass




# #!/usr/bin/env python3
# """
# QUIC Chat Client

# • Connects to the server using QUIC with TLS.
# • Prompts for username and password.
# • Sends an authentication request.
# • Receives and displays messages:
#     – CHAT messages (broadcast or private)
#     – SYS messages (online users list updates)
# • Type "quit" to exit the client gracefully.
# """

# import asyncio
# import sys
# import logging
# from aioquic.asyncio import connect, QuicConnectionProtocol
# from aioquic.quic.configuration import QuicConfiguration
# from protocol import MsgType, pack, unpack

# logging.basicConfig(level=logging.INFO)


# class ChatClientProtocol(QuicConnectionProtocol):
#     def quic_event_received(self, event) -> None:
#         from aioquic.quic.events import StreamDataReceived
#         if isinstance(event, StreamDataReceived):
#             try:
#                 message = unpack(event.data)
#             except Exception as exc:
#                 logging.error(f"Error decoding message: {exc}")
#                 return
#             t = message.get("t")
#             if t == MsgType.AUTH_OK:
#                 print(f"\n[SYSTEM] {message.get('body')}")
#             elif t == MsgType.AUTH_BAD:
#                 print(f"\n[AUTH ERROR] {message.get('body')}")
#             elif t == MsgType.CHAT:
#                 print(f"\n{message.get('body')}")
#             elif t == MsgType.SYS:
#                 print(f"\n[SYSTEM] {message.get('body')}")
#             else:
#                 print(f"\n[UNKNOWN] {message}")
    
#     async def send_message(self, msg: dict):
#         new_stream = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
#         self.transmit()


# async def run_client():
#     username = input("Enter username: ").strip()
#     password = input("Enter password: ").strip()
    
#     config = QuicConfiguration(is_client=True, alpn_protocols=["chat/1"])
#     # Accept self-signed certificate, if needed
#     config.verify_mode = False
    
#     async with connect("localhost", 4433, configuration=config,
#                        create_protocol=ChatClientProtocol) as client:
#         protocol: ChatClientProtocol = client
#         # Send the authentication request (AUTH_REQ)
#         auth_msg = {
#             "v": 1,
#             "t": MsgType.AUTH_REQ,
#             "to": username,    # username goes in "to"
#             "body": password   # password goes in "body"
#         }
#         await protocol.send_message(auth_msg)
#         print("Authenticated (if credentials are accepted). Type your messages below.")
#         print("Type 'quit' to exit.")
        
#         loop = asyncio.get_running_loop()
#         while True:
#             line = await loop.run_in_executor(None, sys.stdin.readline)
#             if not line:
#                 continue
#             line = line.strip()
#             if line.lower() == "quit":
#                 print("Exiting client...")
#                 break
#             msg = {
#                 "v": 1,
#                 "t": MsgType.CHAT,
#                 "body": line
#             }
#             await protocol.send_message(msg)


# if __name__ == "__main__":
#     try:
#         asyncio.run(run_client())
#     except KeyboardInterrupt:
#         print("Client terminated by KeyboardInterrupt.")




# #!/usr/bin/env python3
# """
# Asynchronous QUIC Chat Client

# Features:
# • Connects to the chat server using QUIC with TLS.
# • Prompts for a username and password, then sends an authentication request.
# • Listens for incoming messages (CHAT and SYS) and displays them.
# • Supports sending public messages or private messages (by prefixing with "@username").
# • Typing "quit" exits the client gracefully.
# """

# import asyncio
# import sys
# import logging
# from aioquic.asyncio import connect, QuicConnectionProtocol
# from aioquic.quic.configuration import QuicConfiguration
# from protocol import MsgType, pack, unpack

# logging.basicConfig(level=logging.INFO)


# class ChatClientProtocol(QuicConnectionProtocol):
#     def quic_event_received(self, event) -> None:
#         from aioquic.quic.events import StreamDataReceived
#         if isinstance(event, StreamDataReceived):
#             try:
#                 message = unpack(event.data)
#             except Exception as e:
#                 logging.error(f"Error decoding message: {e}")
#                 return
#             t = message.get("t")
#             if t == MsgType.AUTH_OK:
#                 print(f"[SYSTEM] {message.get('body')}")
#             elif t == MsgType.AUTH_BAD:
#                 print(f"[AUTH ERROR] {message.get('body')}")
#             elif t == MsgType.CHAT:
#                 print(f"{message.get('body')}")
#             elif t == MsgType.SYS:
#                 print(f"[SYSTEM] {message.get('body')}")
#             else:
#                 print(f"[UNKNOWN] {message}")
    
#     async def send_message(self, msg: dict):
#         new_stream = self._quic.get_next_available_stream_id()
#         self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
#         self.transmit()


# async def run_client():
#     username = input("Enter username: ").strip()
#     password = input("Enter password: ").strip()

#     config = QuicConfiguration(is_client=True, alpn_protocols=["chat/1"])
#     # Accept self-signed certificate
#     config.verify_mode = False

#     async with connect("localhost", 4433, configuration=config, create_protocol=ChatClientProtocol) as client:
#         protocol: ChatClientProtocol = client
#         # Send authentication request (AUTH_REQ)
#         auth_msg = {
#             "v": 1,
#             "t": MsgType.AUTH_REQ,
#             "to": username,
#             "body": password,
#             "token": None
#         }
#         await protocol.send_message(auth_msg)
        
#         print("Waiting for authentication reply...")
#         await asyncio.sleep(1)  # slight delay to let the AUTH reply show in the event handler

#         print("You may now start chatting. Type 'quit' to exit.")
#         loop = asyncio.get_running_loop()
#         while True:
#             line = await loop.run_in_executor(None, sys.stdin.readline)
#             if not line:
#                 continue
#             line = line.strip()
#             if line.lower() == "quit":
#                 print("Exiting client...")
#                 break
#             # Build the message. If it starts with '@', include the "to" field.
#             msg = {
#                 "v": 1,
#                 "t": MsgType.CHAT,
#                 "body": line,
#                 "to": None,
#                 "token": None
#             }
#             if line.startswith("@"):
#                 parts = line.split(" ", 1)
#                 if len(parts) == 2:
#                     msg["to"] = parts[0][1:]  # remove the "@" prefix
#                     msg["body"] = parts[1]
#             await protocol.send_message(msg)

# if __name__ == "__main__":
#     try:
#         asyncio.run(run_client())
#     except KeyboardInterrupt:
#         print("Client terminated by KeyboardInterrupt.")




#!/usr/bin/env python3
"""
QUIC Chat Client

Features:
• Prompts the user for a username and password, then sends an AUTH_REQ.
• Listens for incoming messages and displays both public and system messages.
• When the user types a message:
    – If the message begins with "@username", it is sent as a private message.
    – Otherwise it is broadcast publicly.
• Typing "quit" will exit the client gracefully.
"""

import asyncio
import sys
import logging
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from protocol import MsgType, pack, unpack

logging.basicConfig(level=logging.INFO)


class ChatClientProtocol(QuicConnectionProtocol):
    def quic_event_received(self, event) -> None:
        from aioquic.quic.events import StreamDataReceived
        if isinstance(event, StreamDataReceived):
            try:
                message = unpack(event.data)
            except Exception as e:
                logging.error(f"Error decoding message: {e}")
                return
            t = message.get("t")
            if t == MsgType.AUTH_OK:
                print(f"[SYSTEM] {message.get('body')}")
            elif t == MsgType.AUTH_BAD:
                print(f"[AUTH ERROR] {message.get('body')}")
            elif t == MsgType.CHAT:
                print(f"{message.get('body')}")
            elif t == MsgType.SYS:
                print(f"[SYSTEM] {message.get('body')}")
            else:
                print(f"[UNKNOWN] {message}")

    async def send_message(self, msg: dict):
        new_stream = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
        self.transmit()


async def run_client():
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    config = QuicConfiguration(is_client=True, alpn_protocols=["chat/1"])
    config.verify_mode = False  # Accept self-signed certificate

    async with connect("localhost", 4433, configuration=config, create_protocol=ChatClientProtocol) as client:
        protocol: ChatClientProtocol = client
        # Send authentication request
        auth_msg = {"v": 1, "t": MsgType.AUTH_REQ, "body": password, "to": username, "token": None}
        await protocol.send_message(auth_msg)
        print("Waiting for authentication response...")
        await asyncio.sleep(1)  # give time for the server reply
        print("You can now chat. Type 'quit' to exit.")

        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                continue
            line = line.strip()
            if line.lower() == "quit":
                print("Exiting client...")
                break
            # Build the message. If it starts with "@", the server will parse and route it as a private message.
            msg = {"v": 1, "t": MsgType.CHAT, "body": line, "to": None, "token": None}
            await protocol.send_message(msg)

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("Client terminated by KeyboardInterrupt.")
