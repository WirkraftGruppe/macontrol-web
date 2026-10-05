from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
CLAVE = "Clave-Segura-2026"


class UsuarioPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "admin1", password=CLAVE, rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            "emp1", password=CLAVE, rol=User.Rol.EMPLEADO, first_name="Ana"
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_no_expone_hash(self):
        urls = [
            reverse("panel:usuarios:listado"),
            reverse("panel:usuarios:alta"),
            reverse("panel:usuarios:editar", args=[self.empleado.pk]),
            reverse("panel:usuarios:desactivar", args=[self.empleado.pk]),
            reverse("panel:usuarios:contrasena", args=[self.empleado.pk]),
        ]
        for url in urls:
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200, url)
            html = respuesta.content.decode()
            self.assertNotIn(self.empleado.password, html, url)
            self.assertNotIn("pbkdf2", html, url)
        editar = self.client.get(urls[2]).context["form"]
        for prohibido in ("password", "is_staff", "is_superuser"):
            self.assertNotIn(prohibido, editar.fields)

    def test_alta_con_rol_empleado(self):
        datos = {
            "username": "nuevo",
            "first_name": "Luis",
            "last_name": "Paz",
            "email": "luis@example.com",
            "telefono": "2241 555555",
            "rol": User.Rol.EMPLEADO,
            "password1": CLAVE,
            "password2": CLAVE,
        }
        respuesta = self.client.post(reverse("panel:usuarios:alta"), datos)
        self.assertRedirects(respuesta, reverse("panel:usuarios:listado"))
        usuario = User.objects.get(username="nuevo")
        self.assertTrue(usuario.es_empleado)
        self.assertFalse(usuario.is_staff)
        self.assertTrue(usuario.check_password(CLAVE))

    def test_alta_rechaza_contrasenas_distintas_o_debiles(self):
        base = {"username": "x", "rol": User.Rol.EMPLEADO}
        for p1, p2 in ((CLAVE, "otra"), ("12345678", "12345678")):
            respuesta = self.client.post(
                reverse("panel:usuarios:alta"),
                {**base, "password1": p1, "password2": p2},
            )
            self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_empleado_no_accede(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("panel:usuarios:listado"))
        self.assertEqual(respuesta.status_code, 403)

    def test_listado_filtra_por_q_rol_y_activo(self):
        User.objects.filter(pk=self.empleado.pk).update(is_active=False)
        url = reverse("panel:usuarios:listado")
        nombres = lambda **p: {  # noqa: E731
            u.username for u in self.client.get(url, p).context["object_list"]
        }
        self.assertEqual(nombres(q="Ana"), {"emp1"})
        self.assertEqual(nombres(rol="administrador"), {"admin1"})
        self.assertEqual(nombres(activo="0"), {"emp1"})
        self.assertEqual(nombres(activo="1"), {"admin1"})

    def test_edicion_no_toca_la_contrasena(self):
        hash_previo = self.empleado.password
        self.client.post(
            reverse("panel:usuarios:editar", args=[self.empleado.pk]),
            {"username": "emp1", "first_name": "Bea", "rol": User.Rol.EMPLEADO},
        )
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.first_name, "Bea")
        self.assertEqual(self.empleado.password, hash_previo)

    def test_desactivar_por_post_no_borra(self):
        url = reverse("panel:usuarios:desactivar", args=[self.empleado.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)
        self.client.post(url)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)

    def test_no_puede_desactivarse_a_si_mismo(self):
        self.client.post(reverse("panel:usuarios:desactivar", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cambiar_contrasena_invalida_la_anterior(self):
        nueva = "Otra-Clave-Nueva-77"
        respuesta = self.client.post(
            reverse("panel:usuarios:contrasena", args=[self.empleado.pk]),
            {"new_password1": nueva, "new_password2": nueva},
        )
        self.assertRedirects(respuesta, reverse("panel:usuarios:listado"))
        cliente = Client()
        self.assertFalse(cliente.login(username="emp1", password=CLAVE))
        self.assertTrue(cliente.login(username="emp1", password=nueva))
