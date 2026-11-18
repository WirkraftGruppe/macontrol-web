# Plan: portada-video — portada del inicio con video de fondo y video institucional

<!-- Nivel Completo. Rama plan/portada-video, creada desde main 51268a1. Pedido del usuario del
2026-11-18 con diseño aprobado; ajustes del usuario: gthread 8 hilos × 2 workers aplicado antes del
código del video, medición de descargas en producción con script en herramientas/, el <script defer>
solo en inicio.html, la precarga del poster reemplaza a test_hero_con_fetchpriority_alta. -->

- **slug**: `portada-video`
- **fecha**: 2026-11-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): portada-video`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: que la portada del inicio muestre un video en bucle sin sonido detrás del título, con un botón "Ver video · 1 min" que abre el video institucional con sonido, sin que las descargas de video dejen sin respuesta al resto del sitio.
- **fuera de alcance**:
  - Control de sonido sobre el video de fondo; formatos adicionales (WebM, AV1); recodificar los archivos entregados.
  - Almacenamiento externo, CDN o incrustados de terceros; video editable desde el admin.
  - Otras páginas (las de servicio siguen con `hero-pulverizacion-quincho.webp`), `og:image` y toda imagen existente de `static/img/`.
  - `config/csp.py`, `config/settings/**` y las cabeceras de seguridad: la CSP queda idéntica.
  - Modelos y migraciones con datos publicados (`config.presentacion` se recorta en la vista, no en la base); la única migración es `0005_contadoringreso` de T9, sin datos.
  - `.claude/hooks/**`.
- **áreas**: web | infraestructura
- **seguridad**: sí — cambia el arranque de producción (`start` de gunicorn en `.railway/railway.ts`, aplicado con `railway config apply`) y el servido de estáticos pesados, y agrega el primer JavaScript del sitio bajo la CSP; T9 cambia el límite de ingreso al admin y el reprocesado de imágenes subidas. Corre `auditor-seguridad` sobre T1 y sobre el plan entero antes de T7, además de `verificador` y `verificador-b`.

## Contexto mínimo

- Portada actual: `apps/web/templates/web/paginas/inicio.html:3-18`, grilla texto + `<img fetchpriority="high">` (`IMAGENES["hero"]` en `apps/web/views.py:19-26`); CSS en `static/css/web.css:258-263` y `@media (max-width: 900px)` en l.293-318. `templates/web/base_web.html` no tiene bloques de `<head>` ni de scripts; el único `<script>` del sitio es el JSON-LD de `web/paginas/publica.html:17`.
- CSP (`config/settings/base.py:135-147`): sin `media-src`, el `<video>` cae en `default-src 'self'`, el poster en `img-src 'self'` y un `<script src>` propio en `script-src 'self'`. Sin estilos en línea (`test_diseno` rechaza `style=`).
- Estáticos: WhiteNoise 6.12 solo en `prod.py` (`CompressedManifestStaticFilesStorage`); atiende `Range` (206 + `Content-Range`) y no comprime mp4. `runserver` no atiende `Range`. Los tres mp4 tienen `moov` antes de `mdat` (reproducción progresiva).
- Arranque: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60` (`.railway/railway.ts`, `docs/despliegue.md:15`). Con workers síncronos una descarga lenta ocupa un worker entero; con `gthread` ocupa un hilo, y `--timeout` vigila el latido del worker (hilo principal), no la duración de una petición: una descarga de 12,3 MB a 100 KB/s (≈ 123 s) no se corta. `CONN_MAX_AGE` no está definido (0): a lo sumo 2 × 8 = 16 conexiones simultáneas a Postgres.
- Tests que fijan lo actual y T3 adapta: `test_diseno.DisenoWebTests.test_home_carga_web_css_sin_recursos_externos_ni_unsafe_inline` y `test_base_web.BaseWebTests.test_desplegable_lista_los_servicios` (único `<script>` = JSON-LD), `test_diseno.…test_hero_con_fetchpriority_alta` (se reemplaza por la precarga del poster).
- Archivos entregados, sin commitear en la raíz (sha256): `static/video/portada-bucle-480.mp4` `8d991a69…`, `portada-bucle-720.mp4` `dd025ec1…`, `video-institucional-720.mp4` `368cc08f…`, `static/img/portada-poster.webp` `551878e9…` (hashes completos en los criterios de T3).
- Medición en el navegador: Chrome instalado, Playwright 1.64.1 con `channel="chrome"` (decodifica H.264); no hay `ffmpeg`.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (gunicorn gthread), T2 (script de descargas), T3 (portada con video), T4 (integración) | ninguna |
| 2 | T5 (script de medición de la portada), T10 (comportamiento del JS, en el worktree de T5), T9 (contador atómico del login e imágenes seguras entre hilos), T6 (integración y verificación `TODO` previa al despliegue) | web (solo T9: 0005) |
| 3 | T11 (cortar la reserva al primer balde lleno; integración y verificación `TODO` previa por el principal) | ninguna |
| 4 | T7 (aplicar gunicorn, desplegar y medir en producción, principal) | ninguna |
| 5 | T8 (cierre, principal) | ninguna |

## Subtareas

### T1 — Pasar gunicorn a gthread con 8 hilos y 2 workers

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.railway/railway.ts`, `config/tests/test_despliegue.py`, `docs/despliegue.md`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `config/csp.py`, `requirements.txt`, `apps/`, `templates/`, `static/`, `herramientas/`
- **Skill a leer antes**: `.agents/skills/python-performance-optimization/SKILL.md` (solo para el razonamiento de concurrencia; no hay código de rendimiento) y `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**: cambiar solo el `start` a `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --worker-class gthread --threads 8 --timeout 60` (nada más del archivo cambia: `railway config plan` debe mostrar un único cambio). Test nuevo en `RailwayTests` que lea `start:` con el mismo estilo que `test_predeploy_declarado_en_iac` y exija exactamente una línea con esas cinco opciones. En `docs/despliegue.md` § 1 ("Arranque:") el comando nuevo y un párrafo: por qué gthread (descargas lentas de video servidas por WhiteNoise ocupan un hilo y no un worker), qué vigila `--timeout` con gthread, y el máximo de conexiones a Postgres "2 × 8 = 16" con `CONN_MAX_AGE` en 0. La sección Historia no se toca.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue.RailwayTests.test_start_gthread_dos_workers_ocho_hilos --keepdb`
  - `[grep-1]` `grep -nF 'start: "gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --worker-class gthread --threads 8 --timeout 60",' .railway/railway.ts`
  - `[cmd]` `test "$(git diff --numstat 51268a1 -- .railway/railway.ts | cut -f1,2)" = "$(printf '1\t1')"`
  - `[grep-1]` `grep -nF -e '--worker-class gthread --threads 8' docs/despliegue.md`
  - `[grep-1]` `grep -nF '2 × 8 = 16' docs/despliegue.md`
  - `[grep-1]` `grep -nF 'CONN_MAX_AGE' docs/despliegue.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T1`

### T2 — Script de descargas concurrentes limitadas (`herramientas/medir_descargas.py`)

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `herramientas/medir_descargas.py`, `apps/web/tests/test_descargas.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `.railway/`, `apps/web/templates/`, `apps/web/views.py`, `herramientas/sondear.py`, `herramientas/medir_movil.py`, `herramientas/humo_web.py`
- **Skill a leer antes**: `.agents/skills/python-best-practices/SKILL.md` y `.agents/skills/test-driven-development/SKILL.md` § Red-Green-Refactor
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**: script con solo la biblioteca estándar (como `herramientas/sondear.py`, que sirve de modelo de salida y de test). Uso: `medir_descargas.py --pagina URL --video URL [--descargas 4] [--kbps 100] [--limite 2.0] [--cada 2]`. Lanza N descargas simultáneas del video, cada una leyendo a lo sumo `kbps` KB/s; mientras alguna siga activa, pide `--pagina` cada `--cada` segundos. Imprime una línea por pedido de página (`AAAA-MM-DDTHH:MM:SS pagina <código> <ms>`) y una por descarga (`descarga <n> <recibidos>/<Content-Length> <segundos>`), y al final exactamente una línea `PASA …` o `FALLA …`. Sale con 0 solo si: toda descarga recibió exactamente `Content-Length` bytes con 200 o 206, hubo al menos un pedido de página, y todos dieron 200 en menos de `--limite` segundos. Los tests levantan un `ThreadingHTTPServer` local, como `test_sondeo.py`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_descargas.MedirDescargasTests.test_pasa_con_servidor_concurrente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_descargas.MedirDescargasTests.test_falla_si_una_descarga_queda_incompleta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_descargas.MedirDescargasTests.test_falla_si_la_pagina_supera_el_limite --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_descargas.MedirDescargasTests.test_respeta_el_limite_de_velocidad --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_descargas.MedirDescargasTests.test_pide_la_pagina_mientras_hay_descargas --keepdb`
  - `[existe]` `herramientas/medir_descargas.py`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/medir_descargas.py --help`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/medir_descargas.py apps/web/tests/test_descargas.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T2`

### T3 — Portada con video de fondo, velo, pausa y diálogo del video institucional

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `static/video/portada-bucle-480.mp4`, `static/video/portada-bucle-720.mp4`, `static/video/video-institucional-720.mp4`, `static/img/portada-poster.webp` (solo agregarlos, copiados sin recodificar desde `C:/Users/Emanuel/Desktop/WEB/macontrol-web/static/`), `static/js/portada.js`, `static/css/web.css`, `templates/web/base_web.html`, `apps/web/templates/web/paginas/inicio.html`, `apps/web/views.py`, `apps/web/tests/test_portada_video.py`, `apps/web/tests/test_diseno.py`, `apps/web/tests/test_base_web.py`, `docs/02-diseno.md` (es la subtarea "diseño" de la tabla de propiedad)
- **No puede tocar**: `docs/planes/`, `config/`, `.railway/`, `herramientas/`, `apps/web/models.py`, `apps/web/migrations/`, `apps/web/templates/web/paginas/publica.html`, toda imagen existente de `static/img/`, `docs/despliegue.md`
- **Skill a leer antes**: `.agents/skills/web-design-guidelines/SKILL.md`, `.agents/skills/frontend-design/SKILL.md` § Frontend Aesthetics Guidelines, `.agents/skills/django-security/SKILL.md` § Template Escaping
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 450 líneas agregadas
- **Qué hacer**:
  - `base_web.html`: dos bloques vacíos nuevos, `{% block precargas %}` en `<head>` y `{% block scripts %}` antes de `</body>`. `inicio.html` los llena: `<link rel="preload" as="image" href="{% static 'img/portada-poster.webp' %}" fetchpriority="high">` y `<script src="{% static 'js/portada.js' %}" defer></script>`. Ninguna otra página carga el JS.
  - Portada a todo el ancho (`<section class="hero" id="hero">` se conserva, y también el orden de secciones): `<video muted loop playsinline autoplay poster="…portada-poster.webp" aria-hidden="true">` con `<source media="(max-width: 900px)">` de 480 y luego `<source>` de 720, los dos `type="video/mp4"`; velo con degradado de izquierda a derecha y, en ≤ 900 px, de arriba hacia abajo con el texto abajo. Contraste AA de título, párrafo y botones en todo el bucle.
  - Párrafo: solo la primera oración de `config.presentacion`, recortada en la vista con una función con nombre (el texto completo sigue en `/empresa/`).
  - Botón "Ver video · 1 min" junto a "Llamar ahora": sin JS es `<a href="{% static 'video/video-institucional-720.mp4' %}">`; el JS lo intercepta y abre un `<dialog>` con `<video controls preload="none" src="…video-institucional-720.mp4">` y un botón de cerrar; al cerrar (botón, Escape o fondo) pausa el institucional. Botón de pausa del fondo (`type="button"`, `aria-label`, `aria-pressed="false"`), con `hidden` en el HTML; el JS lo muestra y alterna `aria-pressed` y el `aria-label`.
  - JS (`static/js/portada.js`): sin dependencias. Con `prefers-reduced-motion: reduce` pausa el fondo y lo vuelve al poster. Lo pausa cuando la portada sale del viewport (`IntersectionObserver`) y mientras el diálogo está abierto, y lo reanuda después salvo que el usuario lo haya pausado. Objetivos táctiles de 44×44 px como mínimo. Sin estilos en línea ni manejadores en atributos.
  - Tests: los nuevos de abajo; adaptar los dos tests de scripts existentes (único `src` = `/static/js/portada.js` en `/`, ningún script en línea salvo el JSON-LD) y borrar `test_hero_con_fetchpriority_alta` (lo reemplaza `test_poster_precargado_con_prioridad_alta`). `docs/02-diseno.md`: componente "Portada con video" (velo, móvil, pausa, diálogo, movimiento reducido) y la línea "Home:" de Estructura; la tabla de Recursos suma el poster y los videos.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_video_de_fondo_con_atributos_y_fuentes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_poster_precargado_con_prioridad_alta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_inicio_un_unico_script_externo_y_ninguno_en_linea --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_otras_paginas_no_cargan_el_script --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_enlace_de_respaldo_al_video_institucional --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_video_institucional_solo_con_preload_none --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_dialogo_con_boton_de_cerrar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_boton_de_pausa_con_aria --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_parrafo_de_portada_es_la_primera_oracion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_javascript_servido_desde_estaticos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.EstaticosVideoTests.test_videos_responden_206_con_range --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno apps.web.tests.test_base_web apps.web.tests.test_paginas --keepdb`
  - `[cmd]` `test "$(git show HEAD:static/video/portada-bucle-480.mp4 | sha256sum | cut -d' ' -f1)" = 8d991a690ef04ac651d062f82b313b02f9fde1ce135d6ad4d69914649ad1372f`
  - `[cmd]` `test "$(git show HEAD:static/video/portada-bucle-720.mp4 | sha256sum | cut -d' ' -f1)" = dd025ec1747af4787552e84ac79d8d55b8d2b81e502d6e17fe1de9c3b81c6c01`
  - `[cmd]` `test "$(git show HEAD:static/video/video-institucional-720.mp4 | sha256sum | cut -d' ' -f1)" = 368cc08fd0e3d6bce4bccc30d79e9b28af391a59203169bddabd2e0c022cddb6`
  - `[cmd]` `test "$(git show HEAD:static/img/portada-poster.webp | sha256sum | cut -d' ' -f1)" = 551878e9002991e9b311ef1a34b95ee7b492e9b10295f92845a59a2bd916558b`
  - `[existe]` `static/js/portada.js`
  - `[grep-0]` `grep -nE 'innerHTML|eval\(|new Function|document\.write|setAttribute\(.style' static/js/portada.js`
  - `[grep-0]` `grep -nE '<script>|<script [^>]*>[^<]|\son[a-z]+=|style=' apps/web/templates/web/paginas/inicio.html templates/web/base_web.html`
  - `[cmd]` `git diff --exit-code 51268a1 -- config/csp.py config/settings/ apps/web/templates/web/paginas/publica.html`
  - `[cmd]` `test -z "$(git diff --name-only --diff-filter=DMR 51268a1 -- static/img/)"`
  - `[grep-1]` `grep -nF 'portada-poster.webp' docs/02-diseno.md`
  - `[grep-1]` `grep -niE 'prefers-reduced-motion|movimiento reducido' docs/02-diseno.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 450 --subtarea T3`

### T4 — Integración de la ola 1 (principal)

- **Ola**: 1 (después de verificar T1, T2 y T3)
- **Depende de**: T1, T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/portada-video` de cada subtarea, no los informes.
  2. Antes de integrar T3: comprobar que los cuatro archivos sin commitear de la raíz tienen los sha256 de T3 y moverlos a `~/respaldos/macontrol-web/portada-video-originales/` (si quedan en la raíz, el merge falla con "untracked working tree files would be overwritten").
  3. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh portada-video T<n> plan/portada-video <ruta>...` para T1, T2 y T3 con las rutas de su `Puede tocar`.
  4. Crear el worktree de T5: `bash .claude/hooks/worktree-crear.sh portada-video T5 plan/portada-video`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T1: integra portada-video-T1"`
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T2: integra portada-video-T2"`
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T3: integra portada-video-T3"`
  - `[cmd]` `test -z "$(git status --porcelain -- static/video static/img)"`

### T5 — Script de medición de la portada (`herramientas/medir_portada.py`)

- **Ola**: 2
- **Depende de**: T4
- **Puede tocar**: `herramientas/medir_portada.py`, `apps/web/tests/test_medir_portada.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `.railway/`, `apps/web/templates/`, `apps/web/views.py`, `herramientas/humo_web.py`, `herramientas/medir_movil.py`, `herramientas/medir_descargas.py`, `herramientas/sondear.py`
- **Skill a leer antes**: `.agents/skills/python-best-practices/SKILL.md`, `.agents/skills/web-design-guidelines/SKILL.md` (contraste y objetivos táctiles)
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**: script con Playwright (`channel="chrome"`, `bypass_csp=True` solo para ocultar texto durante la medición). Sin `--url`, arranca la base temporal y `loaddata contenido_inicial` reutilizando `humo_web` (como `medir_movil.py`), y sirve con un servidor WSGI con hilos de la biblioteca estándar que envuelve la aplicación Django en `whitenoise.WhiteNoise(…, root=static/, prefix="static/")`, para que el video admita `Range` y búsquedas. Con `--url` mide ese sitio. Comprueba e imprime una línea por medición y al final `PASA …` o `FALLA …` (exit 0 solo con todo en PASA):
  - Contraste: en 1280×800 y en 375×812, con el fondo pausado en los segundos 0, 3 y 7, contraste ≥ 4,5:1 del color calculado de `h1`, del párrafo y de cada botón de la portada contra el píxel de mayor luminancia bajo su caja, con el texto oculto.
  - En 375×812, los dos botones ("Llamar ahora", "Ver video") con su borde inferior ≤ 812 sin desplazarse.
  - Botones de la portada y de pausa de al menos 44×44 px (el de cerrar el diálogo lo mide T10).
  - Comportamiento del JS y página sin JavaScript: pasan a T10 (contrato modificado por presupuesto).
  - Las funciones puras (luminancia relativa, contraste, evaluación de una medición) se testean sin navegador.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada.MedirPortadaTests.test_contraste_blanco_sobre_negro_es_21 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada.MedirPortadaTests.test_contraste_menor_a_4_5_es_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada.MedirPortadaTests.test_objetivo_tactil_menor_a_44_es_falla --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_movil.py`   (el desborde horizontal de `/` en 375×812 lo mide la herramienta existente)
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/medir_portada.py apps/web/tests/test_medir_portada.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T5`

### T10 — Medición del comportamiento del JS de la portada (`herramientas/medir_portada_js.py`)

<!-- Agregada por contrato modificado (decisión del usuario, 2026-11-18): T5 agregó 422 líneas
contra 350; el presupuesto no se sube y lo que no entra va acá. -->

- **Ola**: 2
- **Depende de**: T5
- **Puede tocar**: `herramientas/medir_portada_js.py`, `herramientas/medir_portada.py` (solo para importar y llamar a la medición nueva), `apps/web/tests/test_medir_portada_js.py`
- **No puede tocar**: lo mismo que T5
- **Skill a leer antes**: lo mismo que T5
- **Worktree**: el de T5 (rama `portada-video-T5`), en commits `T10:` posteriores a los `T5:`; se integra junto con T5
- **Ruta**: delegada
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**: en `herramientas/medir_portada_js.py`, con el mismo navegador y la misma URL que `medir_portada.py`, y con el mismo formato de líneas: el fondo se reproduce; con `reduced_motion="reduce"` queda pausado; se pausa al desplazar la portada fuera del viewport y al abrir el diálogo; al cerrarlo, el institucional queda pausado; el botón de pausa alterna `aria-pressed`; el botón de cerrar del diálogo mide al menos 44×44 px. Sin JavaScript (`java_script_enabled=False`), "Ver video" es un enlace al mp4 y el título y "Llamar ahora" se ven. `medir_portada.py` la llama y suma sus resultados al `PASA`/`FALLA` final. La evaluación de las observaciones es una función pura testeada sin navegador.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada_js.MedirPortadaJsTests.test_falla_si_el_fondo_no_se_pausa_con_el_dialogo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada_js.MedirPortadaJsTests.test_falla_si_sin_js_ver_video_no_es_enlace_al_mp4 --keepdb`
  - `[existe]` `herramientas/medir_portada_js.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -q 'movimiento reducido'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/medir_portada_js.py herramientas/medir_portada.py apps/web/tests/test_medir_portada_js.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 --subtarea T10`

### T9 — Contador atómico del límite de ingreso al admin e imágenes seguras entre hilos

<!-- Agregada por contrato modificado (decisión del usuario, 2026-11-18) tras la auditoría de T1:
con gthread hay 16 peticiones simultáneas por réplica y dos defectos dejan de estar acotados. -->

- **Ola**: 2
- **Depende de**: T4
- **Puede tocar**: `config/limites.py`, `apps/web/models.py`, `apps/web/migrations/0005_contadoringreso.py`, `apps/web/imagenes.py`, `config/tests/test_limites.py`, `config/tests/test_limites_admin.py`, `config/tests/test_limites_atomicos.py`, `apps/web/tests/test_imagenes_hilos.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `config/csp.py`, `config/admin.py`, `.railway/`, `templates/`, `static/`, `herramientas/`, `apps/web/views.py`, `apps/web/admin.py`, `apps/web/templates/`, toda migración existente
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md`, `.agents/skills/django-conventions/SKILL.md` § Models, `.agents/skills/test-driven-development/SKILL.md` § Red-Green-Refactor
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - Límite de ingreso (`config/limites.py`): hoy chequea el contador antes del hash de la contraseña y suma el fallo después con `cache.incr` (get + set): con peticiones simultáneas todas pasan el chequeo y se pierden sumas. Reemplazar los baldes en caché por un modelo nuevo `ContadorIngreso` (`clave` CharField primaria, `cuenta` PositiveIntegerField, `vence` DateTimeField con índice; sin admin) en `apps/web/models.py`, migración `0005_contadoringreso` sin datos. Cada POST **reserva** el intento antes de evaluar la contraseña: por cada balde (las mismas tres claves y ventanas fijas de hoy), `get_or_create` de la fila de la ventana en curso y `filter(...).update(cuenta=F("cuenta") + 1)`; si algún balde queda por encima de su máximo, 429 sin evaluar la contraseña (sigue sin ser oráculo). Ingreso correcto: borra el balde (usuario, IP) y devuelve la reserva de los baldes por IP y por usuario (`F("cuenta") - 1`, sin bajar de 0), así siguen contando solo los fallos. Las filas vencidas se borran al reservar. El docstring del módulo describe el mecanismo nuevo (sin "atómico entre procesos" para la caché).
  - Imágenes (`apps/web/imagenes.py`): quitar `warnings.catch_warnings`/`simplefilter` (estado global del proceso, no seguro entre hilos) y rechazar con el mismo `ValidationError` cuando `ancho × alto > Image.MAX_IMAGE_PIXELS`, leído de la cabecera antes de `load()`.
  - Los tests existentes de límites que dependan de la caché se adaptan sin perder lo que comprueban.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_atomicos.ReservaIntentoTests.test_intento_se_reserva_antes_de_evaluar_la_contrasena --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_atomicos.ReservaIntentoTests.test_reservas_pendientes_cuentan_para_el_cupo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_atomicos.ReservaIntentoTests.test_suma_es_un_unico_update_con_expresion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_atomicos.ReservaIntentoTests.test_ingreso_correcto_no_consume_cupo_de_ip_ni_de_usuario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_atomicos.ReservaIntentoTests.test_ventana_vencida_reinicia_la_cuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_imagenes_hilos.PixelesTests.test_rechaza_exceso_de_pixeles_sin_depender_de_los_filtros_de_avisos --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites config.tests.test_limites_admin apps.web --keepdb`
  - `[existe]` `apps/web/migrations/0005_contadoringreso.py`
  - `[grep-0]` `grep -nE 'cache\.(incr|add|get)' config/limites.py`
  - `[grep-0]` `grep -nE 'catch_warnings|simplefilter' apps/web/imagenes.py`
  - `[grep-1]` `grep -nF 'F("cuenta")' config/limites.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check config/limites.py apps/web/models.py apps/web/imagenes.py config/tests apps/web/tests apps/web/migrations/0005_contadoringreso.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T9`

### T6 — Integración de la ola 2 (principal)

- **Ola**: 2 (después de verificar T5, T10 y T9)
- **Depende de**: T5, T10, T9
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/portada-video`, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh portada-video T5 plan/portada-video herramientas/medir_portada.py herramientas/medir_portada_js.py apps/web/tests/test_medir_portada.py apps/web/tests/test_medir_portada_js.py` (lleva T5 y T10) y `bash .claude/hooks/worktree-integrar.sh portada-video T9 plan/portada-video <rutas de su Puede tocar>`.
  3. Con todo integrado: cierre global, `verificador` y `verificador-b` sobre `TODO` (salvo T7 y T8) y `auditor-seguridad` sobre el plan entero (incluido T9: autenticación del admin e imágenes), antes de T7.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T5: integra portada-video-T5"`
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T9: integra portada-video-T9"`
  - `[cmd]` `git diff --exit-code 51268a1 -- config/csp.py config/settings/`

### T11 — Cortar la reserva al primer balde lleno (auditoría previa al despliegue)

<!-- Agregada por contrato modificado (decisión del usuario, 2026-11-18): la auditoría del plan entero
confirmó que con T9 los intentos rechazados con 429 suman en el balde global por usuario y una sola IP
bloquea al superusuario desde cualquier IP (H1), y que la tabla crece sin tope bajo ataque (H2). -->

- **Ola**: 3
- **Depende de**: T6
- **Puede tocar**: `config/limites.py`, `config/tests/test_limites_atomicos.py`, `config/tests/test_limites_corte.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `config/csp.py`, `config/admin.py`, `apps/`, `.railway/`, `templates/`, `static/`, `herramientas/`, toda migración
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md`, `.agents/skills/test-driven-development/SKILL.md` § Red-Green-Refactor
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**: en `reservar_intento`, reservar los baldes en orden (IP, usuario e IP, usuario) y, en cuanto uno queda por encima de su máximo, devolver lo reservado en esta llamada (`F("cuenta") - 1` con `cuenta__gt=0`) y cortar sin tocar los baldes siguientes: cuentan solo los intentos que se evalúan, como antes de T9, y una IP bloqueada no crea filas de usuario. `devolver_reserva` usa el mismo instante que la reserva (guardado en el `request`), no un `time.time()` nuevo. Actualizar el comentario que dice que se suman todos los baldes.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_corte.CorteDeReservaTests.test_una_ip_bloqueada_no_bloquea_al_usuario_desde_otra_ip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_corte.CorteDeReservaTests.test_ip_bloqueada_no_crea_filas_de_usuario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites_corte.CorteDeReservaTests.test_devolucion_usa_la_ventana_de_la_reserva --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests apps.web --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check config/limites.py config/tests`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 --subtarea T11`

### T7 — Aplicar gunicorn, desplegar el video y medir en producción (principal)

- **Ola**: 4
- **Depende de**: T6, T11 (integrada con `worktree-integrar.sh`) y la verificación `TODO` previa en PASA
- **Pasos** (⚠ = autorización explícita del usuario con la salida a la vista; ninguno se encadena con el siguiente sin ella):
  1. `railway status` → `macontrol-web`.
  2. `curl -sSI https://www.macontrol.com.ar/ > docs/evidencia/2026-11-18-portada-video/cabeceras-antes.txt` (CSP de `main` en producción).
  3. Sondeo del apply, en segundo plano y justo antes del paso 4: `./venv/Scripts/python.exe herramientas/sondear.py https://www.macontrol.com.ar/ --cada 5 --durante 900 > docs/evidencia/2026-11-18-portada-video/sondeo-apply.txt`.
  4. `railway config plan`: un único cambio (`startCommand` del servicio `web`), 0 a destruir; cualquier otra cosa, parar y consultar → ⚠ `railway config apply`. Esperar SUCCESS del despliegue (código de `main`, sin el video) y guardar `railway logs --deployment <id> --lines 300` en `docs/evidencia/2026-11-18-portada-video/arranque-gthread.log` (revisar que no tenga secretos).
  5. ⚠ El usuario decide el merge de `plan/portada-video` en `main` y el push. Justo antes del push, sondeo en segundo plano a `docs/evidencia/2026-11-18-portada-video/sondeo.txt` (mismo comando). Seguir el despliegue hasta SUCCESS.
  6. Medir: `./venv/Scripts/python.exe herramientas/medir_descargas.py --pagina https://www.macontrol.com.ar/ --video https://www.macontrol.com.ar/static/video/video-institucional-720.mp4 --descargas 4 --kbps 100 --limite 2.0 > docs/evidencia/2026-11-18-portada-video/descargas.txt` y `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py --url https://www.macontrol.com.ar/ > docs/evidencia/2026-11-18-portada-video/portada.txt`.
  7. Correr los criterios; commit `T7: evidencia del despliegue de la portada con video`.
- **Presupuesto**: 1500 líneas agregadas (evidencia generada: cabeceras, sondeos, log y mediciones)
- **Criterios**:
  - `[grep-1]` `grep -nF 'Using worker: gthread' docs/evidencia/2026-11-18-portada-video/arranque-gthread.log`
  - `[cmd]` `railway config plan --detailed-exit-code`
  - `[grep-0]` `grep -nE '^[^ ]+ 5[0-9]{2} ' docs/evidencia/2026-11-18-portada-video/sondeo-apply.txt`
  - `[grep-0]` `grep -nE '^[^ ]+ 5[0-9]{2} ' docs/evidencia/2026-11-18-portada-video/sondeo.txt`
  - `[cmd]` `test "$(grep -cE '^[^ ]+ 200 [0-9]+$' docs/evidencia/2026-11-18-portada-video/sondeo.txt)" -ge 60`
  - `[cmd]` `test "$(tail -n 1 docs/evidencia/2026-11-18-portada-video/descargas.txt | cut -d' ' -f1)" = PASA`
  - `[cmd]` `test "$(grep -cE '^descarga [0-9]+ ([0-9]+)/\1 ' docs/evidencia/2026-11-18-portada-video/descargas.txt)" -eq 4`
  - `[grep-0]` `grep -nE ' pagina ([^2]|2[^0]|20[^0])' docs/evidencia/2026-11-18-portada-video/descargas.txt`
  - `[cmd]` `test "$(tail -n 1 docs/evidencia/2026-11-18-portada-video/portada.txt | cut -d' ' -f1)" = PASA`
  - `[cmd]` `for v in portada-bucle-480 portada-bucle-720 video-institucional-720; do h="$(curl -sS -o /dev/null -D - -H 'Range: bytes=0-1023' "https://www.macontrol.com.ar/static/video/$v.mp4" | tr -d '\r')"; echo "$h" | head -n 1 | grep -q ' 206' && echo "$h" | grep -qi '^content-range: bytes 0-1023/' || exit 1; done`
  - `[cmd]` `test "$(grep -i '^content-security-policy:' docs/evidencia/2026-11-18-portada-video/cabeceras-antes.txt | tr -d '\r')" = "$(curl -sSI https://www.macontrol.com.ar/ | grep -i '^content-security-policy:' | tr -d '\r')"`
  - `[cmd]` `git log --oneline plan/portada-video | grep -q "T11: integra portada-video-T11"`
  - `[cmd]` `curl -fsS https://www.macontrol.com.ar/ | grep -q 'portada-bucle-720'`
  - `[cmd]` `MSYS_NO_PATHCONV=1 railway ssh -s web -- sh -c 'cd /app && /app/.venv/bin/python manage.py showmigrations web' 2>&1 | grep -q "\[X\] 0005_contadoringreso"`
  - `[cmd]` `for p in / /empresa/ /contacto/ /servicio/control-murcielagos/ /favicon.ico /admin/login/; do test "$(curl -sS -o /dev/null -w '%{http_code}' "https://www.macontrol.com.ar$p")" = 200 || exit 1; done`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T7`

### T8 — Cierre (principal)

- **Ola**: 5
- **Depende de**: T7
- **Pasos**: bitácora ("Estado actual" y entrada), decisiones del plan copiadas a `docs/decisiones.md`, `### Cierra` y pendientes nuevos; commits `T8:` en `plan/portada-video` y merge en `main` con autorización del usuario.
- **Presupuesto**: 120 líneas agregadas
- **Criterios**:
  - `[grep-1]` `grep -nF 'gthread' docs/decisiones.md`
  - `[grep-1]` `grep -nF 'portada-video' docs/bitacora.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T8`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-11-18-portada-video.md portada-video`

## Registro de verificación

commit_base: f8d5cf1

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |
| T7 | hecha |
| T8 | pendiente |
| T9 | hecha |
| T10 | hecha |
| T11 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-11-18 | T1 (verificador) | 829b416 | PASA 8/8 | contrato intacto |
| 2026-11-18 | T2 (verificador) | 80eb487 | PASA 9/9 | obs.: `medir_descargas.py:75` silencia errores de red (la descarga igual queda incompleta → FALLA) |
| 2026-11-18 | T1, T2 (verificador-b) | 829b416, 80eb487 | PASA 17/17 | — |
| 2026-11-18 | T3 (verificador) | c363e4b | PASA 25/25 | — |
| 2026-11-18 | T3 (verificador-b) | c363e4b | PASA 25/25 | — |
| 2026-11-18 | T1 (auditor-seguridad) | 829b416 | sin bloqueantes; 1 importante, 1 menor | límite de login no atómico (agravado ×8 por gthread) y `catch_warnings` no seguro entre hilos → T9 por decisión del usuario |
| 2026-11-18 | T4 (integración) | 4c94f03 | 207 tests OK en cada `worktree-integrar.sh` | originales movidos a `~/respaldos/macontrol-web/portada-video-originales/` tras comparar sha256 |
| 2026-11-18 | T9 (verificador, verificador-b) | d867c82 | 14/14 criterios PASA; veredicto FALLA solo por contrato modificado (4bb14f4, decisión del usuario) | alcance: 8 archivos, todos en su Puede tocar |
| 2026-11-18 | T5, T10 (verificador, verificador-b) | 5bce088 | 14/14 criterios PASA; veredicto FALLA solo por contrato modificado (4bb14f4, 130340a, decisiones del usuario) | `medir_portada.py`: PASA 58 mediciones; contraste mínimo 8,08:1 |
| 2026-11-18 | T6 (integración) | 86869bb | 214 y 220 tests OK en `worktree-integrar.sh`; criterios de T6 en PASA | T5 lleva los commits de T10 |
| 2026-11-18 | TODO previo al despliegue (verificador) | f60db7e | 82/83 PASA; única FALLA `congelado.sh` por contrato modificado (4bb14f4, 130340a) | 220 tests OK |
| 2026-11-18 | plan entero (auditor-seguridad) | f60db7e | sin bloqueantes; H1 importante confirmado, H2 menor, H3 obs., H4 menor | H1–H3 → T11 por decisión del usuario; H4 queda como pendiente |
| 2026-11-18 | T11 (verificador, verificador-b) | 51fa853 | 6/6 criterios PASA; veredicto FALLA solo por contrato modificado (4bb14f4, 130340a, 77e9697) | rojo previo de los 3 tests confirmado por el implementador; integrada con 223 tests OK |
| 2026-11-18 | TODO previo al despliegue, 2.ª (verificador) | 37a988d | 88/89 PASA; única FALLA `congelado.sh` (4bb14f4, 130340a, 77e9697) | 223 tests OK; PASA 58 mediciones |
| 2026-11-18 | TODO previo al despliegue, 2.ª (verificador-b) | 37a988d | 117/118 PASA; única FALLA `congelado.sh` | la 1.ª corrida de verificador-b (f60db7e→37a988d) se descarta: el HEAD cambió durante la corrida |
| 2026-11-18 | T11 (auditor-seguridad) | 37a988d | H1, H2, H3 cerrados; sin hallazgos nuevos ni bloqueantes | H1 reproducido de nuevo: 302 desde otra IP. Pide en T7: `check --deploy` y `IP_CLIENTE_CABECERA` en Railway |
| 2026-11-18 | T7 (principal, en producción) | 73258b9 | todos los criterios PASA | apply 0164a368 (gthread), merge f8ff6c9 → d9113f24; `showmigrations` de la 0005 lo corrió el usuario (`railway ssh` bloqueado por permisos): `[X] 0005_contadoringreso` |

### Decisiones del plan

- T1 — concurrencia de gunicorn — sync con más workers / gthread / gevent — `gthread`, 2 workers × 8 hilos, `--timeout 60` — decisión del usuario: sin dependencias nuevas y una descarga lenta ocupa un hilo, no un worker — de usuario — revertir el `start` y `railway config apply`
- T2/T7 — dónde se mide la concurrencia — local / producción / ambos — producción, con `herramientas/medir_descargas.py` y evidencia en `docs/evidencia/` — decisión del usuario: gunicorn no corre en Windows — de usuario — no aplica
- T3 — `autoplay` y movimiento reducido — sin `autoplay` y arranque por JS / `autoplay` y pausa por JS — `autoplay` (lo pide el alcance) y el JS pausa y vuelve al poster con `reduce`; sin JS no hay pausa — autónoma — quitar `autoplay` y arrancar desde el JS — decidida por Claude, revisable
- T3 — prueba del 206 sin producción — test con `whitenoise.WhiteNoise` en el mismo proceso / solo producción — los dos (test en T3, `curl` en T7) — autónoma — no aplica — decidida por Claude, revisable
- T3 — fuente según viewport — `<source media>` / elegir por JS — `<source media="(max-width: 900px)">`, sin JS — autónoma — elegir la fuente desde `portada.js` — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-portada-video-1 [menor] Ningún código usa ya la caché `cache_sitio` para el login: los contadores pasaron a `ContadorIngreso` (T9). Pero `config/settings/prod.py:81-82` dice que "los contadores del login del admin viven acá", y `docs/despliegue.md:14` y el `createcachetable` de `.railway/railway.ts` siguen asumiendo la caché. Corregir el comentario y decidir si se retiran `CACHES` y `createcachetable`; esto último toca el `preDeploy` (auditor-seguridad, H4).
- P-portada-video-2 [observación] `herramientas/medir_descargas.py:75` silencia los errores de red de una descarga. En la 1.ª corrida en producción (`docs/evidencia/2026-11-18-portada-video/descargas-1.txt`) una descarga se cortó a los 26 s con 2,6 MB y no quedó registrado por qué; la 2.ª corrida pasó completa. Imprimir la excepción.
- P-portada-video-3 [observación] Dos fallas aisladas en producción, sin rastro en los logs de gunicorn ni reinicio de workers: un `000` del sondeo a las 17:29:16 (`sondeo.txt`), mientras `medir_descargas.py` recibía 200 en menos de 1,7 s, y la descarga cortada de P-portada-video-2. Vigilar si se repiten.
- P-portada-video-4 [observación] Con gthread, después del primer byte el socket queda bloqueante y sin tiempo límite (`gunicorn/workers/gthread.py:492`); `--timeout` no lo corta. 16 conexiones lentas ocupan todos los hilos de la réplica hasta que corte el borde de Railway (≈15 min, no verificado). `docs/despliegue.md:16` debería aclarar que "no se corta" también vale para un cliente malicioso (auditor-seguridad, T1).
- P-portada-video-5 [observación] El balde global por usuario se llena desde 10 grupos de IP (antes de T9/T11: 3), y con IPv6 agrupado por /64 un /56 da 256 grupos. Las filas de `ContadorIngreso` solo se limpian al reservar. La atomicidad de la reserva en Postgres se comprobó razonando, no con tráfico real: probar con N≥10 POST simultáneos sobre un balde en máximo − 1 (auditor-seguridad, T11).
- P-portada-video-6 [observación] `primera_oracion` (`apps/web/views.py`) corta en `.`, `!` o `?` seguido de mayúscula: si el cliente edita `presentacion` con "S.A. Somos…", la portada muestra solo hasta "S.A." (T3).
- P-portada-video-7 [observación] `devolver_reserva` depende de `request._ahora_limites`, un atributo privado que pone `reservar_intento` en el `request`. Ese acoplamiento no se ve en el código y solo lo cubre el flujo del mixin del login (T11).

### Decisiones

- 2026-11-18 — gunicorn pasa a `--worker-class gthread --threads 8` con 2 workers y `--timeout 60`, aplicado con `railway config apply` antes del código del video; como `CONN_MAX_AGE` vale 0, hay como máximo 2 × 8 = 16 conexiones a Postgres — con workers síncronos, una descarga lenta de video servida por WhiteNoise ocupaba un worker entero — decisión del usuario — reemplaza a: (nada)
- 2026-11-18 — La concurrencia con descargas de video se mide en producción con `herramientas/medir_descargas.py` (4 descargas a 100 KB/s, `/` en 200 por debajo de 2 s, descargas completas) — gunicorn no corre en Windows — decisión del usuario — reemplaza a: (nada)
- 2026-11-18 — La portada del inicio es un video de fondo con poster precargado con `fetchpriority="high"`, y `static/js/portada.js` se carga solo en `inicio.html` (bloques `precargas` y `scripts` de `base_web.html`); la CSP no cambia — decisión del usuario — reemplaza a: (nada)
- 2026-11-18 — El límite de ingreso al admin deja la caché por `ContadorIngreso` en Postgres: reserva atómica antes de evaluar la contraseña y corte en el primer balde lleno (T9 y T11, migración 0005) — con gthread la caché perdía sumas y una sola IP podía bloquear al superusuario — decisión del usuario tras dos auditorías — reemplaza a: (nada)
- 2026-11-18 — T5 se partió en T5 y T10 por exceder el presupuesto (422 de 350 líneas) en lugar de subirlo — CLAUDE.md § 4 — decisión del usuario — reemplaza a: (nada)

### Cierra

- cierra: P-puesta-en-produccion-3 — T9 y T11: `ContadorIngreso` con `F("cuenta") + 1`, el intento se reserva antes del hash y el docstring de `config/limites.py` describe el mecanismo nuevo.
- cierra: P-puesta-en-produccion-8 — los contadores del login ya no viven en `DatabaseCache`, así que el cull de la caché no puede reiniciarlos.
