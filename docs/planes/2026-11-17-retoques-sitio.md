# Plan: retoques-sitio — datos reales, identidad y ajustes visuales del sitio público

<!-- Nivel Completo. Rama plan/retoques-sitio, creada desde main 2643b78.
Veredicto de juez-plan (1.ª pasada): 1 bloqueante y 3 observaciones, todos corregidos: el criterio de T2
que regeneraba los archivos pasó a un test con directorio temporal; el test de whatsapp_href (que ya
funcionaba) pasó a probar el dato real del fixture; la CSP de T7 se compara con los commits de la rama
(`main..HEAD`) y no con `main`. -->

- **slug**: `retoques-sitio`
- **fecha**: 2026-11-17
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): retoques-sitio`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: que el sitio público de producción (`https://www.macontrol.com.ar`) muestre los datos reales de MAControl S.A. (Adjunto A del pedido del 2026-11-17), tenga favicon, imagen para compartir y datos estructurados, y aplique los ajustes visuales aprobados (navegación, móvil, tarjetas, sectores, clientes, portada, pie, WhatsApp flotante).
- **fuera de alcance**:
  - Sección "Nuestros valores", descripción del inicio (`eslogan`) y `titulo_seo` de los servicios: quedan como están.
  - Fotos nuevas, logos de clientes, analítica, formularios.
  - Variable `SITE_URL` de Railway y redirección de `macontrol.com.ar` a `www`: las hace el usuario (pendientes al cierre).
  - Cabecera CSP y demás cabeceras de seguridad: no cambian (`config/settings/**`, `config/csp.py` intactos).
  - URL públicas existentes (`/servicio/<slug>/`, `/q/<uuid>/`) y slugs de servicio.
  - `.claude/hooks/**`.
- **áreas**: web | admin | infraestructura
- **seguridad**: sí — toca datos de la empresa (migración de datos sobre `Configuracion` y `Servicio` en producción), rutas nuevas que sirven archivos desde la raíz (`/favicon.ico`, `/apple-touch-icon.png`, `/site.webmanifest`), un bloque JSON-LD armado con datos de la base, y el `preDeployCommand` de Railway. Corre `auditor-seguridad` en T1, T6 y T8, además de `verificador` y `verificador-b`.

## Contexto mínimo

- **Datos**: `Configuracion` (`apps/web/models.py:47-111`) no tiene CUIT, segundo teléfono ni número internacional. `telefono_href` arma `tel:+54` + dígitos del texto visible, así que "02241 15-546232" daría `tel:+54224115546232` (el pedido exige `+5492241546232`). El fixture (`apps/web/fixtures/contenido_inicial.json`) y producción traen 02241 49 6047, Naveiro 7 / Perón 427, Agroindustria y "más de diez años". Decisión del usuario (2026-11-17): campos nuevos con el número internacional aparte, y migración de datos que actualiza producción.
- **Producción**: el `preDeployCommand` de `railway.json` (array) no se ejecuta (P-puesta-en-produccion-18); sin arreglarlo, la migración de datos no llegaría. CSP en vivo: `default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'`.
- **Plantillas**: `templates/web/base_web.html` (nav, menú móvil `<details>`, pie de 3 columnas), `apps/web/templates/web/paginas/inicio.html` (tarjetas sin icono, sectores en `.grilla-4` de 12 tarjetas, clientes en `.logos-clientes`), `servicio.html:18-20` (`.campo-imagen` sin proporción fija), `_respaldos.html:5` y `servicio.html:55` con "Ministerio de Agroindustria" fijo. `qr.html`, `404.html` y `500.html` no reciben `config`.
- **Vistas**: `_pagina` (`apps/web/views.py:39-56`) arma `config`, `paginas_nav` y `seo` (og:image por defecto = foto del hero). No hay ruta para favicon ni manifiesto. No hay JavaScript en el sitio.
- **Tests que fijan estructura**: `test_paginas.py:24-33` (orden de `id` de sección, 9 enlaces `/servicio/` entre `#servicios` y `#mantenimiento`), `test_diseno.py:21` (sin `<script`), `test_diseno.py:58-59` (logo 206×52).
- **Herramientas**: Pillow 13 del venv abre las woff2 de `static/fonts/` (comprobado); Chrome está instalado en la máquina de desarrollo.
- Modelo: `docs/01-modelo-y-arquitectura.md` § Configuración; diseño: `docs/02-diseno.md` § Componentes.

## Contrato de interfaz entre T5 y T6

Clases CSS que define T5 (en `static/css/web.css`) y usa T6 (en `apps/web/templates/web/paginas/**`):

