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
    "RAILWAY_ENVIRONMENT",
)


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
            DJANGO_ENV="production",
            SECRET_KEY="x" * 60,
            DATABASE_URL="sqlite:///prod-test.sqlite3",
            ALLOWED_HOSTS="macontrol.com.ar",
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
            DJANGO_ENV="production",
            SECRET_KEY="x" * 60,
            DATABASE_URL="sqlite:///prod-test.sqlite3",
            ALLOWED_HOSTS=" macontrol.com.ar , ,www.macontrol.com.ar",
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


class CheckDeployTests(SimpleTestCase):
    def test_check_deploy_solo_avisa_hsts_diferido(self):
        r = _correr(
            ["check", "--deploy"],
            DJANGO_ENV="production",
            SECRET_KEY="clave-Larga_de-PRUEBA-0123456789-abcdefghijklmnopqrstuvwxyz-!@#$%^&*",
            DATABASE_URL="sqlite:///prod-test.sqlite3",
            ALLOWED_HOSTS="macontrol.com.ar",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ids = set(re.findall(r"security\.W\d+", r.stdout + r.stderr))
        self.assertEqual(ids, {"security.W005", "security.W021"})


class DespliegueTests(SimpleTestCase):
    """Configuración para alojar: orígenes CSRF, hosts obligatorios y WhiteNoise."""

    _PROD = {
        "DJANGO_ENV": "production",
        "SECRET_KEY": "x" * 60,
        "DATABASE_URL": "sqlite:///prod-test.sqlite3",
        "ALLOWED_HOSTS": "demo.up.railway.app",
    }

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
