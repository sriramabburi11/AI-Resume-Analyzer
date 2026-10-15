import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn

from database import engine, Base, get_db
from models import User, ResumeAnalysis, PasswordResetToken
from security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_random_token,
    hash_token,
    get_current_user
)
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

# Automatically initialize database tables on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as db_init_err:
    print(f"Database schema init notice: {db_init_err}")

app = FastAPI(
    title="AI Resume Analyzer & ATS Optimizer API",
    description="API for analyzing resumes, ATS compatibility, role matching, and resume improvements with self-managed PostgreSQL.",
    version="2.0.0"
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
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unavailable: {str(e)}"
    
    dialect_name = engine.dialect.name
    return {
        "status": "ok",
        "database": db_status,
        "engine": f"SQLAlchemy 2.x ({dialect_name.upper()})"
    }

# ==============================================================================
# Authentication Endpoints
# ==============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(
    body: UserRegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Registers a new user in PostgreSQL with securely hashed password (Argon2id).
    Prevents duplicate email registrations.
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

    # Check for duplicate email
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in."
        )

    # Hash password with Argon2id
    hashed = hash_password(body.password)

    new_user = User(
        full_name=clean_name,
        email=clean_email,
        password_hash=hashed,
        email_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT access token
    access_token = create_access_token(user_id=new_user.id, email=new_user.email)

    # Set HttpOnly session cookie
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 days
    )

    return AuthResponse(
        user=UserProfileResponse(
            id=str(new_user.id),
            email=new_user.email,
            full_name=new_user.full_name,
            email_verified=new_user.email_verified,
            created_at=str(new_user.created_at)
        ),
        access_token=access_token,
        token_type="bearer"
    )

@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(
    body: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticates a user via email and password.
    Validates Argon2id password hash and returns signed JWT token.
    """
    clean_email = body.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id, email=user.email)

    # Set HttpOnly session cookie
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )

    return AuthResponse(
        user=UserProfileResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            email_verified=user.email_verified,
            created_at=str(user.created_at)
        ),
        access_token=access_token,
        token_type="bearer"
    )

@app.post("/api/auth/logout")
def logout_user(response: Response):
    """
    Logs out the user by clearing the session cookie.
    """
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns current authenticated user profile.
    """
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        created_at=str(current_user.created_at)
    )

@app.put("/api/auth/profile", response_model=UserProfileResponse)
def update_profile_name(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated user's display name.
    """
    clean_name = body.full_name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot be empty."
        )

    current_user.full_name = clean_name
    db.commit()
    db.refresh(current_user)

    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        created_at=str(current_user.created_at)
    )

@app.post("/api/auth/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Initiates password recovery.
    Always returns uniform message to prevent user enumeration.
    """
    clean_email = body.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if user:
        raw_token = generate_random_token()
        hashed = hash_token(raw_token)
        from datetime import datetime, timezone, timedelta
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires,
            used=False
        )
        db.add(token_record)
        db.commit()

        # In production, send via configured email service. For local dev, token is logged safely.
        print(f"[AUTH] Password reset token generated for {clean_email}: {raw_token}")

    return {
        "message": "If an account exists with this email address, password reset instructions have been sent."
    }

@app.post("/api/auth/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Validates reset token and sets new password.
    """
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    hashed_input_token = hash_token(body.token.strip())
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hashed_input_token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > now
    ).first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used password reset link. Please request a new one."
        )

    # Update user password
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found."
        )

    user.password_hash = hash_password(body.new_password)
    token_record.used = True
    db.commit()

    return {"message": "Password updated successfully. You can now log in with your new password."}

# ==============================================================================
# Resume Analysis & History Endpoints
# ==============================================================================

@app.post("/api/analyze-resume", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected resume analysis endpoint.
    1. Validates and parses uploaded PDF in-memory (no permanent disk storage).
    2. Runs Gemini ATS and role analysis engine.
    3. Persists structured analysis results against authenticated user's ID in PostgreSQL.
    """
    # 1. File validation
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a PDF file."
        )

    try:
        # Read file contents into memory (not persisted on disk)
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

        # 4. Save analysis summary to PostgreSQL resume_analyses table
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

            record = ResumeAnalysis(
                user_id=current_user.id,
                resume_name=resume.filename,
                job_title=job_title,
                ats_score=analysis_result.ats_score,
                structure_score=analysis_result.structure_score,
                content_score=analysis_result.content_score,
                job_match_score=analysis_result.job_match_score,
                analysis_summary=clean_summary
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            analysis_result.saved_analysis_id = str(record.id)
            analysis_result.saved_to_history = True
            analysis_result.history_error = None
        except Exception as save_err:
            print(f"Error saving analysis to PostgreSQL: {save_err}")
            analysis_result.saved_to_history = False
            analysis_result.history_error = "Resume analyzed successfully, but could not be saved to your PostgreSQL history."

        return analysis_result

    except PDFParsingError as pe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(pe)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the resume. Please try again."
        )

@app.get("/api/history", response_model=List[AnalysisHistoryItem])
@app.get("/api/analyses", response_model=List[AnalysisHistoryItem])
def get_user_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the user's historical resume analysis records from PostgreSQL.
    Strictly isolated to the authenticated user ID.
    """
    records = db.query(ResumeAnalysis).filter(
        ResumeAnalysis.user_id == current_user.id
    ).order_by(ResumeAnalysis.created_at.desc()).all()

    return [
        AnalysisHistoryItem(
            id=str(r.id),
            resume_name=r.resume_name,
            job_title=r.job_title,
            ats_score=float(r.ats_score) if r.ats_score is not None else None,
            structure_score=float(r.structure_score) if r.structure_score is not None else None,
            content_score=float(r.content_score) if r.content_score is not None else None,
            job_match_score=float(r.job_match_score) if r.job_match_score is not None else None,
            created_at=str(r.created_at)
        )
        for r in records
    ]

@app.get("/api/history/{analysis_id}", response_model=AnalysisDetailResponse)
@app.get("/api/analyses/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches details for a single analysis record belonging strictly to the authenticated user.
    """
    record = db.query(ResumeAnalysis).filter(
        ResumeAnalysis.id == analysis_id,
        ResumeAnalysis.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found or access denied."
        )

    return AnalysisDetailResponse(
        id=str(record.id),
        user_id=str(record.user_id),
        resume_name=record.resume_name,
        job_title=record.job_title,
        ats_score=float(record.ats_score) if record.ats_score is not None else None,
        structure_score=float(record.structure_score) if record.structure_score is not None else None,
        content_score=float(record.content_score) if record.content_score is not None else None,
        job_match_score=float(record.job_match_score) if record.job_match_score is not None else None,
        analysis_summary=record.analysis_summary,
        created_at=str(record.created_at)
    )

@app.delete("/api/history/{analysis_id}")
@app.delete("/api/analyses/{analysis_id}")
def delete_history_item(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes an analysis record belonging strictly to the authenticated user.
    """
    record = db.query(ResumeAnalysis).filter(
        ResumeAnalysis.id == analysis_id,
        ResumeAnalysis.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not delete analysis record. It may have already been removed."
        )

    db.delete(record)
    db.commit()

    return {"deleted": True, "id": analysis_id}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
