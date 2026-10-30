"""Lambda (back/app.py) con DynamoDB falsa (monkeypatch de la tabla) y cliente de Bedrock simulado.

Cubre los contratos de las insignias (API viva, Persistencia, Asíncrono) y la GenAI del flujo central.
"""
import base64
import json
import re
import sys
import time
import unittest
from pathlib import Path

import support  # noqa: F401  (añade back/ a sys.path)

import app
import worker
from aulalista import bedrock as bedrock_module
from aulalista.bedrock import BedrockGenerator, extract_json
from aulalista.dynamo_repository import DynamoRepository
from aulalista.service import Service

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------
from fakes import ClientError, FakeBedrock, FakeDynamoClient, ReadTimeoutError  # noqa: E402


def lesson_json(minutes=(10, 15, 12, 8), refs=(["M1"], ["M1", "M2"], ["M2"], ["M3"])):
    return json.dumps({
        "title": "Escuchamos y comprobamos lo que entendimos",
        "purpose": "Practicar la escucha activa y el parafraseo en parejas.",
        "activities": [
            {"title": "Actividad %d" % (i + 1), "minutes": m, "description": "Las parejas conversan y practican la actividad %d." % (i + 1),
             "references": list(r)}
            for i, (m, r) in enumerate(zip(minutes, refs))
        ],
        "expectedEvidence": "Cada estudiante parafrasea una idea de su pareja y pregunta si la entendió bien.",
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def event(method, path, body=None, raw=None, b64=False, query=""):
    payload = raw if raw is not None else (json.dumps(body) if body is not None else None)
    if b64 and payload is not None:
        payload = base64.b64encode(payload.encode()).decode()
    return {
        "version": "2.0",
        "rawPath": path,
        "rawQueryString": query,
        "headers": {"content-type": "application/json"},
        "requestContext": {"http": {"method": method, "path": path}},
        "body": payload,
        "isBase64Encoded": b64,
    }


class LambdaTestCase(unittest.TestCase):
    """Cada prueba arma la Lambda con una tabla falsa y Bedrock simulado (sin red ni AWS)."""

    team = "T005"

    def setUp(self):
        self.env = {"TEAM_ID": self.team, "TABLE_NAME": "tabla-falsa", "MODEL_ID": "modelo-de-prueba"}
        self._old_env = {k: app.os.environ.get(k) for k in self.env}
        app.os.environ.update(self.env)
        self.db = FakeDynamoClient()
        self.bedrock = FakeBedrock(lesson_json())
        self.sleeps = []
        self.dispatched = []
        settings = app.lambda_settings()
        generator = BedrockGenerator(model_id=settings.model_id, client=self.bedrock, sleep=self.sleeps.append)
        self.service = Service(DynamoRepository(self.db, "tabla-falsa"), generator, settings,
                               dispatcher=self.dispatched.append)
        app._service, app._settings = self.service, settings  # monkeypatch del servicio global

    def tearDown(self):
        app._service, app._settings = None, None
        for key, value in self._old_env.items():
            if value is None:
                app.os.environ.pop(key, None)
            else:
                app.os.environ[key] = value

    def call(self, method, path, body=None, **kw):
        response = app.handler(event(method, path, body, **kw), None)
        content_type = response["headers"]["Content-Type"]
        data = json.loads(response["body"]) if content_type.startswith("application/json") else response["body"]
        return response["statusCode"], data, response["headers"]

    def generate(self, **overrides):
        body = {**support.CASE, **overrides}
        return self.call("POST", "/api/drafts/generate", body)


# ---------------------------------------------------------------------------
# Insignia «API viva»
# ---------------------------------------------------------------------------
class HealthTests(LambdaTestCase):
    def test_health(self):
        status, body, headers = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "team": "T005"})
        self.assertTrue(headers["Content-Type"].startswith("application/json"))

    def test_health_usa_la_variable_team_id(self):
        app.os.environ["TEAM_ID"] = "T999"
        app._service = None  # nuevo contenedor de Lambda
        original = app.build_service
        app.build_service = lambda settings, **kw: Service(DynamoRepository(FakeDynamoClient(), "t"), BedrockGenerator(client=self.bedrock), settings, **kw)
        try:
            self.assertEqual(self.call("GET", "/health")[1]["team"], "T999")
        finally:
            app.build_service = original

    def test_template_declara_team_id_y_lo_pasa_a_la_lambda(self):
        template = (ROOT / "template.yaml").read_text(encoding="utf-8")
        self.assertRegex(template, r"TeamId:\s*\n\s*Type: String\s*\n\s*Default: T005")
        self.assertIn("TEAM_ID: !Ref TeamId", template)
        self.assertIn("TABLE_NAME: !Ref ItemsTable", template)
        self.assertIn("MODEL_ID: !Ref ModelId", template)
        self.assertIn("bedrock:InvokeModel", template)
        self.assertIn("ApiUrl:", template)
        self.assertNotIn("Auth", template)  # rutas públicas


