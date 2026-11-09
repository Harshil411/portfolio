"""Unit tests: project facts, the model and its metadata, the résumé generator, and source rules.

Run every suite from the repo root:  .venv311/bin/python -m unittest discover tests
"""
import importlib.util
import re
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import joblib
from fastapi import HTTPException

from app import main

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"
GENERATOR = ROOT / "scripts" / "generate_resume_pdf.py"

EMAIL = "agrawalharshil600@gmail.com"
PHONE = "+1 (540) 998-6474"

# Facts that were retired or never verified. None may appear anywhere on the site or résumé.
RETIRED = [r"0\.84\b", r"0\.866", r"32,017", r"multilingual", r"Banking PII", r"\bReact\b", r"Hugging Face",
           r"harshilsagrawal@gmail\.com", r"87667", r"\+91", r"under publication", r"\breported\b", r"Run all"]

APPROVED_DECISIONS = {
    "llm-ordering-platform": [],
    "salesvitals": [
        "Served insights from a versioned SQLite snapshot instead of live warehouse reads, trading data freshness for zero recurring query cost on the delivery path.",
        "Validated snapshots in GitHub Actions so a bad build fails before it reaches the field team.",
    ],
    "mortgage-pii": [
        "Runs with networking disabled, so the text never leaves the machine.",
        "Ranks detections by evidence: a checksum that holds outranks a model's confidence, and every rejected candidate comes back with a reason.",
    ],
    "lstm-drl-trading": ["Separated forecasting from execution so each stage can be evaluated on its own terms."],
    "defect-prediction": ["Used synthetic data by design: the goal is to demonstrate serving, interface design, and honest evaluation, not to claim field performance."],
}

# Approved résumé wording (handoff, section 5). Shared with the integration test for /resume.
RESUME_LINES = [
    "Shipped a WhatsApp ordering assistant for pharmaceutical distribution on Azure App Service that has handled 10,000+ orders from about 1,000 pharmacies, using Azure OpenAI intent classification over a 1,500+ product catalog with Snowflake-backed conversation logs.",
    "Built SalesVitals, a FastAPI customer-insights tool that shows pharmaceutical field reps a customer's full history before each call; before it, every outreach was manual, with no view of the customer.",
    "Removed per-request Snowflake queries and their recurring cost by serving SalesVitals from a scheduled SQLite snapshot, validated on every build in GitHub Actions.",
    "Maintained reproducibility with Git, GitHub Actions, and automated test suites.",
    "Built a Dockerized NLP service in FastAPI that finds and redacts 19 types of personal data in US mortgage and loan-servicing documents, from SSNs and routing numbers to borrower names, and runs with networking disabled so sensitive text stays on the machine.",
    "Resolved overlapping matches by strength of evidence, letting checksum validators (SSA, ABA routing, Luhn) outrank spaCy NER confidence, and returned every rejected match with its reason so each redaction can be audited.",
    "Reached 0.977 strict micro-F1 (0.981 precision, 0.974 recall) on 2,070 labeled entities in held-out synthetic documents; the evaluation and 267 pytest tests run on every push in GitHub Actions.",
    "Sharpe ratio of about 1.8",
]


def site_sources():
    """Every file whose text ends up on the site or in the résumé PDF."""
    files = [ROOT / "app" / "main.py", ROOT / "README.md", GENERATOR, *TEMPLATES.glob("*.html"), *STATIC.glob("*.css"), *STATIC.glob("*.js")]
    return {f: f.read_text() for f in files}


class ProjectFacts(unittest.TestCase):
    def test_projects_appear_in_order_with_the_confirmed_metrics(self):
        self.assertEqual(
            [(p["slug"], p["no"], p["metric"]["value"]) for p in main.PROJECTS],
            [("llm-ordering-platform", "01", "10,000+"), ("salesvitals", "02", "0"), ("mortgage-pii", "03", "0.977"),
             ("lstm-drl-trading", "04", "~1.8"), ("defect-prediction", "05", "0.881")],
        )

    def test_each_project_says_who_owns_it(self):
        self.assertEqual([p["status"] for p in main.PROJECTS],
                         ["Employer-owned work", "Employer-owned work", "Open source", "Accepted paper", "Live implementation"])

    def test_decision_lines_are_the_six_approved_ones(self):
        self.assertEqual({p["slug"]: p["decisions"] for p in main.PROJECTS}, APPROVED_DECISIONS)

    def test_every_project_has_what_its_case_cell_renders(self):
        for p in main.PROJECTS:
            with self.subTest(p["slug"]):
                self.assertEqual(len(p["trace"]), 4)
                self.assertTrue(p["name"] and p["headline"] and p["summary"] and p["tags"] and p["metric"]["short"])
                self.assertIn(p["status_tone"], {"private", "public", "progress"})


