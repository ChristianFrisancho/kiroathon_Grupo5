"""Reproducciones de la auditoría: integridad de versiones, escrituras parciales, procedencia de Bedrock,
idempotencia, presupuesto de tiempo, patrones de consulta, validación de la salida de IA y migración."""
import copy
import json
import threading
import unittest

import support
from fakes import ClientError, FakeBedrock, FakeClock, FakeDynamoClient, ReadTimeoutError
from support import CASE, Api, TempDb, make_service, make_settings

from aulalista import bedrock as bedrock_module
from aulalista import budget
from aulalista.bedrock import BedrockGenerator, undeclared_resources
from aulalista.dynamo_repository import DynamoRepository
from aulalista.generator import split_minutes
from aulalista.service import Service

import app


def lesson(minutes=(10, 15, 12, 8), refs=(["M1"], ["M1", "M2"], ["M2"], ["M3"]), descriptions=None, **extra):
    descriptions = descriptions or ["Las parejas conversan y practican la actividad %d." % (i + 1) for i in range(len(minutes))]
    data = {
        "title": "Escuchamos y comprobamos lo que entendimos",
        "purpose": "Practicar la escucha activa y el parafraseo en parejas.",
        "activities": [{"title": "Actividad %d" % (i + 1), "minutes": m, "description": d, "references": list(r)}
                       for i, (m, r, d) in enumerate(zip(minutes, refs, descriptions))],
        "expectedEvidence": "Cada estudiante parafrasea una idea de su pareja.",
    }
    data.update(extra)
    return json.dumps(data, ensure_ascii=False)


def dynamo_service(bedrock=None, clock=None, **kw):
    db = FakeDynamoClient()
    generator = BedrockGenerator(model_id="modelo-de-prueba", client=bedrock or FakeBedrock(lesson()),
                                 sleep=(clock.sleep if clock else (lambda s: None)),
                                 **({"monotonic": clock.monotonic} if clock else {}))
    settings = make_settings()
    service = Service(DynamoRepository(db, "tabla-falsa"), generator, settings, **kw)
    return service, db


def bedrock_sqlite_service(bedrock=None):
    generator = BedrockGenerator(model_id="modelo-de-prueba", client=bedrock or FakeBedrock(lesson()),
                                 sleep=lambda s: None)
    return make_service(generator=generator)


def edit_payload(session, title, parent=None):
    content = copy.deepcopy(session["currentVersion"]["content"])
    content["title"] = title
    body = {"content": content}
    if parent is not None:
        body["parentVersionId"] = parent
    return body


class BackendCase(unittest.TestCase):
    """Cada prueba se ejecuta contra SQLite y contra DynamoDB (cliente falso con transacciones)."""

    def backends(self):
        sqlite_service = make_service()
        dyn_service, _db = dynamo_service()
        return [("sqlite", sqlite_service), ("dynamodb", dyn_service)]


