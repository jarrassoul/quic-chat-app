


# #!/usr/bin/env python3
# """
# QUIC Chat Client

# Features:
# • Prompts the user for a username and password, then sends an AUTH_REQ.
# • Listens for incoming messages and displays both public and system messages.
# • When the user types a message:
#     – If the message begins with "@username", it is sent as a private message.
#     – Otherwise it is broadcast publicly.
# • Typing "quit" will exit the client gracefully.
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
#     config.verify_mode = False  # Accept self-signed certificate

#     async with connect("localhost", 4433, configuration=config, create_protocol=ChatClientProtocol) as client:
#         protocol: ChatClientProtocol = client
#         # Send authentication request
#         auth_msg = {"v": 1, "t": MsgType.AUTH_REQ, "body": password, "to": username, "token": None}
#         await protocol.send_message(auth_msg)
#         print("Waiting for authentication response...")
#         await asyncio.sleep(1)  # give time for the server reply
#         print("You can now chat. Type 'quit' to exit.")

#         loop = asyncio.get_event_loop()
#         while True:
#             line = await loop.run_in_executor(None, sys.stdin.readline)
#             if not line:
#                 continue
#             line = line.strip()
#             if line.lower() == "quit":
#                 print("Exiting client...")
#                 break
#             # Build the message. If it starts with "@", the server will parse and route it as a private message.
#             msg = {"v": 1, "t": MsgType.CHAT, "body": line, "to": None, "token": None}
#             await protocol.send_message(msg)

# if __name__ == "__main__":
#     try:
#         asyncio.run(run_client())
#     except KeyboardInterrupt:
#         print("Client terminated by KeyboardInterrupt.")





#!/usr/bin/env python3
"""
Asynchronous QUIC Chat Client

Features:
 • Connects to the QUIC chat server using a client-side QUIC configuration.
 • Prompts for a username and password and sends an authentication request.
 • Remains active, reading user input and sending each message on a new stream,
   until the user explicitly types '/quit'.
 • Supports public broadcast messages as well as private messages (type '@username message').
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
                print(f"\n[SYSTEM] {message.get('body')}")
                self.token = message.get("token")
            elif t == MsgType.AUTH_BAD:
                print(f"\n[AUTH ERROR] {message.get('body')}")
            elif t == MsgType.CHAT:
                print(f"\n{message.get('body')}")
            elif t == MsgType.SYS:
                print(f"\n[SYSTEM] {message.get('body')}")
            else:
                print(f"\n[UNKNOWN] {message}")

    async def send_message(self, msg: dict):
        new_stream = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(new_stream, pack(msg), end_stream=True)
        self.transmit()

async def main():
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    config = QuicConfiguration(is_client=True, alpn_protocols=["chat/1"])
    # Accept self-signed certificate.
    config.verify_mode = 0  # equivalent to ssl.CERT_NONE

    async with connect("localhost", 4433, configuration=config, create_protocol=ChatClientProtocol) as protocol:
        # Send authentication message.
        auth_msg = {"v": 1, "t": MsgType.AUTH_REQ, "to": username, "body": password, "token": None}
        await protocol.send_message(auth_msg)
        # Wait a short time for auth reply.
        await asyncio.sleep(1)
        if not hasattr(protocol, "token") or protocol.token is None:
            print("Authentication failed, exiting.")
            return
        print("Logged in. You may now start chatting. Type '/quit' to exit.")
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                continue
            line = line.strip()
            if line.lower() == "/quit":
                print("Exiting chat.")
                break
            msg_out = {"v": 1, "t": MsgType.CHAT, "body": line, "to": None, "token": protocol.token}
            if line.startswith("@"):
                parts = line.split(" ", 1)
                if len(parts) != 2:
                    print("Invalid private message format. Use '@username message'")
                    continue
                msg_out["to"] = parts[0][1:]
                msg_out["body"] = parts[1]
            await protocol.send_message(msg_out)

if __name__ == "__main__":
    asyncio.run(main())
