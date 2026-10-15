# AI Resume Analyzer & ATS Optimizer

An end-to-end web application that allows users to upload a PDF resume and receive automated structure analysis, ATS compatibility scoring, exact line-by-line recommendations, suitable job role recommendations, keyword categorization, and optional job description matching — powered by **Supabase Database & Authentication** and **Google Gemini AI**.

---

## 🌟 Key Features

1. **PDF Resume Upload**: Drag-and-drop or click to upload PDF resumes (validated format & size limit).
2. **PDF Text & Layout Extraction**: In-memory text extraction and structural feature auditing via PyMuPDF.
3. **Resume Structure Analysis**: Section completeness check (Contact, Summary, Skills, Experience, Projects, Education, etc.) with non-standard section title recommendations.
4. **Estimated ATS Compatibility**: Diagnostic checks for multi-column layouts, graphics/images, border tables, contact details, date formatting, and decorative symbols.
5. **Exact Improvements**: Structured recommendations enforcing the format:
   `CURRENT` → `PROBLEM` → `RECOMMENDED CHANGE` → `REASON` → `PRIORITY`
6. **Role Recommendation Engine**: Recommends 4-6 target software roles with match percentages, matching skills, missing skills, and evidence.
7. **Optional Job Description Matching**: Match score calculation, matched vs. missing skill identification, and targeted resume tailoring suggestions without fake keyword stuffing.
8. **Categorized Keyword Analysis**: Categorizes extracted keywords into Languages, Frameworks, Databases, Tools, Cloud, and Engineering Concepts.
9. **User Authentication & History**: Integrated with **Supabase Auth** (Sign-up, Sign-in, Password Reset) and **Supabase Database** with Row Level Security (RLS) for private analysis history tracking.
10. **Modern SaaS Dashboard**: Interactive tabbed navigation, score gauges, progress bars, and clean responsive layout.

---

## 🏗️ Architecture & Technology Stack

```text
React (Vite + Tailwind CSS + @supabase/supabase-js)
       │
       ├── Supabase Auth (Sign up / Sign in / Session persistence)
       │
       ▼ (REST API / JSON & multipart form-data)
FastAPI Backend (Python 3.13)
       │
       ├── Supabase Cloud Database (PostgreSQL + Row Level Security)
       ├── PyMuPDF (In-Memory PDF Text & Layout Heuristics)
       ├── ATS & Structure Rules Engine
       └── Gemini API (google-genai SDK) / Intelligent Heuristic Fallback
```

* **Frontend**: React, Vite, Tailwind CSS, `@supabase/supabase-js`, Lucide Icons.
* **Backend**: FastAPI, `supabase` Python SDK, PyMuPDF, Pydantic v2, Python-dotenv.
* **Database & Auth**: Supabase Cloud PostgreSQL with Row Level Security (RLS) policies.
* **Privacy**: Uploaded resumes are processed strictly in-memory; raw PDF files are never stored on disk.

---

## 🚀 Quick Start Instructions

### 1. Supabase Database Schema Setup

1. Open your [Supabase Project Dashboard](https://supabase.com/dashboard).
2. Navigate to the **SQL Editor** tab.
3. Open and run the migration script:
   [`supabase/migrations/20261015000000_create_resume_analyzer_schema.sql`](supabase/migrations/20261015000000_create_resume_analyzer_schema.sql).
4. This script creates the `profiles` and `resume_analyses` tables, triggers, performance indexes, and configures Row Level Security (RLS) policies.

---

### 2. Backend Setup

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

4. Configure environment variables in `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   ```

5. Start the FastAPI backend server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The backend API will run at `http://127.0.0.1:8000`. API docs are available at `http://127.0.0.1:8000/docs`.

---

### 3. Frontend Setup

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables in `frontend/.env`:
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

## 🧪 Testing Backend Integration

Run the built-in test suite to verify Supabase connectivity, route security, and the resume analysis engine:
```bash
./backend/venv/bin/python backend/test_supabase_integration.py
./backend/venv/bin/python backend/test_resume_analyzer.py
```

---

## 🔒 Privacy & Security

* **In-Memory Processing**: Uploaded PDF files are read and processed entirely in memory and discarded immediately after response generation.
* **Row Level Security (RLS)**: User resume history is isolated via Supabase RLS so users can only access their own analysis records.
* **Role Separation**: Client application uses the anonymous publishable key, while privileged database operations use the server-only service-role key.
