# Plan: web-independiente — el repositorio queda solo con el sitio público

<!-- Nivel Completo, pedido por el usuario. Flujo: juez-plan → aprobación del usuario → commit
`docs(plan): web-independiente` → commit_base en el Registro; congelado arriba del corte.
Destino en el repo: docs/planes/2026-10-17-web-independiente.md. Rama plan/web-independiente,
creada desde 1e049a3 (plan/demo-portatil). -->

<!-- Veredicto de juez-plan (1.ª pasada): 8 bloqueantes, 7 observaciones. Corregidos en este texto:
 - grep con backticks de T4 → "^### Servicio";
 - grep-0 de T1 que chocaban con sus propios tests → acotados con --exclude-dir=tests;
 - T1 sin test_paginas.py → agregado a Puede tocar;
 - presupuesto de T7 que no cubría el git mv → 1300 con el motivo;
 - tests "nuevos" que ya existían → renombrados con alcance propio (y el de CSP quitado: lo cubren test_csp/test_cabeceras);
 - git log --grep con $ → toma el primer docs(plan);
 - pendientes.py → grep anclado al id;
 - Plan activo → títulos nuevos de bitácora/decisiones;
 - grep de agentes que ya pasaba → términos del dominio;
 - ls | wc -l → no-existe + recuento de historico/.
 Abiertos para el usuario: los 3 bloqueantes de propiedad (c), cubiertos por la decisión "Excepción a la tabla de propiedad", que se aprueba con el plan. -->

- **slug**: `web-independiente`
- **fecha**: 2026-10-17
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): web-independiente`. El hash se anota en `## Registro de verificación`.
- **objetivo**: que este repositorio sea solo el sitio público de MAControl S.A., con su propio modelo de contenido (Servicio, ClienteDestacado, Configuracion) editado desde el admin de Django; el panel, la API y la app viven en el repositorio detach.
- **fuera de alcance**:
  - El diseño aprobado: `static/css/web.css`, `static/img/**`, `static/fonts/**` no cambian; `templates/web/base_web.html` y las plantillas de `apps/web/templates/web/paginas/` cambian solo lo necesario para leer el modelo nuevo (`pagina.tipo.nombre` → `servicio.nombre`, y los datos legales de `empresa.html`).
  - La política CSP (`CONTENT_SECURITY_POLICY`) y `SECURE_REFERRER_POLICY` mantienen su valor. Solo cambian los comentarios que hablan del panel.
  - El servido de `media/` en producción: queda como pendiente re-declarado.
  - `.claude/hooks/**`: no se tocan. `pendientes.py` sigue leyendo solo `docs/planes/*.md`.
  - `railway.json`.
  - Formularios públicos: el contacto sigue siendo teléfono y WhatsApp (decisión 2026-09-29).
- **áreas**: web | infraestructura
- **seguridad**: sí — toca la autenticación: se quita `accounts.User`, el login del admin conserva el límite de intentos y la base pasa a `auth.User`. También toca la subida de imágenes desde el admin (EXIF, tipos) y los settings de producción (INSTALLED_APPS, MIDDLEWARE, requirements). Por eso corre también `auditor-seguridad`, además de `verificador` y `verificador-b`.

## Contexto mínimo

Inventario de solo lectura de lo que usa `apps/web` hoy (1e049a3):
- **Modelos**:
  - `Configuracion`: una sola fila (pk=1). Campos: razón social, eslogan, presentación, teléfono, WhatsApp, correo, horario, `direcciones` JSON y `redes` JSON.
  - `PaginaServicio`: `tipo = OneToOneField("servicios.TipoServicio", PROTECT)`. Campos: titulo_seo, resumen, problema, adicional, `metodos`/`faq`/`sectores` JSON, imagen_portada y publicado. Es la única dependencia ajena (`apps/web/models.py:120-125`), y `0001_initial` depende de `servicios.0003`.
  - `ClienteDestacado`: nombre, logo, orden y activo.
  - `Sector`: TextChoices con 12 valores.
