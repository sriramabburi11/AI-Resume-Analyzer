import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

logger = logging.getLogger("supabase_service")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

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
