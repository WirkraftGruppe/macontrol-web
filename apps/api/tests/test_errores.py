"""Formato uniforme de errores de la API."""

from django.core.exceptions import ValidationError as ErrorDjango
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from apps.api.excepciones import manejar_excepcion


class FormatoErrorTests(TestCase):
    def test_error_de_validacion_tiene_detalle_y_campos(self):
        respuesta = manejar_excepcion(
            ValidationError({"nombre": ["Obligatorio."], "otro": "Mal."}), {}
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["campos"], {"nombre": ["Obligatorio."], "otro": ["Mal."]}
        )
        self.assertIsInstance(respuesta.data["detalle"], str)

    def test_401_tiene_detalle(self):
        respuesta = self.client.get("/api/v1/")
        self.assertEqual(respuesta.status_code, 401)
        cuerpo = respuesta.json()
        self.assertTrue(cuerpo["detalle"])
        self.assertEqual(cuerpo["campos"], {})

    def test_validation_error_de_django_es_400(self):
        respuesta = manejar_excepcion(ErrorDjango("Mal hecho."), {})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["detalle"], "Mal hecho.")


class ExcepcionInternaTests(SimpleTestCase):
    def test_excepcion_interna_no_expone_su_texto(self):
        with self.assertLogs("apps.api.excepciones", level="ERROR"):
            respuesta = manejar_excepcion(RuntimeError("secreto-interno"), {})
        self.assertEqual(respuesta.status_code, 500)
        self.assertNotIn("secreto-interno", str(respuesta.data))
        self.assertEqual(respuesta.data["campos"], {})
