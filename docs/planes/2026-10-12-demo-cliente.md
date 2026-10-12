# Plan: demo-cliente — datos de demostración, arranque local y preparación para alojar
<!-- Nivel Chico, decidido por el usuario: sin juez-plan. Flujo: commit docs(plan) → commit_base en el Registro; congelado arriba del corte. -->

- **slug**: demo-cliente
- **fecha**: 2026-10-12
- **commit_base**: (se anota en el Registro)
- **objetivo**: que mañana el cliente recorra el sitio público y el panel desde una notebook y un teléfono, en la red local, con datos precargados y realistas. Además, dejar el proyecto listo para alojarlo (solo configuración).
- **fuera de alcance**:
  - Escaneo de QR y flujo del empleado. Por decisión del usuario, la demo es solo del panel; el escaneo espera a la app móvil.
  - Desplegar.
  - Tocar `apps/web/templates/**` y `static/**`, que son de robustez-panel T4/T10.
  - Formularios de contacto.
  - Textos nuevos de la empresa.
  - Los pendientes de `despliegue` que no se citan en T3.
- **áreas**: panel, infraestructura
- **seguridad**: sí, solo T3. Toca settings de producción, así que `auditor-seguridad` revisa T3 antes de integrarlo (CLAUDE.md § 6).

## Contexto mínimo
- `apps/panel/management/commands/cargar_demo.py` ya existe:
  - Crea `demo-admin` y `demo-empleado` con clave `demo1234` (`CLAVE_DEMO`, :28): 2 "Cliente Demo N", 3 sitios, 10 puntos, 1 plano y unos días de visitas.
  - Usa `get_or_create`, sin marca de demo.
  - Tests en `apps/panel/tests/test_cargar_demo.py`, con conteos exactos en :58, :69-70, :96 y :110, y el regex `^Cliente Demo` en :41.
- `apps/panel/demo.py:15` `exigir_entorno_demo` permite correr solo con DEBUG, `DJANGO_ENV=development` y SQLite (decisión 2026-10-06, `docs/decisiones.md:93`). Se mantiene.
- Los servicios de visitas no admiten historia vieja:
  - `registrar_revision` rechaza un atraso mayor a `ATRASO_MAXIMO_HORAS` (168 h; `apps/visitas/services.py:376`).
  - `abrir_visita` sella la hora actual.
  - Los `creado` son `auto_now_add`.
  - Por eso 3 meses de historia necesitan ORM directo con `full_clean()` y `.update()` de las fechas.
- `apps/sitios/qr.py` arma el QR al vuelo desde `qr_codigo`. Todo punto ya tiene su QR, y el panel lo descarga (`PuntoQRPng`).
- Los planos usan `apps/sitios/services.ubicar_en_plano` (:114). Las fotos pasan por `procesar_imagen` en `Foto.save`.
- `config/settings/dev.py:23-43` acepta IP privadas en `ALLOWED_HOSTS` y toma `DATABASE_URL` (por defecto SQLite).
- `prod.py` exige `SECRET_KEY` y `DATABASE_URL`, y no lee `CSRF_TRUSTED_ORIGINS`.
- No hay whitenoise, gunicorn, Procfile ni railway.json.
- Hay tests de settings en `config/tests/test_settings.py`, entre ellos `CheckDeployTests`.
- `docs/00-contenido-fuente.md:70-71` es la lista de "Quienes confían en nosotros". P-sitio-publico-3: `cargar_demo` no carga `contenido_inicial`.

## Olas
| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 en paralelo, después T4 (integración) | ninguna |
| 2 | T3 desde el commit de T4, después T5 (integración y cierre) | ninguna |

T3 va sola en la ola 2 porque `config/` y `requirements.txt` son del principal y nunca se tocan en paralelo (Tabla de propiedad).

## Subtareas

### T1 — Reescribir `cargar_demo` con datos realistas, marcados y recreables
- **Ola**: 1 · **Depende de**: — · **Worktree**: sí (`worktrees/demo-cliente-T1`) · **Ruta**: delegada (`implementador`)
- **Puede tocar**:
  - `apps/panel/management/commands/cargar_demo.py`
  - `apps/panel/demo.py`
  - `apps/panel/demo_*.py` (módulos nuevos de generación de imágenes o datos)
  - `apps/panel/tests/test_cargar_demo.py`
