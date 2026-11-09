"""Smoke-check a running portfolio. Usage: python scripts/check_site.py [base_url]

Fails loudly (AssertionError) if a page breaks, a project metric goes missing from the home notebook,
the live-model presets stop showing both outcomes, or /predict accepts out-of-range input.
The full suites live in tests/ (python -m unittest discover tests); this one also runs against production.
"""
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
TEMPLATES = Path(__file__).resolve().parents[1] / "app" / "templates"


def request(path, data=None, accept="text/html"):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(BASE + path, data=body, headers={"Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:  # follows the /projects and /contact redirects
            return res.status, res.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


pages = {path: request(path) for path in ["/", "/projects", "/demo", "/resume", "/contact"]}
for path, (status, _) in pages.items():
    assert status == 200, f"{path} returned {status}"

status, body = request("/no-such-page")
assert status == 404 and "FileNotFoundError" in body, "unknown routes should render the notebook 404 page"

status, body = request("/api/projects", accept="application/json")
projects = json.loads(body)
home = pages["/"][1]
for p in projects:
    value = p["metric"]["value"]
    assert f'<td class="r v">{value}</td>' in home, f"{p['name']} metric {value} missing from the evidence table"
    assert f"<b>{value}</b>" in home, f"{p['name']} metric {value} missing from its case cell"

presets = [json.loads(html.unescape(m)) for m in re.findall(r"data-preset='([^']+)'", pages["/demo"][1])]
assert presets, "live-model presets not found on /demo"
outcomes = []
for preset in presets:
    status, body = request("/predict", preset, "application/json")
    assert status == 200, f"/predict {preset} returned {status}"
    result = json.loads(body)
    assert abs(sum(result["probability"].values()) - 1) < 1e-3, result
    outcomes.append(result["prediction"])
assert outcomes[0] == 0 and 1 in outcomes, f"presets should start normal and show a defect: {outcomes}"

status, _ = request("/predict", {**presets[0], "temperature": 1e6}, "application/json")
assert status == 422, f"out-of-range input should be rejected with 422, got {status}"

for template in TEMPLATES.glob("*.html"):
    for style in re.findall(r'style="([^"]*)"', template.read_text()):
        assert style.strip().startswith("--"), f"{template.name}: inline style {style!r}; use a class"

print(f"ok: {len(pages)} pages, 404, {len(projects)} projects, {len(presets)} presets, bounds, templates")