- **Vistas** (`apps/web/urls.py`): `/`, `/servicio/<slug>/` (en singular), `/empresa/`, `/contacto/`, `/q/<uuid>/`, `/sitemap.xml` y `/robots.txt`. Un servicio no publicado o con el tipo inactivo da 404 por `PaginaServicio.objects.publicadas()`. No hay context processors propios.
- **Imágenes y formularios**:
  - `apps/web/imagenes.py` (`reprocesar_imagen`, Pillow, quita EXIF) y `validators.py`.
  - `forms.py` (`ReprocesaImagenesMixin`, `ConfiguracionForm.clean_redes`): hoy los usa solo el panel. `admin.py` usa los ModelForm por defecto (P-sitio-publico-12, P-robustez-panel-5).
  - `panel_views.py`, `panel_urls.py`, `api_urls.py` y `templates/web/panel/` cuelgan del panel y de la API.
- **Plantillas**:
  - `templates/web/base_web.html`, `apps/web/templates/web/paginas/*` y `404.html`/`500.html` (404 enlaza a `/panel/`). `robots.txt` bloquea `/panel/` y `/api/`.
  - Los datos legales están fijos en `empresa.html:41-47`, `_respaldos.html` y `servicio.html:55`.
  - Ninguna plantilla pública tiene `<form` ni "presupuesto".
  - `templates/base.html` y `templates/panel/**` son del panel.
- **Estáticos del sitio**: `static/css/web.css`, `static/fonts/*`, `static/img/logo.png` y 5 `.webp`. Del panel: `static/css/panel.css`, `static/vendor/{htmx,leaflet}`, y los estáticos de `apps/panel` y `apps/sitios`. Leaflet no está en `requirements.txt`: está copiado en `static/vendor/`.
- **Fixture**: `apps/web/fixtures/contenido_inicial.json` tiene 9 `servicios.tiposervicio`, 1 configuración, 9 páginas publicadas y 13 clientes.
- **Tests de web**:
  - `test_paginas.py:179` `PlantillasTests.test_ninguna_plantilla_publica_tiene_form_ni_presupuesto` es el que hay que migrar.
  - `test_csp.py` y `test_base.py` usan `templates/base.html`.
  - `test_panel.py`, `test_seguridad_contenido.py` y `test_rutas.py` usan `panel:*` y `api:*`.
- **Settings y config**:
  - `config/settings/base.py` tiene DRF, SimpleJWT, spectacular, `simple_history` (app y middleware) y ajustes de dominio (`ATRASO_*`, `DISTANCIA_*`, `PRECISION_*`, `VISITA_*`). Además `AUTH_USER_MODEL = "accounts.User"` y `LOGIN_URL = "/panel/ingresar/"`.
  - CSP la pone django-csp 4 y Referrer-Policy la pone `SecurityMiddleware`.
  - `config/admin.py` importa `apps.accounts.limites.LimiteIngresoMixin`, que usa `apps/accounts/red.py`.
  - En `config/tests/` hay partes de DRF y de dominio (`test_settings.py:38-51,205-233`, `test_ajustes_ingreso.py:27-38`, `test_registro.py`, `test_admin_site.py`).
- **Requirements que dejan de usarse**: djangorestframework, simplejwt, drf-spectacular(+sidecar), django-simple-history, WeasyPrint, segno, pypdfium2, django-storages y jsonschema (los dos últimos ya no tenían imports). Quedan Django, django-environ, django-csp, Pillow, psycopg, whitenoise, gunicorn y ruff.
- **Otros archivos que cuelgan del panel**: `demo.bat`, `herramientas/empaquetar_demo.py`, `herramientas/humo_demo.py`, `docs/demo-cliente.md`, `docs/api/`, `apps/panel/management/commands/cargar_demo.py`. `.env.example` tiene variables de dominio y `STORAGE_BACKEND`/`AWS_*`, que ningún setting lee.
- **Hooks**: `pendientes.py`, `contexto.sh` y `verificar_plan.py` leen solo `docs/planes/*.md`, sin recursión. Al mover los planes a `historico/`, sus pendientes y sus `cierra:` dejan de verse. Por eso los del sitio se re-declaran en este plan y no se usa `cierra:` sobre ids que se archivan.
- **Contenido**: `docs/00-contenido-fuente.md` trae 8 servicios con texto más mantenimiento edilicio (L20), es decir 9. Legales: L58 "Director técnico matriculado" (sin nombre), L63 "Empresa inscripta y habilitada — Ministerio de Agroindustria" (sin número), L64 Ley 10.699/88.

