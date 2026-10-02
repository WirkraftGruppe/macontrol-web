from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.clientes.models import Cliente
from apps.sitios.models import Sitio


class SitioTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")

    def _sitio(self, nombre, **extra):
        return Sitio.objects.create(cliente=self.cliente, nombre=nombre, **extra)

    def test_qr_codigo_se_genera_y_es_unico(self):
        uno = self._sitio("Planta 1")
        dos = self._sitio("Planta 2")
        self.assertIsNotNone(uno.qr_codigo)
        self.assertIsNotNone(dos.qr_codigo)
        self.assertNotEqual(uno.qr_codigo, dos.qr_codigo)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._sitio("Planta 3", qr_codigo=uno.qr_codigo)

    def test_qr_codigo_no_es_editable(self):
        self.assertIs(Sitio._meta.get_field("qr_codigo").editable, False)

    def test_historial_registra_cambios(self):
        sitio = self._sitio("Planta 1")
        sitio.nombre = "Planta Norte"
        sitio.save()
        self.assertEqual(sitio.history.count(), 2)

    def test_historial_no_guarda_contacto_ni_telefono(self):
        modelo = Sitio.history.model
        for campo in ("contacto_en_sitio", "telefono_en_sitio"):
            with self.assertRaises(FieldDoesNotExist):
                modelo._meta.get_field(campo)
