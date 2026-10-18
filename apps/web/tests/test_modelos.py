"""Tests de los modelos de contenido del sitio público."""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import include, path

from apps.web.models import ClienteDestacado, Configuracion, Sector, Servicio
from apps.web.validators import TAMANO_MAXIMO_IMAGEN

urlpatterns = [
    path(
        "",
        include(
            (
                [
                    path(
                        "servicio/<slug:slug>/",
                        lambda request, slug: HttpResponse(slug),
                        name="servicio",
                    )
                ],
                "web",
            )
        ),
    )
]
CLIENTES_CARTA = [
    "ESAB", "Nutrisur", "Villa del Sur", "Danone", "Howard Johnson", "Banco Nación",
    "Banco Provincia", "YPF Agro", "YPF", "Día", "Open Sports", "Super Beef", "La Zona",
]  # fmt: skip


class ConfiguracionTests(TestCase):
    def test_singleton_y_fixture_carga(self):
        call_command("loaddata", "contenido_inicial", verbosity=0)
        self.assertEqual(Configuracion.objects.count(), 1)
        config = Configuracion.obtener()
        self.assertEqual(config.pk, 1)
        self.assertEqual(config.razon_social, "MAControl S.A.")
        self.assertEqual(config.eslogan, "Manejo integral de plagas")
        self.assertEqual(config.correo, "administracion@macontrol.com.ar")
        self.assertEqual(
            config.direcciones,
            [
                {"localidad": "Castelli", "direccion": "Ricardo Naveiro 7"},
                {"localidad": "Chascomús", "direccion": "Presidente Perón 427"},
            ],
        )
        # save() fuerza pk=1: no se crea una segunda fila.
        Configuracion(razon_social="Otra").save()
        self.assertEqual(Configuracion.objects.count(), 1)
        self.assertEqual(Configuracion.obtener().razon_social, "Otra")

    def test_obtener_no_escribe_en_la_base(self):
        self.assertEqual(Configuracion.objects.count(), 0)
        config = Configuracion.obtener()
        self.assertEqual(Configuracion.objects.count(), 0)
        self.assertIsNone(config._state.db)
        self.assertEqual(config.pk, 1)
        self.assertEqual(config.direcciones, [])
        Configuracion(razon_social="Guardada").save()
        self.assertEqual(Configuracion.obtener().razon_social, "Guardada")

    def test_whatsapp_y_horario_vacios_y_href_de_telefono(self):
        call_command("loaddata", "contenido_inicial", verbosity=0)
        config = Configuracion.obtener()
        self.assertEqual(config.whatsapp, "")
        self.assertEqual(config.horario, "")
        self.assertEqual(config.redes, [])
        self.assertEqual(config.telefono_href, "tel:+542241496047")
        self.assertEqual(config.whatsapp_href, "")
        config.whatsapp = "02241 15 55 1234"
        self.assertEqual(config.whatsapp_href, "https://wa.me/54224115551234")


