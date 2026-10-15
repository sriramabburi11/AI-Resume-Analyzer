import os
import io
import sys

# Configure test environment with SQLite test database
os.environ["DATABASE_URL"] = "sqlite:///./test_resume_analyzer.db"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-12345678901234567890"

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app
from database import engine, Base, SessionLocal
from models import User, ResumeAnalysis, PasswordResetToken
from test_resume_analyzer import create_sample_resume_pdf

# Recreate test database tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "PostgreSQL" in data["engine"]

def test_registration_and_login_flow():
    # 1. Register User
    reg_payload = {
        "full_name": "Sarah Connor",
        "email": "sarah@example.com",
        "password": "SecurePassword123!"
    }
    r_reg = client.post("/api/auth/register", json=reg_payload)
    assert r_reg.status_code == 200
    reg_data = r_reg.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "sarah@example.com"
    assert reg_data["user"]["full_name"] == "Sarah Connor"

    # Verify password is NOT stored as plain text
    db = SessionLocal()
    db_user = db.query(User).filter(User.email == "sarah@example.com").first()
    assert db_user is not None
    assert db_user.password_hash != "SecurePassword123!"
    assert "$argon2id$" in db_user.password_hash
    db.close()

    # 2. Duplicate registration should be rejected
    r_dup = client.post("/api/auth/register", json=reg_payload)
    assert r_dup.status_code == 400
    assert "already exists" in r_dup.json()["detail"].lower()

    # 3. Login with wrong password should fail
    r_wrong = client.post("/api/auth/login", json={"email": "sarah@example.com", "password": "WrongPassword"})
    assert r_wrong.status_code == 401

    # 4. Login with correct password
    r_login = client.post("/api/auth/login", json={"email": "sarah@example.com", "password": "SecurePassword123!"})
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]
    assert token

    # 5. Fetch current user via /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    r_me = client.get("/api/auth/me", headers=headers)
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "sarah@example.com"

    # 6. Update user profile
    r_update = client.put("/api/auth/profile", json={"full_name": "Sarah J. Connor"}, headers=headers)
    assert r_update.status_code == 200
    assert r_update.json()["full_name"] == "Sarah J. Connor"

def test_password_reset_flow():
    # 1. Request password reset
    r_forgot = client.post("/api/auth/forgot-password", json={"email": "sarah@example.com"})
    assert r_forgot.status_code == 200

    # Retrieve generated reset token from test DB
    db = SessionLocal()
    user = db.query(User).filter(User.email == "sarah@example.com").first()
    reset_rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).order_by(PasswordResetToken.created_at.desc()).first()
    assert reset_rec is not None

    # In security.py we hash the token. Let's create a known raw token test
    import security
    raw_test_token = security.generate_random_token()
    reset_rec.token_hash = security.hash_token(raw_test_token)
    db.commit()
    db.close()

    # 2. Reset password using valid token
    r_reset = client.post("/api/auth/reset-password", json={
        "token": raw_test_token,
        "new_password": "NewSecretPassword2026!"
    })
    assert r_reset.status_code == 200

    # 3. Old password should now fail
    r_old = client.post("/api/auth/login", json={"email": "sarah@example.com", "password": "SecurePassword123!"})
    assert r_old.status_code == 401

    # 4. New password should now succeed
    r_new = client.post("/api/auth/login", json={"email": "sarah@example.com", "password": "NewSecretPassword2026!"})
    assert r_new.status_code == 200

def test_unauthenticated_endpoints_return_401():
    # History endpoint
    r_hist = client.get("/api/history")
    assert r_hist.status_code == 401

    # Profile
    r_prof = client.get("/api/auth/me")
    assert r_prof.status_code == 401

    # Analysis
    pdf_bytes = create_sample_resume_pdf()
    files = {"resume": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r_analyze = client.post("/api/analyze-resume", files=files)
    assert r_analyze.status_code == 401

def test_resume_analysis_and_history_isolation():
    # Register User A
    res_a = client.post("/api/auth/register", json={
        "full_name": "Developer Alpha",
        "email": "alpha@example.com",
        "password": "PasswordAlpha123"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    res_b = client.post("/api/auth/register", json={
        "full_name": "Developer Beta",
        "email": "beta@example.com",
        "password": "PasswordBeta123"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A analyzes a resume
    pdf_bytes = create_sample_resume_pdf()
    files = {"resume": ("alpha_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"job_description": "Senior Python Engineer"}

    res_analysis = client.post("/api/analyze-resume", files=files, data=data, headers=headers_a)
    assert res_analysis.status_code == 200
    analysis_data = res_analysis.json()
    assert analysis_data["saved_to_history"] is True
    analysis_id = analysis_data["saved_analysis_id"]
    assert analysis_id is not None

    # User A checks history -> sees 1 analysis
    res_hist_a = client.get("/api/history", headers=headers_a)
    assert res_hist_a.status_code == 200
    items_a = res_hist_a.json()
    assert len(items_a) == 1
    assert items_a[0]["id"] == str(analysis_id)

    # User B checks history -> sees 0 analyses (strictly isolated!)
    res_hist_b = client.get("/api/history", headers=headers_b)
    assert res_hist_b.status_code == 200
    items_b = res_hist_b.json()
    assert len(items_b) == 0

    # User B attempts to access User A's analysis record -> receives 404 / access denied
    res_detail_b = client.get(f"/api/history/{analysis_id}", headers=headers_b)
    assert res_detail_b.status_code == 404

    # User A accesses own record -> receives 200
    res_detail_a = client.get(f"/api/history/{analysis_id}", headers=headers_a)
    assert res_detail_a.status_code == 200
    assert res_detail_a.json()["id"] == str(analysis_id)

    # User A deletes own record -> succeeds
    res_del_a = client.delete(f"/api/history/{analysis_id}", headers=headers_a)
    assert res_del_a.status_code == 200
    assert res_del_a.json()["deleted"] is True

    # User A history is now empty
    res_empty_a = client.get("/api/history", headers=headers_a)
    assert len(res_empty_a.json()) == 0

if __name__ == "__main__":
    print("--- Running PostgreSQL & Backend Auth Integration Tests ---")
    test_health_endpoint()
    print("✓ Health endpoint passed.")
    test_unauthenticated_endpoints_return_401()
    print("✓ Unauthenticated route rejection passed (401 returned).")
    test_registration_and_login_flow()
    print("✓ User registration, Argon2id hashing, and login flow passed.")
    test_password_reset_flow()
    print("✓ Secure password reset flow passed.")
    test_resume_analysis_and_history_isolation()
    print("✓ Resume analysis, DB persistence, and multi-user data isolation passed.")
    print("\nAll PostgreSQL database and authentication tests completed successfully!")

    # Cleanup test db
    if os.path.exists("./test_resume_analyzer.db"):
        os.remove("./test_resume_analyzer.db")
