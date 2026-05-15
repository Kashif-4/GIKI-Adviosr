"""
extract_curricula.py  
Reads UG-Prospectus-2022.pdf, finds all degree program course tables,
and writes a structured prerequisites.json that the DegreePlanner uses.

Run once:  python extract_curricula.py
"""

import json
import re
import os

# Try pdfplumber first (best for tables), fall back to PyMuPDF (fitz)
try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    USE_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    USE_FITZ = True
except ImportError:
    USE_FITZ = False

PDF_PATH   = "data/UG-Prospectus-2022.pdf"
OUT_PATH   = "data/prerequisites.json"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Regex: course codes look like "CS101", "AI-301", "MT 202", "HM101" etc.
CODE_RE = re.compile(r'\b([A-Z]{2,4}[-\s]?\d{3}[A-Z]?)\b')

def normalise_code(raw: str) -> str:
    """Remove spaces/hyphens and uppercase: 'AI-301' → 'AI301'."""
    return re.sub(r'[\s\-]', '', raw).upper()

def extract_text_with_fitz(path: str) -> list:
    """Return list of (page_number, text) tuples."""
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        pages.append((i + 1, page.get_text()))
    return pages

def extract_text_with_pdfplumber(path: str) -> list:
    """Return list of (page_number, text) tuples."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            pages.append((i + 1, page.extract_text() or ""))
    return pages

# ─────────────────────────────────────────────────────────────────────────────
# Degree Detection Patterns
# ─────────────────────────────────────────────────────────────────────────────

DEGREE_PATTERNS = {
    "BSCS": re.compile(r'BS\s*(?:Computer Science|CS)', re.I),
    "BSAI": re.compile(r'BS\s*(?:Artificial Intelligence|AI)\b', re.I),
    "BSDS": re.compile(r'BS\s*(?:Data Science|DS)\b', re.I),
    "BSSE": re.compile(r'BS\s*(?:Software Engineering|SE)\b', re.I),
    "BSCE": re.compile(r'BS\s*(?:Computer Engineering|CE)\b', re.I),
    "BSEE": re.compile(r'BS\s*(?:Electrical Engineering|EE)\b', re.I),
}

# ─────────────────────────────────────────────────────────────────────────────
# Row Parser: tries to parse a text line into (code, name, credits, prereqs, sem)
# ─────────────────────────────────────────────────────────────────────────────

def parse_course_line(line: str, semester_hint: int):
    """
    Try to extract a course entry from a text line.
    Expected rough formats from prospectus:
        CS101   Computing and AI           3   -
        CS112   Object Oriented Prog.      3   CS101
        MT202   Calculus II                3   MT101, MT102
    Returns dict or None.
    """
    line = line.strip()
    if not line:
        return None

    # Must start with a course code
    m = CODE_RE.match(line)
    if not m:
        return None

    raw_code = m.group(1)
    code = normalise_code(raw_code)
    rest = line[m.end():].strip()

    # Split remaining by 2+ spaces or tabs to find columns
    parts = re.split(r'\s{2,}|\t', rest)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return None

    name    = parts[0] if len(parts) > 0 else code
    credits = 3  # default
    prereqs = []

    # Look for a credits number (1–4)
    credit_idx = None
    for i, p in enumerate(parts):
        if re.fullmatch(r'[1-4]', p):
            credits = int(p)
            credit_idx = i
            break

    # Everything after credits field could be prereq column
    if credit_idx is not None and credit_idx + 1 < len(parts):
        prereq_str = parts[credit_idx + 1]
        # Extract all course codes from prereq field
        raw_prereqs = CODE_RE.findall(prereq_str)
        prereqs = [normalise_code(r) for r in raw_prereqs]

    # If name is just a code, use the raw rest as name
    if re.fullmatch(r'[A-Z0-9]+', name):
        name = rest[:40].split("  ")[0].strip()

    return {
        "code":     code,
        "name":     name[:80],
        "credits":  credits,
        "prereqs":  prereqs,
        "semester": semester_hint,
    }

# ─────────────────────────────────────────────────────────────────────────────
# Main Extraction Logic
# ─────────────────────────────────────────────────────────────────────────────

SEM_HEADER_RE = re.compile(
    r'(?:semester|sem(?:ester)?)[.\s]*(\d)\b', re.I
)

def extract_degrees(pages: list) -> dict:
    """
    Walk pages in order. When we detect a degree heading, collect courses
    until the next degree heading. Detect semester numbers from sub-headers.
    """
    curricula = {key: {} for key in DEGREE_PATTERNS}

    current_degree = None
    current_sem    = 1

    for page_no, text in pages:
        lines = text.split('\n')

        for line in lines:
            stripped = line.strip()

            # ── Detect degree heading ───────────────────────────────────────
            for deg, pat in DEGREE_PATTERNS.items():
                if pat.search(stripped):
                    current_degree = deg
                    current_sem    = 1
                    break

            if current_degree is None:
                continue

            # ── Detect semester heading ─────────────────────────────────────
            sm = SEM_HEADER_RE.search(stripped)
            if sm:
                current_sem = int(sm.group(1))
                continue

            # ── Try to parse a course row ───────────────────────────────────
            entry = parse_course_line(stripped, current_sem)
            if entry:
                code = entry["code"]
                # Don't overwrite if already seen with a lower semester hint
                if code not in curricula[current_degree]:
                    curricula[current_degree][code] = {
                        "name":     entry["name"],
                        "credits":  entry["credits"],
                        "prereqs":  entry["prereqs"],
                        "semester": entry["semester"],
                    }

    # Remove empty degrees
    curricula = {k: v for k, v in curricula.items() if v}
    return curricula

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: {PDF_PATH} not found.")
        return

    print(f"Opening {PDF_PATH} ...")

    if USE_PDFPLUMBER:
        print("Using pdfplumber (table-aware).")
        pages = extract_text_with_pdfplumber(PDF_PATH)
    elif USE_FITZ:
        print("Using PyMuPDF (fitz).")
        pages = extract_text_with_fitz(PDF_PATH)
    else:
        print("ERROR: Install pdfplumber or PyMuPDF:\n  pip install pdfplumber  OR  pip install pymupdf")
        return

    print(f"Loaded {len(pages)} pages. Extracting curricula...")
    curricula = extract_degrees(pages)

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n=== Extraction Results ===")
    for deg, courses in curricula.items():
        if courses:
            print(f"  {deg}: {len(courses)} courses")
        else:
            print(f"  {deg}: (no courses found)")

    # ── Merge with existing prerequisites.json ────────────────────────────────
    existing = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, "r") as f:
            existing = json.load(f)
        print(f"\nMerging into existing {OUT_PATH}...")

    for deg, courses in curricula.items():
        if courses:
            if deg in existing:
                print(f"  Updating {deg} ({len(existing[deg])} → {len(courses)} courses)")
            else:
                print(f"  Adding new degree: {deg} ({len(courses)} courses)")
            existing[deg] = courses

    with open(OUT_PATH, "w") as f:
        json.dump(existing, f, indent=4)

    print(f"\n✅ Saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
