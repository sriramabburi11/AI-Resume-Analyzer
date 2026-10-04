from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

from services.pdf_parser import extract_resume_text, PDFParsingError
from services.resume_analyzer import analyze_resume_with_gemini
from schemas.resume_schema import ResumeAnalysisResponse

app = FastAPI(
    title="AI Resume Analyzer & ATS Optimizer API",
    description="API for analyzing resumes, ATS compatibility, role matching, and resume improvements.",
    version="1.0.0"
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
    return {"status": "ok"}

@app.post("/api/analyze-resume", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: Optional[str] = Form(None)
):
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

        # 2. Extract text and metadata
        pdf_meta = extract_resume_text(contents)
        
        # 3. Analyze resume
        analysis_result = analyze_resume_with_gemini(
            pdf_meta=pdf_meta,
            job_description=job_description,
            filename=resume.filename
        )

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
