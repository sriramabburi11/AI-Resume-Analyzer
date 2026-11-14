import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from schemas.resume_schema import (
    ATSIssue,
    ImprovementItem,
    JobMatchDetails,
    KeywordAnalysis,
    ResumeAnalysisResponse,
    RoleRecommendation,
    SectionDetail,
)
from services.ats_analyzer import analyze_structure_and_ats
from services.privacy_guardrail import redact_pii, sanitize_log_message

load_dotenv()

PROMPT_SYSTEM_INSTRUCTIONS = """
You are an expert AI Resume Coach and Applicant Tracking System (ATS) Auditor for software engineers and technology professionals.
Analyze the provided resume text (and optional Job Description) and return a strictly structured JSON matching the requested schema.

CRITICAL RULES:
1. EXACT IMPROVEMENTS (Feature 5):
   - For every improvement recommendation, identify an EXACT statement currently in the resume.
   - Do NOT just say "Improve your projects".
   - Follow the structure:
     CURRENT: exact current phrase or bullet from resume
     PROBLEM: why it is weak, generic, or missing metrics
     RECOMMENDED CHANGE: improved, action-oriented version using strong verbs and tech context
     REASON: rationale for the change
     PRIORITY: "High", "Medium", or "Low"
   - NEVER invent achievements, technologies, companies, or fake metrics that are not supported by the candidate's actual background.
   - If adding a missing standard section, specify "Add this section only if you genuinely have this experience."

2. ROLE RECOMMENDATIONS (Feature 6):
   - Suggest 4-6 realistic job roles (e.g. Full Stack Developer, Backend Developer, Python Developer, AI Application Developer, Frontend Developer, DevOps Engineer).
   - Base match percentage on concrete evidence in the text. Do NOT recommend a role based on only 1 single keyword.
   - List matching_skills, missing_skills, evidence, and reason.

3. KEYWORD ANALYSIS (Feature 8):
   - Extract relevant technical keywords (languages, frameworks, databases, tools, cloud, concepts).
   - Categorize them into matched, missing, partial, and categorized dict: {"Languages": [], "Frameworks": [], "Databases": [], "Tools": [], "Cloud": [], "Concepts": []}.

4. JOB DESCRIPTION MATCHING (Feature 7):
   - If a job description is provided: calculate job_match_score (0-100), matched_skills, missing_skills, partial_matches, and specific tailored recommendations.
   - Never encourage fake keyword stuffing. State: "Add missing skills only if you genuinely have experience with them."

5. JSON ONLY:
   - Output MUST be pure JSON with no markdown block fences or extra text.
"""


