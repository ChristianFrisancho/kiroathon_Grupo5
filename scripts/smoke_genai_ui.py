#!/usr/bin/env python3
"""Prueba de humo en navegador real (Chromium/Playwright) de los botones con GenAI contra la URL desplegada.

Pulsa «Crear borrador», «Regenerar borrador», «Adaptar en Mi aula» y «Resumir acuerdos», y exige que cada
resultado venga de Amazon Bedrock (no «Respaldo local»). Mide el tiempo de cada botón y guarda capturas.
Deja una sola sesión de prueba titulada «Prueba de verificación» (la adaptación se descarta).
Uso: python3 scripts/smoke_genai_ui.py --base https://... --report docs/evidencias/genai-botones.json
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "capturas"


def api_get(base, path):
    with urllib.request.urlopen(base + path, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--report", default="docs/evidencias/genai-botones.json")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    report = {"timestampUtc": datetime.now(timezone.utc).isoformat(), "commit": commit, "baseUrl": base,
              "browser": "Chromium headless (Playwright)", "results": []}
    SHOTS.mkdir(parents=True, exist_ok=True)

    def record(button, ok, seconds, **detail):
        report["results"].append({"button": button, "passed": ok, "seconds": round(seconds, 2), **detail})
        print("%-22s %s  %.2f s  %s" % (button, "OK   " if ok else "FALLA", seconds, detail.get("origin", detail.get("error", ""))))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("dialog", lambda d: d.accept())

        # 1. Crear borrador → guardar como sesión de prueba
        try:
            page.goto(base + "/#/aula")
            page.get_by_role("button", name="Crear borrador").wait_for()
            t = time.perf_counter()
            page.get_by_role("button", name="Crear borrador").click()
            page.get_by_role("heading", name="Revisar el borrador").wait_for(timeout=40000)
            seconds = time.perf_counter() - t
            origin = page.locator(".alert").filter(has_text="Origen del borrador").inner_text()
            ok = "Amazon Bedrock" in origin and "Respaldo local" not in origin
            page.screenshot(path=str(SHOTS / "genai-crear-borrador.png"))
            record("Crear borrador", ok, seconds, origin=origin.replace("\n", " ")[:160])
            page.get_by_label("Título de la sesión").fill("Prueba de verificación (GenAI)")
            page.get_by_role("button", name="Guardar borrador").click()
            page.locator(".saved-notice").wait_for(timeout=20000)
            session_id = page.url.rsplit("/", 1)[-1]
        except Exception as exc:  # noqa: BLE001
            record("Crear borrador", False, 0, error=str(exc)[:200])
            session_id = None

        # 2. Regenerar borrador (crea la versión 2 de la sesión de prueba)
        if session_id:
            try:
                t = time.perf_counter()
                page.get_by_role("button", name="Regenerar borrador").click()
                page.locator(".saved-notice").get_by_text("Nueva versión regenerada").wait_for(timeout=40000)
                seconds = time.perf_counter() - t
                session = api_get(base, "/api/sessions/" + session_id)
                current = session["currentVersion"]
                origin = current["generatedBy"]
                ok = origin.get("engine") == "bedrock" and origin.get("isBedrock") is True and current["number"] == 2
                badges = page.locator("main .badge").all_inner_texts()
                page.screenshot(path=str(SHOTS / "genai-regenerar.png"))
                record("Regenerar borrador", ok and "Amazon Bedrock" in badges, seconds, origin=origin.get("label"),
                       version=current["number"], badges=badges)
            except Exception as exc:  # noqa: BLE001
                record("Regenerar borrador", False, 0, error=str(exc)[:200])

        # 3. Adaptar en Mi aula (desde una experiencia de Mi red); se descarta al final
        try:
            page.goto(base + "/#/red/exp-sim-balanza-ecuaciones")
            page.get_by_role("button", name="Adaptar en Mi aula").wait_for()
            page.locator("#a-duration").fill("40")
            t = time.perf_counter()
            page.get_by_role("button", name="Adaptar en Mi aula").click()
            page.get_by_role("heading", name="Revisar el borrador").wait_for(timeout=40000)
            seconds = time.perf_counter() - t
            origin = page.locator(".alert").filter(has_text="Origen del borrador").inner_text()
            provenance = page.locator(".alert").filter(has_text="Adaptación de").inner_text()
            total = sum(int(page.input_value("#act-min-%d" % i)) for i in range(page.locator("input[id^='act-min-']").count()))
            ok = "Amazon Bedrock" in origin and "La balanza de las ecuaciones" in provenance and total == 40
            page.screenshot(path=str(SHOTS / "genai-adaptar.png"))
            record("Adaptar en Mi aula", ok, seconds, origin=origin.replace("\n", " ")[:160], totalMinutes=total,
                   provenance=provenance.replace("\n", " ")[:120])
            page.get_by_role("button", name="Descartar").click()
            page.get_by_role("heading", name="Tu próxima clase empieza aquí").wait_for(timeout=10000)
        except Exception as exc:  # noqa: BLE001
            record("Adaptar en Mi aula", False, 0, error=str(exc)[:200])

        # 4. Resumir acuerdos
        try:
            page.goto(base + "/#/red/exp-sim-geometria-pasos")
            page.get_by_role("button", name="Resumir acuerdos").wait_for()
            t = time.perf_counter()
            page.get_by_role("button", name="Resumir acuerdos").click()
            page.locator(".pre").wait_for(timeout=40000)
            seconds = time.perf_counter() - t
            text = page.locator(".pre").inner_text()
            label = page.locator(".pre + p").inner_text()
            ok = "Amazon Bedrock" in label and "Respaldo" not in label and len(text) > 40
            page.locator(".pre").scroll_into_view_if_needed()
            page.screenshot(path=str(SHOTS / "genai-resumir.png"))
            record("Resumir acuerdos", ok, seconds, origin=label, summaryChars=len(text), summaryStart=text[:160])
        except Exception as exc:  # noqa: BLE001
            record("Resumir acuerdos", False, 0, error=str(exc)[:200])

        report["consoleErrors"] = errors
        browser.close()

    report["allPassed"] = all(r["passed"] for r in report["results"]) and not report["consoleErrors"]
    target = ROOT / args.report
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("errores de consola:", report["consoleErrors"])
    print("Informe:", args.report)
    return 0 if report["allPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
