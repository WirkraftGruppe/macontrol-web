# Plan: demo-portatil — carpeta autocontenida para correr la demo en cualquier PC con Windows
<!-- Nivel Chico, decidido por el usuario: sin juez-plan. Flujo: commit docs(plan) → commit_base en el Registro; congelado arriba del corte. -->

- **slug**: `demo-portatil`
- **fecha**: 2026-10-12
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): demo-portatil`. El hash se anota en `## Registro de verificación`.
- **objetivo**: que una carpeta `macontrol-demo/` (entregada como zip) se copie a cualquier PC con Windows 10/11 de 64 bits y arranque la demo con doble clic, sin instalar Python ni dependencias en esa PC.
- **fuera de alcance**:
  - `demo.bat` de la raíz.
  - `apps/panel/management/commands/cargar_demo.py`.
  - `templates/**`, `static/**` (incluido el CSS).
  - `config/settings/**`: el control de hosts públicos de `dev.py` no se afloja.
  - GTK y la generación de PDF: el paquete portátil no genera PDF.
- **áreas**: infraestructura
- **seguridad**: no. No toca la autenticación, los roles ni los settings de producción. El paquete copia solo archivos versionados, así que no lleva `.env`.

## Contexto mínimo
- `demo.bat` (raíz) depende de `venv\Scripts\python.exe`, que no es portable.
- `config/settings/dev.py:45-50` corta con `ImproperlyConfigured` ante cualquier host de `ALLOWED_HOSTS` que no sea local ni una IP privada, y `*` entra en ese caso. Por eso el `demo.bat` portátil detecta la IP como el de la raíz (`localhost,127.0.0.1,<IP>`). Si no hay red, arranca solo con localhost y lo avisa.
- WeasyPrint figura en `requirements.txt` pero ningún `.py` de `apps/` ni de `config/` lo importa: no hace falta pasarlo a import perezoso. Un test nuevo protege que `check` siga pasando sin él.
- El venv es Python 3.13.15. El embebido es `python-3.13.15-embed-amd64.zip` de python.org, con tamaño y SHA-256 fijos en el script.
- `dev.py:53-54` toma `DATABASE_URL`; con `sqlite:///demo.sqlite3` el archivo queda en el directorio actual (`demo.bat` hace `cd /d "%~dp0"`).

## Decisiones
- 2026-10-12 — Detectar la IP privada en el `demo.bat` portátil en lugar de usar `ALLOWED_HOSTS=*` — `dev.py` rechaza `*` y aflojar ese control no se justifica para una demo — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-12 — Instalar las dependencias con el pip del venv (`--target python/Lib/site-packages --platform win_amd64 --python-version 3.13 --only-binary :all:`) en lugar de `get-pip.py` dentro del embebido — una descarga sin verificar menos, el paquete no lleva pip y las wheels quedan en caché en `dist/cache/wheels/`, así que `--sin-descarga` funciona sin red — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-12 — La caché vive en `dist/cache/` del checkout principal (resuelto con `git rev-parse --git-common-dir`) — los worktrees la comparten y `--sin-descarga` funciona en ellos — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-12 — El código se copia con `git ls-files` sobre las rutas incluidas — nunca viajan `.env`, `__pycache__`, `media/` ni archivos sin versionar — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-12 — `demo.bat` portátil no abre el navegador si `DEMO_SIN_NAVEGADOR=1` — lo necesita la prueba de humo — decidida por Claude, revisable — reemplaza a: (nada)

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | ninguna |
| 2 | T3, T4 (integración y cierre) | ninguna |

## Subtareas

