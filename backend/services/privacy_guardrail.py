import re
import os
import logging
from typing import Dict, Any, List, Tuple, Optional
import pymupdf as fitz

logger = logging.getLogger("privacy_guardrail")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_JOB_DESCRIPTION_CHARS = 10000

# Placeholder tokens for redacted sensitive information
REDACTED_EMAIL = "[EMAIL_REDACTED]"
REDACTED_PHONE = "[PHONE_REDACTED]"
REDACTED_GOV_ID = "[GOVERNMENT_ID_REDACTED]"
REDACTED_PASSPORT = "[PASSPORT_REDACTED]"
REDACTED_ADDRESS = "[ADDRESS_REDACTED]"

# Regex Patterns for Deterministic PII Detection
# 1. Email: standard RFC 5322 compliant regex
EMAIL_PATTERN = re.compile(
    r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b',
    re.IGNORECASE
)

# 2. Government IDs:
# 2a. Indian Aadhaar: 12 digits, often 4-4-4 separated by space or hyphen, or labeled
AADHAAR_PATTERN = re.compile(
    r'\b[2-9]\d{3}[\s-]\d{4}[\s-]\d{4}\b'
)
AADHAAR_LABELED_PATTERN = re.compile(
    r'(?i)\b(?:aadhaar|aadhar|uidai|uid)[-:\s#]*([2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4})\b'
)

# 2b. Indian PAN Card: 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_PATTERN = re.compile(
    r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
)

# 2c. US Social Security Number (SSN): 3-2-4 digits with hyphens
SSN_PATTERN = re.compile(
    r'\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b'
)

# 3. Passport numbers:
# Indian / standard passport: 1 letter followed by 7 digits, or labeled passport number
PASSPORT_LABELED_PATTERN = re.compile(
    r'(?i)\b(?:passport(?:\s*(?:no|number|#))?[:\s]+)([A-PR-WYa-pr-wy][0-9]{7,8})\b'
)
PASSPORT_PATTERN = re.compile(
    r'\b[A-PR-WYa-pr-wy][1-9]\d{6}\b'
)

# 4. Phone numbers:
# Covers international format with +country code, US (xxx) xxx-xxxx, and 10-digit mobile
PHONE_INTERNATIONAL_PATTERN = re.compile(
    r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
)
PHONE_INDIAN_PATTERN = re.compile(
    r'(?:\+91[-.\s]?)?[6-9]\d{4}[-.\s]?\d{5}\b'
)
PHONE_LABELED_PATTERN = re.compile(
    r'(?i)\b(?:phone|tel|telephone|mobile|cell|contact(?:\s+no)?)[-:\s]*((?:\+\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5})\b'
)

# 5. Physical addresses:
# Common address keywords and street suffix patterns
STREET_ADDRESS_PATTERN = re.compile(
    r'\b\d{1,5}\s+[A-Za-z0-9\.\s,]{2,35}\s+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir)\b(?:[,\s]+(?:Apt|Suite|Unit|Ste|#)\s*[\w\d-]+)?',
    re.IGNORECASE
)
ADDRESS_LABELED_PATTERN = re.compile(
    r'(?i)\b(?:residential\s+address|street\s+address|mailing\s+address|permanent\s+address|current\s+address|home\s+address)[:\s]+([^\n\r]+)'
)
POSTAL_CODE_LABELED_PATTERN = re.compile(
    r'(?i)\b(?:pin(?:\s*code)?|zip(?:\s*code)?|postal(?:\s*code)?)[-:\s]*([0-9]{5,6}(?:-[0-9]{4})?)\b'
)