- **No puede tocar**:
  - `docs/planes/`
  - `config/`
  - `apps/*/models.py`, `apps/*/migrations/`, `apps/*/services.py`
  - `apps/web/templates/**`, `static/**`
  - `apps/visitas/management/commands/registrar_revision_demo.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` y la sección de tests/management de `.agents/skills/` que aplique a Django.
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**:
  - **Marca de demo, sin migraciones**:
    - `Cliente.notas` y `Sitio.notas` empiezan con `[demo] Datos de demostración generados por cargar_demo.`
    - Los productos demo llevan el sufijo ` (demo)` en `nombre_comercial`.
    - Los datos del formato viejo (`^Cliente Demo \d+$`, tipo `demo-control-de-plagas`) también cuentan como demo, para limpiar las bases ya cargadas.
  - **Borrado y recreación** en una transacción:
    - Se borran solo los datos marcados, en orden visitas → proyectos → planos y puntos → sitios → clientes → productos demo (respetando los PROTECT), junto con sus filas `Historical*` y los archivos de plano y foto.
    - Las cuentas `demo-admin` y `demo-empleado` se conservan con el comportamiento actual (crear si faltan, avisar sin modificar).
    - Nunca se toca un dato sin marca.
  - **Contenido**:
    - 4 clientes con `razon_social` tomada literal de la lista de la Carta.
    - 6 sitios con direcciones genéricas de Castelli y Chascomús ("Ruta 2 km …", "Calle … s/n"), coordenadas reales de esas localidades y `telefono_en_sitio` claramente ficticio (`0000-000000`). Sin email ni CUIT.
    - Entre 20 y 30 puntos en total, contando los "General".
    - 1 plano esquemático dibujado con Pillow en uno de los sitios, con al menos 4 puntos ubicados mediante `ubicar_en_plano`.
    - Tipos de servicio reales tomados por slug (`control-plagas-urbanas`, `servicio-mipu`). Si faltan, se crean con `get_or_create` y el nombre del fixture, sin pisar nada.
    - Si no hay ninguna `PaginaServicio`, se carga `contenido_inicial` (cierra P-sitio-publico-3).
  - **Historia de unos 90 días**:
    - Visitas quincenales REALIZADA por proyecto, origen APP y cierre EMPLEADO, creadas por ORM con `full_clean()` y fechas retrotraídas con `.update()`.
    - Una revisión por punto activo con al menos 1 foto generada.
    - `ProductoAplicado` en una parte de las revisiones.
    - 2 o 3 revisiones con `incidencia_ubicacion` (`distancia_m > DISTANCIA_MAXIMA_M`), con la visita marcada.
    - 1 visita PENDIENTE próxima y `proxima_visita` coherente.
    - Datos de planilla completados según `esquema_planilla`.
    - Nada se descarga de la red.
  - **Tests**:
    - Se reemplazan los que fijaban el contrato viejo (conteos exactos, regex `Cliente Demo`, atraso acotado y corrida incompleta).
    - Se conservan los de entorno (`test_rechaza_*`, `test_base_local_rechaza_host_remoto`), `test_avisa_usuario_demo_existente_sin_modificarlo` y el de planos huérfanos, adaptado si hace falta.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_crea_los_conteos_esperados --keepdb`. Comprueba: 4 clientes, 6 sitios, entre 20 y 30 puntos, ≥1 plano con ≥4 puntos con x/y, al menos 1 `ProductoAplicado`, entre 2 y 3 revisiones con incidencia de ubicación, 1 cuenta por rol y toda revisión con ≥1 foto.
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_segunda_corrida_no_duplica --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_conserva_datos_que_no_son_demo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_clientes_salen_de_la_carta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_historial_de_tres_meses --keepdb`. Comprueba que la visita realizada más vieja tiene ≥85 días y que hay visitas en cada uno de los 3 meses.
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_limpia_el_formato_viejo --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo --keepdb`
  - `[grep-0]` `grep -nE "contacto_email|urlopen|requests\." apps/panel/management/commands/cargar_demo.py apps/panel/demo.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T1`

### T2 — `demo.bat` y guía de la demo
- **Ola**: 1 · **Depende de**: — · **Worktree**: sí (`worktrees/demo-cliente-T2`) · **Ruta**: delegada (`implementador`)
- **Puede tocar**: `demo.bat` y `docs/demo-cliente.md`, ambos nuevos.
- **No puede tocar**: `docs/planes/`, `config/`, `apps/**`, `static/**`, `requirements.txt`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (comandos canónicos).
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `demo.bat` en la raíz:
    1. Usa `venv\Scripts\python.exe`. Si no existe, avisa y sale.
    2. Fija `DJANGO_ENV=development`, `PYTHONIOENCODING=utf-8` y `DATABASE_URL=sqlite:///<raíz>/demo.sqlite3`, una base aparte que ya ignora `*.sqlite3`, para no mezclar la demo con la base de desarrollo.
    3. Detecta la IPv4 de la red local con PowerShell (interfaz con gateway, sin loopback ni vEthernet). Arma `ALLOWED_HOSTS=localhost,127.0.0.1,<ip>`.
    4. Corre `migrate --noinput` y `cargar_demo`, y corta si alguno falla.
    5. Imprime `http://<ip>:8000/`, `http://<ip>:8000/panel/` y las dos cuentas con su clave.
    6. Arranca `runserver 0.0.0.0:8000`.
  - `docs/demo-cliente.md`:
    - Requisitos: misma red Wi-Fi y permitir Python en el firewall de Windows la primera vez.
    - Cómo arrancar.
    - Recorrido en orden:
      1. Sitio público: inicio, servicios, empresa, contacto.
      2. Panel como `demo-admin`: tablero, mapa, clientes, sitio con plano y puntos, QR de un punto, ficha de visita con fotos y productos, incidencias de ubicación, historial.
      3. El mismo panel desde el teléfono.
    - Cómo apagar (Ctrl+C) y cómo volver a cargar los datos.
    - Sin escaneo de QR, por decisión del usuario.
- **Criterios**:
  - `[existe]` `demo.bat`
  - `[existe]` `docs/demo-cliente.md`
  - `[grep-1]` `grep -nF "0.0.0.0:8000" demo.bat`
  - `[grep-1]` `grep -n "cargar_demo" demo.bat`
  - `[grep-1]` `grep -nF "demo.sqlite3" demo.bat`
  - `[grep-0]` `grep -n "DJANGO_ENV=production" demo.bat`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development DATABASE_URL=sqlite:///demo.sqlite3 ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50 ./venv/Scripts/python.exe manage.py check`
  - `[grep-1]` `grep -n "demo-empleado" docs/demo-cliente.md`
  - `[grep-1]` `grep -nF "Ctrl+C" docs/demo-cliente.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`

### T6 — Historia de 90 días de la demo (partición de T1 por presupuesto)
- **Ola**: 1 · **Depende de**: T1 · **Worktree**: sí (misma rama `demo-cliente-T1`) · **Ruta**: delegada (`implementador`, ya escrito en T1); el principal parte el commit sin cambiar código
- **Puede tocar**: `apps/panel/demo_historia.py`
- **No puede tocar**: lo mismo que T1
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: el generador de la historia de unos 90 días descripto en T1 ("Historia de unos 90 días"). T1 lo excedía (789 líneas contra 700); su commit se parte en `T1:` (todo menos `demo_historia.py`) y `T6:` (`demo_historia.py`). El commit intermedio `T1:` no es autónomo porque importa `demo_historia`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_planillas_validas_contra_su_esquema --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoClienteTests.test_visita_pendiente_coherente_con_el_proyecto --keepdb`
  - `[grep-0]` `grep -nE "urlopen|requests\." apps/panel/demo_historia.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T6`

### T4 — Integración ola 1 (principal)
- **Ola**: 1 · **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/demo-cliente` en cada worktree.
  2. Spot check de un comando de cada informe.
  3. `worktree-integrar.sh demo-cliente T1 plan/demo-cliente apps/panel/`
  4. `worktree-integrar.sh demo-cliente T2 plan/demo-cliente demo.bat docs/demo-cliente.md`
  5. Crear `demo-cliente-T3` desde ese commit.
- **Presupuesto**: no aplica
- **Criterios**:
  - `[cmd]` `git log --oneline plan/demo-cliente | grep -q "T1: integra demo-cliente-T1"`
  - `[cmd]` `git log --oneline plan/demo-cliente | grep -q "T2: integra demo-cliente-T2"`

### T3 — Configuración para alojar, sin desplegar
- **Ola**: 2 · **Depende de**: T4 · **Worktree**: sí (`worktrees/demo-cliente-T3`) · **Ruta**: delegada (`implementador`) y después `auditor-seguridad`
- **Puede tocar**:
  - `config/settings/prod.py` y `config/settings/dev.py`
  - `config/tests/test_settings.py`
  - `requirements.txt`
  - `railway.json`, `.python-version` y `docs/despliegue.md`, los tres nuevos
  - `.env.example`
- **No puede tocar**: `docs/planes/`, `config/settings/base.py`, `config/urls.py`, `apps/**`, `static/**`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`. Opcionalmente `railway:use-railway`, solo como referencia de `railway.json`.
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - `requirements.txt`: agregar `gunicorn` y `whitenoise`.
  - `prod.py`:
    - `WhiteNoiseMiddleware` justo después de `SecurityMiddleware`.
    - `STORAGES` con `CompressedManifestStaticFilesStorage` para static y disco local para media (`MEDIA_ROOT` del entorno).
    - `CSRF_TRUSTED_ORIGINS` desde el entorno, separado por comas y con recorte de espacios.
    - Abortar si `ALLOWED_HOSTS` está vacío.
  - `dev.py`: abortar si existe `RAILWAY_ENVIRONMENT`, para que no se despliegue con DEBUG (atiende P-pendientes-heredados-15 para Railway).
  - `railway.json`:
    - Build con `collectstatic --noinput`.
    - `preDeployCommand` con `migrate --noinput`.
    - Inicio con `gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 60`.
  - `.python-version` con 3.13.
  - `.env.example` con `CSRF_TRUSTED_ORIGINS`.
  - `docs/despliegue.md`, guía para que el usuario despliegue a mano:
    - Cuenta, proyecto, base Postgres y variables.
    - Volumen para `media/`.
    - Por qué `cargar_demo` no corre sobre Postgres: decisión 2026-10-06.
    - Pendientes de `despliegue` que siguen abiertos.
  - En el venv compartido se instalan gunicorn y whitenoise. Es aditivo; gunicorn no arranca en Windows, pero se instala.
- **Criterios**:
  - `[grep-1]` `grep -n "^gunicorn" requirements.txt`
  - `[grep-1]` `grep -n "^whitenoise" requirements.txt`
  - `[grep-1]` `grep -nF "whitenoise.middleware.WhiteNoiseMiddleware" config/settings/prod.py`
  - `[grep-1]` `grep -n "collectstatic" railway.json`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_lee_csrf_trusted_origins --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_sin_allowed_hosts_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_dev_aborta_en_railway --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=production SECRET_KEY=ejemplo-solo-para-check-9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1 DATABASE_URL=postgres://demo:demo@localhost:5432/demo ALLOWED_HOSTS=demo.up.railway.app CSRF_TRUSTED_ORIGINS=https://demo.up.railway.app ./venv/Scripts/python.exe manage.py check --deploy`. Pasa con warnings, que se listan en el informe.
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T3`

### T5 — Integración ola 2 y cierre (principal)
- **Ola**: 2 · **Depende de**: T3
- **Pasos**:
  1. Revisar `cambios.sh`.
  2. Correr `auditor-seguridad` sobre T3 y corregir lo bloqueante (máximo dos rondas).
  3. `worktree-integrar.sh demo-cliente T3 plan/demo-cliente config/ requirements.txt railway.json .python-version .env.example docs/despliegue.md`
  4. `verificador` con TODO.
- **Presupuesto**: no aplica
- **Criterios**:
  - `[cmd]` `git log --oneline plan/demo-cliente | grep -q "T3: integra demo-cliente-T3"`

## Criterios de cierre global
```bash
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb
[cmd] ./venv/Scripts/python.exe -m ruff check .
[cmd] test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0
[cmd] bash .claude/hooks/congelado.sh docs/planes/2026-10-12-demo-cliente.md demo-cliente
```

## Registro de verificación
commit_base: d8caed8

### Estado de subtareas
| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T6 | hecha |
| T4 | hecha |
| T3 | hecha |
| T5 | hecha |

### Corridas
| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-12 | T1, T6, T2 (verificador) | b368e3e (T1/T6) · 9452ed1 (T2) | FALLA formal: 23/23 criterios PASA; único motivo congelado.sh CONTRATO MODIFICADO (055dd91, dffcb24) | modificaciones aprobadas por el usuario |
| 2026-10-12 | T4 (principal) | 568d857 | 2/2 PASA | worktree-integrar: 619 tests OK en cada merge; `branch -d` falla con la raíz en main (rama destino sin checkout en la raíz), ramas borradas con -D tras `merge-base --is-ancestor` |
| 2026-10-12 | T3 (verificador) | 4188e67 | FALLA formal: 10/10 PASA; único motivo CONTRATO MODIFICADO | check --deploy: solo W005 y W021 (HSTS reversible) |
| 2026-10-12 | T3 (auditor-seguridad) | 4188e67 | sin bloqueantes | I-1, I-2 importantes; M-1 menor; O-1 a O-3 observaciones → P-demo-cliente-4 a -9 |
| 2026-10-12 | T5 (principal) | 60fc3a8 | 1/1 PASA | worktree-integrar: 623 tests OK; mismo fallo de `branch -d` (P-demo-cliente-10) |

## Pendientes que deja este plan
### Problemas
- P-demo-cliente-1 [importante] [despliegue] `media/` queda en el disco local del contenedor, que sin volumen se pierde en cada despliegue. Antes de producción hace falta un volumen o almacenamiento de objetos (`django-storages` ya está instalado y no se configura).
- P-demo-cliente-2 [observación] [robustez-panel] demo-cliente reescribió `apps/panel/management/commands/cargar_demo.py` y su test. robustez-panel T10, dueño de `apps/panel/**`, debe rebasear sobre `main` antes de empezar y no tocar esos archivos.
- P-demo-cliente-3 [observación] [despliegue] Una instancia alojada queda sin datos de demo, porque `cargar_demo` exige SQLite (decisión 2026-10-06). Mostrar datos en un alojamiento requiere una decisión nueva del usuario.
- P-demo-cliente-4 [importante] [despliegue] `config/settings/dev.py:12` aborta solo con `RAILWAY_ENVIRONMENT`; si Railway inyecta únicamente `RAILWAY_ENVIRONMENT_ID`/`_NAME`, `RAILWAY_PROJECT_ID` o `RAILWAY_SERVICE_ID`, un servicio con `DJANGO_ENV=development` arranca con DEBUG y expone la página técnica (auditor I-1, PLAUSIBLE). Comprobar con `railway ssh -- env | grep ^RAILWAY_` y ampliar la lista de variables.
- P-demo-cliente-5 [importante] [despliegue] `docs/despliegue.md` genera un dominio público sin `NUM_PROXIES`: tras el proxy todos comparten `REMOTE_ADDR` y 20 logins fallidos de un anónimo bloquean el ingreso de todos (auditor I-2). Agregar `NUM_PROXIES` a la tabla con su verificación, o advertir que la instancia no se comparte hasta resolverlo.
- P-demo-cliente-6 [menor] [despliegue] `CSRF_TRUSTED_ORIGINS` en `prod.py:21-24` acepta comodines y `http://`; `.env.example` y la guía lo llaman obligatorio cuando el propio dominio ya se acepta (auditor M-1). Rechazar orígenes no https o con `*` y corregir el texto.
- P-demo-cliente-7 [observación] [despliegue] `ALLOWED_HOSTS='*'` pasa el aborto de `prod.py` (auditor O-1); hoy sin escenario concreto.
- P-demo-cliente-8 [importante] [despliegue] Logos de clientes y portadas de servicios (`inicio.html:139`, `apps/web/views.py:73`) dan 404 en producción porque no hay ruta `/media/` (auditor O-2). No resolverlo con `WHITENOISE_ROOT = MEDIA_ROOT`, `static(MEDIA_URL)` ni `serve` sobre `MEDIA_ROOT`: publicaría fotos y planos sin autenticación. Vista pública acotada a esos campos o mover a `static/`.
- P-demo-cliente-9 [observación] [despliegue] `STORAGE_BACKEND` de `.env.example:16` no lo lee ningún setting (auditor O-3).
- P-demo-cliente-10 [menor] [hooks] `worktree-integrar.sh` corre `git branch -d` en la raíz; si la rama destino no es la del checkout de la raíz (p. ej. raíz en `main`, destino `plan/<slug>` en su worktree), falla con exit 1 tras un merge correcto. En demo-cliente se borraron T1, T2 y T3 con `-D` tras `merge-base --is-ancestor`.
- P-demo-cliente-11 [menor] [demo] Cada corrida de `cargar_demo` recrea los puntos demo y sus `qr_codigo`: un QR impreso de una corrida anterior deja de valer. Está en el `help` del comando, no en `docs/demo-cliente.md`.
- P-demo-cliente-12 [observación] [demo] No hay pantalla de historial propia (`/panel/informes/` vacío); la guía usa `/panel/visitas/` filtrado.
- P-demo-cliente-13 [observación] [despliegue] `railway.json` usa `"builder": "RAILPACK"` y `restartPolicyType: ON_FAILURE` sin validar contra Railway; confirmarlo en el primer despliegue.

### Decisiones
- 2026-10-12 — La demo es solo del sitio público y del panel; el escaneo de QR queda para cuando exista la app móvil — decisión del usuario — reemplaza a: (nada)
- 2026-10-12 — `cargar_demo` se reescribe en `apps/panel` y no en una app nueva, con aviso a robustez-panel — elección del usuario — reemplaza a: (nada)
- 2026-10-12 — Los datos demo se marcan en `notas` de cliente y sitio y con el sufijo ` (demo)` en productos, sin migraciones — evita tocar modelos de cuatro apps — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — La historia de 3 meses se crea por ORM con `full_clean()` y fechas retrotraídas, no por los servicios — los servicios rechazan más de `ATRASO_MAXIMO_HORAS` de atraso y sellan la hora actual — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — `demo.bat` usa una base aparte, `demo.sqlite3` — no mezcla la demo con la base de desarrollo — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — Alojamiento preparado para Railway (`railway.json`), porque el proyecto ya tiene el plugin de Railway; no se agrega Procfile — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — T3 va sola en la ola 2 y lleva `auditor-seguridad` aunque el nivel sea Chico — `config/` es del principal (nunca en paralelo) y CLAUDE.md § 6 exige el auditor sobre settings de producción — reemplaza a: (nada) — decidida por Claude, revisable

### Cierra
- cierra: P-sitio-publico-3 — `cargar_demo` carga `contenido_inicial` si no hay páginas de servicio (T1)

## Verificación de punta a punta (después de T5, antes del merge)
- El hook de cierre corre los criterios de las tareas hechas y los de cierre global. Después, `verificador` con TODO, y su informe va sin editar.
- Prueba manual del usuario:
  1. Correr `demo.bat` en la notebook.
  2. Abrir la URL impresa desde el teléfono.
  3. Entrar como `demo-admin` y recorrer el guion de `docs/demo-cliente.md`.
- Para tenerlo mañana: o el usuario decide hoy fusionar `plan/demo-cliente` en `main`, o la demo se corre desde `worktrees/demo-cliente`.
