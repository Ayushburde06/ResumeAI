#!/usr/bin/env python3
"""Create a test PDF resume for E2E testing."""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

RESUME_TEXT = """Ayushkumar Burde
Email: ayushburde156@gmail.com | Phone: +91-8600820291 | Mumbai, India

SUMMARY
Software Engineer with a Master's in Computer Applications and hands-on experience building AI-powered, cloud-based systems. Proficient in Python, React, TypeScript, and backend development with Node.js and Django. Comfortable working across RESTful APIs, NoSQL databases, and CI/CD pipelines in Agile environments.

EXPERIENCE
CrystalTech Services Pvt Ltd -- Software Engineer Intern | Indore, India | Jul 2024 - Dec 2024
Built microservices with Node.js and Express.js; deployed on AWS to improve cloud infrastructure response time and service reliability. Contributed to React.js and TypeScript frontend; integrated RESTful APIs and followed Agile/SCRUM workflows with Git for version control. Worked with MongoDB and Elasticsearch for NoSQL data storage; supported CI/CD pipelines and debugging across distributed services.

EDUCATION
Tulsiramji Gaikwad Patil College of Engineering and Technology -- Master of Computer Applications | Nagpur, India | 2025
City Premier College -- Bachelor of Computer Applications | Nagpur, India | 2022

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frontend: React.js, HTML5, CSS3
Backend: Node.js, Express.js, Django, RESTful APIs, Microservices Architecture
Databases: MongoDB, SQLite, Elasticsearch, NoSQL
Cloud & DevOps: AWS, Azure, Google Cloud, CI/CD, Docker, Git, GitHub
Concepts: OOP, Agile/SCRUM, Version Control, Backend Development, AI-Driven Systems

PROJECTS
ResumeAI - AI-powered ATS Resume Builder with multi-agent optimization loop, RAG-based keyword retrieval, and job description analysis for targeted resume tailoring. Engineered a PDF export pipeline using Playwright and Jinja2 template rendering.

NotesApp - Full-stack CRUD application using React, Node.js, and MongoDB; implemented JWT authentication, deployed on AWS, and served 2K+ users with reliable uptime.

CV Generator - Django web application with PDF generation via ReportLab; implemented form validation, SQLite data persistence, and Google Cloud file storage.

CERTIFICATIONS
AWS Cloud Practitioner Essentials
Google Cloud Digital Leader
"""

out = Path(__file__).resolve().parent / "ats_quick_out" / "test_resume.pdf"
out.parent.mkdir(parents=True, exist_ok=True)

doc = SimpleDocTemplate(str(out), pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
styles = getSampleStyleSheet()
custom = ParagraphStyle("Custom", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)

elems = []
for line in RESUME_TEXT.strip().split("\n"):
    line = line.strip()
    if not line:
        elems.append(Spacer(1, 6))
    elif line.isupper() or line.startswith(("SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "CERTIFICATIONS")):
        elems.append(Paragraph(f"<b>{line}</b>", custom))
    else:
        elems.append(Paragraph(line, custom))

doc.build(elems)
print(f"PDF created: {out} ({out.stat().st_size} bytes)")
