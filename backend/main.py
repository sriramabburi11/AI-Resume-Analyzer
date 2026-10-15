import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from schemas.resume_schema import (
    ResumeAnalysisResponse,
    UserRegisterRequest,
    UserLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserProfileResponse,
    UserProfileUpdate,
    AuthResponse,
    AnalysisHistoryItem,
    AnalysisDetailResponse
)
from services.pdf_parser import extract_resume_text, PDFParsingError
from services.resume_analyzer import analyze_resume_with_gemini
from services.supabase_service import (
    get_supabase_client,
    get_current_user,
    save_resume_analysis,
    get_user_analyses,
    get_analysis_by_id,
    delete_analysis_by_id,
    check_supabase_connection
)

logger = logging.getLogger("main")

app = FastAPI(
    title="AI Resume Analyzer & ATS Optimizer API",
    description="API for analyzing resumes, ATS compatibility, role matching, and resume improvements with Supabase backend.",
    version="3.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows local dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


@app.get("/api/health")
def health_check():
    """
    Health check returning status of the backend service and Supabase connection.
    """
    supabase_info = check_supabase_connection()
    return {
        "status": "ok",
        "database": supabase_info.get("status", "connected"),
        "provider": supabase_info.get("provider", "Supabase Cloud")
    }


# ==============================================================================
# Authentication Endpoints (Supabase Auth Integration)
# ==============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(body: UserRegisterRequest):
    """
    Registers a new user in Supabase Auth.
    """
    clean_name = body.full_name.strip()
    clean_email = body.email.strip().lower()

    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required."
        )

    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    client = get_supabase_client()
    user_id = None
    try:
        # Create user via Supabase Admin API with email_confirm: True so email rate limits never block the user
        admin_res = client.auth.admin.create_user({
            "email": clean_email,
            "password": body.password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": clean_name
            }
        })
        user_id = str(admin_res.user.id)
    except Exception as e:
        err_msg = str(e)
        if "already" in err_msg.lower() or "exists" in err_msg.lower():
            # If user already registered, ensure email is confirmed and password updated
            try:
                users = client.auth.admin.list_users()
                existing = next((u for u in users if u.email == clean_email), None)
                if existing:
                    client.auth.admin.update_user_by_id(
                        str(existing.id),
                        {
                            "email_confirm": True,
                            "password": body.password,
                            "user_metadata": {"full_name": clean_name}
                        }
                    )
                    user_id = str(existing.id)
            except Exception as upd_err:
                logger.warning(f"Error updating existing user: {upd_err}")
        else:
            logger.error(f"Supabase user creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg
            )

    # Immediately authenticate to obtain session token
    token = ""
    try:
        login_res = client.auth.sign_in_with_password({
            "email": clean_email,
            "password": body.password
        })
        if login_res.session:
            token = login_res.session.access_token
    except Exception as login_err:
        logger.warning(f"Post-registration login notice: {login_err}")

    return AuthResponse(
        user=UserProfileResponse(
            id=user_id or "",
            email=clean_email,
            full_name=clean_name,
            email_verified=True,
            created_at=None
        ),
        access_token=token,
        token_type="bearer"
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(body: UserLoginRequest):
    """
    Authenticates a user via Supabase Auth with email and password.
    """
    clean_email = body.email.strip().lower()
    client = get_supabase_client()

    try:
        auth_res = client.auth.sign_in_with_password({
            "email": clean_email,
            "password": body.password
        })
    except Exception as e:
        logger.warning(f"Supabase login failed for {clean_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_res.user or not auth_res.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please verify your credentials."
        )

    meta = getattr(auth_res.user, "user_metadata", {}) or {}
    full_name = meta.get("full_name") or meta.get("name") or clean_email.split("@")[0]

    return AuthResponse(
        user=UserProfileResponse(
            id=str(auth_res.user.id),
            email=auth_res.user.email or clean_email,
            full_name=full_name,
            email_verified=bool(auth_res.user.confirmed_at),
            created_at=str(auth_res.user.created_at) if hasattr(auth_res.user, "created_at") else None
        ),
        access_token=auth_res.session.access_token,
        token_type="bearer"
    )


@app.post("/api/auth/logout")
def logout_user():
    """
    Logs out the user session.
    """
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile from Supabase Auth.
    """
    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        email_verified=True,
        created_at=None
    )


@app.put("/api/auth/profile", response_model=UserProfileResponse)
def update_profile_name(
    body: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Updates the user's full name in Supabase user metadata.
    """
    clean_name = body.full_name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot be empty."
        )

    client = get_supabase_client()
    try:
        client.auth.admin.update_user_by_id(
            current_user["id"],
            {"user_metadata": {"full_name": clean_name}}
        )
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile name."
        )

    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=clean_name,
        email_verified=True,
        created_at=None
    )


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    """
    Sends a password reset email via Supabase Auth.
    """
    clean_email = body.email.strip().lower()
    client = get_supabase_client()
    try:
        client.auth.reset_password_email(clean_email)
    except Exception as e:
        logger.info(f"Password reset request for {clean_email}: {e}")

    return {
        "message": "If an account exists with this email address, password reset instructions have been sent."
    }


