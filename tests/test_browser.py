"""Browser tests: notebook.js and the CSS states it drives, in headless Chromium.

Skipped unless Playwright is installed:  uv pip install -r requirements-dev.txt && playwright install chromium
"""
import re
import unittest

from _server import start
from app.main import NORMAL
from test_unit import EMAIL

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

# Outputs a reader can't see: transparent (still queued) or not laid out at all.
HIDDEN_OUTPUTS = "[...document.querySelectorAll('.cell.code .out')].filter(o => getComputedStyle(o).opacity !== '1' || !o.offsetHeight).length"
NB_IO = "document.documentElement.classList.contains('nb-io')"


def setUpModule():
    global server, BASE, pw, browser
    if sync_playwright is None:
        raise unittest.SkipTest("Playwright is not installed")
    server, BASE = start()
    pw = sync_playwright().start()
    browser = pw.chromium.launch()


def tearDownModule():
    browser.close()
    pw.stop()
    server.should_exit = True


class BrowserTest(unittest.TestCase):
    def open(self, path="/", *, motion=True, js=True, width=1440, init=None, block=None, permissions=()):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, java_script_enabled=js, color_scheme="light",
                                  reduced_motion="no-preference" if motion else "reduce", permissions=list(permissions))
        self.addCleanup(ctx.close)
        if init:
            ctx.add_init_script(init)
        page = ctx.new_page()
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and self.errors.append(m.text))
        if block:
            page.route(block, lambda route: route.abort())
        page.goto(BASE + path)
        return page


class Visibility(BrowserTest):
    def test_cells_run_in_reading_order_as_they_scroll_into_view(self):
        page = self.open("/")
        self.assertTrue(page.evaluate(NB_IO))
        last = page.locator(".cell.code").last
        self.assertEqual(last.get_attribute("data-state"), "queued")
        self.assertEqual(last.locator(".out").evaluate("o => getComputedStyle(o).opacity"), "0")
        for _ in range(40):
            page.evaluate("scrollBy(0, 400)")
            page.wait_for_timeout(50)
        page.wait_for_function("[...document.querySelectorAll('.cell.code')].every(c => c.dataset.state === 'done')", timeout=10_000)
        numbers = page.eval_on_selector_all(".cell.code .row.out .n", "ns => ns.map(n => +n.textContent)")
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        page.wait_for_function("[...document.querySelectorAll('.k-state')].every(s => s.textContent === 'idle')")
        page.wait_for_timeout(600)  # let the reveal animation finish
        self.assertEqual(page.evaluate(HIDDEN_OUTPUTS), 0)
        self.assertEqual(self.errors, [])

    def test_reduced_motion_shows_every_output_at_once(self):
        page = self.open("/", motion=False)
        self.assertFalse(page.evaluate(NB_IO))
        self.assertEqual(page.evaluate(HIDDEN_OUTPUTS), 0)

    def test_without_javascript_every_output_is_visible(self):
        for path in ["/", "/demo"]:
            with self.subTest(path):
                page = self.open(path, js=False)
                self.assertEqual(page.evaluate(HIDDEN_OUTPUTS), 0)
                self.assertEqual(page.locator("#model-cell .risk-p").inner_text(), f"{NORMAL['probability']['defect'] * 100:.1f}%")

    def test_outputs_show_even_if_notebook_js_fails_to_load(self):
        page = self.open("/", block="**/notebook.js*")
        self.assertFalse(page.evaluate(NB_IO))
        self.assertEqual(page.evaluate(HIDDEN_OUTPUTS), 0)

    def test_print_shows_every_output_and_hides_the_app_chrome(self):
        page = self.open("/")
        page.emulate_media(media="print")
        self.assertEqual(page.evaluate(HIDDEN_OUTPUTS), 0)
        for chrome in [".bar", ".toc", ".statusbar"]:
            self.assertFalse(page.locator(chrome).is_visible(), chrome)


class CodeSwitch(BrowserTest):
    def test_switch_hides_the_code_keeps_the_results_and_remembers(self):
        page = self.open("/", motion=False)
        switch = page.locator(".btn-code")
        self.assertEqual(switch.get_attribute("aria-pressed"), "true")
        self.assertTrue(page.locator(".row.in").first.is_visible())
        self.assertTrue(page.locator(".howto .h-on").is_visible())
        switch.click()
        self.assertEqual(switch.get_attribute("aria-pressed"), "false")
        self.assertFalse(page.locator(".row.in").first.is_visible())
        self.assertTrue(page.locator(".facts").is_visible())
        self.assertTrue(page.locator(".howto .h-off").is_visible())
        self.assertEqual(page.evaluate("localStorage.getItem('code')"), "off")
        page.locator(".howto .h-off [data-code-toggle]").click()
        self.assertEqual(switch.get_attribute("aria-pressed"), "true")
        self.assertTrue(page.locator(".row.in").first.is_visible())

    def test_saved_choice_is_applied_by_the_head_script_before_paint(self):
        page = self.open("/", init="localStorage.setItem('code', 'off')", block="**/notebook.js*")
        self.assertTrue(page.evaluate("document.documentElement.classList.contains('code-off')"))
        self.assertFalse(page.locator(".row.in").first.is_visible())


