"""Ajustes de ingreso: proxies de confianza y cupos de intentos fallidos."""

import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import base


class AjustesIngresoTests(SimpleTestCase):
    def test_num_proxies_por_defecto_es_cero(self):
        entorno = {k: v for k, v in os.environ.items() if k != "NUM_PROXIES"}
        with mock.patch.dict(os.environ, entorno, clear=True):
            self.assertEqual(base.leer_num_proxies(), 0)

    def test_num_proxies_invalido_lanza_error(self):
        for valor in ("abc", "-1", "1.5"):
            with mock.patch.dict(os.environ, {"NUM_PROXIES": valor}):
                with self.assertRaises(ImproperlyConfigured):
                    base.leer_num_proxies()
        with mock.patch.dict(os.environ, {"NUM_PROXIES": "2"}):
            self.assertEqual(base.leer_num_proxies(), 2)

    def test_drf_usa_el_mismo_num_proxies(self):
        self.assertEqual(settings.REST_FRAMEWORK["NUM_PROXIES"], settings.NUM_PROXIES)

    def test_cupos_de_ingreso_definidos(self):
        self.assertEqual(settings.INTENTOS_FALLIDOS_POR_IP, 20)
        self.assertEqual(settings.VENTANA_MINUTOS, 15)
        self.assertEqual(settings.FALLOS_POR_USUARIO_E_IP, 5)
        self.assertEqual(settings.FALLOS_POR_USUARIO, 50)
        self.assertEqual(settings.VENTANA_USUARIO_MINUTOS, 60)
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["token"], "10/min"
        )
