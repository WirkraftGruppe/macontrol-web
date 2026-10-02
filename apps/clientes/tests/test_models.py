from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.clientes.models import Cliente


class ClienteTests(TestCase):
    def test_cuit_invalido_no_valida(self):
        for cuit in ("2012345678", "20-1234567-9", "2012345678a"):
            with self.subTest(cuit=cuit):
                with self.assertRaises(ValidationError) as ctx:
                    Cliente(razon_social="ACME", cuit=cuit).full_clean()
                self.assertIn("cuit", ctx.exception.message_dict)

    def test_cuit_valido_pasa(self):
        Cliente(razon_social="ACME", cuit="20123456789").full_clean()

    def test_cuit_es_opcional(self):
        cliente = Cliente(razon_social="ACME")
        cliente.full_clean()
        cliente.save()
        self.assertEqual(cliente.cuit, "")
