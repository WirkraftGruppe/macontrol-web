from django.template.loader import render_to_string
from django.test import SimpleTestCase


class BaseTemplateTests(SimpleTestCase):
    def test_base_define_tokens_de_ambos_temas(self):
        html = render_to_string("base.html")
        self.assertIn('[data-tema="oscuro"]', html)
        self.assertIn('[data-tema="claro"]', html)
        self.assertIn("#0f1417", html)
        self.assertIn("#f4f3ef", html)
        self.assertIn("--brand: #ffc600", html)
        self.assertIn('data-tema="oscuro"', html)
        self.assertIn("img/logo.png", html)