# ---------------------------------------------------------------------------------------------------
# 1. Versiones: concurrencia y números únicos
# ---------------------------------------------------------------------------------------------------
class VersionConcurrencyTests(BackendCase):
    def test_dos_guardados_desde_la_misma_version_uno_confirma_otro_recibe_409(self):
        for name, service in self.backends():
            with self.subTest(backend=name):
                api = Api(service)
                session = support.generate_and_save(api)
                parent = session["currentVersion"]["id"]
                first = api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "A", parent))
                second = api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "B", parent))
                self.assertEqual(first[0], 201)
                self.assertEqual((second[0], second[1]["error"]["code"]), (409, "version_conflict"))
                self.assertIn("guarda tu trabajo como una sesión nueva", second[1]["error"]["message"])
                numbers = [v["number"] for v in api("GET", "/api/sessions/%s" % session["id"])[1]["versions"]]
                self.assertEqual(numbers, [1, 2])
                service.close()

    def test_carrera_real_en_sqlite_con_hilos(self):
        service = make_service()
        api = Api(service)
        session = support.generate_and_save(api)
        parent = session["currentVersion"]["id"]
        results = []
        barrier = threading.Barrier(8)

        def save(i):
            barrier.wait()
            results.append(api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "T%d" % i, parent))[0])

        threads = [threading.Thread(target=save, args=(i,)) for i in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), [201] + [409] * 7)
        numbers = [v["number"] for v in api("GET", "/api/sessions/%s" % session["id"])[1]["versions"]]
        self.assertEqual(numbers, [1, 2])
        service.close()

    def test_carrera_en_dynamodb_entre_lectura_y_transaccion_sin_parent_explicito(self):
        service, db = dynamo_service()
        api = Api(service)
        session = support.generate_and_save(api)
        # Otra petición confirma una versión justo entre la lectura y la transacción de esta.
        db.before_transaction = lambda: api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "Otra"))
        status, body = api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "Mía"))
        self.assertEqual((status, body["error"]["code"]), (409, "version_conflict"))
        versions = api("GET", "/api/sessions/%s" % session["id"])[1]["versions"]
        self.assertEqual([v["number"] for v in versions], [1, 2])
        self.assertEqual(versions[-1]["content"]["title"], "Otra")
        self.assertEqual(len([k for k in db.rows if k == ("SESSION#" + session["id"], "META")]), 1)
        self.assertEqual(len([k for k in db.rows if k[0] == "SESSION#" + session["id"] and k[1].startswith("VERSION#")]), 2)

    def test_parent_que_ya_no_es_vigente_da_409(self):
        for name, service in self.backends():
            with self.subTest(backend=name):
                api = Api(service)
                session = support.generate_and_save(api)
                v1 = session["currentVersion"]["id"]
                api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "v2", v1))
                status, _ = api("POST", "/api/sessions/%s/regenerate" % session["id"], {"parentVersionId": v1})
                self.assertEqual(status, 409)
                service.close()


# ---------------------------------------------------------------------------------------------------
# 2. Escrituras parciales: sin versiones huérfanas
# ---------------------------------------------------------------------------------------------------
class PartialWriteTests(unittest.TestCase):
    def test_dynamodb_fallo_al_crear_sesion_no_deja_version_huerfana(self):
        service, db = dynamo_service()
        api = Api(service)
        _, draft = api("POST", "/api/drafts/generate", CASE)
        db.fail_next_transaction = ClientError("InternalServerError")
        status, body = api("POST", "/api/sessions", {"moduleId": draft["module"]["id"], "context": draft["context"],
                                                     "content": draft["content"], "draftId": draft["draftId"]})
        self.assertEqual(status, 500)
        self.assertNotIn("InternalServerError", json.dumps(body))
        self.assertEqual([k for k in db.rows if k[0].startswith("SESSION#") or k[0].startswith("USER#")], [])
        self.assertEqual(api("GET", "/api/sessions")[1], [])

    def test_dynamodb_fallo_al_anadir_version_no_cambia_nada(self):
        service, db = dynamo_service()
        api = Api(service)
        session = support.generate_and_save(api)
        before = dict(db.rows)
        db.fail_next_transaction = ClientError("ProvisionedThroughputExceededException")
        status, _ = api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "x"))
        self.assertEqual(status, 500)  # error real, no un falso conflicto
        self.assertEqual(db.rows, before)

    def test_sqlite_fallo_tras_mover_la_vigente_hace_rollback(self):
        service = make_service()
        api = Api(service)
        session = support.generate_and_save(api)
        original = service.repo._insert_version
        service.repo._insert_version = lambda v: (_ for _ in ()).throw(RuntimeError("disco lleno"))
        try:
            status, _ = api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "x"))
        finally:
            service.repo._insert_version = original
        self.assertEqual(status, 500)
        detail = api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(detail["currentVersionId"], session["currentVersionId"])
        self.assertEqual(len(detail["versions"]), 1)
        service.close()

    def test_registro_concurrente_no_restaura_una_version_vigente_antigua(self):
        service, db = dynamo_service()
        api = Api(service)
        session = support.generate_and_save(api)
        # Mientras se guarda el registro, otra petición crea la versión 2.
        db.before_transaction = lambda: api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "v2"))
        status, _ = api("POST", "/api/sessions/%s/records" % session["id"],
                        {"declaredDate": "2026-10-30", "activity": "a", "observation": "b"})
        self.assertEqual(status, 201)
        detail = api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(detail["currentVersion"]["number"], 2)
        summary = api("GET", "/api/sessions")[1][0]
        self.assertEqual((summary["currentVersionNumber"], summary["versionCount"], summary["recordCount"]), (2, 2, 1))


