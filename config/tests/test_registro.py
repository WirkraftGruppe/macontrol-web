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


def _filtrar(msg, args=(), **extra):
    r = _record(msg, args, **extra)
    FiltroDatosPersonales().filter(r)
    return r


class FiltroAuditoriaTests(SimpleTestCase):
    def test_claves_por_subcadena_y_sin_mayusculas(self):
        r = _filtrar(
            "%(a)s",
            (
                {
                    "Password": 1,
                    "CUIT": 2,
                    "refresh": 3,
                    "new_password1": 4,
                    "HTTP_AUTHORIZATION": 5,
                    "Teléfono_contacto": 6,
                    "nombre": "ok",
                },
            ),
        )
        self.assertEqual(r.args["nombre"], "ok")
        self.assertEqual(
            [v for k, v in r.args.items() if k != "nombre"], ["[oculto]"] * 6
        )

    def test_limpieza_recursiva_en_args(self):
        r = _filtrar("%s", ([{"cuit": "S6"}],))
        self.assertEqual(r.args, ([{"cuit": "[oculto]"}],))
        r = _filtrar("%s %s", ("x", {"latitud": "S7"}))
        self.assertEqual(r.args, ("x", {"latitud": "[oculto]"}))
        r = _filtrar("%s", ({"a": {"b": ({"token": "S"},)}},))
        self.assertEqual(r.args["a"]["b"], ({"token": "[oculto]"},))

    def test_modelo_dentro_de_lista(self):
        usuario = get_user_model()(pk=3)
        r = _filtrar("%s", ([usuario],))
        self.assertEqual(r.getMessage(), "['<accounts.User pk=3>']")

    def test_extra_con_estructuras_anidadas(self):
        r = _filtrar("m", datos=[{"token": "S15"}], access="x")
        self.assertEqual(r.datos, [{"token": "[oculto]"}])
        self.assertEqual(r.access, "[oculto]")

    def test_profundidad_maxima_oculta(self):
        anidado = "S"
        for _ in range(10):
            anidado = [anidado]
        r = _filtrar("%s", (anidado,))
        self.assertNotIn("S", r.getMessage())
        self.assertIn("[oculto]", r.getMessage())

    def test_msg_que_no_es_texto(self):
        r = _filtrar({"cuit": "S1"})
        self.assertEqual(r.getMessage(), "{'cuit': '[oculto]'}")
        usuario = get_user_model()(pk=9)
        self.assertEqual(_filtrar(usuario).getMessage(), "<accounts.User pk=9>")

    def test_loggers_de_django_usan_solo_el_handler_filtrado(self):
        for nombre in ("django", "django.server"):
            cfg = settings.LOGGING["loggers"][nombre]
            self.assertEqual(cfg["handlers"], ["consola"])
            self.assertIs(cfg["propagate"], False)