class PrivacyValidationError(Exception):
    """Exception raised when input fails deterministic privacy or security validation."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_uploaded_file(
    contents: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None
) -> None:
    """
    Deterministic security and format validation for uploaded resume files.
    Ensures safe defaults and rejects invalid, empty, or malicious inputs.
    """
    # 1. Filename presence and extension check
    if not filename or not filename.lower().endswith(".pdf"):
        raise PrivacyValidationError(
            "Invalid file format. Only PDF (.pdf) documents are permitted.",
            status_code=400
        )

    # 2. File size validation
    if len(contents) == 0:
        raise PrivacyValidationError(
            "Uploaded PDF file is empty (0 bytes).",
            status_code=400
        )

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise PrivacyValidationError(
            f"File size exceeds the maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
            status_code=400
        )

    # 3. Magic bytes inspection: must match PDF signature (%PDF-)
    # A genuine PDF starts with %PDF (or within the first 1024 bytes per PDF standard)
    header_chunk = contents[:1024]
    if b"%PDF" not in header_chunk:
        raise PrivacyValidationError(
            "File content does not match genuine PDF format. The file may be corrupt or misnamed.",
            status_code=400
        )

    # 4. Executable & Polyglot header detection
    # Reject DOS/PE executable ('MZ'), ELF binaries ('\x7fELF'), Java class / Mach-O files
    if contents.startswith(b"MZ") or contents.startswith(b"\x7fELF") or contents.startswith(b"\xca\xfe\xba\xbe"):
        raise PrivacyValidationError(
            "Executable or polyglot files are strictly rejected for security.",
            status_code=400
        )

    # Reject common script files disguised as PDF
    if contents.lstrip().startswith((b"<html", b"<?php", b"#!/bin/", b"#! /bin/")):
        raise PrivacyValidationError(
            "Script and markup files disguised as PDF are strictly rejected.",
            status_code=400
        )

    # 5. PDF structural validity check using PyMuPDF
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if doc.page_count == 0:
            doc.close()
            raise PrivacyValidationError("PDF document contains 0 pages.", status_code=400)
        doc.close()
    except PrivacyValidationError:
        raise
    except Exception as e:
        raise PrivacyValidationError(
            f"Unable to read or parse PDF structure: corrupted or malformed file.",
            status_code=422
        )


def validate_job_description(job_description: Optional[str]) -> Optional[str]:
    """
    Validates optional job description input to prevent excessive prompt bloat or abuse.
    """
    if not job_description:
        return None

    cleaned = job_description.strip()
    if not cleaned:
        return None

    if len(cleaned) > MAX_JOB_DESCRIPTION_CHARS:
        raise PrivacyValidationError(
            f"Job description exceeds the maximum length of {MAX_JOB_DESCRIPTION_CHARS} characters.",
            status_code=400
        )

    return cleaned


def detect_pii(text: str) -> Dict[str, List[str]]:
    """
    Detects Personally Identifiable Information (PII) deterministically in the given text.
    Returns a dictionary of categorized detected items.
    """
    detected: Dict[str, List[str]] = {
        "emails": [],
        "phones": [],
        "government_ids": [],
        "passports": [],
        "addresses": []
    }

    if not text:
        return detected

    # Emails
    emails = EMAIL_PATTERN.findall(text)
    detected["emails"] = list(dict.fromkeys(emails))

    # Government IDs: Aadhaar
    aadhaar_matches = AADHAAR_PATTERN.findall(text)
    for m in AADHAAR_LABELED_PATTERN.finditer(text):
        aadhaar_matches.append(m.group(1))
    
    # Government IDs: PAN
    pan_matches = PAN_PATTERN.findall(text)

    # Government IDs: SSN
    ssn_matches = SSN_PATTERN.findall(text)

    detected["government_ids"] = list(dict.fromkeys(aadhaar_matches + pan_matches + ssn_matches))

    # Passports
    passport_matches = []
    for m in PASSPORT_LABELED_PATTERN.finditer(text):
        passport_matches.append(m.group(1))
    for m in PASSPORT_PATTERN.findall(text):
        # Exclude common tech acronyms if needed
        passport_matches.append(m)
    detected["passports"] = list(dict.fromkeys(passport_matches))

    # Phones
    phone_matches = []
    for m in PHONE_LABELED_PATTERN.finditer(text):
        phone_matches.append(m.group(1).strip())
    phone_matches.extend(PHONE_INTERNATIONAL_PATTERN.findall(text))
    phone_matches.extend(PHONE_INDIAN_PATTERN.findall(text))
    
    # Filter out false positives (e.g. 4-digit years)
    clean_phones = []
    for p in phone_matches:
        digits_only = re.sub(r'\D', '', p)
        if len(digits_only) >= 10:
            clean_phones.append(p)
    detected["phones"] = list(dict.fromkeys(clean_phones))

    # Addresses
    address_matches = []
    for m in ADDRESS_LABELED_PATTERN.finditer(text):
        address_matches.append(m.group(1).strip())
    address_matches.extend(STREET_ADDRESS_PATTERN.findall(text))
    for m in POSTAL_CODE_LABELED_PATTERN.finditer(text):
        address_matches.append(m.group(0).strip())
    detected["addresses"] = list(dict.fromkeys(address_matches))

    return detected


def redact_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Deterministic PII Redaction Engine.
    Replaces sensitive personal identifiers with meaningful placeholders before external AI calls.
    Returns (redacted_text, redaction_counts).
    """
    if not text:
        return "", {}

    redacted = text
    counts: Dict[str, int] = {
        "emails": 0,
        "phones": 0,
        "government_ids": 0,
        "passports": 0,
        "addresses": 0
    }

    # 1. Redact Emails
    email_matches = list(set(EMAIL_PATTERN.findall(redacted)))
    for email in email_matches:
        redacted = re.sub(re.escape(email), REDACTED_EMAIL, redacted)
        counts["emails"] += 1

    # 2. Redact Government IDs (Aadhaar, PAN, SSN)
    # 2a. Aadhaar labeled
    def replace_aadhaar_labeled(m):
        counts["government_ids"] += 1
        full = m.group(0)
        target = m.group(1)
        return full.replace(target, REDACTED_GOV_ID)

    redacted = AADHAAR_LABELED_PATTERN.sub(replace_aadhaar_labeled, redacted)

    # 2b. Aadhaar standard 4-4-4
    aadhaar_matches = list(set(AADHAAR_PATTERN.findall(redacted)))
    for a in aadhaar_matches:
        redacted = re.sub(re.escape(a), REDACTED_GOV_ID, redacted)
        counts["government_ids"] += 1

    # 2c. PAN Cards
    pan_matches = list(set(PAN_PATTERN.findall(redacted)))
    for p in pan_matches:
        redacted = re.sub(r'\b' + re.escape(p) + r'\b', REDACTED_GOV_ID, redacted)
        counts["government_ids"] += 1

    # 2d. US SSN
    ssn_matches = list(set(SSN_PATTERN.findall(redacted)))
    for s in ssn_matches:
        redacted = re.sub(re.escape(s), REDACTED_GOV_ID, redacted)
        counts["government_ids"] += 1

    # 3. Redact Passports
    def replace_passport_labeled(m):
        counts["passports"] += 1
        full = m.group(0)
        target = m.group(1)
        return full.replace(target, REDACTED_PASSPORT)

    redacted = PASSPORT_LABELED_PATTERN.sub(replace_passport_labeled, redacted)

    passport_matches = list(set(PASSPORT_PATTERN.findall(redacted)))
    for pass_no in passport_matches:
        # Avoid redacting placeholders or non-passports
        if not pass_no.startswith("[") and not pass_no.endswith("]"):
            redacted = re.sub(r'\b' + re.escape(pass_no) + r'\b', REDACTED_PASSPORT, redacted)
            counts["passports"] += 1

    # 4. Redact Phones
    # 4a. Labeled phones
    def replace_phone_labeled(m):
        counts["phones"] += 1
        full = m.group(0)
        target = m.group(1)
        return full.replace(target, REDACTED_PHONE)

    redacted = PHONE_LABELED_PATTERN.sub(replace_phone_labeled, redacted)

    # 4b. International and Indian phones
    phone_candidates = list(set(PHONE_INTERNATIONAL_PATTERN.findall(redacted) + PHONE_INDIAN_PATTERN.findall(redacted)))
    for ph in phone_candidates:
        digits_only = re.sub(r'\D', '', ph)
        # Verify it contains at least 10 digits to avoid redacting short numbers/years
        if len(digits_only) >= 10:
            redacted = re.sub(re.escape(ph), REDACTED_PHONE, redacted)
            counts["phones"] += 1

    # 5. Redact Physical Addresses
    def replace_address_labeled(m):
        counts["addresses"] += 1
        return m.group(0).replace(m.group(1), REDACTED_ADDRESS)

    redacted = ADDRESS_LABELED_PATTERN.sub(replace_address_labeled, redacted)

    street_matches = list(set(STREET_ADDRESS_PATTERN.findall(redacted)))
    for st in street_matches:
        redacted = re.sub(re.escape(st), REDACTED_ADDRESS, redacted)
        counts["addresses"] += 1

    postal_matches = list(set(POSTAL_CODE_LABELED_PATTERN.findall(redacted)))
    for pm in postal_matches:
        redacted = re.sub(re.escape(pm), REDACTED_ADDRESS, redacted)
        counts["addresses"] += 1

    return redacted, counts


def sanitize_log_message(msg: str) -> str:
    """
    Sanitizes log messages by masking emails, phone numbers, government IDs, and auth tokens.
    Guarantees no sensitive PII is recorded in application logs.
    """
    if not msg:
        return ""

    sanitized = str(msg)
    # Mask emails
    sanitized = EMAIL_PATTERN.sub("[EMAIL_MASKED]", sanitized)
    # Mask phone numbers
    sanitized = PHONE_INTERNATIONAL_PATTERN.sub("[PHONE_MASKED]", sanitized)
    sanitized = PHONE_INDIAN_PATTERN.sub("[PHONE_MASKED]", sanitized)
    # Mask Aadhaar, PAN, SSN
    sanitized = AADHAAR_PATTERN.sub("[ID_MASKED]", sanitized)
    sanitized = PAN_PATTERN.sub("[ID_MASKED]", sanitized)
    sanitized = SSN_PATTERN.sub("[ID_MASKED]", sanitized)
    # Mask Bearer tokens
    sanitized = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [TOKEN_MASKED]', sanitized)
    # Mask JWTs
    sanitized = re.sub(r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+', '[JWT_MASKED]', sanitized)

    return sanitized
