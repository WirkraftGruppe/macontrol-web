import logging
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone
from simple_history.utils import update_change_reason

from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.sitios.models import PuntoControl
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita
from apps.visitas.planillas import validar_datos

# Topes de una revisión desde la app; los comparte el serializer de la API.
MAX_FOTOS = 10
MAX_PRODUCTOS = 30
TOLERANCIA_FUTURO = timedelta(minutes=10)
MENSAJE_QR_INVALIDO = "El código QR no corresponde a este proyecto."
# Precisión máxima (metros) para que una revisión proponga la ubicación del punto.
PRECISION_MAXIMA_PROPUESTA_M = 50

logger = logging.getLogger(__name__)


class RevisionDuplicada(Exception):
    """El `cliente_uuid` ya fue registrado; `revision` es la revisión existente."""

    def __init__(self, revision):
        super().__init__("La revisión ya fue registrada.")
        self.revision = revision


@contextmanager
def _transaccion_con_archivos():
    """Transacción que, si falla, borra los archivos de las fotos ya escritas.

    Entrega la lista donde el cuerpo anota las fotos guardadas. La transacción
    revierte la base, no los archivos.
    """
    guardadas, confirmada = [], False
    try:
        with transaction.atomic():
            yield guardadas
        confirmada = True
    finally:
        if not confirmada:
            _borrar_archivos(guardadas)


def _cargar_proyecto(proyecto):
    """Devuelve el proyecto (con sitio y cliente) si existe y está activo."""
    pk = getattr(proyecto, "pk", proyecto)
    try:
        proyecto = Proyecto.objects.select_related("sitio__cliente").get(pk=pk)
    except (Proyecto.DoesNotExist, TypeError, ValueError):
        raise ValidationError({"proyecto": "El proyecto no existe o no está activo."})
    if proyecto.estado != Proyecto.Estado.ACTIVO:
        raise ValidationError({"proyecto": "El proyecto no existe o no está activo."})
    return proyecto


def _resolver_punto(proyecto, qr_codigo):
    """Punto activo del sitio del proyecto que tiene ese QR; si no, error genérico.

    Mismo mensaje para QR ajeno, punto o sitio inactivo y cliente dado de baja: no
    se revela el motivo.
    """
    try:
        codigo = UUID(str(qr_codigo))
    except ValueError:
        raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
    punto = (
        PuntoControl.objects.select_related("sitio__cliente")
        .filter(qr_codigo=codigo, activo=True, sitio_id=proyecto.sitio_id)
        .first()
    )
    if punto is None or not punto.sitio.activo or not punto.sitio.cliente.activo:
        raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
    return punto


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
            aplicado.full_clean(exclude=["revision", "producto"])
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


def _validar_coordenadas(latitud, longitud, obligatorias=False):
    """Errores por campo si la latitud o la longitud faltan (si son obligatorias)
    o están fuera de rango."""
    errores = {}
    for clave, valor, limite in (
        ("latitud", latitud, 90),
        ("longitud", longitud, 180),
    ):
        if valor is None and obligatorias:
            errores[clave] = ["Este campo es obligatorio."]
            continue
        try:
            fuera = valor is not None and not -limite <= valor <= limite
        except TypeError:
            fuera = True
        if fuera:
            errores[clave] = [f"Debe estar entre -{limite} y {limite}."]
    return errores


def _errores_planilla(esquema, datos):
    """Mensajes de la planilla contra su esquema (lista vacía si es válida)."""
    return [
        mensaje if clave == "datos" else f"{clave}: {mensaje}"
        for clave, mensajes in validar_datos(esquema, datos).items()
        for mensaje in mensajes
    ]


def _validar_evidencia(esquema, datos, productos_aplicados):
    """Valida planilla y productos; devuelve (errores por campo, productos armados)."""
    errores = {}
    errores_datos = _errores_planilla(esquema, datos)
    if errores_datos:
        errores["datos"] = errores_datos
    if len(productos_aplicados) > MAX_PRODUCTOS:
        errores["productos_aplicados"] = [
            f"Se permiten hasta {MAX_PRODUCTOS} productos por revisión."
        ]
        return errores, []
    aplicados, errores_productos = _armar_productos(productos_aplicados)
    if errores_productos:
        errores["productos_aplicados"] = errores_productos
    return errores, aplicados


