import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.visitas.models import Foto, ProductoAplicado, Visita
from apps.visitas.planillas import validar_datos

# Topes de una visita desde la app; los comparte el serializer de la API.
MAX_FOTOS = 10
MAX_PRODUCTOS = 30
TOLERANCIA_FUTURO = timedelta(minutes=10)
MENSAJE_QR_INVALIDO = "El código QR no corresponde a este proyecto."

logger = logging.getLogger(__name__)


class VisitaDuplicada(Exception):
    """El `cliente_uuid` ya fue registrado; `visita` es la visita existente."""

    def __init__(self, visita):
        super().__init__("La visita ya fue registrada.")
        self.visita = visita


def registrar_visita_realizada(visita, empleado, realizada_en):
    """Marca la visita como realizada y actualiza el proyecto; devuelve la copia.

    La instancia recibida no se modifica: todo ocurre sobre una copia bloqueada.
    """
    with transaction.atomic():
        visita_bd = Visita.objects.select_for_update().get(pk=visita.pk)
        proyecto = Proyecto.objects.select_for_update().get(pk=visita_bd.proyecto_id)

        if visita_bd.estado != Visita.Estado.PENDIENTE:
            raise ValidationError("Solo se puede registrar una visita pendiente.")
        if realizada_en > timezone.now() + TOLERANCIA_FUTURO:
            raise ValidationError("La fecha de realización no puede ser futura.")
        if visita_bd.origen == Visita.Origen.APP:
            if visita_bd.latitud is None or visita_bd.longitud is None:
                raise ValidationError("Una visita desde la app exige coordenadas.")
            if not visita_bd.fotos.exists():
                raise ValidationError(
                    "Una visita desde la app exige al menos una foto."
                )
        elif visita_bd.origen == Visita.Origen.MANUAL:
            if not (visita_bd.motivo_manual or "").strip():
                raise ValidationError("Una visita manual exige el motivo.")

        visita_bd.empleado = empleado
        visita_bd.estado = Visita.Estado.REALIZADA
        visita_bd.realizada_en = realizada_en
        visita_bd.esquema_planilla = proyecto.tipo_servicio.esquema_planilla()
        visita_bd.full_clean()
        visita_bd.save()

        hay_posterior = (
            Visita.objects.filter(
                proyecto=proyecto,
                estado=Visita.Estado.REALIZADA,
                realizada_en__gt=realizada_en,
            )
            .exclude(pk=visita_bd.pk)
            .exists()
        )
        if not hay_posterior:
            proyecto.encargado_actual = empleado
            if proyecto.frecuencia_dias:
                proyecto.proxima_visita = timezone.localdate(realizada_en) + timedelta(
                    days=proyecto.frecuencia_dias
                )
            proyecto.save(
                update_fields=["encargado_actual", "proxima_visita", "actualizado"]
            )
    return visita_bd


def _validar_proyecto_y_qr(proyecto, qr_codigo):
    """Devuelve el proyecto (con sitio y cliente) si está activo y el QR corresponde."""
    pk = getattr(proyecto, "pk", proyecto)
    try:
        proyecto = Proyecto.objects.select_related("sitio__cliente").get(pk=pk)
    except (Proyecto.DoesNotExist, TypeError, ValueError):
        raise ValidationError({"proyecto": "El proyecto no existe o no está activo."})
    if proyecto.estado != Proyecto.Estado.ACTIVO:
        raise ValidationError({"proyecto": "El proyecto no existe o no está activo."})
    sitio = proyecto.sitio
    # Mismo mensaje para QR ajeno, sitio inactivo o cliente dado de baja: no se
    # revela el motivo.
    if (
        str(sitio.qr_codigo) != str(qr_codigo).lower()
        or not sitio.activo
        or not sitio.cliente.activo
    ):
        raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
    return proyecto


