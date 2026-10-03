from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.visitas.models import Visita


class VisitaAdminTests(TestCase):
    def setUp(self):
        self.administrador = User.objects.create_superuser(
            username="root", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def test_changelist_responde_200(self):
        self.client.force_login(self.administrador)
        respuesta = self.client.get(reverse("admin:visitas_visita_changelist"))
        self.assertEqual(respuesta.status_code, 200)

    def test_estado_y_realizada_en_son_solo_lectura(self):
        request = RequestFactory().get("/admin/visitas/visita/")
        request.user = self.administrador
        solo_lectura = admin.site._registry[Visita].get_readonly_fields(request)
        for campo in ("estado", "realizada_en", "esquema_planilla"):
            self.assertIn(campo, solo_lectura)
