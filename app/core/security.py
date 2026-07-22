import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from cryptography.fernet import Fernet
import bcrypt
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    pwd_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    subject: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token with an expiration timestamp."""
    to_encode = subject.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    return jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM]
    )


def _get_fernet() -> Fernet:
    """Helper to initialize Fernet cipher using configured PII secret key."""
    key = settings.PII_SECRET_KEY
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key
    if len(key_bytes) != 44:
        key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
    return Fernet(key_bytes)


def encrypt_pii(plain_text: str) -> str:
    """Encrypt PII data (e.g., DNI or phone number) using AES-256 (Fernet)."""
    if not plain_text:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plain_text.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_pii(encrypted_text: str) -> str:
    """Decrypt PII data using AES-256 (Fernet)."""
    if not encrypted_text:
        return ""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_text.encode("utf-8"))
    return decrypted.decode("utf-8")


def hash_dni_hmac(dni: str) -> str:
    """Generate a deterministic HMAC-SHA256 hash for fast, secure DNI indexing."""
    cleaned_dni = "".join(filter(str.isdigit, str(dni)))
    salt_bytes = settings.DNI_HMAC_SALT.encode("utf-8")
    dni_bytes = cleaned_dni.encode("utf-8")
    return hmac.new(salt_bytes, dni_bytes, hashlib.sha256).hexdigest()


def mask_dni(dni: str) -> str:
    """Mask DNI format to XX.XXX.789 for non-administrative views."""
    cleaned = "".join(filter(str.isdigit, str(dni)))
    if len(cleaned) < 3:
        return "***"
    last_three = cleaned[-3:]
    return f"XX.XXX.{last_three}"


def mask_phone(phone: str) -> str:
    """Mask phone format to XXXX-XX1234 for non-administrative views."""
    cleaned = "".join(filter(str.isdigit, str(phone)))
    if len(cleaned) < 4:
        return "****"
    last_four = cleaned[-4:]
    return f"XXXX-XX{last_four}"
