import os
import re
import logging
from datetime import datetime, timezone
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
    RegisterResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    AnalysisHistoryItem,
    AnalysisDetailResponse
)
from services.pdf_parser import extract_resume_text, PDFParsingError
from services.resume_analyzer import analyze_resume_with_gemini
from services.email_service import (
    generate_secure_otp,
    hash_otp,
    verify_otp_hash,
    send_verification_email
)
from services.supabase_service import (
    get_supabase_client,
    get_admin_client,
    get_current_user,
    save_resume_analysis,
    get_user_analyses,
    get_analysis_by_id,
    delete_analysis_by_id,
    check_supabase_connection,
    save_otp_record,
    get_active_otp_record,
    increment_otp_attempt,
    mark_otp_consumed,
    mark_user_email_verified
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
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


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
# Authentication Endpoints (Supabase Auth & OTP Email Verification)
# ==============================================================================

@app.post("/api/auth/register", response_model=RegisterResponse)
def register_user(body: UserRegisterRequest):
    """
    Registers a new user account with unverified status and issues a 6-digit OTP to their email.
    """
    clean_name = body.full_name.strip()
    clean_email = body.email.strip().lower()

    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required."
        )

    if not clean_email or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address (e.g. user@example.com)."
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    admin_client = get_admin_client()
    existing_user = None

    try:
        users = admin_client.auth.admin.list_users()
        existing_user = next((u for u in users if u.email == clean_email), None)
    except Exception as list_err:
        logger.warning(f"Error checking existing users: {list_err}")

    if existing_user:
        # Check if user is already verified
        is_already_verified = bool(getattr(existing_user, "confirmed_at", None))
        meta = getattr(existing_user, "user_metadata", {}) or {}
        if is_already_verified or meta.get("email_verified") is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please sign in."
            )
        # Existing unverified user: update password and metadata
        try:
            admin_client.auth.admin.update_user_by_id(
                str(existing_user.id),
                {
                    "password": body.password,
                    "user_metadata": {
                        "full_name": clean_name,
                        "email_verified": False
                    }
                }
            )
        except Exception as upd_err:
            logger.error(f"Error updating unverified user: {upd_err}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to process registration: {str(upd_err)}"
            )
    else:
        # Create new unverified user in Supabase
        try:
            admin_client.auth.admin.create_user({
                "email": clean_email,
                "password": body.password,
                "email_confirm": False,
                "user_metadata": {
                    "full_name": clean_name,
                    "email_verified": False
                }
            })
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Supabase user creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg
            )

    # Generate 6-digit cryptographic OTP
    otp = generate_secure_otp(6)
    otp_hash = hash_otp(clean_email, otp, "email_verification")

    # Save hashed OTP in database with 10-minute expiry
    save_otp_record(clean_email, otp_hash, "email_verification", expires_in_minutes=10)

    # Dispatch verification email
    dispatch = send_verification_email(clean_email, otp, clean_name)
    delivered = bool(dispatch.get("delivered"))
    msg = "A 6-digit verification code has been sent to your email." if delivered else "Verification code generated."

    return RegisterResponse(
        message=msg,
        email=clean_email,
        requires_verification=True,
        cooldown_seconds=60,
        delivery_mode="live" if delivered else "sandbox",
        delivery_notice=dispatch.get("notice"),
        preview_otp=dispatch.get("preview_otp")
    )


