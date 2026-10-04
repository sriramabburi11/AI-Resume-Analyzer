import pymupdf as fitz
import json
from services.pdf_parser import extract_resume_text
from services.ats_analyzer import analyze_structure_and_ats
from services.resume_analyzer import analyze_resume_with_gemini

def create_sample_resume_pdf():
    doc = fitz.open()
    page = doc.new_page()
    
    resume_content = """
    Alex Mercer
    Email: alex.mercer@example.com | Phone: (555) 019-2834 | Location: San Francisco, CA
    LinkedIn: linkedin.com/in/alexmercer | GitHub: github.com/alexmercer

    Professional Summary
    Results-oriented Full Stack Software Engineer with 4+ years of experience building scalable web applications, REST APIs, and microservices using Python, React, and PostgreSQL.

    Technical Arsenal
    • Languages: Python, JavaScript, TypeScript, SQL, HTML/CSS
    • Frameworks: React, Node.js, FastAPI, Express, Django, Tailwind CSS
    • Databases: PostgreSQL, MongoDB, Redis
    • Developer Tools: Git, Docker, Vite, Postman, Linux

    Work Experience
    Senior Software Engineer — TechCorp Inc. (Jan 2022 - Present)
    • Created a website using React and Node.js for client dashboard.
    • Architected high-throughput REST APIs using FastAPI and PostgreSQL, serving 500k monthly active users.
    • Reduced API latency by 35% through query optimization and caching strategies.

    Projects
    AI Resume Optimizer (2024)
    • Developed a responsive web application leveraging FastAPI and Gemini API for automated resume ATS feedback.

    Education
    B.S. in Computer Science — University of California, Berkeley (2018 - 2022)
    """
    
    page.insert_text((50, 50), resume_content, fontsize=10)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def main():
    print("--- Creating Sample Resume PDF ---")
    pdf_bytes = create_sample_resume_pdf()
    
    print("\n--- Testing PDF Text Extraction ---")
    meta = extract_resume_text(pdf_bytes)
    print(f"Extracted Word Count: {meta['word_count']}")
    print(f"Contact Info: {meta['contact_info']}")
    
    print("\n--- Testing ATS & Structure Analysis ---")
    s_score, a_score, s_map, s_details, a_issues = analyze_structure_and_ats(meta)
    print(f"Structure Score: {s_score}/100")
    print(f"ATS Score: {a_score}/100")
    print(f"Detected Sections: {json.dumps(s_map, indent=2)}")
    
    print("\n--- Testing Complete Resume Analysis Engine ---")
    result = analyze_resume_with_gemini(
        pdf_meta=meta,
        job_description="Seeking a Senior Full Stack Engineer proficient in Python, React, Docker, and AWS.",
        filename="alex_mercer_resume.pdf"
    )
    
    print(f"Overall Score: {result.overall_score}/100")
    print(f"Content Score: {result.content_score}/100")
    print(f"Recommended Roles Count: {len(result.roles)}")
    print(f"Improvements Count: {len(result.improvements)}")
    print(f"Job Match Score: {result.job_match_score}%")
    
    print("\n✓ Sample test completed successfully!")

if __name__ == "__main__":
    main()
