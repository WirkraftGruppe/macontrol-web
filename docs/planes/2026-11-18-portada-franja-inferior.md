# Plan: portada-franja-inferior — en escritorio, el texto de la portada va en una franja inferior

<!-- Nivel Chico (4 archivos, sin juez-plan). Rama plan/portada-franja-inferior, creada desde main 54475f9.
Pedido del usuario del 2026-11-18: que el texto y los botones de la portada no tapen al operario de la toma final del bucle. -->

- **slug**: `portada-franja-inferior`
- **fecha**: 2026-11-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): portada-franja-inferior`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: en viewports de más de 900 px, `.hero-texto` y `.hero-botones` quedan en una franja al pie de `.hero` (texto a la izquierda, botones a la derecha alineados con la base del texto) y `.hero-velo` es un degradado vertical que deja sin velo la mitad superior del video.
- **fuera de alcance**: textos, botones, el `<video>` y su marcado, `static/js/portada.js`, el diálogo, el botón de pausa, la CSP, todo el diseño de ≤ 900 px, otras páginas, los planes anteriores y su evidencia.
- **áreas**: web
- **seguridad**: no — solo cambia la presentación de la portada y la herramienta que la mide.

## Contexto mínimo

- `static/css/web.css:259-273`: `.hero` es `display: grid; align-items: center` con `padding: 96px 0`; `.hero-velo` es un degradado horizontal (0,94 → 0,86 → 0,35); `.hero-texto` tiene `max-width: 640px`. El bloque de ≤ 900 px (líneas 327-330) ya lleva el texto abajo con un velo vertical y no cambia.
- `h1` mide 84 px en mayúsculas (`web.css:73`); el eslogan del fixture es "Manejo integral de plagas". Si a 84 px el `h1` no entra en una línea junto a los botones, el `h1` de la portada puede bajar en escritorio, nunca por debajo de 56 px.
- `apps/web/templates/web/paginas/inicio.html:12-21`: `.hero-texto` contiene eyebrow, `h1`, `p` y `.hero-botones`. Puede sumarse un envoltorio solo si el CSS lo necesita.
- `herramientas/medir_portada.py`: mide en 1280×800 y 375×812 los objetivos táctiles, el borde inferior de los botones en móvil y el contraste de cada texto en los segundos 0, 3 y 7. Sus funciones puras se prueban en `apps/web/tests/test_medir_portada.py`.
- `docs/02-diseno.md:66` describe el velo y la posición del texto.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (franja inferior en escritorio), T2 (integración y verificación) | ninguna |

## Subtareas

### T1 — Franja inferior de la portada en escritorio

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `static/css/web.css`, `apps/web/templates/web/paginas/inicio.html`, `herramientas/medir_portada.py`, `apps/web/tests/test_medir_portada.py`, `docs/02-diseno.md`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/js/`, `static/video/`, `static/img/`, `.railway/`, `apps/web/views.py`, `herramientas/medir_portada_js.py`, `apps/web/tests/test_medir_portada_js.py`, el resto de `apps/web/tests/`, `docs/evidencia/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 220 líneas agregadas
- **Qué hacer**:
  1. **Antes de tocar el CSS**, medir en 375×812 las posiciones de `.hero-texto` y `.hero-botones` (top y bottom de cada uno, relativos al top de `.hero`) y dejarlas como constante de referencia en `medir_portada.py`, con un comentario que diga que son las de `main` 54475f9.
  2. CSS, solo fuera de la media query de ≤ 900 px (o en una `min-width: 901px`): `.hero` alinea su contenido al borde inferior; `.hero-velo` es un degradado vertical transparente arriba y `rgba(15, 20, 23, 0.93)` desde alrededor del 45 % inferior; eyebrow, `h1` en una línea y párrafo (ancho máximo 640 px) a la izquierda, `.hero-botones` a la derecha alineados con la base del texto. Entre 901 y 1100 px, si no entran, los botones pasan debajo del texto. El `h1` de la portada no baja de 56 px. Lo de ≤ 900 px no cambia.
  3. `medir_portada.py` agrega estas mediciones, cada una con su línea PASA/FALLA, decididas por funciones puras con test:
     - `franja escritorio h1 una línea` (1280×800): el `h1` ocupa una sola línea;
     - `franja escritorio botones al pie` (1280×800): el borde inferior de `.hero-botones` queda a menos de 60 px del borde inferior de `.hero`;
     - `franja escritorio texto abajo` (1280×800): el borde superior de `.hero-texto` queda por debajo del 50 % de la altura de `.hero`;
     - `franja angosto h1 tamaño` (1000×800, viewport nuevo `angosto` que también mide contraste): el `font-size` del `h1` es de al menos 56 px y `.hero-botones` no se sale de `.hero` por la derecha;
     - `posición móvil hero-texto` y `posición móvil hero-botones` (375×812): coinciden con la referencia del paso 1, con tolerancia de 1 px.
  4. Tests nuevos en `test_medir_portada.py` sobre las funciones puras (cajas de ejemplo, sin navegador): botones a 60 px o más del borde dan FALLA, y una posición móvil corrida 2 px de la referencia da FALLA.
  5. `docs/02-diseno.md` describe la franja inferior y el velo vertical en escritorio.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada.MedirPortadaTests.test_botones_lejos_del_pie_es_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_medir_portada.MedirPortadaTests.test_posicion_movil_distinta_de_la_referencia_es_falla --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA franja escritorio h1 una línea'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA franja escritorio botones al pie'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA franja escritorio texto abajo'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA franja angosto h1 tamaño'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA posición móvil hero-texto'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA posición móvil hero-botones'`
  - `[cmd]` `PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe herramientas/medir_portada.py | grep -qE '^PASA contraste escritorio h1 s7'`
  - `[cmd]` `test -z "$(git diff --name-only "$(git log --format=%h -1 --grep='^docs(plan): portada-franja-inferior')"..HEAD -- apps/web/tests/ | grep -v '^apps/web/tests/test_medir_portada.py$')"`
  - `[cmd]` `test -z "$(git diff --name-only "$(git log --format=%h -1 --grep='^docs(plan): portada-franja-inferior')"..HEAD -- static/js/ config/ apps/web/views.py)"`
  - `[grep-1]` `grep -nF 'rgba(15, 20, 23, 0.93)' static/css/web.css`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/medir_portada.py apps/web/tests/test_medir_portada.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 220 --subtarea T1`

### T2 — Integración (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/portada-franja-inferior`, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh portada-franja-inferior T1 plan/portada-franja-inferior static/css/web.css apps/web/templates/web/paginas/inicio.html herramientas/medir_portada.py apps/web/tests/test_medir_portada.py docs/02-diseno.md`.
  3. Cierre global; bitácora al cierre. El merge en `main` y el push (que despliega) los decide el usuario.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/portada-franja-inferior | grep -q "T1: integra portada-franja-inferior-T1"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-11-18-portada-franja-inferior.md portada-franja-inferior`

## Registro de verificación

commit_base: (pendiente)

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

### Cierra
