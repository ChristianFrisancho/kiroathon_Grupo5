"""Mi red · Aprendemos juntos: compartir, valorar, comentar y adaptar."""
import json
import unittest

import support
from support import CASE, Api, generate_and_save, make_service, rating_payload

SEED_ID = "exp-sim-escucha-v1"


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.service = make_service()
        self.api = Api(self.service)

    def tearDown(self):
        self.service.close()

    def rate(self, user, values, exp_id=SEED_ID, **kw):
        return self.api("POST", "/api/experiences/%s/ratings" % exp_id, rating_payload(values, **kw), user)

    def summary(self, exp_id=SEED_ID):
        return self.api("GET", "/api/experiences/%s" % exp_id)[1]["ratingSummary"]

    def share(self, session, user=None, **overrides):
        body = {"confirm": True, "purpose": "Practicar escucha activa", "description": "Parejas",
                "observation": "Las instrucciones fueron largas", "improvement": "Tres pasos"}
        body.update(overrides)
        return self.api("POST", "/api/sessions/%s/share" % session["id"], body, user)

    # --- experiencia simulada y media ---------------------------------------
    def test_experiencia_simulada_muestra_4_4_con_tres_completas(self):
        status, cards = self.api("GET", "/api/experiences")
        self.assertEqual(status, 200)
        card = next(c for c in cards if c["id"] == SEED_ID)
        self.assertTrue(card["isSimulated"])
        s = card["ratingSummary"]
        self.assertEqual((s["average"], s["completeCount"], s["partialCount"], s["label"]), (4.4, 3, 0, "Pocas valoraciones"))
        self.assertEqual(card["purpose"][:9], "Practicar")
        self.assertTrue(card["observation"] and card["improvement"])

    def test_detalle_separa_valoraciones_de_comentarios_de_diseno(self):
        exp = self.api("GET", "/api/experiences/%s" % SEED_ID)[1]
        self.assertEqual(len(exp["ratings"]), 3)
        self.assertEqual(len(exp["comments"]), 1)
        self.assertEqual(exp["comments"][0]["kind"], "diseno")
        self.assertNotIn("reviewerId", json.dumps(exp))
        self.assertEqual(self.api("GET", "/api/experiences/no-existe")[0], 404)

    # --- reglas de valoración ----------------------------------------------------
    def test_valorar_exige_declarar_que_se_uso(self):
        status, body = self.rate("u-demo", [5, 5, 5, 5], used=False)
        self.assertEqual((status, body["error"]["code"]), (422, "use_not_declared"))
        self.assertEqual(self.summary()["completeCount"], 3)

    def test_valoracion_nueva_suma_y_cambia_la_media(self):
        status, body = self.rate("u-demo", [5, 5, 5, 5])
        self.assertEqual(status, 201)
        s = self.summary()
        self.assertEqual(s["completeCount"], 4)
        self.assertEqual(s["average"], 4.6)  # (4,5 + 4,25 + 4,5 + 5) / 4 = 4,5625

    def test_editar_reemplaza_no_duplica(self):
        self.assertEqual(self.rate("u-demo", [5, 5, 5, 5])[0], 201)
        status, body = self.rate("u-demo", [1, 1, 1, 1])
        self.assertEqual(status, 200)
        self.assertFalse(body["created"])
        s = self.summary()
        self.assertEqual(s["completeCount"], 4)
        self.assertEqual(s["average"], 3.6)  # (4,5 + 4,25 + 4,5 + 1) / 4 = 3,5625 -> 3,6
        mine = body["experience"]["myRating"]
        self.assertEqual(mine["clarity"], 1)

    def test_no_puedo_valorarlo_queda_como_parcial_fuera_de_la_media(self):
        before = self.summary()["average"]
        status, body = self.rate("u-demo", [1, 1, 1, None])
        self.assertEqual(status, 201)
        s = self.summary()
        self.assertEqual((s["completeCount"], s["partialCount"], s["average"]), (3, 1, before))
        mine = body["experience"]["myRating"]
        self.assertIsNone(mine["observation"])
        self.assertFalse(mine["complete"])

    def test_criterio_ausente_se_guarda_como_nulo_nunca_como_cero(self):
        payload = {"declaredUse": True, "context": "Aula", "clarity": 4}
        status, body = self.api("POST", "/api/experiences/%s/ratings" % SEED_ID, payload)
        self.assertEqual(status, 201)
        mine = body["experience"]["myRating"]
        self.assertEqual(mine["clarity"], 4)
        for key in ("feasibility", "coherence", "observation"):
            self.assertIsNone(mine[key])

    def test_parcial_se_puede_completar_despues_sin_duplicar(self):
        self.rate("u-demo", [4, 4, 4, None])
        status, _ = self.rate("u-demo", [4, 4, 4, 4])
        self.assertEqual(status, 200)
        s = self.summary()
        self.assertEqual((s["completeCount"], s["partialCount"]), (4, 0))

    def test_valores_invalidos_se_rechazan(self):
        for bad in (0, 6, "5", 3.5, True):
            status, _ = self.rate("u-demo", [bad, 4, 4, 4])
            self.assertEqual(status, 422, bad)
        self.assertEqual(self.rate("u-demo", [None, None, None, None])[0], 422)
        self.assertEqual(self.summary()["completeCount"], 3)

    def test_contexto_de_uso_obligatorio(self):
        self.assertEqual(self.rate("u-demo", [4, 4, 4, 4], context="")[0], 422)

    def test_un_usuario_distinto_si_aporta_otra_valoracion(self):
        self.rate("u-demo", [4, 4, 4, 4])
        self.rate("u-colega", [4, 4, 4, 4])
        self.assertEqual(self.summary()["completeCount"], 5)
        self.assertEqual(self.summary()["label"], "")  # ya no son «pocas»

    def test_el_autor_no_puede_valorar_su_propia_version(self):
        status, body = self.rate("u-sim-autor", [5, 5, 5, 5])
        self.assertEqual((status, body["error"]["code"]), (403, "own_rating"))
        self.assertEqual(self.summary()["completeCount"], 3)

    def test_comentar_no_cuenta_como_valoracion(self):
        status, exp = self.api("POST", "/api/experiences/%s/comments" % SEED_ID, {"text": "Me gustó la idea"})
        self.assertEqual(status, 201)
        self.assertEqual(len(exp["comments"]), 2)
        self.assertEqual(exp["ratingSummary"]["completeCount"], 3)
        self.assertEqual(self.api("POST", "/api/experiences/%s/comments" % SEED_ID, {"text": " "})[0], 422)

    def test_resumen_calculado_localmente_no_se_presenta_como_bedrock(self):
        status, result = self.api("GET", "/api/experiences/%s/summary" % SEED_ID)
        self.assertEqual(status, 200)
        self.assertIn("no es una opinión de Amazon Bedrock", result["text"])
        self.assertFalse(result["generatedBy"]["isBedrock"])
        self.assertIn("3 valoraciones completas", result["text"])

    # --- compartir -----------------------------------------------------------------
    def test_compartir_exige_confirmacion_expresa(self):
        session = generate_and_save(self.api, reviewed=True)
        status, body = self.share(session, confirm=False)
        self.assertEqual((status, body["error"]["code"]), (422, "confirm_required"))
        self.assertEqual(len(self.api("GET", "/api/experiences")[1]), 1)

    def test_no_se_comparte_un_borrador(self):
        session = generate_and_save(self.api, reviewed=False)
        status, body = self.share(session)
        self.assertEqual((status, body["error"]["code"]), (409, "not_reviewed"))

    def test_compartir_crea_copia_sin_registros_privados(self):
        session = generate_and_save(self.api, reviewed=True)
        marker = "SECRETO-REGISTRO-PRIVADO-123"
        self.api("POST", "/api/sessions/%s/records" % session["id"],
                 {"declaredDate": "2026-10-30", "activity": marker, "observation": marker, "nextAdjustment": marker})
        status, exp = self.share(session, observation="Observación elegida por el autor")
        self.assertEqual(status, 201)
        everything = (json.dumps(self.api("GET", "/api/experiences")[1], ensure_ascii=False)
                      + json.dumps(exp, ensure_ascii=False))
        self.assertNotIn(marker, everything)
        self.assertIn("Observación elegida por el autor", everything)
        self.assertTrue(exp["isMine"])
        self.assertEqual(exp["ratingSummary"]["completeCount"], 0)
        # Otra persona ve la copia, pero no la sesión privada.
        self.assertEqual(self.api("GET", "/api/experiences/%s" % exp["id"], user="u-colega")[0], 200)
        self.assertEqual(self.api("GET", "/api/sessions/%s" % session["id"], user="u-colega")[0], 403)

    def test_la_copia_compartida_es_inmutable_aunque_el_autor_edite(self):
        session = generate_and_save(self.api, reviewed=True)
        exp = self.share(session)[1]
        content = json.loads(json.dumps(session["currentVersion"]["content"]))
        content["title"] = "Título nuevo, versión 2"
        self.api("POST", "/api/sessions/%s/versions" % session["id"], {"content": content})
        again = self.api("GET", "/api/experiences/%s" % exp["id"])[1]
        self.assertEqual(again["content"]["title"], session["currentVersion"]["content"]["title"])

    def test_no_se_comparte_dos_veces_la_misma_version(self):
        session = generate_and_save(self.api, reviewed=True)
        self.assertEqual(self.share(session)[0], 201)
        self.assertEqual(self.share(session)[1]["error"]["code"], "already_shared")

    def test_solo_el_dueno_comparte(self):
        session = generate_and_save(self.api, reviewed=True)
        self.assertEqual(self.share(session, user="u-otra")[0], 403)

    def test_la_autoevaluacion_del_autor_de_una_copia_no_cuenta(self):
        session = generate_and_save(self.api, reviewed=True)
        exp = self.share(session)[1]
        status, _ = self.rate("u-demo", [5, 5, 5, 5], exp_id=exp["id"])
        self.assertEqual(status, 403)
        self.assertEqual(self.summary(exp["id"])["completeCount"], 0)

    # --- adaptación y versiones nuevas ------------------------------------------------
    def adapt(self, **overrides):
        body = {"durationMinutes": 30, "materials": "papel", "grade": "Quinto de primaria"}
        body.update(overrides)
        return self.api("POST", "/api/experiences/%s/adapt" % SEED_ID, body)

    def test_adaptar_devuelve_borrador_con_procedencia_sin_persistir(self):
        status, draft = self.adapt()
        self.assertEqual(status, 200)
        self.assertEqual(draft["reviewStatus"], "borrador")
        self.assertEqual(draft["provenance"]["experienceId"], SEED_ID)
        self.assertEqual(draft["provenance"]["authorLabel"], "Docente simulado (autor)")
        self.assertEqual(sum(a["minutes"] for a in draft["content"]["activities"]), 30)
        self.assertEqual(draft["content"]["materials"], ["papel"])
        self.assertIn("Dividir las instrucciones en tres pasos", draft["content"]["activities"][0]["description"])
        self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    def test_adaptacion_guardada_conserva_la_procedencia(self):
        _, draft = self.adapt()
        status, session = self.api("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "provenance": {"experienceId": SEED_ID}, "generatedBy": draft["generatedBy"]})
        self.assertEqual(status, 201)
        self.assertEqual(session["provenance"]["type"], "adaptacion")
        self.assertEqual(session["provenance"]["experienceId"], SEED_ID)
        self.assertEqual(self.api("GET", "/api/sessions")[1][0]["provenance"]["title"],
                         "Escucha activa por parejas (versión 1)")

    def test_procedencia_inventada_se_rechaza(self):
        _, draft = self.adapt()
        status, _ = self.api("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "provenance": {"experienceId": "exp-falsa"}})
        self.assertEqual(status, 422)

    def test_la_version_nueva_no_hereda_la_media_y_la_original_no_cambia(self):
        _, draft = self.adapt()
        _, session = self.api("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "provenance": {"experienceId": SEED_ID}, "markReviewed": True})
        status, new_exp = self.share(session, improvement="Probé con voluntarios")
        self.assertEqual(status, 201)
        self.assertNotEqual(new_exp["id"], SEED_ID)
        s_new = new_exp["ratingSummary"]
        self.assertEqual((s_new["average"], s_new["completeCount"], s_new["label"]), (None, 0, "Sin valoración general"))
        self.assertEqual(self.summary()["average"], 4.4)
        self.assertEqual(self.summary()["completeCount"], 3)

    def test_adaptar_con_fallo_del_motor_da_error_y_no_guarda(self):
        self.service.generator = support.FailingGenerator()
        status, body = self.adapt()
        self.assertEqual((status, body["error"]["code"]), (502, "generation_failed"))
        self.assertEqual(self.api("GET", "/api/sessions")[1], [])

    def test_adaptar_valida_el_contexto(self):
        self.assertEqual(self.adapt(durationMinutes=3)[0], 422)
        self.assertEqual(self.api("POST", "/api/experiences/no-existe/adapt", {})[0], 404)

    # --- reconocimientos ----------------------------------------------------------------
    def test_reconocimientos_cuentan_acciones_comprobables(self):
        before = self.api("GET", "/api/recognitions")[1]
        self.assertEqual((before["sharedExperiences"], before["documentedImprovements"]), (0, 0))
        session = generate_and_save(self.api, reviewed=True)
        content = json.loads(json.dumps(session["currentVersion"]["content"]))
        _, edited = self.api("POST", "/api/sessions/%s/versions" % session["id"],
                             {"content": content, "reason": "Simplifiqué las instrucciones iniciales"})
        self.assertEqual(self.share(edited)[0], 409)  # la edición es un borrador: hay que revisarla primero
        self.api("POST", "/api/sessions/%s/versions/%s/review" % (session["id"], edited["currentVersion"]["id"]))
        self.assertEqual(self.share(edited)[0], 201)
        mine = self.api("GET", "/api/recognitions")[1]
        self.assertEqual(mine["sharedExperiences"], 1)
        self.assertEqual(mine["documentedImprovements"], 1)
        self.assertEqual(mine["adaptedByOthers"], 0)
        # Otra persona adapta la copia compartida: se reconoce al autor.
        exp_id = next(e["id"] for e in self.api("GET", "/api/experiences")[1] if e["isMine"])
        _, draft = self.api("POST", "/api/experiences/%s/adapt" % exp_id, {}, "u-colega")
        self.api("POST", "/api/sessions", {
            "moduleId": draft["module"]["id"], "context": draft["context"], "content": draft["content"],
            "provenance": {"experienceId": exp_id}}, "u-colega")
        self.assertEqual(self.api("GET", "/api/recognitions")[1]["adaptedByOthers"], 1)
        self.assertNotIn("calidad", self.api("GET", "/api/recognitions")[1]["text"])


if __name__ == "__main__":
    unittest.main()
