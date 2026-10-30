"""Comprobaciones estáticas del front: estructura, paleta, accesibilidad básica y seguridad (sin navegador)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import support
from support import BACK, FRONT, ROOT

INDEX = (FRONT / "index.html").read_text(encoding="utf-8")
CSS = (FRONT / "css" / "styles.css").read_text(encoding="utf-8")
JS_FILES = sorted((FRONT / "js").rglob("*.js"))
ALL_JS = {path: path.read_text(encoding="utf-8") for path in JS_FILES}
ALL_JS_TEXT = "\n".join(ALL_JS.values())

SECTIONS = ["hoy", "aprendizaje", "aula", "portafolio", "red", "oportunidades", "bienestar"]


def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def css_vars():
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", CSS))


class StructureTests(unittest.TestCase):
    def test_back_y_front_estan_separados(self):
        self.assertTrue(BACK.is_dir() and FRONT.is_dir())
        self.assertEqual([p for p in BACK.rglob("*") if p.suffix in (".html", ".css", ".js")], [])
        self.assertEqual([p for p in FRONT.rglob("*") if p.suffix == ".py"], [])

    def test_el_back_solo_usa_biblioteca_estandar(self):
        stdlib_ok = {"__future__", "json", "re", "os", "sys", "uuid", "copy", "threading", "sqlite3", "typing",
                     "dataclasses", "datetime", "decimal", "fractions", "pathlib", "concurrent", "http",
                     "urllib", "mimetypes", "aulalista"}
        for path in (BACK / "aulalista").glob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w]*)", line)
                if match and not line.lstrip().startswith("from ."):
                    self.assertIn(match.group(1), stdlib_ok, "%s importa %s" % (path.name, match.group(1)))


class IndexHtmlTests(unittest.TestCase):
    def test_documento_basico(self):
        self.assertIn('<html lang="es">', INDEX)
        self.assertIn("<title>", INDEX)
        self.assertIn('<meta name="viewport"', INDEX)
        self.assertIn('id="app"', INDEX)
        self.assertIn('<script type="module" src="/js/app.js">', INDEX)
        self.assertIn('class="skip-link"', INDEX)
        self.assertIn('aria-live="polite"', INDEX)

    def test_navegacion_con_las_siete_secciones(self):
        for section in SECTIONS:
            self.assertIn('data-nav="%s"' % section, INDEX)
        for label in ("Hoy", "Mi aprendizaje", "Mi aula", "Mi portafolio", "Mi red", "Mis oportunidades",
                      "Mi bienestar"):
            self.assertIn(">%s</a>" % label, INDEX)

    def test_cada_seccion_tiene_ruta_en_app_js(self):
        app = ALL_JS[FRONT / "js" / "app.js"]
        for section in SECTIONS:
            self.assertIn("nav: '%s'" % section, app)

    def test_sin_scripts_ni_estilos_en_linea(self):
        self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)[^>]*>", INDEX))
        self.assertIsNone(re.search(r"\sstyle\s*=", INDEX))
        self.assertIsNone(re.search(r"\son\w+\s*=", INDEX))

    def test_aviso_de_datos_simulados_visible(self):
        self.assertIn("datos simulados", INDEX.lower())


class PaletteTests(unittest.TestCase):
    def test_paleta_halloween_naranja_y_negro(self):
        colors = css_vars()
        self.assertEqual(colors["negro"].lower(), "#0b0a0d")
        self.assertEqual(colors["naranja"].lower(), "#ff7a1a")
        self.assertEqual(colors["hueso"].lower(), "#f7efe3")
        self.assertRegex(CSS, r"background:[^;]*var\(--negro\)")
        self.assertRegex(CSS, r"border-bottom:\s*3px solid var\(--naranja\)")

    def test_contraste_minimo_aa(self):
        c = css_vars()
        pairs = [
            ("hueso", "negro"), ("naranja", "negro"), ("negro", "naranja"), ("gris", "panel"),
            ("naranja-claro", "panel"), ("hueso", "panel"), ("hueso", "naranja-oscuro"),
            ("verde", "panel"), ("rojo", "panel"), ("morado", "panel"), ("amarillo", "panel"),
            ("naranja-claro", "carbon"),
        ]
        for fg, bg in pairs:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast(c[fg], c[bg]), 4.5, "%s sobre %s" % (fg, bg))

    def test_accesibilidad_y_responsive_en_css(self):
        self.assertIn(":focus-visible", CSS)
        self.assertIn("prefers-reduced-motion", CSS)
        self.assertIn("@media print", CSS)
        self.assertIn("min-height: 44px", CSS)
        self.assertNotRegex(CSS, r"outline:\s*none;\s*}\s*$")


class JavascriptTests(unittest.TestCase):
    def test_nunca_se_inserta_html_dinamico(self):
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(banned, ALL_JS_TEXT, banned)

    def test_sin_estilos_en_linea_que_bloquee_la_csp(self):
        self.assertIsNone(re.search(r"\bstyle\s*:", ALL_JS_TEXT))
        self.assertNotIn("setAttribute('style'", ALL_JS_TEXT)

    def test_los_imports_relativos_existen(self):
        for path, text in ALL_JS.items():
            for target in re.findall(r"from\s+'(\.[^']+)'", text):
                self.assertTrue((path.parent / target).resolve().is_file(), "%s -> %s" % (path.name, target))

    def test_las_rutas_de_la_api_usadas_existen_en_el_back(self):
        api = (BACK / "aulalista" / "api.py").read_text(encoding="utf-8")
        route_patterns = re.findall(r'@route\("(\w+)", "([^"]+)"\)', api)
        regexes = [re.compile("^" + re.sub(r"\{\w+\}", r"[^/]+", p) + "$") for _, p in route_patterns]
        used = set(re.findall(r"['`](/api/[^'`?]*)['`]", ALL_JS_TEXT))
        self.assertTrue(used)
        for url in used:
            concrete = re.sub(r"\$\{[^}]+\}", "x", url)
            self.assertTrue(any(r.match(concrete) for r in regexes), "El front llama a %s, que no existe" % url)

    def test_etiquetas_clave_del_recorrido(self):
        for label in ("Preparar clase", "Mi portafolio", "Crear borrador", "Guardar borrador",
                      "Guardar versión revisada", "Usar en mi clase", "Continuar edición", "Registro simulado",
                      "Guardar registro", "Adaptar en Mi aula", "Resumir acuerdos", "Compartir copia",
                      "No puedo valorarlo", "Función futura", "Descartar", "Reintentar", "Imprimir"):
            self.assertIn(label, ALL_JS_TEXT, label)

    def test_la_salida_local_se_rotula_y_no_se_presenta_como_bedrock(self):
        self.assertIn("Origen del borrador", ALL_JS_TEXT)
        generator = (BACK / "aulalista" / "generator.py").read_text(encoding="utf-8")
        self.assertIn("No es Amazon Bedrock", generator)

    def test_estados_de_espera_y_error(self):
        for text in ("Creando borrador…", "Guardando…", "role: 'alert'", "Tu edición sigue aquí",
                     "No hay conexión con el servidor"):
            self.assertIn(text, ALL_JS_TEXT, text)

    @unittest.skipUnless(shutil.which("node"), "node no está instalado")
    def test_sintaxis_de_los_modulos(self):
        for path in JS_FILES:
            with self.subTest(file=path.name):
                result = subprocess.run(["node", "--input-type=module", "--check"], input=path.read_text(encoding="utf-8"),
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)


class FrontendNotesTests(unittest.TestCase):
    """Los textos para el registro del frontend deben respetar los límites y describir lo que existe."""

    notes = (ROOT / "docs" / "NOTAS-FRONTEND.md").read_text(encoding="utf-8")

    def line(self, prefix):
        match = re.search(r"^%s\s*(.+)$" % re.escape(prefix), self.notes, re.M)
        self.assertIsNotNone(match, prefix)
        return match.group(1).strip()

    def test_limites_de_longitud_y_contenido(self):
        for prefix in ("NOTA:", "GENAI-FASE2:"):
            text = self.line(prefix)
            with self.subTest(prefix=prefix):
                self.assertLessEqual(len(text), 240, len(text))
                self.assertNotIn("@", text)
                self.assertIsNone(re.search(r"\d{7,}", text))

    def test_la_nota_tiene_entre_1_y_3_pasos_con_etiquetas_reales(self):
        note = self.line("NOTA:")
        steps = re.findall(r"\d\)", note)
        self.assertTrue(1 <= len(steps) <= 3)
        for label in ("Preparar clase", "Crear borrador", "Guardar versión revisada", "Mi portafolio"):
            self.assertIn(label, note)
            self.assertIn(label, ALL_JS_TEXT)

    def test_el_texto_genai_esta_marcado_como_pendiente_de_la_fase_2(self):
        self.assertIn("No usar este texto hasta la fase 2", self.notes)


if __name__ == "__main__":
    unittest.main()
