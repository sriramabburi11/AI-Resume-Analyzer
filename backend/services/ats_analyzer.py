import re
from typing import Dict, Any, List, Tuple
from schemas.resume_schema import ATSIssue, SectionDetail

STANDARD_SECTION_PATTERNS = {
    "contact": [r"\bcontact\b", r"\bcontact info\b", r"\bcontact information\b", r"\bpersonal details\b"],
    "summary": [r"\bprofessional summary\b", r"\bsummary\b", r"\babout me\b", r"\bcareer summary\b", r"\bprofile\b", r"\bexecutive summary\b"],
    "education": [r"\beducation\b", r"\bacademic background\b", r"\bacademic qualifications\b", r"\beducational background\b"],
    "skills": [r"\btechnical skills\b", r"\bskills\b", r"\bcore competencies\b", r"\bkey skills\b", r"\btechnologies\b", r"\btechnical stack\b", r"\btechnical arsenal\b"],
    "experience": [r"\bwork experience\b", r"\bexperience\b", r"\bprofessional experience\b", r"\bemployment history\b", r"\bwork history\b"],
    "internships": [r"\binternships\b", r"\binternship experience\b"],
    "projects": [r"\bprojects\b", r"\bkey projects\b", r"\bpersonal projects\b", r"\bselected projects\b", r"\bportfolio projects\b"],
    "certifications": [r"\bcertifications\b", r"\blicenses & certifications\b", r"\bcertificates\b", r"\bprofessional certifications\b"],
    "achievements": [r"\bachievements\b", r"\bhonors & awards\b", r"\bawards\b", r"\baccolades\b"]
}

NON_STANDARD_HEADINGS_MAP = {
    "technical arsenal": ("Technical Skills", "Technical Skills is a more conventional section heading and is easier for resume parsers and recruiters to recognize."),
    "my skills": ("Technical Skills", "Use 'Technical Skills' for improved ATS parsing accuracy."),
    "what i know": ("Technical Skills", "Use 'Technical Skills' for standard resume categorization."),
    "where i worked": ("Work Experience", "Use 'Work Experience' or 'Experience' for standard ATS scanning."),
    "things i built": ("Projects", "Use 'Projects' or 'Key Projects' as a standard section header."),
    "what i've built": ("Projects", "Use 'Projects' or 'Key Projects' as a standard section header."),
    "schooling": ("Education", "Use 'Education' as a standard header."),
    "about me": ("Professional Summary", "Using 'Professional Summary' communicates career intent more clearly to recruiters and ATS."),
}

