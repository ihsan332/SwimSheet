from pypdf import PdfReader, PdfWriter
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from definitions import POSITION_SETS
from LTGenerator.models import Level, Session, Instructor, Skills, studentresults, Student, levelskills
from LTGenerator import db

def print_general_fields(pdf_path, output_path, session):

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])

    c = canvas.Canvas('sheets/drawing.pdf', pagesize=landscape(letter))
    width, height = landscape(letter)

    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 22)

    fBarcode = f"{session.session}" 
    fDayTime = f"{session.weekdays} {session.time}"
    fSeries = "Summer 2026"
    fPool = f"{session.pool}"
    fInstructor = f"{session.Instructor.name}"
    fLevel = f"{session.Level.name}"
    fStudents = session.students[:8]
    fSkills = session.Level.skills
    fResults = []

    for student in fStudents:
        record = {
            "name": student.name,
            "skills": {}
        }
        for skill in fSkills:
            result = next((r for r in student.studentresults if r.skillid == skill.skillid), None)            
            record["skills"][skill.name] = result if result else "N/A"
        fResults.append(record)

    # TODO: Check values based on submission form from edit session page
    level = next((l for l in POSITION_SETS if l == session.Level.name), None)
    names = [f for f in level if f["value"].startswith("Name")]
    skills = [f for f in level if isinstance(f["value"], int)]


    for field in level:
        match field["value"]:
            case "Barcode":
                c.drawString(field["x"], field["y"], fBarcode)
            case "Time":
                c.drawString(field["x"], field["y"], fDayTime)
            case "Season":
                c.drawString(field["x"], field["y"], fSeries)
            case "Pool":
                c.drawString(field["x"], field["y"], fPool)
            case "Instructor":
                c.drawString(field["x"], field["y"], fInstructor)
            case "Name1":
                c.drawString(field["x"], field["y"], fStudents[0].name if len(fStudents) > 0 else "N/A")
            case "Name2":
                c.drawString(field["x"], field["y"], fStudents[1].name if len(fStudents) > 1 else "N/A")
            case "Name3":
                c.drawString(field["x"], field["y"], fStudents[2].name if len(fStudents) > 2 else "N/A")
            case "Name4":
                c.drawString(field["x"], field["y"], fStudents[3].name if len(fStudents) > 3 else "N/A")
            case "Name5":
                c.drawString(field["x"], field["y"], fStudents[4].name if len(fStudents) > 4 else "N/A")
            case "Name6":
                c.drawString(field["x"], field["y"], fStudents[5].name if len(fStudents) > 5 else "N/A")
            case "Name7":
                c.drawString(field["x"], field["y"], fStudents[6].name if len(fStudents) > 6 else "N/A")
            case "Name8":
                c.drawString(field["x"], field["y"], fStudents[7].name if len(fStudents) > 7 else "N/A")
    for i, name in enumerate(names):      
        i = 0
        if len(fStudents) > i:
            cstudent = fStudents[i] 
            for skill in skills:
                targetskill = skill["value"]
                match = next((s for s in fSkills if s.skillid == targetskill), None)
                evaluation = match.result if match and match.result else ""
                c.drawString(skill["x"], name["y"], evaluation)
        else:
            pass

    c.save()

    drawing_reader = PdfReader('sheets/drawing.pdf')
    writer.pages[0].merge_page(drawing_reader.pages[0])

    with open(output_path, 'wb') as f:
        writer.write(f)

print_general_fields('sheets/P1.pdf', 'sheets/output.pdf', Instructor, Session, Level)