@override_settings(ROOT_URLCONF=__name__)
class ServicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)

    def test_publicados_ordena_por_orden_y_excluye_no_publicados(self):
        Servicio.objects.all().delete()
        for nombre, orden, publicado in (
            ("B", 2, True), ("A", 2, True), ("Z", 1, True), ("Oculto", 0, False),
        ):  # fmt: skip
            Servicio.objects.create(
                nombre=nombre,
                slug=nombre.lower(),
                titulo_seo=nombre,
                resumen="r",
                problema="p",
                orden=orden,
                publicado=publicado,
            )
        nombres = [s.nombre for s in Servicio.objects.publicados()]
        self.assertEqual(nombres, ["Z", "A", "B"])

    def test_fixture_nueve_servicios_con_faq_vacia_y_validos(self):
        self.assertEqual(Servicio.objects.count(), 9)
        for servicio in Servicio.objects.all():
            self.assertEqual(servicio.faq, [])
            self.assertTrue(servicio.publicado)
            servicio.full_clean()
        publicados = list(Servicio.objects.publicados())
        self.assertEqual([s.orden for s in publicados], list(range(1, 10)))
        self.assertEqual(
            publicados[0].get_absolute_url(),
            "/servicio/desinfeccion-sanitizacion-desodorizacion/",
        )

    def test_slug_es_unico(self):
        duplicado = Servicio.objects.get(pk=1)
        duplicado.pk = None
        with self.assertRaises(ValidationError) as ctx:
            duplicado.full_clean()
        self.assertIn("slug", ctx.exception.message_dict)

    def test_sectores_fuera_de_la_lista_se_rechazan(self):
        servicio = Servicio.objects.get(pk=1)
        servicio.sectores = [Sector.SALUD.value, "astronautas"]
        with self.assertRaises(ValidationError) as ctx:
            servicio.full_clean()
        self.assertIn("sectores", ctx.exception.message_dict)
        servicio.sectores = "centros-de-salud"
        with self.assertRaises(ValidationError):
            servicio.full_clean()
        servicio.sectores = [Sector.SALUD.value, Sector.HOTELERIA.value]
        servicio.full_clean()

    @override_settings(ROOT_URLCONF="config.urls")
    def test_solo_publicados_en_home_y_sitemap(self):
        Servicio.objects.filter(pk=2).update(publicado=False)
        home = self.client.get("/").content.decode()
        sitemap = self.client.get("/sitemap.xml").content.decode()
        for pk, visible in ((1, True), (2, False), (3, True)):
            url = Servicio.objects.get(pk=pk).get_absolute_url()
            self.assertEqual(url in home, visible, url)
            self.assertEqual(url in sitemap, visible, url)

    def test_sectores_del_fixture_son_validos(self):
        for servicio in Servicio.objects.all():
            self.assertTrue(set(servicio.sectores) <= set(Sector.values))


class ClienteDestacadoTests(TestCase):
    def test_fixture_trae_13_clientes_activos_sin_logo(self):
        call_command("loaddata", "contenido_inicial", verbosity=0)
        clientes = list(ClienteDestacado.objects.activos())
        self.assertEqual(len(clientes), 13)
        self.assertEqual([c.nombre for c in clientes], CLIENTES_CARTA)
        self.assertTrue(all(not c.logo for c in clientes))

    def test_activos_excluye_inactivos(self):
        ClienteDestacado.objects.create(nombre="B", orden=2)
        ClienteDestacado.objects.create(nombre="A", orden=2)
        ClienteDestacado.objects.create(nombre="C", orden=1, activo=False)
        self.assertEqual(
            [c.nombre for c in ClienteDestacado.objects.activos()], ["A", "B"]
        )

    def test_logo_rechaza_extension_y_tamano_no_permitidos(self):
        cliente = ClienteDestacado(nombre="X")
        cliente.logo = SimpleUploadedFile(
            "logo.gif", b"GIF89a", content_type="image/gif"
        )
        with self.assertRaises(ValidationError) as ctx:
            cliente.full_clean()
        self.assertIn("logo", ctx.exception.message_dict)

        cliente.logo = SimpleUploadedFile(
            "logo.png", b"0" * (TAMANO_MAXIMO_IMAGEN + 1), content_type="image/png"
        )
        with self.assertRaises(ValidationError) as ctx:
            cliente.full_clean()
        self.assertTrue(
            any("2 MB" in m for m in ctx.exception.message_dict["logo"]),
            ctx.exception.message_dict,
        )


class FotoServicioTests(TestCase):
    def test_foto_rechaza_extension_tamano_y_usa_uuid(self):
        servicio = Servicio(
            nombre="S", slug="s", titulo_seo="S", resumen="r", problema="p"
        )
        servicio.foto = SimpleUploadedFile("f.gif", b"GIF89a", "image/gif")
        with self.assertRaises(ValidationError) as ctx:
            servicio.full_clean()
        self.assertIn("foto", ctx.exception.message_dict)

        servicio.foto = SimpleUploadedFile(
            "f.jpg", b"0" * (TAMANO_MAXIMO_IMAGEN + 1), "image/jpeg"
        )
        with self.assertRaises(ValidationError) as ctx:
            servicio.full_clean()
        self.assertTrue(any("2 MB" in m for m in ctx.exception.message_dict["foto"]))

        campo = Servicio._meta.get_field("foto")
        self.assertRegex(
            campo.generate_filename(servicio, "Mi Foto.JPG"),
            r"^servicios[/\\][0-9a-f]{32}\.jpg$",
        )
