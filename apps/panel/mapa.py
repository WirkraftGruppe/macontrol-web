"""Mapa de sitios: datos agregados por sitio con el peor estado de sus puntos."""

from django.db.models import Max, Prefetch, Q
from django.urls import NoReverseMatch, reverse

from apps.proyectos.models import Proyecto
from apps.sitios.estado import estados_de_puntos, peor_estado_punto
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import Visita

ORIGEN_TESELAS = "https://tile.openstreetmap.org"


def url_ficha(sitio):
    """URL de la ficha del sitio, o None mientras la ruta no exista."""
    try:
        return reverse("panel:sitios:ficha", args=[sitio.pk])
    except NoReverseMatch:
        return None


def _fecha(valor):
    return valor.isoformat() if valor else None


def sitios_para_mapa(cliente=None, servicio=None, estado=None):
    """Sitios activos con coordenadas, en un número fijo de consultas."""
    proyectos = Proyecto.objects.filter(estado=Proyecto.Estado.ACTIVO)
    if servicio:
        proyectos = proyectos.filter(tipo_servicio_id=servicio)
    proyectos = proyectos.select_related("tipo_servicio", "encargado_actual").annotate(
        ultima_visita=Max(
            "visitas__cerrada_en", filter=Q(visitas__estado=Visita.Estado.REALIZADA)
        )
    )
    sitios = (
        Sitio.objects.filter(activo=True, latitud__isnull=False, longitud__isnull=False)
        .select_related("cliente")
        .prefetch_related(
            Prefetch("proyectos", queryset=proyectos, to_attr="activos"),
            Prefetch(
                "puntos",
                queryset=PuntoControl.objects.filter(activo=True),
                to_attr="puntos_activos",
            ),
        )
    )
    if cliente:
        sitios = sitios.filter(cliente_id=cliente)
    if servicio:
        sitios = sitios.filter(
            proyectos__estado=Proyecto.Estado.ACTIVO,
            proyectos__tipo_servicio_id=servicio,
        ).distinct()

    sitios = list(sitios)
    # Una sola llamada para todos los puntos: el costo no crece con los sitios.
    estados = estados_de_puntos(p for s in sitios for p in s.puntos_activos)
    resultado = []
    for sitio in sitios:
        color = peor_estado_punto(estados[p.pk] for p in sitio.puntos_activos)
        if estado and color != estado:
            continue
        ultimas = [p.ultima_visita for p in sitio.activos if p.ultima_visita]
        resultado.append(
            {
                "id": sitio.pk,
                "nombre": sitio.nombre,
                "cliente": sitio.cliente.razon_social,
                "lat": float(sitio.latitud),
                "lng": float(sitio.longitud),
                "estado": color.value,
                "ultima_visita": _fecha(max(ultimas, default=None)),
                "url_ficha": url_ficha(sitio),
                "proyectos": [
                    {
                        "titulo": p.titulo,
                        "servicio": p.tipo_servicio.nombre,
                        "estado": p.estado_visita.value,
                        "proxima_visita": _fecha(p.proxima_visita),
                        "ultima_visita": _fecha(p.ultima_visita),
                        "encargado": p.encargado_actual.get_full_name()
                        or p.encargado_actual.get_username(),
                    }
                    for p in sitio.activos
                ],
            }
        )
    return resultado
