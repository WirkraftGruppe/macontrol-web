# Plan: corregir los hallazgos de la auditoría del esqueleto

- **slug**: `hallazgos-esqueleto`
- **fecha**: 2026-10-01
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): hallazgos-esqueleto`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: el esqueleto no puede arrancar en modo desarrollo en un servidor público, las rutas tienen espacios de nombres, las fuentes se sirven desde el propio sitio y HSTS arranca con valores reversibles.
- **fuera de alcance**: autenticación, mixin de rol, DRF/JWT, CSP, `AdminSite` propio (van en el plan de autenticación); los tests `test_panel_responde_200` y `test_api_v1_responde_200` no se tocan.
- **áreas**: web | infraestructura
- **seguridad**: sí — settings de desarrollo y producción (`dev.py`, `prod.py`, HSTS), `.env.example` y recursos de terceros en `base.html`; corre también `auditor-seguridad`.

## Contexto mínimo

La auditoría del plan `esqueleto` (bitácora, entrada 2026-10-01) dejó cuatro hallazgos abiertos, y el usuario pidió corregirlos:
1. [importante] `.env.example:5` trae `DJANGO_ENV=development` como valor requerido, y `config/settings/dev.py` arranca con `DEBUG=True` cualquiera sea `ALLOWED_HOSTS`.
2. [menor] `apps/web/urls.py:8` y `apps/panel/urls.py:8` usan los dos `name="inicio"`, y ninguna app define `app_name`.
3. [menor] `templates/base.html:7-9` carga Google Fonts; la IP de cada visitante va a un tercero.
4. [menor] `config/settings/prod.py:19-21` activa HSTS con un año, subdominios y preload desde el primer despliegue.

Además, el verificador observó que `apps/web/tests/test_base.py:13` no distingue el atributo `data-tema="oscuro"` del selector CSS.

Decisiones de diseño:
- La barrera de `dev.py` acepta solo `localhost`, `127.0.0.1`, `[::1]`, `testserver` y direcciones IP privadas o de loopback. Las IP privadas quedan permitidas porque la app móvil va a probar contra el servidor de desarrollo por la red local.
- Las fuentes Barlow (400, 500, 600 y 700) y Barlow Condensed (600, 700 y 800) se sirven en woff2, subconjunto latin (cubre el español), desde `static/fonts/`, con su licencia OFL.
- HSTS: `SECURE_HSTS_SECONDS = 3600`, `INCLUDE_SUBDOMAINS = False`, `PRELOAD = False`. Se suben recién después de verificar los subdominios de la empresa.

Las tres subtareas escriben archivos disjuntos, pero los criterios de cada una cargan `dev.py` y los `urls.py`, y corren `ruff` sobre todo el árbol. Por eso van en serie, T1 → T2 → T3, en el mismo árbol. Ninguna crea migraciones.

## Subtareas

### T1 — Impedir el modo desarrollo con hosts públicos y dejar HSTS reversible

- **Depende de**: —
- **Puede tocar**: `.env.example`, `config/settings/dev.py`, `config/settings/prod.py`, `config/tests/__init__.py`, `config/tests/test_settings.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `config/settings/base.py`, `config/settings/__init__.py`, `config/urls.py`, `apps/`, `templates/`, `static/`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (settings de producción, HSTS), `.claude/skills/convenciones-proyecto/SKILL.md` § Variables de entorno
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `.env.example`: `DJANGO_ENV=` vacío, con un comentario que diga que en la máquina local va `development` y en el hosting va `production` (obligatorio). `ALLOWED_HOSTS` pasa a la sección de requeridas en producción, con una nota: sin ella, toda petición da 400.
  - `dev.py`: después de definir `ALLOWED_HOSTS`, si algún host no es local (`localhost`, `127.0.0.1`, `[::1]`, `testserver`) ni una IP privada o de loopback según `ipaddress`, lanzar `ImproperlyConfigured`. El mensaje tiene que contener el texto `usar DJANGO_ENV=production`.
  - `prod.py`: `SECURE_HSTS_SECONDS = 3600`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = False`, `SECURE_HSTS_PRELOAD = False`, con un comentario: se suben después de verificar los subdominios (ver `docs/decisiones.md`).
  - Tests en `config/tests/test_settings.py`, clase `SettingsTests`. Cada test levanta un proceso aparte con `sys.executable manage.py …` y su propio entorno; hay que quitar del entorno heredado `DJANGO_ENV`, `ALLOWED_HOSTS`, `SECRET_KEY` y `DATABASE_URL`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_rechaza_hosts_publicos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_acepta_hosts_locales_y_red_privada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_prod_hsts_reversible --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_env_example_no_fija_django_env --keepdb`
  - `[grep-0]` `grep -n "^DJANGO_ENV=development" .env.example`
  - `[grep-1]` `grep -n "^DJANGO_ENV=$" .env.example`
  - `[grep-0]` `grep -n "SECURE_HSTS_PRELOAD = True" config/settings/prod.py`
  - `[cmd]` `out="$(env -u SECRET_KEY -u DATABASE_URL ALLOWED_HOSTS=macontrol.com.ar PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check 2>&1)"; test $? -ne 0 && echo "$out" | grep -q "usar DJANGO_ENV=production"`
  - `[cmd]` `env -u SECRET_KEY -u DATABASE_URL ALLOWED_HOSTS=localhost,192.168.1.10 PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `out="$(SECRET_KEY="$(./venv/Scripts/python.exe -c 'import secrets;print(secrets.token_urlsafe(60))')" DATABASE_URL=sqlite:///prod-check.sqlite3 ALLOWED_HOSTS=macontrol.com.ar PYTHONIOENCODING=utf-8 DJANGO_ENV=production ./venv/Scripts/python.exe manage.py check --deploy 2>&1)" && test "$(echo "$out" | grep -oE 'security\.W[0-9]+' | sort -u | tr '\n' ' ')" = "security.W005 security.W021 "`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hallazgos-esqueleto.md hallazgos-esqueleto)" 250 .env.example config/settings/dev.py config/settings/prod.py config/tests`

