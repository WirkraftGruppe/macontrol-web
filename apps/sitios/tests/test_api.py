import datetime
import uuid

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Visita


class ResolverQRTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(
            cliente=self.cliente,
            nombre="Planta 1",
            direccion="Calle 1",
            localidad="Castelli",
            latitud="-36.100000",
            longitud="-57.800000",
            contacto_en_sitio="Juan Contacto",
            telefono_en_sitio="2245-000000",
            horario_acceso="8 a 12",
            notas="Nota interna",
        )
        self.punto = self.sitio.puntos.get()
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.otro = User.objects.create_user(
            username="otro", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.proyecto = self._proyecto("Control")
        self.cliente_api = APIClient()
        self.cliente_api.force_authenticate(self.empleado)

    def _proyecto(self, titulo, **extra):
        return Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=self.tipo,
            titulo=titulo,
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
            **extra,
        )

    def _visita(self, proyecto, empleado, dias):
        return Visita.objects.create(
            proyecto=proyecto,
            empleado=empleado,
            origen=Visita.Origen.MANUAL,
            programada_para=datetime.date(2026, 1, 1) + datetime.timedelta(days=dias),
        )

    def _resolver(self, codigo=None, cliente=None):
        codigo = codigo or self.punto.qr_codigo
        return (cliente or self.cliente_api).post(f"/api/v1/qr/{codigo}/resolver/")

    def test_qr_valido_devuelve_proyectos_y_esquema(self):
        self._proyecto("Pausado", estado=Proyecto.Estado.PAUSADO)
        r = self._resolver()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["sitio"],
            {"nombre": "Planta 1", "direccion": "Calle 1", "localidad": "Castelli"},
        )
        self.assertEqual(r.json()["cliente"], {"razon_social": "ACME"})
        proyectos = r.json()["proyectos"]
        self.assertEqual(len(proyectos), 1)
        self.assertEqual(proyectos[0]["id"], self.proyecto.id)
        self.assertEqual(
            proyectos[0]["tipo_servicio"],
            {"id": self.tipo.id, "nombre": "Desratización"},
        )
        self.assertEqual(proyectos[0]["esquema_planilla"], self.tipo.esquema_planilla())
        self.assertIsNone(proyectos[0]["visita_pendiente_propia"])

    def test_qr_inactivo_da_404_igual_que_inexistente(self):
        self.sitio.activo = False
        self.sitio.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inexistente.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())

    def test_qr_de_punto_inactivo_da_404(self):
        self.punto.activo = False
        self.punto.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())
        self.assertEqual(self.sitio.puntos.filter(activo=True).count(), 0)

    def test_cliente_inactivo_da_404(self):
        self.cliente.activo = False
        self.cliente.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())

    def test_administrador_no_resuelve_qr(self):
        cliente = APIClient()
        cliente.force_authenticate(self.admin)
        self.assertEqual(self._resolver(cliente=cliente).status_code, 403)
        self.assertEqual(self._resolver(cliente=APIClient()).status_code, 401)

    def test_respuesta_sin_coordenadas_ni_contactos(self):
        texto = self._resolver().content.decode()
        for prohibido in (
            "-36.1",
            "-57.8",
            "Juan Contacto",
            "2245-000000",
            "8 a 12",
            "Nota interna",
            "latitud",
            "notas",
        ):
            self.assertNotIn(prohibido, texto)

    def test_pendiente_propia_por_proyecto(self):
        segundo = self._proyecto("Segundo")
        tercero = self._proyecto("Tercero")
        self._visita(self.proyecto, self.empleado, 10)
        antigua = self._visita(self.proyecto, self.empleado, 1)
        self._visita(tercero, self.otro, 1)  # de otro empleado: no aparece
        realizada = self._visita(segundo, self.empleado, 1)
        realizada.estado = Visita.Estado.REALIZADA
        realizada.realizada_en = "2026-01-02T10:00:00Z"
        realizada.save()
        por_id = {p["id"]: p for p in self._resolver().json()["proyectos"]}
        self.assertEqual(
            por_id[self.proyecto.id]["visita_pendiente_propia"], antigua.id
        )
        self.assertIsNone(por_id[segundo.id]["visita_pendiente_propia"])
        self.assertIsNone(por_id[tercero.id]["visita_pendiente_propia"])

    def test_throttle_por_usuario(self):
        for _ in range(30):
            self.assertEqual(self._resolver().status_code, 200)
        self.assertEqual(self._resolver().status_code, 429)
        otro = APIClient()
        otro.force_authenticate(self.otro)
        self.assertEqual(self._resolver(cliente=otro).status_code, 200)