| Clase | Uso |
|---|---|
| `.tarjeta-servicio` | tarjeta de servicio del inicio (dentro de `.tarjeta-enlace`); altura igual por fila |
| `.tarjeta-icono` | caja de 48×48 con el `<svg>` del servicio |
| `.tarjeta-ver` | indicador "Ver servicio" con flecha (`→`) al pie de la tarjeta |
| `.franja-sectores` | contenedor de la franja de sectores: título a la izquierda, lista a la derecha |
| `.lista-sectores` | `<ul>` de sectores: 3 columnas con filete superior; 2 en ≤ 900 px |
| `.franja-clientes` | `<ul>` de nombres de clientes con salto de línea natural |
| `.cliente-nombre` | `<li>` de cliente: Barlow Condensed 700 en mayúsculas, rombo `--brand` delante (`::before`) |
| `.campo-imagen-portada` | contenedor de la portada de servicio: `aspect-ratio: 16 / 9`, `img` con `object-fit: cover` |

Clases propias de T5 en `base_web.html`: `.nav-actual`, `.nav-desplegable`, `.nav-desplegable-panel`, `.nav-telefono-icono`, `.whatsapp-flotante`, `.pie-marca`.

Propiedades del modelo que define T1 y consumen T5 y T6: `Configuracion.cuit`, `telefono_internacional`, `telefono_2`, `telefono_2_internacional`, `atiende_24_horas`, `telefono_href`, `telefono_2_href`, `whatsapp_href`, `direcciones_con_mapa` (lista de dicts con `localidad`, `direccion`, `provincia`, `mapa_href`).

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (datos), T2 (identidad), T3 (despliegue y Playwright), T4 (integración) | web (solo T1: 0002 esquema y 0003 datos) |
| 2 | T5 (diseño), T6 (páginas, metadatos, JSON-LD), T10 (formulario de Configuración), T7 (integración) | ninguna |
| 3 | T8 (despliegue y comprobación en producción, principal), T9 (cierre, principal) | ninguna |

## Subtareas

