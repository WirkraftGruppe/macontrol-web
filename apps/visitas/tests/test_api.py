import json
import shutil
import tempfile
from datetime import date, datetime, timedelta
from io import BytesIO
from uuid import uuid4

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Foto, ProductoAplicado, Visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-api-test-")


def jpeg_chico():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


class BaseApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(
            cliente=cliente,
            nombre="Planta 1",
            direccion="Calle 1",
            localidad="Castelli",
            latitud="-36.100000",
            longitud="-57.800000",
        )
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.empleado = self._usuario("emp", User.Rol.EMPLEADO)
        self.otro = self._usuario("otro", User.Rol.EMPLEADO)
        self.admin = self._usuario("adm", User.Rol.ADMINISTRADOR)
        self.proyecto = Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=self.tipo,
            titulo="Control",
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
        )
        self.api = self._api(self.empleado)

    def _usuario(self, nombre, rol):
        return User.objects.create_user(username=nombre, password="x", rol=rol)

    def _api(self, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def _visita(self, empleado, **extra):
        extra.setdefault("origen", Visita.Origen.MANUAL)
        extra.setdefault("motivo_manual", "Carga")
        return Visita.objects.create(proyecto=self.proyecto, empleado=empleado, **extra)

    def _realizada(self, empleado, dia):
        realizada = timezone.make_aware(datetime(2026, 9, dia, 12, 0))
        return self._visita(
            empleado, estado=Visita.Estado.REALIZADA, realizada_en=realizada
        )


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CrearVisitaTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.producto = Producto.objects.create(nombre_comercial="Cebo X")

    def _cuerpo(self, **cambios):
        cuerpo = {
            "qr_codigo": str(self.sitio.qr_codigo),
            "proyecto": self.proyecto.id,
            "cliente_uuid": str(uuid4()),
            "realizada_en": (timezone.now() - timedelta(minutes=1)).isoformat(),
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": "8.5",
            "datos": json.dumps({"cebos": 3}),
            "fotos": [jpeg_chico()],
        }
        cuerpo.update(cambios)
        return {k: v for k, v in cuerpo.items() if v is not None}

    def _post(self, api=None, **cambios):
        return (api or self.api).post(
            "/api/v1/visitas/", self._cuerpo(**cambios), format="multipart"
        )

    def test_crea_visita_con_fotos_y_productos(self):
        productos = [
            {
                "producto": self.producto.id,
                "lote": "L1",
                "dosis": "2.5",
                "unidad": "ml/l",
                "cantidad": "10",
            }
        ]
        r = self._post(
            fotos=[jpeg_chico(), jpeg_chico()],
            productos_aplicados=json.dumps(productos),
            observaciones="Todo en orden",
        )
        self.assertEqual(r.status_code, 201, r.content)
        visita = Visita.objects.get(pk=r.data["id"])
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.fotos.count(), 2)
        self.assertEqual(ProductoAplicado.objects.filter(visita=visita).count(), 1)
        self.assertEqual(len(r.data["fotos"]), 2)
        self.assertNotIn("latitud", r.data)

    def test_qr_que_no_corresponde_al_proyecto_da_400(self):
        r = self._post(qr_codigo=str(uuid4()))
        self.assertEqual(r.status_code, 400)
        self.assertIn("qr_codigo", r.data["campos"])
        self.assertFalse(Visita.objects.exists())

    def test_sin_foto_da_400(self):
        r = self._post(fotos=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn("fotos", r.data["campos"])

    def test_mas_de_diez_fotos_da_400(self):
        r = self._post(fotos=[jpeg_chico() for _ in range(11)])
        self.assertEqual(r.status_code, 400)
        self.assertIn("fotos", r.data["campos"])
        self.assertFalse(Visita.objects.exists())

    def test_datos_invalidos_contra_esquema_da_400(self):
        r = self._post(datos=json.dumps({"cebos": "mucho", "otra": 1}))
        self.assertEqual(r.status_code, 400)
        self.assertIn("datos", r.data["campos"])
        r = self._post(datos="no es json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("datos", r.data["campos"])

    def test_completa_pendiente_propia(self):
        pendiente = self._visita(self.empleado, programada_para=date(2026, 9, 1))
        r = self._post()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["id"], pendiente.id)
        self.assertEqual(Visita.objects.count(), 1)

    def test_pendiente_de_otro_marca_incidencia_asignacion(self):
        ajena = self._visita(self.otro, programada_para=date(2026, 9, 1))
        r = self._post()
        self.assertEqual(r.status_code, 201, r.content)
        nueva = Visita.objects.get(pk=r.data["id"])
        self.assertNotEqual(nueva.id, ajena.id)
        self.assertTrue(nueva.incidencia_asignacion)
        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, Visita.Estado.PENDIENTE)

    def test_reintento_con_mismo_cliente_uuid_da_409(self):
        clave = str(uuid4())
        primera = self._post(cliente_uuid=clave)
        self.assertEqual(primera.status_code, 201, primera.content)
        r = self._post(cliente_uuid=clave)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["visita"], primera.data["id"])
        r = self._post(api=self._api(self.otro), cliente_uuid=clave)
        self.assertEqual(r.status_code, 409)
        self.assertNotIn("visita", r.data)
        self.assertEqual(r.data["detalle"], "La visita ya fue registrada.")
        self.assertEqual(Visita.objects.count(), 1)

    def test_producto_fuera_del_catalogo_da_400(self):
        productos = [{"producto": 99999, "lote": "L", "dosis": "1", "unidad": "ml"}]
        r = self._post(productos_aplicados=json.dumps(productos))
        self.assertEqual(r.status_code, 400)
        self.assertIn("productos_aplicados", r.data["campos"])
        self.assertFalse(Visita.objects.exists())

    def test_administrador_no_crea_visita(self):
        r = self._post(api=self._api(self.admin))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Visita.objects.exists())

    def test_cliente_uuid_es_obligatorio(self):
        r = self._post(cliente_uuid=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn("cliente_uuid", r.data["campos"])

    def test_topes_de_coordenadas_precision_y_productos(self):
        for cambio in (
            {"latitud": "90.5"},
            {"longitud": "-180.1"},
            {"latitud": "-36.1234567"},
            {"precision_m": "-1"},
            {"precision_m": "8.55"},
            {"productos_aplicados": json.dumps([{}] * 31)},
            {"productos_aplicados": json.dumps(["x"])},
        ):
            with self.subTest(cambio=cambio):
                r = self._post(**cambio)
                self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(Visita.objects.exists())

    def test_foto_de_mas_de_8_mb_da_400(self):
        grande = SimpleUploadedFile(
            "g.jpg", b"0" * (8 * 1024 * 1024 + 1), content_type="image/jpeg"
        )
        r = self._post(fotos=[grande])
        self.assertEqual(r.status_code, 400)
        self.assertIn("fotos.0", r.data["campos"])


class MisVisitasTests(BaseApiTests):
    def test_solo_pendientes_propias(self):
        propia = self._visita(self.empleado, programada_para=date(2026, 9, 1))
        self._visita(self.otro, programada_para=date(2026, 9, 1))
        self._realizada(self.empleado, 2)
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["id"] for v in r.data["results"]], [propia.id])
        item = r.data["results"][0]
        self.assertEqual(
            item["proyecto"], {"id": self.proyecto.id, "titulo": "Control"}
        )
        self.assertEqual(
            item["sitio"],
            {"nombre": "Planta 1", "direccion": "Calle 1", "localidad": "Castelli"},
        )
        self.assertEqual(item["programada_para"], "2026-09-01")
        self.assertEqual(
            self._api(self.admin).get("/api/v1/me/visitas/").status_code, 403
        )
        self.assertEqual(APIClient().get("/api/v1/me/visitas/").status_code, 401)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class HistorialTests(BaseApiTests):
    def test_solo_visitas_propias(self):
        propia = self._realizada(self.empleado, 2)
        Foto.objects.create(visita=propia, imagen=jpeg_chico())
        self._realizada(self.otro, 2)
        self._visita(self.empleado)
        r = self.api.get("/api/v1/me/historial/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["id"] for v in r.data["results"]], [propia.id])
        item = r.data["results"][0]
        self.assertNotIn("latitud", item)
        self.assertNotIn("longitud", item)
        codigo = propia.fotos.get().codigo
        self.assertEqual(item["fotos"], [f"/api/v1/fotos/{codigo}/"])

    def test_rango_de_fechas_filtra(self):
        ids = {dia: self._realizada(self.empleado, dia).id for dia in (1, 5, 10)}

        def pedir(**parametros):
            r = self.api.get("/api/v1/me/historial/", parametros)
            self.assertEqual(r.status_code, 200, r.content)
            return {v["id"] for v in r.data["results"]}

        self.assertEqual(
            pedir(desde="2026-09-05", hasta="2026-09-10"), {ids[5], ids[10]}
        )
        self.assertEqual(pedir(hasta="2026-09-01"), {ids[1]})
        self.assertEqual(pedir(desde="2026-09-11"), set())
        r = self.api.get("/api/v1/me/historial/", {"desde": "ayer"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("desde", r.data["campos"])


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.visita = self._realizada(self.empleado, 2)
        self.foto = Foto.objects.create(visita=self.visita, imagen=jpeg_chico())
        self.url = f"/api/v1/fotos/{self.foto.codigo}/"

    def test_foto_se_sirve_al_dueno_y_403_a_otro(self):
        r = self.api.get(self.url, HTTP_ACCEPT="image/jpeg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertEqual(r["Cache-Control"], "private, no-store")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"\xff\xd8"))
        r = self._api(self.otro).get(self.url)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["campos"], {})
        self.assertEqual(self.api.get(f"/api/v1/fotos/{uuid4()}/").status_code, 404)
        self.assertEqual(APIClient().get(self.url).status_code, 401)

    def test_administrador_ve_la_foto(self):
        r = self._api(self.admin).get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        r.close()
