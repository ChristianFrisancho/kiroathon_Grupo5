import unittest

import support  # noqa: F401  (prepara sys.path)

from aulalista import scoring
from aulalista.errors import ApiError


def rating(values, **extra):
    keys = ("clarity", "feasibility", "coherence", "observation")
    data = dict(zip(keys, values))
    data.update(extra)
    return data


class ScoringTests(unittest.TestCase):
    def test_ejemplo_simulado_da_4_4(self):
        summary = scoring.summarize([rating([5, 4, 4, 5]), rating([4, 4, 5, 4]), rating([5, 5, 4, 4])])
        self.assertEqual(summary["average"], 4.4)
        self.assertEqual(summary["completeCount"], 3)
        self.assertEqual(summary["partialCount"], 0)
        self.assertEqual(summary["label"], "Pocas valoraciones")

    def test_sin_valoraciones_completas(self):
        summary = scoring.summarize([])
        self.assertIsNone(summary["average"])
        self.assertEqual(summary["completeCount"], 0)
        self.assertEqual(summary["label"], "Sin valoración general")

    def test_ausente_no_se_convierte_en_cero(self):
        summary = scoring.summarize([rating([5, 5, 5, None])])
        self.assertIsNone(summary["average"])
        self.assertEqual(summary["completeCount"], 0)
        self.assertEqual(summary["partialCount"], 1)

    def test_parciales_no_alteran_la_media_de_completas(self):
        base = [rating([5, 4, 4, 5]), rating([4, 4, 5, 4]), rating([5, 5, 4, 4])]
        with_partial = base + [rating([1, 1, 1, None])]
        self.assertEqual(scoring.summarize(with_partial)["average"], scoring.summarize(base)["average"])
        self.assertEqual(scoring.summarize(with_partial)["partialCount"], 1)

    def test_cinco_o_mas_completas_no_son_pocas(self):
        summary = scoring.summarize([rating([4, 4, 4, 4])] * 5)
        self.assertEqual(summary["label"], "")
        self.assertEqual(summary["average"], 4.0)

    def test_redondeo_half_up_a_un_decimal(self):
        # 4,25 debe mostrarse 4,3 (round() de Python daría 4,2).
        self.assertEqual(scoring.summarize([rating([4, 4, 4, 5])])["average"], 4.3)

    def test_media_de_medias_no_de_valores_sueltos(self):
        # Medias por valoración: 5,0 y 3,0 -> 4,0.
        self.assertEqual(scoring.summarize([rating([5, 5, 5, 5]), rating([3, 3, 3, 3])])["average"], 4.0)

    def test_parse_values_ausente_es_none(self):
        values = scoring.parse_values({"clarity": 5})
        self.assertEqual(values, {"clarity": 5, "feasibility": None, "coherence": None, "observation": None})

    def test_parse_values_rechaza_fuera_de_rango_y_tipos_raros(self):
        for bad in (0, 6, -1, "5", 4.5, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ApiError) as ctx:
                    scoring.parse_values({"clarity": bad})
                self.assertEqual(ctx.exception.status, 422)

    def test_is_complete(self):
        self.assertTrue(scoring.is_complete(rating([1, 2, 3, 4])))
        self.assertFalse(scoring.is_complete(rating([1, 2, 3, None])))

    def test_medias_por_criterio_solo_con_completas(self):
        summary = scoring.summarize([rating([5, 4, 4, 5]), rating([3, 3, 3, None])])
        self.assertEqual(summary["criteriaMeans"]["clarity"], 5.0)


if __name__ == "__main__":
    unittest.main()
