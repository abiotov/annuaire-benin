"""Smoke test de l'atlas publié (Playwright, chromium headless).

Charge la page telle que commitée dans docs/atlas/, attend la couche
cartographique et vérifie les éléments structurants. Ne tourne que si
la variable d'environnement E2E=1 est posée (la CI la pose ; en local,
il faut `pip install -e ".[e2e]"` puis `playwright install chromium`).
"""

import http.server
import os
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("E2E") != "1", reason="E2E non demandé")

ATLAS_DIR = Path(__file__).resolve().parents[2] / "docs" / "atlas"


@pytest.fixture(scope="module")
def atlas_url():
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(ATLAS_DIR), **kw
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


def test_atlas_loads_and_renders(atlas_url):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 900})
        page.goto(atlas_url)

        expect(page).to_have_title("Atlas économique du Bénin")
        # La couche des 77 communes est dessinée (le masque en plus).
        page.wait_for_selector(".leaflet-interactive", timeout=15_000)
        assert page.locator(".leaflet-interactive").count() >= 77
        # Compteurs du héros remplis par le JS.
        expect(page.locator("#tiles .v").first).not_to_have_text("0")
        # La vue tableau liste les 77 communes.
        page.click("#viewBtn")
        assert page.locator("#tableBody tr").count() == 77
        # La métrique spécialisation sans secteur affiche l'invite dédiée.
        page.click("#viewBtn")  # retour carte
        page.click('[data-metric="spec"]')
        expect(page.locator("#legend")).to_contain_text("choisissez un secteur")
        # Un secteur choisi : la légende divergente apparaît.
        page.select_option("#sectorSel", index=1)
        expect(page.locator("#legend")).to_contain_text("moyenne")
        browser.close()


def test_natural_language_search_answers_and_drives_the_map(atlas_url):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 900})
        page.goto(atlas_url)
        page.wait_for_selector(".leaflet-interactive", timeout=15_000)
        page.fill("#communeSearch", "combien de pressings à Cotonou ?")
        page.press("#communeSearch", "Enter")
        expect(page.locator("#answer")).to_be_visible()
        expect(page.locator("#answerTxt")).to_contain_text("COTONOU")
        # La réponse pilote la carte : secteur sélectionné dans le filtre.
        assert page.input_value("#sectorSel") == "services-divers"
        browser.close()


def test_atlas_mobile_has_no_horizontal_overflow(atlas_url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(atlas_url)
        page.wait_for_selector(".leaflet-interactive", timeout=15_000)
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 1, f"débordement horizontal de {overflow}px sur mobile"
        browser.close()