def generate_mock_fallback_analysis(
    text: str,
    pdf_meta: dict[str, Any],
    structure_score: int,
    ats_score: int,
    sections_map: dict[str, bool],
    section_details: list[SectionDetail],
    ats_issues: list[ATSIssue],
    job_description: str | None = None
) -> ResumeAnalysisResponse:
    """
    Intelligent heuristic fallback analyzer when Gemini API is unavailable or key is missing.
    Extracts real keywords, bullets, and sections from the uploaded resume text.
    """
    text_lower = text.lower()

    # Extract sentences / bullets for improvements
    lines = [line.strip()
             for line in text.split("\n") if len(line.strip()) > 15]

    # Simple bullet/statement extract
    bullet_candidates = [
        cand for cand in lines if any(
            cand.startswith(ch) for ch in [
                '•',
                '-',
                '*',
                '▪',
                '1.',
                '2.',
                '3.']) or len(cand) > 30]
    if not bullet_candidates:
        bullet_candidates = lines[:5]

    sample_bullet = bullet_candidates[0] if bullet_candidates else "Created a web application using React and Node.js."
    sample_bullet_clean = re.sub(r'^[•\-\*\d\.\s]+', '', sample_bullet).strip()

    # Detect technologies present
    tech_keywords = {
        "Languages": ["python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "html", "css", "sql"],
        "Frameworks": ["react", "next.js", "vue", "angular", "node.js", "express", "fastapi", "django", "flask", "spring boot", "tailwind"],
        "Databases": ["postgresql", "postgres", "mongodb", "mysql", "redis", "sqlite", "dynamodb"],
        "Tools": ["git", "docker", "kubernetes", "jira", "vite", "webpack", "npm", "postman"],
        "Cloud": ["aws", "gcp", "azure", "vercel", "netlify", "docker"],
        "Concepts": ["rest api", "graphql", "microservices", "ci/cd", "agile", "unit testing", "system design", "object-oriented programming"]
    }

    matched_by_cat = {
        "Languages": [],
        "Frameworks": [],
        "Databases": [],
        "Tools": [],
        "Cloud": [],
        "Concepts": []}
    all_matched = []

    for cat, kw_list in tech_keywords.items():
        for kw in kw_list:
            if kw in text_lower:
                matched_by_cat[cat].append(
                    kw.title() if len(kw) <= 4 or kw in [
                        "fastapi", "django", "flask"] else kw.capitalize())
                all_matched.append(kw.title())

    # Formulate improvements based on real text content
    improvements = []
    if sample_bullet_clean:
        improvements.append(ImprovementItem(
            priority="High",
            current=sample_bullet_clean[:120],
            problem="The bullet point describes actions at a high level without detailing specific impact or technical depth.",
            recommended_change=f"Engineered key functionality in {
                sample_bullet_clean[
                    :60]} using modern architectural practices, enhancing responsiveness and maintainability.",
            reason="Using active verbs and highlighting functional impact makes the achievement significantly more compelling to engineering hiring managers."
        ))

    if not sections_map.get("summary"):
        improvements.append(ImprovementItem(
            priority="High",
            current="[Missing Section] Professional Summary",
            problem="Resume lacks a concise top summary outlining your core technical stack and target role.",
            recommended_change="Add a 2-3 line Professional Summary at the top highlighting key experience, main technologies (e.g. Python, React), and focus areas.",
            reason="A clear summary grounds the recruiter's understanding of your professional profile within the first 6 seconds.",
        ))

    improvements.append(ImprovementItem(
        priority="Medium",
        current="Listed technical skills in an unstructured format.",
        problem="Grouped skills without category headers can slow down recruiter scanning.",
        recommended_change="Categorize skills clearly into 'Languages', 'Frameworks & Libraries', 'Databases', and 'Developer Tools'.",
        reason="Categorization improves readability and enables instant skill identification during recruiter screens."
    ))

    # Determine roles match based on detected skills
    roles = []
    has_python = any(
        k in text_lower for k in [
            "python",
            "fastapi",
            "django",
            "flask"])
    has_frontend = any(
        k in text_lower for k in [
            "react",
            "javascript",
            "typescript",
            "html",
            "css",
            "tailwind",
            "vue"])
    has_backend = any(
        k in text_lower for k in [
            "node.js",
            "fastapi",
            "python",
            "express",
            "sql",
            "postgresql",
            "mongodb"])

    if has_python and has_frontend and has_backend:
        roles.append(RoleRecommendation(
            role="Full Stack Developer",
            match_percentage=92,
            matching_skills=[s for s in all_matched if s.lower(
            ) in ["python", "react", "javascript", "sql", "git", "rest api"]][:5],
            missing_skills=["Docker", "AWS", "CI/CD"],
            reason="The resume demonstrates hands-on experience across frontend, backend logic, APIs, and data modeling.",
            evidence="Projects and experience sections reference full stack web engineering tools."
        ))

    if has_python:
        roles.append(RoleRecommendation(
            role="Python Developer",
            match_percentage=88,
            matching_skills=[s for s in all_matched if s.lower(
            ) in ["python", "fastapi", "django", "sql", "git"]][:5],
            missing_skills=["PyTest", "Celery"],
            reason="Strong presence of Python and associated ecosystem tools detected.",
            evidence="Code samples, projects, or work history explicitly mention Python development."
        ))

    if has_backend:
        roles.append(RoleRecommendation(
            role="Backend Developer",
            match_percentage=84,
            matching_skills=[s for s in all_matched if s.lower(
            ) in ["python", "node.js", "postgresql", "sql", "rest api"]][:5],
            missing_skills=["Microservices", "Redis", "Docker"],
            reason="Good foundational backend and database manipulation indicators.",
            evidence="Backend framework and API handling keywords identified."
        ))

    roles.append(RoleRecommendation(
        role="AI / Software Application Engineer",
        match_percentage=80,
        matching_skills=[s for s in all_matched if s.lower(
        ) in ["python", "javascript", "git", "rest api"]][:5],
        missing_skills=["LangChain", "Vector DBs", "PyTorch"],
        reason="Solid general software development skills that translate well to modern AI application engineering.",
        evidence="Demonstrates core programming proficiency and project building capabilities."
    ))

    # Job description matching if supplied
    job_match_score = None
    job_match_details = None
    if job_description and len(job_description.strip()) > 20:
        jd_lower = job_description.lower()

        # Check matching skills between resume and JD
        jd_tech_keywords = [kw for cat in tech_keywords.values()
                            for kw in cat if kw in jd_lower]
        matched_jd_skills = [kw.title()
                             for kw in jd_tech_keywords if kw in text_lower]
        missing_jd_skills = [kw.title()
                             for kw in jd_tech_keywords if kw not in text_lower]

        # Deduplicate
        matched_jd_skills = list(dict.fromkeys(matched_jd_skills))
        missing_jd_skills = list(dict.fromkeys(missing_jd_skills))

        total_req = len(matched_jd_skills) + len(missing_jd_skills)
        if total_req > 0:
            calc_score = int((len(matched_jd_skills) / total_req) * 100)
            job_match_score = min(98, max(45, calc_score))
        else:
            job_match_score = 75

        job_match_details = JobMatchDetails(
            job_match_score=job_match_score,
            matched_skills=matched_jd_skills or ["Python", "Git", "REST APIs"],
            missing_skills=missing_jd_skills or ["Docker", "AWS"],
            partial_matches=["System Design", "Agile Methodologies"],
            recommendations=[
                (
                    f"Highlight your experience with {', '.join(matched_jd_skills[:3])} near the top of your resume."
                    if matched_jd_skills
                    else "Highlight your most relevant technical skills near the top of your resume."
                ),
                (
                    f"Add experience with {missing_jd_skills[0]} ONLY if you genuinely have used it in prior projects or coursework."
                    if missing_jd_skills
                    else "Tailor project descriptions to closely match keywords in the targeted job description."
                ),
            ]
        )

    # Content Score calculation
    content_score = 78
    if len(bullet_candidates) >= 4:
        content_score += 5
    if len(all_matched) >= 6:
        content_score += 7
    if sections_map.get("summary"):
        content_score += 5
    content_score = min(98, max(50, content_score))

    # Overall Score formula (weighted average)
    overall_score = int(
        (structure_score * 0.25) +
        (ats_score * 0.35) +
        (content_score * 0.40)
    )

    strengths = [
        "Strong foundation in core technical technologies.",
        "Clear section divisions for primary categories.",
        "Readable PDF layout with extractable text structure."
    ]
    if sections_map.get("education"):
        strengths.append("Clearly stated Education section.")
    if len(all_matched) >= 5:
        strengths.append(
            f"Demonstrates relevant tech stack keywords ({', '.join(all_matched[:4])}).")

    problems = [
        "Some bullet points lack quantifiable business or technical metrics.",
        "Potential layout or formatting adjustments needed for maximum ATS score."
    ]
    if not sections_map.get("summary"):
        problems.append("Missing a concise top Professional Summary.")

    return ResumeAnalysisResponse(
        overall_score=overall_score,
        structure_score=structure_score,
        ats_score=ats_score,
        content_score=content_score,
        sections=sections_map,
        section_details=section_details,
        ats_issues=ats_issues,
        strengths=strengths,
        problems=problems,
        improvements=improvements,
        roles=roles,
        keywords=KeywordAnalysis(
            matched=all_matched,
            missing=["Docker", "AWS", "CI/CD", "Kubernetes"],
            partial=["REST APIs", "Unit Testing"],
            categorized=matched_by_cat
        ),
        job_match_score=job_match_score,
        job_match_details=job_match_details,
        filename=pdf_meta.get("filename"),
        text_length=pdf_meta.get("character_count", 0)
    )


