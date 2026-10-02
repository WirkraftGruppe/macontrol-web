from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios.models import Sitio


class SitioAdminTests(TestCase):
    def test_accion_regenerar_qr_cambia_el_codigo(self):
        admin = User.objects.create_superuser(username="root", password="x")
        self.client.force_login(admin)
        cliente = Cliente.objects.create(razon_social="ACME")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        anterior = sitio.qr_codigo
        respuesta = self.client.post(
            reverse("admin:sitios_sitio_changelist"),
            {"action": "regenerar_qr", "_selected_action": [sitio.pk]},
        )
        self.assertEqual(respuesta.status_code, 302)
        sitio.refresh_from_db()
        self.assertNotEqual(sitio.qr_codigo, anterior)
