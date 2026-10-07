"""Vistas del sitio público: contenido desde la base, sin formularios."""

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse

from .models import ClienteDestacado, Configuracion, PaginaServicio, Sector

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
        "paginas_nav": PaginaServicio.objects.publicadas(),
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


def servicio(request, slug):
    pagina = get_object_or_404(PaginaServicio.objects.publicadas(), tipo__slug=slug)
    if pagina.imagen_portada:
        portada = {"url": pagina.imagen_portada.url, "ancho": 1200, "alto": 675}
    else:
        portada = _imagen(PORTADA_POR_SLUG.get(slug, "hero"))
    return _pagina(
        request,
        "web/paginas/servicio.html",
        titulo=pagina.titulo_seo or pagina.tipo.nombre,
        descripcion=pagina.resumen,
        ruta=pagina.get_absolute_url(),
        og_imagen=portada["url"],
        pagina=pagina,
        portada=portada,
        sectores=[
            Sector(valor).label for valor in pagina.sectores if valor in Sector.values
        ],
        relacionados=PaginaServicio.objects.publicadas().exclude(pk=pagina.pk),
    )


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
    rutas += [p.get_absolute_url() for p in PaginaServicio.objects.publicadas()]
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