## Decisiones

- 2026-10-17 — El repositorio queda solo con el sitio público; el panel, la API y la app pasan al repositorio detach — pedido del usuario — reemplaza a: 2026-09-28 (un único proyecto Django sitio + panel + API)
- 2026-10-17 — El contenido del sitio se edita desde el admin de Django; no hay panel de contenido — pedido del usuario — reemplaza a: 2026-10-07 (panel de contenido en la ola 2)
- 2026-10-17 — El fixture lleva 9 servicios: los 8 de la Carta más mantenimiento edilicio — decisión del usuario; la Carta no trae más, y los 12 son sectores — reemplaza a: (nada; confirma 2026-09-28 sobre el fixture de 9)
- 2026-10-17 — `Servicio` conserva las secciones del diseño aprobado: nombre, slug, resumen, problema (el "texto"), metodos, adicional, faq, sectores, foto, orden, publicado, titulo_seo — decisión del usuario — reemplaza a: (nada)
- 2026-10-17 — Se quita `apps/accounts`; se usa `django.contrib.auth.User`, y `limites.py`/`red.py` pasan a `config/` con el mismo comportamiento para el login del admin — decisión del usuario — reemplaza a: (nada)
- 2026-10-17 — Los pendientes abiertos que aplican al sitio se re-declaran como `P-web-independiente-<n>`; los del panel y la API quedan en `docs/planes/historico/`, del repo detach — decisión del usuario — reemplaza a: (nada)
- 2026-10-17 — `Configuracion` suma `habilitacion`, `ley` y `director_tecnico`. `empresa.html` los muestra con el mismo texto que hoy, y el fixture carga exactamente esos textos de la Carta. `director_tecnico` queda vacío (la Carta no da nombre) y la página muestra "Director técnico matriculado". `_respaldos.html` y `servicio.html:55` quedan fijos — pedido del usuario — reemplaza a: 2026-10-07 (los datos legales no entran en `Configuracion`)
- 2026-10-17 — `/q/<uuid>/` se conserva: es del sitio, no depende de otra app y puede haber QR impresos que apuntan al dominio — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-17 — La vista previa del admin es una URL propia del ModelAdmin (`<pk>/vista-previa/`, envuelta en `admin_site.admin_view`). Renderiza la plantilla pública aunque el servicio no esté publicado y responde con `X-Robots-Tag: noindex` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-17 — Los ModelAdmin usan `form=` con los formularios de `apps/web/forms.py` (reprocesado de imágenes, `clean_redes`). Resuelve P-sitio-publico-12 y P-robustez-panel-5, que se archivan sin `cierra:` porque sus planes van a `historico/` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-17 — En DEBUG, `config/urls.py` sirve `MEDIA_URL`: `media/` ya solo tiene contenido público (logos y fotos de servicios). El servido en producción queda pendiente — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-17 — Excepción a la tabla de propiedad, solo para este plan. T1 (delegada) escribe `config/**`, `requirements.txt` y `.env.example`, que son del principal, y borra `templates/base.html` y `static/css/panel.css`, que son de "diseño". T3 escribe la línea de `servicios` en `INSTALLED_APPS` y el `static(MEDIA_URL)` de `config/urls.py`. Retirar una app no se separa de su registro en settings, y ninguna otra subtarea de la misma ola toca esos archivos — decisión del usuario al aprobar el plan (frontera del esquema; juez-plan la marcó) — reemplaza a: (nada)
- 2026-10-17 — `apps/servicios` sobrevive a la ola 1 reducida a modelos, migraciones y fixture, y T3 la borra al independizar `apps/web`. Así cada ola integra en verde — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-17 — `docs/decisiones.md` y `docs/bitacora.md` se reescriben. El contenido anterior pasa a `docs/historico/decisiones-proyecto-completo.md` y `docs/historico/bitacora-proyecto-completo.md`, sin editar. Las decisiones vigentes del sitio se vuelven a escribir cada una con su "reemplaza a" — decidida por Claude, revisable — reemplaza a: (nada)

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | ninguna nueva (se borran las de las apps retiradas) |
| 2 | T3, T4, T5 (integración y archivo de planes) | web (0001 nueva; se borran 0001 y 0002) |
| 3 | T6, T7 (integración y cierre) | ninguna |

## Subtareas

