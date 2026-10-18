"""Las plantillas públicas no tienen formularios ni pedidos de presupuesto."""

from pathlib import Path

from django.test import SimpleTestCase

RAIZ = Path(__file__).resolve().parents[3]


class PlantillasPublicasTests(SimpleTestCase):
    def test_sin_form_ni_presupuesto(self):
        carpetas = [RAIZ / "templates/web", RAIZ / "apps/web/templates/web/paginas"]
        archivos = [a for c in carpetas for a in c.rglob("*") if a.is_file()]
        archivos += [
            RAIZ / "apps/web/templates/404.html",
            RAIZ / "apps/web/templates/500.html",
        ]
        self.assertGreaterEqual(len(archivos), 10)
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8").lower()
            self.assertNotIn("<form", texto, archivo)
            self.assertNotIn("presupuesto", texto, archivo)
