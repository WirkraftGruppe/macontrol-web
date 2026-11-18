"""El intento de ingreso se reserva antes de evaluar la contraseña (contador atómico)."""

from datetime import UTC, datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.web.models import ContadorIngreso
from config import limites

CLAVE = "clave-segura-123"
IP = "203.0.113.21"
# Mitad de una ventana de 15 min y de la de 60 min: ningún test cruza un borde.
RELOJ_FIJO = 900 * 2_000_000 + 450
User = get_user_model()


class ReservaIntentoTests(TestCase):
    def setUp(self):
        self.reloj = mock.patch("config.limites.time.time", return_value=RELOJ_FIJO)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)
        User.objects.create_superuser("adm", password=CLAVE)

    def _ingresar(self, usuario="adm", clave="mala", ip=IP):
        return self.client.post(
            "/admin/login/", {"username": usuario, "password": clave}, REMOTE_ADDR=ip
        )

    def _cuenta(self, fragmento):
        filas = ContadorIngreso.objects.filter(clave__startswith=fragmento)
        return [fila.cuenta for fila in filas]

    def test_intento_se_reserva_antes_de_evaluar_la_contrasena(self):
        vistas = []

        def autenticar_simulado(*args, **kwargs):
            vistas.append(self._cuenta("ingreso:usuario-ip:"))
            return None

        with mock.patch(
            "django.contrib.auth.forms.authenticate", side_effect=autenticar_simulado
        ):
            self._ingresar()
        self.assertEqual(vistas, [[1]])

    @override_settings(FALLOS_POR_USUARIO_E_IP=3)
    def test_reservas_pendientes_cuentan_para_el_cupo(self):
        ahora = RELOJ_FIJO
        ventana = 900
        baldes = limites._baldes(self._peticion(), "adm")
        clave, _maximo, _ventana = baldes[1]
        ContadorIngreso.objects.create(
            clave=limites._clave_de_ventana(clave, ventana, ahora),
            cuenta=3,
            vence=datetime.fromtimestamp((ahora // ventana + 1) * ventana, UTC),
        )
        with mock.patch("django.contrib.auth.forms.authenticate") as autenticar:
            respuesta = self._ingresar(clave=CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        autenticar.assert_not_called()

    def _peticion(self):
        return RequestFactory().post("/admin/login/", REMOTE_ADDR=IP)

    def test_suma_es_un_unico_update_con_expresion(self):
        self._ingresar()  # crea las filas de la ventana
        with CaptureQueriesContext(connection) as consultas:
            self._ingresar()
        sqls = [c["sql"] for c in consultas.captured_queries]
        updates = [s for s in sqls if s.lstrip().upper().startswith('UPDATE "WEB_CONT')]
        self.assertEqual(len(updates), 3)
        for sql in updates:
            self.assertIn('"cuenta" + ', sql)
        # La cuenta solo se lee (sin otras columnas) justo después de su UPDATE.
        for i, sql in enumerate(sqls):
            columnas = sql.split("FROM")[0]
            if sql.lstrip().upper().startswith("SELECT") and '"clave"' not in columnas:
                if '"cuenta"' in columnas:
                    self.assertTrue(sqls[i - 1].lstrip().upper().startswith("UPDATE"))

    def test_ingreso_correcto_no_consume_cupo_de_ip_ni_de_usuario(self):
        self._ingresar()
        self._ingresar()
        self.assertEqual(self._cuenta("ingreso:ip:"), [2])
        self.assertEqual(self._cuenta("ingreso:usuario:"), [2])
        self.assertEqual(self._ingresar(clave=CLAVE).status_code, 302)
        self.assertEqual(self._cuenta("ingreso:ip:"), [2])
        self.assertEqual(self._cuenta("ingreso:usuario:"), [2])
        self.assertEqual(self._cuenta("ingreso:usuario-ip:"), [])

    def test_ventana_vencida_reinicia_la_cuenta(self):
        for _ in range(3):
            self._ingresar()
        self.assertEqual(self._cuenta("ingreso:usuario-ip:"), [3])
        # Se pasa a la ventana siguiente de 15 min: las filas viejas se borran.
        with mock.patch("config.limites.time.time", return_value=RELOJ_FIJO + 900):
            self._ingresar()
        self.assertEqual(self._cuenta("ingreso:usuario-ip:"), [1])
        self.assertEqual(self._cuenta("ingreso:ip:"), [1])
        self.assertFalse(ContadorIngreso.objects.filter(cuenta=3).exists())
