"""Integration tests: the real app on uvicorn, exercised over HTTP the way a browser or curl would."""
import html
import json
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from _server import start
from app.main import NORMAL, PRESETS, PROJECTS, model_meta, predict_reading
from test_unit import EMAIL, PHONE, RESUME_LINES, RETIRED

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://harshil-portfolio.duckdns.org"
PAGES = {}


def setUpModule():
    global server, BASE
    server, BASE = start()
    for path in ["/", "/demo", "/resume", "/no-such-page"]:
        PAGES[path] = fetch(path)[2]


def tearDownModule():
    server.should_exit = True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch(path, data=None, accept="text/html", follow=True):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers={"Accept": accept})
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=10) as res:
            return res.status, res.headers, res.read().decode(errors="replace")
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read().decode(errors="replace")


def text(markup):
    """Visible text, roughly: no scripts or styles, tags stripped, entities decoded, whitespace collapsed."""
    markup = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def presets_on(page):
    return [json.loads(html.unescape(m)) for m in re.findall(r"data-preset='([^']+)'", page)]


def pct(p):
    return f"{p * 100:.1f}%"


class Routes(unittest.TestCase):
    def test_pages_render_as_html(self):
        for path in ["/", "/demo", "/resume"]:
            status, headers, _ = fetch(path)
            with self.subTest(path):
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["content-type"])

    def test_retired_pages_redirect_to_their_home_sections(self):
        for path, target, code in [("/projects", "/#work", 301), ("/contact", "/#contact", 301), ("/blog", "/#work", 307)]:
            status, headers, _ = fetch(path, follow=False)
            with self.subTest(path):
                self.assertEqual((status, headers["location"]), (code, target))

    def test_unknown_page_renders_the_notebook_404(self):
        status, _, body = fetch("/no-such-page")
        self.assertEqual(status, 404)
        self.assertIn("<html", body)
        self.assertIn("FileNotFoundError: no page at /no-such-page", text(body))

    def test_404_escapes_the_requested_path(self):
        status, _, body = fetch("/%3Cscript%3Ealert(1)%3C/script%3E")
        self.assertEqual(status, 404)
        self.assertNotIn("<script>alert(1)", body)
        self.assertIn("&lt;script&gt;alert(1)", body)

    def test_api_clients_get_json_errors_not_html(self):
        status, _, body = fetch("/no-such-page", accept="application/json")
        self.assertEqual((status, json.loads(body)), (404, {"detail": "Not Found"}))

    def test_health(self):
        status, _, body = fetch("/health", accept="application/json")
        self.assertEqual((status, json.loads(body)), (200, {"status": "healthy", "model_loaded": True}))

    def test_api_projects_serves_the_same_data_that_renders_the_site(self):
        status, _, body = fetch("/api/projects", accept="application/json")
        self.assertEqual((status, json.loads(body)), (200, json.loads(json.dumps(PROJECTS))))


class Predict(unittest.TestCase):
    def test_presets_on_both_pages_answer_from_the_server(self):
        expected = [values for _, values in PRESETS]
        for path in ["/", "/demo"]:
            with self.subTest(path):
                self.assertEqual(presets_on(PAGES[path]), expected)
        outcomes = []
        for values in expected:
            status, _, body = fetch("/predict", values, "application/json")
            self.assertEqual(status, 200, values)
            self.assertEqual(json.loads(body), predict_reading(values))
            outcomes.append(json.loads(body)["prediction"])
        self.assertEqual(outcomes[0], 0)
        self.assertIn(1, outcomes)

    def test_rejects_out_of_range_and_missing_readings(self):
        normal = PRESETS[0][1]
        for bad in [{**normal, "temperature": 1e6}, {**normal, "humidity": -1}, {k: v for k, v in normal.items() if k != "rpm"}]:
            with self.subTest(bad):
                self.assertEqual(fetch("/predict", bad, "application/json")[0], 422)