# ---------------------------------------------------------------------------------------------------
# 3. Procedencia de Bedrock verificada por el servidor
# ---------------------------------------------------------------------------------------------------
class ProvenanceTests(BackendCase):
    def save(self, api, draft, content=None, **extra):
        return api("POST", "/api/sessions", {"moduleId": draft["module"]["id"], "context": draft["context"],
                                             "content": content or draft["content"], **extra})

    def test_generatedBy_del_navegador_no_crea_atribucion_falsa(self):
        bedrock = FakeBedrock(lesson())
        service = bedrock_sqlite_service(bedrock)
        api = Api(service)
        _, draft = api("POST", "/api/drafts/generate", CASE)
        calls = len(bedrock.calls)
        status, session = self.save(api, draft, generatedBy={"engine": "bedrock", "isBedrock": True})
        self.assertEqual(status, 201)
        self.assertFalse(session["currentVersion"]["generatedBy"]["isBedrock"])
        self.assertEqual(session["currentVersion"]["generatedBy"]["engine"], "manual")
        self.assertEqual(len(bedrock.calls), calls)
        service.close()

    def test_borrador_real_conserva_origen_y_edicion_se_marca(self):
        for name, service in [("sqlite", bedrock_sqlite_service()), ("dynamodb", dynamo_service()[0])]:
            with self.subTest(backend=name):
                api = Api(service)
                _, draft = api("POST", "/api/drafts/generate", CASE)
                self.assertTrue(draft["draftId"].startswith("drf-"))
                _, intact = self.save(api, draft, draftId=draft["draftId"])
                v = intact["currentVersion"]
                self.assertTrue(v["generatedBy"]["isBedrock"])
                self.assertFalse(v["editedByTeacher"])
                self.assertEqual(v["sourceDraftId"], draft["draftId"])
                edited = copy.deepcopy(draft["content"])
                edited["purpose"] = "Propósito corregido por la docente."
                _, changed = self.save(api, draft, content=edited, draftId=draft["draftId"])
                self.assertTrue(changed["currentVersion"]["generatedBy"]["isBedrock"])
                self.assertTrue(changed["currentVersion"]["editedByTeacher"])
                # Una versión posterior hereda el origen del servidor y queda marcada como editada.
                _, v2 = api("POST", "/api/sessions/%s/versions" % intact["id"], edit_payload(intact, "Nuevo título"))
                self.assertTrue(v2["currentVersion"]["generatedBy"]["isBedrock"])
                self.assertTrue(v2["currentVersion"]["editedByTeacher"])
                service.close()

    def test_borrador_de_otra_persona_o_caducado_no_se_acepta(self):
        service = bedrock_sqlite_service()
        api = Api(service)
        _, draft = api("POST", "/api/drafts/generate", CASE, user="u-otra")
        status, session = self.save(api, draft, draftId=draft["draftId"])
        self.assertEqual(status, 201)  # se guarda (sin perder trabajo) pero sin la procedencia ajena
        self.assertFalse(session["currentVersion"]["generatedBy"]["isBedrock"])
        self.assertIsNone(session["currentVersion"]["sourceDraftId"])
        self.assertIn("No pudimos verificar", session["provenanceNote"])
        _, mine = api("POST", "/api/drafts/generate", CASE)
        service.clock = lambda: "2026-11-30T00:00:00.000+00:00"  # un mes después
        _, late = self.save(api, mine, draftId=mine["draftId"])
        self.assertFalse(late["currentVersion"]["generatedBy"]["isBedrock"])
        self.assertIn("caducó", late["provenanceNote"])
        service.close()

    def test_respaldo_local_sigue_como_respaldo_al_guardar(self):
        service = bedrock_sqlite_service(FakeBedrock(ReadTimeoutError("timeout")))
        api = Api(service)
        _, draft = api("POST", "/api/drafts/generate", CASE)
        self.assertEqual(draft["generatedBy"]["engine"], "local-respaldo")
        _, session = self.save(api, draft, draftId=draft["draftId"])
        self.assertEqual(session["currentVersion"]["generatedBy"]["engine"], "local-respaldo")
        self.assertFalse(session["currentVersion"]["generatedBy"]["isBedrock"])
        service.close()