def _id_producto(item):
    """Id entero del producto de un ítem, o None si no es utilizable."""
    try:
        return int(item.get("producto"))
    except (TypeError, ValueError, AttributeError):
        return None


def _armar_productos(productos_aplicados):
    """Valida cada producto aplicado; devuelve (instancias sin guardar, errores).

    Busca todos los productos del pedido en una sola consulta.
    """
    ids = {_id_producto(item) for item in productos_aplicados} - {None}
    catalogo = Producto.objects.filter(pk__in=ids, activo=True).in_bulk()
    errores, instancias = [], []
    for posicion, item in enumerate(productos_aplicados, start=1):
        try:
            producto = catalogo[_id_producto(item)]
            aplicado = ProductoAplicado(
                producto=producto,
                lote=item.get("lote") or "",
                dosis=item.get("dosis"),
                unidad=item.get("unidad") or "",
                cantidad=item.get("cantidad"),
            )
            # El producto ya se leyó del catálogo: no se vuelve a consultar.
            aplicado.full_clean(exclude=["visita", "producto"])
        except (KeyError, TypeError, ValueError, AttributeError):
            errores.append(f"Producto {posicion}: no existe o está inactivo.")
        except ValidationError as error:
            detalle = "; ".join(
                m for lista in error.message_dict.values() for m in lista
            )
            errores.append(f"Producto {posicion}: {detalle}")
        else:
            instancias.append(aplicado)
    return instancias, errores


def _validar_coordenadas(latitud, longitud):
    """Errores por campo si la latitud o la longitud están fuera de rango."""
    errores = {}
    for clave, valor, limite in (
        ("latitud", latitud, 90),
        ("longitud", longitud, 180),
    ):
        try:
            fuera = valor is not None and not -limite <= valor <= limite
        except TypeError:
            fuera = True
        if fuera:
            errores[clave] = [f"Debe estar entre -{limite} y {limite}."]
    return errores


def _pendiente_para(proyecto, empleado):
    """Pendiente propia bloqueada (la más antigua) y si hay una de otro empleado."""
    pendientes = Visita.objects.filter(
        proyecto=proyecto, estado=Visita.Estado.PENDIENTE
    )
    propia = (
        pendientes.select_for_update()
        .filter(empleado=empleado)
        .order_by(F("programada_para").asc(nulls_last=True), "pk")
        .first()
    )
    return propia, pendientes.exclude(empleado=empleado).exists()


