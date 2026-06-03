import io
import os
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from sqlalchemy import func, select
from .definitions import POSITION_SETS
from LTGenerator.models import Level, Session, Instructor, Skills, studentresults, Student, levelskills
from LTGenerator import db

_SHEETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sheets')

# Fallback when levels.template is missing or invalid in the database
_LEVEL_PDF_FALLBACK = {
    "Preschool 1": "P1.pdf",
    "Preschool 2": "P2.pdf",
    "Preschool 3": "P3.pdf",
    "Preschool 4": "P4.pdf",
}


def resolve_sheet_pdf_path(root_path, level):
    """Return an absolute path to the sheet PDF for *level*, trying fallbacks."""
    sheets_dir = os.path.join(root_path, "sheets")
    candidates = []
    if level.template and level.template not in ("x", ""):
        candidates.append(level.template)
    if level.name in _LEVEL_PDF_FALLBACK:
        candidates.append(_LEVEL_PDF_FALLBACK[level.name])
    candidates.append(f"P{level.levelid}.pdf")

    for name in candidates:
        if not name:
            continue
        path = os.path.join(sheets_dir, name)
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        f"No sheet PDF found for level {level.name!r}. "
        f"Looked for: {', '.join(c for c in candidates if c)} in {sheets_dir}"
    )


def print_general_fields(pdf_path, session, form_rows=None):
    """
    Overlay session data onto the template PDF and return the result as a
    BytesIO buffer.  No files are left on disk after this call returns.

    form_rows: optional list of 8 dicts ``{'name': str, 'sid': str}`` from
    worksheet rows 1–8.  Row 1 maps to Name1, row 2 to Name2, etc.
    """

    # ── Resolve absolute paths ──────────────────────────────────────────────
    drawing_path = os.path.join(_SHEETS_DIR, '_drawing_tmp.pdf')

    # ── Gather data from session ────────────────────────────────────────────
    fBarcode    = str(session.session)
    fDayTime    = f"{session.weekdays} {session.time}"
    fSeries     = "Summer 2026"
    fPool       = str(session.pool)
    fInstructor = str(session.Instructor.name)
    fSkills     = list(session.Level.skills)

    if form_rows is None:
        trimmed = func.trim(Student.name)
        last_char = func.lower(func.right(trimmed, 1))
        raw = db.session.scalars(
            select(Student)
            .where(Student.sessionid == session.sessionid)
            .order_by(last_char, Student.sid)
        ).all()
        raw = sorted(
            raw,
            key=lambda s: (s.name.strip()[-1].lower() if s.name.strip() else '', s.sid),
        )[:8]
        slots = raw + [None] * (8 - len(raw))
        form_rows = [
            {
                'name': slots[i].name if slots[i] else '',
                'sid': str(slots[i].sid) if slots[i] else '',
            }
            for i in range(8)
        ]

    # Worksheet row i (0-based) -> Name{i+1} on the PDF
    name_map = {f"Name{i + 1}": form_rows[i]['name'] for i in range(8)}

    # ── Find position set for this level ────────────────────────────────────
    level_positions = POSITION_SETS.get(session.Level.name)
    if level_positions is None:
        raise ValueError(
            f"No POSITION_SETS entry for level '{session.Level.name}'. "
            "Add it to definitions.py before printing."
        )

    names_positions  = [f for f in level_positions if isinstance(f.get("value"), str) and f["value"].startswith("Name")]
    skills_positions = [f for f in level_positions if isinstance(f.get("value"), int)]

    # ── Draw overlay canvas ─────────────────────────────────────────────────
    c = canvas.Canvas(drawing_path, pagesize=landscape(letter))
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 15)

    for field in level_positions:
        val = field.get("value")
        x, y = field.get("x"), field.get("y")
        if x is None or y is None:
            continue
        match val:
            case "Barcode":    c.drawString(x, y, fBarcode)
            case "Time":       c.drawString(x, y, fDayTime)
            case "Season":     c.drawString(x, y, fSeries)
            case "Pool":       c.drawString(x, y, fPool)
            case "Instructor": c.drawString(x, y, fInstructor)
            case str() if val.startswith("Name"):
                c.drawString(x, y, name_map.get(val, ""))

    # Skill evaluation marks — same row index as names (row 1 -> Name1)
    name_by_slot = {f["value"]: f for f in names_positions}
    for i in range(8):
        name_field = name_by_slot.get(f"Name{i + 1}")
        if name_field is None:
            continue

        row = form_rows[i]
        if not row['name']:
            continue

        sid = row['sid']
        if not sid.isdigit():
            continue

        student = db.session.get(Student, int(sid))
        if student is None:
            continue

        skill_results = {r.skillid: r.result for r in student.studentresults}
        for skill_field in skills_positions:
            skill_id = skill_field["value"]
            sx = skill_field.get("x")
            sy = name_field.get("y")
            if sx is None or sy is None:
                continue
            mark = skill_results.get(skill_id, "")
            if mark == "C":
                c.drawString(sx, sy, "C")
            elif mark == "I":
                c.drawString(sx, sy, "IC")
            else:
                c.drawString(sx, sy, "IC")

    c.save()

    # ── Merge drawing onto template page ────────────────────────────────────
    reader  = PdfReader(pdf_path)
    writer  = PdfWriter()
    writer.add_page(reader.pages[0])

    drawing_reader = PdfReader(drawing_path)
    writer.pages[0].merge_page(drawing_reader.pages[0])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    # ── Clean up temp drawing file ───────────────────────────────────────────
    try:
        os.remove(drawing_path)
    except OSError:
        pass

    return buf
