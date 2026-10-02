from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.servicios.models import CampoPlanilla, TipoServicio


class CampoPlanillaTests(TestCase):
    def setUp(self):
        self.tipo = TipoServicio.objects.create(nombre="Uno", slug="uno")

    def test_clave_unica_por_tipo_servicio(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CampoPlanilla.objects.create(
                tipo_servicio=self.tipo, orden=2, etiqueta="B", clave="a", tipo="texto"
            )

    def test_misma_clave_en_otro_tipo_servicio_es_valida(self):
        otro = TipoServicio.objects.create(nombre="Dos", slug="dos")
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        campo = CampoPlanilla.objects.create(
            tipo_servicio=otro, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        self.assertEqual(campo.clave, "a")


class TipoServicioTests(TestCase):
    fixtures = ["tipos_servicio"]

    def test_esquema_planilla_respeta_orden(self):
        tipo = TipoServicio.objects.create(nombre="Prueba", slug="prueba")
        for orden in (3, 1, 2):
            CampoPlanilla.objects.create(
                tipo_servicio=tipo,
                orden=orden,
                etiqueta=f"Campo {orden}",
                clave=f"campo-{orden}",
                tipo=CampoPlanilla.Tipo.NUMERO,
            )
        esquema = tipo.esquema_planilla()
        self.assertEqual(
            [c["clave"] for c in esquema], ["campo-1", "campo-2", "campo-3"]
        )
        self.assertEqual(
            set(esquema[0]),
            {"clave", "etiqueta", "tipo", "opciones", "obligatorio", "ayuda", "orden"},
        )

    def test_fixture_carga_nueve_servicios(self):
        self.assertEqual(TipoServicio.objects.count(), 9)
        self.assertTrue(
            TipoServicio.objects.filter(nombre="Mantenimiento edilicio").exists()
        )