# ---------------------------------------------------------------------------------------------------
# 4. Idempotencia de escrituras con clave de operación
# ---------------------------------------------------------------------------------------------------
class IdempotencyTests(BackendCase):
    def test_misma_clave_y_contenido_no_duplica(self):
        for name, service in self.backends():
            with self.subTest(backend=name):
                api = Api(service)
                _, draft = api("POST", "/api/drafts/generate", CASE)
                body = {"moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
                        "draftId": draft["draftId"], "operationKey": "op-guardar-0001"}
                first = api("POST", "/api/sessions", body)
                again = api("POST", "/api/sessions", body)  # reintento tras perder la confirmación
                self.assertEqual(first[0], 201)
                self.assertEqual(again[1]["id"], first[1]["id"])
                self.assertEqual(len(api("GET", "/api/sessions")[1]), 1)
                other = dict(body, content=dict(body["content"], title="Otro"))
                self.assertEqual(api("POST", "/api/sessions", other)[1]["error"]["code"], "operation_key_reused")
                rec = {"declaredDate": "2026-10-30", "activity": "a", "observation": "b", "operationKey": "op-registro-01"}
                sid = first[1]["id"]
                r1 = api("POST", "/api/sessions/%s/records" % sid, rec)
                r2 = api("POST", "/api/sessions/%s/records" % sid, rec)
                self.assertEqual(r1[1]["id"], r2[1]["id"])
                self.assertEqual(len(api("GET", "/api/sessions/%s" % sid)[1]["records"]), 1)
                service.close()

    def test_clave_en_curso_da_409_y_un_error_libera_la_clave(self):
        from aulalista.service import content_digest
        service = make_service()
        api = Api(service)
        session = support.generate_and_save(api)
        sid = session["id"]
        body = {"declaredDate": "2026-10-30", "activity": "a", "observation": "b"}
        # Otra petición con la misma clave y el mismo contenido sigue en curso.
        digest = content_digest({"op": "record:" + sid, "payload": body})
        service.repo.reserve_operation("u-demo", "op-en-curso-01", digest, service.clock())
        status, err = api("POST", "/api/sessions/%s/records" % sid, dict(body, operationKey="op-en-curso-01"))
        self.assertEqual((status, err["error"]["code"]), (409, "operation_in_progress"))
        self.assertEqual(api("GET", "/api/sessions/%s" % sid)[1]["records"], [])
        # Un error confirmado libera la clave: el docente corrige y la misma clave se acepta.
        bad = dict(body, declaredDate="mal", operationKey="op-fallida-0001")
        self.assertEqual(api("POST", "/api/sessions/%s/records" % sid, bad)[0], 422)
        good = dict(body, operationKey="op-fallida-0001")
        self.assertEqual(api("POST", "/api/sessions/%s/records" % sid, good)[0], 201)
        service.close()


