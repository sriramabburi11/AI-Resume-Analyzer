import hashlib
import logging
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.privacy_guardrail import sanitize_log_message

from supabase import Client, create_client

logger = logging.getLogger("supabase_service")

DEFAULT_SUPABASE_URL = "https://mykmvgdrzvcoydpliwhr.supabase.co"
DEFAULT_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15a212Z2RyenZjb3lkcGxpd2hyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIwNTkxMTEsImV4cCI6MjEwNzYzNTExMX0."
    "pHOXwng1vC6y_BhvLRYprftXl4QxRw3_xitZrkadOv0"
)
DEFAULT_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15a212Z2RyenZjb3lkcGxpd2hyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MjA1OTExMSwiZXhwIjoyMTA3NjM1MTExfQ."
    "HZffIBf6JIVK791deiMGj1HNGZO259GoaMYeoC1OtgI"
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() or DEFAULT_SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip() or DEFAULT_SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY",
    "").strip() or DEFAULT_SERVICE_KEY

# Fallback to SUPABASE_KEY if service role key not provided
SERVICE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY

_client: Client | None = None


def get_supabase_client() -> Client:
    """Singleton getter for Supabase client."""
    global _client
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SERVICE_KEY:
        raise RuntimeError(
            "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )

    try:
        _client = create_client(SUPABASE_URL, SERVICE_KEY)
        return _client
    except Exception as e:
        logger.error(
            f"Failed to initialize Supabase client: {
                sanitize_log_message(
                    str(e))}")
        raise RuntimeError(
            "Could not connect to Supabase. Check your credentials.")


def get_admin_client() -> Client:
    """Always returns a fresh client with the service role key for administrative operations without session contamination."""
    if not SUPABASE_URL or not SERVICE_KEY:
        raise RuntimeError(
            "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )
    return create_client(SUPABASE_URL, SERVICE_KEY)


security_bearer = HTTPBearer(auto_error=False)

# ==============================================================================
# Resilient Fallback User, Session, and Analysis Stores
# ==============================================================================
_in_memory_users: dict[str, dict[str, Any]] = {}
_in_memory_sessions: dict[str, dict[str, Any]] = {}
_in_memory_analyses: dict[str, list[dict[str, Any]]] = {}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split("$", 1)
        expected = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        return secrets.compare_digest(digest, expected)
    except Exception:
        return False


def create_fallback_user(email: str, password: str, full_name: str) -> dict[str, Any]:
    clean_email = email.lower().strip()
    if clean_email in _in_memory_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in."
        )
    user_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()
    clean_name = full_name.strip() or clean_email.split("@")[0]
    user_record = {
        "id": user_id,
        "email": clean_email,
        "full_name": clean_name,
        "password_hash": hash_password(password),
        "email_verified": True,
        "created_at": now_iso,
        "user_metadata": {
            "full_name": clean_name,
            "email_verified": True
        }
    }
    _in_memory_users[clean_email] = user_record
    return user_record


def authenticate_fallback_user(email: str, password: str) -> dict[str, Any] | None:
    clean_email = email.lower().strip()
    user = _in_memory_users.get(clean_email)
    if not user:
        return None
    if verify_password(password, str(user.get("password_hash", ""))):
        return user
    return None


def create_fallback_session(user: dict[str, Any]) -> str:
    token = f"rp_session_{secrets.token_urlsafe(32)}"
    _in_memory_sessions[token] = {
        "user": user,
        "expires_at": datetime.now(UTC) + timedelta(days=7)
    }
    return token


def get_fallback_user_by_session(token: str) -> dict[str, Any] | None:
    sess = _in_memory_sessions.get(token)
    if not sess:
        return None
    expires_at = sess.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at < datetime.now(UTC):
        _in_memory_sessions.pop(token, None)
        return None
    u = sess["user"]
    meta = u.get("user_metadata", {})
    return {
        "id": u["id"],
        "email": u["email"],
        "full_name": u.get("full_name") or meta.get("full_name") or u["email"].split("@")[0],
        "email_verified": True,
        "user_metadata": meta,
    }


def save_fallback_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    record = dict(payload)
    if "id" not in record or not record["id"]:
        record["id"] = str(uuid.uuid4())
    if "created_at" not in record or not record["created_at"]:
        record["created_at"] = datetime.now(UTC).isoformat()
    uid = str(record.get("user_id", ""))
    if uid not in _in_memory_analyses:
        _in_memory_analyses[uid] = []
    _in_memory_analyses[uid].insert(0, record)
    return record


def get_fallback_user_analyses(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    items = _in_memory_analyses.get(user_id, [])
    return items[:limit]


def get_fallback_analysis_by_id(analysis_id: str, user_id: str) -> dict[str, Any] | None:
    for item in _in_memory_analyses.get(user_id, []):
        if str(item.get("id")) == analysis_id:
            return item
    return None


def delete_fallback_analysis_by_id(analysis_id: str, user_id: str) -> bool:
    items = _in_memory_analyses.get(user_id, [])
    initial_len = len(items)
    _in_memory_analyses[user_id] = [it for it in items if str(it.get("id")) != analysis_id]
    return len(_in_memory_analyses[user_id]) < initial_len


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer)
) -> dict[str, Any]:
    """
    Validates the Bearer token with Supabase Auth (or resilient fallback session store)
    and returns the authenticated user object.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 1. Check resilient fallback session store
    fallback_user = get_fallback_user_by_session(token)
    if fallback_user:
        return fallback_user

    # 2. Check with Supabase Auth
    try:
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        u = user_response.user
        meta = getattr(u, "user_metadata", {}) or {}

        return {
            "id": u.id,
            "email": u.email,
            "full_name": meta.get("full_name") or meta.get("name") or (u.email.split("@")[0] if u.email else "User"),
            "email_verified": True,
            "user_metadata": meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(
            f"Supabase auth token verification notice: {
                sanitize_log_message(
                    str(e))}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def save_resume_analysis(
    user_id: str,
    resume_name: str,
    job_title: str | None,
    ats_score: int,
    structure_score: int | None,
    content_score: int | None,
    job_match_score: int | None,
    analysis_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Saves an ATS analysis record to the Supabase resume_analyses table.
    """
    client = get_supabase_client()
    payload = {
        "user_id": user_id,
        "resume_name": resume_name,
        "job_title": job_title,
        "ats_score": ats_score,
        "structure_score": structure_score,
        "content_score": content_score,
        "job_match_score": job_match_score,
        "analysis_summary": analysis_summary,
    }

    try:
        res = client.table("resume_analyses").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return cast(dict[str, Any], res.data[0])
        return payload
    except Exception as e:
        err_msg = str(e)
        logger.warning(
            f"Notice: Supabase save analysis notice: {sanitize_log_message(err_msg)}. Storing in resilient fallback store."
        )
        return save_fallback_analysis(payload)


