# AI Resume Analyzer & ATS Optimizer

An end-to-end web application that allows users to upload a PDF resume and receive automated structure analysis, ATS compatibility scoring, exact line-by-line recommendations, suitable job role recommendations, keyword categorization, and optional job description matching.

---

## 🌟 Key Features

1. **PDF Resume Upload**: Drag-and-drop or click to upload PDF resumes (validated format & size limit).
2. **PDF Text & Layout Extraction**: In-memory text extraction and structural feature auditing via PyMuPDF.
3. **Resume Structure Analysis**: Section completeness check (Contact, Summary, Skills, Experience, Projects, Education, etc.) with non-standard section title recommendations (e.g. recommending *"Technical Skills"* over *"Technical Arsenal"*).
4. **Estimated ATS Compatibility**: Diagnostic checks for multi-column layouts, graphics/images, border tables, contact details, date formatting, and decorative symbols.
5. **Exact Improvements**: Structured recommendations enforcing the format:
   `CURRENT` → `PROBLEM` → `RECOMMENDED CHANGE` → `REASON` → `PRIORITY`
6. **Role Recommendation Engine**: Recommends 4-6 target software roles with match percentages, matching skills, missing skills, and evidence.
7. **Optional Job Description Matching**: Match score calculation, matched vs. missing skill identification, and targeted resume tailoring suggestions without fake keyword stuffing.
8. **Categorized Keyword Analysis**: Categorizes extracted keywords into Languages, Frameworks, Databases, Tools, Cloud, and Engineering Concepts.
9. **Resume Quality Scores**: Overall score calculated from weighted Structure, ATS, and Content quality metrics.
10. **Modern SaaS Dashboard**: Interactive tabbed navigation, score gauges, progress bars, and clean responsive layout.

---

## 🏗️ Architecture & Technology Stack

```text
React (Vite + Tailwind CSS)
       │
       ▼ (REST API / multipart form-data)
FastAPI Backend (Python 3.13)
       │
       ├── PyMuPDF (PDF Text & Layout Heuristics)
       ├── ATS & Structure Rules Engine
       └── Gemini API (google-genai SDK) / Intelligent Heuristic Fallback
```

* **Frontend**: React, Vite, Tailwind CSS, Lucide Icons.
* **Backend**: FastAPI, PyMuPDF, Pydantic v2, Python-Dotenv, Google GenAI SDK.
* **Database**: None (Stateless in-memory processing for maximum privacy).

---

## 🚀 Quick Start Instructions

### 1. Environment Setup (Backend)

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your Gemini API Key in `.env`:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
   *(Note: If `GEMINI_API_KEY` is not provided, the application will automatically fall back to an intelligent heuristic mock engine so you can test the UI out of the box).*

5. Start the FastAPI backend server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The backend API will run at `http://127.0.0.1:8000`.

---

### 2. Frontend Setup

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

## 🧪 Testing Backend Integration

Run the built-in test suite to verify text extraction, section audit, and API response schema formatting:
```bash
./backend/venv/bin/python backend/test_resume_analyzer.py
```

---

## 🔒 Privacy & Security

* **No Storage**: Uploaded files are processed strictly in memory and are discarded immediately after response generation.
* **Key Protection**: Gemini API key is stored exclusively in the backend `.env` file and is never exposed to the client.