class Chrome(unittest.TestCase):
    def test_head_has_canonical_social_and_person_metadata(self):
        for path in ["/", "/demo", "/resume"]:
            page = PAGES[path]
            with self.subTest(path):
                self.assertIn(f'<link rel="canonical" href="{SITE}{path}">', page)
                self.assertIn(f'<meta property="og:url" content="{SITE}{path}">', page)
                self.assertRegex(page, r'<meta name="description" content="[^"]{60,}">')
                person = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
                self.assertEqual((person["@type"], person["name"]), ("Person", "Harshil Agrawal"))

    def test_tabs_link_every_page_and_mark_the_current_one(self):
        for path, current in [("/", "harshil_agrawal"), ("/demo", "model"), ("/resume", "resume"), ("/no-such-page", None)]:
            tabs = re.findall(r'<a class="tab[^"]*" href="([^"]+)"([^>]*)><span>(\w+)', PAGES[path])
            with self.subTest(path):
                self.assertEqual([name for _, _, name in tabs], ["harshil_agrawal", "work", "model", "resume", "contact"])
                self.assertEqual([href for href, _, _ in tabs][1:], ["/#work", "/demo", "/resume", "/#contact"])
                self.assertEqual([name for _, attrs, name in tabs if 'aria-current="page"' in attrs], [current] if current else [])

    def test_every_local_link_and_asset_resolves(self):
        urls = {u for page in PAGES.values() for u in re.findall(r'(?:href|src)="(/[^"#]*)', page)}
        self.assertTrue({"/static/site.css", "/static/notebook.js", "/demo", "/resume"} <= {u.split("?")[0] for u in urls})
        for url in sorted(urls):
            with self.subTest(url):
                self.assertEqual(fetch(url, accept="*/*")[0], 200)

    def test_in_page_anchors_exist(self):
        home_ids = set(re.findall(r'\bid="([^"]+)"', PAGES["/"]))
        for path, page in PAGES.items():
            ids = set(re.findall(r'\bid="([^"]+)"', page))
            for target in re.findall(r'href="#([^"]+)"', page):
                with self.subTest(path=path, anchor=target):
                    self.assertIn(target, ids)
            for target in re.findall(r'href="/#([^"]+)"', page):
                with self.subTest(path=path, anchor=target):
                    self.assertIn(target, home_ids)

    def test_static_files_are_served_with_their_types(self):
        for url, kind in [("/static/site.css", "text/css"), ("/static/notebook.js", "javascript"),
                          ("/static/fonts/instrument-sans.woff2", "font/woff2"), ("/static/fonts/jetbrains-mono.woff2", "font/woff2")]:
            with self.subTest(url):
                self.assertIn(kind, fetch(url, accept="*/*")[1]["content-type"])

    def test_no_page_shows_a_retired_fact(self):
        for path, page in PAGES.items():
            for pattern in RETIRED:
                with self.subTest(path=path, pattern=pattern):
                    self.assertIsNone(re.search(pattern, page))