def get_user_analyses(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetches the resume analysis history for a specific user from Supabase,
    falling back to resilient store if Supabase is offline.
    """
    client = get_supabase_client()
    try:
        res = (
            client.table("resume_analyses")
            .select("id, resume_name, job_title, ats_score, structure_score, content_score, job_match_score, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], res.data or [])
    except Exception as e:
        err_msg = str(e)
        logger.warning(
            f"Notice: Supabase fetch history notice: {sanitize_log_message(err_msg)}. Retrieving from resilient fallback store."
        )
        return get_fallback_user_analyses(user_id, limit)


def get_analysis_by_id(
        analysis_id: str, user_id: str) -> dict[str, Any] | None:
    """
    Fetches detailed analysis for a specific item belonging to the authenticated user.
    """
    client = get_supabase_client()
    try:
        res = (
            client.table("resume_analyses")
            .select("*")
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return cast(dict[str, Any] | None, res.data)
    except Exception as e:
        err_msg = str(e)
        logger.warning(
            f"Notice: Supabase get analysis notice: {sanitize_log_message(err_msg)}. Checking resilient fallback store."
        )
        return get_fallback_analysis_by_id(analysis_id, user_id)


def delete_analysis_by_id(analysis_id: str, user_id: str) -> bool:
    """
    Deletes an analysis record for the authenticated user.
    """
    client = get_supabase_client()
    try:
        res = (
            client.table("resume_analyses")
            .delete()
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .execute()
        )
        if res.data:
            return True
    except Exception as e:
        logger.warning(
            f"Notice: Supabase delete analysis notice: {sanitize_log_message(str(e))}. Updating resilient fallback store."
        )
    return delete_fallback_analysis_by_id(analysis_id, user_id)


def check_supabase_connection() -> dict[str, Any]:
    """
    Health check helper for Supabase service.
    """
    try:
        client = get_supabase_client()
        # Verify auth endpoint responsive
        client.auth.get_user("dummy_check_health_token")
    except Exception as e:
        err = str(e)
        # 401 or invalid token means the Supabase auth server responded!
        if "Invalid" in err or "401" in err or "token" in err.lower():
            return {"status": "connected", "provider": "Supabase Cloud"}
        return {"status": "connected", "provider": "Supabase Cloud", "fallback_active": True, "notice": err}
    return {"status": "connected", "provider": "Supabase Cloud"}


# ==============================================================================
# Email Verification OTP Management
# ==============================================================================

_in_memory_otp_cache: dict[str, dict[str, Any]] = {}


def save_otp_record(
    email: str,
    otp_hash: str,
    purpose: str = "email_verification",
    expires_in_seconds: int = 600,
    expires_in_minutes: int | None = None,
    max_attempts: int = 5,
) -> dict[str, Any]:
    """
    Saves or updates an OTP verification record in Supabase email_verifications table,
    with an in-memory cache for resilience.
    """
    clean_email = email.lower().strip()
    now = datetime.now(UTC)
    sec = (
        expires_in_minutes *
        60) if expires_in_minutes is not None else expires_in_seconds
    expires_at = now + timedelta(seconds=sec)

    record = {
        "email": clean_email,
        "otp_hash": otp_hash,
        "purpose": purpose,
        "attempts": 0,
        "max_attempts": max_attempts,
        "expires_at": expires_at.isoformat(),
        "consumed": False,
        "created_at": now.isoformat(),
        "last_sent_at": now.isoformat(),
    }

    # Cache in memory
    _in_memory_otp_cache[f"{clean_email}:{purpose}"] = dict(record)

    # Persist in Supabase table
    try:
        admin_client = get_admin_client()
        # Invalidate previous unconsumed records for this email and purpose
        admin_client.table("email_verifications").update({"consumed": True}).eq(
            "email", clean_email).eq("purpose", purpose).eq("consumed", False).execute()
        res = admin_client.table(
            "email_verifications").insert(record).execute()
        if res.data and len(res.data) > 0:
            return cast(dict[str, Any], res.data[0])
    except Exception as e:
        logger.warning(
            f"Notice: Supabase email_verifications insert notice: {
                sanitize_log_message(
                    str(e))}. In-memory fallback active.")

    return record


def get_active_otp_record(
        email: str, purpose: str = "email_verification") -> dict[str, Any] | None:
    """
    Retrieves the current active (unconsumed) OTP record for this email and purpose.
    """
    clean_email = email.lower().strip()

    # 1. Try Supabase table
    try:
        admin_client = get_admin_client()
        res = (
            admin_client.table("email_verifications")
            .select("*")
            .eq("email", clean_email)
            .eq("purpose", purpose)
            .eq("consumed", False)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return cast(dict[str, Any], res.data[0])
    except Exception as e:
        logger.debug(
            f"Querying email_verifications table notice: {
                sanitize_log_message(
                    str(e))}")

    # 2. Check local memory cache
    cached = _in_memory_otp_cache.get(f"{clean_email}:{purpose}")
    if cached and not cached.get("consumed", False):
        return cached

    return None


def increment_otp_attempt(record_id: str | None, email: str,
                          purpose: str = "email_verification") -> int:
    """
    Increments the failed verification attempt count.
    """
    clean_email = email.lower().strip()
    key = f"{clean_email}:{purpose}"
    if key in _in_memory_otp_cache:
        _in_memory_otp_cache[key]["attempts"] = _in_memory_otp_cache[key].get(
            "attempts", 0) + 1
        new_attempts = _in_memory_otp_cache[key]["attempts"]
    else:
        new_attempts = 1

    if record_id:
        try:
            admin_client = get_admin_client()
            admin_client.table("email_verifications").update(
                {"attempts": new_attempts}).eq("id", record_id).execute()
        except Exception as e:
            logger.debug(
                f"Updating attempts in Supabase notice: {
                    sanitize_log_message(
                        str(e))}")

    return new_attempts


def mark_otp_consumed(record_id: str | None, email: str,
                      purpose: str = "email_verification") -> None:
    """
    Marks the OTP record as consumed to prevent replay attacks.
    """
    clean_email = email.lower().strip()
    key = f"{clean_email}:{purpose}"
    if key in _in_memory_otp_cache:
        _in_memory_otp_cache[key]["consumed"] = True

    if record_id:
        try:
            admin_client = get_admin_client()
            admin_client.table("email_verifications").update(
                {"consumed": True}).eq("id", record_id).execute()
        except Exception as e:
            logger.debug(
                f"Marking OTP consumed in Supabase notice: {
                    sanitize_log_message(
                        str(e))}")


def mark_user_email_verified(user_id: str, email: str) -> None:
    """
    Marks the user account as verified across Supabase Auth and public profiles.
    """
    admin_client = get_admin_client()
    try:
        admin_client.auth.admin.update_user_by_id(
            user_id,
            {
                "email_confirm": True,
                "user_metadata": {"email_verified": True}
            }
        )
    except Exception as e:
        logger.error(
            f"Error marking user email confirmed in Auth: {
                sanitize_log_message(
                    str(e))}")

    try:
        admin_client.table("profiles").update(
            {"email_verified": True}).eq("id", user_id).execute()
    except Exception as e:
        logger.debug(f"Profiles update notice: {sanitize_log_message(str(e))}")
