import shutil
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import mock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connection, models
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla
from apps.visitas.models import Foto, ProductoAplicado, Visita
from apps.visitas.services import (
    MAX_FOTOS,
    MAX_PRODUCTOS,
    VisitaDuplicada,
    registrar_visita_desde_app,
    registrar_visita_realizada,
)
from apps.visitas.tests.test_models import crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-test-")
COORDENADAS = {"latitud": Decimal("-35.1"), "longitud": Decimal("-57.7")}


def jpeg_chico():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RegistrarVisitaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.ahora = timezone.make_aware(datetime(2026, 9, 1, 12, 0))

    def con_foto(self, visita):
        Foto.objects.create(visita=visita, imagen=jpeg_chico())

    def test_actualiza_encargado_actual_y_proxima_visita(self):
        visita = crear_visita(**COORDENADAS)
        self.con_foto(visita)
        proyecto = visita.proyecto
        proyecto.frecuencia_dias = 30
        proyecto.save()
        resultado = registrar_visita_realizada(visita, visita.empleado, self.ahora)
        self.assertEqual(resultado.estado, Visita.Estado.REALIZADA)
        self.assertEqual(resultado.realizada_en, self.ahora)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, visita.empleado)
        self.assertEqual(
            proyecto.proxima_visita,
            timezone.localdate(self.ahora) + timedelta(days=30),
        )

    def test_sin_frecuencia_no_toca_proxima_visita(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        proyecto = visita.proyecto
        proyecto.proxima_visita = date(2027, 1, 1)
        proyecto.save()
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.proxima_visita, date(2027, 1, 1))

    def test_origen_app_exige_coordenadas_y_foto(self):
        visita = crear_visita()
        proyecto = visita.proyecto
        antes = (proyecto.encargado_actual_id, proyecto.proxima_visita)

        def verificar_rechazo(nombre):
            with self.subTest(nombre):
                with self.assertRaises(ValidationError):
                    registrar_visita_realizada(visita, visita.empleado, self.ahora)
                visita.refresh_from_db()
                self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
                self.assertIsNone(visita.realizada_en)
                proyecto.refresh_from_db()
                self.assertEqual(
                    (proyecto.encargado_actual_id, proyecto.proxima_visita), antes
                )

        verificar_rechazo("sin coordenadas ni foto")
        visita.latitud, visita.longitud = COORDENADAS.values()
        visita.save()
        verificar_rechazo("sin foto")
        visita.latitud = visita.longitud = None
        visita.save()
        self.con_foto(visita)
        verificar_rechazo("sin coordenadas")

    def test_origen_app_con_coordenadas_y_foto_se_registra(self):
        visita = crear_visita(**COORDENADAS)
        self.con_foto(visita)
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_origen_manual_exige_motivo(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="   ")
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
        visita.motivo_manual = "Sin señal en el sitio"
        visita.save()
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_guarda_copia_del_esquema_de_planilla(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        campo = CampoPlanilla.objects.create(
            tipo_servicio=visita.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(len(visita.esquema_planilla), 1)
        self.assertEqual(visita.esquema_planilla[0]["clave"], "cebos")
        campo.etiqueta = "Otra"
        campo.save()
        visita.refresh_from_db()
        self.assertEqual(visita.esquema_planilla[0]["etiqueta"], "Cebos")

    def test_rechaza_visita_no_pendiente(self):
        visita = crear_visita(
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
            estado=Visita.Estado.CANCELADA,
        )
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.CANCELADA)

    def otro_empleado(self):
        return User.objects.create_user(
            username="emp-otro", password="x", rol=User.Rol.EMPLEADO
        )

    def test_doble_registro_con_lecturas_distintas_falla(self):
        creada = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        primera = Visita.objects.get(pk=creada.pk)
        segunda = Visita.objects.get(pk=creada.pk)
        otro = self.otro_empleado()
        registrar_visita_realizada(primera, primera.empleado, self.ahora)
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(segunda, otro, self.ahora + timedelta(hours=1))
        creada.refresh_from_db()
        self.assertEqual(creada.empleado, primera.empleado)
        self.assertEqual(creada.realizada_en, self.ahora)

    def test_visita_atrasada_no_retrocede_el_proyecto(self):
        reciente = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        proyecto = reciente.proyecto
        proyecto.frecuencia_dias = 30
        proyecto.save()
        otro = self.otro_empleado()
        atrasada = Visita.objects.create(
            proyecto=proyecto,
            empleado=reciente.empleado,
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga tardía",
        )
        registrar_visita_realizada(reciente, reciente.empleado, self.ahora)
        registrar_visita_realizada(atrasada, otro, self.ahora - timedelta(days=10))
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, reciente.empleado)
        self.assertEqual(
            proyecto.proxima_visita,
            timezone.localdate(self.ahora) + timedelta(days=30),
        )
        atrasada.refresh_from_db()
        self.assertEqual(atrasada.estado, Visita.Estado.REALIZADA)

    def test_rechaza_realizada_en_futura(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(
                visita, visita.empleado, timezone.now() + timedelta(hours=1)
            )
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(visita.realizada_en)

    def test_falla_de_validacion_no_muta_la_instancia(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        admin = User.objects.create_user(
            username="admin-svc", password="x", rol=User.Rol.ADMINISTRADOR
        )
        empleado_original = visita.empleado
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(visita, admin, self.ahora)
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
        self.assertEqual(visita.empleado, empleado_original)
        self.assertIsNone(visita.realizada_en)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RegistrarDesdeAppTests(TestCase):
    def setUp(self):
        self.pendiente = crear_visita(programada_para=date(2026, 9, 1))
        self.empleado = self.pendiente.empleado
        self.proyecto = self.pendiente.proyecto
        self.producto = Producto.objects.create(nombre_comercial="Cebo")
        self.archivos_previos = self.archivos_en_disco()

    def archivos_en_disco(self):
        return set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*"))

    def registrar(self, **extra):
        argumentos = {
            "empleado": self.empleado,
            "proyecto": self.proyecto.pk,
            "qr_codigo": self.proyecto.sitio.qr_codigo,
            "cliente_uuid": uuid4(),
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.7"),
            "precision_m": Decimal("8.5"),
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_visita_desde_app(**argumentos)

    def assertNadaCreado(self):
        self.assertEqual(Visita.objects.count(), 1)
        self.assertEqual(Foto.objects.count(), 0)
        self.assertEqual(ProductoAplicado.objects.count(), 0)
        self.assertEqual(self.archivos_en_disco(), self.archivos_previos)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(self.pendiente.cliente_uuid)

    def test_completa_la_pendiente_propia(self):
        item = {
            "producto": self.producto.pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad": "ml/l",
            "cantidad": None,
        }
        visita = self.registrar(
            productos_aplicados=[item], observaciones="Sin novedades"
        )
        self.assertEqual(visita.pk, self.pendiente.pk)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertFalse(visita.incidencia_asignacion)
        self.assertEqual(visita.observaciones, "Sin novedades")
        self.assertEqual(visita.fotos.count(), 1)
        self.assertEqual(visita.productos.get().lote, "L1")
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.encargado_actual, self.empleado)

    def test_completar_pendiente_limpia_motivo_manual(self):
        self.pendiente.origen = Visita.Origen.MANUAL
        self.pendiente.motivo_manual = "Carga a mano"
        self.pendiente.save()
        visita = self.registrar()
        self.assertEqual(visita.pk, self.pendiente.pk)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.motivo_manual, "")
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.motivo_manual, "")

    def test_crea_nueva_con_origen_app_sin_pendiente(self):
        self.pendiente.delete()
        visita = self.registrar()
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.empleado, self.empleado)
        self.assertFalse(visita.incidencia_asignacion)

    def test_pendiente_de_otro_crea_nueva_con_incidencia_asignacion(self):
        otro = User.objects.create_user(
            username="emp-b", password="x", rol=User.Rol.EMPLEADO
        )
        self.pendiente.empleado = otro
        self.pendiente.save()
        visita = self.registrar()
        self.assertNotEqual(visita.pk, self.pendiente.pk)
        self.assertTrue(visita.incidencia_asignacion)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, Visita.Estado.PENDIENTE)
        self.assertEqual(self.pendiente.empleado, otro)

    def test_cliente_uuid_repetido_levanta_visita_duplicada(self):
        codigo = uuid4()
        primera = self.registrar(cliente_uuid=codigo)
        with self.assertRaises(VisitaDuplicada) as contexto:
            self.registrar(cliente_uuid=codigo)
        self.assertEqual(contexto.exception.visita.pk, primera.pk)
        self.assertEqual(Visita.objects.count(), 1)
        self.assertEqual(Foto.objects.count(), 1)

    def test_qr_de_otro_sitio_se_rechaza(self):
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(qr_codigo=uuid4())
        self.assertIn("qr_codigo", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_cliente_dado_de_baja_se_rechaza(self):
        cliente = self.proyecto.sitio.cliente
        cliente.activo = False
        cliente.save()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar()
        self.assertEqual(
            contexto.exception.message_dict["qr_codigo"],
            ["El código QR no corresponde a este proyecto."],
        )
        self.assertNadaCreado()

    def test_proyecto_no_activo_se_rechaza(self):
        self.proyecto.estado = Proyecto.Estado.PAUSADO
        self.proyecto.save()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar()
        self.assertIn("proyecto", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_datos_invalidos_no_crean_nada(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(datos={"otro": 1})
        self.assertIn("datos", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_producto_inactivo_se_rechaza(self):
        self.producto.activo = False
        self.producto.save()
        item = {"producto": self.producto.pk, "lote": "L", "dosis": "1", "unidad": "ml"}
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(productos_aplicados=[item])
        self.assertIn("productos_aplicados", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_sin_fotos_se_rechaza(self):
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(fotos=[])
        self.assertIn("fotos", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_foto_invalida_revierte_todo_y_borra_archivos(self):
        basura = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(fotos=[jpeg_chico(), basura])
        self.assertIn("fotos", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_registra_recibida_en_del_servidor(self):
        antes = timezone.now()
        visita = self.registrar(realizada_en=antes - timedelta(days=2))
        self.assertGreaterEqual(visita.recibida_en, antes)
        self.assertLessEqual(visita.recibida_en, timezone.now())
        self.assertLess(visita.realizada_en, visita.recibida_en)

    def item_valido(self, producto=None):
        return {
            "producto": (producto or self.producto).pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad": "ml/l",
            "cantidad": None,
        }

    def test_mas_fotos_que_el_tope_se_rechaza(self):
        fotos = [jpeg_chico() for _ in range(MAX_FOTOS + 1)]
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(fotos=fotos)
        self.assertIn("fotos", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_mas_productos_que_el_tope_se_rechaza(self):
        item = self.item_valido()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(productos_aplicados=[item] * (MAX_PRODUCTOS + 1))
        self.assertIn("productos_aplicados", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_productos_se_buscan_en_una_consulta(self):
        otro = Producto.objects.create(nombre_comercial="Gel")
        items = [self.item_valido(p) for p in (self.producto, otro, self.producto)]
        with CaptureQueriesContext(connection) as consultas:
            self.registrar(productos_aplicados=items)
        sobre_productos = [
            c["sql"] for c in consultas if 'FROM "productos_producto"' in c["sql"]
        ]
        self.assertEqual(len(sobre_productos), 1, sobre_productos)

    def test_fallo_del_insert_de_foto_no_deja_archivo_huerfano(self):
        guardar = models.Model.save_base

        def falla_en_foto(instancia, *args, **kwargs):
            if isinstance(instancia, Foto):
                raise OperationalError("fallo simulado del INSERT")
            return guardar(instancia, *args, **kwargs)

        with mock.patch.object(models.Model, "save_base", falla_en_foto):
            with self.assertRaises(OperationalError):
                self.registrar()
        self.assertNadaCreado()

    def test_error_al_borrar_no_tapa_la_excepcion_original(self):
        basura = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with mock.patch(
            "django.core.files.storage.FileSystemStorage.delete",
            side_effect=OSError("no se pudo borrar"),
        ):
            with self.assertRaises(ValidationError) as contexto:
                self.registrar(fotos=[jpeg_chico(), basura])
        self.assertIn("fotos", contexto.exception.message_dict)

    def test_cliente_uuid_obligatorio(self):
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(cliente_uuid=None)
        self.assertIn("cliente_uuid", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_latitud_fuera_de_rango_se_rechaza(self):
        for valor in (Decimal("90.1"), Decimal("-91")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError) as contexto:
                    self.registrar(latitud=valor)
                self.assertIn("latitud", contexto.exception.message_dict)
                self.assertNadaCreado()

    def test_longitud_fuera_de_rango_se_rechaza(self):
        for valor in (Decimal("180.1"), Decimal("-181")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError) as contexto:
                    self.registrar(longitud=valor)
                self.assertIn("longitud", contexto.exception.message_dict)
                self.assertNadaCreado()
