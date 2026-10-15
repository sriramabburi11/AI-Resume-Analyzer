import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
import jwt
from fastapi import HTTPException, status, Header, Cookie, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User

ph = PasswordHasher()

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SESSION_SECRET") or "ai-resume-analyzer-secure-jwt-secret-key-change-in-production-2026"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))) # 7 days

def hash_password(password: str) -> str:
    """Hashes a password using Argon2id."""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        # Fallback to bcrypt if hash is in bcrypt format
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception:
                return False
        return False

def create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token for authentication."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def generate_random_token() -> str:
    """Generates a secure cryptographically random token string."""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hashes a token string for secure DB lookup."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def get_current_user(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that extracts and validates the Bearer token or HttpOnly session cookie.
    Derives the authenticated user from the database.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    elif session_token:
        token = session_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Allow mock tokens during isolated unit tests if enabled
    if os.getenv("ALLOW_MOCK_AUTH", "").lower() in ("true", "1") and token.startswith("mock_token_"):
        user_id = token.replace("mock_token_", "")
        mock_user = db.query(User).filter(User.id == user_id).first()
        if not mock_user:
            # Create transient mock user for test
            mock_user = User(
                id=user_id,
                full_name="Test User",
                email=f"{user_id}@example.com",
                password_hash=hash_password("testpass123")
            )
            db.add(mock_user)
            db.commit()
            db.refresh(mock_user)
        return mock_user

    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