# ---------------------------------------------------------------------------
# Insignia «Persistencia»
# ---------------------------------------------------------------------------
class ItemsTests(LambdaTestCase):
    def test_crear_leer_y_listar_un_item(self):
        nonce = "nonce-%d" % time.time_ns()
        status, created, headers = self.call("POST", "/items", {"value": nonce})
        self.assertIn(status, (200, 201))
        self.assertEqual(created["value"], nonce)
        self.assertTrue(created["id"])
        status, got, headers = self.call("GET", "/items/%s" % created["id"])
        self.assertEqual((status, got), (200, {"id": created["id"], "value": nonce}))
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        status, listing, _ = self.call("GET", "/items")
        self.assertEqual(status, 200)
        self.assertIn(nonce, [i["value"] for i in listing])
        # Quedó guardado en la tabla (ItemsTable), no en memoria.
        self.assertIn(("ITEM", created["id"]), self.db.rows)

    def test_la_lista_pagina_toda_la_tabla(self):
        ids = [self.call("POST", "/items", {"value": "v%d" % i})[1]["id"] for i in range(7)]
        before = len(self.db.calls)
        listing = self.call("GET", "/items")[1]
        self.assertEqual(set(ids), {i["id"] for i in listing})
        queries = [c for c in self.db.calls[before:] if c == ("query", "ITEMS_BY_TIME")]
        self.assertEqual(len(queries), 4)  # 7 ítems / 2 por página: pagina hasta el final

    def test_la_lista_trae_primero_los_recientes_y_maximo_100(self):
        for i in range(103):
            self.service.repo.add_item("item-%03d" % i, json.dumps("v%d" % i), "2026-10-30T10:%02d:%02d" % (i // 60, i % 60))
        nonce = self.call("POST", "/items", {"value": "el-mas-reciente"})[1]
        listing = self.call("GET", "/items")[1]
        self.assertEqual(len(listing), 100)
        self.assertEqual(listing[0]["id"], nonce["id"])

    def test_item_inexistente_y_cuerpo_invalido(self):
        self.assertEqual(self.call("GET", "/items/no-existe")[0], 404)
        self.assertEqual(self.call("POST", "/items", {})[0], 422)
        self.assertEqual(self.call("POST", "/items", raw="{roto")[0], 400)

    def test_cuerpo_en_base64(self):
        status, created, _ = self.call("POST", "/items", {"value": "b64"}, b64=True)
        self.assertIn(status, (200, 201))
        self.assertEqual(self.call("GET", "/items/%s" % created["id"])[1]["value"], "b64")


# ---------------------------------------------------------------------------
# Insignia «Asíncrono»
# ---------------------------------------------------------------------------
class JobsTests(LambdaTestCase):
    def run_worker(self, job_id):
        worker.get_repo = lambda: self.service.repo  # el worker usa la misma tabla (falsa)
        return worker.handler({"jobId": job_id}, None)

    def test_post_202_despacha_y_el_worker_termina_sin_que_nadie_consulte(self):
        nonce = "abc1"
        status, job, _ = self.call("POST", "/jobs", {"input": nonce})
        self.assertEqual(status, 202)
        self.assertEqual(self.dispatched, [job["jobId"]])
        stored = json.loads(self.db.rows[("JOB", job["jobId"])]["doc"]["S"])
        self.assertEqual(stored["status"], "queued")
        self.assertEqual(self.run_worker(job["jobId"])["status"], "done")  # sin ningún GET previo
        stored = json.loads(self.db.rows[("JOB", job["jobId"])]["doc"]["S"])
        self.assertEqual((stored["status"], stored["output"]), ("done", "1cba"))
        self.assertEqual(self.call("GET", "/jobs/%s" % job["jobId"])[1],
                         {"jobId": job["jobId"], "status": "done", "output": "1cba"})

    def test_get_solo_lee_el_estado(self):
        job = self.call("POST", "/jobs", {"input": "Día-ñ"})[1]
        for _ in range(3):
            self.assertEqual(self.call("GET", "/jobs/%s" % job["jobId"])[1]["status"], "queued")
        self.run_worker(job["jobId"])
        self.assertEqual(self.call("GET", "/jobs/%s" % job["jobId"])[1]["output"], "ñ-aíD")

    def test_worker_idempotente_ante_entregas_repetidas(self):
        job = self.call("POST", "/jobs", {"input": "xyz"})[1]
        self.run_worker(job["jobId"])
        writes = len([c for c in self.db.calls if c == ("put_item", "JOB")])
        self.assertEqual(self.run_worker(job["jobId"])["status"], "done")
        self.assertEqual(len([c for c in self.db.calls if c == ("put_item", "JOB")]), writes)
        self.assertEqual(self.run_worker("job-inexistente")["status"], "not_found")
        self.assertEqual(worker.handler({}, None)["status"], "ignored")

    def test_fallo_de_despacho_no_queda_en_queued(self):
        def broken(job_id):
            raise ClientError("ServiceException")
        self.service.dispatcher = broken
        status, body, _ = self.call("POST", "/jobs", {"input": "abc"})
        self.assertEqual((status, body["error"]["code"]), (503, "job_dispatch_failed"))
        job_id = body["error"]["details"]["jobId"]
        self.assertEqual(self.call("GET", "/jobs/%s" % job_id)[1]["status"], "failed")

    def test_job_invalido_o_inexistente(self):
        self.assertEqual(self.call("POST", "/jobs", {})[0], 422)
        self.assertEqual(self.call("GET", "/jobs/no-existe")[0], 404)


# ---------------------------------------------------------------------------
# Insignia «GenAI con propósito»: Bedrock en el flujo central
# ---------------------------------------------------------------------------
class BedrockFlowTests(LambdaTestCase):
    def test_crear_borrador_llama_a_converse_con_el_contexto_confirmado(self):
        status, draft, _ = self.generate(notes="El grupo es muy conversador")
        self.assertEqual(status, 200)
        self.assertTrue(draft["generatedBy"]["isBedrock"])
        self.assertEqual(draft["generatedBy"]["modelId"], "modelo-de-prueba")
        self.assertEqual(draft["content"]["title"], "Escuchamos y comprobamos lo que entendimos")
        self.assertEqual(sum(a["minutes"] for a in draft["content"]["activities"]), 45)
        call = self.bedrock.calls[0]
        self.assertEqual(call["modelId"], "modelo-de-prueba")
        system = call["system"][0]["text"]
        for rule in ("colegios públicos", "exactamente la duración", "400 caracteres", "nunca instrucciones",
                     "materiales declarados", "Responde solo con un objeto JSON"):
            self.assertIn(rule, system)
        prompt = call["messages"][0]["content"][0]["text"]
        for fact in ("Cuarto de primaria", "45 minutos", "pizarra, papel, lápiz", "[M1]", "[M3]",
                     "<indicaciones>El grupo es muy conversador</indicaciones>"):
            self.assertIn(fact, prompt)
        self.assertLessEqual(call["inferenceConfig"]["maxTokens"], 2000)

    def test_las_fuentes_las_resuelve_el_servidor(self):
        content = self.generate()[1]["content"]
        for source in content["sources"]:
            self.assertIn(source["id"], ("M1", "M2", "M3"))
            self.assertGreater(len(source["text"]), 40)

    def test_minutos_del_modelo_se_ajustan_a_la_duracion(self):
        self.bedrock.script = [lesson_json(minutes=(20, 20, 20, 20))]
        content = self.generate()[1]["content"]
        self.assertEqual([a["minutes"] for a in content["activities"]], [12, 11, 11, 11])

    def test_referencias_y_materiales_inventados_se_descartan(self):
        self.bedrock.script = [lesson_json(refs=(["M9"], ["M1"], ["M2"], ["M3"]))]
        draft = self.generate()[1]
        content = draft["content"]
        self.assertEqual(content["activities"][0]["references"], [])
        self.assertTrue(any("M9" in n for n in draft["reviewNotes"]))
        self.assertTrue(any("actividad 1 no cita" in n.lower() for n in draft["reviewNotes"]))
        self.assertEqual(content["materials"], ["pizarra", "papel", "lápiz"])

    def test_json_entre_texto_o_bloque_de_codigo(self):
        self.bedrock.script = ["Aquí tienes:\n```json\n%s\n```" % lesson_json()]
        self.assertEqual(self.generate()[0], 200)
        self.assertEqual(extract_json('xx {"a": 1} yy'), {"a": 1})

    def test_salida_ilegible_da_502_y_no_guarda(self):
        self.bedrock.script = ["No puedo ayudarte con eso."]
        status, body, _ = self.generate()
        self.assertEqual((status, body["error"]["code"]), (502, "generation_failed"))
        self.assertIn("reintentar", body["error"]["message"])
        self.assertEqual(self.call("GET", "/api/sessions")[1], [])

    def test_throttling_reintenta_con_espera_y_luego_responde(self):
        self.bedrock.script = [ClientError("ThrottlingException"), ClientError("ThrottlingException"), lesson_json()]
        status, draft, _ = self.generate()
        self.assertEqual(status, 200)
        self.assertTrue(draft["generatedBy"]["isBedrock"])
        self.assertEqual(len(self.bedrock.calls), 3)
        self.assertEqual(self.sleeps, list(bedrock_module.BACKOFF_SECONDS))

    def test_si_el_modelo_no_responde_usa_respaldo_rotulado(self):
        for failure in (ReadTimeoutError("timeout"), ClientError("ServiceUnavailableException"),
                        ClientError("ModelNotReadyException")):
            with self.subTest(failure=type(failure).__name__):
                self.bedrock.script = [failure]
                status, draft, _ = self.generate()
                self.assertEqual(status, 200)
                self.assertFalse(draft["generatedBy"]["isBedrock"])
                self.assertEqual(draft["generatedBy"]["engine"], "local-respaldo")
                self.assertIn("Respaldo local", draft["generatedBy"]["label"])
                self.assertEqual(sum(a["minutes"] for a in draft["content"]["activities"]), 45)

    def test_throttling_persistente_tambien_usa_respaldo(self):
        self.bedrock.script = [ClientError("ThrottlingException")]
        status, draft, _ = self.generate()
        self.assertEqual(status, 200)
        self.assertEqual(draft["generatedBy"]["engine"], "local-respaldo")
        self.assertEqual(len(self.bedrock.calls), bedrock_module.MAX_ATTEMPTS)

    def test_otros_errores_dan_502(self):
        for code in ("AccessDeniedException", "ValidationException"):
            with self.subTest(code=code):
                self.bedrock.script = [ClientError(code)]
                status, body, _ = self.generate()
                self.assertEqual(status, 502)
                self.assertIn(code, body["error"]["message"])

    def test_entrada_invalida_no_llega_al_modelo(self):
        for bad in ({"durationMinutes": 500}, {"grade": ""}, {"notes": "x" * 501}):
            status, _, _ = self.generate(**bad)
            self.assertIn(status, (400, 422))
        self.assertEqual(self.bedrock.calls, [])

    def test_flujo_completo_guardar_recuperar_y_registrar_en_dynamodb(self):
        draft = self.generate()[1]
        status, session, _ = self.call("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "markReviewed": True, "draftId": draft["draftId"]})
        self.assertEqual(status, 201)
        self.assertTrue(session["currentVersion"]["generatedBy"]["isBedrock"])
        self.assertFalse(session["currentVersion"]["editedByTeacher"])
        self.assertEqual(len(self.bedrock.calls), 1)  # guardar no vuelve a llamar al modelo
        status, rec, _ = self.call("POST", "/api/sessions/%s/records" % session["id"], {
            "declaredDate": "2026-10-30", "activity": "Parejas", "observation": "Observación simulada"})
        self.assertEqual(status, 201)
        # Otro contenedor de Lambda (servicio nuevo) sobre la misma tabla recupera todo.
        fresh = Service(DynamoRepository(self.db, "tabla-falsa"), BedrockGenerator(client=self.bedrock), app.lambda_settings())
        app._service = fresh
        listing = self.call("GET", "/api/sessions")[1]
        self.assertEqual([s["id"] for s in listing], [session["id"]])
        detail = self.call("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(detail["currentVersion"]["reviewStatus"], "revisada")
        self.assertEqual(len(detail["records"]), 1)
        self.assertTrue(detail["records"][0]["isSimulated"])
        # La semilla no se duplica en el arranque del nuevo contenedor.
        exp = self.call("GET", "/api/experiences/exp-sim-escucha-v1")[1]
        self.assertEqual((exp["ratingSummary"]["average"], exp["ratingSummary"]["completeCount"]), (4.4, 3))
        self.assertEqual(len(exp["comments"]), 1)

    def test_adaptar_experiencia_envia_la_mejora_al_modelo(self):
        status, draft, _ = self.call("POST", "/api/experiences/exp-sim-escucha-v1/adapt", {"durationMinutes": 45})
        self.assertEqual(status, 200)
        self.assertTrue(draft["generatedBy"]["isBedrock"])
        self.assertEqual(draft["provenance"]["experienceId"], "exp-sim-escucha-v1")
        prompt = self.bedrock.calls[-1]["messages"][0]["content"][0]["text"]
        self.assertIn("<experiencia>", prompt)
        self.assertIn("Dividir las instrucciones en tres pasos", prompt)

    def test_resumir_acuerdos_con_bedrock_y_respaldo(self):
        self.bedrock.script = ["Coincidencias: instrucciones claras. Cambio sugerido: tres pasos. Pocas valoraciones."]
        status, result, _ = self.call("GET", "/api/experiences/exp-sim-escucha-v1/summary")
        self.assertEqual(status, 200)
        self.assertTrue(result["generatedBy"]["isBedrock"])
        self.assertIn("Pocas valoraciones", result["text"])
        call = self.bedrock.calls[-1]
        self.assertIn("120 palabras", call["system"][0]["text"])
        self.assertIn('"valoracionesCompletas": 3', call["messages"][0]["content"][0]["text"])
        self.bedrock.script = [ReadTimeoutError("timeout")]
        status, result, _ = self.call("GET", "/api/experiences/exp-sim-escucha-v1/summary")
        self.assertEqual(status, 200)
        self.assertFalse(result["generatedBy"]["isBedrock"])

    def test_el_cliente_no_puede_fingir_que_un_texto_manual_es_de_bedrock(self):
        self.service.generator = support.LocalSimulatedGenerator()
        draft = self.generate()[1]
        _, session, _ = self.call("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "generatedBy": {"engine": "bedrock", "isBedrock": True}})
        self.assertFalse(session["currentVersion"]["generatedBy"]["isBedrock"])


# ---------------------------------------------------------------------------
# Frontend servido por la Lambda
# ---------------------------------------------------------------------------
class FrontFromLambdaTests(LambdaTestCase):
    def setUp(self):
        super().setUp()
        app._settings = app.lambda_settings().__class__(**{**app._settings.__dict__, "front_dir": str(ROOT / "front")})

    def test_raiz_200_html_sin_redireccion(self):
        response = app.handler(event("GET", "/"), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(response["headers"]["Content-Type"].startswith("text/html"))
        self.assertNotIn("Location", response["headers"])
        self.assertIn("AulaLista", response["body"])

    def test_assets_y_rutas_fuera_de_front(self):
        self.assertEqual(app.handler(event("GET", "/js/app.js"), None)["statusCode"], 200)
        self.assertEqual(app.handler(event("GET", "/../template.yaml"), None)["statusCode"], 404)
        self.assertEqual(app.handler(event("GET", "/%2e%2e/template.yaml"), None)["statusCode"], 404)
        self.assertEqual(app.handler(event("POST", "/"), None)["statusCode"], 405)

    def test_el_paquete_de_la_lambda_incluye_front(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("cp -r front", makefile)
        self.assertIn("cp back/app.py", makefile)


if __name__ == "__main__":
    unittest.main()
