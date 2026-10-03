"""Filtro de logging de datos personales."""

import io
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from config.registro import FiltroDatosPersonales


def _record(msg, args, **extra):
    r = logging.LogRecord("t", logging.INFO, __file__, 1, msg, args, None)
    for k, v in extra.items():
        setattr(r, k, v)
    return r


class RegistroTests(SimpleTestCase):
    def test_filtro_oculta_claves_sensibles(self):
        r = _record(
            "%(password)s",
            (
                {
                    "password": "x",
                    "token": "t",
                    "latitud": 1,
                    "longitud": 2,
                    "cuit": "3",
                    "nombre": "ok",
                },
            ),
            token="abc",
            otro="visible",
        )
        FiltroDatosPersonales().filter(r)
        self.assertEqual(r.args["password"], "[oculto]")
        for clave in ("token", "latitud", "longitud", "cuit"):
            self.assertEqual(r.args[clave], "[oculto]")
        self.assertEqual(r.args["nombre"], "ok")
        self.assertEqual(r.token, "[oculto]")
        self.assertEqual(r.otro, "visible")
        r2 = _record("%s", ({"password": "x"}, "y"))
        FiltroDatosPersonales().filter(r2)
        self.assertEqual(r2.args[0]["password"], "[oculto]")
        self.assertEqual(r2.args[1], "y")

    def test_filtro_reemplaza_instancias_de_modelo(self):
        usuario = get_user_model()(pk=7, username="x")
        r = _record("usuario %s", (usuario,))
        FiltroDatosPersonales().filter(r)
        self.assertEqual(r.getMessage(), "usuario <accounts.User pk=7>")

    def test_handler_de_consola_usa_el_filtro(self):
        config = settings.LOGGING
        self.assertEqual(
            config["filters"]["datos_personales"]["()"],
            "config.registro.FiltroDatosPersonales",
        )
        self.assertIn("datos_personales", config["handlers"]["consola"]["filters"])
        flujo = io.StringIO()
        handler = logging.StreamHandler(flujo)
        handler.addFilter(FiltroDatosPersonales())
        log = logging.getLogger("prueba.registro")
        log.addHandler(handler)
        self.addCleanup(log.removeHandler, handler)
        log.warning("datos %(password)s", {"password": "secreto"})
        self.assertNotIn("secreto", flujo.getvalue())
        self.assertIn("[oculto]", flujo.getvalue())
