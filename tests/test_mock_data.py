"""Datos simulados de matemática (back/aulalista/mockdata/): integridad, siembra y uso en el flujo."""
import json
import re
import unittest
from dataclasses import replace

import support
from fakes import FakeDynamoClient
from support import Api, TempDb, make_settings

from aulalista import mockdata, scoring
from aulalista.dynamo_repository import DynamoRepository
from aulalista.generator import LocalSimulatedGenerator
from aulalista.repository import Repository
from aulalista.service import Service
from aulalista.validators import normalize_context, validate_lesson_content

MOCK = mockdata.load()
MATH_IDS = {"mod-geometria-perimetro-area", "mod-algebra-ecuaciones", "mod-fracciones-equivalentes"}
MATH_EXPERIENCES = {"exp-sim-geometria-pasos", "exp-sim-balanza-ecuaciones", "exp-sim-fracciones-papel"}


def service(repo=None, enabled=True):
    settings = replace(make_settings(), mock_data=enabled)
    return Service(repo or Repository(":memory:"), LocalSimulatedGenerator(), settings)


class MockFileTests(unittest.TestCase):
    def test_modulos_de_matematica_con_fragmentos(self):
        self.assertEqual(set(MOCK["modules"]), MATH_IDS)
        for module in MOCK["modules"].values():
            with self.subTest(module=module["id"]):
                ids = [f["id"] for f in module["fragments"]]
                self.assertGreaterEqual(len(ids), 3)
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(module["isSimulated"])
                self.assertIn("simulado", module["sourceLabel"].lower())
                self.assertIn("Matemática", module["area"])
                self.assertTrue(all(len(f["text"]) > 40 for f in module["fragments"]))

    def test_cada_experiencia_es_una_sesion_valida(self):
        for exp in MOCK["experiences"]:
            with self.subTest(exp=exp["id"]):
                module = MOCK["modules"][exp["context"]["moduleId"]]
                context = normalize_context(exp["context"], module)
                content = validate_lesson_content(exp["content"], module, context)  # minutos, refs, materiales
                self.assertEqual(sum(a["minutes"] for a in content["activities"]), context["durationMinutes"])
                self.assertTrue(content["sources"])
                self.assertEqual(exp["grade"], context["grade"])

    def test_valoraciones_respetan_las_reglas(self):
        for exp in MOCK["experiences"]:
            with self.subTest(exp=exp["id"]):
                reviewers = [r["reviewerId"] for r in exp["ratings"]]
                self.assertEqual(len(reviewers), len(set(reviewers)))       # una por persona
                self.assertNotIn(exp["authorId"], reviewers)                 # sin autoevaluación
                for rating in exp["ratings"]:
                    self.assertEqual(len(rating["values"]), 4)
                    self.assertTrue(all(v is None or (isinstance(v, int) and 1 <= v <= 5) for v in rating["values"]))
                    self.assertTrue(rating["context"])

    def test_docentes_ficticios_sin_datos_personales(self):
        people = set(MOCK["users"])
        for exp in MOCK["experiences"]:
            self.assertIn(exp["authorId"], people)
            self.assertTrue({r["reviewerId"] for r in exp["ratings"]} <= people)
            self.assertTrue({c["authorId"] for c in exp["comments"]} <= people)
        text = json.dumps(MOCK, ensure_ascii=False)
        self.assertTrue(all("simulad" in label.lower() for label in MOCK["users"].values()))
        self.assertIsNone(re.search(r"[\w.-]+@[\w-]+\.\w+", text))   # sin correos
        self.assertIsNone(re.search(r"\d{7,}", text))                  # sin teléfonos ni documentos

    def test_ids_no_chocan_con_la_semilla_base(self):
        from aulalista import seed
        self.assertFalse(set(MOCK["modules"]) & set(seed.MODULES))
        self.assertFalse(set(MOCK["users"]) & set(seed.USERS))
        self.assertNotIn(seed.SEED_EXPERIENCE_ID, MATH_EXPERIENCES)


