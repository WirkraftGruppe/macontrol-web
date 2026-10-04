import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Foto, ProductoAplicado, Visita, ruta_foto


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


def imagen_real(color="red"):
    """Archivo subido con un PNG real generado con Pillow."""
    buffer = BytesIO()
    Image.new("RGB", (40, 30), color).save(buffer, format="PNG")
    return SimpleUploadedFile("foto.png", buffer.getvalue(), content_type="image/png")


class FotoArchivoTests(TestCase):
    """El archivo de la foto no queda en disco al borrar o reemplazar la foto."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        configuracion = override_settings(MEDIA_ROOT=self.media)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.visita = crear_visita()

    def _crear_foto(self):
        return Foto.objects.create(visita=self.visita, imagen=imagen_real())

    def test_borrar_foto_borra_el_archivo(self):
        foto = self._crear_foto()
        ruta = Path(foto.imagen.path)
        self.assertTrue(ruta.exists())
        with self.captureOnCommitCallbacks(execute=True):
            foto.delete()
        self.assertFalse(ruta.exists())

    def test_borrar_visita_borra_los_archivos_de_sus_fotos(self):
        rutas = [Path(self._crear_foto().imagen.path) for _ in range(2)]
        self.assertTrue(all(ruta.exists() for ruta in rutas))
        with self.captureOnCommitCallbacks(execute=True):
            self.visita.delete()
        self.assertFalse(any(ruta.exists() for ruta in rutas))

    def test_reemplazar_imagen_borra_el_archivo_anterior(self):
        foto = self._crear_foto()
        anterior = Path(foto.imagen.path)
        foto.imagen = imagen_real("blue")
        with self.captureOnCommitCallbacks(execute=True):
            foto.save()
        nueva = Path(foto.imagen.path)
        self.assertNotEqual(anterior, nueva)
        self.assertFalse(anterior.exists())
        self.assertTrue(nueva.exists())


class ProductoAplicadoTests(TestCase):
    def test_historial_registra_cambio_de_lote(self):
        visita = crear_visita()
        producto = Producto.objects.create(nombre_comercial="Cebo X")
        aplicado = ProductoAplicado.objects.create(
            visita=visita,
            producto=producto,
            lote="L-1",
            dosis=Decimal("1.500"),
            unidad="g",
        )
        aplicado.lote = "L-2"
        aplicado.save()
        historial = aplicado.history.order_by("history_id")
        lotes = list(historial.values_list("lote", flat=True))
        self.assertEqual(lotes, ["L-1", "L-2"])


class CamposAppTests(TestCase):
    def test_cliente_uuid_es_unico(self):
        identificador = uuid4()
        visita = crear_visita(cliente_uuid=identificador)
        self.assertIsNone(visita.recibida_en)
        self.assertFalse(visita.incidencia_asignacion)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Visita.objects.create(
                proyecto=visita.proyecto,
                empleado=visita.empleado,
                origen=Visita.Origen.APP,
                cliente_uuid=identificador,
            )
        # Varias visitas sin cliente_uuid conviven (NULL no choca).
        Visita.objects.create(
            proyecto=visita.proyecto, empleado=visita.empleado, origen="app"
        )
        Visita.objects.create(
            proyecto=visita.proyecto, empleado=visita.empleado, origen="app"
        )

    def test_codigo_de_foto_se_genera_y_es_unico(self):
        visita = crear_visita()
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            primera = Foto.objects.create(visita=visita, imagen=imagen_real())
            segunda = Foto.objects.create(visita=visita, imagen=imagen_real("blue"))
        self.assertIsInstance(primera.codigo, UUID)
        self.assertNotEqual(primera.codigo, segunda.codigo)
        segunda.codigo = primera.codigo
        with self.assertRaises(IntegrityError), transaction.atomic():
            segunda.save()