### T1 — Crear el empaquetador `herramientas/empaquetar_demo.py`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `herramientas/empaquetar_demo.py`, `apps/panel/tests/test_sin_weasyprint.py`, `.gitignore`
- **No puede tocar**: `docs/planes/`, `demo.bat`, `apps/panel/management/`, `templates/`, `static/`, `config/`, `requirements.txt`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (comandos, prohibiciones) y `.agents/skills/python-best-practices/SKILL.md` (la sección que aplique a scripts y subprocess)
- **Worktree**: sí (`worktrees/demo-portatil-T1`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  1. **Preparar el embebido.** Lo descarga de python.org a la caché (`<checkout principal>/dist/cache/`), verificando el tamaño y el SHA-256 fijados como constantes. Con `--sin-descarga` no hay red: usa la caché o falla con un mensaje claro que nombra el archivo faltante. Lo descomprime en `<destino>/macontrol-demo/python/`. Reescribe `python313._pth` con `python313.zip`, `.`, `Lib\site-packages`, `..` e `import site`.
  2. **Instalar las dependencias.** Las wheels de `requirements.txt` se bajan con `pip download --only-binary :all: --platform win_amd64 --python-version 3.13 --implementation cp` a `dist/cache/wheels/`; con `--sin-descarga` se omite ese paso. Después se instalan desde ahí con `pip install --no-index --find-links … --target …/python/Lib/site-packages` y el mismo `--only-binary`. Si un paquete no tiene wheel, falla nombrándolo, sin recurrir al código fuente.
  3. **Copiar el código.** Usa `git ls-files` para `apps/`, `config/`, `templates/`, `static/`, `manage.py`, `requirements.txt` y `docs/demo-cliente.md`. Excluye explícitamente `venv/`, `worktrees/`, `.git/`, `*.sqlite3`, `media/`, `.claude/` y `.env*`.
  4. **Escribir `demo.bat` y `LEEME.txt`.** El `demo.bat` portátil usa `python\python.exe`, nunca `venv`. Variables: `DJANGO_ENV=development`, `PYTHONIOENCODING=utf-8` y `DATABASE_URL=sqlite:///demo.sqlite3`. `ALLOWED_HOSTS` es `localhost,127.0.0.1,<IP>` con la IP detectada como en el `demo.bat` de la raíz, o solo localhost con un aviso si no la encuentra. Corre `migrate --noinput` y `cargar_demo`, e imprime "Notebook: http://localhost:8000/" y "Teléfono (misma Wi-Fi): http://<IP>:8000/". Abre localhost en el navegador salvo con `DEMO_SIN_NAVEGADOR=1`, y termina con `runserver 0.0.0.0:8000 --noreload`. El `LEEME.txt` tiene unas 10 líneas: qué es, el doble clic, qué abrir, cómo apagar y el permiso del firewall.
  5. **Comprimir.** Arma `<destino>/macontrol-demo.zip` e imprime su tamaño y su ruta. Agrega `dist/` a `.gitignore`. Crea el test `apps/panel/tests/test_sin_weasyprint.py`: corre un subproceso con `sys.modules['weasyprint'] = None` y `call_command('check')` (las URL incluidas), que debe terminar en 0.
- **Criterios**:
  - `[existe]` `herramientas/empaquetar_demo.py`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/empaquetar_demo.py --sin-descarga --destino dist/prueba`
  - `[existe]` `dist/prueba/macontrol-demo/python/python.exe`
  - `[existe]` `dist/prueba/macontrol-demo.zip`
  - `[existe]` `dist/prueba/macontrol-demo/LEEME.txt`
  - `[cmd]` `dist/prueba/macontrol-demo/python/python.exe -c "import django, PIL, segno, pypdfium2"`
  - `[cmd]` `cd dist/prueba/macontrol-demo && PYTHONIOENCODING=utf-8 DJANGO_ENV=development DATABASE_URL=sqlite:///demo.sqlite3 ALLOWED_HOSTS=localhost,127.0.0.1 ./python/python.exe manage.py check`
  - `[cmd]` `cd dist/prueba/macontrol-demo && PYTHONIOENCODING=utf-8 DJANGO_ENV=development DATABASE_URL=sqlite:///demo.sqlite3 ALLOWED_HOSTS=localhost,127.0.0.1 ./python/python.exe manage.py migrate --noinput && PYTHONIOENCODING=utf-8 DJANGO_ENV=development DATABASE_URL=sqlite:///demo.sqlite3 ALLOWED_HOSTS=localhost,127.0.0.1 ./python/python.exe manage.py cargar_demo`
  - `[grep-0]` `grep -n "venv" dist/prueba/macontrol-demo/demo.bat`
  - `[no-existe]` `dist/prueba/macontrol-demo/.env`
  - `[no-existe]` `dist/prueba/macontrol-demo/.claude`
  - `[grep-1]` `grep -n "^dist/" .gitignore`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_sin_weasyprint.SinWeasyprintTests.test_check_pasa_con_weasyprint_bloqueado --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T1`

### T2 — Integración (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/demo-portatil` de T1, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh demo-portatil T1 plan/demo-portatil herramientas/empaquetar_demo.py apps/panel/tests/test_sin_weasyprint.py .gitignore`.
  3. Crear `worktrees/demo-portatil-T3` con `bash .claude/hooks/worktree-crear.sh demo-portatil T3 plan/demo-portatil`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/demo-portatil | grep -q "T1: integra demo-portatil-T1"`

### T3 — Prueba de humo `herramientas/humo_demo.py` y documentación

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `herramientas/humo_demo.py`, `docs/demo-cliente.md`
- **No puede tocar**: `docs/planes/`, `herramientas/empaquetar_demo.py`, `demo.bat`, `apps/`, `templates/`, `static/`, `config/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (mapa de rutas, login del panel) y `.agents/skills/python-best-practices/SKILL.md` (subprocess)
- **Worktree**: sí (`worktrees/demo-portatil-T3`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  1. `humo_demo.py <carpeta>` lanza `<carpeta>/demo.bat` en segundo plano con `DEMO_SIN_NAVEGADOR=1` y espera hasta 120 s a que responda `http://localhost:8000/`. Si el puerto 8000 ya está ocupado antes de lanzar, falla.
  2. Comprueba, solo con la biblioteca estándar:
     - `GET /` devuelve 200.
     - `GET /panel/` devuelve 302 con `Location` hacia el login.
     - El login como `demo-admin` / `demo1234` por POST, con el token CSRF de la página y la cookie, funciona.
     - Después del login, `GET /panel/` devuelve 200.
  3. Apaga el árbol de procesos con `taskkill /T /F /PID` en un `finally`, pase o falle, y termina en 0 solo si todo pasó.
  4. Agrega a `docs/demo-cliente.md` la sección `## Llevar la demo a otra PC`: correr el empaquetador, copiar el zip, descomprimir, doble clic en `demo.bat` y aceptar el firewall.
- **Criterios**:
  - `[cmd]` `./venv/Scripts/python.exe herramientas/empaquetar_demo.py --sin-descarga --destino dist/prueba && ./venv/Scripts/python.exe herramientas/humo_demo.py dist/prueba/macontrol-demo`
  - `[existe]` `herramientas/humo_demo.py`
  - `[grep-1]` `grep -n "## Llevar la demo a otra PC" docs/demo-cliente.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`

### T4 — Integración (principal)

- **Ola**: 2 (después de verificar T3)
- **Depende de**: T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/demo-portatil` de T3, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh demo-portatil T3 plan/demo-portatil herramientas/humo_demo.py docs/demo-cliente.md`.
  3. Correr el empaquetador sin `--sin-descarga` hacia `dist/` para obtener el zip final, y después el cierre global y la verificación `TODO`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/demo-portatil | grep -q "T3: integra demo-portatil-T3"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-12-demo-portatil.md demo-portatil`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): demo-portatil — modificado: <motivo>`. -->

commit_base: 74f544d

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
| 2026-10-12 | T1 | 7e10703 | PASA (14/14) | verificador |
| 2026-10-12 | T3 | b3e22eb | PASA (4/4) | verificador |

## Pendientes que deja este plan

### Cierra
- P-demo-portatil-1 [menor] `requirements.txt` instala `ruff` y `WeasyPrint` en el paquete portátil sin usarse ahí (zip de 65,4 MB); separar un `requirements-demo.txt` o de producción lo achicaría.
- P-demo-portatil-2 [menor] El mensaje de falla de `empaquetar_demo.py --sin-descarga` con la caché vacía no se ejercitó en ninguna corrida.
- P-demo-portatil-3 [observación] Al cambiar la versión del embebido hay que actualizar tres constantes del script (versión, tamaño, SHA-256); el SHA-256 se toma del `.sigstore` publicado junto al zip en python.org, porque la página de la release no lo lista.
- P-demo-portatil-4 [observación] La consola cp1252 muestra mal los acentos en la salida de `empaquetar_demo.py` y `humo_demo.py` (solo cosmético).
- 2026-10-12 — El `demo.bat` portátil detecta la IP privada en lugar de `ALLOWED_HOSTS=*` — `dev.py` rechaza `*` — reemplaza a: (nada)
- 2026-10-12 — Las dependencias del paquete portátil se instalan con el pip del venv (`--target`, `--only-binary :all:`, wheels en caché) en lugar de `get-pip.py` — sin pip dentro del paquete y `--sin-descarga` sin red — reemplaza a: (nada)
