"""Tablero del panel: contadores y proyectos más urgentes."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import UMBRAL_PROXIMA_DIAS, Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Visita
from apps.visitas.tests.test_models import crear_revision


class TableroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user("emp", password="clave-segura-123")
        cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        cls.servicio = TipoServicio.objects.create(nombre="Desinsectación", slug="d")
        cls.hoy = timezone.localdate()

    def proyecto(self, dias, estado=Proyecto.Estado.ACTIVO, titulo="P"):
        proxima = None if dias is None else self.hoy + timedelta(days=dias)
        return Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=self.servicio,
            titulo=titulo,
            estado=estado,
            proxima_visita=proxima,
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
        )

    def visita(self, **campos):
        proyecto = campos.pop("proyecto", None) or self.proyecto(None)
        return Visita.objects.create(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.MANUAL,
            **campos,
        )

    def test_contadores(self):
        self.proyecto(-1)
        self.proyecto(-30)
        self.proyecto(-1, estado=Proyecto.Estado.PAUSADO)
        self.proyecto(0)
        self.proyecto(UMBRAL_PROXIMA_DIAS)
        self.proyecto(UMBRAL_PROXIMA_DIAS + 1)
        self.proyecto(None)
        self.visita(programada_para=self.hoy)
        self.visita(programada_para=self.hoy + timedelta(days=1))
        self.visita(programada_para=self.hoy, estado=Visita.Estado.CANCELADA)
        self.visita(incidencia=True)
        self.visita(incidencia=True)
        self.visita(incidencia=True, incidencia_revisada_en=timezone.now())

        self.client.force_login(self.admin)
        respuesta = self.client.get("/panel/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["contadores"],
            {
                "vencidos": 2,
                "proximos": 2,
                "pendientes_hoy": 1,
                "incidencias": 2,
                "incidencias_ubicacion": 0,
            },
        )

    def test_cuenta_incidencias_de_ubicacion(self):
        self.visita(incidencia_ubicacion=True)
        en_revision = self.visita()
        for _ in range(2):  # dos revisiones con incidencia: la visita cuenta una vez
            crear_revision(en_revision, incidencia_ubicacion=True)
        revisada = self.visita(
            incidencia_ubicacion=True, incidencia_revisada_en=timezone.now()
        )
        crear_revision(revisada, incidencia_ubicacion=True)
        self.visita()  # sin incidencia

        self.client.force_login(self.admin)
        respuesta = self.client.get("/panel/")

        self.assertEqual(respuesta.context["contadores"]["incidencias_ubicacion"], 2)
        self.assertContains(respuesta, "Incidencias de ubicación")

    def test_diez_mas_urgentes_en_orden(self):
        for dias in range(12, 0, -1):
            self.proyecto(dias - 6, titulo=f"P{dias}")
        self.proyecto(-20, estado=Proyecto.Estado.FINALIZADO, titulo="Finalizado")
        self.proyecto(None, titulo="Sin fecha")

        self.client.force_login(self.admin)
        urgentes = self.client.get("/panel/").context["urgentes"]

        self.assertEqual(len(urgentes), 10)
        self.assertEqual([p.titulo for p in urgentes], [f"P{n}" for n in range(1, 11)])
