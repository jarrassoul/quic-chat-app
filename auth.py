# auth.py
import time
import bcrypt
from jose import jwt  # Ensure python-jose[bcrypt] is installed

_SECRET = "your-very-secret-key"  # In production, load securely (e.g., via environment variables)
_ALGORITHM = "HS256"
_EXPIRATION = 3600  # Token expiration in seconds

# In-memory user store: username → hashed password
_users = {}

def register(username: str, password: str) -> bool:
    if username in _users:
        return False
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    _users[username] = hashed
    return True

def verify(username: str, password: str) -> bool:
    hashed = _users.get(username)
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed)

def issue_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + _EXPIRATION}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)

def validate(token: str) -> str or None:
    try:
        data = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return data.get("sub")
    except Exception:
        return None