def _borrar_archivos(fotos):
    """Borra del almacenamiento los archivos de fotos de una operación fallida."""
    for foto in fotos:
        try:
            foto.imagen.storage.delete(foto.imagen.name)
        except Exception:  # noqa: BLE001
            # No debe tapar la excepción original que se está propagando.
            logger.exception("No se pudo borrar un archivo de foto.")


def _pendiente_para(proyecto, empleado):
    """Pendiente propia bloqueada (la más antigua) y si hay una de otro empleado."""
    pendientes = Visita.objects.filter(
        proyecto=proyecto, estado=Visita.Estado.PENDIENTE
    )
    # Una pendiente con revisiones (evidencia migrada) no se reutiliza.
    sin_revisiones = ~Exists(Revision.objects.filter(visita=OuterRef("pk")))
    propia = (
        pendientes.select_for_update()
        .filter(sin_revisiones, empleado=empleado)
        .order_by(F("programada_para").asc(nulls_last=True), "pk")
        .first()
    )
    return propia, pendientes.exclude(empleado=empleado).exists()


def abrir_visita(*, empleado, proyecto):
    """Abre la jornada del empleado en el proyecto; devuelve `(visita, creada)`.

    Es idempotente: si el empleado ya tiene una visita abierta para el proyecto la
    devuelve con `creada=False`. Si tiene una pendiente asignada, la abre. Si no,
    crea una nueva, con `incidencia_asignacion` cuando otro empleado tiene la
    pendiente. Levanta `ValidationError` si el proyecto, su sitio o su cliente no
    están activos.
    """
    with transaction.atomic():
        proyecto = _cargar_proyecto(proyecto)
        if not (proyecto.sitio.activo and proyecto.sitio.cliente.activo):
            raise ValidationError(
                {"proyecto": "El proyecto no existe o no está activo."}
            )
        # Serializa las aperturas del mismo proyecto: no quedan dos abiertas.
        Proyecto.objects.select_for_update(of=("self",)).get(pk=proyecto.pk)
        abierta = (
            Visita.objects.select_for_update()
            .filter(proyecto=proyecto, empleado=empleado, estado=Visita.Estado.ABIERTA)
            .order_by("pk")
            .first()
        )
        if abierta is not None:
            return abierta, False
        propia, hay_de_otro = _pendiente_para(proyecto, empleado)
        ahora = timezone.now()
        if propia is not None:
            propia.estado = Visita.Estado.ABIERTA
            propia.abierta_en = ahora
            propia.origen = Visita.Origen.APP
            propia.motivo_manual = ""
            propia.save()
            return propia, True
        visita = Visita.objects.create(
            proyecto=proyecto,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=ahora,
            incidencia_asignacion=hay_de_otro,
        )
        return visita, True


def _proponer_ubicacion(punto, revision):
    """Guarda las coordenadas de la revisión como ubicación propuesta del punto.

    Solo si el punto no tiene lat/lng, la precisión es de a lo sumo 50 m y no hay
    otra propuesta pendiente (la actualización condicional lo decide en la base).
    """
    precision = revision.precision_m
    if (
        revision.latitud is None
        or revision.longitud is None
        or precision is None
        or precision > PRECISION_MAXIMA_PROPUESTA_M
    ):
        return
    PuntoControl.objects.filter(
        Q(latitud__isnull=True) | Q(longitud__isnull=True),
        pk=punto.pk,
        ubicacion_propuesta__isnull=True,
    ).update(
        ubicacion_propuesta={
            "latitud": f"{revision.latitud:.6f}",
            "longitud": f"{revision.longitud:.6f}",
            "precision_m": f"{precision:.1f}",
            "revision": revision.pk,
        }
    )


def _guardar_fotos_y_productos(revision, fotos, aplicados, guardadas):
    for orden, archivo in enumerate(fotos):
        foto = Foto(revision=revision, imagen=archivo, orden=orden)
        try:
            foto.save()
        except ValidationError as error:
            raise ValidationError({"fotos": error.messages})
        guardadas.append(foto)
    for aplicado in aplicados:
        aplicado.revision = revision
        aplicado.save()


