"""Pruebas del panel de contenido del sitio público."""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.servicios.models import TipoServicio
from apps.web.models import ClienteDestacado, Configuracion, PaginaServicio


class ContenidoPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-web", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            username="emp-web", password="x", rol=User.Rol.EMPLEADO
        )
        tipo = TipoServicio.objects.create(nombre="Roedores", slug="roedores-web")
        cls.pagina = PaginaServicio.objects.create(
            tipo=tipo, titulo_seo="Roedores", resumen="r", problema="p"
        )

    def datos_pagina(self, **cambios):
        datos = {
            "titulo_seo": "Control de roedores",
            "resumen": "Resumen",
            "problema": "Problema",
            "adicional": "",
            "metodos": json.dumps([{"titulo": "Cebado", "descripcion": "Con cebos"}]),
            "faq": "[]",
            "sectores": ["hoteleria"],
            "publicado": "on",
        }
        datos.update(cambios)
        return datos

    def test_editar_configuracion_exige_administrador(self):
        url = reverse("panel:web:configuracion")
        datos = {
            "razon_social": "MAControl S.A.",
            "telefono": "02241 49 6047",
            "direcciones": json.dumps(
                [{"localidad": "Castelli", "direccion": "Ricardo Naveiro 7"}]
            ),
            "redes": "",
        }
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertEqual(Configuracion.obtener().razon_social, "")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertRedirects(self.client.post(url, datos), url)
        config = Configuracion.obtener()
        self.assertEqual(config.razon_social, "MAControl S.A.")
        self.assertEqual(config.direcciones[0]["localidad"], "Castelli")
        self.assertEqual(config.redes, [])

    def test_empleado_recibe_403_y_anonimo_va_al_login(self):
        urls = [
            reverse("panel:web:configuracion"),
            reverse("panel:web:paginas"),
            reverse("panel:web:pagina_editar", args=[self.pagina.pk]),
            reverse("panel:web:clientes"),
            reverse("panel:web:cliente_alta"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.client.logout()
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn("/panel/ingresar/", respuesta["Location"])
                self.client.force_login(self.empleado)
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_edita_pagina_servicio_y_rechaza_metodos_mal_formados(self):
        self.client.force_login(self.admin)
        url = reverse("panel:web:pagina_editar", args=[self.pagina.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("panel:web:paginas")).status_code, 200)
        malos = [
            "no es json",
            '{"titulo": "a", "descripcion": "b"}',
            '[{"titulo": "a"}]',
            '[{"titulo": "a", "descripcion": "b", "extra": "c"}]',
            '[{"titulo": "a", "descripcion": ""}]',
            '[{"titulo": "a", "descripcion": 3}]',
        ]
        for malo in malos:
            with self.subTest(metodos=malo):
                respuesta = self.client.post(url, self.datos_pagina(metodos=malo))
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("metodos", respuesta.context["form"].errors)
        respuesta = self.client.post(url, self.datos_pagina(sectores=["inventado"]))
        self.assertIn("sectores", respuesta.context["form"].errors)
        respuesta = self.client.post(url, self.datos_pagina())
        self.assertRedirects(respuesta, reverse("panel:web:paginas"))
        self.pagina.refresh_from_db()
        self.assertEqual(self.pagina.titulo_seo, "Control de roedores")
        self.assertEqual(self.pagina.metodos[0]["titulo"], "Cebado")
        self.assertEqual(self.pagina.sectores, ["hoteleria"])
        self.assertTrue(self.pagina.publicado)

    def test_admin_da_de_alta_cliente_y_rechaza_logo_no_imagen(self):
        self.client.force_login(self.admin)
        url = reverse("panel:web:cliente_alta")
        falso = SimpleUploadedFile("logo.png", b"no es una imagen", "image/png")
        base = {"nombre": "Cliente A", "orden": 1, "activo": "on"}
        respuesta = self.client.post(url, {**base, "logo": falso})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("logo", respuesta.context["form"].errors)
        pdf = SimpleUploadedFile("logo.pdf", b"%PDF", "application/pdf")
        respuesta = self.client.post(url, {**base, "logo": pdf})
        self.assertIn("logo", respuesta.context["form"].errors)
        self.assertFalse(ClienteDestacado.objects.exists())
        self.assertRedirects(self.client.post(url, base), reverse("panel:web:clientes"))
        cliente = ClienteDestacado.objects.get()
        editar = reverse("panel:web:cliente_editar", args=[cliente.pk])
        self.client.post(editar, {"nombre": "Cliente B", "orden": 2})
        cliente.refresh_from_db()
        self.assertEqual(
            (cliente.nombre, cliente.orden, cliente.activo), ("Cliente B", 2, False)
        )
        self.assertContains(self.client.get(reverse("panel:web:clientes")), "Cliente B")
