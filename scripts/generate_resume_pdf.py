from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


OUTPUT = Path(__file__).resolve().parents[1] / "app/static/Harshil_Agrawal_Resume.pdf"


def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet>{text}", styles["body"])


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="name", parent=styles["Title"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=19, leading=22, spaceAfter=4))
styles.add(ParagraphStyle(name="contact", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#4a4a4a"), spaceAfter=10))
styles.add(ParagraphStyle(name="section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=colors.HexColor("#047857"), spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name="role", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, spaceAfter=1))
styles.add(ParagraphStyle(name="body", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, leftIndent=10, firstLineIndent=-7, spaceAfter=2))
styles.add(ParagraphStyle(name="detail", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#4a4a4a"), spaceAfter=3))


def section(title, story):
    story.extend([Paragraph(title.upper(), styles["section"]), HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d4d2cf")), Spacer(1, 4)])


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=0.55 * inch, rightMargin=0.55 * inch, topMargin=0.45 * inch, bottomMargin=0.45 * inch)
    story = [
        Paragraph("Harshil Agrawal", styles["name"]),
        Paragraph("harshilsagrawal@gmail.com | +91 87667 76202 | Ahmedabad, India | linkedin.com/in/harshil-agrawal | github.com/Harshil411", styles["contact"]),
    ]

    section("Education", story)
    story.extend([
        Paragraph("SVKM's NMIMS University, MPSTME, Mumbai | B.Tech Computer Engineering, GPA: 3.60/4.0 | Graduated May 2026", styles["detail"]),
    ])

    section("Experience", story)
    story.extend([
        Paragraph("Prowess Consulting | Data & AI Engineering Intern | Dec 2025 - Jun 2026", styles["role"]),
        bullet("Owned end-to-end delivery of an LLM-powered WhatsApp ordering platform on Azure App Service for pharmaceutical distribution."),
        bullet("Integrated Azure OpenAI intent classification with a 1,500+ product catalog and Snowflake-backed conversation logging."),
        bullet("Built the SalesVitals FastAPI analytics stack with SQLite snapshot mode, eliminating recurring Snowflake costs."),
        bullet("Maintained reproducibility with Git, GitHub Actions, and automated test suites."),
        Spacer(1, 4),
        Paragraph("Gram Panchayat, Maharashtra | Social Impact Data Analyst, Volunteer | 2024", styles["role"]),
        bullet("Collected and analyzed community participation, sanitation, and education data for rural development."),
        bullet("Tracked 500+ sapling plantations and evaluated sanitation and digital-literacy programs."),
        bullet("Worked with local authorities on resource allocation for old-age homes and orphanages."),
    ])

    section("Selected projects", story)
    story.extend([
        Paragraph("Banking PII Protection | github.com/Harshil411/banking_PII", styles["role"]),
        bullet("Built a local-first FastAPI and React service for PII extraction, schema validation, and anonymized output. Reported micro-F1: 0.866 across 32,017 labeled entities."),
        Spacer(1, 3),
        Paragraph("Manufacturing Defect Prediction | github.com/Harshil411/portfolio", styles["role"]),
        bullet("Deployed an inspectable Random Forest classifier through FastAPI. The project uses synthetic manufacturing sensor data and documents its model behavior and evaluation."),
    ])

    section("Research", story)
    story.extend([
        Paragraph("A Hybrid LSTM + Deep Reinforcement Learning Framework for Enterprise-Grade Decision Support and Automated Trading", styles["role"]),
        Paragraph("IEEE ICCICT 2026, under publication", styles["detail"]),
        bullet("Proposes a hybrid LSTM and Deep RL framework that separates forecasting from execution."),
        bullet("Validated on NIFTY-50 backtests with a reported Sharpe ratio of about 1.8 using LSTM, PPO, DQN, and SAC."),
    ])

    section("Professional development and award", story)
    story.extend([
        Paragraph("Certificate of Participation in ACM SemiCode | Unstop | Mar 2024 | Credential ID: da0389db-6732-4f51-a3fb-4b97ec5dfe93", styles["detail"]),
        Paragraph("Workshops: Power BI Workshop; AI Prompting and N8N Automation Workshop, Prowess Consulting; AI and HPC Workshop, KLA and IIT Madras.", styles["detail"]),
        Paragraph("Award: Best Executive in Public Relations, Google Developer Student Clubs, NMIMS.", styles["detail"]),
    ])

    section("Skills", story)
    story.append(Paragraph("Programming: Python, SQL, Java, C, C++, JavaScript | Backend: FastAPI, Spring Boot, Spring Cloud, REST API | Cloud: Azure, Docker, GitHub Actions, CI/CD | Data and ML: Snowflake, SQLite, LSTM, Deep RL, scikit-learn, pandas", styles["detail"]))
    document.build(story)


if __name__ == "__main__":
    main()