### T1 — Retirar panel, API, apps de dominio y accounts

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**:
  - Borrar: `apps/{accounts,clientes,sitios,proyectos,visitas,productos,informes,panel,api}/**`, `templates/base.html`, `templates/panel/**`, `static/css/panel.css`, `static/vendor/**`, `demo.bat`, `herramientas/empaquetar_demo.py`, `herramientas/humo_demo.py`, `docs/api/**`, `docs/demo-cliente.md`.
  - `apps/servicios/**`: borrar `api_urls.py`, `panel_*.py`, `templates/` y los tests de panel o API; quedan modelos, migraciones, fixture y admin.
  - En `apps/web`: borrar `panel_views.py`, `panel_urls.py`, `api_urls.py`, `templates/web/panel/**`, `tests/test_panel.py`, `tests/test_seguridad_contenido.py` y `tests/test_base.py`; editar `tests/test_rutas.py`, `tests/test_paginas.py` (solo los tests de robots y de la 404 bajo `/panel/`), `tests/test_csp.py`, `tests/test_cabeceras.py` (comentario), `templates/404.html` y `templates/web/paginas/robots.txt`.
  - `config/**`: settings, `urls.py`, `admin.py`, nuevos `config/limites.py` y `config/red.py`, `tests/**`.
  - `requirements.txt`, `.env.example`.
