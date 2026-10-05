from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.clientes.models import Cliente
from apps.sitios.models import Plano, PuntoControl, Sitio


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


class PuntoControlTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")

    def test_qr_unico_y_sitio_inactivo_desactiva_puntos(self):
        uno = PuntoControl.objects.create(sitio=self.sitio, nombre="Depósito", orden=1)
        dos = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=2)
        self.assertNotEqual(uno.qr_codigo, dos.qr_codigo)
        self.assertIs(PuntoControl._meta.get_field("qr_codigo").editable, False)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PuntoControl.objects.create(
                    sitio=self.sitio, nombre="Copia", qr_codigo=uno.qr_codigo
                )
        self.sitio.activo = False
        self.sitio.save()
        self.assertFalse(self.sitio.puntos.filter(activo=True).exists())
        self.assertEqual(self.sitio.puntos.count(), 3)

    def test_sitio_nuevo_recibe_punto_general_con_el_mismo_qr(self):
        general = self.sitio.puntos.get()
        self.assertEqual(general.nombre, "General")
        self.assertEqual(general.orden, 0)
        self.assertEqual(general.qr_codigo, self.sitio.qr_codigo)
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        self.assertEqual(self.sitio.puntos.count(), 1)

    def test_clean_rechaza_activo_en_sitio_inactivo_y_plano_ajeno(self):
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        plano = Plano(sitio=otro, nombre="Planta baja")
        plano.ancho_px = plano.alto_px = 10
        Plano.objects.bulk_create([plano])
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", plano=plano)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("plano", error.exception.message_dict)
        Sitio.objects.filter(pk=self.sitio.pk).update(activo=False)
        self.sitio.refresh_from_db()
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", activo=True)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("activo", error.exception.message_dict)

    def test_historial_no_guarda_la_ubicacion_propuesta(self):
        punto = self.sitio.puntos.get()
        with self.assertRaises(FieldDoesNotExist):
            PuntoControl.history.model._meta.get_field("ubicacion_propuesta")
        punto.ubicacion_propuesta = {"lat": -36.1, "lng": -57.8}
        punto.save()
        self.assertEqual(punto.history.count(), 2)