def _guardar_revision(
    *,
    visita,
    qr_codigo,
    cliente_uuid,
    realizada_en,
    latitud,
    longitud,
    precision_m,
    datos,
    productos_aplicados,
    fotos,
    observaciones,
    incidencia,
    incidencia_detalle,
    guardadas,
):
    """Valida y crea la revisión dentro de la transacción del llamador."""
    proyecto = _cargar_proyecto(visita.proyecto_id)
    punto = _resolver_punto(proyecto, qr_codigo)
    errores = _validar_coordenadas(latitud, longitud, obligatorias=True)
    esquema = proyecto.tipo_servicio.esquema_planilla("punto")
    errores_evidencia, aplicados = _validar_evidencia(
        esquema, datos, productos_aplicados
    )
    errores.update(errores_evidencia)
    if not fotos:
        errores["fotos"] = ["Se requiere al menos una foto."]
    elif len(fotos) > MAX_FOTOS:
        errores["fotos"] = [f"Se permiten hasta {MAX_FOTOS} fotos por revisión."]
    ahora = timezone.now()
    if realizada_en > ahora + TOLERANCIA_FUTURO:
        errores["realizada_en"] = ["La fecha de realización no puede ser futura."]
    elif realizada_en < ahora - timedelta(hours=settings.ATRASO_MAXIMO_HORAS):
        errores["realizada_en"] = [
            f"La revisión tiene más de {settings.ATRASO_MAXIMO_HORAS} horas de "
            "atraso. Avise al administrador para que la cargue como manual."
        ]
    if errores:
        raise ValidationError(errores)

    revision = Revision.objects.create(
        visita=visita,
        punto=punto,
        orden=visita.revisiones.count() + 1,
        realizada_en=realizada_en,
        recibida_en=ahora,
        cliente_uuid=cliente_uuid,
        latitud=latitud,
        longitud=longitud,
        precision_m=precision_m,
        datos=datos,
        esquema_planilla=esquema,
        observaciones=observaciones,
        incidencia=incidencia,
        incidencia_detalle=incidencia_detalle,
    )
    _guardar_fotos_y_productos(revision, fotos, aplicados, guardadas)
    _proponer_ubicacion(punto, revision)
    return revision


def _duplicada(cliente_uuid):
    return (
        Revision.objects.select_related("visita")
        .filter(cliente_uuid=cliente_uuid)
        .first()
    )


