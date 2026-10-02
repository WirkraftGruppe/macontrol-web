import datetime

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios import services
from apps.sitios.models import Sitio


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


class RegenerarQrTests(_BaseSitio):
    def test_regenerar_qr_cambia_codigo_y_borra_fecha_de_impresion(self):
        self.sitio.qr_impreso_el = datetime.date(2026, 1, 1)
        self.sitio.save()
        anterior = self.sitio.qr_codigo
        historial = Sitio.history.filter(id=self.sitio.pk).count()
        nuevo = services.regenerar_qr(self.sitio)
        self.sitio.refresh_from_db()
        self.assertNotEqual(nuevo, anterior)
        self.assertEqual(self.sitio.qr_codigo, nuevo)
        self.assertIsNone(self.sitio.qr_impreso_el)
        self.assertEqual(Sitio.history.filter(id=self.sitio.pk).count(), historial + 1)

    def test_regenerar_qr_guarda_motivo_en_historial(self):
        services.regenerar_qr(self.sitio)
        self.assertEqual(
            self.sitio.history.first().history_change_reason, "Regeneración de QR"
        )

    def test_regenerar_qr_lote_rechaza_mas_del_tope(self):
        sitios = [
            Sitio.objects.create(cliente=self.cliente, nombre=f"Sitio {i}")
            for i in range(services.TOPE_REGENERAR_QR + 1)
        ]
        codigos = [s.qr_codigo for s in sitios]
        with self.assertRaises(ValidationError):
            services.regenerar_qr_lote(sitios)
        for sitio, codigo in zip(sitios, codigos):
            sitio.refresh_from_db()
            self.assertEqual(sitio.qr_codigo, codigo)
