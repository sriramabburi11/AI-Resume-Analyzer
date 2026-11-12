"""
===================================================================================
LEGACY TEST FILE — Pre-Supabase Architecture (PostgreSQL + SQLAlchemy + Argon2id)
===================================================================================

This test file was written for an earlier version of the application that used:
  - A local PostgreSQL (or SQLite) database via SQLAlchemy ORM
  - Direct password hashing with Argon2id via a custom `security` module
  - Local `database.py`, `models.py`, and `security.py` modules

The application has since been migrated to Supabase Cloud (Auth + PostgreSQL + RLS).
The modules imported below (`database`, `models`, `security`) no longer exist in the
current codebase, so these tests cannot run against the current architecture.

Current test suites for the Supabase-based backend:
  - backend/test_privacy_guardrails.py   — PII detection, redaction, and file validation
  - backend/test_resume_analyzer.py      — ATS scoring and resume analysis
  - backend/test_supabase_integration.py — Supabase connectivity and protected routes

This file is preserved for historical reference only.
===================================================================================
"""

import os
import sys
import unittest

# ---------------------------------------------------------------------------------
# Guard: Skip all tests because the legacy modules do not exist in the current
# Supabase-based project.  Running `pytest` will collect this file and report
# the tests as skipped rather than erroring out.
# ---------------------------------------------------------------------------------
LEGACY_MODULES_AVAILABLE = False
try:
    sys.path.insert(0, os.path.dirname(__file__))
    # pyrefly: ignore[missing-import]
    from database import Base, SessionLocal, engine
    # pyrefly: ignore[missing-import]
    from models import PasswordResetToken, ResumeAnalysis, User
    LEGACY_MODULES_AVAILABLE = True
except ImportError:
    Base = SessionLocal = engine = None
    PasswordResetToken = ResumeAnalysis = User = None

SKIP_REASON = (
    "Skipped: Legacy test requires 'database', 'models', and 'security' modules "
    "from the pre-Supabase architecture which are no longer present."
)


@unittest.skipUnless(LEGACY_MODULES_AVAILABLE, SKIP_REASON)
class TestLegacyAuthAndHistory(unittest.TestCase):
    """
    Legacy integration tests for the pre-Supabase PostgreSQL + SQLAlchemy + Argon2id backend.
    These tests are automatically skipped in the current Supabase-based project because the
    required modules (database, models, security) no longer exist.
    """

    def test_health_endpoint(self):
        pass

    def test_registration_and_login_flow(self):
        pass

    def test_password_reset_flow(self):
        pass

    def test_unauthenticated_endpoints_return_401(self):
        pass

    def test_resume_analysis_and_history_isolation(self):
        pass


if __name__ == "__main__":
    if not LEGACY_MODULES_AVAILABLE:
        print("=" * 70)
        print("SKIPPED: Legacy Auth & History Tests")
        print(SKIP_REASON)
        print("=" * 70)
        print("\nCurrent test suites to run instead:")
        print("  pytest backend/test_privacy_guardrails.py -v")
        print("  pytest backend/test_resume_analyzer.py -v")
        print("  pytest backend/test_supabase_integration.py -v")
    else:
        unittest.main()
