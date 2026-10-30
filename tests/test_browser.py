"""Pruebas de comportamiento en un navegador real (Chromium de Playwright) contra el servidor local.

Se omiten si Playwright o su Chromium no están instalados:
    python3 -m pip install --user playwright && python3 -m playwright install chromium
Guardan capturas en docs/capturas/.
"""
import json
import threading
import unittest
from pathlib import Path

import support
from support import TempDb, make_service, make_settings

from aulalista.server import create_server

try:
    from playwright.sync_api import sync_playwright
    _pw = sync_playwright().start()
    try:
        _probe = _pw.chromium.launch()
        _probe.close()
        BROWSER_OK = True
    except Exception:  # noqa: BLE001
        BROWSER_OK = False
    _pw.stop()
except Exception:  # noqa: BLE001
    BROWSER_OK = False

SHOTS = Path(__file__).resolve().parents[1] / "docs" / "capturas"


@unittest.skipUnless(BROWSER_OK, "Playwright/Chromium no disponible")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = TempDb().__enter__()
        cls.service = make_service(cls.db.path)
        cls.httpd = create_server(make_settings(cls.db.path, port=0), cls.service)
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        SHOTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.service.close()
        cls.db.__exit__(None, None, None)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.console_errors, self.bad_responses, self.external, self.posts = [], [], [], []
        self.page.on("console", lambda m: m.type == "error" and self.console_errors.append(m.text))
        self.page.on("pageerror", lambda e: self.console_errors.append(str(e)))
        self.page.on("response", lambda r: r.status == 404 and self.bad_responses.append(r.url))
        self.page.on("request", self._track)

    def _track(self, request):
        if not request.url.startswith(self.base):
            self.external.append(request.url)
        if request.method == "POST":
            self.posts.append(request.url.replace(self.base, ""))

    def tearDown(self):
        self.context.close()

    def assertCleanConsole(self):
        self.assertEqual(self.console_errors, [], self.console_errors)
        self.assertEqual(self.bad_responses, [])
        self.assertEqual(self.external, [])

    def h1(self):
        return self.page.locator("main h1").first.inner_text()

    # ---------------------------------------------------------------------------------
    def test_recorrido_de_aceptacion_dentro_de_16_acciones(self):
        p, actions = self.page, []
        p.goto(self.base)                                                      # (carga, no cuenta)
        p.get_by_role("link", name="Preparar clase").first.click(); actions.append("Preparar clase")
        p.get_by_label("Grado").wait_for()
        self.assertEqual(p.get_by_label("Grado").input_value(), "Cuarto de primaria")
        self.assertEqual(p.get_by_label("Duración en minutos").input_value(), "45")
        p.get_by_role("button", name="Crear borrador").click(); actions.append("Crear borrador")
        p.get_by_role("heading", name="Revisar el borrador").wait_for()
        self.assertEqual(p.title(), "Revisar el borrador · Docente Presente")
        p.get_by_text("Ver referencias").first.click(); actions.append("Ver referencias")
        self.assertIn("Escuchar a otra persona", p.locator("details[open] .source").first.inner_text())
        p.get_by_label("Título de la sesión").fill("Escucha activa: mi versión"); actions.append("Editar título")
        p.get_by_role("button", name="Guardar versión revisada").click(); actions.append("Guardar versión revisada")
        p.locator(".saved-notice").get_by_text("Versión revisada guardada").wait_for()
        self.assertEqual(self.h1(), "Escucha activa: mi versión")
        p.screenshot(path=str(SHOTS / "escritorio-sesion-guardada.png"), full_page=True)
        p.get_by_role("link", name="Volver a Mi portafolio").first.click(); actions.append("Volver a Mi portafolio")
        p.get_by_role("link", name="Escucha activa: mi versión").click(); actions.append("Abrir sesión")
        p.reload(); actions.append("Recargar")
        p.get_by_role("heading", name="Escucha activa: mi versión").wait_for()
        p.get_by_role("button", name="Usar ejemplo simulado").click(); actions.append("Usar ejemplo simulado")
        p.get_by_role("button", name="Guardar registro").click(); actions.append("Guardar registro")
        p.locator(".saved-notice").get_by_text("Registro simulado guardado para la versión 1").wait_for()
        self.assertIn("Registro simulado", p.locator("#records-title").locator("..").inner_text())
        self.assertLessEqual(len(actions), 16, actions)
        print("\n[recorrido] %d acciones: %s" % (len(actions), " → ".join(actions)))
        self.assertEqual(self.posts.count("/api/sessions"), 1)
        self.assertCleanConsole()

    def test_overview_caido_mantiene_portada_y_reintentar_recupera(self):
        p = self.page
        p.route("**/api/overview", lambda route: route.fulfill(status=500, content_type="application/json",
                                                              body=json.dumps({"error": {"code": "x", "message": "Servicio no disponible."}})))
        p.goto(self.base)
        p.get_by_text("Servicio no disponible.").wait_for()
        self.assertTrue(p.get_by_role("link", name="Preparar clase").first.is_visible())
        self.assertEqual(p.get_by_text("Tu portafolio empieza con una clase").count(), 0)  # sin falso vacío
        p.unroute("**/api/overview")
        p.get_by_role("button", name="Reintentar").click()
        p.locator("#recent-title").wait_for()
        p.wait_for_function("() => !document.body.innerText.includes('Servicio no disponible.')")
        self.console_errors = [e for e in self.console_errors if "500" not in e]
        self.assertCleanConsole()

    def test_validacion_de_campos_sin_enviar(self):
        p = self.page
        p.goto(self.base + "/#/aula")
        p.get_by_label("Grado").wait_for()
        for value in ("", "45.5", "9", "181"):
            p.get_by_label("Duración en minutos").fill(value)
            p.get_by_role("button", name="Crear borrador").click()
            self.assertEqual(p.get_by_label("Duración en minutos").get_attribute("aria-invalid"), "true", value)
            self.assertTrue(p.locator("#f-duration-error").is_visible())
        p.get_by_label("Duración en minutos").fill("45")
        p.get_by_label("Grado").fill("    ")
        p.get_by_role("button", name="Crear borrador").click()
        self.assertEqual(p.get_by_label("Grado").get_attribute("aria-invalid"), "true")
        self.assertEqual(p.evaluate("document.activeElement.id"), "f-grade")
        self.assertNotIn("/api/drafts/generate", self.posts)

    def test_doble_clic_en_crear_borrador_envia_una_sola_peticion(self):
        p = self.page
        p.goto(self.base + "/#/aula")
        p.get_by_role("button", name="Crear borrador").dblclick()
        p.get_by_role("heading", name="Revisar el borrador").wait_for()
        self.assertEqual(self.posts.count("/api/drafts/generate"), 1)

    def test_error_de_generacion_conserva_datos_y_reintentar_valida(self):
        p = self.page
        p.route("**/api/drafts/generate", lambda route: route.fulfill(status=502, content_type="application/json",
                                                                     body=json.dumps({"error": {"code": "generation_failed", "message": "No pudimos crear el borrador."}})))
        p.goto(self.base + "/#/aula")
        p.get_by_label("Grado").fill("Quinto de primaria")
        p.get_by_role("button", name="Crear borrador").click()
        p.get_by_text("No pudimos crear el borrador.").wait_for()
        self.assertEqual(p.get_by_label("Grado").input_value(), "Quinto de primaria")
        p.get_by_label("Duración en minutos").fill("5")
        p.get_by_role("button", name="Reintentar").click()  # pasa por la validación del formulario
        self.assertEqual(p.get_by_label("Duración en minutos").get_attribute("aria-invalid"), "true")
        self.assertEqual(self.posts.count("/api/drafts/generate"), 1)

    def _draft(self):
        p = self.page
        p.goto(self.base + "/#/aula")
        p.get_by_role("button", name="Crear borrador").click()
        p.get_by_role("heading", name="Revisar el borrador").wait_for()

    def test_guardado_sin_confirmacion_no_pierde_el_borrador(self):
        self._draft()
        p = self.page
        p.get_by_label("Título de la sesión").fill("Borrador que no debe perderse")
        p.route("**/api/sessions", lambda route: route.abort())
        p.get_by_role("button", name="Guardar versión revisada").click()
        p.get_by_text("No recibimos la confirmación").wait_for()
        self.assertEqual(p.get_by_label("Título de la sesión").input_value(), "Borrador que no debe perderse")
        self.assertFalse(p.get_by_role("button", name="Guardar versión revisada").is_disabled())
        self.assertEqual(p.get_by_role("button", name="Reintentar").count(), 0)  # sin reintento ciego
        p.reload()
        p.get_by_role("heading", name="Revisar el borrador").wait_for()
        self.assertEqual(p.get_by_label("Título de la sesión").input_value(), "Borrador que no debe perderse")
        self.console_errors = []
        self.bad_responses = []

    def test_confirmacion_perdida_y_reintento_no_duplica(self):
        self._draft()
        p = self.page
        p.get_by_label("Título de la sesión").fill("Una sola sesión")
        before = len(support.Api(self.service)("GET", "/api/sessions")[1])

        def processed_but_lost(route):
            route.fetch()   # el servidor sí guarda…
            route.abort()   # …pero la respuesta no llega al navegador
        p.route("**/api/sessions", processed_but_lost)
        p.get_by_role("button", name="Guardar versión revisada").click()
        p.get_by_text("No recibimos la confirmación").wait_for()
        p.unroute("**/api/sessions")
        p.get_by_role("button", name="Guardar versión revisada").click()  # mismo contenido → misma clave
        p.locator(".saved-notice").get_by_text("Versión revisada guardada").wait_for()
        titles = [s["title"] for s in support.Api(self.service)("GET", "/api/sessions")[1]]
        self.assertEqual(len(titles), before + 1)
        self.assertEqual(titles.count("Una sola sesión"), 1)
        self.console_errors = []

    def test_conflicto_de_version_conserva_la_edicion(self):
        session = support.generate_and_save(support.Api(self.service), reviewed=True)
        p = self.page
        p.goto(self.base + "/#/portafolio/" + session["id"])
        p.get_by_role("button", name="Continuar edición").click()
        p.get_by_label("Título de la sesión").fill("Mi edición en conflicto")
        # Otra pestaña guarda antes una versión nueva de la misma sesión.
        support.Api(self.service)("POST", "/api/sessions/%s/versions" % session["id"],
                                  {"content": dict(session["currentVersion"]["content"], title="Edición de otra pestaña")})
        p.get_by_role("button", name="Guardar borrador").click()
        p.get_by_text("Mientras editabas se guardó otra versión").wait_for()
        self.assertEqual(p.get_by_label("Título de la sesión").input_value(), "Mi edición en conflicto")
        p.get_by_role("button", name="Guardar mi edición como sesión nueva").click()
        p.get_by_role("button", name="Guardar borrador").click()
        p.locator(".saved-notice").get_by_text("Borrador guardado").wait_for()
        self.assertIn("Mi edición en conflicto", self.h1())
        versions = support.Api(self.service)("GET", "/api/sessions/%s" % session["id"])[1]["versions"]
        self.assertEqual([v["number"] for v in versions], [1, 2])
        self.console_errors = []

    def test_almacenamiento_bloqueado_el_flujo_sigue_en_memoria(self):
        ctx = self.browser.new_context()
        ctx.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('bloqueado'); } });")
        p = ctx.new_page()
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(self.base + "/#/aula")
        p.get_by_role("button", name="Crear borrador").click()
        p.get_by_role("heading", name="Revisar el borrador").wait_for()
        p.get_by_text("este navegador no permite copias locales").wait_for()
        p.get_by_role("button", name="Guardar borrador").click()
        p.locator(".saved-notice").get_by_text("Borrador guardado").wait_for()
        self.assertEqual(errors, [])
        ctx.close()

    def test_error_422_muestra_los_problemas(self):
        self._draft()
        p = self.page
        p.route("**/api/sessions", lambda route: route.fulfill(status=422, content_type="application/json", body=json.dumps(
            {"error": {"code": "invalid_lesson", "message": "La sesión no es válida.", "details": ["Actividad 1: falta el título."]}})))
        p.get_by_role("button", name="Guardar borrador").click()
        p.get_by_text("Actividad 1: falta el título.").wait_for()
        self.assertEqual(p.get_by_text("{").count(), 0)

    def test_minutos_que_no_suman_bloquean_guardar(self):
        self._draft()
        p = self.page
        p.get_by_label("Minutos").first.fill("99")
        self.assertTrue(p.get_by_role("button", name="Guardar versión revisada").is_disabled())
        self.assertIn("Los tiempos suman", p.locator(".sum-bad").inner_text())

    def test_navegar_durante_la_generacion_no_redirige(self):
        p = self.page
        p.route("**/api/drafts/generate", lambda route: (p.wait_for_timeout(800), route.continue_()))
        p.goto(self.base + "/#/aula")
        p.get_by_role("button", name="Crear borrador").click()
        p.get_by_role("link", name="Mi aprendizaje").click()
        p.wait_for_timeout(1500)
        self.assertEqual(self.h1(), "Mi aprendizaje")
        p.get_by_role("link", name="Hoy").first.click()
        p.get_by_text("Tienes cambios pendientes de guardar").wait_for()

    def test_registro_sobre_version_antigua_y_borrador_de_formulario(self):
        session = support.generate_and_save(support.Api(self.service), reviewed=True)
        content = dict(session["currentVersion"]["content"], title="Segunda versión")
        support.Api(self.service)("POST", "/api/sessions/%s/versions" % session["id"], {"content": content})
        p = self.page
        p.goto(self.base + "/#/portafolio/" + session["id"])
        p.get_by_label("Observación declarada").fill("Texto en curso que no debe borrarse")
        p.get_by_role("button", name="Ver versión 1").click()
        p.get_by_text("Estás viendo la versión 1").wait_for()
        self.assertEqual(p.get_by_label("Observación declarada").input_value(), "Texto en curso que no debe borrarse")
        p.get_by_label("Versión utilizada").select_option(label="Versión 1 · Revisada")
        p.get_by_label("Actividad realizada").fill("Parejas")
        p.get_by_label("Observación declarada").fill("Observación simulada para la versión 1")
        p.get_by_role("button", name="Guardar registro").click()
        p.locator(".saved-notice").get_by_text("Registro simulado guardado para la versión 1").wait_for()
        records = support.Api(self.service)("GET", "/api/sessions/%s" % session["id"])[1]["records"]
        self.assertEqual(records[-1]["versionId"], session["currentVersion"]["id"])

    def test_localstorage_corrupto_y_ruta_inexistente(self):
        p = self.page
        p.goto(self.base)
        p.evaluate("localStorage.setItem('aulalista.working', '{\"content\": 5}')")
        p.reload()
        p.get_by_text("copia local dañada").wait_for()
        p.goto(self.base + "/#/no-existe")
        p.get_by_role("heading", name="No encontramos esa página").wait_for()
        p.get_by_role("link", name="Volver a Hoy").click()
        p.get_by_role("heading", name="Tu próxima clase empieza aquí").wait_for()
        self.assertCleanConsole()

    def test_movil_320_sin_desplazamiento_horizontal_y_capturas(self):
        api = support.Api(self.service)
        long_case = dict(support.CASE, materials=["pizarra", "papel", "lápiz", "Cartulinadecoloresrecortadaenformas" * 1])
        _, draft = api("POST", "/api/drafts/generate", long_case)
        content = dict(draft["content"], title="Sesiónconuntítulomuylargoysinespaciosparacomprobarelajuste" * 3)
        self.long_session = api("POST", "/api/sessions", {"moduleId": draft["module"]["id"], "context": draft["context"],
                                                          "content": content, "draftId": draft["draftId"]})[1]["id"]
        # 640 px equivale a 1280 px con zoom del 200 %.
        for width, name in ((320, "movil-320"), (390, "movil-390"), (640, "zoom200-1280"), (768, "tablet-768"), (1440, "escritorio-1440")):
            ctx = self.browser.new_context(viewport={"width": width, "height": 800})
            page = ctx.new_page()
            for route in ("/#/hoy", "/#/aula", "/#/portafolio", "/#/red", "/#/aprendizaje", "/#/bienestar", "/#/oportunidades"):
                page.goto(self.base + route)
                page.locator("main h1").first.wait_for()
                page.wait_for_timeout(250)
                overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                self.assertLessEqual(overflow, 0, "%s %s" % (width, route))
            page.goto(self.base + "/#/portafolio/" + self.long_session)
            page.locator("main h1").first.wait_for()
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            self.assertLessEqual(overflow, 0, "%s título y materiales largos" % width)
            page.goto(self.base + "/#/hoy")
            page.get_by_text("Tus sesiones recientes").wait_for()
            page.screenshot(path=str(SHOTS / ("hoy-%s.png" % name)), full_page=True)
            page.goto(self.base + "/#/aula")
            page.get_by_label("Grado").wait_for()
            page.screenshot(path=str(SHOTS / ("preparar-%s.png" % name)), full_page=True)
            ctx.close()

    def test_teclado_skip_link_y_foco_en_encabezado(self):
        p = self.page
        p.goto(self.base)
        p.keyboard.press("Tab")
        self.assertEqual(p.evaluate("document.activeElement.textContent"), "Saltar al contenido")
        p.get_by_role("link", name="Preparar clase").first.click()
        p.get_by_label("Grado").wait_for()
        self.assertEqual(p.evaluate("document.activeElement.tagName"), "H1")  # cambio de ruta → foco en el h1
        self.assertEqual(p.title(), "Preparar clase · Docente Presente")
        self.assertEqual(p.evaluate("document.querySelectorAll('main h1').length"), 1)
        self.assertEqual(p.evaluate("[...document.querySelectorAll('[tabindex]')].filter(e => e.tabIndex > 0).length"), 0)


if __name__ == "__main__":
    unittest.main()
