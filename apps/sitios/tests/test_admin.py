from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios import services
from apps.sitios.models import Sitio


class SitioAdminTests(TestCase):
    def setUp(self):
        self.administrador = User.objects.create_superuser(
            username="root", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")
        self.url = reverse("admin:sitios_sitio_changelist")

    def test_accion_regenerar_qr_cambia_el_codigo(self):
        self.client.force_login(self.administrador)
        anterior = self.sitio.qr_codigo
        respuesta = self.client.post(
            self.url,
            {
                "action": "regenerar_qr",
                "_selected_action": [self.sitio.pk],
                "confirmado": "si",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.sitio.refresh_from_db()
        self.assertNotEqual(self.sitio.qr_codigo, anterior)

    def test_staff_sin_rol_administrador_no_ve_las_acciones(self):
        usuario = User.objects.create_user(
            username="staff", password="x", rol=User.Rol.EMPLEADO, is_staff=True
        )
        permisos = Permission.objects.filter(
            content_type__app_label="sitios",
            codename__in=["view_sitio", "change_sitio", "delete_sitio"],
        )
        usuario.user_permissions.add(*permisos)
        request = RequestFactory().get(self.url)
        request.user = User.objects.get(pk=usuario.pk)
        acciones = admin.site._registry[Sitio].get_actions(request)
        self.assertNotIn("regenerar_qr", acciones)
        self.assertNotIn("suprimir_datos", acciones)

        self.client.force_login(usuario)
        anterior = self.sitio.qr_codigo
        self.client.post(
            self.url,
            {
                "action": "regenerar_qr",
                "_selected_action": [self.sitio.pk],
                "confirmado": "si",
            },
        )
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.qr_codigo, anterior)

    def test_regenerar_qr_pide_confirmacion(self):
        self.client.force_login(self.administrador)
        anterior = self.sitio.qr_codigo
        respuesta = self.client.post(
            self.url, {"action": "regenerar_qr", "_selected_action": [self.sitio.pk]}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "admin/sitios/sitio/confirmar_accion.html")
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.qr_codigo, anterior)

    def test_suprimir_datos_pide_confirmacion(self):
        self.client.force_login(self.administrador)
        respuesta = self.client.post(
            self.url, {"action": "suprimir_datos", "_selected_action": [self.sitio.pk]}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "admin/sitios/sitio/confirmar_accion.html")
        self.assertTrue(Sitio.objects.filter(pk=self.sitio.pk).exists())

    def test_suprimir_datos_borra_sitio_e_historial(self):
        self.client.force_login(self.administrador)
        pk = self.sitio.pk
        respuesta = self.client.post(
            self.url,
            {"action": "suprimir_datos", "_selected_action": [pk], "confirmado": "si"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 0)

    def test_revertir_sitio_desde_historial_esta_prohibido(self):
        self.client.force_login(self.administrador)
        anterior = self.sitio.qr_codigo
        nuevo = services.regenerar_qr(self.sitio)
        version_anterior = Sitio.history.filter(id=self.sitio.pk).order_by(
            "history_date", "history_id"
        )[0]
        self.assertEqual(version_anterior.qr_codigo, anterior)
        url = reverse(
            "admin:sitios_sitio_simple_history",
            args=[self.sitio.pk, version_anterior.history_id],
        )

        respuesta = self.client.post(
            url,
            {
                "cliente": self.cliente.pk,
                "nombre": "Planta 1",
                "sector": self.sitio.sector,
                "activo": "on",
            },
        )

        self.assertEqual(respuesta.status_code, 403)
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.qr_codigo, nuevo)
        self.assertEqual(self.client.get(url).status_code, 200)