### T1 — Cargar los datos reales de la empresa en el modelo, el fixture y producción

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/web/models.py`, `apps/web/admin.py`, `apps/web/migrations/0002_configuracion_datos_empresa.py`, `apps/web/migrations/0003_datos_adjunto_a.py`, `apps/web/fixtures/contenido_inicial.json`, `apps/web/tests/test_modelos.py`, `apps/web/tests/test_fixture.py`, `apps/web/tests/test_migraciones.py` (nuevo), y solo las aserciones de datos (teléfono, WhatsApp, habilitación) de `apps/web/tests/test_paginas.py`, `apps/web/tests/test_publicas.py` y `apps/web/tests/test_recorrido.py`; `docs/00-contenido-fuente.md`, `docs/01-modelo-y-arquitectura.md`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/web/views.py`, `apps/web/templates/`, `railway.json`, `requirements*.txt`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models y § Migrations; `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones (migraciones a mano solo `RunPython` justificado)
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  - Migración 0002 (generada con `makemigrations`, solo agrega): en `Configuracion`, `cuit` (CharField 13, blank), `telefono_internacional` y `telefono_2_internacional` (CharField 16, blank, `RegexValidator(r"^\+549\d{10}$")`), `telefono_2` (CharField 40, blank), `atiende_24_horas` (BooleanField, default False). Admin: los campos nuevos en el `ModelAdmin` de `Configuracion` (con `fields`/`fieldsets` explícitos, sin `__all__`). `help_text` de `direcciones`: `{"localidad", "direccion", "provincia"}`.
  - Propiedades: `telefono_href` = `tel:` + `telefono_internacional` si está, si no la lógica actual; `telefono_2_href` igual con `telefono_2_internacional` (vacío si no hay); `whatsapp_href` no cambia (con `+5492241546232` ya devuelve `https://wa.me/5492241546232`); `direcciones_con_mapa` agrega a cada dirección `mapa_href = "https://www.google.com/maps/search/?api=1&query=" + quote_plus("<direccion>, <localidad>, <provincia>, Argentina")` (omitiendo partes vacías).
  - Migración 0003 (`RunPython`, docstring con la justificación: lleva a producción los datos del Adjunto A, reverso `noop`): si existe `Configuracion` pk=1, fija razón social "MAControl S.A.", `cuit` "30-71834106-6", `director_tecnico` "Miguel Canale", `direcciones` `[{"localidad": "Castelli", "direccion": "Saavedra 555", "provincia": "Buenos Aires"}]`, `telefono` "02241 15-546232", `telefono_internacional` "+5492241546232", `telefono_2` "02241 15-496047", `telefono_2_internacional` "+5492241496047", `whatsapp` "+5492241546232", `correo` "administracion@macontrol.com.ar", `horario` "Atención las 24 horas, todos los días", `atiende_24_horas` True, `habilitacion` "Empresa inscripta y habilitada — Ministerio de Desarrollo Agrario", `redes` Instagram y Facebook (URL del Adjunto A), y en `presentacion` reemplaza "más de diez años" por "15 años". En `Servicio`, por slug: `mosquitos-vectores` → "Control de mosquitos vectores"; `manejo-plagas-edificios` → "Manejo integral de plagas en edificios y departamentos"; `servicio-mipu` → "Servicio MIPU", con el `resumen` empezando por "Manejo Integral de Plagas Urbanas (MIPU): " si no empieza ya así. No toca `titulo_seo` ni `eslogan`.
  - `Sector.TRANSPORTE` pasa a la etiqueta "Vehículos de transporte" (valor sin cambios). Fixture con los mismos valores que la 0003. `docs/00-contenido-fuente.md`: sección "Adjunto A — datos entregados el 2026-11-17" con lo que reemplaza; `docs/01`: campos nuevos de `Configuracion`.
  - Actualizar las aserciones de datos viejos (Naveiro/Perón, `whatsapp == ""`, `tel:+542241496047`, "no hay wa.me", Agroindustria) en los archivos de test listados.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionTelefonosTests.test_telefono_href_usa_numero_internacional --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionTelefonosTests.test_telefono_2_href --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionTelefonosTests.test_whatsapp_del_fixture_es_el_real --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionTelefonosTests.test_internacional_rechaza_formato_invalido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionMapaTests.test_direccion_enlaza_a_google_maps --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_migraciones.MigracionDatosTests.test_0003_carga_adjunto_a --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_migraciones.MigracionDatosTests.test_0003_sin_configuracion_no_crea_fila --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_fixture.FixtureTests.test_fixture_trae_adjunto_a --keepdb`
  - `[existe]` `apps/web/migrations/0002_configuracion_datos_empresa.py`
  - `[existe]` `apps/web/migrations/0003_datos_adjunto_a.py`
  - `[grep-1]` `grep -n "RunPython" apps/web/migrations/0003_datos_adjunto_a.py`
  - `[grep-0]` `grep -nE "Naveiro|Presidente Perón|Agroindustria|más de diez años|49 6047" apps/web/fixtures/contenido_inicial.json`
  - `[grep-1]` `grep -n '"Vehículos de transporte"' apps/web/models.py`
  - `[grep-1]` `grep -n "30-71834106-6" docs/00-contenido-fuente.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T1`

### T2 — Generar el favicon, los iconos de la aplicación y la imagen para compartir

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `herramientas/generar_identidad.py` (nuevo), `static/img/favicon.svg`, `static/favicon.ico`, `static/img/apple-touch-icon.png`, `static/img/icono-192.png`, `static/img/icono-512.png`, `static/img/og-macontrol.png`, `apps/web/templates/web/_iconos.html` (nuevo), `apps/web/tests/test_identidad.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/`, `templates/web/base_web.html`, `static/css/`, `static/img/logo.png`, `static/img/logo-nav.png`, `apps/web/models.py`, `apps/web/views.py`, `apps/web/templates/web/paginas/`, `requirements*.txt`
- **Skill a leer antes**: `.agents/skills/python-best-practices/SKILL.md` (la sección de scripts); `docs/02-diseno.md` § Tokens
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - `static/img/favicon.svg`: `viewBox="0 0 64 64"`, rectángulo `#ffc600` de 64×64 con `rx`/`ry` de 12,8 (20 %), y dos `<path>` del Adjunto B (M y C) con `fill="none"`, `stroke="#0f1417"`, `stroke-width="6"`, copiados literal.
  - `herramientas/generar_identidad.py` (solo Pillow, sin dependencias nuevas): dibuja el mismo favicon a 8× (rectángulo redondeado y trazos con arcos de radio 4 aproximados) y lo reduce con LANCZOS a 180 (`apple-touch-icon.png`), 192 y 512 (`icono-192.png`, `icono-512.png`) y a `static/favicon.ico` con tamaños 16 y 32. `og-macontrol.png` de 1200×630: fondo `#0f1417`, `static/img/logo.png` centrado y el eslogan "Manejo integral de plagas" en Barlow Condensed 700 (`static/fonts/barlow-condensed-latin-700-normal.woff2`) en `#e8e6df`. Docstring con el uso; el script es idempotente y acepta un directorio de salida (`--salida <dir>`, por defecto `static/`), para que el test lo corra en un directorio temporal y compare con los archivos commiteados sin escribir en el árbol.
  - `apps/web/templates/web/_iconos.html`: `<link rel="icon" href="/favicon.ico" sizes="32x32">`, `<link rel="icon" href="{% static 'img/favicon.svg' %}" type="image/svg+xml">`, `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`, `<link rel="manifest" href="/site.webmanifest">`, `<meta name="theme-color" content="#0f1417">`. Sin `style=` ni `<script`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_tamanos_de_los_png --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_ico_trae_16_y_32 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_og_es_1200x630 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_svg_trae_los_trazos_del_adjunto_b --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_parcial_enlaza_iconos --keepdb`
  - `[existe]` `static/favicon.ico`
  - `[existe]` `static/img/og-macontrol.png`
  - `[grep-1]` `grep -n 'M57.5 21 H43 a4 4 0 0 0 -4 4 V40 a4 4 0 0 0 4 4 H57.5' static/img/favicon.svg`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_identidad.IdentidadTests.test_generador_reproduce_los_archivos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T2`

