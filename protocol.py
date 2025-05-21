# protocol.py
import json
from enum import IntEnum

class MsgType(IntEnum):
    AUTH_REQ = 0  # Client authentication request.
    AUTH_OK  = 1  # Server authentication success.
    AUTH_BAD = 2  # Authentication failure.
    CHAT     = 3  # Chat messages.
    SYS      = 4  # System messages (e.g., online users updates).

def pack(msg: dict) -> bytes:
    return json.dumps(msg).encode("utf-8")

def unpack(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))
