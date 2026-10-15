import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from services.supabase_service import get_supabase_client, check_supabase_connection
from services.pdf_parser import extract_resume_text
import pymupdf as fitz

client = TestClient(app)

class TestSupabaseIntegration(unittest.TestCase):

    def test_01_health_check(self):
        """Verifies health check endpoint returns 200 with Supabase provider."""
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("provider"), "Supabase Cloud")
        print("✓ Health check endpoint successfully verified.")

    def test_02_supabase_client_singleton(self):
        """Verifies Supabase client can be created with configured environment variables."""
        supabase_client = get_supabase_client()
        self.assertIsNotNone(supabase_client)
        conn_check = check_supabase_connection()
        self.assertEqual(conn_check.get("status"), "connected")
        print("✓ Supabase client singleton initialized and connected.")

    def test_03_protected_route_rejection(self):
        """Ensures /api/analyze-resume and /api/history strictly reject requests without Bearer token."""
        # 1. Test /api/analyze-resume without token
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test Resume Content with Skills", fontsize=10)
        pdf_bytes = doc.write()
        doc.close()

        res_analyze = client.post(
            "/api/analyze-resume",
            files={"resume": ("test.pdf", pdf_bytes, "application/pdf")}
        )
        self.assertEqual(res_analyze.status_code, 401)
        self.assertIn("Authentication token required", res_analyze.json().get("detail", ""))

        # 2. Test /api/history without token
        res_history = client.get("/api/history")
        self.assertEqual(res_history.status_code, 401)
        print("✓ Route security verified: unauthenticated requests correctly rejected with 401.")

    def test_04_pdf_in_memory_processing(self):
        """Verifies PDF extraction operates strictly in-memory."""
        with open("sample_resume.pdf", "rb") as f:
            pdf_bytes = f.read()

        meta = extract_resume_text(pdf_bytes)
        self.assertIn("Full Stack", meta["text"])
        self.assertTrue(meta["contact_info"]["has_email"])
        print("✓ In-memory PDF text extraction verified.")

if __name__ == "__main__":
    unittest.main()