def registrar_revision(
    *,
    visita,
    empleado,
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
    """Registra el escaneo de un punto en una visita abierta y devuelve la `Revision`.

    `visita` es la instancia o el id; `qr_codigo` es el del punto (el servidor lo
    resuelve y exige que sea de un punto activo del sitio del proyecto);
    `productos_aplicados` es una lista de dicts con `producto` como id; `fotos`, una
    lista de archivos. Valida coordenadas, de 1 a `MAX_FOTOS` fotos, planilla de
    ámbito `punto` y el atraso. Si el punto no tiene ubicación, propone la de la
    revisión. Todo ocurre en una transacción (y sin fotos huérfanas si falla).
    Levanta `RevisionDuplicada` si el `cliente_uuid` ya existe y `ValidationError`
    con errores por campo. No debe llamarse dentro de otro `atomic`.
    """
    if cliente_uuid is None:
        raise ValidationError({"cliente_uuid": "Este campo es obligatorio."})
    try:
        with _transaccion_con_archivos() as guardadas:
            existente = _duplicada(cliente_uuid)
            if existente:
                raise RevisionDuplicada(existente)
            try:
                visita_bd = Visita.objects.select_for_update().get(
                    pk=getattr(visita, "pk", visita)
                )
            except (Visita.DoesNotExist, TypeError, ValueError):
                raise ValidationError({"visita": "La visita no existe."})
            if (
                visita_bd.estado != Visita.Estado.ABIERTA
                or visita_bd.empleado_id != empleado.pk
            ):
                raise ValidationError(
                    {"visita": "La visita no está abierta o no es suya."}
                )
            return _guardar_revision(
                visita=visita_bd,
                qr_codigo=qr_codigo,
                cliente_uuid=cliente_uuid,
                realizada_en=realizada_en,
                latitud=latitud,
                longitud=longitud,
                precision_m=precision_m,
                datos=datos,
                productos_aplicados=productos_aplicados,
                fotos=fotos,
                observaciones=observaciones,
                incidencia=incidencia,
                incidencia_detalle=incidencia_detalle,
                guardadas=guardadas,
            )
    except IntegrityError:
        # Carrera: otro pedido con el mismo `cliente_uuid` ganó.
        existente = _duplicada(cliente_uuid)
        if existente:
            raise RevisionDuplicada(existente)
        raise


def _cerrar_sin_revisiones(visita):
    """Cierre por sistema de una visita sin revisiones: no toca el proyecto.

    Si venía asignada vuelve a pendiente; si no, queda cancelada.
    """
    if visita.asignada_por_id:
        visita.estado = Visita.Estado.PENDIENTE
        visita.abierta_en = None
        visita.cierre = ""
    else:
        visita.estado = Visita.Estado.CANCELADA
        visita.cierre = Visita.Cierre.SISTEMA
    visita.full_clean()
    visita.save()
    return visita


def cerrar_visita(
    visita,
    *,
    quien,
    cierre,
    datos=None,
    observaciones=None,
    incidencia=None,
    incidencia_detalle=None,
    cerrada_en=None,
):
    """Cierra la visita abierta y actualiza el proyecto; devuelve la copia cerrada.

    La instancia recibida no se modifica: todo ocurre sobre una copia bloqueada.
    Exige al menos una revisión, salvo en el cierre por sistema (ver
    `_cerrar_sin_revisiones`). `datos` es la planilla de ámbito `visita` (se valida,
    salvo en el cierre por sistema). `cerrada_en` es la hora de cierre: por defecto
    ahora, o la de la última revisión en el cierre por sistema. Solo la visita más
    reciente del proyecto fija `encargado_actual` y `proxima_visita`.
    """
    if cierre not in Visita.Cierre.values:
        raise ValidationError({"cierre": "Tipo de cierre inválido."})
    with transaction.atomic():
        visita_bd = Visita.objects.select_for_update().get(pk=visita.pk)
        proyecto = (
            Proyecto.objects.select_for_update(of=("self",))
            .select_related("tipo_servicio")
            .get(pk=visita_bd.proyecto_id)
        )

        if visita_bd.estado != Visita.Estado.ABIERTA:
            raise ValidationError("Solo se puede cerrar una visita abierta.")
        if cierre == Visita.Cierre.EMPLEADO and (
            quien is None or quien.pk != visita_bd.empleado_id
        ):
            raise ValidationError("Solo el empleado de la visita puede cerrarla.")
        if cierre == Visita.Cierre.ADMINISTRADOR and not (
            quien is not None and quien.es_administrador
        ):
            raise ValidationError("Solo un administrador puede cerrar de este modo.")
        revisiones = visita_bd.revisiones.all()
        if cierre != Visita.Cierre.ADMINISTRADOR:
            # Cuentan las recibidas durante esta jornada (hora del servidor, no la
            # del teléfono): la evidencia heredada de una migración no.
            revisiones = revisiones.filter(recibida_en__gte=visita_bd.abierta_en)
        ultima = revisiones.order_by("-realizada_en", "-id").first()
        if ultima is None:
            if cierre != Visita.Cierre.SISTEMA:
                raise ValidationError("La visita necesita al menos una revisión.")
            return _cerrar_sin_revisiones(visita_bd)
        if (
            visita_bd.origen == Visita.Origen.MANUAL
            and not (visita_bd.motivo_manual or "").strip()
        ):
            raise ValidationError("Una visita manual exige el motivo.")

        if cerrada_en is None:
            sistema = cierre == Visita.Cierre.SISTEMA
            cerrada_en = ultima.realizada_en if sistema else timezone.now()
        if cerrada_en > timezone.now() + TOLERANCIA_FUTURO:
            raise ValidationError("La fecha de cierre no puede ser futura.")
        esquema = proyecto.tipo_servicio.esquema_planilla("visita")
        if datos is not None:
            visita_bd.datos = datos
        if cierre != Visita.Cierre.SISTEMA:
            errores = _errores_planilla(esquema, visita_bd.datos)
            if errores:
                raise ValidationError({"datos": errores})
        for campo, valor in (
            ("observaciones", observaciones),
            ("incidencia", incidencia),
            ("incidencia_detalle", incidencia_detalle),
        ):
            if valor is not None:
                setattr(visita_bd, campo, valor)
        visita_bd.esquema_planilla = esquema
        visita_bd.estado = Visita.Estado.REALIZADA
        visita_bd.cierre = cierre
        visita_bd.cerrada_en = cerrada_en
        visita_bd.full_clean()
        visita_bd.save()

        hay_posterior = (
            Visita.objects.filter(
                proyecto=proyecto,
                estado=Visita.Estado.REALIZADA,
                cerrada_en__gt=cerrada_en,
            )
            .exclude(pk=visita_bd.pk)
            .exists()
        )
        if not hay_posterior:
            proyecto.encargado_actual = visita_bd.empleado
            if proyecto.frecuencia_dias:
                proyecto.proxima_visita = timezone.localdate(cerrada_en) + timedelta(
                    days=proyecto.frecuencia_dias
                )
            proyecto.save(
                update_fields=["encargado_actual", "proxima_visita", "actualizado"]
            )
    return visita_bd


def registrar_visita_manual(
    *,
    proyecto,
    empleado,
    administrador,
    motivo,
    realizada_en,
    puntos,
    datos,
    productos_aplicados,
    fotos,
    pendiente=None,
    confirmar_atraso=False,
    datos_visita=None,
    observaciones="",
    incidencia=False,
    incidencia_detalle="",
):
    """Registra una visita cargada a mano por un administrador y la devuelve.

    Crea una revisión por cada punto de `puntos`, todas con la planilla `datos`
    (ámbito `punto`); las fotos y los productos quedan en la revisión del primer
    punto por `orden`. Cierra la visita con `cierre=administrador` y `cerrada_en`
    igual a `realizada_en`; `datos_visita` es la planilla de ámbito `visita`. Crea
    la visita, o completa `pendiente`, con `origen=manual`. Una carga con más de
    `ATRASO_MAXIMO_HORAS` de atraso exige `confirmar_atraso` y deja la confirmación
    en el historial. Todo ocurre en una transacción; si algo falla no queda nada,
    tampoco los archivos. Levanta `ValidationError` con errores por campo. No debe
    llamarse dentro de otro `atomic`.
    """
    with _transaccion_con_archivos() as guardadas:
        errores = {}
        if not (motivo or "").strip():
            errores["motivo"] = ["El motivo de la carga manual es obligatorio."]
        if proyecto.estado != Proyecto.Estado.ACTIVO:
            errores["proyecto"] = ["El proyecto no está activo."]
        if not (empleado.is_active and empleado.es_empleado):
            errores["empleado"] = ["Debe ser un empleado activo."]
        horas = settings.ATRASO_MAXIMO_HORAS
        atrasada = realizada_en < timezone.now() - timedelta(hours=horas)
        if atrasada and not confirmar_atraso:
            errores["confirmar_atraso"] = [
                f"La visita tiene más de {horas} horas de atraso: "
                "confirme la carga para continuar."
            ]
        puntos = sorted(puntos, key=lambda p: (p.orden, p.pk))
        if not puntos:
            errores["puntos"] = ["Elija al menos un punto de control."]
        elif any(not p.activo or p.sitio_id != proyecto.sitio_id for p in puntos):
            errores["puntos"] = [
                "Los puntos deben ser activos y del sitio del proyecto."
            ]
        esquema_punto = proyecto.tipo_servicio.esquema_planilla("punto")
        errores_evidencia, aplicados = _validar_evidencia(
            esquema_punto, datos, productos_aplicados
        )
        errores.update(errores_evidencia)
        if len(fotos) > MAX_FOTOS:
            errores["fotos"] = [f"Se permiten hasta {MAX_FOTOS} fotos por revisión."]
        visita = None
        if pendiente is not None:
            visita = Visita.objects.select_for_update().get(pk=pendiente.pk)
            if (
                visita.proyecto_id != proyecto.pk
                or visita.estado != Visita.Estado.PENDIENTE
            ):
                errores["pendiente"] = ["La visita no es una pendiente del proyecto."]
        if errores:
            raise ValidationError(errores)

        if visita is None:
            visita = Visita(proyecto=proyecto)
        visita.empleado = empleado
        visita.origen = Visita.Origen.MANUAL
        visita.motivo_manual = motivo.strip()
        visita.asignada_por = administrador
        visita.estado = Visita.Estado.ABIERTA
        visita.abierta_en = realizada_en
        visita.save()

        ahora = timezone.now()
        for orden, punto in enumerate(puntos, start=1):
            revision = Revision.objects.create(
                visita=visita,
                punto=punto,
                orden=orden,
                realizada_en=realizada_en,
                recibida_en=ahora,
                datos=datos,
                esquema_planilla=esquema_punto,
            )
            if orden == 1:
                _guardar_fotos_y_productos(revision, fotos, aplicados, guardadas)
        resultado = cerrar_visita(
            visita,
            quien=administrador,
            cierre=Visita.Cierre.ADMINISTRADOR,
            datos=datos_visita,
            observaciones=observaciones,
            incidencia=incidencia,
            incidencia_detalle=incidencia_detalle,
            cerrada_en=realizada_en,
        )
        if atrasada:
            update_change_reason(
                resultado,
                f"Carga manual atrasada confirmada por {administrador.get_username()}",
            )
    return resultado


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