def analyze_resume_with_gemini(
    pdf_meta: dict[str, Any],
    job_description: str | None = None,
    filename: str | None = None
) -> ResumeAnalysisResponse:
    """
    Main entry point for analyzing a resume.
    Calculates deterministic ATS and Structure scores, then invokes Gemini API for deep semantic evaluation.
    Falls back gracefully to intelligent mock analysis if Gemini API is not configured or encounters error.
    Deterministic Privacy Guardrail: All Personally Identifiable Information (PII) is redacted BEFORE external AI processing.
    """
    pdf_meta["filename"] = filename
    structure_score, ats_score, sections_map, section_details, ats_issues = analyze_structure_and_ats(
        pdf_meta)
    resume_text = pdf_meta["text"]

    # Deterministic Privacy Guardrail: Detect and redact PII before external
    # AI processing
    redacted_resume_text, _ = redact_pii(resume_text)
    redacted_job_description = None
    if job_description:
        redacted_job_description, _ = redact_pii(job_description)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # If no valid API key is set, use intelligent mock response with sanitized
    # text
    if not api_key or api_key == "your_gemini_api_key_here":
        return generate_mock_fallback_analysis(
            text=redacted_resume_text,
            pdf_meta=pdf_meta,
            structure_score=structure_score,
            ats_score=ats_score,
            sections_map=sections_map,
            section_details=section_details,
            ats_issues=ats_issues,
            job_description=redacted_job_description
        )

    # Call Gemini API using google-genai standard SDK with PII-redacted text
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
        RESUME TEXT:
        ---
        {redacted_resume_text}
        ---

        OPTIONAL JOB DESCRIPTION:
        ---
        {redacted_job_description or "None provided."}
        ---

        DETERMINISTIC ATS & STRUCTURE EVALUATION (Reference metadata):
        - Calculated Structure Score: {structure_score}/100
        - Calculated Estimated ATS Score: {ats_score}/100
        - Detected Sections: {json.dumps(sections_map)}

        Generate structured JSON matching this schema:
        {{
            "content_score": integer (0-100),
            "strengths": [array of strings],
            "problems": [array of strings],
            "improvements": [
                {{
                    "priority": "High" | "Medium" | "Low",
                    "current": "exact line or phrase from resume",
                    "problem": "explanation of problem",
                    "recommended_change": "improved rewrite",
                    "reason": "explanation of why it is better"
                }}
            ],
            "roles": [
                {{
                    "role": "Role Title",
                    "match_percentage": integer (0-100),
                    "matching_skills": ["skill1", "skill2"],
                    "missing_skills": ["skillA", "skillB"],
                    "reason": "explanation",
                    "evidence": "evidence from resume"
                }}
            ],
            "keywords": {{
                "matched": ["skill1"],
                "missing": ["skill2"],
                "partial": ["skill3"],
                "categorized": {{
                    "Languages": [],
                    "Frameworks": [],
                    "Databases": [],
                    "Tools": [],
                    "Cloud": [],
                    "Concepts": []
                }}
            }},
            "job_match_score": integer or null (if job description provided),
            "job_match_details": {{
                "job_match_score": integer,
                "matched_skills": [],
                "missing_skills": [],
                "partial_matches": [],
                "recommendations": []
            }} or null
        }}
        """

        # Choose fast and reliable model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_SYSTEM_INSTRUCTIONS,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        resp_text = response.text
        if not resp_text:
            raise ValueError("AI model returned an empty response")

        data = json.loads(resp_text)

        # Combine deterministic scores with AI output
        c_score = data.get("content_score", 78)
        overall_score = int((structure_score * 0.25) +
                            (ats_score * 0.35) + (c_score * 0.40))

        # Parse improvements into objects with defense-in-depth PII redaction
        improvements_list = []
        for imp in data.get("improvements", []):
            clean_curr, _ = redact_pii(imp.get("current", ""))
            clean_rec, _ = redact_pii(imp.get("recommended_change", ""))
            improvements_list.append(ImprovementItem(
                priority=imp.get("priority", "Medium"),
                current=clean_curr,
                problem=imp.get("problem", ""),
                recommended_change=clean_rec,
                reason=imp.get("reason", "")
            ))

        # Parse roles into objects with defense-in-depth PII redaction
        roles_list = []
        for r in data.get("roles", []):
            clean_evidence, _ = redact_pii(r.get("evidence", ""))
            roles_list.append(RoleRecommendation(
                role=r.get("role", ""),
                match_percentage=r.get("match_percentage", 80),
                matching_skills=r.get("matching_skills", []),
                missing_skills=r.get("missing_skills", []),
                reason=r.get("reason", ""),
                evidence=clean_evidence
            ))

        # Job match details
        jm_score = data.get("job_match_score")
        jm_details = None
        if data.get("job_match_details"):
            d = data["job_match_details"]
            jm_details = JobMatchDetails(
                job_match_score=d.get("job_match_score", jm_score or 75),
                matched_skills=d.get("matched_skills", []),
                missing_skills=d.get("missing_skills", []),
                partial_matches=d.get("partial_matches", []),
                recommendations=d.get("recommendations", [])
            )

        kw_data = data.get("keywords", {})

        return ResumeAnalysisResponse(
            overall_score=overall_score,
            structure_score=structure_score,
            ats_score=ats_score,
            content_score=c_score,
            sections=sections_map,
            section_details=section_details,
            ats_issues=ats_issues,
            strengths=data.get("strengths", []),
            problems=data.get("problems", []),
            improvements=improvements_list,
            roles=roles_list,
            keywords=KeywordAnalysis(
                matched=kw_data.get("matched", []),
                missing=kw_data.get("missing", []),
                partial=kw_data.get("partial", []),
                categorized=kw_data.get("categorized", {})
            ),
            job_match_score=jm_score,
            job_match_details=jm_details,
            filename=filename,
            text_length=pdf_meta.get("character_count", 0)
        )

    except Exception as e:
        safe_msg = sanitize_log_message(str(e))
        import logging
        logging.getLogger("resume_analyzer").warning(
            f"Gemini API call failed or unparseable: {safe_msg}. Falling back to heuristic analysis.")
        return generate_mock_fallback_analysis(
            text=redacted_resume_text,
            pdf_meta=pdf_meta,
            structure_score=structure_score,
            ats_score=ats_score,
            sections_map=sections_map,
            section_details=section_details,
            ats_issues=ats_issues,
            job_description=redacted_job_description
        )
