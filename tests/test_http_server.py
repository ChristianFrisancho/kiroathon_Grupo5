"""Servidor real: front y API en el mismo origen, cabeceras, errores y recorrido completo por HTTP."""
import http.client
import json
import threading
import time
import unittest

import support
from support import CASE, TempDb, make_service, make_settings, rating_payload

from aulalista.server import create_server

SEED_ID = "exp-sim-escucha-v1"


class LiveServer:
    def __init__(self, db_path=":memory:"):
        self.service = make_service(db_path)
        self.httpd = create_server(make_settings(db_path, port=0), self.service)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def request(self, method, path, body=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
            hdrs = dict(headers or {})
            if data is not None:
                hdrs.setdefault("Content-Type", "application/json")
            conn.request(method, path, body=data, headers=hdrs)
            response = conn.getresponse()
            payload = response.read()
            return response.status, dict(response.getheaders()), payload
        finally:
            conn.close()

    def json(self, method, path, body=None, user=None, **kw):
        headers = {"X-User-Id": user} if user else {}
        status, hdrs, payload = self.request(method, path, body, headers, **kw)
        return status, (json.loads(payload) if payload else None)

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.service.close()


class FrontServingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LiveServer()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_raiz_responde_200_html_sin_redireccion(self):
        status, headers, body = self.server.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertIn(b"Docente Presente", body)
        self.assertNotIn("Location", headers)

    def test_assets_con_tipo_correcto(self):
        for path, expected in (("/css/styles.css", "text/css"), ("/js/app.js", "javascript"),
                               ("/js/views/red.js", "javascript")):
            status, headers, _ = self.server.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn(expected, headers["Content-Type"], path)

    def test_no_se_sirve_nada_fuera_de_front(self):
        for path in ("/../back/run.py", "/%2e%2e/back/run.py", "/..%2fback%2frun.py", "/js/../../README.md",
                     "/no-existe.js", "/back/run.py"):
            status, _, body = self.server.request("GET", path)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"def main", body)

    def test_cabeceras_de_seguridad(self):
        _, headers, _ = self.server.request("GET", "/")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", headers["Content-Security-Policy"])

    def test_health_por_http(self):
        status, headers, body = self.server.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(json.loads(body), {"status": "ok", "team": "T005"})


class HttpErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LiveServer()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_json_invalido(self):
        status, body = self.server.json("POST", "/api/drafts/generate", raw=b"{no es json")
        self.assertEqual((status, body["error"]["code"]), (400, "invalid_json"))

    def test_cuerpo_que_no_es_objeto(self):
        status, body = self.server.json("POST", "/api/drafts/generate", raw=b"[1,2,3]")
        self.assertEqual((status, body["error"]["code"]), (400, "invalid_json"))

    def test_cuerpo_demasiado_grande(self):
        big = json.dumps({"notes": "x" * 300_000}).encode()
        status, body = self.server.json("POST", "/api/drafts/generate", raw=big)
        self.assertEqual(status, 413)

    def test_ruta_y_metodo(self):
        self.assertEqual(self.server.json("GET", "/api/no-existe")[0], 404)
        status, body = self.server.json("DELETE", "/api/sessions")
        self.assertEqual((status, body["error"]["code"]), (405, "method_not_allowed"))
        self.assertEqual(self.server.json("POST", "/health")[0], 405)

    def test_usuario_de_demo_invalido(self):
        status, _ = self.server.json("GET", "/api/sessions", user="../etc/passwd")
        self.assertEqual(status, 400)

    def test_un_fallo_interno_no_filtra_detalles(self):
        original = self.server.service.overview
        self.server.service.overview = lambda user: (_ for _ in ()).throw(RuntimeError("clave-secreta /etc/passwd"))
        try:
            status, body = self.server.json("GET", "/api/overview")
        finally:
            self.server.service.overview = original
        self.assertEqual(status, 500)
        self.assertNotIn("clave-secreta", json.dumps(body))
        self.assertNotIn("Traceback", json.dumps(body))

    def test_html_en_los_textos_se_guarda_como_texto(self):
        payload = "<img src=x onerror=alert(1)>"
        status, draft = self.server.json("POST", "/api/drafts/generate", {**CASE, "notes": payload})
        self.assertEqual(status, 200)
        # El servidor devuelve JSON (nunca HTML): el navegador lo inserta como texto.
        status, headers, _ = self.server.request("POST", "/api/drafts/generate", {**CASE, "notes": payload})
        self.assertIn("application/json", headers["Content-Type"])


