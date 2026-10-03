from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Visita, ruta_foto


def crear_visita(**extra):
    """Visita guardada con proyecto, empleado y administrador propios."""
    cliente = Cliente.objects.create(razon_social="ACME")
    sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
    tipo = TipoServicio.objects.create(nombre="Roedores", slug="roedores-vis")
    empleado = User.objects.create_user(
        username="emp-vis", password="x", rol=User.Rol.EMPLEADO
    )
    proyecto = Proyecto.objects.create(
        sitio=sitio,
        tipo_servicio=tipo,
        titulo="Roedores mensual",
        encargado_inicial=empleado,
        encargado_actual=empleado,
    )
    datos = {"proyecto": proyecto, "empleado": empleado, "origen": Visita.Origen.APP}
    datos.update(extra)
    return Visita.objects.create(**datos)


class VisitaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita()
        cls.admin = User.objects.create_user(
            username="admin-vis", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def test_empleado_debe_tener_rol_empleado(self):
        self.visita.empleado = self.admin
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("empleado", ctx.exception.message_dict)

    def test_realizada_exige_realizada_en(self):
        self.visita.estado = Visita.Estado.REALIZADA
        self.visita.realizada_en = None
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("realizada_en", ctx.exception.message_dict)

    def test_cancelada_no_admite_realizada_en(self):
        self.visita.estado = Visita.Estado.CANCELADA
        self.visita.realizada_en = timezone.now()
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("realizada_en", ctx.exception.message_dict)

    def test_historial_excluye_coordenadas_y_datos(self):
        campos = {f.name for f in Visita.history.model._meta.get_fields()}
        for excluido in ("latitud", "longitud", "precision_m", "datos"):
            self.assertNotIn(excluido, campos)
        self.assertIn("estado", campos)


class FotoModeloTests(TestCase):
    def test_ruta_foto_usa_uuid_y_no_el_nombre_original(self):
        ruta = ruta_foto(None, "casa de Perez.png")
        self.assertRegex(ruta, r"^visitas/fotos/[0-9a-f]{32}\.jpg$")
        self.assertNotIn("Perez", ruta)
        self.assertNotEqual(ruta, ruta_foto(None, "casa de Perez.png"))
