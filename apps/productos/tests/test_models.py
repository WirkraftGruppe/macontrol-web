from django.test import TestCase

from apps.productos.models import Producto


class ProductoTests(TestCase):
    def test_producto_activo_por_defecto(self):
        producto = Producto.objects.create(nombre_comercial="Cipermetrina 20")
        self.assertIs(producto.activo, True)
        self.assertEqual(str(producto), "Cipermetrina 20")
