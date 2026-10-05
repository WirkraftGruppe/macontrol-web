import datetime

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios import services
from apps.sitios.models import PuntoControl, Sitio


class _BaseSitio(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")


class SuprimirSitioTests(_BaseSitio):
    def test_suprimir_borra_sitio_e_historial(self):
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        pk = self.sitio.pk
        self.assertEqual(Sitio.history.filter(id=pk).count(), 2)
        services.suprimir_sitio(self.sitio)
        self.assertFalse(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 0)

    def test_borra_historial_de_proyectos(self):
        tipo = TipoServicio.objects.create(nombre="Desratización", slug="desratizacion")
        encargado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO, is_active=True
        )
        proyecto = Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=tipo,
            titulo="Control",
            encargado_inicial=encargado,
            encargado_actual=encargado,
        )
        proyecto.titulo = "Control mensual"
        proyecto.save()
        pk = self.sitio.pk
        self.assertEqual(Proyecto.history.filter(sitio_id=pk).count(), 2)
        proyecto.delete()
        services.suprimir_sitio(self.sitio)
        self.assertEqual(Proyecto.history.filter(sitio_id=pk).count(), 0)

    def test_suprimir_con_proyectos_no_borra_nada(self):
        tipo = TipoServicio.objects.create(nombre="Desratización", slug="desratizacion")
        encargado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO, is_active=True
        )
        Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=tipo,
            titulo="Control",
            encargado_inicial=encargado,
            encargado_actual=encargado,
        )
        pk = self.sitio.pk
        with self.assertRaises(ProtectedError):
            services.suprimir_sitio(self.sitio)
        self.assertTrue(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 1)

    def test_suprimir_sitios_informa_los_que_tienen_proyectos(self):
        tipo = TipoServicio.objects.create(nombre="Desratización", slug="desratizacion")
        encargado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO, is_active=True
        )
        con_proyecto = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        Proyecto.objects.create(
            sitio=con_proyecto,
            tipo_servicio=tipo,
            titulo="Control",
            encargado_inicial=encargado,
            encargado_actual=encargado,
        )
        pk_libre = self.sitio.pk
        resultado = services.suprimir_sitios([self.sitio, con_proyecto])
        self.assertEqual(resultado, (1, [con_proyecto]))
        self.assertFalse(Sitio.objects.filter(pk=pk_libre).exists())
        self.assertEqual(Sitio.history.filter(id=pk_libre).count(), 0)
        self.assertTrue(Sitio.objects.filter(pk=con_proyecto.pk).exists())

    def test_suprimir_borra_puntos_y_su_historial(self):
        pk = self.sitio.pk
        self.assertEqual(PuntoControl.history.filter(sitio_id=pk).count(), 1)
        services.suprimir_sitio(self.sitio)
        self.assertFalse(PuntoControl.objects.filter(sitio_id=pk).exists())
        self.assertEqual(PuntoControl.history.filter(sitio_id=pk).count(), 0)


class RegenerarQrPuntoTests(_BaseSitio):
    def setUp(self):
        super().setUp()
        self.general = self.sitio.puntos.get()

    def test_regenerar_qr_cambia_codigo_y_borra_fecha_de_impresion(self):
        self.general.qr_impreso_el = datetime.date(2026, 1, 1)
        self.general.save()
        anterior = self.general.qr_codigo
        historial = PuntoControl.history.filter(id=self.general.pk).count()
        nuevo = services.regenerar_qr(self.general)
        self.general.refresh_from_db()
        self.assertNotEqual(nuevo, anterior)
        self.assertEqual(self.general.qr_codigo, nuevo)
        self.assertIsNone(self.general.qr_impreso_el)
        self.assertEqual(
            PuntoControl.history.filter(id=self.general.pk).count(), historial + 1
        )

    def test_regenerar_qr_guarda_motivo_en_historial(self):
        services.regenerar_qr(self.general)
        self.assertEqual(
            self.general.history.first().history_change_reason, "Regeneración de QR"
        )

    def test_regenerar_el_general_copia_el_codigo_al_sitio(self):
        nuevo = services.regenerar_qr(self.general)
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.qr_codigo, nuevo)

    def test_regenera_solo_el_punto_y_respeta_tope(self):
        otro = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        codigo_general = self.general.qr_codigo
        nuevo = services.regenerar_qr(otro)
        self.general.refresh_from_db()
        self.sitio.refresh_from_db()
        otro.refresh_from_db()
        self.assertEqual(otro.qr_codigo, nuevo)
        self.assertNotEqual(nuevo, codigo_general)
        self.assertEqual(self.general.qr_codigo, codigo_general)
        self.assertEqual(self.sitio.qr_codigo, codigo_general)
        puntos = [
            PuntoControl.objects.create(sitio=self.sitio, nombre=f"P{i}", orden=i + 2)
            for i in range(services.TOPE_REGENERAR_QR + 1)
        ]
        codigos = [p.qr_codigo for p in puntos]
        with self.assertRaises(ValidationError):
            services.regenerar_qr_lote(puntos)
        for punto, codigo in zip(puntos, codigos):
            punto.refresh_from_db()
            self.assertEqual(punto.qr_codigo, codigo)
        self.assertEqual(services.regenerar_qr_lote(puntos[:3]), 3)