@app.post("/api/auth/verify-email", response_model=AuthResponse)
def verify_email(body: VerifyEmailRequest):
    """
    Verifies the user's email with the 6-digit OTP code, marks account verified, and issues an active session token.
    """
    clean_email = body.email.strip().lower()
    clean_otp = body.otp.strip()

    if not clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required."
        )

    if not clean_otp or len(clean_otp) != 6 or not clean_otp.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code must be exactly 6 digits."
        )

    # Retrieve active OTP record
    otp_record = get_active_otp_record(clean_email, "email_verification")
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found or code has expired. Please request a new code."
        )

    record_id = otp_record.get("id")
    current_attempts = otp_record.get("attempts", 0)
    max_attempts = otp_record.get("max_attempts", 5)

    if current_attempts >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum verification attempts exceeded. Please request a new code."
        )

    # Validate OTP hash
    stored_hash = otp_record.get("otp_hash", "")
    is_valid = verify_otp_hash(clean_email, clean_otp, stored_hash, "email_verification")

    if not is_valid:
        new_attempts = increment_otp_attempt(record_id, clean_email, "email_verification")
        remaining = max(0, max_attempts - new_attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Invalid code. Maximum attempts reached. Please request a new verification code."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        )

    # Valid OTP: Consume record
    mark_otp_consumed(record_id, clean_email, "email_verification")

    # Mark user verified in Supabase Auth & profiles
    admin_client = get_admin_client()
    user_id = None
    full_name = clean_email.split("@")[0]
    try:
        users = admin_client.auth.admin.list_users()
        user_obj = next((u for u in users if u.email == clean_email), None)
        if user_obj:
            user_id = str(user_obj.id)
            meta = getattr(user_obj, "user_metadata", {}) or {}
            full_name = meta.get("full_name") or meta.get("name") or full_name
            # Confirm user
            admin_client.auth.admin.update_user_by_id(
                user_id,
                {
                    "email_confirm": True,
                    "user_metadata": {**meta, "email_verified": True}
                }
            )
            mark_user_email_verified(user_id, clean_email)
    except Exception as e:
        logger.error(f"Error marking user verified: {e}")

    # Generate authenticated session token
    access_token = ""
    try:
        link_res = admin_client.auth.admin.generate_link({"type": "magiclink", "email": clean_email})
        hashed_token = link_res.properties.hashed_token
        auth_client = get_supabase_client()
        auth_res = auth_client.auth.verify_otp({"token_hash": hashed_token, "type": "magiclink"})
        if auth_res.session:
            access_token = auth_res.session.access_token
    except Exception as token_err:
        logger.warning(f"Session generation warning: {token_err}")

    return AuthResponse(
        user=UserProfileResponse(
            id=user_id or "",
            email=clean_email,
            full_name=full_name,
            email_verified=True,
            created_at=None
        ),
        access_token=access_token,
        token_type="bearer"
    )


@app.post("/api/auth/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(body: ResendVerificationRequest):
    """
    Issues and sends a fresh 6-digit OTP code to the user's email with a 60-second cooldown rate limit.
    """
    clean_email = body.email.strip().lower()

    if not clean_email or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    admin_client = get_admin_client()
    user_name = "Job Seeker"
    try:
        users = admin_client.auth.admin.list_users()
        user_obj = next((u for u in users if u.email == clean_email), None)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account registered with this email address."
            )

        meta = getattr(user_obj, "user_metadata", {}) or {}
        user_name = meta.get("full_name") or user_name
        is_already_verified = bool(getattr(user_obj, "confirmed_at", None)) or meta.get("email_verified") is True
        if is_already_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your email is already verified. You can log in directly."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error checking user for resend: {e}")

    # Check cooldown against previous record
    active_record = get_active_otp_record(clean_email, "email_verification")
    if active_record and active_record.get("last_sent_at"):
        last_sent = active_record["last_sent_at"]
        if isinstance(last_sent, str):
            try:
                last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            except Exception:
                last_dt = None
        else:
            last_dt = last_sent

        if last_dt:
            elapsed = (datetime.now(timezone.utc) - last_dt.astimezone(timezone.utc)).total_seconds()
            if elapsed < 60:
                wait_sec = int(60 - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait_sec} second{'s' if wait_sec != 1 else ''} before requesting another code."
                )

    # Generate new OTP
    otp = generate_secure_otp(6)
    otp_hash = hash_otp(clean_email, otp, "email_verification")
    save_otp_record(clean_email, otp_hash, "email_verification", expires_in_minutes=10)

    # Dispatch email
    dispatch = send_verification_email(clean_email, otp, user_name)
    delivered = bool(dispatch.get("delivered"))
    msg = "A new 6-digit verification code has been sent to your email." if delivered else "A new verification code has been generated."

    return ResendVerificationResponse(
        message=msg,
        cooldown_seconds=60,
        delivery_mode="live" if delivered else "sandbox",
        delivery_notice=dispatch.get("notice"),
        preview_otp=dispatch.get("preview_otp")
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(body: UserLoginRequest):
    """
    Authenticates a user via Supabase Auth with email and password.
    Blocks unverified accounts with HTTP 403 Forbidden.
    """
    clean_email = body.email.strip().lower()

    if not clean_email or not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )

    admin_client = get_admin_client()
    user_obj = None
    try:
        users = admin_client.auth.admin.list_users()
        user_obj = next((u for u in users if u.email == clean_email), None)
    except Exception as err:
        logger.warning(f"User check warning in login: {err}")

    # Attempt sign-in with client
    client = get_supabase_client()
    auth_res = None
    try:
        auth_res = client.auth.sign_in_with_password({
            "email": clean_email,
            "password": body.password
        })
    except Exception as e:
        err_msg = str(e).lower()
        logger.warning(f"Login attempt failed for {clean_email}: {e}")

        # Check if failure is due to unconfirmed email
        if "confirm" in err_msg or "verif" in err_msg:
            # Generate and send fresh OTP so user can verify immediately
            otp = generate_secure_otp(6)
            otp_hash = hash_otp(clean_email, otp, "email_verification")
            save_otp_record(clean_email, otp_hash, "email_verification", expires_in_minutes=10)
            user_name = ""
            if user_obj:
                meta = getattr(user_obj, "user_metadata", {}) or {}
                user_name = meta.get("full_name") or ""
            send_verification_email(clean_email, otp, user_name)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. A new verification code has been sent to your email."
            )

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

    # Check verified status
    meta = getattr(auth_res.user, "user_metadata", {}) or {}
    is_verified = bool(getattr(auth_res.user, "confirmed_at", None)) or bool(meta.get("email_verified", False))

    if not is_verified:
        # Generate and dispatch fresh OTP
        otp = generate_secure_otp(6)
        otp_hash = hash_otp(clean_email, otp, "email_verification")
        save_otp_record(clean_email, otp_hash, "email_verification", expires_in_minutes=10)
        full_name = meta.get("full_name") or clean_email.split("@")[0]
        send_verification_email(clean_email, otp, full_name)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. A new verification code has been sent to your email."
        )

    full_name = meta.get("full_name") or meta.get("name") or clean_email.split("@")[0]

    return AuthResponse(
        user=UserProfileResponse(
            id=str(auth_res.user.id),
            email=auth_res.user.email or clean_email,
            full_name=full_name,
            email_verified=True,
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
