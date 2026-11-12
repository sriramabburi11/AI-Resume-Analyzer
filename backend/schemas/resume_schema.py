from typing import Any

from pydantic import BaseModel, Field


class ImprovementItem(BaseModel):
    priority: str = Field(description="High, Medium, or Low")
    current: str = Field(
        description="Exact current text or statement from resume")
    problem: str = Field(description="Why the current text needs improvement")
    recommended_change: str = Field(
        description="Improved, action-oriented version of the statement")
    reason: str = Field(
        description="Explanation of why the recommended change is better")


class RoleRecommendation(BaseModel):
    role: str = Field(description="Job role title")
    match_percentage: int = Field(description="Match percentage (0-100)")
    matching_skills: list[str] = Field(
        default_factory=list,
        description="Skills present in resume that match role")
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Skills missing or weak for this role")
    reason: str = Field(
        description="Explanation for why this role is a good or partial fit")
    evidence: str = Field(
        default="",
        description="Specific resume sections/projects supporting match")


class ATSIssue(BaseModel):
    type: str = Field(description="warning, fail, or pass")
    issue: str = Field(description="Description of the ATS check or issue")
    detail: str | None = Field(default=None,
                               description="Additional context or guidance")


class SectionDetail(BaseModel):
    name: str = Field(description="Standard section name")
    found: bool = Field(description="Whether section was detected")
    heading_used: str | None = Field(
        default=None, description="Actual heading used in resume")
    recommendation: str | None = Field(
        default=None, description="Recommendation if heading non-standard or missing")


class KeywordAnalysis(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    partial: list[str] = Field(default_factory=list)
    categorized: dict[str, list[str]] = Field(
        default_factory=dict, description="Categorized keywords like Languages, Frameworks, Databases, Tools, Cloud, Concepts")


class JobMatchDetails(BaseModel):
    job_match_score: int = Field(
        description="Percentage match with provided job description (0-100)")
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ResumeAnalysisResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    structure_score: int = Field(ge=0, le=100)
    ats_score: int = Field(ge=0, le=100)
    content_score: int = Field(ge=0, le=100)

    sections: dict[str, bool] = Field(
        description="Boolean map of standard section names (contact, summary, education, skills, experience, projects, certifications, etc.)"
    )
    section_details: list[SectionDetail] = Field(default_factory=list)

    ats_issues: list[ATSIssue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)

    improvements: list[ImprovementItem] = Field(default_factory=list)
    roles: list[RoleRecommendation] = Field(default_factory=list)

    keywords: KeywordAnalysis = Field(default_factory=KeywordAnalysis)

    job_match_score: int | None = Field(
        default=None, description="Job match score if job description was provided")
    job_match_details: JobMatchDetails | None = Field(default=None)

    filename: str | None = Field(default=None)
    text_length: int | None = Field(default=0)
    saved_analysis_id: str | None = Field(
        default=None, description="Database UUID of the saved analysis")
    saved_to_history: bool = Field(
        default=False,
        description="Whether the record was successfully saved in history")
    history_error: str | None = Field(
        default=None, description="Error message if saving history failed")


class UserRegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class UserLoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    email_verified: bool = False
    created_at: str | None = None


class UserProfileUpdate(BaseModel):
    full_name: str


class AuthResponse(BaseModel):
    user: UserProfileResponse
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    message: str
    email: str
    requires_verification: bool = True
    cooldown_seconds: int = 60
    delivery_mode: str | None = "live"
    delivery_notice: str | None = None
    preview_otp: str | None = None


class VerifyEmailRequest(BaseModel):
    email: str
    otp: str


class ResendVerificationRequest(BaseModel):
    email: str


class ResendVerificationResponse(BaseModel):
    message: str
    cooldown_seconds: int = 60
    delivery_mode: str | None = "live"
    delivery_notice: str | None = None
    preview_otp: str | None = None


class AnalysisHistoryItem(BaseModel):
    id: str
    resume_name: str | None = None
    job_title: str | None = None
    ats_score: float | None = None
    structure_score: float | None = None
    content_score: float | None = None
    job_match_score: float | None = None
    created_at: str


class AnalysisDetailResponse(BaseModel):
    id: str
    user_id: str
    resume_name: str | None = None
    job_title: str | None = None
    ats_score: float | None = None
    structure_score: float | None = None
    content_score: float | None = None
    job_match_score: float | None = None
    analysis_summary: dict[str, Any]
    created_at: str