- **No puede tocar**: `docs/planes/`, `apps/web/models.py`, `apps/web/migrations/`, `apps/web/fixtures/`, `apps/web/views.py`, `templates/web/**`, `apps/web/templates/web/paginas/*.html`, `static/css/web.css`, `static/img/**`, `static/fonts/**`, `.claude/**`, `CLAUDE.md`.
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (comandos canónicos) y `.agents/skills/django-security/SKILL.md` § autenticación.
- **Worktree**: sí (`worktrees/web-independiente-T1`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 700 líneas agregadas (incluye mover `limites.py`, `red.py` y sus tests)
- **Qué hacer**:
  1. Borrar las apps y archivos listados. Sacar de `base.py` las apps, `rest_framework*`, `drf_spectacular*` y `simple_history` (app y middleware), `REST_FRAMEWORK`, `SPECTACULAR_SETTINGS`, `SIMPLE_JWT`, los ajustes de dominio y `AUTH_USER_MODEL`. Pasar `LOGIN_URL`, `LOGIN_REDIRECT_URL` y `LOGOUT_REDIRECT_URL` al admin. Conservar CSP, Referrer-Policy, `NUM_PROXIES`, los cupos de login, el logging y `SITE_URL`.
  2. Mover `apps/accounts/limites.py` y `red.py` a `config/` (`config/admin.py` importa de ahí) con sus tests en `config/tests/`. El login del admin conserva los tres baldes.
  3. `config/urls.py`: solo `admin/` y `""`. `apps/web`: quitar todo enlace a `/panel/` y `/api/` (`404.html`, `robots.txt` y tests de rutas).
  4. `requirements.txt` sin los paquetes listados en el Contexto. `.env.example` sin las variables de dominio ni `STORAGE_BACKEND`/`AWS_*`.
  5. Tests nuevos en `config/tests/test_retiro.py` y `config/tests/test_limites_admin.py`.
- **Criterios**:
  - `[no-existe]` `apps/panel`
  - `[no-existe]` `apps/api`
  - `[no-existe]` `apps/accounts`
  - `[cmd]` `for a in clientes sitios proyectos visitas productos informes; do test ! -e apps/$a || exit 1; done`
  - `[no-existe]` `templates/panel`
  - `[no-existe]` `static/vendor`
  - `[no-existe]` `demo.bat`
  - `[no-existe]` `docs/api`
  - `[grep-0]` `grep -rn "rest_framework\|simple_history\|drf_spectacular\|simplejwt\|AUTH_USER_MODEL" config/settings config/urls.py config/admin.py config/apps.py`
  - `[grep-0]` `grep -rn "rest_framework" config/ --exclude-dir=tests`
  - `[grep-0]` `grep -niE "^(djangorestframework|django-simple-history|weasyprint|segno|pypdfium2|drf-spectacular|django-storages|jsonschema)" requirements.txt`
  - `[grep-0]` `grep -rnE "apps\.(accounts|panel|api|clientes|sitios|proyectos|visitas|productos|informes)" config/ apps/ templates/ --exclude-dir=tests`
  - `[grep-0]` `grep -rnE "/panel/|/api/" apps/web/templates/`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_retiro.RetiroTests.test_apps_retiradas_no_estan_instaladas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_retiro.RetiroTests.test_panel_y_api_dan_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_retiro.RetiroTests.test_usuario_es_el_de_django --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_admin.LimiteLoginAdminTests.test_admin_bloquea_tras_fallos_por_ip --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T1`

### T2 — Integración (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/web-independiente` de T1, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh web-independiente T1 plan/web-independiente <rutas de T1>`.
  3. Crear `worktrees/web-independiente-T3` y `-T4` con `worktree-crear.sh … plan/web-independiente`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/web-independiente | grep -q "T1: integra web-independiente-T1"`

### T3 — Modelo de contenido propio, fixture, vistas y humo

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**:
  - `apps/web/models.py`, `apps/web/migrations/**` (borrar 0001 y 0002, crear 0001 nueva), `apps/web/fixtures/contenido_inicial.json`, `apps/web/views.py`, `apps/web/forms.py` (solo para que importe: `PaginaServicioForm` → `ServicioForm`), `apps/web/admin.py` (solo para que importe), `apps/web/tests/**`.
  - `apps/web/templates/web/paginas/{inicio,servicio,empresa}.html` y `templates/web/base_web.html`, solo en las variables.
  - Borrar `apps/servicios/**`. En `config/settings/base.py`, solo la línea `apps.servicios`. En `config/urls.py`, solo el `static(MEDIA_URL)` en DEBUG.
  - `herramientas/humo_web.py` (nuevo).
- **No puede tocar**: `docs/planes/`, `static/**`, `templates/web/**` fuera de `base_web.html`, `_respaldos.html`, `_contacto*.html`, `.claude/**`, `CLAUDE.md`, `docs/**`.
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models y `.agents/skills/test-driven-development/SKILL.md`.
- **Worktree**: sí (`worktrees/web-independiente-T3`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 1200 líneas agregadas (unas 450 son el fixture)
- **Qué hacer**:
  1. **`Servicio`**: reemplaza a `PaginaServicio` y `TipoServicio`. Campos: `nombre`, `slug` único, `titulo_seo`, `resumen`, `problema`, `metodos`, `adicional`, `faq`, `sectores` (con `validar_sectores`), `foto` (`ruta_portada` y `VALIDADORES_IMAGEN`), `orden` y `publicado`. El queryset `publicados()` ordena por `orden` y nombre. `get_absolute_url` apunta a `web:servicio`.
  2. **`Configuracion` y `ClienteDestacado`**: `Configuracion` suma `habilitacion`, `ley` y `director_tecnico` (CharField, blank). `ClienteDestacado` queda igual. Una sola migración `0001_initial` sin dependencias de otras apps. Todos los `verbose_name` en español.
  3. **Fixture**: los 9 servicios con los textos actuales de `contenido_inicial.json` (`nombre`/`slug` del tipo, `orden` igual al pk viejo, todos publicados), la configuración actual más los textos legales de la Carta (L63, L64; `director_tecnico` vacío) y los 13 clientes.
  4. **Vistas y plantillas**: leen `Servicio`. `empresa.html` muestra `config.habilitacion`, `config.ley` y el director técnico con el mismo texto que hoy. El test de plantillas sin formularios se migra a `test_plantillas.py`.
  5. **`herramientas/humo_web.py`**:
     - Usa una base SQLite temporal (`DATABASE_URL`), corre `migrate` y `loaddata contenido_inicial`, y levanta `runserver` en un puerto libre con `DJANGO_ENV=development`.
     - Comprueba con la biblioteca estándar `GET /` → 200 y `GET /servicio/control-plagas-urbanas/` → 200.
     - Apaga el árbol de procesos en un `finally` y sale con 0 solo si todo pasó.
- **Criterios**:
  - `[no-existe]` `apps/servicios`
  - `[grep-0]` `grep -rnE "TipoServicio|PaginaServicio|apps\.servicios" apps/ config/ templates/`
  - `[cmd]` `test "$(ls apps/web/migrations/0*.py | wc -l)" -eq 1`
  - `[grep-0]` `grep -rnE "\(\"servicios\"|\('servicios'" apps/web/migrations/`
  - `[grep-0]` `grep -rniE "<form" templates/web apps/web/templates/web/paginas apps/web/templates/404.html apps/web/templates/500.html`
  - `[grep-0]` `grep -rni "presupuesto" templates/ apps/web/templates/`
  - `[grep-1]` `grep -n "10.699/88" apps/web/fixtures/contenido_inicial.json`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_fixture.FixtureTests.test_carga_nueve_servicios_publicados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_fixture.FixtureTests.test_configuracion_trae_datos_legales_de_la_carta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_publicas.PaginasPublicasTests.test_cada_servicio_del_fixture_y_las_paginas_fijas_dan_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_publicas.PaginasPublicasTests.test_servicio_con_publicado_falso_da_404_y_sale_del_menu --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_publicas.PaginasPublicasTests.test_empresa_muestra_datos_legales_de_configuracion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_plantillas.PlantillasPublicasTests.test_sin_form_ni_presupuesto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ServicioTests.test_publicados_ordena_por_orden_y_excluye_no_publicados --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/humo_web.py`
  - `[cmd]` `git diff --quiet "$(git log --format=%h --grep='^docs(plan): web-independiente' | tail -1)" -- static/css/web.css static/img static/fonts`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1200 --subtarea T3`

### T4 — Reescribir el esquema de trabajo y la documentación para el sitio solo

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `CLAUDE.md`, `.claude/skills/convenciones-proyecto/SKILL.md`, `.claude/agents/auditor-seguridad.md`, `.claude/agents/juez-plan.md`, `docs/plantilla-plan.md`, `docs/01-modelo-y-arquitectura.md`, `docs/02-diseno.md`, `docs/despliegue.md`, `docs/ARRANQUE.md`
- **No puede tocar**: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `docs/00-contenido-fuente.md`, `.claude/hooks/**`, `apps/`, `config/`, `templates/`, `static/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (estructura actual) y la sección de este plan `## Decisiones`.
- **Worktree**: sí (`worktrees/web-independiente-T4`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**:
  1. **`CLAUDE.md`**: mismo esquema (plan → delegación → verificación, olas, worktrees, hooks y cierre). El proyecto se describe como "repositorio del sitio público". Sin API ni app móvil, y el `mobile/` sale de la navegación.
  2. **`convenciones-proyecto`**: stack reducido; estructura (`apps/web`, `config/`); tabla de propiedad sin api ni panel; olas sin grafo de dominio; comandos (incluido `herramientas/humo_web.py`); mapa de rutas (`/`, `/servicio/<slug>/`, `/empresa/`, `/contacto/`, `/q/<uuid>/`, `/sitemap.xml`, `/robots.txt`, `/admin/`); sin roles.
  3. **`docs/01`**: el modelo de contenido del sitio (Servicio, ClienteDestacado, Configuracion, Sector), la edición desde el admin y la vista previa. **`docs/02`**: quitar el panel y corregir "12 tarjetas" de servicios a 9. **`despliegue.md`** y **`ARRANQUE.md`**: sin panel, sin `cargar_demo` ni `cerrar_visitas_abiertas`.
  4. **`auditor-seguridad.md`**: alcance del admin, el login, las imágenes subidas, las cabeceras y los settings de producción.
  5. **`juez-plan.md`**: sin el grafo de FK de dominio, conservando los textos que protege `test_agentes.py`.
  6. **`plantilla-plan.md`**: `áreas` y `seguridad` del sitio. El paso de integración ya no cablea `apps/api`/`apps/panel`. Se mantienen la integración final y los 6 criterios de cierre global.
- **Criterios**:
  - `[grep-0]` `grep -nE "/api/v1|apps/panel|apps/api|simplejwt|rest_framework|mobile/" CLAUDE.md .claude/skills/convenciones-proyecto/SKILL.md docs/plantilla-plan.md`
  - `[grep-0]` `grep -niE "jwt|get_queryset|visitas|proyectos|qr_codigo" .claude/agents/juez-plan.md .claude/agents/auditor-seguridad.md`
  - `[grep-1]` `grep -n "repositorio del sitio público" CLAUDE.md`
  - `[grep-1]` `grep -n "/servicio/<slug>/" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "^### Servicio" docs/01-modelo-y-arquitectura.md`
  - `[grep-0]` `grep -n "12 tarjetas" docs/02-diseno.md`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py .claude/hooks/test_agentes.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T4`

### T5 — Integración y archivo de planes (principal)

- **Ola**: 2 (después de verificar T3 y T4)
- **Depende de**: T3, T4
- **Pasos**:
  1. Revisar `cambios.sh` de T3 y T4; integrar cada una con `worktree-integrar.sh` desde la raíz.
  2. `git mv` de todos los `docs/planes/2026-*.md`, salvo `2026-10-17-web-independiente.md`, a `docs/planes/historico/`, en un commit `T5: archiva planes en docs/planes/historico/`.
  3. Crear `worktrees/web-independiente-T6`.
- **Presupuesto**: no aplica (merges, `git mv` sin líneas nuevas y `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/web-independiente | grep -q "T3: integra web-independiente-T3"`
  - `[cmd]` `git log --oneline plan/web-independiente | grep -q "T4: integra web-independiente-T4"`
  - `[existe]` `docs/planes/historico/2026-10-12-demo-portatil.md`
  - `[existe]` `docs/planes/historico/2026-10-01-esqueleto.md`
  - `[no-existe]` `docs/planes/2026-10-12-demo-portatil.md`
  - `[no-existe]` `docs/planes/2026-10-01-esqueleto.md`
  - `[cmd]` `test "$(ls docs/planes/historico/2026-*.md | wc -l)" -eq 30`

### T6 — Admin en español con vista previa y validación de imágenes y redes

- **Ola**: 3
- **Depende de**: T5
- **Puede tocar**: `apps/web/admin.py`, `apps/web/forms.py`, `apps/web/templates/admin/web/**` (nuevo), `apps/web/tests/test_admin.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `apps/web/models.py`, `apps/web/migrations/`, `apps/web/views.py`, `templates/web/**`, `apps/web/templates/web/paginas/**`, `static/**`, `config/**`
- **Skill a leer antes**: `.agents/skills/django-expert/SKILL.md` (admin) y `.agents/skills/django-security/SKILL.md` (subida de archivos).
- **Worktree**: sí (`worktrees/web-independiente-T6`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  1. **`ServicioAdmin`**:
     - `form = ServicioForm` (reprocesa la foto y quita el EXIF).
     - `list_display` con nombre, orden y publicado; `list_editable` con orden y publicado; `prepopulated_fields` para el slug.
     - Miniatura de la foto como campo de solo lectura.
     - Botón "Vista previa" hacia `<pk>/vista-previa/` (URL agregada en `get_urls` con `self.admin_site.admin_view`), que renderiza `web/paginas/servicio.html` aunque no esté publicado y agrega `X-Robots-Tag: noindex`.
  2. **`ConfiguracionAdmin`**: `form = ConfiguracionForm` (`clean_redes`), con fieldsets "Contacto", "Datos legales" y "Redes y direcciones". Conserva `has_add_permission` y `has_delete_permission` de `apps/web/admin.py:10-14`. **`ClienteDestacadoAdmin`**: `form = ClienteDestacadoForm`, con miniatura del logo.
  3. Textos del admin en español (`verbose_name` ya viene de T3; títulos y fieldsets acá).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.VistaPreviaTests.test_superusuario_ve_servicio_no_publicado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.VistaPreviaTests.test_anonimo_redirige_al_login_del_admin --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.VistaPreviaTests.test_staff_no_superusuario_no_accede --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_foto_subida_pierde_exif --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_red_con_javascript_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_datos_legales_se_editan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminEspanolTests.test_listado_y_formulario_en_espanol --keepdb`
  - `[grep-1]` `grep -n "form = ServicioForm" apps/web/admin.py`
  - `[grep-1]` `grep -n "form = ConfiguracionForm" apps/web/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T6`

### T7 — Integración y cierre (principal)

- **Ola**: 3 (después de verificar T6 y su auditoría)
- **Depende de**: T6
- **Pasos**:
  1. Revisar e integrar T6 con `worktree-integrar.sh`.
  2. Reescribir la bitácora y las decisiones (un solo archivo de documentación cada una, inline):
     - Pasar el contenido de `docs/bitacora.md` y `docs/decisiones.md` a `docs/historico/` sin editar.
     - La bitácora nueva lleva "Estado actual" (`Plan activo: docs/planes/2026-10-17-web-independiente.md`) y una entrada que dice que los planes viejos están en `docs/planes/historico/`.
     - Las decisiones nuevas son las vigentes del sitio más las de este plan, en commits `T7: …`.
  3. Re-declarar en `## Pendientes que deja este plan` los abiertos que aplican al sitio. Al menos: media en producción (P-sitio-publico-1 / P-demo-cliente-8), datos de la empresa (-4, P-pendientes-heredados-31/-33, número de habilitación y nombre del director técnico), -8, -10, -11, -14, -15, -16, la barrera de `dev.py` (P-pendientes-heredados-15, P-demo-cliente-4), `NUM_PROXIES` y la caché compartida para los baldes del admin (P-limites-ingreso-2/-3/-5/-6/-8, P-pendientes-heredados-21, P-demo-cliente-5), `CSRF_TRUSTED_ORIGINS` (P-demo-cliente-6), el tope de cuerpo en el login del admin (P-contrato-app-6, P-panel-23), el filtro de logging (P-pendientes-heredados-26) y `railway.json` (P-demo-cliente-13).
  4. Cierre global y verificación `TODO` con `verificador` y `verificador-b`, más `auditor-seguridad` sobre el plan entero.
- **Presupuesto**: 1300 líneas agregadas. `presupuesto.sh` usa `diff-tree --numstat` sin `-M`, así que el `git mv` de la bitácora (unas 410 líneas) y de las decisiones (unas 200) cuenta entero. Sobre eso, unas 300 de contenido nuevo.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/web-independiente | grep -q "T6: integra web-independiente-T6"`
  - `[existe]` `docs/historico/decisiones-proyecto-completo.md`
  - `[existe]` `docs/historico/bitacora-proyecto-completo.md`
  - `[grep-1]` `grep -n "^# Bitácora del sitio público de MAControl" docs/bitacora.md`
  - `[grep-1]` `grep -n "^# Decisiones del sitio público de MAControl" docs/decisiones.md`
  - `[grep-1]` `grep -n "docs/planes/historico/" docs/bitacora.md`
  - `[grep-1]` `grep -n "reemplaza a: 2026-09-28" docs/decisiones.md`
  - `[cmd]` `py -3 .claude/hooks/pendientes.py | grep -qE "^- P-web-independiente-[0-9]+ "`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/humo_web.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1300 --subtarea T7`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-17-web-independiente.md web-independiente`

## Registro de verificación

commit_base: da3eef5

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | en curso |
| T7 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-18 | T1 | eb66d12 | PASA (21/21) | verificador |
| 2026-10-18 | T1 | eb66d12 | PASA (20/20) | verificador-b; sin --keepdb también 92 OK |
| 2026-10-18 | T1 | eb66d12 | sin bloqueantes | auditor-seguridad: 2 menores (comentario SITE_URL/QR, despliegue.md), 2 observaciones (EXIF hasta T6, base nueva) |
| 2026-10-18 | T2 | (integración) | PASA (1/1) | principal; worktree-integrar.sh exit 0, 92 tests OK |
| 2026-10-18 | T3 | 6a76cdb | PASA (19/19) | verificador; 92→91 tests explicado (−7 de apps/servicios, +6 en apps/web) |
| 2026-10-18 | T3 | 6a76cdb | PASA (19/19) | verificador-b; textos de los 9 servicios idénticos al fixture anterior |
| 2026-10-18 | T3 | 6a76cdb | sin bloqueantes | auditor-seguridad: M1 humo sin DJANGO_SETTINGS_MODULE, M2 sin test de validadores de foto; O1-O3 |
| 2026-10-18 | T4 | 2c5dda5 | PASA (8/8) | verificador |
| 2026-10-18 | T4 | 2c5dda5 | PASA (8/8) | verificador-b; docs ubica 404/500 en templates/web/ (están en apps/web/templates/); vista previa llega en T6 |
| 2026-10-18 | T5 | (integración) | PASA (7/7) | principal; worktree-integrar T3 y T4 exit 0 (91 tests); 30 planes a historico/ |

## Pendientes que deja este plan

### Problemas

### Decisiones

### Cierra
