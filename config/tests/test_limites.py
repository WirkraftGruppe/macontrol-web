"""Límites de fallos de ingreso al admin (ventana fija)."""

from datetime import UTC, datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings

from config import limites
from config.limites import registrar_fallo

CLAVE = "clave-segura-123"
IP = "203.0.113.5"
# Mitad de una ventana de 15 min y de la de 60 min: ningún test cruza un borde.
RELOJ_FIJO = 900 * 2_000_000 + 450
User = get_user_model()


class LimitesAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        reloj = mock.patch("config.limites.time.time", return_value=RELOJ_FIJO)
        reloj.start()
        self.addCleanup(reloj.stop)
        self.admin = User.objects.create_superuser("adm", password=CLAVE)

    def test_reloj_fijo_lejos_de_los_bordes_de_ventana(self):
        self.assertEqual(limites.time.time(), RELOJ_FIJO)
        for ventana in (900, 3600):
            resto = limites.time.time() % ventana
            self.assertGreater(resto, 60)
            self.assertLess(resto, ventana - 60)

    def _ingresar(self, usuario, clave, ip=IP, url="/admin/login/"):
        return self.client.post(
            url, {"username": usuario, "password": clave}, REMOTE_ADDR=ip
        )

    def _fallar(self, cantidad, usuario="adm", ip=IP):
        for _ in range(cantidad):
            self.assertEqual(self._ingresar(usuario, "mala", ip).status_code, 200)

    @override_settings(INTENTOS_FALLIDOS_POR_IP=4)
    def test_ip_con_fallos_no_bloquea_contrasena_correcta(self):
        for i in range(3):
            self._ingresar(f"otro{i}", "mala")
        respuesta = self._ingresar("adm", CLAVE)
        self.assertRedirects(respuesta, "/admin/", fetch_redirect_response=False)

    @override_settings(INTENTOS_FALLIDOS_POR_IP=4)
    def test_umbral_de_fallos_por_ip_bloquea(self):
        for i in range(4):
            self._ingresar(f"otro{i}", "mala")
        respuesta = self._ingresar("adm", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self._ingresar("adm", CLAVE, "198.51.100.1").status_code, 302)

    def test_variantes_unicode_del_usuario_comparten_cupo(self):
        variantes = ["adm", "ADM", "ａｄｍ", " Adm ", "ＡＤＭ"]
        for variante in variantes:
            self.assertEqual(self._ingresar(variante, "mala").status_code, 200)
        for variante in variantes:
            self.assertEqual(self._ingresar(variante, CLAVE).status_code, 429)

    def test_fallos_desde_otra_ip_no_bloquean_al_usuario(self):
        self._fallar(5)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)
        respuesta = self._ingresar("adm", CLAVE, "198.51.100.1")
        self.assertRedirects(respuesta, "/admin/", fetch_redirect_response=False)

    @override_settings(FALLOS_POR_USUARIO=3)
    def test_cupo_global_por_usuario_bloquea_desde_cualquier_ip(self):
        for i in range(3):
            self._fallar(1, ip=f"198.51.100.{i}")
        self.assertEqual(self._ingresar("adm", CLAVE, "192.0.2.77").status_code, 429)

    def test_bloqueo_no_evalua_la_contrasena(self):
        self._fallar(5)
        with mock.patch("django.contrib.auth.forms.authenticate") as autenticar:
            respuesta = self._ingresar("adm", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        autenticar.assert_not_called()

    def test_ingreso_exitoso_limpia_solo_el_balde_usuario_ip(self):
        self._fallar(4)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 302)
        self.client.logout()
        # Con el balde (usuario, IP) limpio caben otros 5 fallos antes del bloqueo.
        self._fallar(5)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)

    def test_usuario_sin_acceso_al_admin_cuenta_como_fallo(self):
        User.objects.create_user("emp", password=CLAVE)  # sin is_staff
        for _ in range(5):
            self._ingresar("emp", CLAVE)
        self.assertEqual(self._ingresar("emp", CLAVE).status_code, 429)

    def test_ipv6_del_mismo_64_comparte_balde(self):
        direcciones = ["2001:db8:1:2::1", "2001:db8:1:2:ffff::9"]
        for i in range(5):
            self._fallar(1, ip=direcciones[i % 2])
        self.assertEqual(
            self._ingresar("adm", CLAVE, "2001:db8:1:2:abcd::7").status_code, 429
        )
        otra = self._ingresar("adm", CLAVE, "2001:db8:1:3::1")
        self.assertRedirects(otra, "/admin/", fetch_redirect_response=False)

    def test_ipv4_mapeada_usa_su_propio_balde(self):
        self._fallar(5, ip="::ffff:203.0.113.5")
        self.assertEqual(self._ingresar("adm", CLAVE, IP).status_code, 429)

    def test_claves_de_cache_usan_hmac_con_sal(self):
        from django.utils.crypto import salted_hmac

        self._fallar(1)
        esperado = salted_hmac("config.limites", IP).hexdigest()
        claves = [k for k in cache._cache if "ingreso:ip:" in k]
        self.assertEqual(len(claves), 1)
        self.assertIn(esperado, claves[0])

    def test_registrar_fallo_usa_incremento_atomico(self):
        peticion = RequestFactory().post("/admin/login/", REMOTE_ADDR=IP)
        with (
            mock.patch.object(cache, "get") as leer,
            mock.patch.object(cache, "set") as escribir,
            mock.patch.object(cache, "add") as agregar,
            mock.patch.object(cache, "incr") as incrementar,
        ):
            registrar_fallo(peticion, "adm")
        self.assertEqual(agregar.call_count, 3)
        self.assertEqual(incrementar.call_count, 3)
        leer.assert_not_called()
        escribir.assert_not_called()

    def test_incremento_con_databasecache_conserva_el_fin_de_ventana(self):
        """`DatabaseCache.incr` reinicia el vencimiento al TIMEOUT (300 s)"""
        tabla = "cache_prueba_limites"
        caches = {
            "default": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": tabla,
            }
        }
        with override_settings(CACHES=caches):
            call_command("createcachetable", tabla, verbosity=0)
            self.addCleanup(cache.clear)
            peticion = RequestFactory().post("/admin/login/", REMOTE_ADDR=IP)
            # Justo al inicio de ambas ventanas, para que el resto sea siempre > 600 s.
            with mock.patch("config.limites.time") as reloj:
                reloj.time.return_value = 3600 * 1000 + 1
                registrar_fallo(peticion, "adm")
                registrar_fallo(peticion, "adm")
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT expires FROM {tabla}")
                filas = [fila[0] for fila in cursor.fetchall()]
        self.assertEqual(len(filas), 3)
        ahora = datetime.now(UTC).replace(tzinfo=None)
        for vencimiento in filas:
            if not isinstance(vencimiento, datetime):
                vencimiento = datetime.fromisoformat(str(vencimiento))
            restante = (vencimiento.replace(tzinfo=None) - ahora).total_seconds()
            self.assertGreater(restante, 600)