# ---------------------------------------------------------------------------------------------------
# 5. Presupuesto de tiempo de Bedrock dentro del plazo de la Lambda
# ---------------------------------------------------------------------------------------------------
class TimeBudgetTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def tearDown(self):
        budget.set_deadline(None)

    def generator(self, *script):
        client = FakeBedrock(*script, clock=self.clock)
        return BedrockGenerator(client=client, sleep=self.clock.sleep, monotonic=self.clock.monotonic), client

    def module_ctx(self):
        from aulalista import seed
        from aulalista.validators import normalize_context
        module = seed.MODULES["mod-escucha-activa"]
        return module, normalize_context(dict(CASE), module)

    def test_throttling_y_exito_dentro_del_presupuesto(self):
        budget.set_deadline(self.clock.now + 26)
        gen, client = self.generator(ClientError("ThrottlingException"), (lesson(), 3))
        result = gen.generate(*self.module_ctx())
        self.assertTrue(result["_generatedBy"]["isBedrock"])
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(self.clock.slept, [bedrock_module.BACKOFF_SECONDS[0]])

    def test_sin_presupuesto_no_inicia_intento_y_devuelve_respaldo(self):
        budget.set_deadline(self.clock.now + 10)  # < MIN_ATTEMPT_SECONDS
        gen, client = self.generator(lesson())
        result = gen.generate(*self.module_ctx())
        self.assertEqual(client.calls, [])
        self.assertEqual(result["_generatedBy"]["engine"], "local-respaldo")

    def test_no_reintenta_si_la_espera_dejaria_sin_margen(self):
        budget.set_deadline(self.clock.now + 26)
        gen, client = self.generator((ClientError("ThrottlingException"), 10))  # el intento consume 10 s
        start = self.clock.now
        result = gen.generate(*self.module_ctx())
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["_generatedBy"]["engine"], "local-respaldo")
        self.assertLess(self.clock.now - start, 26)

    def test_timeout_largo_termina_con_respaldo_antes_del_limite(self):
        budget.set_deadline(self.clock.now + 26)
        gen, client = self.generator((ReadTimeoutError("timeout"), bedrock_module.ATTEMPT_TIMEOUT))
        start = self.clock.now
        result = gen.generate(*self.module_ctx())
        self.assertEqual(result["_generatedBy"]["engine"], "local-respaldo")
        self.assertLessEqual(self.clock.now - start, 26)
        self.assertFalse(result["_generatedBy"]["isBedrock"])

    def test_permisos_no_se_convierten_en_respaldo(self):
        budget.set_deadline(self.clock.now + 26)
        gen, _ = self.generator(ClientError("AccessDeniedException"))
        with self.assertRaises(bedrock_module.GeneratorError):
            gen.generate(*self.module_ctx())

    def test_el_sdk_no_reintenta_por_su_cuenta(self):
        self.assertLessEqual(bedrock_module.ATTEMPT_TIMEOUT + bedrock_module.CONNECT_TIMEOUT,
                             bedrock_module.MIN_ATTEMPT_SECONDS)
        source = open(bedrock_module.__file__, encoding="utf-8").read()
        self.assertIn('retries={"max_attempts": 1', source)

    def test_la_lambda_fija_el_plazo_con_el_tiempo_restante(self):
        class Context:
            def get_remaining_time_in_millis(self):
                return 9000  # 9 s: no alcanza para un intento de Bedrock

        bedrock = FakeBedrock(lesson())
        generator = BedrockGenerator(client=bedrock, sleep=lambda s: None)
        app._service = Service(DynamoRepository(FakeDynamoClient(), "t"), generator, app.lambda_settings(),
                               dispatcher=lambda j: None)
        try:
            event = {"rawPath": "/api/drafts/generate", "requestContext": {"http": {"method": "POST"}},
                     "headers": {}, "body": json.dumps(CASE)}
            response = app.handler(event, Context())
        finally:
            app._service = None
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["generatedBy"]["engine"], "local-respaldo")
        self.assertEqual(bedrock.calls, [])
        self.assertIsNone(budget.deadline())  # el plazo no se filtra a la siguiente petición


