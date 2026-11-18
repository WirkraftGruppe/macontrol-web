# Plan: texto-boton-video — el botón del video institucional dice "Video"

<!-- Nivel Chico (4 archivos, sin juez-plan). Rama plan/texto-boton-video, creada desde main 436e3dc.
Pedido del usuario del 2026-11-18: cambiar "Ver video · 1 min" por "Video". -->

- **slug**: `texto-boton-video`
- **fecha**: 2026-11-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): texto-boton-video`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: que el botón de la portada que abre el video institucional diga "Video" en lugar de "Ver video · 1 min".
- **fuera de alcance**: el comportamiento del botón, del diálogo y del JS; `id="ver-video"`; estilos; otras páginas; la CSP; los videos; los planes anteriores y su evidencia.
- **áreas**: web
- **seguridad**: no — solo cambia un texto visible y la herramienta que lo mide.

## Contexto mínimo

- El texto está en `apps/web/templates/web/paginas/inicio.html:18` (`<a … id="ver-video" …>Ver video · 1 min</a>`).
- `herramientas/medir_portada.py:202` elige por el texto visible qué botones miden el borde inferior en 375×812 (`"Ver video · 1 min"`): si cambia solo la plantilla, esa medición deja de aplicarse al botón sin avisar. El selector de la línea 34 (`#hero #ver-video`) no cambia.
- `apps/web/tests/test_portada_video.py:114` afirma el texto viejo; `docs/02-diseno.md:68` lo cita.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (texto del botón), T2 (integración y verificación) | ninguna |

## Subtareas

### T1 — Cambiar el texto del botón a "Video"

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/web/templates/web/paginas/inicio.html`, `apps/web/tests/test_portada_video.py`, `herramientas/medir_portada.py`, `docs/02-diseno.md`
- **No puede tocar**: `docs/planes/`, `config/`, `static/`, `templates/`, `.railway/`, `apps/web/views.py`, `herramientas/medir_portada_js.py`, `apps/web/tests/test_medir_portada_js.py`, `docs/evidencia/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 60 líneas agregadas
- **Qué hacer**: el enlace `#ver-video` de `inicio.html` dice exactamente `Video` (sin cambiar `id`, `class` ni `href`). Test nuevo que exija ese texto exacto en el enlace al video institucional, y el `assertIn` viejo de `test_enlace_de_respaldo_al_video_institucional` pasa al texto nuevo. En `medir_portada.py`, la condición del borde inferior en móvil deja de depender del texto viejo, de modo que el botón del video se siga midiendo (las líneas de salida pueden llamarlo "Video"). `docs/02-diseno.md` cita el texto nuevo.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_portada_video.PortadaVideoTests.test_boton_del_video_institucional_dice_video --keepdb`
  - `[grep-1]` `grep -nE 'id="ver-video"[^>]*>Video</a>' apps/web/templates/web/paginas/inicio.html`
  - `[grep-0]` `grep -rnF 'Ver video · 1 min' apps/ herramientas/ static/ templates/ docs/02-diseno.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA borde inferior móvil Video'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/medir_portada.py apps/web/tests/test_portada_video.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T1`

### T2 — Integración (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/texto-boton-video`, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh texto-boton-video T1 plan/texto-boton-video apps/web/templates/web/paginas/inicio.html apps/web/tests/test_portada_video.py herramientas/medir_portada.py docs/02-diseno.md`.
  3. Cierre global y verificación `TODO`; bitácora al cierre. El merge en `main` y el push (que despliega) los decide el usuario.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/texto-boton-video | grep -q "T1: integra texto-boton-video-T1"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-11-18-texto-boton-video.md texto-boton-video`

## Registro de verificación

commit_base: <hash del commit docs(plan): texto-boton-video>

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|

### Decisiones del plan

## Pendientes que deja este plan

### Problemas

### Decisiones

- 2026-11-18 — El botón de la portada que abre el video institucional dice "Video" — decisión del usuario — reemplaza a: 2026-11-18 (el texto "Ver video · 1 min" del pedido de `portada-video`)

### Cierra
