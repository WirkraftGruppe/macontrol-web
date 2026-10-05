import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.visitas.admin import (
    CAMPOS_EVIDENCIA,
    FotoInline,
    FotoInlineForm,
    ProductoAplicadoInline,
)
from apps.visitas.models import Foto, ProductoAplicado, Visita

from .test_models import crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="macontrol-test-admin-")


def _imagen_real():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "blue").save(salida, format="JPEG")
    return SimpleUploadedFile("f.jpg", salida.getvalue(), content_type="image/jpeg")


def _png_demasiado_grande():
    """PNG de 8000x6000 (modo L): lo acepta ImageField, pero procesar_imagen no."""
    salida = BytesIO()
    Image.new("L", (8000, 6000)).save(salida, format="PNG")
    return SimpleUploadedFile("grande.png", salida.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class VisitaAdminTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _request(self):
        request = RequestFactory().get("/admin/")
        request.user = self.administrador
        return request

    def _realizada_con_foto(self):
        visita = crear_visita(
            estado=Visita.Estado.REALIZADA, realizada_en=timezone.now()
        )
        foto = Foto.objects.create(visita=visita, imagen=_imagen_real())
        return visita, foto

    def _pendiente_de(self, otra):
        return Visita.objects.create(
            proyecto=otra.proyecto, empleado=otra.empleado, origen=Visita.Origen.APP
        )

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

    def test_visita_realizada_tiene_evidencia_de_solo_lectura(self):
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        solo_lectura = modeladmin.get_readonly_fields(self._request(), realizada)
        for campo in CAMPOS_EVIDENCIA:
            self.assertIn(campo, solo_lectura)
        solo_lectura = modeladmin.get_readonly_fields(self._request(), pendiente)
        for campo in ("proyecto", "empleado"):
            self.assertNotIn(campo, solo_lectura)

    def test_no_se_borran_visitas_ni_fotos(self):
        visita, foto = self._realizada_con_foto()
        self.client.force_login(self.administrador)
        url = reverse("admin:visitas_visita_delete", args=[visita.pk])
        respuesta = self.client.post(url, {"post": "yes"})
        self.assertEqual(respuesta.status_code, 403)
        url = reverse("admin:visitas_foto_delete", args=[foto.pk])
        respuesta = self.client.post(url, {"post": "yes"})
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Visita.objects.filter(pk=visita.pk).exists())
        self.assertTrue(Foto.objects.filter(pk=foto.pk).exists())
        request = self._request()
        for modelo in (Visita, Foto):
            self.assertFalse(
                admin.site._registry[modelo].has_delete_permission(request)
            )
        inline = admin.site._registry[Visita].get_inline_instances(request, visita)[0]
        self.assertFalse(inline.has_delete_permission(request, visita))
        pendiente = self._pendiente_de(visita)
        self.assertFalse(inline.has_delete_permission(request, pendiente))

    def test_inlines_bloqueados_en_visita_realizada(self):
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        request = self._request()
        modeladmin = admin.site._registry[Visita]
        for inline in modeladmin.get_inline_instances(request, realizada):
            self.assertFalse(inline.has_add_permission(request, realizada))
            self.assertFalse(inline.has_change_permission(request, realizada))
            self.assertFalse(inline.has_delete_permission(request, realizada))
        for clase in (FotoInline, ProductoAplicadoInline):
            inline = clase(Visita, admin.site)
            self.assertTrue(inline.has_add_permission(request, pendiente))
            self.assertTrue(inline.has_change_permission(request, pendiente))

    def test_foto_admin_no_cambia_foto_de_visita_realizada(self):
        realizada, foto = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        foto_pendiente = Foto.objects.create(visita=pendiente, imagen=_imagen_real())
        request = self._request()
        fotoadmin = admin.site._registry[Foto]
        self.assertFalse(fotoadmin.has_add_permission(request))
        self.assertFalse(fotoadmin.has_change_permission(request, foto))
        self.assertTrue(fotoadmin.has_change_permission(request, foto_pendiente))
        self.client.force_login(self.administrador)
        url = reverse("admin:visitas_foto_change", args=[foto.pk])
        self.assertEqual(self.client.post(url, {"orden": 9}).status_code, 403)
        foto.refresh_from_db()
        self.assertEqual(foto.orden, 0)
        for modelo in (Foto, ProductoAplicado):
            solo_lectura = admin.site._registry[modelo].get_readonly_fields(
                request, foto_pendiente if modelo is Foto else None
            )
            self.assertIn("visita", solo_lectura)

    def test_revertir_desde_historial_esta_prohibido(self):
        visita = crear_visita(latitud=Decimal("-35.1"), longitud=Decimal("-58.1"))
        visita.estado = Visita.Estado.REALIZADA
        visita.realizada_en = timezone.now()
        visita.save()
        realizada_en = visita.realizada_en
        version_pendiente = visita.history.get(estado=Visita.Estado.PENDIENTE)
        self.client.force_login(self.administrador)
        url = reverse(
            "admin:visitas_visita_simple_history",
            args=[visita.pk, version_pendiente.pk],
        )
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["adminform"].form
        datos = {
            nombre: ("" if valor is None else valor)
            for nombre, valor in formulario.initial.items()
            if nombre in formulario.fields
        }
        datos["latitud"] = -36.5
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 403)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.realizada_en, realizada_en)
        self.assertEqual(visita.latitud, Decimal("-35.1"))

    def _datos_iniciales(self, formulario):
        return {
            nombre: ("" if valor is None else valor)
            for nombre, valor in formulario.initial.items()
            if nombre in formulario.fields
        }

    def test_imagen_invalida_da_error_de_formulario_no_500(self):
        """Una foto que procesar_imagen rechaza es error del formulario, no un 500."""
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        formulario = FotoInlineForm(
            data={"visita": pendiente.pk, "orden": 0},
            files={"imagen": _png_demasiado_grande()},
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn("imagen", formulario.errors)
        self.assertEqual(pendiente.fotos.count(), 0)

    def test_pendiente_no_muestra_inlines_de_evidencia(self):
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        self.assertEqual(modeladmin.get_inlines(request, None), ())
        self.assertEqual(modeladmin.get_inlines(request, pendiente), ())
        self.assertEqual(
            modeladmin.get_inlines(request, realizada),
            (FotoInline, ProductoAplicadoInline),
        )
        self.client.force_login(self.administrador)
        for url in (
            reverse("admin:visitas_visita_change", args=[pendiente.pk]),
            reverse("admin:visitas_visita_add"),
        ):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.context["inline_admin_formsets"], [])

    def test_coordenadas_y_datos_solo_lectura_en_pendiente(self):
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        for obj in (None, pendiente):
            solo_lectura = modeladmin.get_readonly_fields(request, obj)
            for campo in ("latitud", "longitud", "precision_m", "datos"):
                self.assertIn(campo, solo_lectura)

    def test_foto_admin_imagen_invalida_da_error_de_formulario(self):
        """FotoAdmin también devuelve error de campo para una imagen inválida."""
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        foto = Foto.objects.create(visita=pendiente, imagen=_imagen_real())
        nombre = foto.imagen.name
        self.client.force_login(self.administrador)
        url = reverse("admin:visitas_foto_change", args=[foto.pk])
        respuesta = self.client.post(
            url, {"imagen": _png_demasiado_grande(), "tomada_en": "", "orden": 0}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("imagen", respuesta.context["adminform"].form.errors)
        foto.refresh_from_db()
        self.assertEqual(foto.imagen.name, nombre)

    def test_programada_para_solo_lectura_en_realizada(self):
        """La planificación es de solo lectura en visitas cerradas."""
        realizada, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        cerrada = modeladmin.get_readonly_fields(request, realizada)
        abierta = modeladmin.get_readonly_fields(request, pendiente)
        for campo in ("programada_para", "asignada_por"):
            self.assertIn(campo, cerrada)
            self.assertNotIn(campo, abierta)
        for campo in ("observaciones", "incidencia", "incidencia_detalle"):
            self.assertNotIn(campo, cerrada)


class FormVisitaTests(TestCase):
    def test_form_de_visita_declara_campos(self):
        modeladmin = admin.site._registry[Visita]
        self.assertNotEqual(modeladmin.fields, "__all__")
        editables = {
            f.name for f in Visita._meta.get_fields() if getattr(f, "editable", False)
        }
        editables -= {"id"}
        self.assertEqual(set(modeladmin.fields), editables)
        for campo in ("incidencia_asignacion", "cliente_uuid", "recibida_en"):
            self.assertIn(campo, modeladmin.readonly_fields)
        self.assertNotIn("__all__", (FotoInlineForm._meta.fields,))
        self.assertEqual(
            set(FotoInlineForm._meta.fields), {"visita", "imagen", "tomada_en", "orden"}
        )


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AdminPendienteTests(TestCase):
    def test_post_forjado_con_foto_se_rechaza(self):
        pendiente = crear_visita()
        foto = Foto.objects.create(visita=pendiente, imagen=_imagen_real())
        administrador = User.objects.create_superuser(
            username="root-pend", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(administrador)
        url = reverse("admin:visitas_visita_change", args=[pendiente.pk])
        self.client.post(
            url,
            {
                "estado": Visita.Estado.REALIZADA,
                "realizada_en_0": "2026-10-01",
                "realizada_en_1": "10:00:00",
                "latitud": "-35.1",
                "longitud": "-58.1",
                "datos": '{"a": 1}',
                "proyecto": pendiente.proyecto_id,
                "empleado": pendiente.empleado_id,
                "origen": Visita.Origen.APP,
                "fotos-TOTAL_FORMS": 1,
                "fotos-INITIAL_FORMS": 1,
                "fotos-0-id": foto.pk,
                "fotos-0-visita": pendiente.pk,
                "fotos-0-orden": 5,
                "productos-TOTAL_FORMS": 0,
                "productos-INITIAL_FORMS": 0,
            },
        )
        pendiente.refresh_from_db()
        foto.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(pendiente.realizada_en)
        self.assertIsNone(pendiente.latitud)
        self.assertIsNone(pendiente.longitud)
        self.assertEqual(pendiente.datos, {})
        self.assertEqual(foto.orden, 0)
