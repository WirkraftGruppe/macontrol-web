"""Carga datos de demostración genéricos: clientes, sitios, puntos, planos y visitas."""

import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.demo import exigir_entorno_demo
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios import services as servicios_sitio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas import services as servicios_visita
from apps.visitas.models import Visita

CLAVE_DEMO = "demo1234"
LATITUD_BASE = Decimal("-36.090000")
LONGITUD_BASE = Decimal("-57.800000")

# (cliente, sitio, nombres de los puntos además de "General")
SITIOS = [
    (
        "Cliente Demo 1",
        "Planta Demo Norte",
        ["Entrada", "Depósito", "Cocina", "Muelle de carga"],
    ),
    ("Cliente Demo 1", "Depósito Demo Sur", ["Pasillo", "Patio"]),
    ("Cliente Demo 2", "Oficina Demo Centro", ["Recepción"]),
]


def _imagen(ancho, alto, color, formato, nombre):
    """Archivo subido con una imagen lisa generada con Pillow."""
    salida = BytesIO()
    imagen = Image.new("RGB", (ancho, alto), color)
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle([10, 10, ancho - 10, alto - 10], outline="white", width=3)
    imagen.save(salida, format=formato)
    return SimpleUploadedFile(nombre, salida.getvalue())


class Command(BaseCommand):
    help = (
        "Carga datos de demostración genéricos (clientes, sitios, puntos, planos, "
        "proyectos, visitas con revisiones y fotos). Es idempotente y solo corre "
        "con DEBUG, DJANGO_ENV=development y SQLite (sin DATABASE_URL), "
        "para no tocar nunca una base remota. Crea los usuarios demo-admin "
        "(administrador) y demo-empleado "
        f"(empleado) con la contraseña {CLAVE_DEMO}: existen solo en desarrollo."
    )

    def handle(self, *args, **opciones):
        exigir_entorno_demo("cargar_demo")
        with transaction.atomic():
            empleado = self._usuarios()
            tipo, _ = TipoServicio.objects.get_or_create(
                slug="demo-control-de-plagas",
                defaults={"nombre": "Control de plagas (demo)"},
            )
            sitios = [self._sitio(*datos) for datos in SITIOS]
            proyectos = [self._proyecto(sitio, tipo, empleado) for sitio in sitios]
        # Los servicios de visitas abren su propia transacción: van fuera.
        for orden, proyecto in enumerate(proyectos):
            self._visitas(proyecto, empleado, orden)
        self.stdout.write("Demo lista.")

    def _usuarios(self):
        """Crea los usuarios demo y devuelve el empleado.

        Uno que ya existía con otro rol u otra contraseña no se modifica: se avisa
        por stderr y la contraseña solo se informa de los recién creados.
        """
        usuarios = []
        for nombre, rol in (
            ("demo-admin", User.Rol.ADMINISTRADOR),
            ("demo-empleado", User.Rol.EMPLEADO),
        ):
            usuario, creado = User.objects.get_or_create(
                username=nombre, defaults={"rol": rol}
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
                usuario.save()
                self.stdout.write(f"Usuario creado: {nombre}, contraseña {CLAVE_DEMO}.")
            elif usuario.rol != rol or not usuario.check_password(CLAVE_DEMO):
                self.stderr.write(
                    f"El usuario {nombre} ya existía con otro rol u otra "
                    "contraseña: no se modificó."
                )
            usuarios.append(usuario)
        return usuarios[1]

    def _sitio(self, razon_social, nombre, nombres_puntos):
        cliente, _ = Cliente.objects.get_or_create(razon_social=razon_social)
        sitio, _ = Sitio.objects.get_or_create(
            cliente=cliente,
            nombre=nombre,
            defaults={"latitud": LATITUD_BASE, "longitud": LONGITUD_BASE},
        )
        puntos = [sitio.puntos.get(nombre="General")]
        for orden, nombre_punto in enumerate(nombres_puntos, start=1):
            punto, _ = PuntoControl.objects.get_or_create(
                sitio=sitio, nombre=nombre_punto, defaults={"orden": orden}
            )
            puntos.append(punto)
        # Cada punto, apenas corrido del anterior para que el mapa los distinga.
        for numero, punto in enumerate(puntos):
            if punto.latitud is None:
                servicios_sitio.fijar_ubicacion(
                    punto,
                    LATITUD_BASE + Decimal(numero) / 10000,
                    LONGITUD_BASE + Decimal(numero) / 10000,
                )
        if len(puntos) > 3:
            self._plano(sitio, puntos)
        return sitio

    def _plano(self, sitio, puntos):
        """Plano generado con los marcadores repartidos en una grilla de 0 a 1."""
        plano = sitio.planos.first()
        if plano is None:
            plano = Plano(
                sitio=sitio,
                nombre="Planta general",
                imagen=_imagen(800, 500, "#d9e2ec", "PNG", "plano.png"),
            )
            plano.save()
        for numero, punto in enumerate(puntos):
            if punto.plano_id is None:
                punto.plano = plano
                punto.save(update_fields=["plano"])
                servicios_sitio.mover_en_plano(
                    punto,
                    Decimal(numero % 3 + 1) / 4,
                    Decimal(numero // 3 + 1) / 3,
                )

    def _proyecto(self, sitio, tipo, empleado):
        proyecto, _ = Proyecto.objects.get_or_create(
            sitio=sitio,
            tipo_servicio=tipo,
            titulo=f"Control mensual de {sitio.nombre}",
            defaults={
                "encargado_inicial": empleado,
                "encargado_actual": empleado,
                "frecuencia_dias": 30,
            },
        )
        return proyecto

    def _visitas(self, proyecto, empleado, orden):
        """Visitas por los servicios del dominio, solo si el proyecto no tiene."""
        if proyecto.visitas.exists():
            return
        puntos = list(proyecto.sitio.puntos.filter(activo=True))
        ahora = timezone.now()
        # El primer proyecto tiene dos jornadas realizadas, el segundo una y el
        # último queda con una visita abierta.
        jornadas = {0: [timedelta(days=3), timedelta(days=1)], 1: [timedelta(hours=5)]}
        for atraso in jornadas.get(orden, []):
            visita = self._jornada(proyecto, empleado, puntos, ahora - atraso)
            servicios_visita.cerrar_visita(
                visita, quien=empleado, cierre=Visita.Cierre.EMPLEADO
            )
        if orden == 2:
            self._jornada(proyecto, empleado, puntos[:1], ahora)

    def _jornada(self, proyecto, empleado, puntos, realizada_en):
        """Abre una visita y registra una revisión por punto, cada una con foto."""
        visita, _ = servicios_visita.abrir_visita(
            empleado=empleado, proyecto=proyecto, qr_codigo=puntos[0].qr_codigo
        )
        for numero, punto in enumerate(puntos):
            servicios_visita.registrar_revision(
                visita=visita,
                empleado=empleado,
                qr_codigo=punto.qr_codigo,
                cliente_uuid=uuid.uuid4(),
                realizada_en=realizada_en + timedelta(minutes=numero),
                latitud=punto.latitud,
                longitud=punto.longitud,
                precision_m=Decimal("8.0"),
                datos={},
                productos_aplicados=[],
                fotos=[_imagen(320, 240, "#7a9e7e", "JPEG", f"foto-{numero}.jpg")],
                observaciones="Revisión de demostración.",
            )
        return visita
