"""Historia principal: módulo → borrador → revisión → guardado → portafolio → registro."""
import copy
import time
import unittest

import support
from support import CASE, Api, TempDb, generate_and_save, make_service


class TeacherFlowTests(unittest.TestCase):
    def setUp(self):
        self.service = make_service()
        self.api = Api(self.service)

    def tearDown(self):
        self.service.close()

    # --- módulo y borrador -------------------------------------------------
    def test_modulo_precargado_con_fuente_y_fragmentos(self):
        status, module = self.api("GET", "/api/modules/mod-escucha-activa")
        self.assertEqual(status, 200)
        self.assertEqual([f["id"] for f in module["fragments"]], ["M1", "M2", "M3"])
        self.assertTrue(module["isSimulated"])
        self.assertIn("APRENDE PERÚ", module["sourceLabel"])
        self.assertEqual(self.api("GET", "/api/modules/no-existe")[0], 404)

    def test_borrador_usa_el_contexto_confirmado_y_no_se_persiste(self):
        status, draft = self.api("POST", "/api/drafts/generate", CASE)
        self.assertEqual(status, 200)
        self.assertTrue(draft["isDraft"])
        self.assertEqual(draft["reviewStatus"], "borrador")
        self.assertEqual(draft["context"]["grade"], "Cuarto de primaria")
        self.assertEqual(draft["content"]["durationMinutes"], 45)
        self.assertEqual(sum(a["minutes"] for a in draft["content"]["activities"]), 45)
        self.assertEqual(set(draft["content"]["materials"]), {"pizarra", "papel", "lápiz"})
        self.assertFalse(draft["generatedBy"]["isBedrock"])
        # Las referencias existen y son inspeccionables.
        for source in draft["content"]["sources"]:
            self.assertIn(source["id"], {"M1", "M2", "M3"})
            self.assertTrue(source["text"])
        self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    def test_entradas_invalidas_dan_error_comprensible(self):
        for bad in ({**CASE, "durationMinutes": 5}, {**CASE, "grade": ""}, {**CASE, "moduleId": "x"}):
            status, body = self.api("POST", "/api/drafts/generate", bad)
            self.assertIn(status, (404, 422))
            self.assertTrue(body["error"]["message"])

    # --- guardado, versiones y revisión ------------------------------------
    def test_guardar_borrador_y_recuperarlo(self):
        session = generate_and_save(self.api)
        self.assertEqual(session["currentVersion"]["reviewStatus"], "borrador")
        status, listing = self.api("GET", "/api/sessions")
        self.assertEqual(status, 200)
        self.assertEqual(listing[0]["id"], session["id"])
        status, fetched = self.api("GET", "/api/sessions/%s" % session["id"])
        self.assertEqual(fetched["currentVersion"]["content"], session["currentVersion"]["content"])

    def test_guardar_version_revisada_requiere_accion_expresa(self):
        self.assertEqual(generate_and_save(self.api)["currentVersion"]["reviewStatus"], "borrador")
        self.assertEqual(generate_and_save(self.api, reviewed=True)["currentVersion"]["reviewStatus"], "revisada")

    def test_edicion_posterior_crea_otro_borrador_y_conserva_la_revisada(self):
        session = generate_and_save(self.api, reviewed=True)
        content = copy.deepcopy(session["currentVersion"]["content"])
        content["title"] = "Título editado por el docente"
        status, updated = self.api("POST", "/api/sessions/%s/versions" % session["id"],
                                   {"content": content, "reason": "Cambié el título"})
        self.assertEqual(status, 201)
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["currentVersion"]["number"], 2)
        self.assertEqual(updated["currentVersion"]["reviewStatus"], "borrador")
        self.assertEqual(updated["versions"][0]["reviewStatus"], "revisada")
        self.assertEqual(updated["versions"][0]["content"]["title"], session["currentVersion"]["content"]["title"])
        self.assertEqual(updated["currentVersion"]["parentVersionId"], updated["versions"][0]["id"])
        self.assertEqual(updated["currentVersion"]["reason"], "Cambié el título")

    def test_marcar_como_revisada_es_una_accion_explicita(self):
        session = generate_and_save(self.api)
        vid = session["currentVersion"]["id"]
        status, updated = self.api("POST", "/api/sessions/%s/versions/%s/review" % (session["id"], vid))
        self.assertEqual(status, 200)
        self.assertEqual(updated["currentVersion"]["reviewStatus"], "revisada")

    def test_markReviewed_solo_con_true_estricto(self):
        session = generate_and_save(self.api)
        content = session["currentVersion"]["content"]
        for value in ("true", 1, "yes"):
            _, updated = self.api("POST", "/api/sessions/%s/versions" % session["id"],
                                  {"content": content, "markReviewed": value})
            self.assertEqual(updated["currentVersion"]["reviewStatus"], "borrador", value)

    def test_edicion_con_minutos_incorrectos_se_rechaza_y_no_guarda(self):
        session = generate_and_save(self.api)
        content = copy.deepcopy(session["currentVersion"]["content"])
        content["activities"][0]["minutes"] += 3
        status, body = self.api("POST", "/api/sessions/%s/versions" % session["id"], {"content": content})
        self.assertEqual(status, 422)
        self.assertIn("suman", body["error"]["message"])
        self.assertEqual(len(self.api("GET", "/api/sessions/%s" % session["id"])[1]["versions"]), 1)

    def test_cambiar_duracion_exige_que_los_minutos_cuadren(self):
        session = generate_and_save(self.api)
        content = copy.deepcopy(session["currentVersion"]["content"])
        context = dict(session["currentVersion"]["context"], durationMinutes=50)
        self.assertEqual(self.api("POST", "/api/sessions/%s/versions" % session["id"],
                                  {"content": content, "context": context})[0], 422)
        content["activities"][0]["minutes"] += 5
        content["durationMinutes"] = 50
        status, updated = self.api("POST", "/api/sessions/%s/versions" % session["id"],
                                   {"content": content, "context": context})
        self.assertEqual(status, 201)
        self.assertEqual(updated["currentVersion"]["context"]["durationMinutes"], 50)

    def test_regenerar_no_hereda_la_aprobacion(self):
        session = generate_and_save(self.api, reviewed=True)
        status, updated = self.api("POST", "/api/sessions/%s/regenerate" % session["id"], {"durationMinutes": 30})
        self.assertEqual(status, 201)
        self.assertEqual(updated["currentVersion"]["reviewStatus"], "borrador")
        self.assertEqual(updated["currentVersion"]["content"]["durationMinutes"], 30)
        self.assertEqual(updated["versions"][0]["reviewStatus"], "revisada")

    def test_copia_no_hereda_la_revision_ni_toca_el_original(self):
        session = generate_and_save(self.api, reviewed=True)
        status, clone = self.api("POST", "/api/sessions/%s/copy" % session["id"], {})
        self.assertEqual(status, 201)
        self.assertNotEqual(clone["id"], session["id"])
        self.assertEqual(clone["currentVersion"]["reviewStatus"], "borrador")
        self.assertTrue(clone["title"].startswith("Copia de"))
        self.assertEqual(clone["provenance"]["type"], "copia")
        original = self.api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(original["currentVersion"]["reviewStatus"], "revisada")
        self.assertEqual(len(self.api("GET", "/api/sessions")[1]), 2)

    # --- errores: no se pierde el trabajo ni se simula éxito ----------------
    def test_generador_caido_da_error_claro_y_no_crea_nada(self):
        self.service.generator = support.FailingGenerator()
        status, body = self.api("POST", "/api/drafts/generate", CASE)
        self.assertEqual(status, 502)
        self.assertEqual(body["error"]["code"], "generation_failed")
        self.assertIn("reintentar", body["error"]["message"])
        self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    def test_regenerar_con_fallo_conserva_las_versiones(self):
        session = generate_and_save(self.api, reviewed=True)
        self.service.generator = support.FailingGenerator()
        status, _ = self.api("POST", "/api/sessions/%s/regenerate" % session["id"], {})
        self.assertEqual(status, 502)
        fetched = self.api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(len(fetched["versions"]), 1)
        self.assertEqual(fetched["currentVersion"]["reviewStatus"], "revisada")

    def test_salida_invalida_del_motor_se_rechaza(self):
        for generator in (support.WrongMinutesGenerator(), support.BadReferenceGenerator(),
                          support.UndeclaredMaterialGenerator()):
            with self.subTest(generator=type(generator).__name__):
                self.service.generator = generator
                status, body = self.api("POST", "/api/drafts/generate", CASE)
                self.assertEqual(status, 422)
                self.assertEqual(body["error"]["code"], "invalid_lesson")
                self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    def test_la_sesion_no_queda_a_medias_si_falla_el_guardado(self):
        original = self.service.repo._insert_version
        self.service.repo._insert_version = lambda v: (_ for _ in ()).throw(RuntimeError("disco lleno"))
        try:
            _, draft = self.api("POST", "/api/drafts/generate", CASE)
            status, body = self.api("POST", "/api/sessions", {
                "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"]})
            self.assertEqual(status, 500)
            self.assertNotIn("disco lleno", str(body))
        finally:
            self.service.repo._insert_version = original
        self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    # --- propiedad y permisos ------------------------------------------------
    def test_otra_persona_no_puede_ver_ni_editar_mis_sesiones(self):
        session = generate_and_save(self.api, user="u-demo")
        sid = session["id"]
        content = session["currentVersion"]["content"]
        self.assertEqual(self.api("GET", "/api/sessions/%s" % sid, user="u-otra")[0], 403)
        self.assertEqual(self.api("POST", "/api/sessions/%s/versions" % sid, {"content": content}, "u-otra")[0], 403)
        self.assertEqual(self.api("POST", "/api/sessions/%s/records" % sid, {}, "u-otra")[0], 403)
        self.assertEqual(self.api("POST", "/api/sessions/%s/copy" % sid, {}, "u-otra")[0], 403)
        self.assertEqual(self.api("GET", "/api/sessions", user="u-otra")[1], [])
        self.assertEqual(self.api("GET", "/api/sessions/ses-inexistente")[0], 404)

    # --- registros de aplicación ---------------------------------------------
    def record(self, session, **overrides):
        body = {"declaredDate": "2026-10-30", "activity": "Parejas de escucha",
                "observation": "Observación declarada de prueba", "nextAdjustment": "Dar pasos más cortos"}
        body.update(overrides)
        return self.api("POST", "/api/sessions/%s/records" % session["id"], body)

    def test_registro_simulado_ligado_a_la_version_usada(self):
        session = generate_and_save(self.api, reviewed=True)
        status, rec = self.record(session)
        self.assertEqual(status, 201)
        self.assertTrue(rec["isSimulated"])
        self.assertEqual(rec["versionId"], session["currentVersion"]["id"])
        detail = self.api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertEqual(len(detail["records"]), 1)
        self.assertEqual(self.api("GET", "/api/sessions")[1][0]["recordCount"], 1)

    def test_en_demo_el_cliente_no_puede_declarar_un_registro_como_real(self):
        session = generate_and_save(self.api)
        self.assertTrue(self.record(session, isSimulated=False)[1]["isSimulated"])

    def test_fuera_de_demo_se_respeta_el_indicador(self):
        service = make_service(demo_mode=False)
        try:
            api = Api(service)
            session = generate_and_save(api)
            body = {"declaredDate": "2026-10-30", "activity": "x", "observation": "y"}
            _, rec = api("POST", "/api/sessions/%s/records" % session["id"], body)
            self.assertFalse(rec["isSimulated"])
        finally:
            service.close()

    def test_registro_valida_campos_y_version(self):
        session = generate_and_save(self.api)
        for bad in ({"declaredDate": "ayer"}, {"activity": ""}, {"observation": "  "}):
            status, _ = self.record(session, **bad)
            self.assertEqual(status, 422, bad)
        other = generate_and_save(self.api)
        status, _ = self.record(session, versionId=other["currentVersion"]["id"])
        self.assertEqual(status, 404)
        self.assertEqual(self.api("GET", "/api/sessions/%s" % session["id"])[1]["records"], [])

    def test_guardar_una_sesion_no_equivale_a_clase_aplicada(self):
        session = generate_and_save(self.api, reviewed=True)
        self.assertEqual(session["records"], [])
        self.assertEqual(self.api("GET", "/api/sessions")[1][0]["recordCount"], 0)

    def test_evidencia_esperada_y_observacion_declarada_son_campos_distintos(self):
        session = generate_and_save(self.api)
        self.record(session)
        detail = self.api("GET", "/api/sessions/%s" % session["id"])[1]
        self.assertIn("expectedEvidence", detail["currentVersion"]["content"])
        self.assertNotIn("observation", detail["currentVersion"]["content"])
        self.assertIn("observation", detail["records"][0])

    # --- persistencia real -----------------------------------------------------
    def test_lo_guardado_sobrevive_a_reiniciar(self):
        with TempDb() as db:
            first = make_service(db.path)
            api1 = Api(first)
            session = generate_and_save(api1, reviewed=True)
            api1("POST", "/api/sessions/%s/records" % session["id"],
                 {"declaredDate": "2026-10-30", "activity": "a", "observation": "b"})
            first.close()
            second = make_service(db.path)
            try:
                api2 = Api(second)
                listing = api2("GET", "/api/sessions")[1]
                self.assertEqual([s["id"] for s in listing], [session["id"]])
                detail = api2("GET", "/api/sessions/%s" % session["id"])[1]
                self.assertEqual(detail["currentVersion"]["content"], session["currentVersion"]["content"])
                self.assertEqual(len(detail["records"]), 1)
                # El dato simulado no se duplica al reabrir.
                exp = api2("GET", "/api/experiences")[1]
                self.assertEqual(exp[0]["ratingSummary"]["completeCount"], 3)
            finally:
                second.close()

    # --- Mi tiempo y bienestar --------------------------------------------------
    def test_hoy_ofrece_sesiones_recientes_sin_cifras_de_ahorro(self):
        generate_and_save(self.api)
        status, overview = self.api("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertEqual(len(overview["recentSessions"]), 1)
        self.assertEqual(overview["defaultCase"]["durationMinutes"], 45)
        self.assertNotIn("hoursSaved", overview)
        self.assertFalse(overview["generator"]["isBedrock"])

    def test_preferencias_apagadas_por_defecto_y_validadas(self):
        _, prefs = self.api("GET", "/api/preferences")
        self.assertFalse(prefs["remindersEnabled"])
        self.assertFalse(prefs["sharePublicly"])
        status, saved = self.api("PUT", "/api/preferences", {"remindersEnabled": True, "reminderTime": "07:30"})
        self.assertEqual(status, 200)
        self.assertEqual(self.api("GET", "/api/preferences")[1]["reminderTime"], "07:30")
        self.assertEqual(self.api("PUT", "/api/preferences", {"reminderTime": "25:99"})[0], 422)
        self.assertEqual(self.api("PUT", "/api/preferences", {"remindersEnabled": "si"})[0], 422)
        # Las preferencias son por persona.
        self.assertFalse(self.api("GET", "/api/preferences", user="u-otra")[1]["remindersEnabled"])


class ContractTests(unittest.TestCase):
    """Contratos verificables de las insignias."""

    def setUp(self):
        self.service = make_service()
        self.api = Api(self.service)

    def tearDown(self):
        self.service.close()

    def test_health(self):
        self.assertEqual(self.api("GET", "/health"), (200, {"status": "ok", "team": "T005"}))

    def test_items_persisten_y_se_listan(self):
        nonce = "nonce-8f3a"
        status, created = self.api("POST", "/items", {"value": nonce})
        self.assertIn(status, (200, 201))
        status, item = self.api("GET", "/items/%s" % created["id"])
        self.assertEqual((status, item["value"]), (200, nonce))
        self.assertIn(nonce, [i["value"] for i in self.api("GET", "/items")[1]])
        self.assertEqual(self.api("GET", "/items/no-existe")[0], 404)
        self.assertEqual(self.api("POST", "/items", {})[0], 422)

    def test_job_asincrono_devuelve_el_nonce_invertido(self):
        nonce = "abc123XYZ"
        status, job = self.api("POST", "/jobs", {"input": nonce})
        self.assertEqual(status, 202)
        deadline = time.time() + 12
        result = None
        while time.time() < deadline:
            status, result = self.api("GET", "/jobs/%s" % job["jobId"])
            if result["status"] == "done":
                break
            time.sleep(0.05)
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["output"], nonce[::-1])

    def test_job_con_entrada_invalida_o_inexistente(self):
        self.assertEqual(self.api("POST", "/jobs", {"input": ""})[0], 422)
        self.assertEqual(self.api("POST", "/jobs", {"input": 5})[0], 422)
        self.assertEqual(self.api("GET", "/jobs/job-inexistente")[0], 404)


if __name__ == "__main__":
    unittest.main()