# ---------------------------------------------------------------------------------------------------
# 6. Patrones de consulta acotados en DynamoDB
# ---------------------------------------------------------------------------------------------------
class QueryPatternTests(unittest.TestCase):
    def test_hoy_y_portafolio_no_leen_versiones_ni_registros_por_sesion(self):
        service, db = dynamo_service()
        api = Api(service)
        sessions = [support.generate_and_save(api) for _ in range(8)]
        for s in sessions[:3]:
            api("POST", "/api/sessions/%s/records" % s["id"], {"declaredDate": "2026-10-30", "activity": "a", "observation": "b"})
        db.calls.clear()
        overview = api("GET", "/api/overview")[1]
        self.assertEqual(len(overview["recentSessions"]), 5)
        self.assertEqual(overview["sessionCount"], 8)
        queried = {pk for (op, pk) in db.calls if op == "query"}
        self.assertEqual(queried, {"USER#u-demo"})
        db.calls.clear()
        listing = api("GET", "/api/sessions")[1]
        self.assertEqual(sum(s["recordCount"] for s in listing), 3)
        queried = {pk for (op, pk) in db.calls if op == "query"}
        self.assertEqual(queried, {"USER#u-demo", "EXPERIENCE"})

    def test_items_se_detienen_en_el_limite(self):
        service, db = dynamo_service()
        for i in range(150):
            service.repo.add_item("item-%03d" % i, json.dumps(i), "2026-10-30T10:%02d:%02d.000" % (i // 60, i % 60))
        db.calls.clear()
        items = service.list_items()
        self.assertEqual(len(items), 100)
        self.assertEqual(items[0]["id"], "item-149")
        self.assertEqual(len([c for c in db.calls if c == ("query", "ITEMS_BY_TIME")]), 50)  # no 75

    def test_sesion_de_otra_persona_sigue_dando_403(self):
        service, _ = dynamo_service()
        api = Api(service)
        session = support.generate_and_save(api)
        self.assertEqual(api("GET", "/api/sessions/%s" % session["id"], user="u-otra")[0], 403)


# ---------------------------------------------------------------------------------------------------
# 7. Validación de la salida de IA
# ---------------------------------------------------------------------------------------------------
class AiOutputTests(unittest.TestCase):
    def generate(self, *script):
        service = bedrock_sqlite_service(FakeBedrock(*script))
        try:
            return Api(service)("POST", "/api/drafts/generate", CASE)
        finally:
            service.close()

    def test_respuesta_invalida_se_vuelve_a_pedir_una_vez(self):
        bad = json.loads(lesson())
        bad["expectedEvidence"] = ["lista", "en vez de texto"]   # caso real observado en producción
        bedrock = FakeBedrock(json.dumps(bad), lesson())
        service = bedrock_sqlite_service(bedrock)
        try:
            status, draft = Api(service)("POST", "/api/drafts/generate", CASE)
        finally:
            service.close()
        self.assertEqual(status, 200)
        self.assertTrue(draft["generatedBy"]["isBedrock"])
        self.assertEqual(len(bedrock.calls), 2)
        self.assertIn("no fue válida", bedrock.calls[1]["messages"][0]["content"][0]["text"])

    def test_dos_respuestas_invalidas_dan_502_sin_guardar(self):
        bad = json.loads(lesson())
        bad["expectedEvidence"] = {"texto": "objeto"}
        bedrock = FakeBedrock(json.dumps(bad))
        service = bedrock_sqlite_service(bedrock)
        try:
            api = Api(service)
            status, body = api("POST", "/api/drafts/generate", CASE)
            self.assertEqual((status, body["error"]["code"]), (502, "generation_failed"))
            self.assertIn("la evidencia esperada debe ser texto", body["error"]["message"])
            self.assertEqual(len(bedrock.calls), 2)
            self.assertEqual(api("GET", "/api/sessions")[1], [])
        finally:
            service.close()

    def test_todas_las_referencias_inventadas_da_502(self):
        status, body = self.generate(lesson(refs=(["M7"], ["M8"], ["X"], [])))
        self.assertEqual(status, 502)
        self.assertIn("no citó ningún fragmento real", body["error"]["message"])

    def test_referencias_mixtas_se_avisan(self):
        status, draft = self.generate(lesson(refs=(["M1", "M9"], ["M2"], ["M2"], ["M3"])))
        self.assertEqual(status, 200)
        self.assertEqual(draft["content"]["activities"][0]["references"], ["M1"])
        self.assertTrue(any("M9" in n for n in draft["reviewNotes"]))

    def test_recurso_no_declarado_genera_aviso_de_revision(self):
        descriptions = ["Proyecta un video con el proyector y comenta en parejas.", "Las parejas conversan en silencio.",
                        "Cada estudiante parafrasea a su pareja.", "Cierre con preguntas de aclaración."]
        status, draft = self.generate(lesson(descriptions=descriptions))
        self.assertEqual(status, 200)
        note = next(n for n in draft["reviewNotes"] if "no declaraste" in n)
        self.assertIn("proyector", note)
        self.assertEqual(undeclared_resources("Usa la pizarra y papel", ["pizarra", "papel"]), [])

    def test_json_invalido_truncado_o_cortado(self):
        for script in ('{"title": "x", "activities": [', "Lo siento, no puedo.",
                       {"stopReason": "max_tokens", "output": {"message": {"content": [{"text": lesson()}]}}}):
            with self.subTest(script=str(script)[:30]):
                status, body = self.generate(script)
                self.assertEqual(status, 502)
                self.assertIn("reintentar", body["error"]["message"])

    def test_actividades_sin_contenido_util(self):
        # Una actividad vacía ya no se descarta en silencio: la respuesta entera es inválida (502).
        status, body = self.generate(lesson(descriptions=["", "ok", "Las parejas conversan y practican.", "Cierre con preguntas de aclaración."]))
        self.assertEqual((status, body["error"]["code"]), (502, "generation_failed"))

    def test_reescalar_nunca_deja_actividades_en_cero(self):
        parts = split_minutes(10, [100, 1, 1, 1, 1])
        self.assertEqual(sum(parts), 10)
        self.assertTrue(all(p >= 1 for p in parts))
        with self.assertRaises(ValueError):
            split_minutes(3, [1, 1, 1, 1])
        status, draft = self.generate(lesson(minutes=(200, 1, 1, 1)))
        self.assertEqual(status, 200)
        self.assertTrue(all(a["minutes"] >= 1 for a in draft["content"]["activities"]))
        self.assertTrue(any("se ajustaron" in n for n in draft["reviewNotes"]))


# ---------------------------------------------------------------------------------------------------
# 8. Registro ligado a la versión elegida
# ---------------------------------------------------------------------------------------------------
class RecordVersionTests(BackendCase):
    def test_registro_sobre_version_antigua_conserva_su_id(self):
        for name, service in self.backends():
            with self.subTest(backend=name):
                api = Api(service)
                session = support.generate_and_save(api)
                v1 = session["currentVersion"]["id"]
                api("POST", "/api/sessions/%s/versions" % session["id"], edit_payload(session, "v2"))
                status, rec = api("POST", "/api/sessions/%s/records" % session["id"],
                                  {"versionId": v1, "declaredDate": "2026-10-30", "activity": "a", "observation": "b"})
                self.assertEqual(status, 201)
                self.assertEqual((rec["versionId"], rec["versionNumber"]), (v1, 1))
                other = support.generate_and_save(api)
                bad = api("POST", "/api/sessions/%s/records" % session["id"],
                          {"versionId": other["currentVersion"]["id"], "declaredDate": "2026-10-30", "activity": "a", "observation": "b"})
                self.assertEqual(bad[0], 404)
                service.close()


# ---------------------------------------------------------------------------------------------------
# 9. Migración compatible del esquema anterior de DynamoDB
# ---------------------------------------------------------------------------------------------------
class MigrationTests(unittest.TestCase):
    def test_datos_del_esquema_anterior_se_copian_sin_borrar(self):
        db = FakeDynamoClient()

        def put(pk, sk, doc):
            db.rows[(pk, sk)] = {"pk": {"S": pk}, "sk": {"S": sk}, "doc": {"S": json.dumps(doc)}}

        session = {"id": "ses-old", "ownerId": "u-demo", "title": "Antigua", "moduleId": "mod-escucha-activa",
                   "moduleVersion": "1.0", "provenance": None, "currentVersionId": "ver-old",
                   "createdAt": "2026-10-30T09:00:00.000+00:00", "updatedAt": "2026-10-30T09:00:00.000+00:00"}
        version = {"id": "ver-old", "sessionId": "ses-old", "number": 1, "parentVersionId": None,
                   "context": {}, "content": {"title": "Antigua"}, "reviewStatus": "revisada", "reason": "",
                   "generatedBy": {"engine": "bedrock", "isBedrock": True}, "createdAt": session["createdAt"]}
        put("SESSION", "ses-old", session)
        put("VERSION", "ver-old", version)
        put("VERSION", "ver-huerfana", dict(version, id="ver-huerfana", sessionId="ses-sin-sesion"))
        put("RECORD", "rec-old", {"id": "rec-old", "sessionId": "ses-old", "versionId": "ver-old",
                                  "createdAt": session["createdAt"]})
        put("RATING", "exp-x#u-1", {"id": "r", "versionId": "exp-x", "reviewerId": "u-1", "createdAt": "t"})
        put("ITEM", "item-old", {"id": "item-old", "value": "\"v\"", "createdAt": "2026-10-30T08:00:00"})
        legacy_keys = set(db.rows)
        repo = DynamoRepository(db, "t")
        self.assertTrue(repo.migrate_legacy())
        self.assertFalse(repo.migrate_legacy())  # idempotente
        self.assertTrue(legacy_keys <= set(db.rows))  # no borra nada
        listed = repo.list_sessions("u-demo")
        self.assertEqual([s["id"] for s in listed], ["ses-old"])
        self.assertEqual((listed[0]["currentVersionNumber"], listed[0]["recordCount"]), (1, 1))
        self.assertEqual(len(repo.list_versions("ses-old")), 1)
        self.assertEqual(len(repo.list_ratings("exp-x")), 1)
        self.assertEqual([i["id"] for i in repo.list_items()], ["item-old"])
        self.assertIsNone(repo.get_session("ses-sin-sesion"))


if __name__ == "__main__":
    unittest.main()
