# Plan: railway-iac — migraciones automáticas al desplegar y salida de `railway.json`

<!-- Nivel Completo. Rama plan/railway-iac, creada desde main 0e971fc.
Veredicto de juez-plan (1.ª pasada): 1 bloqueante y 3 observaciones, todos corregidos: T2 borraba
`railway.json` sin poder tocar `config/tests/test_despliegue.py`, que lo lee (pasa a T2 y prueba
`.railway/railway.ts`); se quitó el criterio sobre P-puesta-en-produccion-9 (ya no aparece en el archivo);
el sondeo que cuenta se lanza justo antes del push y el del apply va aparte. -->

- **slug**: `railway-iac`
- **fecha**: 2026-11-17
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): railway-iac`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: que cada despliegue del servicio `web` en Railway aplique `migrate` y `createcachetable` antes de servir tráfico, sin intervención manual, con la configuración del servicio declarada en `.railway/railway.ts` y no en `railway.json` (que Railway deja de leer el 2026-12-01).
- **fuera de alcance**:
  - Modelos, plantillas, estilos y contenido del sitio (la migración 0004 no cambia esquema ni datos).
  - Variables de entorno (el archivo nuevo las declara `managed: false`), dominio, Postgres y el volumen.
  - `config/settings/**`, `config/csp.py`, cabeceras de seguridad y URL públicas.
  - Integración continua o GitHub Actions para aplicar la configuración; staging u otros entornos.
  - `.claude/hooks/**`.
- **áreas**: infraestructura
- **seguridad**: sí — cambia cómo se configura y despliega producción (comando previo con acceso a la base, montaje del volumen) y hace un respaldo de la base con hashes de contraseña. Corre `auditor-seguridad` en T2 y sobre el plan entero antes del despliegue (T5), además de `verificador` y `verificador-b`.

## Contexto mínimo

- **Diagnóstico (CLI 5.74.1, 2026-11-17)**: `railway config migrate status` → "No services in production read Config as Code". El servicio `web` se creó el 2026-10-18 y no tiene ruta de Config File: el build todavía toma `buildCommand` y `startCommand` de `railway.json` (log: Railpack ejecuta `collectstatic` y arranca gunicorn, con la advertencia de deprecación), pero el `serviceManifest` del despliegue activo `7d40e0af` trae `preDeployCommand: null` y `restartPolicyMaxRetries: 10`, y `fileServiceManifest: {}`. La sección `deploy` del archivo nunca se aplicó; por eso el sitio dio 500 en los dos despliegues con migraciones (P-puesta-en-produccion-18, P-retoques-sitio-12).
- **Ensayo en seco** (archivo en el scratchpad, `railway config plan --file`): la salida de `railway config migrate --variables=unmanaged` desmonta el volumen (`volumeAttachments.web-media.mountPath "/data" → null`, "1 destructive change"); con `volume("web-media", { region: "us-east4-eqdc4a", sizeMB: 50000 })` montado en `/data` el plan queda en "0 to add, 2 to change, 0 to destroy": `buildCommand`, `preDeployCommand` y `startCommand` del servicio `web`, nada más.
- **Pre-deploy en Railway**: corre en un contenedor aparte, sin volúmenes, con las variables y la red privada del servicio; si falla, el despliegue no avanza (https://docs.railway.com/guides/pre-deploy-command).
- **Volumen**: `/data` montado (46 G, 2,1 M usados) y vacío salvo `lost+found`; `MEDIA_ROOT=/data/media` no existe todavía. No hay imágenes subidas que comprobar: el criterio comprueba que el volumen siga montado.
- **Formato**: TypeScript (`railway` 3.17.0 de npm, versión exacta, en `.railway/package.json`). Ver `### Decisiones del plan`.
- **Restricciones de producción** (del pedido): `railway status` = `macontrol-web` antes de todo comando; `config plan` con 0 a destruir; `config apply`, cortes y despliegues con autorización explícita y el plan a la vista; respaldo `dumpdata` fuera de carpetas temporales antes del primer cambio aplicado.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (documentación), T2 (configuración IaC), T3 (migración de prueba y sondeo), T4 (integración) | web (solo T3: 0004 sin operaciones de esquema) |
| 2 | T5 (corte y prueba en producción, principal) | ninguna |
| 3 | T6 (cierre, principal) | ninguna |

## Subtareas

### T1 — Reescribir `docs/despliegue.md` con el procedimiento vigente y el diagnóstico

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `docs/despliegue.md`
- **No puede tocar**: `docs/planes/`, `railway.json`, `.railway/`, `apps/`, `config/`, `herramientas/`, `docs/bitacora.md`, `docs/decisiones.md`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Variables de entorno
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - Procedimiento vigente: la configuración del servicio vive en `.railway/railway.ts` (`npm ci --prefix .railway` la primera vez); un cambio se aplica con `railway config plan` → revisión (0 a destruir) → `railway config apply`; `git push` a `main` despliega código, no configuración. Comando previo (`migrate --noinput && createcachetable`): dónde corre, que es idempotente y que si falla el despliegue no avanza y sigue el anterior.
  - Cómo correr comandos en producción (P-retoques-sitio-11): `railway status` primero, `cd /app`, intérprete `/app/.venv/bin/python`, `MSYS_NO_PATHCONV=1` en Git Bash.
  - Quitar lo obsoleto: la sección de `NUM_PROXIES` que dice que "lo confirma T7" y la fila que lo describe como si se usara (P-puesta-en-produccion-16), la URL `*.up.railway.app` como URL pública (es `https://www.macontrol.com.ar`).
  - Sección final `## Historia: Config as Code (hasta 2026-11)` con el diagnóstico de este plan (texto de `## Contexto mínimo`, con las salidas que entrega el principal en el prompt). Es el único lugar del archivo donde puede aparecer `railway.json`.
- **Criterios**:
  - `[cmd]` `test "$(awk '/^## /{h=($0 ~ /^## Historia/)} /railway\.json/ && !h' docs/despliegue.md | wc -l)" -eq 0`
  - `[grep-1]` `grep -n "^## Historia: Config as Code" docs/despliegue.md`
  - `[grep-1]` `grep -n "fileServiceManifest" docs/despliegue.md`
  - `[grep-1]` `grep -n "No services in production read Config as Code" docs/despliegue.md`
  - `[grep-1]` `grep -n "railway config apply" docs/despliegue.md`
  - `[grep-1]` `grep -n "railway config plan" docs/despliegue.md`
  - `[grep-1]` `grep -n "npm ci --prefix .railway" docs/despliegue.md`
  - `[grep-1]` `grep -n "/app/.venv/bin/python" docs/despliegue.md`
  - `[grep-1]` `grep -n "MSYS_NO_PATHCONV" docs/despliegue.md`
  - `[grep-1]` `grep -n "https://www.macontrol.com.ar" docs/despliegue.md`
  - `[grep-0]` `grep -n "lo confirma T7" docs/despliegue.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T1`

### T2 — Declarar el servicio `web` en `.railway/railway.ts` y retirar `railway.json`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.railway/railway.ts` (nuevo), `.railway/package.json` (nuevo), `.railway/package-lock.json` (nuevo), `.railway/README.md` (nuevo), `railway.json` (se borra), `config/tests/test_despliegue.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `apps/`, `config/settings/`, `config/csp.py`, `config/urls.py`, `herramientas/`, `requirements*.txt`, `pyproject.toml`, `.gitignore`
- **Skill a leer antes**: `railway:use-railway` → `references/iac.md` (§ Core rules, § Migrate legacy Config as Code)
- **Worktree**: sí (el worktree está bajo la raíz vinculada a `macontrol-web`; si `railway status` no lo confirma, parar y avisar, nunca `railway link`)
- **Ruta**: delegada
- **Presupuesto**: 200 líneas agregadas en `.railway/railway.ts`, `.railway/package.json`, `.railway/README.md` y `config/tests/test_despliegue.py` (el `package-lock.json` es generado y no cuenta)
- **Qué hacer**:
  - `.railway/railway.ts`: la salida de `railway config migrate --variables=unmanaged --show` (partial `web`), más `volume("web-media", { region: "us-east4-eqdc4a", sizeMB: 50000 })` montado con `volumeMounts: { "/data": media }` y agregado a `resources`. Comentarios en español. Sin UUID ni dominios `*.up.railway.app`. Sin variables (las sigue gestionando Railway).
  - `.railway/package.json` (`"private": true`, sin `scripts`) con `railway` en versión exacta, y su `package-lock.json` (`npm install --save-exact railway --prefix .railway`). `node_modules/` ya está en `.gitignore`.
  - `.railway/README.md` en español: qué es, `npm ci --prefix .railway`, `railway config plan` y `apply`, y que Railway no lee esta carpeta al desplegar.
  - `config/tests/test_despliegue.py` lee hoy `railway.json` (`RailwayTests.test_predeploy_es_un_solo_comando`): se reemplaza por `test_predeploy_declarado_en_iac` (lee `.railway/railway.ts`: una línea `preDeploy:` con un solo comando que contiene `migrate --noinput` y `createcachetable`), `test_volumen_montado_en_data` (`"/data"` en `volumeMounts`) y `test_railway_json_retirado` (el archivo no existe).
  - `git rm railway.json`. No ejecutar `railway config apply`, `migrate --apply`, `cutover` ni ningún comando que escriba en Railway.
- **Criterios**:
  - `[no-existe]` `railway.json`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue.RailwayTests.test_predeploy_declarado_en_iac --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue.RailwayTests.test_volumen_montado_en_data --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_despliegue.RailwayTests.test_railway_json_retirado --keepdb`
  - `[grep-0]` `grep -n "railway\.json" config/tests/test_despliegue.py`
  - `[existe]` `.railway/railway.ts`
  - `[existe]` `.railway/package-lock.json`
  - `[existe]` `.railway/README.md`
  - `[grep-1]` `grep -nF 'preDeploy: "python manage.py migrate --noinput && python manage.py createcachetable"' .railway/railway.ts`
  - `[grep-1]` `grep -nF 'start: "gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60"' .railway/railway.ts`
  - `[grep-1]` `grep -nF 'buildCommand: "python manage.py collectstatic --noinput"' .railway/railway.ts`
  - `[grep-1]` `grep -nF 'volumeMounts: { "/data": media }' .railway/railway.ts`
  - `[grep-1]` `grep -nF 'variables: { managed: false }' .railway/railway.ts`
  - `[grep-0]` `grep -nEi '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|up\.railway\.app' .railway/railway.ts`
  - `[grep-1]` `grep -nE '"railway": "[0-9]+\.[0-9]+\.[0-9]+"' .railway/package.json`
  - `[cmd]` `railway status --json | ./venv/Scripts/python.exe -c "import json,sys; sys.exit(json.load(sys.stdin)['name'] != 'macontrol-web')"`
  - `[cmd]` `rc=0; out=$(railway config plan --detailed-exit-code 2>&1) || rc=$?; [ $rc -eq 0 ] || { [ $rc -eq 2 ] && grep -q " 0 to destroy" <<<"$out" && ! grep -qi "destructive" <<<"$out"; }`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 .railway/railway.ts .railway/package.json .railway/README.md config/tests/test_despliegue.py`

### T3 — Migración de prueba sin efecto y herramienta de sondeo

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/web/migrations/0004_prueba_despliegue.py` (nuevo), `apps/web/tests/test_migraciones.py`, `apps/web/tests/test_sondeo.py` (nuevo), `herramientas/sondear.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `docs/`, `apps/web/models.py`, las migraciones 0001–0003, `config/`, `.railway/`, `railway.json`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Migrations (si no existe, `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones)
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - `0004_prueba_despliegue.py`: depende de `0003_datos_adjunto_a`; única operación `migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)`; docstring que explica que existe para comprobar el comando previo de Railway.
  - `herramientas/sondear.py URL [--cada 5] [--durante 600]`: solo biblioteca estándar; un GET cada `--cada` segundos durante `--durante`; no sigue redirecciones; una línea por sondeo a stdout, con flush, con el formato `AAAA-MM-DDTHH:MM:SS <código> <ms>` (error de conexión o tiempo agotado = código `000`); sale con 0 si hubo al menos un sondeo y todos dieron 200, si no con 1. `main(argv)` importable.
  - Tests: servidor HTTP local en un hilo (rutas que responden 200, 500 y 302) y una URL a un puerto cerrado; `--cada` y `--durante` en fracciones de segundo. Los de 0004 usan `MigrationExecutor`: migrar a 0003 y volver a 0004 sin error, y contar filas de `Configuracion`, `Servicio` y `ClienteDestacado` antes y después.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_migraciones.PruebaDespliegueTests.test_0004_es_reversible --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_migraciones.PruebaDespliegueTests.test_0004_no_cambia_filas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_sondeo.SondeoTests.test_sale_con_cero_si_todas_las_respuestas_son_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_sondeo.SondeoTests.test_sale_con_uno_si_aparece_un_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_sondeo.SondeoTests.test_no_sigue_redirecciones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_sondeo.SondeoTests.test_error_de_conexion_se_registra_como_000 --keepdb`
  - `[existe]` `apps/web/migrations/0004_prueba_despliegue.py`
  - `[grep-0]` `grep -nE "migrations\.(AddField|RemoveField|AlterField|RenameField|CreateModel|DeleteModel|RunSQL|AlterModelOptions)" apps/web/migrations/0004_prueba_despliegue.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check herramientas/sondear.py apps/web`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T3`

### T4 — Integración (principal)

- **Ola**: 1 (después de verificar T1, T2 y T3)
- **Depende de**: T1, T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/railway-iac` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh railway-iac T<n> plan/railway-iac <ruta>...` para T1 (`docs/despliegue.md`), T2 (`.railway railway.json config/tests/test_despliegue.py`) y T3 (`apps/web herramientas/sondear.py`).
  3. `npm ci --prefix .railway` en la raíz; `makemigrations --check --dry-run`.
  4. `verificador` y `verificador-b` sobre T1–T4; `auditor-seguridad` sobre T2. Con todo en PASA, verificación `TODO` previa al despliegue (T5 y T6 sin hacer).
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T4:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T4`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/railway-iac | grep -q "T1: integra railway-iac-T1"`
  - `[cmd]` `git log --oneline plan/railway-iac | grep -q "T2: integra railway-iac-T2"`
  - `[cmd]` `git log --oneline plan/railway-iac | grep -q "T3: integra railway-iac-T3"`

### T5 — Aplicar la configuración y comprobar un despliegue con migración (principal)

- **Ola**: 2
- **Depende de**: T4 y la verificación `TODO` previa en PASA
- **Pasos** (⚠ = autorización explícita del usuario con la salida a la vista; ninguno se encadena con el siguiente sin ella):
  1. `railway status` → `macontrol-web`.
  2. Respaldo: `MSYS_NO_PATHCONV=1 railway ssh -s web -- sh -c 'cd /app && /app/.venv/bin/python manage.py dumpdata --exclude sessions --exclude contenttypes --exclude auth.permission --exclude admin.logentry --indent 2'` a `~/respaldos/macontrol-web/railway-iac-predespliegue.json` (fuera del repositorio: lleva hashes de contraseña).
  3. `railway config migrate status`: si algún servicio volviera a leer Config as Code, ⚠ `railway config migrate cutover`.
  4. Sondeo del apply, en segundo plano y justo antes del paso 5: `./venv/Scripts/python.exe herramientas/sondear.py https://www.macontrol.com.ar/ --cada 5 --durante 900 > docs/evidencia/2026-11-17-railway-iac/sondeo-apply.txt`.
  5. `railway config plan` (debe ser exactamente los 2 cambios del ensayo, 0 a destruir; si propone borrar o recrear Postgres, el volumen o el servicio, parar y consultar) → ⚠ `railway config apply`. Si el apply dispara un despliegue, esperar SUCCESS (el comando previo corre sin migraciones pendientes).
  6. ⚠ El usuario decide el merge de `plan/railway-iac` en `main` y el push a `origin`. Inmediatamente antes del push, sondeo en segundo plano: `./venv/Scripts/python.exe herramientas/sondear.py https://www.macontrol.com.ar/ --cada 5 --durante 900 > docs/evidencia/2026-11-17-railway-iac/sondeo.txt`; si el despliegue no termina dentro de esa ventana, se repite el sondeo con otro despliegue de prueba en lugar de dar el criterio por cumplido; Railway despliega el borrado de `railway.json` y la 0004. Seguir ese despliegue por id hasta SUCCESS; guardar `railway logs --deployment <id> --lines 1000` en `docs/evidencia/2026-11-17-railway-iac/despliegue.log` (revisar que no tenga secretos antes del commit).
  7. Si la 0004 no se aplicó sola: no migrar a mano sin consultar. La alternativa con la misma garantía (`migrate && createcachetable && gunicorn` en `start` más `healthcheckPath: "/"`) es un cambio de contrato y la decide el usuario.
  8. Correr los criterios; commit `T5: evidencia del despliegue con migración automática`.
- **Presupuesto**: 1500 líneas agregadas (evidencia generada: sondeo y log)
- **Criterios**:
  - `[cmd]` `./venv/Scripts/python.exe -c "import json,os; d=json.load(open(os.path.expanduser('~/respaldos/macontrol-web/railway-iac-predespliegue.json'), encoding='utf-8')); assert len(d) > 0"`
  - `[cmd]` `test -z "$(git ls-tree main -- railway.json)"`
  - `[cmd]` `railway config migrate status 2>&1 | grep -q "No services in production read Config as Code"`   (guarda: ya pasa antes de T5; falla si un servicio vuelve a leer Config as Code)
  - `[cmd]` `railway config plan --detailed-exit-code`
  - `[grep-1]` `grep -n "Applying web.0004_prueba_despliegue" docs/evidencia/2026-11-17-railway-iac/despliegue.log`
  - `[cmd]` `MSYS_NO_PATHCONV=1 railway ssh -s web -- sh -c 'cd /app && /app/.venv/bin/python manage.py showmigrations web' 2>&1 | grep -q "\[X\] 0004_prueba_despliegue"`
  - `[cmd]` `test "$(grep -cE '^[^ ]+ 200 [0-9]+$' docs/evidencia/2026-11-17-railway-iac/sondeo.txt)" -ge 60`
  - `[grep-0]` `grep -nE '^[^ ]+ 5[0-9]{2} ' docs/evidencia/2026-11-17-railway-iac/sondeo.txt`
  - `[grep-0]` `grep -nE '^[^ ]+ 5[0-9]{2} ' docs/evidencia/2026-11-17-railway-iac/sondeo-apply.txt`
  - `[cmd]` `for p in / /empresa/ /contacto/ /servicio/control-murcielagos/ /favicon.ico /admin/login/; do test "$(curl -sS -o /dev/null -w '%{http_code}' "https://www.macontrol.com.ar$p")" = 200 || exit 1; done`
  - `[cmd]` `curl -fsSI https://www.macontrol.com.ar/ | tr -d '\r' | grep -qx "content-security-policy: default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"`
  - `[cmd]` `MSYS_NO_PATHCONV=1 railway ssh -s web -- sh -c 'grep -q " /data " /proc/mounts && test -d /data/lost+found'`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T5`

### T6 — Cierre (principal)

- **Ola**: 3
- **Depende de**: T5
- **Pasos**: bitácora (entrada y "Estado actual"), decisiones del plan copiadas a `docs/decisiones.md`, `### Cierra` y pendientes nuevos; commits `T6:` en `plan/railway-iac` y merge en `main` con autorización del usuario.
- **Presupuesto**: 120 líneas agregadas
- **Criterios**:
  - `[grep-1]` `grep -n "railway.ts" docs/decisiones.md`
  - `[grep-1]` `grep -n "railway-iac" docs/bitacora.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T6`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-11-17-railway-iac.md railway-iac`

## Registro de verificación

commit_base: 1c896e8

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-11-17 | T1, T2, T3 (verificador) | raíz efd9737; T1 e302018, T2 b2d49fe, T3 176b824 | FALLA solo por CONTRATO MODIFICADO (efd9737, aprobado por el usuario); 41/41 criterios en PASA | criterios corridos en cada worktree |
| 2026-11-17 | T1, T2, T3 (verificador-b) | ídem | FALLA solo por CONTRATO MODIFICADO; 38/38 criterios en PASA | |
| 2026-11-17 | T2 (auditor-seguridad) | b2d49fe | sin bloqueantes ni importantes; 4 observaciones | plan real: 0 to add, 2 to change, 0 to destroy |
| 2026-11-17 | T4 (principal) | c889dbb | 3 integraciones con `worktree-integrar.sh` (exit 0, 188 tests); `npm ci --prefix .railway`; `config plan` desde la raíz igual al ensayo | |
| 2026-11-17 | TODO previa al despliegue (T1–T4 + cierre global; verificador) | d270f3a | FALLA 49/50: solo `congelado.sh` por CONTRATO MODIFICADO (efd9737, aprobado por el usuario) | 188 tests OK, ruff OK |
| 2026-11-17 | T5 (verificador) | d6d2e37 | FALLA solo por CONTRATO MODIFICADO (efd9737, 31e3c0c, aprobados); 13/13 criterios en PASA | apply sin destruir; despliegue 9fa65c0d aplicó la 0004 en el preDeploy; sondeos sin 5xx (un 000 en el traspaso) |
| 2026-11-17 | T5 (verificador-b) | d6d2e37 | FALLA 12/13: el `ssh` de `/proc/mounts` no llegó a correr ("Railway can't verify your SSH key right now… temporary service issue") | el mismo criterio pasó en el verificador sobre el mismo HEAD |

### Decisiones del plan

- T2 — lenguaje del archivo de configuración — TypeScript (GA) o Python (beta) — TypeScript — Python está en beta y `config migrate --lang py` descarta `preDeploy`; Node 24 ya está en la máquina y el paquete queda aislado en `.railway/`, que Railway no lee al desplegar ni Railpack detecta — autónoma — reescribir en `.railway/railway.py` — decidida por Claude, revisable
- T2 — política de reinicio — los 3 reintentos de `railway.json` o el valor efectivo — el efectivo (ON_FAILURE, 10, por defecto de la plataforma, sin declararlo) — los 3 reintentos nunca se aplicaron; el pedido pide la política "actual" — autónoma — agregar el campo al servicio y aplicar — decidida por Claude, revisable
- T2 — variables — `managed` o `unmanaged` — `unmanaged` (`variables: { managed: false }`) — el pedido excluye cambiar variables; así IaC no las lee ni las toca — autónoma — pasar a `managed` con `preserve()` — decidida por Claude, revisable
- T5 — respaldo — dónde guardarlo — `~/respaldos/macontrol-web/` — fuera de temporales y del repositorio, porque lleva hashes de contraseña — autónoma — mover el archivo — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-railway-iac-1 [observación] Si un despliegue trae varias migraciones y falla una intermedia, las anteriores quedan aplicadas (una transacción por migración en Postgres) y el código viejo sigue sirviendo sobre ese esquema; lo mismo si `migrate` sale bien y falla `createcachetable`. Documentarlo en `docs/despliegue.md` y preferir migraciones compatibles con el código anterior (auditor-seguridad T2, O2).
- P-railway-iac-2 [observación] `domains: ["www.macontrol.com.ar"]` (`.railway/railway.ts`) hace al archivo dueño del dominio: quitarlo o cambiarlo y aplicar borraría el dominio personalizado. Revisar siempre que el plan diga 0 to destroy (auditor-seguridad T2, O3).
- P-railway-iac-4 [importante] Cada despliegue deja `/` sin responder unos segundos: con un volumen montado Railway no superpone despliegues (https://docs.railway.com/reference/healthchecks), y el servicio no tiene healthcheck. Plan propio: llevar media a un bucket (el volumen `web-media` está vacío al 2026-11-17) y agregar `healthcheck: "/"` con `healthcheck.railway.app` en `ALLOWED_HOSTS`.
- P-railway-iac-3 [observación] El comentario de `config/settings/prod.py:82` dice que `cache_sitio` se crea "en el preDeployCommand"; desde este plan es el `preDeploy` de `.railway/railway.ts` (auditor-seguridad T2).

### Decisiones

- 2026-11-17 — La configuración del servicio `web` vive en `.railway/railway.ts` (Infrastructure as Code en TypeScript, partial `web`, variables no gestionadas, volumen `web-media` declarado en `/data`) y se aplica con `railway config plan` → revisión → `railway config apply`; `railway.json` se retira y `migrate --noinput && createcachetable` corre como `preDeploy` del servicio — el `preDeployCommand` de `railway.json` nunca se aplicó (el servicio no leía Config as Code) y Railway deja de leer ese archivo el 2026-12-01 — reemplaza a: 2026-11-17 (el `preDeployCommand` pasa a un solo comando)
- 2026-11-17 — Los criterios del sondeo de T5 exigen ningún 5xx en lugar de todo 200, como el criterio de aceptación del pedido: con el volumen `web-media` montado Railway no superpone despliegues y hay unos segundos sin respuesta en cada traspaso (un `000` de 10,5 s a las 17:25:44 en el despliegue 9fa65c0d), que un healthcheck no evita — decisión del usuario ante la FALLA del sondeo — reemplaza a: (nada)
- 2026-11-17 — El `[grep-0]` de T2 sobre `config/tests/test_despliegue.py` escapa el punto (`railway\.json`): con `.` sin escapar coincidía con el nombre `test_railway_json_retirado` que exige el propio contrato — decisión del usuario ante la contradicción informada por el implementador de T2 — reemplaza a: (nada)

### Cierra

- cierra: P-puesta-en-produccion-18 — el comando previo vive en `.railway/railway.ts` y corrió en los despliegues 7794f003 y 9fa65c0d (este aplicó `web.0004_prueba_despliegue` sin intervención)
- cierra: P-retoques-sitio-12 — ídem; comprobado con la migración trivial 0004 (T5)
- cierra: P-retoques-sitio-10 — `railway.json` retirado de `main` (75cea6a); `railway config migrate status`: ningún servicio lee Config as Code
- cierra: P-retoques-sitio-11 — `docs/despliegue.md` § comandos en producción: `railway status` primero, `/app/.venv/bin/python`, `MSYS_NO_PATHCONV=1` en Git Bash
- cierra: P-puesta-en-produccion-16 — `docs/despliegue.md` describe `NUM_PROXIES=0` como exigida por `prod.py` pero sin uso con `IP_CLIENTE_CABECERA`
