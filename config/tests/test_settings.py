"""Pruebas de los módulos de settings, cada una en un proceso aparte."""

import os
import re
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_HEREDADAS = (
    "DJANGO_ENV",
    "ALLOWED_HOSTS",
    "SECRET_KEY",
    "DATABASE_URL",
    "CSRF_TRUSTED_ORIGINS",
    "NUM_PROXIES",
    "SITE_URL",
    "MEDIA_ROOT",
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID",
    "RAILWAY_PUBLIC_DOMAIN",
    "RENDER",
    "FLY_APP_NAME",
    "DYNO",
    "K_SERVICE",
)

_VARIABLES_DE_HOSTING = _HEREDADAS[-9:]

# Variables mínimas de producción: sin ellas el arranque aborta.
_PROD_MINIMA = {
    "DJANGO_ENV": "production",
    "SECRET_KEY": "x" * 60,
    "DATABASE_URL": "sqlite:///prod-test.sqlite3",
    "ALLOWED_HOSTS": "macontrol.com.ar",
    "NUM_PROXIES": "1",
    "SITE_URL": "https://macontrol.com.ar",
}


def _correr(args, **entorno):
    """Ejecuta manage.py con un entorno propio y devuelve el proceso."""
    env = {k: v for k, v in os.environ.items() if k not in _HEREDADAS}
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(entorno)
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class SettingsTests(SimpleTestCase):
    def test_samesite_lax_fijado(self):
        """SameSite y el tope de archivos se fijan explícitos en base.py."""
        from config.settings import base

        self.assertEqual(getattr(base, "SESSION_COOKIE_SAMESITE", None), "Lax")
        self.assertEqual(getattr(base, "DATA_UPLOAD_MAX_NUMBER_FILES", None), 12)

    def test_dev_aborta_con_variables_de_hosting(self):
        for variable in _VARIABLES_DE_HOSTING:
            with self.subTest(variable=variable):
                r = _correr(["check"], DJANGO_ENV="development", **{variable: "x"})
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(variable, r.stdout + r.stderr)

    def test_limite_de_cuerpo_registrado_antes_de_csrf(self):
        mw = list(settings.MIDDLEWARE)
        limite = "config.limite_cuerpo.LimiteCuerpoMiddleware"
        seguridad = "django.middleware.security.SecurityMiddleware"
        csrf = "django.middleware.csrf.CsrfViewMiddleware"
        self.assertLess(mw.index(seguridad), mw.index(limite))
        self.assertLess(mw.index(limite), mw.index(csrf))
        self.assertEqual(settings.LIMITE_CUERPO_BYTES, 3 * 1024 * 1024)

    def test_dev_rechaza_hosts_publicos(self):
        r = _correr(
            ["check"], DJANGO_ENV="development", ALLOWED_HOSTS="macontrol.com.ar"
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("usar DJANGO_ENV=production", r.stdout + r.stderr)

    def test_dev_acepta_hosts_locales_y_red_privada(self):
        hosts = "localhost,127.0.0.1,[::1],testserver,192.168.1.10,10.0.0.5"
        r = _correr(["check"], DJANGO_ENV="development", ALLOWED_HOSTS=hosts)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prod_hsts_reversible(self):
        r = _correr(
            [
                "shell",
                "-c",
                "from django.conf import settings as s;"
                "print(s.SECURE_HSTS_SECONDS, s.SECURE_HSTS_INCLUDE_SUBDOMAINS,"
                " s.SECURE_HSTS_PRELOAD)",
            ],
            **_PROD_MINIMA,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "3600 False False")

    def test_dev_recorta_espacios_de_allowed_hosts(self):
        r = _correr(
            ["check"],
            DJANGO_ENV="development",
            ALLOWED_HOSTS="localhost, 192.168.1.10 ",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prod_recorta_espacios_de_allowed_hosts(self):
        r = _correr(
            [
                "shell",
                "-c",
                "from django.conf import settings as s; print(s.ALLOWED_HOSTS)",
            ],
            **{
                **_PROD_MINIMA,
                "ALLOWED_HOSTS": " macontrol.com.ar , ,www.macontrol.com.ar",
            },
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            r.stdout.strip().splitlines()[-1],
            "['macontrol.com.ar', 'www.macontrol.com.ar']",
        )

    def test_env_example_no_fija_django_env(self):
        texto = Path(settings.BASE_DIR, ".env.example").read_text(encoding="utf-8")
        lineas = [linea.strip() for linea in texto.splitlines()]
        self.assertIn("DJANGO_ENV=", lineas)


_LEER_DEBUG = "from django.conf import settings as s; print(s.DEBUG)"
_CLAVE_LARGA = "clave-Larga_de-PRUEBA-0123456789-abcdefghijklmnopqrstuvwxyz-!@#$%^&*"


class CheckDeployTests(SimpleTestCase):
    def test_check_deploy_solo_avisa_hsts_diferido(self):
        r = _correr(
            ["check", "--deploy"],
            **{**_PROD_MINIMA, "SECRET_KEY": _CLAVE_LARGA},
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ids = set(re.findall(r"security\.W\d+", r.stdout + r.stderr))
        self.assertEqual(ids, {"security.W005", "security.W021"})

    def test_check_deploy_con_variables_de_produccion_completas(self):
        """Con todas las variables de la guía de despliegue, solo avisa el HSTS."""
        r = _correr(
            ["check", "--deploy"],
            **{
                **_PROD_MINIMA,
                "SECRET_KEY": _CLAVE_LARGA,
                "ALLOWED_HOSTS": "demo.up.railway.app",
                "CSRF_TRUSTED_ORIGINS": "https://demo.up.railway.app",
                "SITE_URL": "https://demo.up.railway.app",
                "MEDIA_ROOT": "/data/media",
            },
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ids = set(re.findall(r"security\.W\d+", r.stdout + r.stderr))
        self.assertEqual(ids, {"security.W005", "security.W021"})


class DespliegueTests(SimpleTestCase):
    """Configuración para alojar: orígenes CSRF, hosts obligatorios y WhiteNoise."""

    _PROD = {**_PROD_MINIMA, "ALLOWED_HOSTS": "demo.up.railway.app"}

    def _leer_prod(self, expresion, **extra):
        return _correr(
            [
                "shell",
                "-c",
                f"from django.conf import settings as s; print({expresion})",
            ],
            **{**self._PROD, **extra},
        )

    def test_prod_lee_csrf_trusted_origins(self):
        r = self._leer_prod(
            "s.CSRF_TRUSTED_ORIGINS",
            CSRF_TRUSTED_ORIGINS=" https://a.up.railway.app , ,https://b.com.ar ",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            r.stdout.strip().splitlines()[-1],
            "['https://a.up.railway.app', 'https://b.com.ar']",
        )

    def test_prod_sin_allowed_hosts_falla(self):
        for valor in ("", " , "):
            with self.subTest(valor=valor):
                r = self._leer_prod("s.ALLOWED_HOSTS", ALLOWED_HOSTS=valor)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("ALLOWED_HOSTS", r.stdout + r.stderr)

    def test_prod_exige_num_proxies(self):
        sin = {k: v for k, v in self._PROD.items() if k != "NUM_PROXIES"}
        r = _correr(["shell", "-c", _LEER_DEBUG], **sin)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NUM_PROXIES", r.stdout + r.stderr)
        for valor in ("", "abc", "-1", "\u0663", "1_0"):
            with self.subTest(valor=valor):
                r = self._leer_prod("s.NUM_PROXIES", NUM_PROXIES=valor)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("NUM_PROXIES", r.stdout + r.stderr)
        r = self._leer_prod("s.NUM_PROXIES", NUM_PROXIES="2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "2")

    def test_prod_usa_cache_en_base_de_datos(self):
        r = self._leer_prod("s.CACHES['default']")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            r.stdout.strip().splitlines()[-1],
            "{'BACKEND': 'django.core.cache.backends.db.DatabaseCache', "
            "'LOCATION': 'cache_sitio', 'OPTIONS': {'MAX_ENTRIES': 100000}}",
        )

    def test_prod_rechaza_csrf_trusted_origins_inseguros(self):
        malos = (
            "http://demo.up.railway.app",
            "demo.up.railway.app",
            "https://*.up.railway.app",
            "*",
            "https://demo.up.railway.app/admin",
            "https://demo.up.railway.app,http://otro.com",
        )
        for valor in malos:
            with self.subTest(valor=valor):
                r = self._leer_prod(
                    "s.CSRF_TRUSTED_ORIGINS", CSRF_TRUSTED_ORIGINS=valor
                )
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("CSRF_TRUSTED_ORIGINS", r.stdout + r.stderr)
        r = self._leer_prod(
            "s.CSRF_TRUSTED_ORIGINS", CSRF_TRUSTED_ORIGINS="https://demo.up.railway.app"
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_prod_exige_site_url_https(self):
        sin = {k: v for k, v in self._PROD.items() if k != "SITE_URL"}
        r = _correr(["shell", "-c", _LEER_DEBUG], **sin)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SITE_URL", r.stdout + r.stderr)
        for valor in (
            "",
            "http://demo.up.railway.app",
            "demo.up.railway.app",
            "https://",
        ):
            with self.subTest(valor=valor):
                r = self._leer_prod("s.SITE_URL", SITE_URL=valor)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("SITE_URL", r.stdout + r.stderr)
        r = self._leer_prod("s.SITE_URL", SITE_URL="https://demo.up.railway.app/")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            r.stdout.strip().splitlines()[-1], "https://demo.up.railway.app"
        )

    def test_dev_aborta_en_railway(self):
        r = _correr(
            ["check"], DJANGO_ENV="development", RAILWAY_ENVIRONMENT="production"
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RAILWAY_ENVIRONMENT", r.stdout + r.stderr)

    def test_prod_whitenoise_despues_de_security_y_storages(self):
        r = self._leer_prod(
            "s.MIDDLEWARE[:2], s.STORAGES['staticfiles']['BACKEND'],"
            " s.STORAGES['default']['BACKEND']"
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        salida = r.stdout.strip().splitlines()[-1]
        self.assertIn(
            "['django.middleware.security.SecurityMiddleware', "
            "'whitenoise.middleware.WhiteNoiseMiddleware']",
            salida,
        )
        self.assertIn("CompressedManifestStaticFilesStorage", salida)
        self.assertIn("FileSystemStorage", salida)


class SiteUrlTests(SimpleTestCase):
    def test_quita_barra_final(self):
        """Un SITE_URL con barra final no deja `//q/` en el contenido de los QR."""
        r = _correr(
            [
                "shell",
                "-c",
                "from django.conf import settings as s; print(s.SITE_URL)",
            ],
            DJANGO_ENV="development",
            SITE_URL="https://ejemplo.com.ar/",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "https://ejemplo.com.ar")