class SeedingTests(unittest.TestCase):
    def test_desactivado_no_cambia_la_demo_base(self):
        svc = service(enabled=False)
        api = Api(svc)
        self.assertEqual([m["id"] for m in api("GET", "/api/modules")[1]], ["mod-escucha-activa"])
        self.assertEqual([e["id"] for e in api("GET", "/api/experiences")[1]], ["exp-sim-escucha-v1"])
        self.assertEqual(api("GET", "/api/modules/mod-algebra-ecuaciones")[0], 404)
        svc.close()

    def test_activado_publica_modulos_y_experiencias(self):
        svc = service()
        api = Api(svc)
        modules = {m["id"]: m for m in api("GET", "/api/modules")[1]}
        self.assertEqual(set(modules), MATH_IDS | {"mod-escucha-activa"})
        self.assertEqual(modules["mod-algebra-ecuaciones"]["area"], "Matemática · Álgebra")
        cards = {e["id"]: e for e in api("GET", "/api/experiences")[1]}
        self.assertTrue(MATH_EXPERIENCES <= set(cards))
        geo = cards["exp-sim-geometria-pasos"]
        self.assertTrue(geo["isSimulated"])
        self.assertEqual(geo["authorLabel"], "Docente simulada de matemática · primaria")
        self.assertEqual((geo["ratingSummary"]["completeCount"], geo["ratingSummary"]["partialCount"]), (2, 1))
        self.assertEqual(geo["ratingSummary"]["average"], 4.3)  # (4,5 + 4,0) / 2 = 4,25 → 4,3
        alg = cards["exp-sim-balanza-ecuaciones"]["ratingSummary"]
        self.assertEqual((alg["completeCount"], alg["average"], alg["label"]), (3, 4.4, "Pocas valoraciones"))  # (4,5 + 4,75 + 4,0) / 3 = 4,42
        frac = cards["exp-sim-fracciones-papel"]["ratingSummary"]
        self.assertEqual((frac["completeCount"], frac["partialCount"], frac["average"]), (1, 1, 4.8))
        detail = api("GET", "/api/experiences/exp-sim-balanza-ecuaciones")[1]
        self.assertEqual(len(detail["comments"]), 1)
        self.assertEqual(detail["comments"][0]["kind"], "diseno")
        self.assertEqual(api("GET", "/api/sessions")[1], [])  # el portafolio del docente sigue limpio
        svc.close()

    def test_la_media_sale_de_los_registros_sembrados(self):
        svc = service()
        for exp in MOCK["experiences"]:
            expected = scoring.summarize([dict(zip(("clarity", "feasibility", "coherence", "observation"), r["values"]))
                                          for r in exp["ratings"]])
            got = Api(svc)("GET", "/api/experiences/%s" % exp["id"])[1]["ratingSummary"]
            self.assertEqual((got["average"], got["completeCount"]), (expected["average"], expected["completeCount"]))
        svc.close()

    def test_siembra_idempotente_en_sqlite_y_dynamodb(self):
        with TempDb() as db:
            for _ in range(3):
                svc = service(Repository(db.path))
                svc.close()
            svc = service(Repository(db.path))
            self.check_counts(Api(svc))
            svc.close()
        client = FakeDynamoClient()
        for _ in range(3):
            service(DynamoRepository(client, "t"))
        self.check_counts(Api(service(DynamoRepository(client, "t"))))

    def check_counts(self, api):
        cards = api("GET", "/api/experiences")[1]
        self.assertEqual(len(cards), 4)
        for exp in MOCK["experiences"]:
            detail = api("GET", "/api/experiences/%s" % exp["id"])[1]
            self.assertEqual(len(detail["ratings"]), len(exp["ratings"]))
            self.assertEqual(len(detail["comments"]), len(exp["comments"]))


class FlowWithMockDataTests(unittest.TestCase):
    def setUp(self):
        self.svc = service()
        self.api = Api(self.svc)

    def tearDown(self):
        self.svc.close()

    def test_preparar_y_guardar_una_clase_de_cada_modulo(self):
        cases = {
            "mod-geometria-perimetro-area": ("Quinto de primaria", 50, ["cinta métrica", "papel cuadriculado"]),
            "mod-algebra-ecuaciones": ("Primero de secundaria", 45, ["pizarra", "tarjetas de papel"]),
            "mod-fracciones-equivalentes": ("Cuarto de primaria", 40, ["hojas de papel", "colores"]),
        }
        for module_id, (grade, minutes, materials) in cases.items():
            with self.subTest(module=module_id):
                status, draft = self.api("POST", "/api/drafts/generate", {
                    "moduleId": module_id, "grade": grade, "durationMinutes": minutes, "materials": materials})
                self.assertEqual(status, 200)
                content = draft["content"]
                self.assertEqual(sum(a["minutes"] for a in content["activities"]), minutes)
                fragment_ids = {f["id"] for f in MOCK["modules"][module_id]["fragments"]}
                self.assertEqual({s["id"] for s in content["sources"]}, fragment_ids)
                self.assertNotIn("escuch", json.dumps(content, ensure_ascii=False).lower())  # no hereda escucha activa
                status, session = self.api("POST", "/api/sessions", {
                    "moduleId": module_id, "context": draft["context"], "content": content,
                    "draftId": draft["draftId"], "markReviewed": True})
                self.assertEqual(status, 201)
                self.assertEqual(session["module"]["id"], module_id)
        self.assertEqual(len(self.api("GET", "/api/sessions")[1]), 3)

    def test_valorar_y_adaptar_una_experiencia_de_matematica(self):
        status, body = self.api("POST", "/api/experiences/exp-sim-fracciones-papel/ratings",
                                support.rating_payload([4, 4, 4, 4], context="Tercero de primaria"))
        self.assertEqual(status, 201)
        summary = body["experience"]["ratingSummary"]
        self.assertEqual((summary["completeCount"], summary["average"]), (2, 4.4))  # (4,75 + 4) / 2 = 4,375 → 4,4
        status, draft = self.api("POST", "/api/experiences/exp-sim-balanza-ecuaciones/adapt", {"durationMinutes": 40})
        self.assertEqual(status, 200)
        self.assertEqual(draft["provenance"]["authorLabel"], "Docente simulado de matemática · secundaria")
        self.assertEqual(sum(a["minutes"] for a in draft["content"]["activities"]), 40)

    def test_resumir_acuerdos_usa_los_registros_sembrados(self):
        status, result = self.api("GET", "/api/experiences/exp-sim-balanza-ecuaciones/summary")
        self.assertEqual(status, 200)
        self.assertIn("3 valoraciones completas", result["text"])
        self.assertIn("Con 40 minutos hay que quitar una ecuación.", result["text"])


if __name__ == "__main__":
    unittest.main()