def analyze_structure_and_ats(pdf_meta: Dict[str, Any]) -> Tuple[int, int, Dict[str, bool], List[SectionDetail], List[ATSIssue]]:
    """
    Evaluates resume structure and estimated ATS compatibility deterministically.
    Returns (structure_score, ats_score, sections_map, section_details, ats_issues).
    """
    text = pdf_meta["text"]
    text_lower = text.lower()

    # 1. Section Analysis
    sections_map = {}
    section_details = []
    
    # Check for presence of each section
    for section_key, patterns in STANDARD_SECTION_PATTERNS.items():
        found = False
        heading_used = None
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                found = True
                heading_used = match.group(0).title()
                break
        
        sections_map[section_key] = found
        
        rec = None
        reason = None
        if not found:
            if section_key in ["contact", "education", "skills", "experience", "projects"]:
                rec = f"Add a dedicated '{section_key.title()}' section."
                reason = f"The '{section_key.title()}' section is a core standard component for technical resumes."
        else:
            # Check for non-standard heading usage
            if heading_used and heading_used.lower() in NON_STANDARD_HEADINGS_MAP:
                std, exp = NON_STANDARD_HEADINGS_MAP[heading_used.lower()]
                rec = f"Change heading to '{std}'."
                reason = exp

        section_details.append(SectionDetail(
            name=section_key.title(),
            found=found,
            heading_used=heading_used,
            recommendation=rec
        ))

    # Calculate Structure Score (out of 100)
    # Core sections weight: contact(20), education(15), skills(20), experience/projects(25), summary(10), certifications/others(10)
    structure_score = 40  # base
    if sections_map.get("contact"): structure_score += 15
    if sections_map.get("education"): structure_score += 10
    if sections_map.get("skills"): structure_score += 15
    if sections_map.get("experience") or sections_map.get("projects"): structure_score += 10
    if sections_map.get("summary"): structure_score += 5
    if sections_map.get("certifications") or sections_map.get("achievements"): structure_score += 5

    # Check for custom non-standard headings in text
    non_standard_found = False
    for ns_k, (std_name, exp_text) in NON_STANDARD_HEADINGS_MAP.items():
        if ns_k in text_lower:
            non_standard_found = True
            structure_score = max(50, structure_score - 5)

    structure_score = min(100, max(0, structure_score))

    # 2. ATS Issues Check
    ats_issues: List[ATSIssue] = []
    ats_score = 100

    # Issue 1: Multi-column layout
    if pdf_meta.get("multi_column_detected"):
        ats_score -= 12
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Multiple-column layout detected",
            detail="Some traditional ATS parsers scan line-by-line horizontally across columns, which can merge unrelated text."
        ))

    # Issue 2: Images detected
    if pdf_meta.get("total_images", 0) > 0:
        ats_score -= 10
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Images or graphic elements detected",
            detail="ATS software cannot parse text embedded inside images, logos, or icons."
        ))

    # Issue 3: Table / line grid objects
    if pdf_meta.get("table_indicators_detected"):
        ats_score -= 8
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Tables or structural borders detected",
            detail="Complex tables can confuse text flow extraction algorithms in older ATS platforms."
        ))

    # Issue 4: Contact Info readability
    contact_info = pdf_meta.get("contact_info", {})
    if not contact_info.get("has_email") or not contact_info.get("has_phone"):
        ats_score -= 15
        missing_parts = []
        if not contact_info.get("has_email"): missing_parts.append("Email")
        if not contact_info.get("has_phone"): missing_parts.append("Phone Number")
        ats_issues.append(ATSIssue(
            type="fail",
            issue=f"Missing essential contact info ({', '.join(missing_parts)})",
            detail="Recruiters and ATS parsers require clear email and phone contact details at the top."
        ))
    else:
        ats_issues.append(ATSIssue(
            type="pass",
            issue="Contact information is readable",
            detail="Email and phone number formatting detected cleanly."
        ))

    # Issue 5: Non-standard headings check
    if non_standard_found:
        ats_score -= 8
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Non-standard section headings detected",
            detail="Use industry-standard section names like 'Technical Skills', 'Experience', and 'Projects'."
        ))
    else:
        ats_issues.append(ATSIssue(
            type="pass",
            issue="Standard section headings detected",
            detail="Section headings align well with common ATS parser definitions."
        ))

    # Issue 6: Date formats check
    date_patterns = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-9]{2})?[\s\./\-]*(?:20\d{2}|19\d{2})\b', text)
    if len(date_patterns) < 2:
        ats_score -= 8
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Inconsistent or missing date formats",
            detail="Ensure work experience and project entries have clear date ranges (e.g., 'MM/YYYY - Present' or 'Jan 2022 - Dec 2023')."
        ))

    # Issue 7: Symbols / Special characters
    if pdf_meta.get("unusual_symbols_count", 0) > 3:
        ats_score -= 5
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Unusual icons or custom unicode symbols detected",
            detail="Replace complex decorative icons with standard bullet points (•) to avoid character rendering errors."
        ))

    # Issue 8: Page count / Length
    page_count = pdf_meta.get("page_count", 1)
    word_count = pdf_meta.get("word_count", 0)
    if word_count > 1200 and page_count == 1:
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Dense page content",
            detail="High text density on a single page can reduce recruiter readability."
        ))
    elif page_count > 3:
        ats_score -= 5
        ats_issues.append(ATSIssue(
            type="warning",
            issue="Resume exceeds 3 pages",
            detail="Most technical ATS profiles favor concise 1 to 2 page resumes."
        ))

    ats_score = min(100, max(40, ats_score))

    return structure_score, ats_score, sections_map, section_details, ats_issues
