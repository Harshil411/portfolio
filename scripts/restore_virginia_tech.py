from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS = {
    "app/templates/index.html": [
        (
            '''            <p class="signal-index">Field note / current</p>
            <div class="signal-row"><span>Focus</span><span>Data systems<br>Applied AI</span></div>
            <div class="signal-row"><span>Seeking</span><span>ML / DS roles<br>Research</span></div>
            <div class="signal-row"><span>Based in</span><span>Ahmedabad, India</span></div>''',
            '''            <p class="signal-index">Field note / 2026 to 27</p>
            <div class="signal-row"><span>Graduate study</span><span>MS Data Science<br>Virginia Tech</span></div>
            <div class="signal-row"><span>Seeking</span><span>GA roles · research<br>ML / DS internships</span></div>
            <div class="signal-row"><span>Relocating</span><span>Blacksburg, VA<br>Aug 2026</span></div>''',
        )
    ],
    "app/templates/resume.html": [
        (
            "Data and AI engineer building practical systems.",
            "Incoming M.S. Data Science student at Virginia Tech.",
        ),
        (
            '''            <div class="flex flex-col md:flex-row md:justify-between gap-2">
                <div>
                    <h3 style="font-size: 1.125rem;">SVKM's NMIMS University, MPSTME, Mumbai</h3>''',
            '''            <div class="flex flex-col md:flex-row md:justify-between gap-2">
                <div>
                    <h3 style="font-size: 1.125rem;">Virginia Tech</h3>
                    <p class="text-secondary">M.S. in Data Science, Blacksburg, VA</p>
                </div>
                <p class="text-tertiary font-mono" style="font-size: 0.875rem;">Aug 2026 to May 2028</p>
            </div>
            <div class="flex flex-col md:flex-row md:justify-between gap-2">
                <div>
                    <h3 style="font-size: 1.125rem;">SVKM's NMIMS University, MPSTME, Mumbai</h3>''',
        ),
    ],
    "app/templates/contact.html": [
        (
            "I am looking for technical opportunities and Summer 2027 internships.",
            "I am looking for on-campus opportunities at Virginia Tech and Summer 2027 internships.",
        ),
        ("Ahmedabad, India</span>", "Ahmedabad, India to Blacksburg, VA (Aug 2026)</span>"),
    ],
    "scripts/generate_resume_pdf.py": [
        (
            'Paragraph("harshilsagrawal@gmail.com | +91 87667 76202 | Ahmedabad, India | linkedin.com/in/harshil-agrawal | github.com/Harshil411", styles["contact"]),',
            'Paragraph("harshilsagrawal@gmail.com | +91 87667 76202 | Ahmedabad, India to Blacksburg, VA | linkedin.com/in/harshil-agrawal | github.com/Harshil411", styles["contact"]),',
        ),
        (
            'section("Education", story)\n    story.extend([\n        Paragraph("SVKM\'s NMIMS University, MPSTME, Mumbai | B.Tech Computer Engineering, GPA: 3.60/4.0 | Graduated May 2026", styles["detail"]),',
            'section("Education", story)\n    story.extend([\n        Paragraph("Virginia Tech | M.S. Data Science | Blacksburg, VA | Aug 2026 to May 2028", styles["role"]),\n        Paragraph("SVKM\'s NMIMS University, MPSTME, Mumbai | B.Tech Computer Engineering, GPA: 3.60/4.0 | Graduated May 2026", styles["detail"]),',
        ),
    ],
}


def main():
    for relative_path, replacements in REPLACEMENTS.items():
        path = ROOT / relative_path
        text = path.read_text()
        for old, new in replacements:
            if old not in text:
                raise RuntimeError(f"Expected temporary content is missing from {relative_path}")
            text = text.replace(old, new, 1)
        path.write_text(text)
    subprocess.run([sys.executable, "scripts/generate_resume_pdf.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
