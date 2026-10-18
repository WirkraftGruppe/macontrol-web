# Decisiones del sitio público de MAControl

Formato: `- AAAA-MM-DD — decisión — motivo — reemplaza a: (nada|fecha)`. La más reciente abajo.
Una decisión no se edita: se agrega otra que la reemplaza y la nombra por su fecha.

Este archivo arranca con el plan `web-independiente` (2026-10-17), cuando el repositorio quedó solo con el sitio público. Las decisiones del proyecto completo (sitio, panel, API) están sin editar en `docs/historico/decisiones-proyecto-completo.md`; las que siguen vigentes para el sitio se trasladan abajo con su fecha original.

## Trasladadas del proyecto completo (vigentes)

- 2026-09-28 — Razón social en textos: MAControl S.A.; el logo "MAControl Group" entregado se usa de forma provisoria — indicación del dueño — reemplaza a: (nada)
- 2026-09-29 — El sitio público no ofrece "pedir presupuesto" ni formularios que envíen correo; el contacto es telefónico (y WhatsApp si el número lo atiende) — los presupuestos se hacen por contacto directo con la empresa — reemplaza a: (nada)
- 2026-09-29 — Tests con el runner de Django (`manage.py test --keepdb`), no pytest — es la forma que ejecutan los agentes y hooks — reemplaza a: (nada)
- 2026-10-01 — Fuentes Barlow autohospedadas en `static/fonts/` (woff2 de @fontsource, subconjunto latin, OFL); sin Google Fonts — la IP de cada visitante no se entrega a un tercero y la CSP no necesita orígenes externos — reemplaza a: (nada)
- 2026-10-01 — Barrera de hosts en `dev.py`: con `DJANGO_ENV=development` solo se aceptan hosts locales, `testserver` e IP privadas o de loopback en `ALLOWED_HOSTS`; cualquier otro host aborta el arranque — impide publicar el sitio con `DEBUG=True` por error de configuración — reemplaza a: (nada)
- 2026-10-07 — La sección de sectores muestra los 12 de la Carta de Servicios — elección del usuario — reemplaza a: (nada)
- 2026-10-07 — El cliente "YPF / Casa Rucery [?]" entra al fixture como "YPF" — elección del usuario — reemplaza a: (nada)
- 2026-10-07 — `base_web.html` es autónoma — es la única base del sitio público — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `sitemap.xml` y `robots.txt` son vistas propias, y las 404 y 500 son plantillas de `apps/web` sin `handler` en `config/urls.py` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `faq` queda vacía en el fixture y la sección de preguntas frecuentes no se muestra si está vacía — la Carta no trae preguntas frecuentes y no se inventa contenido — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — Los textos institucionales fijos (cuatro respaldos, tres valores, cuatro pasos) van literales de la Carta en las plantillas; los datos variables, en `Configuracion` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `sectores` es un JSON de valores de `Sector` (12 `TextChoices`) — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `sectores` del fixture solo lleva lo que la Carta asocia explícitamente (MIPU → gastronómicos y comercios; edificios → torres y condominios) — no se inventa contenido — elección del usuario — reemplaza a: (nada)
- 2026-10-08 — Las imágenes subidas se reprocesan (sin EXIF/GPS, formato real verificado), se guardan con nombre uuid y las redes solo aceptan https sin credenciales — EXIF/GPS se publicaría al servir `media/` — elección del usuario — reemplaza a: (nada)
- 2026-10-08 — Módulo de imágenes propio en `apps/web` (`imagenes.py`) — el logo necesita conservar el canal alfa — reemplaza a: (nada) — decidida por Claude, revisable

## Plan web-independiente

- 2026-10-17 — El repositorio queda solo con el sitio público; el panel, la API y la app pasan al repositorio detach — pedido del usuario — reemplaza a: 2026-09-28 (un único proyecto Django sitio + panel + API)
- 2026-10-17 — El contenido del sitio se edita desde el admin de Django; no hay panel de contenido — pedido del usuario — reemplaza a: 2026-10-07 (panel de contenido en la ola 2)
- 2026-10-17 — El fixture lleva 9 servicios: los 8 de la Carta más mantenimiento edilicio — decisión del usuario; la Carta no trae más, y los 12 son sectores — reemplaza a: 2026-10-02 y 2026-10-07 (9 servicios por `TipoServicio`; mismo número, ahora como `Servicio`)
- 2026-10-17 — `Servicio` conserva las secciones del diseño aprobado: nombre, slug, resumen, problema, metodos, adicional, faq, sectores, foto, orden, publicado, titulo_seo; reemplaza a `PaginaServicio` y `TipoServicio` — decisión del usuario — reemplaza a: 2026-10-08 (el fixture enlaza `PaginaServicio` al tipo por slug)
- 2026-10-17 — Se quita `apps/accounts`; se usa `django.contrib.auth.User`, y `limites.py`/`red.py` pasan a `config/` con el mismo comportamiento para el login del admin — decisión del usuario — reemplaza a: (nada)
- 2026-10-17 — Los pendientes abiertos que aplican al sitio se re-declaran como `P-web-independiente-<n>`; los del panel y la API quedan en `docs/planes/historico/`, del repo detach — decisión del usuario — reemplaza a: (nada)
- 2026-10-17 — `Configuracion` suma `habilitacion`, `ley` y `director_tecnico`; `empresa.html` los muestra con el mismo texto que antes, `director_tecnico` vacío muestra "Director técnico matriculado"; `_respaldos.html` y `servicio.html` quedan fijos — pedido del usuario — reemplaza a: 2026-10-07 (los datos legales no entran en `Configuracion`) y 2026-10-08 (datos legales y textos fijos se resuelven juntos)
- 2026-10-17 — `/q/<uuid>/` se conserva — es del sitio, no depende de otra app y puede haber QR impresos que apuntan al dominio — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-17 — La vista previa del admin es una URL propia del ModelAdmin (`<pk>/vista-previa/`, en `admin_site.admin_view`), renderiza la plantilla pública aunque el servicio no esté publicado y responde con `X-Robots-Tag: noindex` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-17 — Los ModelAdmin usan `form=` con los formularios de `apps/web/forms.py` (reprocesado de imágenes, `clean_redes`) — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-17 — En DEBUG, `config/urls.py` sirve `MEDIA_URL`; `media/` solo tiene contenido público. El servido en producción queda pendiente — reemplaza a: 2026-10-08 (`media/publico/` aparte de las fotos de visitas) — decidida por Claude, revisable
- 2026-10-17 — Excepción a la tabla de propiedad, solo para el plan `web-independiente`: T1 y T3 escribieron archivos del principal y de "diseño" para retirar apps — decisión del usuario al aprobar el plan — reemplaza a: (nada)
- 2026-10-17 — `docs/decisiones.md` y `docs/bitacora.md` se reescriben; el contenido anterior pasa sin editar a `docs/historico/` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-18 — El primer despliegue del sitio usa una base nueva (`migrate`, `loaddata contenido_inicial`, `createsuperuser`); no se reutiliza ninguna base del proyecto completo — las tablas viejas tienen datos personales de empleados y clientes sin finalidad en este repositorio (auditor-seguridad, T1) — reemplaza a: (nada) — decidida por Claude, revisable
