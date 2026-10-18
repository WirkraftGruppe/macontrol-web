"""Dirección IP del cliente según la cantidad de proxies de confianza."""

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.red import ip_del_cliente


class IpDelClienteTests(SimpleTestCase):
    def _pedir(self, remota="10.0.0.9", reenviadas=None, **cabeceras):
        extra = {"REMOTE_ADDR": remota, **cabeceras}
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

    @override_settings(NUM_PROXIES=2, IP_CLIENTE_CABECERA="HTTP_X_REAL_IP")
    def test_cabecera_configurada_tiene_prioridad_sobre_x_forwarded_for(self):
        pedido = self._pedir(
            reenviadas="6.6.6.6, 1.1.1.1", HTTP_X_REAL_IP=" 203.0.113.7 "
        )
        self.assertEqual(ip_del_cliente(pedido), "203.0.113.7")
        pedido = self._pedir(HTTP_X_REAL_IP="2001:db8::1")
        self.assertEqual(ip_del_cliente(pedido), "2001:db8::1")

    @override_settings(NUM_PROXIES=0, IP_CLIENTE_CABECERA="HTTP_X_REAL_IP")
    def test_cabecera_con_valor_que_no_es_ip_usa_la_direccion_remota(self):
        for valor in ("no-es-ip", "1.1.1.1, 2.2.2.2", "999.1.1.1", ""):
            with self.subTest(valor=valor):
                pedido = self._pedir(reenviadas="6.6.6.6", HTTP_X_REAL_IP=valor)
                self.assertEqual(ip_del_cliente(pedido), "10.0.0.9")

    @override_settings(NUM_PROXIES=1, IP_CLIENTE_CABECERA="HTTP_X_REAL_IP")
    def test_cabecera_ausente_usa_la_direccion_remota(self):
        pedido = self._pedir(reenviadas="6.6.6.6")
        self.assertEqual(ip_del_cliente(pedido), "10.0.0.9")

    def test_nombre_de_cabecera_invalido_lanza_improperlyconfigured(self):
        for nombre in ("X-Real-IP", "x_real_ip", "REMOTE_ADDR", "HTTP_x_real", "HTTP_"):
            with self.subTest(nombre=nombre):
                with override_settings(IP_CLIENTE_CABECERA=nombre):
                    with self.assertRaises(ImproperlyConfigured):
                        ip_del_cliente(self._pedir())
