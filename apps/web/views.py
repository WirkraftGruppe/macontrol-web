"""Vistas del sitio público: contenido desde la base, sin formularios."""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_safe

from .models import ClienteDestacado, Configuracion, Sector, Servicio

# Imagen estática, con su tamaño real, para las páginas sin portada cargada.
IMAGENES = {
    "hero": ("img/hero-pulverizacion-quincho.webp", 672, 1536),
    "empresa": ("img/empresa-oficina-equipo.webp", 1193, 896),
    "mantenimiento": ("img/mantenimiento-fachada-andamio.webp", 1201, 1600),
    "fumigacion": ("img/fumigacion-termonebulizacion-cocina.webp", 768, 1365),
    "flota": ("img/flota-vehiculos-industria.webp", 1365, 768),
}
PORTADA_POR_SLUG = {
    "desinfeccion-sanitizacion-desodorizacion": "fumigacion",
    "control-plagas-urbanas": "hero",
    "servicio-mipu": "empresa",
    "mosquitos-vectores": "fumigacion",
    "exclusion-palomas-aves": "mantenimiento",
    "mantenimiento-edilicio": "mantenimiento",
    "manejo-plagas-edificios": "flota",
}


def _imagen(clave):
    ruta, ancho, alto = IMAGENES[clave]
    return {"url": static(ruta), "ancho": ancho, "alto": alto}


def _pagina(request, plantilla, *, titulo, descripcion, ruta, og_imagen=None, **extra):
    """Renderiza una página pública con `config`, `paginas_nav` y los metadatos."""
    og_imagen = og_imagen or _imagen("hero")["url"]
    seo = {
        "titulo": titulo,
        "descripcion": descripcion,
        "url": settings.SITE_URL + ruta,
        "imagen": settings.SITE_URL + og_imagen
        if og_imagen.startswith("/")
        else og_imagen,
    }
    contexto = {
        "config": Configuracion.obtener(),
        "paginas_nav": Servicio.objects.publicados(),
        "seo": seo,
        **extra,
    }
    return render(request, plantilla, contexto)


def inicio(request):
    config = Configuracion.obtener()
    return _pagina(
        request,
        "web/paginas/inicio.html",
        titulo=f"{config.razon_social} · {config.eslogan}",
        descripcion=config.eslogan,
        ruta=reverse("web:inicio"),
        hero=_imagen("hero"),
        empresa_foto=_imagen("empresa"),
        edilicia=_imagen("mantenimiento"),
        sectores=Sector.choices,
        clientes=ClienteDestacado.objects.activos(),
    )


def contexto_servicio(servicio):
    """Argumentos de `_pagina` de un servicio, para la vista pública y la previa."""
    if servicio.foto:
        portada = {"url": servicio.foto.url, "ancho": 1200, "alto": 675}
    else:
        portada = _imagen(PORTADA_POR_SLUG.get(servicio.slug, "hero"))
    return {
        "titulo": servicio.titulo_seo or servicio.nombre,
        "descripcion": servicio.resumen,
        "ruta": servicio.get_absolute_url(),
        "og_imagen": portada["url"],
        "pagina": servicio,
        "portada": portada,
        "sectores": [
            Sector(valor).label for valor in servicio.sectores if valor in Sector.values
        ],
        "relacionados": Servicio.objects.publicados().exclude(pk=servicio.pk),
    }


def servicio(request, slug):
    pagina = get_object_or_404(Servicio.objects.publicados(), slug=slug)
    return _pagina(request, "web/paginas/servicio.html", **contexto_servicio(pagina))


def empresa(request):
    config = Configuracion.obtener()
    return _pagina(
        request,
        "web/paginas/empresa.html",
        titulo=f"Empresa · {config.razon_social}",
        descripcion=config.presentacion[:160] or config.eslogan,
        ruta=reverse("web:empresa"),
        og_imagen=_imagen("empresa")["url"],
        foto=_imagen("empresa"),
    )


def contacto(request):
    config = Configuracion.obtener()
    return _pagina(
        request,
        "web/paginas/contacto.html",
        titulo=f"Contacto · {config.razon_social}",
        descripcion=f"Llame al {config.telefono}. {config.eslogan}.",
        ruta=reverse("web:contacto"),
    )


def qr(request, codigo):
    """Aterrizaje de un QR en el navegador: no consulta la base ni usa el código."""
    return render(request, "web/paginas/qr.html")


def sitemap(request):
    rutas = [reverse("web:inicio"), reverse("web:empresa"), reverse("web:contacto")]
    rutas += [p.get_absolute_url() for p in Servicio.objects.publicados()]
    urls = [settings.SITE_URL + ruta for ruta in rutas]
    return render(
        request,
        "web/paginas/sitemap.xml",
        {"urls": urls},
        content_type="application/xml",
    )


def robots(request):
    contexto = {"sitemap": settings.SITE_URL + reverse("web:sitemap")}
    return render(
        request, "web/paginas/robots.txt", contexto, content_type="text/plain"
    )


CARPETAS_MEDIA_PUBLICAS = ("servicios", "clientes")
EXTENSIONES_MEDIA_PUBLICAS = (".png", ".jpg", ".jpeg", ".webp")


@require_safe
def media_publica(request, ruta):
    """Sirve solo las imágenes de `servicios/` y `clientes/`; todo lo demás es 404."""
    partes = ruta.split("/")
    if (
        len(partes) < 2
        or partes[0] not in CARPETAS_MEDIA_PUBLICAS
        or any(p in ("", ".", "..") or "\\" in p or ":" in p for p in partes)
        or Path(partes[-1]).suffix.lower() not in EXTENSIONES_MEDIA_PUBLICAS
    ):
        raise Http404
    carpeta = (Path(settings.MEDIA_ROOT) / partes[0]).resolve()
    archivo = (carpeta / "/".join(partes[1:])).resolve()
    if not archivo.is_relative_to(carpeta) or not archivo.is_file():
        raise Http404
    tipo = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
    respuesta = FileResponse(archivo.open("rb"), content_type=tipo)
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "public, max-age=86400"
    return respuesta