class FullJourneyOverHttpTests(unittest.TestCase):
    """Recorrido completo del docente y de la comunidad contra el servidor real."""

    def test_recorrido_completo_con_reinicio_del_servidor(self):
        with TempDb() as db:
            server = LiveServer(db.path)
            try:
                status, draft = server.json("POST", "/api/drafts/generate", CASE)
                self.assertEqual(status, 200)
                content = draft["content"]
                content["title"] = "Mi versión de escucha activa"
                status, session = server.json("POST", "/api/sessions", {
                    "moduleId": draft["module"]["id"], "context": draft["context"], "content": content,
                    "markReviewed": True, "generatedBy": draft["generatedBy"]})
                self.assertEqual(status, 201)
                sid = session["id"]
                status, record = server.json("POST", "/api/sessions/%s/records" % sid, {
                    "declaredDate": "2026-10-30", "activity": "Parejas", "observation": "Participaron"})
                self.assertEqual(status, 201)
                status, exp = server.json("POST", "/api/sessions/%s/share" % sid, {
                    "confirm": True, "purpose": "Escucha", "description": "Parejas", "improvement": "Tres pasos"})
                self.assertEqual(status, 201)
                status, _ = server.json("POST", "/api/experiences/%s/ratings" % SEED_ID,
                                        rating_payload([4, 4, 4, 4]), user="u-colega")
                self.assertEqual(status, 201)
                status, _ = server.json("POST", "/api/experiences/%s/ratings" % SEED_ID,
                                        rating_payload([5, 5, 5, 5]), user="u-colega")
                self.assertEqual(status, 200)
                status, item = server.json("POST", "/items", {"value": "nonce-persistente"})
                self.assertIn(status, (200, 201))
            finally:
                server.stop()

            # «Recargar»: un servidor nuevo sobre la misma base recupera todo.
            server = LiveServer(db.path)
            try:
                status, listing = server.json("GET", "/api/sessions")
                self.assertEqual([s["id"] for s in listing], [sid])
                status, detail = server.json("GET", "/api/sessions/%s" % sid)
                self.assertEqual(detail["currentVersion"]["content"]["title"], "Mi versión de escucha activa")
                self.assertEqual(detail["currentVersion"]["reviewStatus"], "revisada")
                self.assertEqual(len(detail["records"]), 1)
                self.assertTrue(detail["records"][0]["isSimulated"])
                status, mine = server.json("GET", "/api/experiences/%s" % exp["id"])
                self.assertEqual(mine["observation"], "")
                self.assertEqual(mine["improvement"], "Tres pasos")
                status, seed = server.json("GET", "/api/experiences/%s" % SEED_ID)
                self.assertEqual(seed["ratingSummary"]["completeCount"], 4)  # 3 simuladas + 1 de u-colega
                self.assertEqual(len(seed["ratings"]), 4)
                status, got = server.json("GET", "/items/%s" % item["id"])
                self.assertEqual(got["value"], "nonce-persistente")
                self.assertIn("nonce-persistente", [i["value"] for i in server.json("GET", "/items")[1]])
            finally:
                server.stop()

    def test_job_por_http_dentro_de_12_segundos(self):
        server = LiveServer()
        try:
            nonce = "k9Zq-77"
            status, job = server.json("POST", "/jobs", {"input": nonce})
            self.assertEqual(status, 202)
            self.assertIn("jobId", job)
            deadline = time.time() + 12
            while time.time() < deadline:
                status, result = server.json("GET", "/jobs/%s" % job["jobId"])
                if result["status"] == "done":
                    break
                time.sleep(0.05)
            self.assertEqual(result["status"], "done")
            self.assertEqual(result["output"], nonce[::-1])
        finally:
            server.stop()

    def test_peticiones_concurrentes_no_corrompen_las_valoraciones(self):
        server = LiveServer()
        try:
            results = []

            def work(index):
                user = "u-par-%d" % (index % 5)  # 5 personas, 4 intentos cada una
                results.append(server.json("POST", "/api/experiences/%s/ratings" % SEED_ID,
                                           rating_payload([4, 4, 4, 4]), user=user)[0])

            threads = [threading.Thread(target=work, args=(i,)) for i in range(20)]
            [t.start() for t in threads]
            [t.join() for t in threads]
            self.assertTrue(all(code in (200, 201) for code in results), results)
            status, seed = server.json("GET", "/api/experiences/%s" % SEED_ID)
            self.assertEqual(seed["ratingSummary"]["completeCount"], 3 + 5)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
