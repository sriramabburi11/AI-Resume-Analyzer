from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ImprovementItem(BaseModel):
    priority: str = Field(description="High, Medium, or Low")
    current: str = Field(description="Exact current text or statement from resume")
    problem: str = Field(description="Why the current text needs improvement")
    recommended_change: str = Field(description="Improved, action-oriented version of the statement")
    reason: str = Field(description="Explanation of why the recommended change is better")

class RoleRecommendation(BaseModel):
    role: str = Field(description="Job role title")
    match_percentage: int = Field(description="Match percentage (0-100)")
    matching_skills: List[str] = Field(default_factory=list, description="Skills present in resume that match role")
    missing_skills: List[str] = Field(default_factory=list, description="Skills missing or weak for this role")
    reason: str = Field(description="Explanation for why this role is a good or partial fit")
    evidence: str = Field(default="", description="Specific resume sections/projects supporting match")

class ATSIssue(BaseModel):
    type: str = Field(description="warning, fail, or pass")
    issue: str = Field(description="Description of the ATS check or issue")
    detail: Optional[str] = Field(default=None, description="Additional context or guidance")

class SectionDetail(BaseModel):
    name: str = Field(description="Standard section name")
    found: bool = Field(description="Whether section was detected")
    heading_used: Optional[str] = Field(default=None, description="Actual heading used in resume")
    recommendation: Optional[str] = Field(default=None, description="Recommendation if heading non-standard or missing")

class KeywordAnalysis(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    partial: List[str] = Field(default_factory=list)
    categorized: Dict[str, List[str]] = Field(default_factory=dict, description="Categorized keywords like Languages, Frameworks, Databases, Tools, Cloud, Concepts")

class JobMatchDetails(BaseModel):
    job_match_score: int = Field(description="Percentage match with provided job description (0-100)")
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    partial_matches: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class ResumeAnalysisResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    structure_score: int = Field(ge=0, le=100)
    ats_score: int = Field(ge=0, le=100)
    content_score: int = Field(ge=0, le=100)
    
    sections: Dict[str, bool] = Field(
        description="Boolean map of standard section names (contact, summary, education, skills, experience, projects, certifications, etc.)"
    )
    section_details: List[SectionDetail] = Field(default_factory=list)
    
    ats_issues: List[ATSIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    
    improvements: List[ImprovementItem] = Field(default_factory=list)
    roles: List[RoleRecommendation] = Field(default_factory=list)
    
    keywords: KeywordAnalysis = Field(default_factory=KeywordAnalysis)
    
    job_match_score: Optional[int] = Field(default=None, description="Job match score if job description was provided")
    job_match_details: Optional[JobMatchDetails] = Field(default=None)

    filename: Optional[str] = Field(default=None)
    text_length: Optional[int] = Field(default=0)