class Model(unittest.TestCase):
    def test_model_loads_without_a_version_warning(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            joblib.load(ROOT / "ml" / "model.joblib")

    def test_metadata_matches_the_numbers_the_site_quotes(self):
        meta = main.model_meta
        self.assertEqual(round(meta["accuracy"], 3), 0.881)
        self.assertEqual(round(meta["baseline_accuracy"], 3), 0.698)  # always guessing "no defect"
        self.assertEqual((meta["train_samples"], meta["test_samples"]), (4000, 1000))
        self.assertEqual(list(meta["feature_importances"]), main.FEATURES)
        self.assertAlmostEqual(sum(meta["feature_importances"].values()), 1, places=3)

    def test_presets_start_from_a_normal_reading_and_include_defects(self):
        self.assertEqual([name for name, _ in main.PRESETS], ["Normal", "Running hot", "Hot & humid", "Shaking at high speed"])
        outcomes = [main.predict_reading(values)["prediction"] for _, values in main.PRESETS]
        self.assertEqual(outcomes[0], 0)
        self.assertIn(1, outcomes)

    def test_predict_reading_returns_rounded_probabilities_that_sum_to_one(self):
        result = main.predict_reading(main.PRESETS[0][1])
        self.assertEqual(result["prediction_label"], "No Defect")
        self.assertAlmostEqual(sum(result["probability"].values()), 1, places=3)
        self.assertTrue(all(round(v, 4) == v for v in result["probability"].values()))
        self.assertEqual(main.NORMAL, result)

    def test_predict_reading_reports_503_when_no_model_is_loaded(self):
        with mock.patch.object(main, "model", None), self.assertRaises(HTTPException) as caught:
            main.predict_reading(main.PRESETS[0][1])
        self.assertEqual(caught.exception.status_code, 503)


class SourceRules(unittest.TestCase):
    def test_no_retired_facts_or_old_contact_details_anywhere(self):
        for path, source in site_sources().items():
            for pattern in RETIRED:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, source))

    def test_new_contact_details_are_used(self):
        self.assertIn(EMAIL, (TEMPLATES / "base.html").read_text())
        self.assertIn(f"{EMAIL} | {PHONE}", GENERATOR.read_text())
        resume = (TEMPLATES / "resume.html").read_text()
        self.assertIn('href="tel:+15409986474"', resume)
        self.assertIn(PHONE, resume)

    def test_templates_use_classes_not_inline_styles(self):
        for template in TEMPLATES.glob("*.html"):
            for style in re.findall(r'style="([^"]*)"', template.read_text()):
                with self.subTest(template=template.name):
                    self.assertTrue(style.strip().startswith("--"), f"inline style {style!r}; use a class")

    def test_css_uses_specificity_not_important_outside_print_and_reduced_motion(self):
        css = (STATIC / "site.css").read_text()
        for block in re.findall(r"@media (?:print|\(prefers-reduced-motion: reduce\)) \{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", css):
            css = css.replace(block, "")
        self.assertNotIn("!important", css)

    def test_fonts_are_self_hosted_woff2_with_their_license(self):
        css = (STATIC / "site.css").read_text()
        for source in site_sources().values():
            self.assertNotRegex(source, r"fonts\.(googleapis|gstatic)\.com")
        urls = re.findall(r"@font-face\s*\{[^}]*url\((/static/[^)]+)\)", css)
        self.assertEqual(len(urls), 2)
        for url in urls:
            self.assertEqual((ROOT / "app" / url.lstrip("/")).read_bytes()[:4], b"wOF2", url)
        base = (TEMPLATES / "base.html").read_text()
        self.assertEqual(sorted(re.findall(r'rel="preload" href="([^"]+)" as="font"', base)), sorted(urls))
        self.assertIn("SIL Open Font License", (STATIC / "fonts" / "OFL.txt").read_text())


class ResumeGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("generate_resume_pdf", GENERATOR)
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    def test_generator_uses_the_approved_wording(self):
        source = GENERATOR.read_text()
        for line in RESUME_LINES + ["Mortgage PII Service | Python, FastAPI, spaCy, Presidio, Docker", "IEEE ICCICT 2026, accepted"]:
            with self.subTest(line=line[:40]):
                self.assertIn(line, source)

    def test_committed_pdf_matches_a_fresh_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "resume.pdf"
            self.generator.main(fresh)
            self.assertEqual(fresh.read_bytes(), self.generator.OUTPUT.read_bytes(),
                             "app/static/Harshil_Agrawal_Resume.pdf is stale: run scripts/generate_resume_pdf.py")


if __name__ == "__main__":
    unittest.main()