### T2 — Dar espacio de nombres a las rutas de web, panel y api

- **Depende de**: T1
- **Puede tocar**: `apps/web/urls.py`, `apps/panel/urls.py`, `apps/api/urls.py`, `apps/web/tests/test_rutas.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `config/`, `templates/`, `static/`, `apps/web/tests/test_base.py`, cualquier otro archivo de `apps/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` (urls)
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 100 líneas agregadas
- **Qué hacer**:
  - Agregar `app_name = "web"`, `app_name = "panel"` y `app_name = "api"` en sus `urls.py`. Los nombres de ruta no cambian.
  - En `test_rutas.py`, agregar a `RutasTests`:
    - `test_rutas_con_espacio_de_nombres`: `reverse("web:inicio") == "/"`, `reverse("panel:inicio") == "/panel/"`, `reverse("api:raiz") == "/api/v1/"`, y `reverse("web:qr", args=[uuid])` arma `/q/<uuid>/`.
    - `test_inicio_sin_espacio_de_nombres_no_resuelve`: `reverse("inicio")` lanza `NoReverseMatch`.
  - Los tests existentes no se modifican.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_rutas_con_espacio_de_nombres --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_inicio_sin_espacio_de_nombres_no_resuelve --keepdb`
  - `[grep-1]` `grep -n "app_name = \"web\"" apps/web/urls.py`
  - `[grep-1]` `grep -n "app_name = \"panel\"" apps/panel/urls.py`
  - `[grep-1]` `grep -n "app_name = \"api\"" apps/api/urls.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hallazgos-esqueleto.md hallazgos-esqueleto)" 100 apps/web/urls.py apps/panel/urls.py apps/api/urls.py apps/web/tests/test_rutas.py`

### T3 — Servir las fuentes desde el propio sitio

