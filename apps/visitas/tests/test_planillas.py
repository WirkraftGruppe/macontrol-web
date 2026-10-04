from django.test import SimpleTestCase

from apps.visitas.planillas import MAX_LARGO_TEXTO, validar_datos


def campo(clave, tipo, obligatorio=False, opciones=None):
    return {
        "clave": clave,
        "tipo": tipo,
        "obligatorio": obligatorio,
        "opciones": opciones or [],
    }


ESQUEMA = [
    campo("zona", "texto", obligatorio=True),
    campo("cantidad", "numero"),
    campo("hubo_actividad", "booleano"),
    campo("nivel", "opcion", opciones=["bajo", "alto"]),
    campo("plagas", "opcion_multiple", opciones=["ratas", "cucarachas"]),
    campo("proxima", "fecha"),
]


class ValidarDatosTests(SimpleTestCase):
    def test_obligatorio_faltante(self):
        self.assertEqual(
            validar_datos(ESQUEMA, {}), {"zona": ["Este campo es obligatorio."]}
        )
        self.assertIn("zona", validar_datos(ESQUEMA, {"zona": None}))
        self.assertIn("datos", validar_datos(ESQUEMA, []))

    def test_tipo_incorrecto(self):
        invalidos = {
            "zona": 5,
            "cantidad": True,
            "hubo_actividad": "si",
            "plagas": "ratas",
            "proxima": "2026-02-30",
        }
        errores = validar_datos(ESQUEMA, invalidos)
        self.assertEqual(set(errores), set(invalidos))
        self.assertIn(
            "cantidad", validar_datos(ESQUEMA, {"zona": "a", "cantidad": "3"})
        )
        self.assertIn(
            "proxima", validar_datos(ESQUEMA, {"zona": "a", "proxima": 20260101})
        )

    def test_opcion_fuera_de_lista(self):
        base = {"zona": "a"}
        self.assertIn("nivel", validar_datos(ESQUEMA, {**base, "nivel": "medio"}))
        self.assertIn("nivel", validar_datos(ESQUEMA, {**base, "nivel": ["bajo"]}))
        self.assertIn("plagas", validar_datos(ESQUEMA, {**base, "plagas": ["moscas"]}))
        self.assertIn(
            "plagas", validar_datos(ESQUEMA, {**base, "plagas": ["ratas", "ratas"]})
        )

    def test_clave_desconocida(self):
        errores = validar_datos(ESQUEMA, {"zona": "a", "otra": 1})
        self.assertEqual(errores, {"otra": ["Campo desconocido en esta planilla."]})

    def test_datos_validos(self):
        datos = {
            "zona": "depósito",
            "cantidad": 3.5,
            "hubo_actividad": False,
            "nivel": "alto",
            "plagas": ["ratas", "cucarachas"],
            "proxima": "2026-11-01",
        }
        self.assertEqual(validar_datos(ESQUEMA, datos), {})
        self.assertEqual(validar_datos(ESQUEMA, {"zona": "a"}), {})
        self.assertEqual(validar_datos([], {}), {})

    def test_numero_no_finito_se_rechaza(self):
        for valor in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(valor=valor):
                errores = validar_datos(ESQUEMA, {"zona": "a", "cantidad": valor})
                self.assertEqual(errores, {"cantidad": ["Debe ser un número."]})

    def test_texto_demasiado_largo_se_rechaza(self):
        self.assertEqual(validar_datos(ESQUEMA, {"zona": "x" * MAX_LARGO_TEXTO}), {})
        errores = validar_datos(ESQUEMA, {"zona": "x" * (MAX_LARGO_TEXTO + 1)})
        self.assertEqual(set(errores), {"zona"})

    def test_tipo_de_campo_desconocido_da_error(self):
        esquema = [campo("raro", "inventado")]
        errores = validar_datos(esquema, {"raro": 1})
        self.assertEqual(errores, {"raro": ["Tipo de campo desconocido."]})
