"""Dirección IP del cliente según la cantidad de proxies de confianza."""

from django.test import RequestFactory, SimpleTestCase, override_settings

from config.red import ip_del_cliente


class IpDelClienteTests(SimpleTestCase):
    def _pedir(self, remota="10.0.0.9", reenviadas=None):
        extra = {"REMOTE_ADDR": remota}
        if reenviadas is not None:
            extra["HTTP_X_FORWARDED_FOR"] = reenviadas
        return RequestFactory().get("/", **extra)

    @override_settings(NUM_PROXIES=0)
    def test_sin_proxies_ignora_x_forwarded_for(self):
        pedido = self._pedir(reenviadas="1.1.1.1, 2.2.2.2")
        self.assertEqual(ip_del_cliente(pedido), "10.0.0.9")

    @override_settings(NUM_PROXIES=1)
    def test_con_un_proxy_toma_la_ultima_ip(self):
        pedido = self._pedir(reenviadas="6.6.6.6, 1.1.1.1 ,2.2.2.2")
        self.assertEqual(ip_del_cliente(pedido), "2.2.2.2")

    @override_settings(NUM_PROXIES=2)
    def test_con_dos_proxies_toma_la_penultima_ip(self):
        pedido = self._pedir(reenviadas="6.6.6.6, 1.1.1.1, 2.2.2.2")
        self.assertEqual(ip_del_cliente(pedido), "1.1.1.1")

    @override_settings(NUM_PROXIES=2)
    def test_sin_entradas_suficientes_usa_la_direccion_remota(self):
        pedido = self._pedir(reenviadas="2.2.2.2")
        self.assertEqual(ip_del_cliente(pedido), "10.0.0.9")
        self.assertEqual(ip_del_cliente(self._pedir()), "10.0.0.9")
