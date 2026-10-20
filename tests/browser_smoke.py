"""Bounded real-browser acceptance check. Starts and always stops its own child server.

Run: python tests/browser_smoke.py
Screenshots are inspection artifacts in test-results/ (not deliverables).
"""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent


def main():
    output = ROOT / "test-results"
    output.mkdir(exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="onboarding-browser-") as temp:
        env = dict(os.environ, PORT=str(port), ONBOARDING_DB=str(Path(temp) / "browser.sqlite3"), PYTHONUTF8="1")
        with (Path(temp) / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, "-m", "app"], cwd=ROOT, env=env,
                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                url = f"http://127.0.0.1:{port}"
                for _ in range(60):
                    if server.poll() is not None:
                        raise RuntimeError((Path(temp) / "server.log").read_text(encoding="utf-8"))
                    try:
                        with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Local server did not start within 12 seconds")
                run_browser(url, output)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


def run_browser(url, output):
    errors, api_errors, external = [], [], []
    with sync_playwright() as pw:
        exe = Path(pw.chromium.executable_path)
        if not exe.is_file():
            exe = next((p for p in [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")] if p.is_file()), None)
            if exe is None:
                raise RuntimeError("Install Playwright Chromium or use the existing Edge/Chrome browser")
        browser = pw.chromium.launch(executable_path=str(exe), headless=True)
        try:
            page = browser.new_page(viewport={"width": 1512, "height": 1100}, device_scale_factor=1)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("response", lambda r: api_errors.append(f"{r.status} {r.url}") if "/api/" in r.url and r.status >= 400 else None)
            page.on("request", lambda r: external.append(r.url) if not r.url.startswith(url) else None)
            base = url + "/supplier-management/rollouts/nordtal-november"
            page.goto(url, wait_until="networkidle")
            if '--capture-docs' in sys.argv:
                assets = ROOT / 'docs' / 'assets'
                assets.mkdir(parents=True, exist_ok=True)
                expect(page.get_by_role('heading', name='November supplier rollout')).to_be_visible()
                page.screenshot(path=str(assets / 'rollout.png'))
                page.goto(base + '/suppliers/weser', wait_until='networkidle')
                expect(page.get_by_role('heading', name='Resolution assistance')).to_be_visible()
                page.screenshot(path=str(assets / 'supplier-record.png'))
                assert not errors, errors
                print(json.dumps({'status':'PASS','documentationImages':str(assets),'database':'isolated temporary fixture'}))
                return
            if '--layout-only' in sys.argv:
                page.set_viewport_size({'width':390,'height':844})
                print(json.dumps(page.evaluate('''() => ({width:innerWidth, scroll:document.documentElement.scrollWidth,
                  elements:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && !e.parentElement?.closest('.table-scroll')).slice(0,20).map(e=>({tag:e.tagName,cls:String(e.className),right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width,overflow:getComputedStyle(e).overflowX})),
                  boxes:['html','body','.app-shell','.workspace','main','.table-card','.table-scroll','.supplier-table'].map(s=>{const e=document.querySelector(s);return{selector:s,width:e.getBoundingClientRect().width,scroll:e.scrollWidth,overflow:getComputedStyle(e).overflowX}})})''')))
                return
            expect(page.get_by_role("heading", name="November supplier rollout")).to_be_visible()
            assert page.locator(".supplier-table tbody tr").count() == 30
            page.screenshot(path=str(output / "rollout-desktop.png"), full_page=True)
            search = page.get_by_label("Search suppliers")
            search.fill("Weser")
            expect(page.locator(".supplier-table tbody tr")).to_have_count(1)
            page.get_by_role("button", name="Weser Precision Components GmbH", exact=True).click()
            expect(page.get_by_role("heading", name="Resolution assistance")).to_be_visible()
            page.get_by_role("button", name="Back to rollout").click()
            expect(search).to_have_value("Weser")
            page.get_by_role("button", name="Clear", exact=True).click()
            page.goto(base + "/suppliers/weser", wait_until="networkidle")
            expect(page.get_by_role("heading", name="Weser Precision Components GmbH")).to_be_visible()
            assert page.get_by_role("button", name="Propose contact correction").count() == 0
            page.get_by_role("button", name="Open evidence E05", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("Hamburg repair operation")
            page.get_by_role("button", name="Close record", exact=True).click()
            page.screenshot(path=str(output / "supplier-desktop.png"), full_page=True)

            # An actually persisted task, with editable draft.
            page.get_by_role("button", name="Create verification task", exact=True).click()
            expect(page.get_by_label("Task title")).to_have_value("Verify the referred contact and relationship scope")
            page.get_by_role("button", name="Create task", exact=True).click()
            expect(page.get_by_role("button", name="Task already assigned", exact=True)).to_be_disabled()
            page.reload(wait_until="networkidle")
            expect(page.get_by_text("Verify the referred contact and relationship scope", exact=True)).to_be_visible()

            def record_verification():
                page.get_by_role("button", name="Record buyer verification", exact=True).click()
                page.get_by_role("button", name="Insert this case’s synthetic example", exact=True).click()
                page.get_by_role("button", name="Record verification", exact=True).click()

            def make_request():
                page.get_by_role("button", name="Propose contact correction", exact=True).click()
                page.get_by_role("button", name="Create correction request", exact=True).click()

            def approve_request():
                page.get_by_role("button", name="Review and approve request", exact=True).click()
                page.get_by_role("button", name="Insert a synthetic review note", exact=True).click()
                page.get_by_role("button", name="Approve reviewed request", exact=True).click()

            record_verification()
            make_request()
            approve_request()
            page.get_by_role("button", name="Open demonstration controls", exact=True).click()
            page.get_by_role("button", name="Add evidence / invalidate review", exact=True).click()
            page.get_by_role("button", name="Close panel", exact=True).click()
            expect(page.get_by_text("Evidence changed. Review the latest case before processing.", exact=True)).to_be_visible()
            assert page.get_by_role("button", name="Process simulated update", exact=True).count() == 0
            approve_request()
            page.get_by_role("button", name="Process simulated update", exact=True).click()
            expect(page.get_by_text("DEMO_ACK:", exact=False)).to_be_visible()
            contact = page.locator(".contacts-grid .contact-card").nth(1)
            expect(contact).to_contain_text("Tom Keller")
            expect(page.locator(".contacts-grid .contact-card").nth(0)).to_contain_text("Anna Becker")
            page.get_by_role("button", name="Open demonstration controls", exact=True).click()
            expect(page.get_by_role("button", name="Record first test confirmation", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Record synthetic registration", exact=True).click()
            page.get_by_role("button", name="Record first test confirmation", exact=True).click()
            page.get_by_role("button", name="Close panel", exact=True).click()
            expect(page.locator(".milestone-grid .completed")).to_have_count(4)
            page.get_by_role("tab", name="Activity").click()
            expect(page.get_by_text("Review approved", exact=True)).to_have_count(2)
            page.get_by_role("tab", name="Onboarding", exact=True).click()

            # Unresolved authority must remain unresolved after the fixture response.
            page.goto(base + "/suppliers/havel", wait_until="networkidle")
            record_verification()
            expect(page.locator('.task-item .badge').filter(has_text="inconclusive")).to_be_visible()
            assert page.get_by_role("button", name="Propose contact correction", exact=True).count() == 0

            # Distinct blockers do not receive contact-replacement controls.
            for cid, button in [("elbe", "Create follow-up task"), ("rhein", "Create technical task")]:
                page.goto(base + "/suppliers/" + cid, wait_until="networkidle")
                expect(page.get_by_role("button", name=button, exact=True)).to_be_visible()
                assert page.get_by_role("button", name="Record buyer verification", exact=True).count() == 0

            # Fixture-driven rejection has an independent persisted result.
            page.goto(base + "/suppliers/weser", wait_until="networkidle")
            page.get_by_role("button", name="Open demonstration controls", exact=True).click()
            page.get_by_label("Main case processing outcome").click()
            page.get_by_role("option", name="Rejected · scope locked", exact=True).click()
            page.get_by_role("button", name="Reset synthetic rollout", exact=True).click()
            page.get_by_role("button", name="Restore sample data", exact=True).click()
            record_verification()
            make_request()
            approve_request()
            page.get_by_role("button", name="Process simulated update", exact=True).click()
            expect(page.get_by_text("DEMO_SCOPE_LOCKED:", exact=False)).to_be_visible()
            expect(page.locator(".contacts-grid .contact-card").nth(1)).to_contain_text("Anna Becker")
            page.screenshot(path=str(output / "rejected-desktop.png"), full_page=True)
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")

            # Mobile: record and panel must remain readable, without page-level overflow.
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(output / "supplier-mobile.png"), full_page=True)
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "Mobile page overflow"
            page.get_by_role("button", name="Back to rollout").click()
            page.screenshot(path=str(output / "rollout-mobile.png"), full_page=True)
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "Mobile list page overflow"
            page.get_by_label("Search suppliers").fill("no-such-supplier")
            expect(page.get_by_role("heading", name="No suppliers match these filters.")).to_be_visible()
            page.get_by_role("button", name="Clear filters", exact=True).click()
            assert not errors, errors
            assert not api_errors, api_errors
            assert not external, external
            print(json.dumps({"status":"PASS", "checks":["30 supplier records", "embedded navigation", "deep link", "evidence",
                "task persistence", "verification", "approval", "stale review", "accepted update", "independent milestones",
                "inconclusive result", "different blocker routes", "rejected update", "mobile layout", "empty search", "no external requests"],
                "javascriptErrors":errors, "screenshots":str(output)}))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