### T3 — Pasar el `preDeployCommand` a un solo comando y agregar Playwright de desarrollo

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `railway.json`, `requirements-dev.txt`, `config/tests/test_despliegue.py` (nuevo), `docs/despliegue.md`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `config/*.py`, `requirements.txt`, `apps/`, `templates/`, `static/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos; `docs/despliegue.md`
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**:
  - `railway.json`: `"preDeployCommand": "python manage.py migrate --noinput && python manage.py createcachetable"` (una cadena; el resto igual).
  - `requirements-dev.txt`: `playwright==<versión exacta>` (la última estable publicada en PyPI hace al menos dos semanas). Se instala en el venv con `./venv/Scripts/python.exe -m pip install -r requirements-dev.txt`; el navegador es el Chrome del sistema (`channel="chrome"`), sin `playwright install`.
  - `config/tests/test_despliegue.py`: lee `railway.json` y comprueba que `preDeployCommand` es una cadena que corre `migrate --noinput` y `createcachetable`.
  - `docs/despliegue.md`: quitar el aviso de que el `preDeployCommand` no corre (líneas 57 y 76, que citan P-9), explicar el formato nuevo y que se comprueba en el próximo despliegue (T8).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue.RailwayTests.test_predeploy_es_un_solo_comando --keepdb`
  - `[grep-1]` `grep -n '"preDeployCommand": "python manage.py migrate --noinput && python manage.py createcachetable"' railway.json`
  - `[grep-1]` `grep -nE '^playwright==[0-9]+\.[0-9]+\.[0-9]+$' requirements-dev.txt`
  - `[cmd]` `./venv/Scripts/python.exe -c "import playwright.sync_api"`
  - `[grep-0]` `grep -n "P-puesta-en-produccion-9" docs/despliegue.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T3`

### T4 — Integración de la ola 1 (principal)

- **Ola**: 1 (después de verificar T1, T2 y T3)
- **Depende de**: T1, T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/retoques-sitio` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh retoques-sitio T<n> plan/retoques-sitio <ruta>...` para T1, T2 y T3.
  3. `makemigrations --check --dry-run` y `test --keepdb`.
  4. `bash .claude/hooks/worktree-crear.sh retoques-sitio T5 plan/retoques-sitio` y lo mismo para T6.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T4:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T4`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T1: integra retoques-sitio-T1"`
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T2: integra retoques-sitio-T2"`
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T3: integra retoques-sitio-T3"`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`

### T5 — Rediseñar la barra, el menú móvil, el pie y los estilos de componentes

