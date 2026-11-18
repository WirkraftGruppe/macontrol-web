"""La reserva se corta en el primer balde lleno: solo cuentan los intentos evaluados."""

from datetime import UTC, datetime
from unittest import mock

from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase

from apps.web.models import ContadorIngreso
from config import limites

CLAVE = "clave-segura-123"
IP_A = "203.0.113.31"
IP_B = "203.0.113.32"
# Mitad de una ventana de 15 min y de la de 60 min.
RELOJ_FIJO = 900 * 2_000_000 + 450
User = get_user_model()


class CorteDeReservaTests(TestCase):
    def setUp(self):
        self.ahora = RELOJ_FIJO
        reloj = mock.patch("config.limites.time.time", side_effect=lambda: self.ahora)
        reloj.start()
        self.addCleanup(reloj.stop)
        User.objects.create_superuser("adm", password=CLAVE)

    def _ingresar(self, usuario="adm", clave="mala", ip=IP_A):
        return self.client.post(
            "/admin/login/", {"username": usuario, "password": clave}, REMOTE_ADDR=ip
        )

    def test_una_ip_bloqueada_no_bloquea_al_usuario_desde_otra_ip(self):
        for _ in range(51):
            self._ingresar(ip=IP_A)
        respuesta = self._ingresar(clave=CLAVE, ip=IP_B)
        self.assertEqual(respuesta.status_code, 302)

    def test_ip_bloqueada_no_crea_filas_de_usuario(self):
        # Cada nombre distinto llena el balde de la IP (20) sin tocar uno por par.
        for numero in range(21):
            self._ingresar(usuario=f"otro{numero}")
        self.assertEqual(self._ingresar(usuario="nuevo").status_code, 429)
        filas = ContadorIngreso.objects.count()
        for numero in range(10):
            self.assertEqual(self._ingresar(usuario=f"x{numero}").status_code, 429)
        self.assertEqual(ContadorIngreso.objects.count(), filas)

    def test_devolucion_usa_la_ventana_de_la_reserva(self):
        borde = 900 * 2_000_001
        self.ahora = borde - 1
        peticion = mock.Mock(META={"REMOTE_ADDR": IP_A})
        clave_ip = limites._baldes(peticion, "adm")[0][0]
        anterior = f"{clave_ip}:{(borde - 1) // 900}"
        siguiente = f"{clave_ip}:{borde // 900}"
        ContadorIngreso.objects.create(
            clave=siguiente, cuenta=3, vence=datetime.fromtimestamp(borde + 900, UTC)
        )

        def autenticar_cruzando_el_borde(*args, **kwargs):
            self.ahora = borde + 1
            return authenticate(*args, **kwargs)

        with mock.patch(
            "django.contrib.auth.forms.authenticate",
            side_effect=autenticar_cruzando_el_borde,
        ):
            respuesta = self._ingresar(clave=CLAVE)
        self.assertEqual(respuesta.status_code, 302)
        cuentas = dict(ContadorIngreso.objects.values_list("clave", "cuenta"))
        self.assertEqual(cuentas[anterior], 0)
        self.assertEqual(cuentas[siguiente], 3)
