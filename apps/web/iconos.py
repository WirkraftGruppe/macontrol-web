"""Iconos de línea de los servicios: el atributo `d` de un `<svg>` de 24×24 por slug."""

ICONO_POR_SLUG = {
    "desinfeccion-sanitizacion-desodorizacion": (
        "M12 3 C12 3 6 10 6 14.5 a6 6 0 0 0 12 0 C18 10 12 3 12 3 z "
        "M9.5 15 a2.5 2.5 0 0 0 2.5 2.5"
    ),
    "control-plagas-urbanas": (
        "M12 9.5 c2.5 0 4.5 2.4 4.5 5.5 s-2 5.5 -4.5 5.5 s-4.5 -2.4 -4.5 -5.5 "
        "s2 -5.5 4.5 -5.5 z M12 9.5 V20.5 M9.8 7.5 a2.2 2.2 0 0 1 4.4 0 "
        "M9.5 5.5 L8 3 M14.5 5.5 L16 3 M7.6 13 H3.5 M7.8 17 L4 19 "
        "M16.4 13 H20.5 M16.2 17 L20 19"
    ),
    "servicio-mipu": (
        "M12 3 l8 3 v6 c0 5 -3.5 8 -8 9 c-4.5 -1 -8 -4 -8 -9 V6 z "
        "M8.5 12 l2.5 2.5 l4.5 -5"
    ),
    "mosquitos-vectores": (
        "M12 3 a9 9 0 1 0 0 18 a9 9 0 0 0 0 -18 z M5.6 5.6 L18.4 18.4 "
        "M12 9 v6 M9.5 10.5 L7.5 9 M14.5 10.5 L16.5 9"
    ),
    "control-murcielagos": "M20 14.5 A8.5 8.5 0 1 1 9.5 4 a6.5 6.5 0 0 0 10.5 10.5 z",
    "exclusion-palomas-aves": (
        "M20 4 C12 4 6 9.5 6 17 v3 M6 17 C14 17 20 12 20 4 M6 17 L14.5 8.5 "
        "M10 13 h4.5 M12.5 10.5 h3.5"
    ),
    "limpieza-tanques-cisternas": (
        "M5 6 c0 -1.7 3.1 -3 7 -3 s7 1.3 7 3 s-3.1 3 -7 3 s-7 -1.3 -7 -3 z "
        "M5 6 v12 c0 1.7 3.1 3 7 3 s7 -1.3 7 -3 V6 "
        "M5 12 c0 1.7 3.1 3 7 3 s7 -1.3 7 -3"
    ),
    "manejo-plagas-edificios": (
        "M5 21 V4 h10 v17 M15 10 h4 v11 M3 21 h18 M8.5 8 h3 M8.5 12 h3 M8.5 16 h3"
    ),
    "mantenimiento-edilicio": (
        "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1"
        "-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94"
        "l-3.76 3.76z"
    ),
}

# Respaldo para un servicio nuevo sin icono propio: círculo con marca de verificación.
ICONO_GENERICO = "M12 3 a9 9 0 1 0 0 18 a9 9 0 0 0 0 -18 z M8 12.5 l2.8 2.8 l5.2 -5.6"


def icono_de(slug):
    """El trazado del icono del servicio, o el genérico si no tiene uno propio."""
    return ICONO_POR_SLUG.get(slug, ICONO_GENERICO)
