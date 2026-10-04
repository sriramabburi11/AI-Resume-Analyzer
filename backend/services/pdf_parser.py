import pymupdf as fitz  # PyMuPDF
import re
from typing import Dict, Any, List, Tuple

class PDFParsingError(Exception):
    pass

def extract_resume_text(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts text and layout metadata from a PDF file using PyMuPDF (fitz).
    Returns text and detected visual/structural heuristics for ATS checks.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise PDFParsingError(f"Failed to open PDF document: {str(e)}")

    if doc.page_count == 0:
        raise PDFParsingError("PDF document has 0 pages.")

    full_text_pages: List[str] = []
    total_images = 0
    total_drawing_objects = 0
    multi_column_detected = False
    font_names = set()
    table_indicators_detected = False

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        full_text_pages.append(text)

        # Count images
        images = page.get_images()
        total_images += len(images)

        # Check drawings (shapes, lines, text boxes borders)
        drawings = page.get_drawings()
        total_drawing_objects += len(drawings)
        if len(drawings) > 15:
            table_indicators_detected = True

        # Analyze blocks for layout/column detection
        blocks = page.get_text("blocks")
        # Sort blocks vertically
        # If we see overlapping y-coordinates with significantly different x-coordinates, multi-column is likely
        x_ranges = []
        for b in blocks:
            # b is (x0, y0, x1, y1, "text", block_no, block_type)
            if len(b) >= 5 and b[4].strip():
                x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
                x_ranges.append((x0, x1, y0, y1))
        
        # Simple multi-column heuristic: check if there are blocks on left half (x1 < page_width*0.55)
        # AND blocks on right half (x0 > page_width*0.45) at similar y ranges.
        rect = page.rect
        page_width = rect.width
        mid_point = page_width / 2.0
        
        left_blocks = [b for b in x_ranges if b[1] <= mid_point + 20]
        right_blocks = [b for b in x_ranges if b[0] >= mid_point - 20]
        if len(left_blocks) >= 2 and len(right_blocks) >= 2:
            multi_column_detected = True

        # Extract fonts if possible
        try:
            fonts = page.get_fonts()
            for f in fonts:
                if len(f) > 3:
                    font_names.add(f[3])
        except Exception:
            pass

    full_text = "\n".join(full_text_pages).strip()
    
    # Clean whitespace for word count
    words = full_text.split()
    word_count = len(words)

    if word_count < 30:
        raise PDFParsingError("Unable to extract text from this PDF. Please upload a text-based PDF.")

    # Contact info detection heuristics
    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text))
    has_phone = bool(re.search(r'(\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', full_text))
    has_linkedin = bool(re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', full_text, re.IGNORECASE)) or 'linkedin' in full_text.lower()
    has_github = bool(re.search(r'github\.com/[a-zA-Z0-9_-]+', full_text, re.IGNORECASE)) or 'github' in full_text.lower()

    # Icon / unusual character detection
    unusual_symbols = len(re.findall(r'[\u2600-\u27bf\u1f300-\u1f6ff\u25a0-\u25ff]', full_text))

    return {
        "text": full_text,
        "page_count": doc.page_count,
        "word_count": word_count,
        "character_count": len(full_text),
        "total_images": total_images,
        "total_drawings": total_drawing_objects,
        "multi_column_detected": multi_column_detected,
        "table_indicators_detected": table_indicators_detected,
        "fonts": list(font_names),
        "contact_info": {
            "has_email": has_email,
            "has_phone": has_phone,
            "has_linkedin": has_linkedin,
            "has_github": has_github
        },
        "unusual_symbols_count": unusual_symbols
    }