- **Depende de**: T2
- **Puede tocar**: `templates/base.html`, `static/fonts/` (todo), `apps/web/tests/test_base.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `config/`, `static/img/`, cualquier otro archivo de `apps/`
- **Skill a leer antes**: `.agents/skills/frontend-design/SKILL.md` (tipografía), `docs/02-diseno.md` (pesos que usa el diseño)
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 300 líneas agregadas, medidas después del commit de T3. Sin rastrear, `presupuesto.sh` cuenta los binarios con `wc -l`; ya commiteados, numstat los marca como binarios y no suman.
- **Qué hacer**:
  - Descargar los woff2, subconjunto latin, de `@fontsource/barlow` y `@fontsource/barlow-condensed` (versión 5, `https://cdn.jsdelivr.net/npm/@fontsource/<familia>@5/files/<familia>-latin-<peso>-normal.woff2`). Barlow: 400, 500, 600 y 700. Barlow Condensed: 600, 700 y 800. Van a `static/fonts/` con el mismo nombre de archivo, junto con la licencia OFL de la familia en `static/fonts/OFL.txt`.
  - En `base.html`: borrar los tres `<link>` a Google, y declarar un `@font-face` por archivo con `{% static %}` y `font-display: swap`.
  - En `test_base.py`:
    - corregir la línea 13 para que compruebe el atributo de `<html>` (`<html lang="es" data-tema="oscuro">`) y no el selector CSS;
    - agregar `test_base_tema_por_defecto_es_oscuro`;
    - agregar `test_base_no_carga_fuentes_de_terceros` (no aparece `fonts.googleapis.com` ni `fonts.gstatic.com`);
    - agregar `test_fuentes_referenciadas_existen`: cada `url(...)` de un `@font-face` del HTML renderizado resuelve con `django.contrib.staticfiles.finders.find`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base.BaseTemplateTests.test_base_tema_por_defecto_es_oscuro --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base.BaseTemplateTests.test_base_no_carga_fuentes_de_terceros --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base.BaseTemplateTests.test_fuentes_referenciadas_existen --keepdb`
  - `[grep-0]` `grep -rn "fonts.googleapis.com\|fonts.gstatic.com" templates/`
  - `[existe]` `static/fonts/OFL.txt`
  - `[existe]` `static/fonts/barlow-latin-400-normal.woff2`
  - `[existe]` `static/fonts/barlow-latin-700-normal.woff2`
  - `[existe]` `static/fonts/barlow-condensed-latin-700-normal.woff2`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hallazgos-esqueleto.md hallazgos-esqueleto)" 300 templates/base.html static/fonts apps/web/tests/test_base.py`

### T4 — Registrar las decisiones y actualizar el documento de diseño

- **Depende de**: T3
- **Puede tocar**: `docs/decisiones.md`, `docs/02-diseno.md`
- **No puede tocar**: `docs/planes/`, código
- **Skill a leer antes**: —
- **Worktree**: no
- **Ruta**: inline (principal) · Evidencia: … · Commit: …
- **Presupuesto**: 20 líneas agregadas
- **Qué hacer**:
  - En `docs/decisiones.md`, tres líneas. Cada una empieza con su rótulo literal:
    - `HSTS reversible` (W005 y W021 aceptados hasta verificar los subdominios);
    - `Fuentes Barlow autohospedadas` (sin Google Fonts en ninguna parte, reemplaza lo escrito en `docs/02-diseno.md`);
    - `Barrera de hosts en dev.py`.
  - En `docs/02-diseno.md`, reemplazar la frase sobre Google Fonts para que diga que las fuentes se sirven desde `static/fonts/` en la web y en el panel.
- **Criterios**:
  - `[grep-1]` `grep -n "HSTS reversible" docs/decisiones.md`
  - `[grep-1]` `grep -n "Fuentes Barlow autohospedadas" docs/decisiones.md`
  - `[grep-1]` `grep -n "Barrera de hosts en dev.py" docs/decisiones.md`
  - `[grep-0]` `grep -n "Google Fonts" docs/02-diseno.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hallazgos-esqueleto.md hallazgos-esqueleto)" 20 docs/decisiones.md docs/02-diseno.md`

## Trabajo del principal (integración)

Nada fuera de T4.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hallazgos-esqueleto.md hallazgos-esqueleto`

## Registro de verificación

commit_base: 8f23dee

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-01 | T1 | afdfc0e | PASA (verificador 13/13; verificador-b 13/13) | ruta: delegada · commit T1: afdfc0e |
| 2026-10-01 | T1+T2 | a5f8b65 | PASA (verificador 21/21; verificador-b 21/21) | ruta: delegada · commit T2: a5f8b65 |
| 2026-10-01 | T1..T4 | 338b81b | PASA (verificador 37/37; verificador-b 41/41, cuenta distinta de agrupación) | ruta: delegada · commit T3: a91fc9f |
| 2026-10-01 | T4 | 338b81b | PASA (en la misma corrida) | ruta: inline (principal) · commit T4: 338b81b |
| | TODO | | | |
