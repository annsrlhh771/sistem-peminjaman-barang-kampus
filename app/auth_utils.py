import os
import datetime
import jwt
import bcrypt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "secret-default-ganti-di-env")
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 24 * 7  # 7 hari

def hash_password(password: str) -> str:
    """Hash password pakai bcrypt, return string."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Cek password cocok dengan hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_token(payload: dict) -> str:
    """Buat JWT token."""
    data = payload.copy()
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode JWT token, raise kalau invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])