- **Ola**: 2
- **Depende de**: T4
- **Puede tocar**: `templates/web/base_web.html`, `static/css/web.css`, `docs/02-diseno.md`, `herramientas/medir_movil.py` (nuevo), `apps/web/tests/test_base_web.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/web/models.py`, `apps/web/views.py`, `apps/web/urls.py`, `apps/web/templates/`, `apps/web/tests/test_paginas.py`, `apps/web/tests/test_diseno.py`, `static/img/`, `requirements*.txt`
- **Skill a leer antes**: `.agents/skills/web-design-guidelines/SKILL.md` (accesibilidad y navegación); `.agents/skills/frontend-design/SKILL.md` § CSS; `docs/02-diseno.md` completo
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 550 líneas agregadas
- **Qué hacer**:
  - Cabecera: `{% include "web/_iconos.html" %}`. Navegación: el enlace de la página actual lleva `aria-current="page"` y `.nav-actual` (texto y subrayado `--brand`), comparando `request.path` con `url_empresa`/`url_contacto`; en `/servicio/…` se marca "Servicios". "Servicios" pasa a `.nav-desplegable` con un `.nav-desplegable-panel` que lista `paginas_nav`, abierto con `:hover` y `:focus-within`, solo HTML y CSS. `section[id] { scroll-margin-top: 100px; }`.
  - ≤ 900 px: logo con `height: 40px; width: auto; flex-shrink: 0` (proporción 3,96:1); teléfono como `.nav-telefono-icono` de 44×44 con un `<svg>` y `aria-label="Llamar al {{ config.telefono }}"`; panel del menú móvil a todo el ancho del viewport.
  - Botón flotante: `{% if config.whatsapp_href %}<a class="whatsapp-flotante" href="{{ config.whatsapp_href }}" aria-label="Escribir por WhatsApp">…svg…</a>{% endif %}`, fijo abajo a la derecha, sin tapar el pie en móvil.
  - Pie: `.pie-marca` con el logo y las redes (`config.redes`); direcciones de `config.direcciones_con_mapa` como enlace (`mapa_href`, `rel="noopener"`); teléfono, segundo teléfono (`telefono_2_href`), WhatsApp, correo y horario; línea legal con CUIT, habilitación, director técnico y `© {% now "Y" %} MAControl S.A.`.
  - CSS del contrato de interfaz (tabla de arriba), con tokens de `docs/02-diseno.md`; `docs/02-diseno.md` documenta los componentes nuevos. `base_web.html` sigue renderizando sin contexto (test existente).
  - `herramientas/medir_movil.py`: base temporal + fixture + runserver como `herramientas/humo_web.py` (reusa su forma), Playwright con `channel="chrome"` en 375×812; recorre `/`, `/empresa/`, `/contacto/` y `/servicio/control-murcielagos/`; sale con 1 e informa si `document.documentElement.scrollWidth > 375`, si el `img` de `.nav-logo` tiene `ancho/alto` fuera de 3,96 ± 2 %, si `.campo-imagen-portada` mide más de 220 px de alto en la página de servicio, o si `/empresa/` no tiene `[aria-current="page"]`. Con 0 imprime las medidas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_marca_pagina_actual --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_whatsapp_flotante_solo_con_numero --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_pie_trae_cuit_segundo_telefono_y_copyright --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_telefono_movil_con_aria_label --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_direccion_enlaza_a_maps --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_desplegable_lista_los_servicios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base_web.BaseWebTests.test_incluye_iconos --keepdb`
  - `[grep-1]` `grep -n "scroll-margin-top: 100px" static/css/web.css`
  - `[grep-1]` `grep -nE "aspect-ratio: ?16 ?/ ?9" static/css/web.css`
  - `[grep-1]` `grep -n "\.whatsapp-flotante" static/css/web.css`
  - `[grep-0]` `grep -nE "<script|style=" templates/web/base_web.html`
  - `[grep-1]` `grep -n "whatsapp-flotante" docs/02-diseno.md`
  - `[existe]` `herramientas/medir_movil.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 550 --subtarea T5`

### T6 — Actualizar las páginas, los metadatos, el JSON-LD y las rutas de iconos

- **Ola**: 2
- **Depende de**: T4
- **Puede tocar**: `apps/web/views.py`, `apps/web/urls.py`, `apps/web/seo.py` (nuevo), `apps/web/iconos.py` (nuevo), `apps/web/templates/web/paginas/**`, `apps/web/templates/web/site.webmanifest` (nuevo), `apps/web/templates/404.html`, `apps/web/templates/500.html`, `apps/web/tests/test_paginas.py`, `apps/web/tests/test_diseno.py`, `apps/web/tests/test_publicas.py`, `apps/web/tests/test_recorrido.py`, `apps/web/tests/test_seo.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/`, `templates/web/base_web.html`, `static/`, `apps/web/models.py`, `apps/web/migrations/`, `apps/web/fixtures/`, `apps/web/templates/web/_iconos.html`, `requirements*.txt`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Views y § Templates; `.agents/skills/django-security/SKILL.md` § servir archivos y escape
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**:
  - Rutas (en `apps/web/urls.py`, sin tocar las existentes): `/favicon.ico` y `/apple-touch-icon.png` → una vista `require_safe` que sirve `static/favicon.ico` y `static/img/apple-touch-icon.png` (nombres fijos en un dict, nada tomado de la URL) con `django.contrib.staticfiles.finders.find` + `FileResponse`, `Content-Type` correcto, `X-Content-Type-Options: nosniff` y `Cache-Control: public, max-age=86400`. `/site.webmanifest` → plantilla `web/site.webmanifest` (nombre, `short_name` "MAControl", `start_url` "/", `display` "standalone", `theme_color` y `background_color` `#0f1417`, iconos 192 y 512 con `{% static %}`), `application/manifest+json`.
  - Metadatos (`publica.html` y `_pagina`): `og:image` por defecto `img/og-macontrol.png` con `og:image:width` 1200 y `og:image:height` 630 (las páginas con foto propia mantienen su imagen y su tamaño), `og:locale` `es_AR`, `og:site_name` (razón social), `twitter:card` `summary_large_image`. `qr.html`, `404.html` y `500.html` incluyen `web/_iconos.html`.
  - `apps/web/seo.py`: `datos_estructurados(config)` arma un dict `LocalBusiness` (`name`, `url` = `SITE_URL`, `logo`, `image`, `telephone` = `telefono_internacional`, segundo teléfono en `contactPoint`, `email`, `address` `PostalAddress` con `streetAddress`/`addressLocality`/`addressRegion`/`addressCountry` "AR", `openingHoursSpecification` 24/7 solo si `atiende_24_horas`, `sameAs` desde `redes`, `taxID` = `cuit`), y `json_ld(datos)` lo serializa con `json.dumps` escapando `<`, `>` y `&` (como `django.utils.html.json_script`) y lo marca seguro. Solo el inicio emite `<script type="application/ld+json">`.
  - `apps/web/iconos.py`: `ICONO_POR_SLUG` con las 9 rutas del Adjunto C y `ICONO_GENERICO` (decidido por Claude), `icono_de(slug)`; la vista `inicio` pasa a cada servicio su `d`. Inicio: tarjetas `.tarjeta-servicio` con `.tarjeta-icono` (`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">`) y `.tarjeta-ver` "Ver servicio →", un solo enlace por tarjeta; `#sectores` como `.franja-sectores` con `.lista-sectores`; `#clientes` como `.franja-clientes` con `.cliente-nombre`; "espacios y sectores"; bloque de contacto con un único título "Contacto directo" (sin "Hablemos" ni "Hablemos por teléfono" en `inicio.html` ni `_contacto.html`), y el segundo teléfono en `_contacto.html`. `servicio.html`: portada dentro de `.campo-imagen-portada`. `_respaldos.html` y `servicio.html`: la habilitación sale de `config.habilitacion`. Direcciones de `_contacto.html` con `direcciones_con_mapa`.
  - Tests: los listados abajo, más la actualización de las aserciones de estructura que cambian (sectores, clientes, "Hablemos", `<script` admitido solo como `application/ld+json` en `test_diseno`).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.RaizTests.test_favicon_ico_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.RaizTests.test_apple_touch_icon_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.RaizTests.test_manifiesto_200_y_json --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.MetadatosTests.test_og_imagen_1200x630_y_locale --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.MetadatosTests.test_paginas_de_error_y_qr_enlazan_iconos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.JsonLdTests.test_inicio_trae_local_business_valido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.JsonLdTests.test_json_ld_escapa_cierre_de_script --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.IconosTests.test_icono_por_slug_y_respaldo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.TextosTests.test_ninguna_pagina_publica_trae_textos_viejos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.TextosTests.test_inicio_trae_telefono_y_whatsapp_reales --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seo.TextosTests.test_segundo_telefono_en_contacto --keepdb`
  - `[grep-0]` `grep -rnE "Agroindustria|Hablemos|espacios/sectores" apps/web/templates`
  - `[grep-0]` `grep -rn "style=" apps/web/templates/web/paginas`
  - `[grep-1]` `grep -n "campo-imagen-portada" apps/web/templates/web/paginas/servicio.html`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T6`

### T10 — Permitir guardar desde el admin la Configuración con los datos nuevos

<!-- Agregada por contrato modificado (2026-11-17, decisión del usuario): T1 mostró que `ConfiguracionForm`
exige exactamente `localidad` y `direccion` en cada dirección, así que con `provincia` el admin no guarda. -->

- **Ola**: 2
- **Depende de**: T4
- **Puede tocar**: `apps/web/forms.py`, `apps/web/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/web/models.py`, `apps/web/admin.py`, `apps/web/migrations/`, `apps/web/views.py`, `apps/web/templates/`, los demás tests
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Forms; `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - `ListaDeObjetosField` acepta claves opcionales (`opcionales=(...)`): cada elemento tiene todas las `claves` obligatorias, puede tener las opcionales y nada más; las presentes no pueden estar vacías. `direcciones` usa `claves=("localidad", "direccion")` y `opcionales=("provincia",)`.
  - `ConfiguracionForm.Meta.fields` suma `cuit`, `telefono_internacional`, `telefono_2`, `telefono_2_internacional` y `atiende_24_horas`.
  - Tests en `AdminConfiguracionTests`: guardar por POST la Configuración del Adjunto A (con `provincia` y los dos números internacionales) da 302 y queda guardada; una dirección con una clave desconocida se rechaza; un número internacional mal formado se rechaza.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_guarda_configuracion_del_adjunto_a --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_direccion_con_clave_desconocida_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_telefono_internacional_invalido_se_rechaza --keepdb`
  - `[grep-1]` `grep -n '"telefono_2_internacional"' apps/web/forms.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T10`

### T7 — Integración de la ola 2 (principal)

- **Ola**: 2 (después de verificar T5, T6 y T10)
- **Depende de**: T5, T6, T10
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/retoques-sitio` de T5 y T6, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh retoques-sitio T5 plan/retoques-sitio <ruta>...` y lo mismo para T6.
  3. `test --keepdb`, `herramientas/humo_web.py` y `herramientas/medir_movil.py`; mirar el sitio en 375 px y en escritorio.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T7:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T7`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T5: integra retoques-sitio-T5"`
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T6: integra retoques-sitio-T6"`
  - `[cmd]` `git log --oneline plan/retoques-sitio | grep -q "T10: integra retoques-sitio-T10"`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/medir_movil.py`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/humo_web.py`
  - `[cmd]` `test -z "$(git log --oneline main..HEAD -- config/settings config/csp.py)"`
  - `[grep-0]` `grep -rnE "Agroindustria|Ricardo Naveiro|Presidente Perón 427|más de diez años" apps/web/templates templates apps/web/fixtures`

### T8 — Desplegar y comprobar en producción (principal)

- **Ola**: 3
- **Depende de**: T7 y la verificación `TODO` en PASA
- **Pasos**:
  1. El usuario decide el merge de `plan/retoques-sitio` en `main` y autoriza el push a `origin` (nunca a `detach`); Railway despliega desde `main`.
  2. Comprobar en los registros del despliegue que corrió el `preDeployCommand` (migraciones 0002 y 0003 aplicadas). Si no corrió, parar y consultar al usuario antes de usar `railway ssh`.
  3. Correr los criterios contra `https://www.macontrol.com.ar`.
- **Presupuesto**: no aplica (sin commits de código)
- **Criterios**:
  - `[cmd]` `curl -fsS -o /dev/null https://www.macontrol.com.ar/favicon.ico`
  - `[cmd]` `curl -fsS -o /dev/null https://www.macontrol.com.ar/apple-touch-icon.png`
  - `[cmd]` `curl -fsS -o /dev/null https://www.macontrol.com.ar/site.webmanifest`
  - `[cmd]` `curl -fsS https://www.macontrol.com.ar/ | grep -q 'tel:+5492241546232'`
  - `[cmd]` `curl -fsS https://www.macontrol.com.ar/ | grep -q 'https://wa.me/5492241546232'`
  - `[cmd]` `curl -fsS https://www.macontrol.com.ar/ | grep -q 'application/ld+json'`
  - `[cmd]` `h=$(curl -fsS https://www.macontrol.com.ar/) && ! grep -qE "Agroindustria|Ricardo Naveiro|Presidente Perón 427|más de diez años" <<<"$h"`
  - `[cmd]` `curl -fsSI https://www.macontrol.com.ar/ | tr -d '\r' | grep -qx "content-security-policy: default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"`

### T9 — Cierre (principal)

- **Ola**: 3
- **Depende de**: T8
- **Pasos**: bitácora (entrada y "Estado actual"), decisiones del plan copiadas a `docs/decisiones.md`, `### Cierra` y pendientes nuevos (`SITE_URL`, redirección `macontrol.com.ar` → `www`, HSTS); commits `T9:` en `plan/retoques-sitio` y merge en `main` con autorización del usuario.
- **Presupuesto**: 120 líneas agregadas
- **Criterios**:
  - `[grep-1]` `grep -n "2026-11-17" docs/decisiones.md`
  - `[grep-1]` `grep -n "retoques-sitio" docs/bitacora.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T9`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-11-17-retoques-sitio.md retoques-sitio`

## Registro de verificación

commit_base: d3390df

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | pendiente |
| T6 | pendiente |
| T7 | pendiente |
| T8 | pendiente |
| T9 | pendiente |
| T10 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-11-17 | T1 | 85a6ec0 | 17/17 PASA (verificador y verificador-b); veredicto formal FALLA solo por contrato modificado (T10, aprobado por el usuario) | auditor-seguridad: sin bloqueantes ni importantes; 1 menor y 4 observaciones → pendientes |
| 2026-11-17 | T2 | 170c146 | PASA 10/10 (verificador y verificador-b) | favicon y OG revisados a ojo por el principal |
| 2026-11-17 | T3 | 70e75e1 | PASA 6/6 (verificador y verificador-b) | el principal corrigió playwright a 1.64.1 (regla de dos semanas) y commiteó T3 |
| 2026-11-17 | T4 | dffa6e6 | criterios corridos por el principal: 3 integraciones y makemigrations --check en verde | worktree-integrar: 158 tests OK |
| | T5 | | | |
| | T6 | | | |
| | T10 | | | |
| | T7 | | | |
| | TODO | | | |
| | T8 | | | |

### Decisiones del plan

- T1 — la 0003 sin fila de Configuracion — crear / no crear — no crea fila — producción ya la tiene y crearla inventaría datos — autónoma — cambiar la migración — decidida por Claude, revisable
- T1 — lógica de los href de teléfono — duplicada / helper común `_href_telefono` — helper común — misma regla para los dos números — autónoma — inlinear — decidida por Claude, revisable
- T1 — claves de `direcciones_con_mapa` — solo las presentes / siempre `localidad`, `direccion`, `provincia` y `mapa_href` — siempre todas — el contrato T5/T6 las espera — autónoma — filtrar — decidida por Claude, revisable

- T6 — icono de respaldo para servicios sin icono asignado — círculo con marca / escudo / sin icono — dibujo propio simple (círculo con marca de verificación) en `ICONO_GENERICO` — el Adjunto C no trae uno y el pedido exige respaldo — autónoma — cambiar la constante — decidida por Claude, revisable
- T3 — cómo medir el viewport de 375 px — Playwright con el Chrome del sistema / Selenium / solo criterios de CSS — Playwright (solo `requirements-dev.txt`, `channel="chrome"`) — los criterios de 375 px y de la portada son de layout y solo un navegador los decide; licencia Apache 2.0, sin costo, no llega a producción — autónoma — quitar la línea y el script — decidida por Claude, revisable
- T6 — servir `/favicon.ico` y `/apple-touch-icon.png` — vista propia / `WHITENOISE_ROOT` en settings — vista propia con nombres fijos — no toca `config/settings` (CSP y settings sin cambios) y es testeable con el cliente de Django — autónoma — volver a quitar las dos rutas — decidida por Claude, revisable
- T1 — provincia de la dirección para Maps y JSON-LD — clave `provincia` en `direcciones` / texto fijo en el código — clave `provincia` en el JSON — el dato es de la empresa, no del código — autónoma — quitar la clave — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-retoques-sitio-1 [menor] La 0003 antepone "Manejo Integral de Plagas Urbanas (MIPU): " al resumen de MIPU de producción, que empieza con mayúscula ("Programa de monitoreo…"); el fixture dice "programa". Bajar la inicial en la migración y ajustar `test_migraciones.py:69-72` (auditor-seguridad T1).
- P-retoques-sitio-2 [observación] `validar_internacional` (`apps/web/models.py:50`) usa `$`, que acepta un salto de línea final; el admin lo recorta (`strip=True`). Endurecer con `\Z` (auditor-seguridad T1).
- P-retoques-sitio-3 [observación] Si `presentacion` de producción fue editada, el reemplazo de "más de diez años" de la 0003 no aplica y no avisa. Comprobar tras el despliegue: `python manage.py shell -c "from apps.web.models import Configuracion as C; p=C.objects.get(pk=1).presentacion; print('15 años' in p, 'diez años' in p)"` → `True False` (auditor-seguridad T1).
- P-retoques-sitio-4 [observación] La 0003 pisa sin condiciones 15 campos de Configuracion y su reverso es noop: respaldar antes del despliegue con `python manage.py dumpdata web.configuracion web.servicio --indent 2` en producción (auditor-seguridad T1).
- P-retoques-sitio-5 [observación] `docs/00-contenido-fuente.md:87-88` y `docs/01-modelo-y-arquitectura.md:93-95` siguen listando como pendientes datos que el Adjunto A ya resolvió (Instagram, segundo teléfono, WhatsApp, horario, director técnico) (auditor-seguridad T1).

### Decisiones

- 2026-11-17 — Los datos de la empresa del Adjunto A (CUIT 30-71834106-6, director técnico Miguel Canale, dirección única Saavedra 555 de Castelli, teléfonos 02241 15-546232 —principal y WhatsApp— y 02241 15-496047, atención 24 horas, habilitación del Ministerio de Desarrollo Agrario, 15 años de trayectoria, Instagram y Facebook) reemplazan a los publicados — entregados por el usuario — reemplaza a: 2026-10-18 (los datos de la empresa los entrega el cliente más adelante)
- 2026-11-17 — `Configuracion` guarda el número internacional de cada teléfono en un campo aparte (`telefono_internacional`, `telefono_2_internacional`), sin deducirlo del texto visible — decisión del usuario — reemplaza a: (nada)
- 2026-11-17 — Los datos nuevos llegan a producción con una migración de datos (0003), y el `preDeployCommand` pasa a un solo comando para que `migrate` corra en cada despliegue — decisión del usuario — reemplaza a: 2026-10-18 (migraciones del primer despliegue por `railway ssh`)
- 2026-11-17 — El dominio `www.macontrol.com.ar` ya está conectado (hecho a mano, fuera de un plan) — informado por el usuario — reemplaza a: 2026-10-18 (el sitio sale primero con `*.up.railway.app`)

### Cierra

- cierra: P-puesta-en-produccion-20 — el usuario conectó `www.macontrol.com.ar` a mano (informado el 2026-11-17); T8 comprueba el sitio en ese dominio
