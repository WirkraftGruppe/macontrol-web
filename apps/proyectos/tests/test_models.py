from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio


class ProyectoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cliente = Cliente.objects.create(razon_social="ACME")
        cls.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        cls.tipo = TipoServicio.objects.create(
            nombre="Control de roedores", slug="roedores-test"
        )
        cls.empleado = User.objects.create_user(
            username="empleado1", password="x", rol=User.Rol.EMPLEADO
        )
        cls.admin = User.objects.create_user(
            username="admin1", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def _proyecto(self, **extra):
        datos = {
            "sitio": self.sitio,
            "tipo_servicio": self.tipo,
            "titulo": "Roedores mensual",
            "encargado_inicial": self.empleado,
            "encargado_actual": self.empleado,
        }
        datos.update(extra)
        return Proyecto.objects.create(**datos)

    def test_estado_visita_vencida_cuando_proxima_visita_paso(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.assertEqual(self._proyecto(proxima_visita=ayer).estado_visita, "vencida")

    def test_estado_visita_sin_programar_sin_proxima_visita(self):
        self.assertEqual(self._proyecto().estado_visita, "sin_programar")

    def test_estado_visita_proxima_dentro_de_siete_dias(self):
        hoy = timezone.localdate()
        for fecha in (hoy, hoy + timedelta(days=7)):
            self.assertEqual(
                self._proyecto(proxima_visita=fecha).estado_visita, "proxima"
            )

    def test_estado_visita_al_dia_mas_alla_de_siete_dias(self):
        fecha = timezone.localdate() + timedelta(days=8)
        self.assertEqual(self._proyecto(proxima_visita=fecha).estado_visita, "al_dia")

    def test_encargado_debe_ser_empleado(self):
        invalido = self._proyecto()
        invalido.encargado_actual = self.admin
        with self.assertRaises(ValidationError) as ctx:
            invalido.full_clean()
        self.assertIn("encargado_actual", ctx.exception.message_dict)
        valido = self._proyecto()
        valido.full_clean()

    def test_historial_registra_cambios(self):
        proyecto = self._proyecto()
        proyecto.titulo = "Roedores quincenal"
        proyecto.save()
        self.assertEqual(proyecto.history.count(), 2)
