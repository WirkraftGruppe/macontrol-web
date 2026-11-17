"""Datos estructurados (JSON-LD) del sitio, armados desde `Configuracion`."""

import json

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

# Los mismos reemplazos que `django.utils.html.json_script`.
_ESCAPES = {
    ord(">"): "\\" + "u003E",
    ord("<"): "\\" + "u003C",
    ord("&"): "\\" + "u0026",
}


def datos_estructurados(config):
    """Dict `LocalBusiness` con lo que haya cargado en la configuración."""
    datos = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": config.razon_social,
        "url": settings.SITE_URL + "/",
        "logo": settings.SITE_URL + static("img/icono-512.png"),
        "image": settings.SITE_URL + static("img/og-macontrol.png"),
    }
    if config.telefono_internacional:
        datos["telephone"] = config.telefono_internacional
    if config.telefono_2_internacional:
        datos["contactPoint"] = [
            {
                "@type": "ContactPoint",
                "telephone": config.telefono_2_internacional,
                "contactType": "customer service",
                "areaServed": "AR",
                "availableLanguage": "es",
            }
        ]
    if config.correo:
        datos["email"] = config.correo
    if config.cuit:
        datos["taxID"] = config.cuit
    if config.direcciones:
        direccion = config.direcciones[0]
        datos["address"] = {
            "@type": "PostalAddress",
            "streetAddress": direccion.get("direccion", ""),
            "addressLocality": direccion.get("localidad", ""),
            "addressRegion": direccion.get("provincia", ""),
            "addressCountry": "AR",
        }
    if config.atiende_24_horas:
        datos["openingHoursSpecification"] = {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            "opens": "00:00",
            "closes": "23:59",
        }
    enlaces = [r["url"] for r in config.redes if r.get("url")]
    if enlaces:
        datos["sameAs"] = enlaces
    return datos


def json_ld(datos):
    """Serializa a JSON escapando `<`, `>` y `&`, listo para un `<script>` de datos."""
    return mark_safe(json.dumps(datos, ensure_ascii=False).translate(_ESCAPES))
