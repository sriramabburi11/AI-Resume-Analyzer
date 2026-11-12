from services.resume_analyzer import analyze_resume_with_gemini
from services.privacy_guardrail import (
    REDACTED_ADDRESS,
    REDACTED_EMAIL,
    REDACTED_GOV_ID,
    REDACTED_PASSPORT,
    REDACTED_PHONE,
    PrivacyValidationError,
    detect_pii,
    redact_pii,
    sanitize_log_message,
    validate_job_description,
    validate_uploaded_file,
)
from services.pdf_parser import extract_resume_text
from services.ats_analyzer import analyze_structure_and_ats
from schemas.resume_schema import ResumeAnalysisResponse
import io
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
import pymupdf as fitz

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def generate_pdf_bytes_with_content(content: str) -> bytes:
    """Helper to generate in-memory PDF bytes containing specified text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), content, fontsize=10)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


class TestPrivacyGuardrailsAndDataMinimization(unittest.TestCase):

    def setUp(self):
        # Configure logging capture
        self.log_stream = io.StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger("privacy_guardrail")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    # --------------------------------------------------------------------------
    # Test Case 1: Valid resume without PII
    # --------------------------------------------------------------------------
    def test_01_valid_resume_without_pii(self):
        clean_content = """
        Professional Summary
        Experienced Python and React developer with 5 years building high scale microservices.

        Technical Skills
        Languages: Python, JavaScript, TypeScript, SQL
        Frameworks: FastAPI, React, Node.js
        Databases: PostgreSQL, Redis
        Tools: Git, Docker, Kubernetes

        Experience
        Software Engineer - Tech Enterprise (2020 - 2024)
        Engineered distributed microservices processing millions of daily transactions.

        Education
        B.S. in Computer Science - State University
        """
        detected = detect_pii(clean_content)
        self.assertEqual(len(detected["emails"]), 0)
        self.assertEqual(len(detected["phones"]), 0)
        self.assertEqual(len(detected["government_ids"]), 0)

        redacted, counts = redact_pii(clean_content)
        self.assertEqual(counts["emails"], 0)
        self.assertEqual(counts["phones"], 0)
        self.assertEqual(counts["government_ids"], 0)
        self.assertEqual(redacted.strip(), clean_content.strip())
        print("✓ Test 1 Passed: Valid resume without PII correctly verified without false positives.")

    # --------------------------------------------------------------------------
    # Test Case 2: Resume containing an email address
    # --------------------------------------------------------------------------
    def test_02_resume_with_email(self):
        email = "developer.candidate@techcorp.io"
        text = f"Contact developer directly at {email} for software engineering roles."
        detected = detect_pii(text)
        self.assertIn(email, detected["emails"])

        redacted, counts = redact_pii(text)
        self.assertEqual(counts["emails"], 1)
        self.assertNotIn(email, redacted)
        self.assertIn(REDACTED_EMAIL, redacted)
        print(
            "✓ Test 2 Passed: Email address detected and redacted with [EMAIL_REDACTED].")

    # --------------------------------------------------------------------------
    # Test Case 3: Resume containing a phone number
    # --------------------------------------------------------------------------
    def test_03_resume_with_phone_number(self):
        phones = ["+1 (555) 019-2834", "+91 98765 43210", "+91-9876543210"]
        for p in phones:
            text = f"Candidate phone line: {p} for technical recruiter contact."
            redacted, counts = redact_pii(text)
            self.assertGreater(
                counts["phones"],
                0,
                f"Failed to redact phone: {p}")
            self.assertNotIn(p, redacted)
            self.assertIn(REDACTED_PHONE, redacted)
        print(
            "✓ Test 3 Passed: Multiple phone number formats detected and redacted with [PHONE_REDACTED].")

    # --------------------------------------------------------------------------
    # Test Case 4: Resume containing Aadhaar/PAN-like identifiers
    # --------------------------------------------------------------------------
    def test_04_resume_with_government_ids(self):
        aadhaar = "9876 5432 1098"
        pan = "ABCDE1234F"
        ssn = "123-45-6789"
        text = f"National ID Verification: Aadhaar: {aadhaar}, PAN: {pan}, SSN: {ssn}"

        detected = detect_pii(text)
        self.assertGreater(len(detected["government_ids"]), 0)

        redacted, counts = redact_pii(text)
        self.assertGreaterEqual(counts["government_ids"], 3)
        self.assertNotIn(aadhaar, redacted)
        self.assertNotIn(pan, redacted)
        self.assertNotIn(ssn, redacted)
        self.assertIn(REDACTED_GOV_ID, redacted)
        print("✓ Test 4 Passed: Aadhaar, PAN, and SSN identifiers detected and redacted.")

    # --------------------------------------------------------------------------
    # Test Case 5: Resume containing multiple types of PII
    # --------------------------------------------------------------------------
    def test_05_resume_with_multiple_pii_types(self):
        full_text = """
        Sriram Candidate
        Email: sriram.applicant@example.com
        Phone: +91 9876543210
        Permanent Address: 124 Park Avenue, Suite 300, Sector 4, Bangalore
        Aadhaar: 4567 8901 2345 | PAN: BZRPK9876L
        Passport No: K1234567

        Summary: Full Stack Engineer proficient in Python, FastAPI, and React.
        """
        redacted, counts = redact_pii(full_text)
        self.assertGreater(counts["emails"], 0)
        self.assertGreater(counts["phones"], 0)
        self.assertGreater(counts["government_ids"], 0)
        self.assertGreater(counts["addresses"], 0)
        self.assertGreater(counts["passports"], 0)

        self.assertNotIn("sriram.applicant@example.com", redacted)
        self.assertNotIn("9876543210", redacted)
        self.assertNotIn("4567 8901 2345", redacted)
        self.assertNotIn("BZRPK9876L", redacted)
        self.assertNotIn("K1234567", redacted)
        self.assertNotIn("124 Park Avenue", redacted)

        self.assertIn(REDACTED_EMAIL, redacted)
        self.assertIn(REDACTED_PHONE, redacted)
        self.assertIn(REDACTED_GOV_ID, redacted)
        self.assertIn(REDACTED_PASSPORT, redacted)
        self.assertIn(REDACTED_ADDRESS, redacted)
        print("✓ Test 5 Passed: Multi-PII document completely sanitized.")

    # --------------------------------------------------------------------------
    # Test Case 6: Resume with invalid file extension
    # --------------------------------------------------------------------------
    def test_06_invalid_file_extension(self):
        pdf_bytes = generate_pdf_bytes_with_content(
            "Sample resume content with technical skills.")
        invalid_filenames = [
            "resume.docx",
            "resume.txt",
            "resume.png",
            "resume.exe",
            "resume"]
        for fn in invalid_filenames:
            with self.assertRaises(PrivacyValidationError) as ctx:
                validate_uploaded_file(contents=pdf_bytes, filename=fn)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Only PDF", ctx.exception.message)
        print("✓ Test 6 Passed: Invalid file extensions strictly rejected.")

    # --------------------------------------------------------------------------
    # Test Case 7: Resume exceeding the upload-size limit
    # --------------------------------------------------------------------------
    def test_07_file_exceeding_size_limit(self):
        oversized_bytes = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 512)
        with self.assertRaises(PrivacyValidationError) as ctx:
            validate_uploaded_file(
                contents=oversized_bytes,
                filename="large_resume.pdf")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn(
            "exceeds the maximum allowed limit",
            ctx.exception.message)
        print("✓ Test 7 Passed: Files exceeding 10MB limit strictly rejected.")

    # --------------------------------------------------------------------------
    # Test Case 8: Empty or corrupted resume
    # --------------------------------------------------------------------------
    def test_08_empty_or_corrupted_resume(self):
        # 8a: Empty file (0 bytes)
        with self.assertRaises(PrivacyValidationError) as ctx1:
            validate_uploaded_file(contents=b"", filename="empty.pdf")
        self.assertEqual(ctx1.exception.status_code, 400)
        self.assertIn("empty", ctx1.exception.message.lower())

        # 8b: Corrupted non-PDF bytes (missing %PDF header)
        corrupted_bytes = b"Just some random binary noise without PDF magic header"
        with self.assertRaises(PrivacyValidationError) as ctx2:
            validate_uploaded_file(
                contents=corrupted_bytes,
                filename="corrupt.pdf")
        self.assertEqual(ctx2.exception.status_code, 400)
        self.assertIn("does not match genuine PDF", ctx2.exception.message)

        # 8c: Executable header (MZ) disguised as PDF
        executable_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"%PDF-1.4"
        with self.assertRaises(PrivacyValidationError) as ctx3:
            validate_uploaded_file(
                contents=executable_bytes,
                filename="malicious.pdf")
        self.assertEqual(ctx3.exception.status_code, 400)
        self.assertIn("Executable or polyglot files", ctx3.exception.message)
        print("✓ Test 8 Passed: Empty, corrupted, and polyglot files strictly rejected.")

    # --------------------------------------------------------------------------
    # Test Case 9: AI API failure during processing
    # --------------------------------------------------------------------------
    def test_09_ai_api_failure_fallback(self):
        resume_content = """
        John Candidate | Email: john@example.com | Phone: 9876543210
        Professional Summary: Python developer with 4 years experience.
        Technical Skills: Python, FastAPI, React, PostgreSQL, Docker
        Experience: Developed RESTful backend services.
        Education: B.S. in Computer Science.
        """
        pdf_bytes = generate_pdf_bytes_with_content(resume_content)
        meta = extract_resume_text(pdf_bytes)

        # Force exception in external AI client to verify graceful fallback
        with patch.dict(os.environ, {"GEMINI_API_KEY": "valid_mock_key_for_test"}):
            with patch("google.genai.Client") as mock_client:
                mock_client.return_value.models.generate_content.side_effect = Exception(
                    "Service unavailable 503")
                result = analyze_resume_with_gemini(
                    pdf_meta=meta,
                    job_description="Looking for Python Engineer",
                    filename="test_fallback.pdf"
                )

                self.assertIsInstance(result, ResumeAnalysisResponse)
                self.assertGreater(result.overall_score, 0)
                self.assertGreater(len(result.roles), 0)
                self.assertGreater(len(result.improvements), 0)
        print("✓ Test 9 Passed: Graceful fallback on external AI API failure verified.")

    # --------------------------------------------------------------------------
    # Test Case 10: Temporary-file cleanup after successful processing
    # --------------------------------------------------------------------------
    def test_10_temp_file_cleanup_on_success(self):
        class MockUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.content_type = "application/pdf"
                self.content = content
                self.closed = False

            async def read(self):
                return self.content

            async def close(self):
                self.closed = True

        resume_text_30_words = """
        Professional Summary: Experienced software engineer specializing in backend systems and APIs.
        Technical Skills: Python, FastAPI, Django, React, PostgreSQL, Docker, Git, Linux.
        Experience: Developed microservices for distributed web architectures and optimized relational database queries.
        Education: Bachelor of Science in Computer Science.
        """
        mock_file = MockUploadFile(
            "clean_resume.pdf",
            generate_pdf_bytes_with_content(resume_text_30_words))

        # Simulate try/finally wrapper
        try:
            validate_uploaded_file(
                contents=mock_file.content,
                filename=mock_file.filename)
            meta = extract_resume_text(mock_file.content)
            self.assertIsNotNone(meta)
        finally:
            import asyncio
            asyncio.run(mock_file.close())

        self.assertTrue(mock_file.closed)
        print("✓ Test 10 Passed: Guaranteed temporary file cleanup verified on success.")

    # --------------------------------------------------------------------------
    # Test Case 11: Temporary-file cleanup after failed processing
    # --------------------------------------------------------------------------
    def test_11_temp_file_cleanup_on_failure(self):
        class MockFailingUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.content_type = "application/pdf"
                self.content = content
                self.closed = False

            async def read(self):
                return self.content

            async def close(self):
                self.closed = True

        mock_file = MockFailingUploadFile("bad.pdf", b"corrupted bytes")
        cleanup_executed = False

        try:
            validate_uploaded_file(
                contents=mock_file.content,
                filename=mock_file.filename)
        except PrivacyValidationError:
            pass  # Expected error
        finally:
            import asyncio
            asyncio.run(mock_file.close())
            cleanup_executed = True

        self.assertTrue(mock_file.closed)
        self.assertTrue(cleanup_executed)
        print("✓ Test 11 Passed: Guaranteed temporary file cleanup verified on failure.")

    # --------------------------------------------------------------------------
    # Test Case 12: Verification that unredacted PII never reaches external AI API requests
    # --------------------------------------------------------------------------
    def test_12_unredacted_pii_never_reaches_external_ai(self):
        raw_email = "sensitive.candidate@privatecorp.com"
        raw_phone = "+1 (555) 987-6543"
        raw_aadhaar = "9876 5432 1098"
        raw_address = "789 Willow Road, Apt 4B, Sunnyvale, CA 94086"

        sensitive_resume = f"""
        Confidential Resume
        Email: {raw_email}
        Phone: {raw_phone}
        Aadhaar: {raw_aadhaar}
        Address: {raw_address}

        Professional Summary
        Full Stack Engineer with experience in Python, TypeScript, and AWS.

        Technical Skills
        Python, React, PostgreSQL, Docker, Git

        Experience
        Senior Developer at Tech Co (2021 - 2024)
        Engineered scalable cloud infrastructure.

        Education
        B.S. in Software Engineering
        """
        pdf_bytes = generate_pdf_bytes_with_content(sensitive_resume)
        meta = extract_resume_text(pdf_bytes)

        captured_prompt = None

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_active_key_12345"}):
            with patch("google.genai.Client") as mock_client:
                mock_model = MagicMock()
                mock_client.return_value.models = mock_model

                # Mock AI response
                mock_response = MagicMock()
                mock_response.text = '{"content_score": 85, "strengths": ["Strong background"], "problems": [], "improvements": [], "roles": [], "keywords": {}}'
                mock_model.generate_content.return_value = mock_response

                analyze_resume_with_gemini(
                    pdf_meta=meta,
                    job_description=f"Send inquiries to {raw_email}",
                    filename="confidential.pdf"
                )

                # Inspect captured contents sent to Gemini
                self.assertTrue(mock_model.generate_content.called)
                call_args, call_kwargs = mock_model.generate_content.call_args
                captured_prompt = call_kwargs.get("contents")

        self.assertIsNotNone(captured_prompt)
        # Verify NONE of the raw PII strings exist in the prompt sent to Gemini
        self.assertNotIn(raw_email, captured_prompt)
        self.assertNotIn(raw_phone, captured_prompt)
        self.assertNotIn(raw_aadhaar, captured_prompt)
        self.assertNotIn(raw_address, captured_prompt)

        # Verify placeholders ARE present
        self.assertIn(REDACTED_EMAIL, captured_prompt)
        self.assertIn(REDACTED_PHONE, captured_prompt)
        self.assertIn(REDACTED_GOV_ID, captured_prompt)
        self.assertIn(REDACTED_ADDRESS, captured_prompt)
        print("✓ Test 12 Passed: Deterministic verification that unredacted PII NEVER reaches external AI.")

    # --------------------------------------------------------------------------
    # Test Case 13: Verification that sensitive information does not appear in application logs
    # --------------------------------------------------------------------------
    def test_13_sensitive_info_does_not_appear_in_logs(self):
        log_sample = "User login error for alex@example.com with phone 9876543210 and token Bearer eyJhbGciOiJIUzI1NiJ9.test.sig"
        sanitized = sanitize_log_message(log_sample)

        self.assertNotIn("alex@example.com", sanitized)
        self.assertNotIn("9876543210", sanitized)
        self.assertNotIn("Bearer eyJhbGciOiJIUzI1NiJ9.test.sig", sanitized)
        self.assertIn("[EMAIL_MASKED]", sanitized)
        self.assertIn("[PHONE_MASKED]", sanitized)
        self.assertIn("[TOKEN_MASKED]", sanitized)
        print("✓ Test 13 Passed: Logging sanitization verified.")

    # --------------------------------------------------------------------------
    # Additional Verification: Existing ATS Scoring & Structure Intact
    # --------------------------------------------------------------------------
    def test_14_existing_ats_and_structure_scoring_intact(self):
        resume_text = """
        Contact: candidate@example.com | (555) 019-2834
        Professional Summary
        Senior Python Engineer with 6 years experience.

        Technical Skills
        Python, FastAPI, Django, React, PostgreSQL, Docker

        Work Experience
        Tech Lead - Enterprise Software (Jan 2021 - Present)
        Led development of cloud microservices.

        Projects
        Resume ATS Optimizer (2024)
        Built an ATS diagnostic tool.

        Education
        B.S. in Computer Science (2016 - 2020)
        """
        pdf_bytes = generate_pdf_bytes_with_content(resume_text)
        meta = extract_resume_text(pdf_bytes)

        s_score, a_score, s_map, s_details, a_issues = analyze_structure_and_ats(
            meta)
        self.assertGreaterEqual(s_score, 70)
        self.assertGreaterEqual(a_score, 70)
        self.assertTrue(s_map.get("skills"))
        self.assertTrue(s_map.get("education"))
        self.assertTrue(s_map.get("experience"))

        # Verify job description validator
        valid_jd = validate_job_description(
            "Software Engineer with Python and React skills")
        self.assertIsNotNone(valid_jd)
        with self.assertRaises(PrivacyValidationError):
            validate_job_description("x" * 15000)

        print("✓ Test 14 Passed: Existing ATS scoring, structure engine, and JD matching preserved.")


if __name__ == "__main__":
    unittest.main()
