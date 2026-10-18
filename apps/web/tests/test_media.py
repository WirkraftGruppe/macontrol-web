"""Servido de las imágenes subidas: solo servicios/ y clientes/, solo imágenes."""

import shutil
import tempfile
from pathlib import Path

from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings

from apps.web import views

CONTENIDO = b"contenido-de-imagen"


class ServirMediaTests(TestCase):
    def setUp(self):
        raiz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        media = raiz / "media"
        for ruta in (
            "servicios/a.jpg",
            "servicios/mayus.PNG",
            "clientes/b.png",
            "otra/c.jpg",
            "servicios/d.txt",
        ):
            archivo = media / ruta
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(CONTENIDO)
        (raiz / "secreto.jpg").write_bytes(b"secreto")
        (media / "secreto.jpg").write_bytes(b"secreto")
        configuracion = override_settings(MEDIA_ROOT=str(media))
        configuracion.enable()
        self.addCleanup(configuracion.disable)

    def leer(self, respuesta):
        try:
            return b"".join(respuesta.streaming_content)
        finally:
            respuesta.close()

    def test_sirve_imagen_de_servicios_con_nosniff_y_cache(self):
        for ruta, tipo in (
            ("servicios/a.jpg", "image/jpeg"),
            ("servicios/mayus.PNG", "image/png"),
            ("clientes/b.png", "image/png"),
        ):
            r = self.client.get(f"/media/{ruta}")
            self.assertEqual(r.status_code, 200, ruta)
            self.assertEqual(r["Content-Type"], tipo)
            self.assertEqual(r["X-Content-Type-Options"], "nosniff")
            self.assertEqual(r["Cache-Control"], "public, max-age=86400")
            self.assertEqual(self.leer(r), CONTENIDO)

    def test_rechaza_rutas_fuera_de_carpetas_publicas(self):
        rutas = [
            "otra/c.jpg",
            "secreto.jpg",
            "servicios/d.txt",
            "servicios/../secreto.jpg",
            "servicios/../otra/c.jpg",
            "../secreto.jpg",
            "servicios/%2e%2e/secreto.jpg",
            "servicios/..%5Csecreto.jpg",
            "servicios/..\\secreto.jpg",
            "/secreto.jpg",
            "/etc/passwd",
            "C:/secreto.jpg",
            "servicios/",
            "servicios",
            "servicios//a.jpg",
        ]
        for ruta in rutas:
            self.assertEqual(self.client.get(f"/media/{ruta}").status_code, 404, ruta)
            with self.assertRaises(Http404, msg=ruta):
                views.media_publica(RequestFactory().get("/"), ruta)

    def test_inexistente_da_404(self):
        self.assertEqual(self.client.get("/media/servicios/nada.jpg").status_code, 404)
        self.assertEqual(self.client.get("/media/servicios/sub/").status_code, 404)

    def test_solo_acepta_lectura(self):
        r = self.client.post("/media/servicios/a.jpg")
        self.assertEqual(r.status_code, 405)