class Home(unittest.TestCase):
    page = property(lambda self: PAGES["/"])

    def test_hero_copy_is_the_approved_wording(self):
        words = text(self.page)
        for line in ["M.S. Data Science · Virginia Tech", "Harshil Agrawal", "I turn messy data into models people actually use.",
                     "From a WhatsApp ordering assistant that has handled 10,000+ orders to an IEEE paper on deep reinforcement learning for trading.",
                     "Open to GA roles, research & Summer 2027 ML/DS internships", "Read the work ↓ Resume (PDF) or try the live model ↓"]:
            with self.subTest(line):
                self.assertIn(line, words)
        self.assertIn("<title>Harshil Agrawal · harshil_agrawal.ipynb</title>", self.page)
        self.assertIn('<h1>Harshil Agrawal</h1>', self.page)
        self.assertIn('<a href="#llm-ordering-platform">10,000+ orders</a>', self.page)
        self.assertIn('<a href="#lstm-drl-trading">IEEE paper</a>', self.page)
        self.assertRegex(self.page, r'<a class="btn" href="/static/Harshil_Agrawal_Resume.pdf" target="_blank" rel="noopener">Resume \(PDF\)</a>')

    def test_about_cell_lists_the_confirmed_facts(self):
        words = text(self.page)
        for fact in ["Studying M.S. Data Science, Virginia Tech Aug 2026 – May 2028",
                     "Previously Data & AI Engineering Intern, Prowess Consulting Dec 2025 – Jun 2026",
                     "Degree B.Tech Computer Engineering, NMIMS (MPSTME), Mumbai May 2026",
                     "Research Hybrid LSTM + deep RL for trading, IEEE ICCICT 2026 accepted", "Based in Blacksburg, VA"]:
            with self.subTest(fact):
                self.assertIn(fact, words)

    def test_evidence_table_has_one_row_per_project(self):
        rows = re.findall(r'<tr><th scope="row">(\d)</th><td><a href="#([\w-]+)">', self.page)
        self.assertEqual(rows, [(str(i), p["slug"]) for i, p in enumerate(PROJECTS)])
        for p in PROJECTS:
            self.assertIn(f'<td class="r v">{p["metric"]["value"]}</td>', self.page)
        self.assertIn("5 rows × 4 columns", self.page)

    def test_each_project_gets_a_case_cell(self):
        for n, p in enumerate(PROJECTS, 3):
            cell = re.search(rf'<div class="cell code" id="{p["slug"]}">(.*?)</article>', self.page, re.S)
            with self.subTest(p["slug"]):
                self.assertIsNotNone(cell)
                cell = cell.group(1)
                self.assertIn(f'In [<b class="n">{n}</b>]:', cell)
                self.assertIn(f"Fig. {p['no']} · {p['trace_label']}", cell)
                self.assertIn(f"<b>{p['metric']['value']}</b><span>{p['metric']['label']}</span>", cell)
                self.assertIn(f"Stack: {', '.join(p['tags'])}", cell)
                for words in [p["name"], p["headline"], p["summary"], p["status"], *p["trace"], *p["decisions"]]:
                    self.assertIn(words, text(cell))
                self.assertEqual(f"Why I built it this way <span class=\"dec-n\">({len(p['decisions'])})</span>" in cell, bool(p["decisions"]))
        self.assertIn('<a href="#model">Try the live model <span aria-hidden="true">→</span></a>', self.page)

    def test_live_model_cell_shows_the_server_prediction_and_honest_baseline(self):
        live = text(self.page.split('id="model-cell"')[1].split('id="contact"')[0])
        self.assertIn(f"{pct(NORMAL['probability']['defect'])} defect probability No defect expected", live)
        self.assertIn(f"Random Forest · {pct(model_meta['accuracy'])} accurate on held-out test data, "
                      f"vs {pct(model_meta['baseline_accuracy'])} for always guessing “no defect” · full model card →", live)
        self.assertIn("88.1% accurate", live)
        self.assertIn("vs 69.8%", live)
        for label in ["Temperature", "Humidity", "Pressure", "Vibration", "Spindle speed", "50% decision line"]:
            self.assertIn(label, live)
        self.assertEqual(len(re.findall(r'<input type="range"', self.page)), 5)
        self.assertEqual(len(re.findall(r'<input type="number"', self.page)), 5)

    def test_contact_cell_offers_email_copy_and_profiles(self):
        for snippet in [f'<a class="email" href="mailto:{EMAIL}">{EMAIL}</a>', f'data-copy="{EMAIL}"', f'data-fallback="mailto:{EMAIL}"',
                        f'href="mailto:{EMAIL}?subject=Portfolio%20inquiry"', 'href="https://github.com/Harshil411"',
                        'href="https://www.linkedin.com/in/harshil-agrawal/"', '<time id="bb-time">']:
            with self.subTest(snippet):
                self.assertIn(snippet, self.page)


class Demo(unittest.TestCase):
    page = property(lambda self: PAGES["/demo"])

    def test_model_card_quotes_the_evaluation(self):
        words = text(self.page)
        for fact in ["88.1%", "69.8%", "always guessing “no defect”", "4,000", "1,000", "Random Forest", "synthetic"]:
            with self.subTest(fact):
                self.assertIn(fact, words)

    def test_feature_importances_are_sorted_from_strongest(self):
        shown = [float(v) for v in re.findall(r'<span class="imp-v">([\d.]+)%</span>', self.page)]
        expected = sorted((v * 100 for v in model_meta["feature_importances"].values()), reverse=True)
        self.assertEqual(shown, [round(v, 1) for v in expected])

    def test_terminal_example_shows_the_real_response(self):
        self.assertIn("curl -X POST https://harshil-portfolio.duckdns.org/predict", self.page)
        self.assertIn(fetch("/predict", PRESETS[0][1], "application/json")[2], text(self.page))

    def test_has_the_live_cell(self):
        self.assertIn('id="model-cell"', self.page)
        self.assertIn('id="reading"', self.page)


class Resume(unittest.TestCase):
    def test_resume_page_has_the_approved_entries_and_contacts(self):
        page, words = PAGES["/resume"], text(PAGES["/resume"])
        for line in RESUME_LINES + ["Mortgage PII Service", "IEEE ICCICT 2026 · accepted", PHONE, EMAIL]:
            with self.subTest(line=line[:40]):
                self.assertIn(line, words)
        self.assertIn('href="tel:+15409986474"', page)
        self.assertIn('href="/static/Harshil_Agrawal_Resume.pdf" download', page)


class SmokeScript(unittest.TestCase):
    def test_check_site_passes_against_the_running_app(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_site.py"), BASE], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