class LiveModel(BrowserTest):
    def test_presets_ask_the_server_and_show_its_answer(self):
        for path in ["/", "/demo"]:
            with self.subTest(path):
                page = self.open(path, motion=False)
                cell = page.locator("#model-cell")
                with page.expect_response("**/predict") as response:
                    cell.get_by_role("button", name="Hot & humid").click()
                answer = response.value.json()
                self.assertEqual(answer["prediction"], 1)
                page.wait_for_function("document.querySelector('#model-cell .risk').dataset.verdict === 'bad'")
                self.assertEqual(cell.locator(".risk-p").inner_text(), f"{answer['probability']['defect'] * 100:.1f}%")
                self.assertEqual(cell.locator(".verdict-t").inner_text(), "Defect likely")
                self.assertEqual(cell.locator('[data-v="temperature"]').inner_text(), "92.0")
                self.assertEqual(cell.locator('[data-v="humidity"]').inner_text(), "82")
                self.assertEqual(cell.locator('.chip[aria-pressed="true"]').all_inner_texts(), ["Hot & humid"])
                self.assertIn("defect likely", page.locator("#risk-sr").inner_text())
                cell.get_by_role("button", name="Normal").click()
                page.wait_for_function("document.querySelector('#model-cell .risk').dataset.verdict === 'ok'")
                self.assertEqual(cell.locator(".verdict-t").inner_text(), "No defect expected")
                self.assertEqual(self.errors, [])

    def test_slider_moves_are_debounced_into_one_request(self):
        page = self.open("/", motion=False)
        requests = []
        page.on("request", lambda r: "/predict" in r.url and requests.append(r))
        page.locator('input[type=range][data-for="temperature"]').focus()
        for _ in range(5):
            page.keyboard.press("ArrowRight")
        page.wait_for_timeout(700)
        self.assertEqual(len(requests), 1)
        self.assertEqual(page.locator("#w-temperature").input_value(), "77.5")
        self.assertEqual(page.locator('[data-v="temperature"]').inner_text(), "77.5")
        self.assertEqual(page.locator('.chip[aria-pressed="true"]').count(), 0)

    def test_typed_values_move_the_slider_and_out_of_range_is_explained(self):
        page = self.open("/", motion=False)
        with page.expect_response("**/predict"):
            page.locator("#w-temperature").fill("95")
        self.assertEqual(page.locator('input[type=range][data-for="temperature"]').input_value(), "95")
        self.assertEqual(page.locator('[data-v="temperature"]').inner_text(), "95.0")
        requests = []
        page.on("request", lambda r: "/predict" in r.url and requests.append(r))
        page.locator("#w-temperature").fill("500")
        page.wait_for_timeout(400)
        self.assertEqual(requests, [])
        self.assertEqual(page.locator("#model-cell").get_attribute("data-state"), "error")
        self.assertIn("Temperature must be between 30 and 120 °C", page.locator("#model-cell .ms").inner_text())


class Keyboard(BrowserTest):
    def test_skip_link_is_the_first_stop_and_jumps_into_the_notebook(self):
        page = self.open("/", motion=False)
        page.keyboard.press("Tab")
        self.assertEqual(page.evaluate("document.activeElement.className"), "skip")
        self.assertGreaterEqual(page.locator(".skip").bounding_box()["y"], 0)
        page.keyboard.press("Enter")
        self.assertEqual(page.evaluate("document.activeElement.id"), "nb")

    def test_j_and_k_select_cells_and_shift_enter_reruns_one(self):
        page = self.open("/", motion=False)
        for key in "jjjk":
            page.keyboard.press(key)
        self.assertEqual(page.eval_on_selector_all(".cell", "cs => cs.findIndex(c => c.classList.contains('is-active'))"), 1)
        before = page.locator(".cell.code").count()
        page.keyboard.press("Shift+Enter")
        page.wait_for_function(f"document.querySelector('#glance .row.out .n').textContent === '{before + 1}'", timeout=3000)


class Chrome(BrowserTest):
    def test_theme_toggle_switches_and_remembers(self):
        page = self.open("/", motion=False)
        toggle = page.locator(".theme-toggle")
        self.assertEqual(toggle.get_attribute("aria-pressed"), "false")
        toggle.click()
        self.assertEqual(page.evaluate("document.documentElement.dataset.theme"), "dark")
        self.assertEqual(page.evaluate("getComputedStyle(document.body).backgroundColor"), "rgb(11, 12, 16)")
        page.reload()
        self.assertEqual(page.evaluate("document.documentElement.dataset.theme"), "dark")
        self.assertEqual(toggle.get_attribute("aria-pressed"), "true")

    def test_copy_email_uses_the_clipboard(self):
        page = self.open("/", motion=False, permissions=["clipboard-read", "clipboard-write"])
        page.get_by_role("button", name="Copy email").click()
        page.wait_for_function("document.querySelector('[data-copy]').textContent === 'Copied'")
        self.assertEqual(page.evaluate("navigator.clipboard.readText()"), EMAIL)
        self.assertEqual(page.locator("#copy-status").inner_text(), "Copied to clipboard")

    def test_copy_email_falls_back_to_mailto_without_a_clipboard(self):
        init = ("Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('denied'))}});"
                "window.open = (url, target) => { window.opened = [url, target]; };")
        page = self.open("/", motion=False, init=init)
        page.get_by_role("button", name="Copy email").click()
        page.wait_for_function("window.opened")
        self.assertEqual(page.evaluate("window.opened"), [f"mailto:{EMAIL}", "_self"])

    def test_blacksburg_clock_shows_a_time(self):
        page = self.open("/", motion=False)
        self.assertRegex(page.locator("#bb-time").inner_text(), r"^\d{1,2}:\d{2}\s[AP]M$")

    def test_every_page_fits_a_phone_and_logs_no_errors(self):
        for path in ["/", "/demo", "/resume", "/missing"]:
            for width in [390, 1440]:
                with self.subTest(path=path, width=width):
                    page = self.open(path, width=width)
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth - innerWidth"), 0)
                    self.assertEqual(page.locator(".toc").is_visible(), width >= 1280)
                    self.assertEqual([e for e in self.errors if not (path == "/missing" and "404" in e)], [])


if __name__ == "__main__":
    unittest.main()