def registrar_visita_desde_app(
    *,
    empleado,
    proyecto,
    qr_codigo,
    cliente_uuid,
    realizada_en,
    latitud,
    longitud,
    precision_m,
    datos,
    productos_aplicados,
    fotos,
    observaciones="",
    incidencia=False,
    incidencia_detalle="",
):
    """Registra una visita hecha desde la app y devuelve la `Visita` realizada.

    `proyecto` es el id (o la instancia) del proyecto; `productos_aplicados` es una
    lista de dicts `{producto, lote, dosis, unidad, cantidad}` con `producto` como id;
    `fotos` es una lista de archivos subidos. Completa la pendiente propia más
    antigua del proyecto si no tiene fotos ni productos; si los tiene, o no hay
    pendiente propia, crea una visita nueva marcando `incidencia_asignacion` (también
    si hay una pendiente de otro empleado). Todo ocurre en una transacción: si algo
    falla no queda visita, fotos, productos ni archivos. Levanta `VisitaDuplicada`
    si el `cliente_uuid` ya existe y `ValidationError` con errores por campo (el
    `cliente_uuid` es obligatorio). Atención: no debe llamarse dentro de otro `atomic`:
    si el llamador revierte después, los archivos ya escritos no se recuperan.
    """
    if cliente_uuid is None:
        raise ValidationError({"cliente_uuid": "Este campo es obligatorio."})
    guardadas, confirmada = [], False
    try:
        with transaction.atomic():
            existente = Visita.objects.filter(cliente_uuid=cliente_uuid).first()
            if existente:
                raise VisitaDuplicada(existente)
            proyecto = _validar_proyecto_y_qr(proyecto, qr_codigo)

            errores = _validar_coordenadas(latitud, longitud)
            esquema = proyecto.tipo_servicio.esquema_planilla()
            errores_datos = validar_datos(esquema, datos)
            if errores_datos:
                errores["datos"] = [
                    mensaje if clave == "datos" else f"{clave}: {mensaje}"
                    for clave, mensajes in errores_datos.items()
                    for mensaje in mensajes
                ]
            if len(productos_aplicados) > MAX_PRODUCTOS:
                errores["productos_aplicados"] = [
                    f"Se permiten hasta {MAX_PRODUCTOS} productos por visita."
                ]
                aplicados, errores_productos = [], []
            else:
                aplicados, errores_productos = _armar_productos(productos_aplicados)
            if errores_productos:
                errores["productos_aplicados"] = errores_productos
            if not fotos:
                errores["fotos"] = ["Se requiere al menos una foto."]
            elif len(fotos) > MAX_FOTOS:
                errores["fotos"] = [f"Se permiten hasta {MAX_FOTOS} fotos por visita."]
            if errores:
                raise ValidationError(errores)

            visita, hay_de_otro = _pendiente_para(proyecto, empleado)
            if visita is not None and (
                visita.fotos.exists() or visita.productos.exists()
            ):
                # Una pendiente con evidencia no se hereda: queda intacta y la
                # visita de la app se registra aparte, marcada como incidencia.
                visita, hay_de_otro = None, True
            if visita is None:
                visita = Visita(
                    proyecto=proyecto,
                    empleado=empleado,
                    incidencia_asignacion=hay_de_otro,
                )
            else:
                visita.motivo_manual = ""
            visita.origen = Visita.Origen.APP
            visita.latitud, visita.longitud = latitud, longitud
            visita.precision_m = precision_m
            visita.datos = datos
            visita.observaciones = observaciones
            visita.incidencia = incidencia
            visita.incidencia_detalle = incidencia_detalle
            visita.cliente_uuid = cliente_uuid
            visita.recibida_en = timezone.now()
            visita.save()

            for orden, archivo in enumerate(fotos):
                foto = Foto(visita=visita, imagen=archivo, orden=orden)
                try:
                    foto.save()
                except ValidationError as error:
                    raise ValidationError({"fotos": error.messages})
                guardadas.append(foto)
            for aplicado in aplicados:
                aplicado.visita = visita
                aplicado.save()
            resultado = registrar_visita_realizada(visita, empleado, realizada_en)
        confirmada = True
        return resultado
    except IntegrityError:
        # Carrera: otro pedido con el mismo `cliente_uuid` ganó.
        existente = Visita.objects.filter(cliente_uuid=cliente_uuid).first()
        if existente:
            raise VisitaDuplicada(existente)
        raise
    finally:
        if not confirmada:
            # La transacción revierte la base, no los archivos ya escritos.
            for foto in guardadas:
                try:
                    foto.imagen.storage.delete(foto.imagen.name)
                except Exception:  # noqa: BLE001
                    # No debe tapar la excepción original que se está propagando.
                    logger.exception("No se pudo borrar un archivo de foto.")


def marcar_incidencia_revisada(visita, administrador):
    """Registra quién y cuándo revisó la incidencia de una visita."""
    if not visita.incidencia:
        raise ValidationError("La visita no tiene incidencia para revisar.")
    if visita.incidencia_revisada_en is not None:
        raise ValidationError("La incidencia ya fue revisada.")
    visita.incidencia_revisada_por = administrador
    visita.incidencia_revisada_en = timezone.now()
    visita.save(
        update_fields=[
            "incidencia_revisada_por",
            "incidencia_revisada_en",
            "actualizado",
        ]
    )
    return visita
