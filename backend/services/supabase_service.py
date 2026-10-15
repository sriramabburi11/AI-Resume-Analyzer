import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

logger = logging.getLogger("supabase_service")

DEFAULT_SUPABASE_URL = "https://mykmvgdrzvcoydpliwhr.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15a212Z2RyenZjb3lkcGxpd2hyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIwNTkxMTEsImV4cCI6MjEwNzYzNTExMX0.pHOXwng1vC6y_BhvLRYprftXl4QxRw3_xitZrkadOv0"
DEFAULT_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15a212Z2RyenZjb3lkcGxpd2hyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MjA1OTExMSwiZXhwIjoyMTA3NjM1MTExfQ.HZffIBf6JIVK791deiMGj1HNGZO259GoaMYeoC1OtgI"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() or DEFAULT_SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip() or DEFAULT_SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or DEFAULT_SERVICE_KEY

# Fallback to SUPABASE_KEY if service role key not provided
SERVICE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY

_client: Optional[Client] = None

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
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise RuntimeError(f"Could not connect to Supabase: {str(e)}")


def get_admin_client() -> Client:
    """Always returns a fresh client with the service role key for administrative operations without session contamination."""
    if not SUPABASE_URL or not SERVICE_KEY:
        raise RuntimeError(
            "Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )
    return create_client(SUPABASE_URL, SERVICE_KEY)


security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Dict[str, Any]:
    """
    Validates the Bearer token with Supabase Auth and returns the authenticated user object.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        client = get_supabase_client()
        # Verify token with Supabase Auth
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
            "id": str(u.id),
            "email": u.email,
            "full_name": meta.get("full_name") or meta.get("name") or (u.email.split("@")[0] if u.email else "User"),
            "email_verified": True,
            "user_metadata": meta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Supabase auth token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def save_resume_analysis(
    user_id: str,
    resume_name: str,
    job_title: Optional[str],
    ats_score: int,
    structure_score: Optional[int],
    content_score: Optional[int],
    job_match_score: Optional[int],
    analysis_summary: Dict[str, Any],
) -> Dict[str, Any]:
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
            return res.data[0]
        return payload
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error saving analysis to Supabase: {err_msg}")
        # Check if table missing
        if "PGRST205" in err_msg or "schema cache" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database table 'resume_analyses' not found. Please execute the SQL migration in supabase/migrations/ in your Supabase SQL editor.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save analysis to Supabase: {err_msg}",
        )


def get_user_analyses(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches the resume analysis history for a specific user from Supabase.
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
        return res.data or []
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error fetching history from Supabase: {err_msg}")
        if "PGRST205" in err_msg or "schema cache" in err_msg:
            return []
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analysis history from Supabase: {err_msg}",
        )


def get_analysis_by_id(analysis_id: str, user_id: str) -> Optional[Dict[str, Any]]:
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
        return res.data
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error fetching analysis detail {analysis_id}: {err_msg}")
        return None


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
        return bool(res.data)
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        return False


def check_supabase_connection() -> Dict[str, Any]:
    """
    Health check helper for Supabase service.
    """
    try:
        client = get_supabase_client()
        # Verify auth endpoint responsive
        settings = client.auth.get_user("dummy_check_health_token")
    except Exception as e:
        err = str(e)
        # 401 or invalid token means the Supabase auth server responded!
        if "Invalid" in err or "401" in err or "token" in err.lower():
            return {"status": "connected", "provider": "Supabase Cloud"}
        return {"status": "error", "error": err, "provider": "Supabase Cloud"}
    return {"status": "connected", "provider": "Supabase Cloud"}


# ==============================================================================
# Email Verification OTP Management
# ==============================================================================

_in_memory_otp_cache: Dict[str, Dict[str, Any]] = {}


def save_otp_record(
    email: str,
    otp_hash: str,
    purpose: str = "email_verification",
    expires_in_seconds: int = 600,
    expires_in_minutes: Optional[int] = None,
    max_attempts: int = 5,
) -> Dict[str, Any]:
    """
    Saves or updates an OTP verification record in Supabase email_verifications table,
    with an in-memory cache for resilience.
    """
    clean_email = email.lower().strip()
    now = datetime.now(timezone.utc)
    sec = (expires_in_minutes * 60) if expires_in_minutes is not None else expires_in_seconds
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
        admin_client.table("email_verifications").update({"consumed": True}).eq("email", clean_email).eq("purpose", purpose).eq("consumed", False).execute()
        res = admin_client.table("email_verifications").insert(record).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        logger.warning(f"Notice: Supabase email_verifications insert notice: {e}. In-memory fallback active.")

    return record


def get_active_otp_record(email: str, purpose: str = "email_verification") -> Optional[Dict[str, Any]]:
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
            return res.data[0]
    except Exception as e:
        logger.debug(f"Querying email_verifications table notice: {e}")

    # 2. Check local memory cache
    cached = _in_memory_otp_cache.get(f"{clean_email}:{purpose}")
    if cached and not cached.get("consumed", False):
        return cached

    return None


def increment_otp_attempt(record_id: Optional[str], email: str, purpose: str = "email_verification") -> int:
    """
    Increments the failed verification attempt count.
    """
    clean_email = email.lower().strip()
    key = f"{clean_email}:{purpose}"
    if key in _in_memory_otp_cache:
        _in_memory_otp_cache[key]["attempts"] = _in_memory_otp_cache[key].get("attempts", 0) + 1
        new_attempts = _in_memory_otp_cache[key]["attempts"]
    else:
        new_attempts = 1

    if record_id:
        try:
            admin_client = get_admin_client()
            admin_client.table("email_verifications").update({"attempts": new_attempts}).eq("id", record_id).execute()
        except Exception as e:
            logger.debug(f"Updating attempts in Supabase notice: {e}")

    return new_attempts


def mark_otp_consumed(record_id: Optional[str], email: str, purpose: str = "email_verification") -> None:
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
            admin_client.table("email_verifications").update({"consumed": True}).eq("id", record_id).execute()
        except Exception as e:
            logger.debug(f"Marking OTP consumed in Supabase notice: {e}")


def mark_user_email_verified(user_id: str, email: str) -> None:
    """
    Marks the user account as verified across Supabase Auth and public profiles.
    """
    clean_email = email.lower().strip()
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
        logger.error(f"Error marking user {user_id} email confirmed in Auth: {e}")

    try:
        admin_client.table("profiles").update({"email_verified": True}).eq("id", user_id).execute()
    except Exception as e:
        logger.debug(f"Profiles update notice: {e}")