# ==============================================================================
# Resume Analysis & History Endpoints (Supabase Backend)
# ==============================================================================

@app.post("/api/analyze-resume", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Protected resume analysis endpoint.
    1. Validates and parses uploaded PDF in-memory (no raw files saved to disk).
    2. Runs Gemini ATS and role analysis engine.
    3. Persists structured analysis results into Supabase `resume_analyses` table against user's UUID.
    """
    # 1. File validation
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a PDF file."
        )

    try:
        # Read file contents into memory
        contents = await resume.read()

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the 10 MB limit. Please upload a smaller PDF."
            )

        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF file is empty."
            )

        # 2. Extract text and metadata in-memory
        pdf_meta = extract_resume_text(contents)

        # 3. Analyze resume with Gemini AI (or mock fallback if unconfigured)
        analysis_result = analyze_resume_with_gemini(
            pdf_meta=pdf_meta,
            job_description=job_description,
            filename=resume.filename
        )

        # 4. Save analysis summary to Supabase resume_analyses table
        try:
            job_title = None
            if job_description and job_description.strip():
                first_line = job_description.strip().splitlines()[0]
                job_title = first_line[:80].strip()
            elif analysis_result.roles and len(analysis_result.roles) > 0:
                job_title = analysis_result.roles[0].role

            clean_summary = analysis_result.model_dump()
            clean_summary.pop("saved_analysis_id", None)
            clean_summary.pop("saved_to_history", None)
            clean_summary.pop("history_error", None)

            record = save_resume_analysis(
                user_id=current_user["id"],
                resume_name=resume.filename,
                job_title=job_title,
                ats_score=analysis_result.ats_score,
                structure_score=analysis_result.structure_score,
                content_score=analysis_result.content_score,
                job_match_score=analysis_result.job_match_score,
                analysis_summary=clean_summary
            )

            analysis_result.saved_analysis_id = str(record.get("id", ""))
            analysis_result.saved_to_history = True
            analysis_result.history_error = None
        except Exception as save_err:
            logger.error(f"Error saving analysis to Supabase: {save_err}")
            analysis_result.saved_to_history = False
            analysis_result.history_error = "Resume analyzed successfully, but could not be saved to your Supabase history."

        return analysis_result

    except PDFParsingError as pe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(pe)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the resume. Please try again."
        )


@app.get("/api/history", response_model=List[AnalysisHistoryItem])
@app.get("/api/analyses", response_model=List[AnalysisHistoryItem])
def get_user_history(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the user's historical resume analysis records from Supabase.
    Strictly isolated to the authenticated user ID.
    """
    records = get_user_analyses(user_id=current_user["id"])

    return [
        AnalysisHistoryItem(
            id=str(r["id"]),
            resume_name=r.get("resume_name"),
            job_title=r.get("job_title"),
            ats_score=float(r["ats_score"]) if r.get("ats_score") is not None else None,
            structure_score=float(r["structure_score"]) if r.get("structure_score") is not None else None,
            content_score=float(r["content_score"]) if r.get("content_score") is not None else None,
            job_match_score=float(r["job_match_score"]) if r.get("job_match_score") is not None else None,
            created_at=str(r.get("created_at", ""))
        )
        for r in records
    ]


@app.get("/api/history/{analysis_id}", response_model=AnalysisDetailResponse)
@app.get("/api/analyses/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetches details for a single analysis record from Supabase belonging strictly to the authenticated user.
    """
    record = get_analysis_by_id(analysis_id, user_id=current_user["id"])

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found or access denied."
        )

    return AnalysisDetailResponse(
        id=str(record["id"]),
        user_id=str(record["user_id"]),
        resume_name=record.get("resume_name"),
        job_title=record.get("job_title"),
        ats_score=float(record["ats_score"]) if record.get("ats_score") is not None else None,
        structure_score=float(record["structure_score"]) if record.get("structure_score") is not None else None,
        content_score=float(record["content_score"]) if record.get("content_score") is not None else None,
        job_match_score=float(record["job_match_score"]) if record.get("job_match_score") is not None else None,
        analysis_summary=record.get("analysis_summary", {}),
        created_at=str(record.get("created_at", ""))
    )


@app.delete("/api/history/{analysis_id}")
@app.delete("/api/analyses/{analysis_id}")
def delete_history_item(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Deletes an analysis record from Supabase belonging strictly to the authenticated user.
    """
    success = delete_analysis_by_id(analysis_id, user_id=current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not delete analysis record. It may have already been removed."
        )

    return {"deleted": True, "id": analysis_id}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
