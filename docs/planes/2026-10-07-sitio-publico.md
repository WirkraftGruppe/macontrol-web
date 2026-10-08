# Plan: Sitio público de MAControl S.A.
<!-- flujo: commit "docs(plan): sitio-publico" antes del primer subagente; hash en Registro (commit_base:); criterios congelados; T<n>: commits; verificador por T<n> y TODO; '<commit_base>' literal entre comillas simples; corte de congelado en ## Registro de verificación; congelado.sh; hook verificar_plan.py -->
<!-- aprobación: juez-plan 2026-10-07 (3 bloqueantes corregidos); usuario 2026-10-07 -->
- **slug**: `sitio-publico`
- **fecha**: 2026-10-07
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): sitio-publico`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: construir el sitio público en `apps/web` (home, una página por servicio publicado, empresa, contacto telefónico, `/q/<uuid>/`, SEO básico) con contenido leído de la base (`web.Configuracion`, `web.PaginaServicio`, `web.ClienteDestacado`), un fixture inicial tomado de la Carta de Servicios y la edición de ese contenido desde el panel.
- **fuera de alcance**: panel más allá de las vistas de contenido web; formularios públicos de cualquier tipo; blog; multilenguaje; despliegue y servido de `media/` en producción; cambios en `templates/base.html`, `templates/panel/base.html`, `config/` y `apps/panel/**`, `apps/visitas/**`, `apps/sitios/**` (la sesión paralela ejecuta `robustez-datos` en esas apps).
- **áreas**: web | panel (vistas de contenido dentro de `apps/web`) | dominio (modelos de `apps/web`)
- **seguridad**: sí. Toca `/q/<uuid>/` (resolución de QR: no debe consultar la base ni exponer datos), roles (las vistas de panel exigen administrador) y subida de imágenes (logo de cliente, portada de servicio). `auditor-seguridad` corre en T6.

## Contexto mínimo
- `docs/02-diseno.md` define la dirección A en tema oscuro: tokens (:9-23), tipografía (:38-54), componentes (:65-73), estructura de la home (:77) y de la página de servicio (:79), responsive a 900 px (:81) y tabla de fotos (:88-94).
- `docs/00-contenido-fuente.md` tiene 8 servicios más mantenimiento edilicio (:20-53), 12 sectores (:68), 13 clientes (:71), las habilitaciones (:58-65) y los valores (:8). No trae preguntas frecuentes.
- `docs/01-modelo-y-arquitectura.md` §3.12 (:133-134) describe los tres modelos de `web`. `TipoServicio` vive en `apps/servicios/models.py:6-19` (con `slug` único) y tiene un fixture de 9 registros, pk 1-9, en `apps/servicios/fixtures/tipos_servicio.json`.
- `apps/web` hoy:
  - `urls.py` define `inicio` y `qr`; `views.py` devuelve texto plano.
  - `panel_urls.py` está vacío, pero ya lo incluye `apps/panel/urls.py:25` como `panel:web:`.
  - No hay modelos, migraciones, plantillas ni admin.
  - Tests: `test_base.py`, `test_cabeceras.py`, `test_csp.py`, `test_rutas.py`. `test_rutas.py` comprueba el texto de `/q/`.
- `templates/base.html` tiene el CSS inline con nonce y un header fijo fuera de bloque, así que la web usa una base propia.
- La CSP de `config/settings/base.py:248-260` permite solo self: sin `style=""` inline, sin fuentes ni scripts externos.
- `static/fonts/` ya tiene los 7 woff2 de Barlow y Barlow Condensed, más `OFL.txt`.
- Las fotos originales están en `C:\Users\Emanuel\Desktop\WEB\MaControl\images-for-content\edited-with-ai\` (image1.jpg … image5.jpg, image3.webp), fuera del worktree.
- El panel usa `AdministradorRequeridoMixin` (`apps/accounts/mixins.py:4`) y el parcial `templates/panel/partials/formulario.html`, que contiene el `<form>`. El patrón de tests está en `apps/servicios/tests/test_panel.py:15-39`.

## Contrato entre subtareas (fijo)
- **Modelos (T1)**, en `apps/web/models.py`:
  - `Sector(models.TextChoices)`: los 12 sectores de la Carta (`docs/00-contenido-fuente.md:68`), con etiqueta literal.
  - `Configuracion` (singleton, pk=1):
    - `razon_social`, `eslogan`, `presentacion` (TextField), `telefono`, `whatsapp` (blank), `correo`, `horario` (blank).
    - `direcciones` (JSON, lista de `{"localidad", "direccion"}`) y `redes` (JSON, lista de `{"nombre", "url"}`, blank).
    - `Configuracion.obtener()` devuelve la fila pk=1 y la crea vacía si falta. `save()` fuerza pk=1.
    - Propiedades `telefono_href` (`tel:+54…`, solo dígitos) y `whatsapp_href` (`https://wa.me/54…`, o `""` si no hay WhatsApp).
  - `PaginaServicio`:
    - `tipo` (OneToOne a `servicios.TipoServicio`, `related_name="pagina"`, PROTECT).
    - `titulo_seo`, `resumen`, `problema`, `adicional` (blank).
    - `metodos` (JSON, lista de `{"titulo", "descripcion"}`), `faq` (JSON, lista de `{"pregunta", "respuesta"}`, puede estar vacía) y `sectores` (JSON, lista de valores de `Sector`, validada).
    - `imagen_portada` (ImageField, blank, `upload_to="servicios/"`) y `publicado` (bool).
    - `PaginaServicio.objects.publicadas()` devuelve las que tienen `publicado=True` y `tipo.activo=True`, con `select_related("tipo")` y orden `tipo_id`.
    - `get_absolute_url()` devuelve `reverse("web:servicio", args=[tipo.slug])`.
  - `ClienteDestacado`: `nombre`, `logo` (ImageField, blank, `upload_to="clientes/"`), `orden` (PositiveSmallInteger) y `activo` (bool). `ClienteDestacado.objects.activos()` devuelve los activos ordenados por `orden, nombre`.
  - Las imágenes subidas solo aceptan `png`, `jpg`, `jpeg` y `webp`, de hasta 2 MB. Los validadores van en `apps/web/validators.py`.
- **Base visual (T2)**, `templates/web/base_web.html`:
  - Plantilla autónoma: no extiende `base.html`.
  - Carga solo `static/css/web.css`. No usa scripts, `style=""` inline ni recursos externos.
  - Bloques: `title`, `meta_descripcion`, `og`, `contenido`.
  - La nav y el pie leen `config` (un `Configuracion`) y `paginas_nav` (un iterable de `PaginaServicio`) del contexto, y toleran que falten.
  - El menú móvil usa `<details>`.
  - Las clases de componentes quedan listadas en el comentario inicial de `web.css`, y T5 las consume tal cual.
- **Nombres de URL**:
  - T5: `web:inicio`, `web:servicio` (`servicio/<slug:slug>/`), `web:empresa`, `web:contacto`, `web:qr` (se conserva), `web:sitemap` (`sitemap.xml`) y `web:robots` (`robots.txt`).
  - T4: `panel:web:configuracion`, `panel:web:paginas`, `panel:web:pagina_editar` (pk), `panel:web:clientes`, `panel:web:cliente_alta` y `panel:web:cliente_editar` (pk).
- **Plantillas**:
  - T2 escribe `templates/web/base_web.html`.
  - T5 escribe las páginas públicas en `apps/web/templates/web/paginas/`, y además `apps/web/templates/404.html` y `500.html`.
  - T4 escribe las plantillas del panel en `apps/web/templates/web/panel/`. Incluyen `panel/partials/formulario.html` y no escriben `<form` literal, porque el criterio `[grep-0]` de formularios cubre `apps/web/templates/`.

## Olas
| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (modelos y contenido) ∥ T2 (diseño: CSS, base, imágenes); T3 (integración) | `web` (solo T1) |
| 2 | T4 (panel de contenido) ∥ T5 (vistas públicas y SEO); T6 (integración, auditoría, verificación TODO) | ninguna |

La ola 2 ramifica desde el commit de integración de T3. Las vistas dependen de los modelos de T1 y de `base_web.html` de T2.

## Subtareas

### T1 — Modelos, admin y fixture de contenido de `web`
- **Ola**: 1
- **Depende de**: —
- **Puede tocar**:
  - `apps/web/models.py`, `apps/web/validators.py`, `apps/web/admin.py`
  - `apps/web/migrations/**`
  - `apps/web/tests/test_contenido.py`
  - `docs/01-modelo-y-arquitectura.md` (solo §3.12)
  - (modificado: el fixture `apps/web/fixtures/contenido_inicial.json` pasa a T7)
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/web/fixtures/`, `apps/web/views.py`, `apps/web/urls.py`, `apps/web/panel_*.py`, `apps/servicios/**`, `apps/panel/**`, el resto de `apps/web/tests/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 900 líneas agregadas (el fixture JSON con los textos de 9 servicios ocupa unas 400; fijado de entrada, no se sube)
- **Qué hacer**:
  - Modelos, validadores y migración según el § Contrato. Admin técnico con los tres modelos; `Configuracion` sin alta si ya existe la fila.
  - `contenido_inicial.json` lleva, en este orden:
    - Los 9 `servicios.tiposervicio` copiados idénticos de `apps/servicios/fixtures/tipos_servicio.json`, para que `loaddata` funcione en una base vacía.
    - La `Configuracion`:
      - razón social `MAControl S.A.`, eslogan "Manejo integral de plagas"
      - teléfono `02241 49 6047`, correo `administracion@macontrol.com.ar`
      - direcciones Ricardo Naveiro 7 (Castelli) y Presidente Perón 427 (Chascomús)
      - WhatsApp, horario y redes vacíos
    - 9 `PaginaServicio` publicadas, una por tipo, redactadas solo con el texto de `docs/00-contenido-fuente.md`:
      - `faq` es `[]` en todas.
      - `adicional` solo donde la Carta trae un "Importante" o un servicio complementario.
      - No llevan cifras que no estén en la Carta ni testimonios.
    - 13 `ClienteDestacado` activos y sin logo, en el orden de `00-contenido-fuente.md:71`, con "YPF / Casa Rucery [?]" escrito como "YPF".
  - Actualizar §3.12 de `docs/01-modelo-y-arquitectura.md` con los campos del contrato:
    - `Configuracion` con `razon_social`, y `ClienteDestacado` con `activo`.
    - `sectores` escrito literalmente como "JSON de valores de web.Sector", reemplazando "M2M a choices".
    - Una frase que diga que los datos legales, las habilitaciones y el director técnico que pide el certificado (§3.10) se agregan a `Configuracion` en el plan de informes.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.ConfiguracionTests.test_singleton_y_fixture_carga --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.ConfiguracionTests.test_whatsapp_y_horario_vacios_y_href_de_telefono --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.PaginaServicioTests.test_fixture_una_pagina_por_tipo_y_faq_vacia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.PaginaServicioTests.test_tipos_del_fixture_coinciden_con_servicios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.PaginaServicioTests.test_sectores_fuera_de_la_lista_se_rechazan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.ClienteDestacadoTests.test_fixture_trae_13_clientes_activos_sin_logo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.ClienteDestacadoTests.test_logo_rechaza_extension_y_tamano_no_permitidos --keepdb`
  - `[grep-1]` `grep -n "MAControl S.A." apps/web/fixtures/contenido_inicial.json`
  - `[grep-0]` `grep -rin "presupuesto" apps/web/fixtures/`
  - `[grep-0]` `grep -n "Rucery" apps/web/fixtures/contenido_inicial.json`
  - `[grep-1]` `grep -n "JSON de valores de web.Sector" docs/01-modelo-y-arquitectura.md`
  - `[grep-0]` `grep -n "M2M a choices" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 900 --subtarea T1`
  - (`test_singleton_y_fixture_carga` carga el fixture con `call_command("loaddata", "contenido_inicial")` sobre la base de test. Reemplaza el `[cmd] loaddata` del pedido, porque el verificador no puede migrar ni escribir la base local).

### T2 — Diseño web: `web.css`, `base_web.html` e imágenes WebP
- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `static/css/web.css`, `static/img/*.webp`, `templates/web/base_web.html`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/base.html`, `templates/panel/**`, `static/css/panel.css`, `static/fonts/**` (ya están; solo se referencian), `static/img/logo.png`, `apps/**` (incluido `apps/web/tests/`: según la tabla de propiedad es de la subtarea de la app; los tests de diseño los escribe T5), `images-for-content/**` (solo lectura)
- **Skill a leer antes**: `.agents/skills/frontend-design/SKILL.md` y `.agents/skills/web-design-guidelines/SKILL.md` (las secciones de color, tipografía, foco y responsive), además de `docs/02-diseno.md` completo
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 700 líneas agregadas (las imágenes binarias no suman líneas)
- **Qué hacer**:
  - En `web.css`:
    - `@font-face` de los 7 woff2 existentes, con `font-display: swap`.
    - Tokens del tema oscuro de `02-diseno.md:9-32` en `:root`, escritos como `--nombre: #rrggbb` (un espacio, hex en minúscula), con los mismos nombres que el documento.
    - Los componentes de `02-diseno.md:65-73` (botón primario y secundario, enlace, tarjeta, tarjeta invertida, etiqueta, bloque de contacto, franja de advertencia), los layouts de home y servicio (grillas, hero, lateral) y el foco visible con `:focus-visible`.
    - Responsive a 900 px según `02-diseno.md:81`.
    - Comentario inicial con la lista de clases.
  - `base_web.html`, según el § Contrato:
    - nav con logo (`img/logo.png`), enlaces y botón de teléfono
    - pie con dirección, teléfono, correo y razón social
    - `<link rel="preload">` de las dos fuentes principales
  - Imágenes: convertir con Pillow las 5 fotos de `C:\Users\Emanuel\Desktop\WEB\MaControl\images-for-content\edited-with-ai\` a los nombres de `02-diseno.md:90-94`. WebP con 1600 px máximo de lado mayor y sin EXIF. El script de conversión no se commitea.
- **Criterios**:
  - (T2 no lleva `[test]` porque no es dueña de `apps/web/tests/`. Sus tests de diseño son de T5 y quedan en `test_diseno.DisenoWebTests`).
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py shell -c "from django.template.loader import render_to_string; render_to_string('web/base_web.html')"`
  - `[cmd]` `./venv/Scripts/python.exe -c "import re, sys, pathlib; css=pathlib.Path('static/css/web.css').read_text(encoding='utf-8'); t=['--bg: #0f1417','--surface: #161c21','--text: #e8e6df','--brand: #ffc600','--on-brand: #0f1417']; f=re.findall(r'fonts/([\w.-]+\.woff2)', css); sys.exit(0 if all(x in css for x in t) and len(set(f))==7 and all(pathlib.Path('static/fonts', x).exists() for x in f) else 1)"`
  - `[grep-1]` `grep -n "font-display: swap" static/css/web.css`
  - `[grep-0]` `grep -n "@import" static/css/web.css`
  - `[existe]` `static/img/hero-pulverizacion-quincho.webp`
  - `[existe]` `static/img/empresa-oficina-equipo.webp`
  - `[existe]` `static/img/mantenimiento-fachada-andamio.webp`
  - `[existe]` `static/img/fumigacion-termonebulizacion-cocina.webp`
  - `[existe]` `static/img/flota-vehiculos-industria.webp`
  - `[cmd]` `./venv/Scripts/python.exe -c "import sys; from PIL import Image; n=['hero-pulverizacion-quincho','empresa-oficina-equipo','mantenimiento-fachada-andamio','fumigacion-termonebulizacion-cocina','flota-vehiculos-industria']; ims=[Image.open('static/img/'+x+'.webp') for x in n]; sys.exit(0 if all(i.format=='WEBP' and max(i.size)<=1600 and len(i.getexif())==0 and 'exif' not in i.info for i in ims) else 1)"`
  - `[grep-0]` `grep -rn "fonts.googleapis" templates/ static/css/web.css`
  - `[grep-0]` `grep -n 'style="' templates/web/base_web.html`
  - `[grep-0]` `grep -n "<script" templates/web/base_web.html`
  - `[grep-1]` `grep -n "focus-visible" static/css/web.css`
  - `[grep-1]` `grep -n "max-width: 900px" static/css/web.css`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T2`

### T7 — Fixture de contenido inicial (partida de T1)
- **Ola**: 1
- **Depende de**: T1 (mismo worktree y rama `sitio-publico-T1`)
- **Puede tocar**: `apps/web/fixtures/contenido_inicial.json`
- **No puede tocar**: `docs/planes/`, todo lo demás
- **Skill a leer antes**: `docs/00-contenido-fuente.md` completo
- **Worktree**: sí (`worktrees/sitio-publico-T1`)
- **Ruta**: delegada (implementador)
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**:
  - Rehacer los commits del worktree de T1: un `T1:` sin el fixture y un `T7:` con el fixture. El contenido es el que describe T1 § Qué hacer.
  - En `sectores` de cada `PaginaServicio`, solo los sectores que la Carta asocia explícitamente con ese servicio: Servicio MIPU → gastronómicos y comercios; Manejo integral en edificios → torres, edificios y condominios. El resto queda en `[]`. Decisión del usuario del 2026-10-07.
- **Criterios**:
  - `[grep-1]` `grep -n "MAControl S.A." apps/web/fixtures/contenido_inicial.json`
  - `[grep-0]` `grep -rin "presupuesto" apps/web/fixtures/`
  - `[grep-0]` `grep -n "Rucery" apps/web/fixtures/contenido_inicial.json`
  - `[cmd]` `./venv/Scripts/python.exe -c "import json, sys; d=json.load(open('apps/web/fixtures/contenido_inicial.json', encoding='utf-8')); s=[o['fields']['sectores'] for o in d if o['model']=='web.paginaservicio']; sys.exit(0 if len(s)==9 and sum(1 for x in s if x)==2 and all(len(x)<=1 for x in s) else 1)"`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T7`

### T3 — Integración de la ola 1 (principal)
- **Ola**: 1 (después de verificar T1, T7 y T2)
- **Depende de**: T1, T7, T2
- **Pasos**:
  1. `verificador` y `verificador-b` sobre T1 y T2 (`refutador` si discrepan). Revisar `bash .claude/hooks/cambios.sh . plan/sitio-publico` de cada worktree, no los informes.
  2. Desde la raíz del worktree del plan:
     - `bash .claude/hooks/worktree-integrar.sh sitio-publico T1 plan/sitio-publico apps/web/models.py apps/web/validators.py apps/web/admin.py apps/web/migrations apps/web/fixtures apps/web/tests/test_contenido.py docs/01-modelo-y-arquitectura.md`
     - `bash .claude/hooks/worktree-integrar.sh sitio-publico T2 plan/sitio-publico static/css/web.css static/img templates/web`
  3. Crear los worktrees de T4 y T5 con `bash .claude/hooks/worktree-crear.sh sitio-publico T<n> plan/sitio-publico`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/sitio-publico | grep -q "T1: integra sitio-publico-T1"`
  - `[cmd]` `git log --oneline plan/sitio-publico | grep -q "T2: integra sitio-publico-T2"`

### T4 — Panel: edición del contenido web
- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/web/panel_views.py`, `apps/web/panel_urls.py`, `apps/web/forms.py`, `apps/web/templates/web/panel/**`, `apps/web/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/panel/**` (incluido `apps/panel/urls.py`, que ya incluye `apps.web.panel_urls`), `templates/**`, `static/**`, `apps/web/models.py`, `apps/web/migrations/**`, `apps/web/views.py`, `apps/web/urls.py`, `apps/web/templates/web/paginas/**`, el resto de `apps/web/tests/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Views y § Forms; `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - Vistas con `AdministradorRequeridoMixin` y nombres según el § Contrato:
    - edición de `Configuracion` (vía `Configuracion.obtener()`);
    - listado y edición de `PaginaServicio` (sin alta: hay una por tipo);
    - listado, alta y edición de `ClienteDestacado`.
  - Formularios con `fields` explícitos. Los campos JSON (`metodos`, `faq`, `direcciones`, `redes`) se validan contra la forma del contrato. `sectores` se edita como selección múltiple de `Sector`.
  - Las plantillas extienden `panel/base.html` e incluyen `panel/partials/formulario.html`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_panel.ContenidoPanelTests.test_editar_configuracion_exige_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_panel.ContenidoPanelTests.test_empleado_recibe_403_y_anonimo_va_al_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_panel.ContenidoPanelTests.test_admin_edita_pagina_servicio_y_rechaza_metodos_mal_formados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_panel.ContenidoPanelTests.test_admin_da_de_alta_cliente_y_rechaza_logo_no_imagen --keepdb`
  - `[grep-0]` `grep -rln "<form" apps/web/templates/web/panel/`
  - `[grep-0]` `grep -rin "presupuesto" apps/web/templates/web/panel/`
  - `[grep-1]` `grep -n "AdministradorRequeridoMixin" apps/web/panel_views.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T4`

### T5 — Vistas públicas, plantillas y SEO
- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**:
  - `apps/web/views.py`, `apps/web/urls.py`
  - `apps/web/templates/web/paginas/**`, `apps/web/templates/404.html`, `apps/web/templates/500.html`
  - `apps/web/tests/test_paginas.py`, `apps/web/tests/test_recorrido.py`, `apps/web/tests/test_diseno.py`, `apps/web/tests/test_rutas.py` (solo el texto esperado de `/q/`)
  - `apps/web/tests/test_contenido.py` (solo agregar el método `PaginaServicioTests.test_solo_publicadas_en_home_y_sitemap`)
- **No puede tocar**:
  - `docs/planes/`, `config/`, `templates/**` (incluido `templates/web/base_web.html`, que es de T2: si le falta algo, va a Pendientes), `static/**`
  - `apps/web/models.py`, `apps/web/migrations/**`, `apps/web/panel_*.py`, `apps/web/forms.py`, `apps/web/templates/web/panel/**`
  - `apps/panel/**`
- **Skill a leer antes**: `.agents/skills/frontend-design/SKILL.md`, `.agents/skills/web-design-guidelines/SKILL.md` (semántica, foco, imágenes, metadatos), `.agents/skills/django-conventions/SKILL.md` § Views, y `docs/02-diseno.md:77-81`
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 900 líneas agregadas (cinco páginas, dos de error, sitemap, robots y tests; fijado de entrada)
- **Qué hacer**:
  - Las páginas extienden `web/base_web.html`. Cada vista pasa `config` (`Configuracion.obtener()`) y `paginas_nav` (`PaginaServicio.objects.publicadas()`).
  - Home, con las secciones en el orden de `02-diseno.md:77`, cada una con `id`:
    - `hero` · `respaldos` · `servicios` (las publicadas) · `mantenimiento` · `sectores` (los 12 de `Sector`) · `como-trabajamos` · `empresa` · `clientes` (los activos; logo si hay, si no el nombre) · `contacto`
    - Los textos fijos (cuatro respaldos, tres valores y los cuatro pasos monitoreo, detección, exclusión y prevención) salen literales de la Carta.
  - `servicio/<slug>/`:
    - Sigue la estructura de `02-diseno.md:79`. Da 404 si la página no está publicada o el tipo está inactivo.
    - Las preguntas frecuentes no se muestran si `faq` está vacía.
    - Sin portada cargada, usa una imagen estática por slug.
  - `empresa/` y `contacto/`:
    - El teléfono es la acción principal (`config.telefono_href`); WhatsApp aparece solo si `config.whatsapp_href`.
    - No hay ningún formulario.
  - `/q/<uuid>/`:
    - Plantilla autónoma con el texto fijo "Punto de control de MAControl S.A. — use la app".
    - Cero consultas, sin repetir el código.
    - Actualizar la aserción de texto en `test_rutas.py`.
  - SEO:
    - `sitemap.xml`: vista propia con las URL absolutas desde `settings.SITE_URL`, que lista inicio, empresa, contacto y los servicios publicados. No usa `django.contrib.sitemaps`.
    - `robots.txt`: permite todo salvo `/panel/`, `/api/`, `/admin/` y `/q/`, y declara el sitemap.
    - `<meta name="description">`, `<link rel="canonical">` y `og:title`, `og:description`, `og:url`, `og:image` (absoluta) en cada página.
  - `404.html` y `500.html` propias y autónomas. La 500 no consulta la base.
  - `RecorridoPublicoTests` recorre home → tres servicios enlazados desde la home → empresa → contacto → `/q/<uuid>/`, siguiendo los `href` del HTML.
  - Test de que ninguna plantilla en `templates/web/` y `apps/web/templates/web/paginas/` contiene `<form` ni "presupuesto".
  - `test_diseno.DisenoWebTests` cubre la base que entregó T2: la CSP de `/` sigue sin `unsafe-inline` y la home carga `web.css` sin recursos externos, y `base_web.html` renderiza sin contexto.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_contenido.PaginaServicioTests.test_solo_publicadas_en_home_y_sitemap --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.HomeTests.test_secciones_en_orden_y_sin_formularios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.ServicioTests.test_servicio_publicado_200_no_publicado_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.ServicioTests.test_faq_vacia_no_muestra_la_seccion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.ContactoTests.test_telefono_principal_y_whatsapp_solo_si_esta_configurado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.QrTests.test_q_uuid_no_consulta_la_base_y_no_expone_datos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.SeoTests.test_sitemap_robots_y_og --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.ErroresTests.test_404_propia_y_500_sin_base --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.PlantillasTests.test_ninguna_plantilla_publica_tiene_form_ni_presupuesto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_recorrido.RecorridoPublicoTests.test_visitante_recorre_el_sitio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno.DisenoWebTests.test_home_carga_web_css_sin_recursos_externos_ni_unsafe_inline --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno.DisenoWebTests.test_base_web_renderiza_sin_contexto --keepdb`
  - `[grep-0]` `grep -rln "<form" templates/web/ apps/web/templates/`
  - `[grep-0]` `grep -rin "presupuesto" templates/web/ apps/web/templates/ apps/web/fixtures/`
  - `[grep-0]` `grep -rn "fonts.googleapis" templates/ apps/web/templates/`
  - `[grep-0]` `grep -rn 'style="' apps/web/templates/web/paginas/ apps/web/templates/404.html apps/web/templates/500.html`
  - `[grep-0]` `grep -rn "django.contrib.sitemaps" apps/web/`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 900 --subtarea T5`

### T6 — Integración de la ola 2, auditoría y verificación TODO (principal)
- **Ola**: 2 (después de verificar T4 y T5)
- **Depende de**: T4, T5
- **Pasos**:
  1. `verificador` y `verificador-b` sobre T4 y T5 (`refutador` si discrepan). Revisar `cambios.sh` de cada worktree.
  2. Integrar desde la raíz del worktree del plan:
     - `bash .claude/hooks/worktree-integrar.sh sitio-publico T4 plan/sitio-publico apps/web/panel_views.py apps/web/panel_urls.py apps/web/forms.py apps/web/templates/web/panel apps/web/tests/test_panel.py`
     - `bash .claude/hooks/worktree-integrar.sh sitio-publico T5 plan/sitio-publico apps/web/views.py apps/web/urls.py apps/web/templates/web/paginas apps/web/templates/404.html apps/web/templates/500.html apps/web/tests/test_paginas.py apps/web/tests/test_recorrido.py apps/web/tests/test_diseno.py apps/web/tests/test_rutas.py apps/web/tests/test_contenido.py`
  3. `auditor-seguridad` sobre:
     - `/q/<uuid>/` (sin consultas ni datos);
     - las vistas de panel (rol administrador);
     - los validadores de imagen;
     - que el sitio público no exponga datos de empleados, de clientes de servicio ni coordenadas.
  4. Verificación `TODO` con `verificador` y `verificador-b`.
  5. Prueba en el navegador por el usuario, como paso de cierre no verificable por tests: contraste del amarillo sobre carbón, foco visible, Lighthouse en móvil y carga de fuentes sin FOIT prolongado. El resultado queda anotado en el Registro.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/sitio-publico | grep -q "T4: integra sitio-publico-T4"`
  - `[cmd]` `git log --oneline plan/sitio-publico | grep -q "T5: integra sitio-publico-T5"`
  - `[grep-0]` `grep -rln "<form" templates/web/ apps/web/templates/`
  - `[grep-0]` `grep -rin "presupuesto" templates/web/ apps/web/templates/ apps/web/fixtures/`
  - `[existe]` `static/fonts/OFL.txt`
  - `[existe]` `static/img/hero-pulverizacion-quincho.webp`

## Criterios de cierre global
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-07-sitio-publico.md sitio-publico`

## Registro de verificación
commit_base: 45fb49c

### Estado de subtareas
| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | pendiente |
| T7 | hecha |

### Corridas
| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-07 | T2 | 8285189 | verificador: 17/17 PASA; verificador-b: 17/17 PASA | ambos marcan CONTRATO MODIFICADO (9ac7c9d, aprobado por el usuario); el bloque de T2 no cambió |
| 2026-10-07 | T1, T7 | 04e4410 | verificador: 21/21 PASA; verificador-b: 18/18 PASA | CONTRATO MODIFICADO (9ac7c9d); T1 490/900, T7 491/600; direcciones del fixture entregadas por el usuario en el pedido |
| 2026-10-07 | T3 (integración ola 1) | 9007d07 | worktree-integrar: makemigrations --check y test --keepdb OK (538 tests) | T1 (con T7) y T2 integradas |
| 2026-10-07 | T4 | 2ed1344 | verificador: 9/9 PASA; verificador-b: 9/9 PASA | CONTRATO MODIFICADO (9ac7c9d); 385/400; las 6 vistas exigen administrador || 2026-10-07 | T5 | e02ac4a | verificador: 19/19 PASA (+4 comprobaciones); verificador-b: 19/19 PASA | CONTRATO MODIFICADO (9ac7c9d); 740/900; qr sin consultas; textos fijos literales de la Carta |

## Pendientes que deja este plan
### Problemas
- P-sitio-publico-1 [importante] `media/` no se sirve en ninguna parte: los logos y portadas que se suban desde el panel no se ven hasta definir el servido público de `media/clientes/` y `media/servicios/` sin exponer las fotos de visitas — destino: `despliegue`.
- P-sitio-publico-2 [menor] El menú de `templates/panel/base.html` no enlaza a "Contenido web" (`panel:web:*`). Es un archivo de la subtarea "diseño" del panel y la sesión paralela toca `apps/panel` — destino: `robustez-panel`.
- P-sitio-publico-3 [menor] `cargar_demo` no carga `contenido_inicial` (está en `apps/panel`, que toca la sesión paralela) — destino: `robustez-panel`.
- P-sitio-publico-4 [observación] Faltan datos de la empresa: WhatsApp, horario, handle real de Instagram, autorización de uso de logos de clientes, nombre exacto del cliente "YPF / Casa Rucery [?]" (cargado como "YPF") y fotos de estaciones cebaderas y sellado de techos — destino: `empresa`.
- P-sitio-publico-5 [menor] `docs/02-diseno.md:77` sigue diciendo "12 tarjetas" de servicios y "8 tarjetas" de sectores — se actualiza al fusionar.
- P-sitio-publico-6 [importante] `loaddata contenido_inicial` sobreescribe `nombre`, `descripcion` y `activo` de los `TipoServicio` pk 1-9. Además falla con IntegrityError si una base tiene alguno de esos slugs con otro pk. En producción se carga una sola vez, sobre una base vacía — destino: `despliegue`.
- P-sitio-publico-7 [importante] `Configuracion` no lleva todavía los datos legales, las habilitaciones ni el director técnico que pide `informes.Certificado` (§3.10) — destino: `informes`.
- P-sitio-publico-8 [menor] `Configuracion.obtener()` crea la fila pk=1 en un GET público si falta (la home escribe en la base la primera vez) — destino: `robustez-datos`.
- P-sitio-publico-9 [observación] `404.html` y `500.html` son globales: también se ven en 404 de `/panel/` y `/admin/` (autónomas, sin datos) — destino: `robustez-panel`.
- P-sitio-publico-10 [observación] Las portadas estáticas por servicio (`PORTADA_POR_SLUG` en `apps/web/views.py`) son una asignación provisoria: 5 fotos para 9 servicios; murciélagos y tanques usan la del hero. Las portadas subidas se muestran con `width=1200 height=675` fijos — destino: `empresa`.
- P-sitio-publico-11 [observación] Los cuatro pasos de "Cómo trabajamos" muestran solo el título (la Carta no trae descripción por paso) — destino: `empresa`.

### Decisiones
- 2026-10-07 — El sitio publica 9 páginas de servicio, una por `TipoServicio` del fixture — confirmado por el usuario; aplica la decisión del 2026-10-02 al sitio — reemplaza a: "12 tarjetas numeradas" de `docs/02-diseno.md:77`
- 2026-10-07 — La sección de sectores muestra los 12 de la Carta de Servicios — elección del usuario — reemplaza a: "8 tarjetas" de `docs/02-diseno.md:77`
- 2026-10-07 — El cliente "YPF / Casa Rucery [?]" entra al fixture como "YPF" — elección del usuario — reemplaza a: (nada)
- 2026-10-07 — Las vistas públicas y el panel de contenido van en la ola 2, separados en T4 y T5, en lugar de una ola 1 de tres worktrees — dependen de los modelos de T1 y de `base_web.html` de T2 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `base_web.html` es autónoma y no extiende `base.html` — `base.html` tiene un header fijo fuera de bloque y este plan no la toca — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `sitemap.xml` y `robots.txt` son vistas propias, y las 404 y 500 son plantillas de `apps/web` sin `handler` en `config/urls.py` — evita tocar `config/` y `INSTALLED_APPS` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `faq` queda vacía en el fixture y la sección de preguntas frecuentes no se muestra si está vacía — la Carta no trae preguntas frecuentes y no se inventa contenido — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — Los textos institucionales fijos (cuatro respaldos, tres valores, cuatro pasos) van literales de la Carta en las plantillas; los datos variables, en `Configuracion` — no hay modelo para ellos y §3.12 no los enumera — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `contenido_inicial.json` repite los 9 `TipoServicio` de `tipos_servicio.json`, y un test comprueba que coinciden — `loaddata contenido_inicial` debe funcionar en una base vacía — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — `sectores` es un JSON de valores de `Sector` (12 `TextChoices`) — "M2M a choices" de §3.12 no es implementable — reemplaza a: §3.12 "sectores (M2M a choices)" — decidida por Claude, revisable
- 2026-10-07 — El `[cmd] manage.py loaddata contenido_inicial` del pedido se reemplaza por `test_singleton_y_fixture_carga`, que carga el fixture en la base de test — el verificador no puede migrar ni escribir la base local (`.claude/agents/verificador.md:41`) — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — T2 (diseño) no escribe tests: sus comprobaciones son `[cmd]` y `[grep]`, y `test_diseno.DisenoWebTests` lo escribe T5 — según la tabla de propiedad, `apps/web/tests/` es de la subtarea de la app — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — Los datos legales de la empresa para el certificado no entran en `Configuracion` en este plan; §3.12 lo anota — el sitio no los necesita y su forma depende del certificado actual, que todavía no llegó — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — T1 se parte en T1 (modelos, admin, migración, tests) y T7 (fixture) — T1 excedió su presupuesto (1036/900) y no se sube; aplica la decisión del 2026-10-04 — elección del usuario — reemplaza a: (nada)
- 2026-10-07 — `sectores` del fixture solo lleva lo que la Carta asocia explícitamente (MIPU → gastronómicos y comercios; edificios → torres y condominios) — la Carta no relaciona servicios con sectores; no se inventa contenido — elección del usuario — reemplaza a: (nada)
- 2026-10-07 — El test de recorrido lo escribe T5, no el principal — necesita todas las páginas públicas, que son de T5 — reemplaza a: (nada) — decidida por Claude, revisable

### Cierra
