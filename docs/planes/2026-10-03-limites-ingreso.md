# Plan: límites de ingreso, commit_base desde el Registro y pendientes por plan

- **slug**: `limites-ingreso`
- **fecha**: 2026-10-03
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): limites-ingreso`. El hash se anota en `## Registro de verificación`.
- **objetivo**: un atacante desde una IP ya no puede bloquear la cuenta de un administrador ni esquivar los cupos con variantes Unicode del usuario o con `X-Forwarded-For`; `/admin/login/` queda limitado igual que el panel; los presupuestos ya no dependen de `congelado.sh`; los problemas abiertos viven en el plan que los deja y se inyectan al entrar.
- **fuera de alcance**: caché compartida y `NUM_PROXIES` real del hosting (despliegue), 2FA, recuperación de contraseña, bloqueo permanente de cuentas, reescribir planes cerrados, el caso "contrato modificado" de `congelado.sh` en el hook (sigue bloqueando la corrida; P-pendientes-heredados-9 queda abierto), migrar usernames existentes.
- **áreas**: panel | api | dominio (accounts) | infraestructura
- **seguridad**: sí — login del panel, `/admin/login/`, `/api/v1/auth/token/`, derivación de la IP del cliente, settings de proxies, `crear_usuario`. Corre `auditor-seguridad` sobre T1 y T2.

## Contexto mínimo

- Hoy el panel (`apps/panel/views.py:20-55`) usa dos `SimpleRateThrottle` de DRF con scope `autenticacion` 10/min: cuentan todo POST, la clave de usuario es `strip().lower()` y la de IP coincide con la del token (`apps/api/views.py:14-17`). `/admin/login/` (`config/admin.py`) no tiene límite. Sin `NUM_PROXIES`, `get_ident` usa el `X-Forwarded-For` del cliente. `CACHES` no está definido (LocMem).
- Diseño elegido por el usuario: módulo propio `apps/accounts/limites.py` con caché de Django y tres baldes **que solo cuentan fallos**: por IP (`INTENTOS_FALLIDOS_POR_IP` en `VENTANA_MINUTOS`), por (usuario, IP) estricto (`FALLOS_POR_USUARIO_E_IP` en `VENTANA_MINUTOS`) y global por usuario, más alto y más largo (`FALLOS_POR_USUARIO` en `VENTANA_USUARIO_MINUTOS`). El panel y el admin comparten baldes; el token usa un throttle DRF con scope propio `token`. La IP sale de una única `ip_del_cliente(request)` (`apps/accounts/red.py`) con `NUM_PROXIES` (default 0, el mismo valor va a `REST_FRAMEWORK["NUM_PROXIES"]`).
- Normalización del usuario: `unicodedata.normalize("NFKC", s).strip().casefold()`, la misma en los cupos, en el formulario de login y en `crear_usuario`. Los usernames existentes no se migran (no hay producción). Uno guardado sin normalizar, como "Ana", deja de poder ingresar hasta que se lo renombre a mano. Queda como decisión del plan, sin test, porque un test de "no hay migración" pasaría sin hacer nada.
- commit_base: hoy los planes lo calculan con `"$(bash .claude/hooks/congelado.sh …)"`, que con un contrato modificado sale con 1 y vacío (P-pendientes-heredados-9). Nuevo: los criterios escriben `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> <rutas>`, con comillas porque sin ellas bash lo toma como redirección. `verificar_plan.py` reemplaza el marcador con la línea `commit_base:` del Registro antes de ejecutar. `presupuesto.sh`, si recibe el marcador literal, lo resuelve con `verificar_plan.py --commit-base`, que usa el mismo parser. El hash tiene que ser un commit con asunto `docs(plan): <slug>` (exacto o con ` — modificado: …`); si no, falla.
- Pendientes: cada plan los declara debajo del corte en `## Pendientes que deja este plan`. `pendientes.py` los consolida y `contexto.sh` los inyecta. La bitácora deja de llevar la lista.
- Este plan usaba para sus presupuestos la forma con `congelado.sh`; desde el contrato modificado (token en los baldes de usuario) usa `'<commit_base>'`, porque `congelado.sh` sale con 1 ante un contrato modificado. T2 se ramifica después de integrar T3, para que el marcador se resuelva en su worktree. Los greps de T5 buscan `'<commit_base` sin el `>` final, para que el hook no los reemplace.
- Propiedad: `config/settings/*.py` es del principal (T1 es su subtarea de integración, sola en `config/`). `config/admin.py`, `.claude/hooks/**`, `.claude/agents/**`, `CLAUDE.md` y `docs/plantilla-plan.md` no figuran en la tabla de propiedad: acá se asignan a un único dueño por subtarea.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (settings, sola: el dueño es el principal, "nunca en paralelo") | ninguna |
| 2 | T2, T3, T4 | ninguna (T2 no crea migraciones: `makemigrations --check` en criterios) |
| 3 | T5 | ninguna |

## Subtareas

### T1 — Settings de ingreso y de proxies

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `config/settings/base.py`, `.env.example`, `config/tests/test_ajustes_ingreso.py`
- **No puede tocar**: `docs/planes/`, `apps/`, `config/settings/dev.py`, `config/settings/prod.py`, `.claude/`
- **Skill a leer antes**: `.agents/skills/api-security-best-practices/SKILL.md` § rate limiting
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**: en `base.py`: `NUM_PROXIES` desde el entorno (entero ≥ 0, default 0; un valor inválido lanza `ImproperlyConfigured`) y `REST_FRAMEWORK["NUM_PROXIES"] = NUM_PROXIES`. Agregar `INTENTOS_FALLIDOS_POR_IP = 20`, `VENTANA_MINUTOS = 15`, `FALLOS_POR_USUARIO_E_IP = 5`, `FALLOS_POR_USUARIO = 50` y `VENTANA_USUARIO_MINUTOS = 60`. Agregar la tasa `"token": "10/min"` a `DEFAULT_THROTTLE_RATES` sin quitar todavía `autenticacion`, que la sigue usando el código hasta T2. `NUM_PROXIES=0` comentado en `.env.example`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_ingreso.AjustesIngresoTests.test_num_proxies_por_defecto_es_cero --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_ingreso.AjustesIngresoTests.test_drf_usa_el_mismo_num_proxies --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_ingreso.AjustesIngresoTests.test_cupos_de_ingreso_definidos --keepdb`
  - `[grep-1]` `grep -n "^NUM_PROXIES" config/settings/base.py`
  - `[grep-1]` `grep -n "NUM_PROXIES" .env.example`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 config/settings config/tests/test_ajustes_ingreso.py .env.example`

### Trabajo del principal (integración de la ola 1)

- **Pasos**:
  1. `cambios.sh . plan/limites-ingreso` de T1; `auditor-seguridad` sobre T1.
  2. `worktree-integrar.sh limites-ingreso T1 plan/limites-ingreso config/settings config/tests/test_ajustes_ingreso.py .env.example`.
  3. Crear los worktrees de T2, T3 y T4 desde `plan/limites-ingreso`.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/limites-ingreso | grep -q "T1: integra limites-ingreso-T1"`

### T3 — commit_base desde el Registro

- **Ola**: 2
- **Depende de**: T1 (solo por orden de olas; no usa sus archivos)
- **Puede tocar**: `.claude/hooks/presupuesto.sh`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/test_presupuesto.py`, `.claude/hooks/test_verificar_plan.py`
- **No puede tocar**: `docs/`, `CLAUDE.md`, `.claude/agents/`, `.claude/hooks/contexto.sh`, `.claude/hooks/congelado.sh`, `apps/`, `config/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos canónicos (tests de hooks con pytest)
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - En `verificar_plan.py`, agregar `commit_base_del_registro(texto_disco, raiz, slug)`. Lee la primera línea `commit_base: <hash>` debajo del corte, la resuelve con `git rev-parse --verify <hash>^{commit}` y exige que su asunto sea `docs(plan): <slug>` o empiece con `docs(plan): <slug> — `.
  - Antes de ejecutar cualquier criterio, reemplazar textualmente `<commit_base>` (con o sin comillas simples alrededor; queda el hash completo) en los comandos. Si la resolución falla, cada criterio que lleva el marcador es FALLA con el mensaje `commit_base sin resolver en <plan>: <motivo>`, sin ejecutarse; los demás se ejecutan.
  - CLI `--commit-base [plan]`: imprime el hash completo y sale con 0, o imprime el motivo a stderr y sale con 2. El plan se deriva como en el hook (`plan_de_rama` o `plan_activo`).
  - `presupuesto.sh`: si `<base>` es literalmente `<commit_base>`, lo resuelve con `verificar_plan.py --commit-base` (Python: `py -3`, si no `python3`, si no `python`). Si falla, sale con 2 y un mensaje claro.
  - Los tests nuevos son funciones pytest a nivel de módulo, no métodos de clase.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_marcador_commit_base_se_resuelve_del_registro -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_marcador_sin_registro_sale_con_dos -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_commit_base_faltante_falla_con_mensaje -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_marcador_se_reemplaza_antes_de_ejecutar -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_commit_base_que_no_es_docs_plan_se_rechaza -q`
  - `[cmd]` `py -3 -m pytest .claude/hooks -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 .claude/hooks/presupuesto.sh .claude/hooks/verificar_plan.py .claude/hooks/test_presupuesto.py .claude/hooks/test_verificar_plan.py`

### T4 — Pendientes por plan: pendientes.py y contexto.sh

- **Ola**: 2
- **Depende de**: T1 (solo por orden de olas; no usa sus archivos)
- **Puede tocar**: `.claude/hooks/pendientes.py`, `.claude/hooks/test_pendientes.py`, `.claude/hooks/contexto.sh`, `.claude/hooks/test_contexto.py`, `.claude/hooks/fixtures/contexto/`, `.claude/hooks/fixtures/pendientes/`
- **No puede tocar**: `docs/`, `CLAUDE.md`, `.claude/agents/`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/presupuesto.sh`, `apps/`, `config/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos canónicos
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - `pendientes.py [--raiz R] [--json]` recorre `docs/planes/AAAA-MM-DD-<slug>.md`. De cada archivo lee solo la sección `## Pendientes que deja este plan` que está debajo de `## Registro de verificación`, con tres subsecciones:
    - `### Problemas`: `- P-<slug>-<n> [bloqueante|importante|menor|observación] texto`; las líneas sangradas que siguen son parte del texto.
    - `### Decisiones`: formato de `decisiones.md`; se valida, no se imprime.
    - `### Cierra`: `- cierra: P-<slug>-<n> — cómo`.
  - Abiertos = declarados menos cerrados (un cierre puede venir de cualquier plan).
  - Avisos, sin fallar:
    - id duplicado;
    - `cierra:` de un id inexistente;
    - id cuyo slug no es el del archivo;
    - severidad desconocida;
    - línea con forma inválida.
  - Salida de texto: agrupada por severidad (bloqueante → observación), con el plan de origen; los avisos van al final.
  - `--json` imprime `{"abiertos": [{"id","severidad","plan","texto"}], "avisos": [str]}`, donde `plan` es el slug pelado (p. ej. `pendientes-heredados`, sin fecha ni `.md`).
  - Escribe siempre en UTF-8 (`sys.stdout.reconfigure(encoding="utf-8")`), porque la consola de Windows es cp1252 y los heredados traen "ａｄｍ".
  - Sale con 0 siempre, incluso sin `docs/planes/`.
  - Todos los tests nuevos, incluido el de `test_contexto.py`, son funciones pytest a nivel de módulo.
  - `contexto.sh` agrega `=== Pendientes abiertos (pendientes.py) ===` con la salida de `pendientes.py --raiz "$raiz"` (Python: `py -3`, si no `python3`), después de la bitácora; si no hay Python, imprime un aviso y sigue con exit 0.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_abiertos_son_abiertos_menos_cerrados -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_id_duplicado_avisa -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_cierre_de_id_inexistente_avisa -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_id_con_slug_ajeno_avisa -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_seccion_arriba_del_corte_se_ignora -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_sin_planes_sale_con_cero -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_json_trae_el_slug_del_plan -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_pendientes.py::test_salida_utf8_con_caracteres_fuera_de_cp1252 -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_contexto.py::test_contexto_inyecta_pendientes -q`
  - `[cmd]` `py -3 .claude/hooks/pendientes.py`
  - `[cmd]` `py -3 -m pytest .claude/hooks -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 .claude/hooks/pendientes.py .claude/hooks/test_pendientes.py .claude/hooks/contexto.sh .claude/hooks/test_contexto.py .claude/hooks/fixtures`

### T2 — Límites de ingreso del panel, el admin y el token

- **Ola**: 2
- **Depende de**: T1, T3 (T3 solo para que `'<commit_base>'` se resuelva en su worktree)
- **Puede tocar**: `apps/accounts/` (salvo `migrations/`), `apps/panel/views.py`, `apps/panel/forms.py`, `apps/panel/tests/test_acceso.py`, `apps/api/views.py`, `apps/api/tests/test_limites.py`, `apps/api/tests/test_auth.py`, `config/admin.py`, `apps/web/tests/test_csp.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `apps/api/urls.py`, `apps/panel/urls.py`, `templates/`, `.claude/`, migraciones
- **Skill a leer antes**: `.agents/skills/api-security-best-practices/SKILL.md` § rate limiting
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 650 líneas agregadas
- **Qué hacer**:
  - `apps/accounts/red.py`: `ip_del_cliente(request)`. Con `NUM_PROXIES == 0`, `REMOTE_ADDR`. Con N > 0, la N-ésima IP desde el final de `X-Forwarded-For` (misma semántica que DRF); si no hay suficientes, `REMOTE_ADDR`.
  - `apps/accounts/limites.py`:
    - `normalizar_usuario(texto)` (NFKC + strip + casefold);
    - los tres baldes de fallos con la caché de Django y ventana deslizante, leyendo los settings de T1;
    - un mixin para `LoginView` que, antes de autenticar, responde 429 si cualquier balde está lleno, sin evaluar la clave (no hay oráculo);
    - el mixin registra un fallo en los tres baldes ante un formulario inválido (incluido `sin_acceso`) y en un ingreso exitoso limpia solo el balde (usuario, IP).
  - Usar el mixin en `IngresarView` y en `SitioAdministracion.login` (mismos baldes). Quitar `LimiteIngresoPorIP` y `LimiteIngresoPorUsuario`.
  - `FormularioIngreso` normaliza el username antes de autenticar.
  - Token: throttle con scope `token` cuyo `get_ident` es `ip_del_cliente`. Además, el token consulta y registra los mismos baldes (usuario, IP) y por usuario que el panel, con `normalizar_usuario`: responde 429 sin evaluar la clave si alguno está lleno y registra un fallo cuando la autenticación falla (contrato modificado por hallazgo del auditor en T1).
  - `ThrottleRenovacion` también usa `ip_del_cliente`. Con IPv6, las claves de los baldes agrupan la dirección por /64.
  - `crear_usuario`:
    - normaliza el nombre;
    - `full_clean()`;
    - rechaza una variante Unicode de un usuario existente;
    - convierte el `IntegrityError` de la carrera en `CommandError`.
  - Test de que el nonce de CSP cambia entre dos respuestas.
  - Los tests existentes de `test_acceso.py` y `test_auth.py` se ajustan solo si dependen del 10/min viejo; ninguno se borra.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_ip_con_fallos_no_bloquea_contrasena_correcta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_umbral_de_fallos_por_ip_bloquea --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_variantes_unicode_del_usuario_comparten_cupo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_admin_login_tiene_el_mismo_limite --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_fallos_desde_otra_ip_no_bloquean_al_usuario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_cupo_global_por_usuario_bloquea_desde_cualquier_ip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_bloqueo_no_evalua_la_contrasena --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_red.IpDelClienteTests.test_sin_proxies_ignora_x_forwarded_for --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_red.IpDelClienteTests.test_con_un_proxy_toma_la_ultima_ip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_limites.LimitesTokenTests.test_cupo_del_token_es_independiente_del_panel --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_limites.LimitesTokenTests.test_token_ignora_x_forwarded_for_sin_proxies --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_limites.LimitesTokenTests.test_token_registra_fallos_en_los_baldes_de_usuario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_limites.LimitesPanelTests.test_ipv6_del_mismo_64_comparte_balde --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_crear_usuario.CrearUsuarioTests.test_normaliza_el_nombre --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_crear_usuario.CrearUsuarioTests.test_rechaza_variante_unicode_de_usuario_existente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_csp.CspTests.test_nonce_cambia_en_cada_respuesta --keepdb`
  - `[grep-1]` `grep -n "def ip_del_cliente" apps/accounts/red.py`
  - `[grep-0]` `grep -rn "LimiteIngresoPorIP\|LimiteIngresoPorUsuario\|scope = \"autenticacion\"" apps config --include=*.py`
  - `[grep-1]` `grep -n "ip_del_cliente" apps/api/views.py`
  - `[grep-1]` `grep -n "normalizar_usuario" apps/panel/forms.py`
  - `[grep-1]` `grep -n "normalizar_usuario" apps/accounts/management/commands/crear_usuario.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 apps/accounts apps/panel apps/api config/admin.py apps/web/tests/test_csp.py`

### Trabajo del principal (integración de la ola 2)

- **Pasos**:
  1. `bash .claude/hooks/cambios.sh . plan/limites-ingreso` por cada subtarea; `auditor-seguridad` sobre T2.
  2. Integrar T2 (`apps/accounts apps/panel apps/api config/admin.py apps/web/tests/test_csp.py`); T3 con `.claude/hooks/presupuesto.sh .claude/hooks/verificar_plan.py .claude/hooks/test_presupuesto.py .claude/hooks/test_verificar_plan.py`; T4 con `.claude/hooks/pendientes.py .claude/hooks/test_pendientes.py .claude/hooks/contexto.sh .claude/hooks/test_contexto.py .claude/hooks/fixtures`.
  3. Inline (un único archivo de documentación, propio de este principal): crear `docs/planes/2026-10-03-pendientes-heredados.md`, con encabezado, `## Registro de verificación` vacío y `## Pendientes que deja este plan` / `### Problemas`, copiando íntegro cada problema abierto de `docs/bitacora.md` § Problemas abiertos con la numeración del Anexo. Commit `registro: pendientes heredados de la bitácora`.
  4. En `config/settings/base.py`, quitar la tasa `autenticacion` (ya sin uso tras T2). Commit `T1: quita la tasa autenticacion`.
  5. Crear el worktree de T5 desde `plan/limites-ingreso`.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/limites-ingreso | grep -q "T2: integra limites-ingreso-T2"`
  - `[cmd]` `git log --oneline plan/limites-ingreso | grep -q "T4: integra limites-ingreso-T4"`
  - `[cmd]` `py -3 .claude/hooks/pendientes.py --json | py -3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(len(d['avisos']) != 0 or len([p for p in d['abiertos'] if p['plan']=='pendientes-heredados']) != 33)"`

### T5 — Documentos del flujo: plantilla, CLAUDE.md y agentes

- **Ola**: 3
- **Depende de**: T3, T4
- **Puede tocar**: `docs/plantilla-plan.md`, `CLAUDE.md`, `.claude/agents/implementador.md`, `.claude/agents/verificador.md`, `.claude/agents/verificador-b.md`
- **No puede tocar**: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `.claude/hooks/`, `apps/`, `config/`
- **Skill a leer antes**: `writing-for-agents` (skill del harness)
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - Plantilla:
    - el criterio de presupuesto pasa a `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> <rutas>`, con una nota de que `<commit_base>` queda literal y entre comillas (excepción a "todo lo que está entre <> se reemplaza");
    - debajo del corte, la sección `## Pendientes que deja este plan` con `### Problemas`, `### Decisiones` y `### Cierra`, con el formato de T4 y un ejemplo comentado.
  - `CLAUDE.md` § 4: el presupuesto con `'<commit_base>'` resuelto del Registro.
  - `CLAUDE.md` § Al entrar: el hook inyecta `pendientes.py`.
  - `CLAUDE.md` § Cierre de sesión:
    - los problemas y decisiones nuevos se escriben en la sección del plan;
    - al fusionar en `main` se copian solo las decisiones a `decisiones.md` (apéndice) y la bitácora recibe la entrada de sesión;
    - un problema se cierra con `cierra:` en el plan que lo resuelve, nunca editando el plan de origen.
  - `implementador.md`: propone pendientes en su informe, en una sección `Pendientes propuestos`, y sigue sin escribir en `docs/planes/`.
  - `verificador.md` y `verificador-b.md`: el veredicto incluye `Pendientes: <n> abiertos`, tomado de `py -3 .claude/hooks/pendientes.py --json`. Paso 0: `'<commit_base>'` se ejecuta tal cual porque `presupuesto.sh` lo resuelve.
- **Criterios**:
  - `[grep-1]` `grep -nF "presupuesto.sh . '<commit_base" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "^## Pendientes que deja este plan" docs/plantilla-plan.md`
  - `[grep-1]` `grep -nF "presupuesto.sh . '<commit_base" CLAUDE.md`
  - `[grep-1]` `grep -nF "cierra: P-" CLAUDE.md`
  - `[grep-1]` `grep -n "pendientes.py" CLAUDE.md`
  - `[grep-1]` `grep -n "Pendientes propuestos" .claude/agents/implementador.md`
  - `[grep-1]` `grep -n "Pendientes: <n> abiertos" .claude/agents/verificador.md`
  - `[grep-1]` `grep -n "Pendientes: <n> abiertos" .claude/agents/verificador-b.md`
  - `[cmd]` `py -3 -m pytest .claude/hooks -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 docs/plantilla-plan.md CLAUDE.md .claude/agents`

### Trabajo del principal (integración de la ola 3 y cierre)

- **Pasos**:
  1. `cambios.sh` de T5 e integrarla (`docs/plantilla-plan.md CLAUDE.md .claude/agents`).
  2. Debajo del corte de este plan, completar `## Pendientes que deja este plan`:
     - `### Cierra` con P-pendientes-heredados-16, -17, -18, -19, -22 y -24;
     - los problemas nuevos que deje la auditoría;
     - las decisiones: diseño de los tres baldes, normalización con casefold sin migrar usernames, commit_base del Registro y pendientes por plan.
  3. `docs/bitacora.md`: reemplazar la lista de "Problemas abiertos" por `Problemas abiertos: ver \`py -3 .claude/hooks/pendientes.py\``, y agregar la entrada de sesión.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/limites-ingreso | grep -q "T5: integra limites-ingreso-T5"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-03-limites-ingreso.md limites-ingreso`
- `[cmd]` `py -3 -m pytest .claude/hooks -q`
- `[cmd]` `py -3 .claude/hooks/pendientes.py`
- `[existe]` `docs/planes/2026-10-03-pendientes-heredados.md`
- `[grep-1]` `grep -n "pendientes.py" docs/bitacora.md`
- `[grep-0]` `grep -nE "^- \[(menor|importante)" docs/bitacora.md`
- `[grep-0]` `grep -n "\"autenticacion\"" config/settings/base.py`
- `[cmd]` `py -3 .claude/hooks/pendientes.py --json | py -3 -c "import json,sys; d=json.load(sys.stdin); a={p['id'] for p in d['abiertos']}; c={'P-pendientes-heredados-%d' % n for n in (16,17,18,19,22,24)}; sys.exit(len(d['avisos']) != 0 or bool(a & c) or len([p for p in d['abiertos'] if p['plan']=='pendientes-heredados']) != 27)"`

## Anexo: numeración de `pendientes-heredados` (texto íntegro desde la bitácora)

Cada id lleva el texto íntegro del punto de la bitácora; el de un subpunto se escribe con su encabezado ("Restos de `autenticacion`: …"). Severidad: la que está entre corchetes; los puntos sin corchete van como `[observación]`.

1 menor: paralelismo, junction · 2 menor: paralelismo, observaciones de T1 · 3 importante: memoria de `procesar_imagen` (completo) · 4 menor: JPEG progresivo > 16 MP y WebP > 8 MP · 5 menor: mensaje de `DecompressionBombError` · 6 menor: lienzo de libwebp · 7 menor: visitas, diferidos · 8 menor: visitas, observaciones · 9 menor: proceso, `congelado.sh` con contrato modificado · 10 menor: H1-b historial · 11 menor: columnas de `sitios/0002` · 12 menor: H2 `bulk_create` · 13 menor: H4 CUIT · 14 menor: `noqa E501` · 15 importante: barrera de `dev.py` (incluye la nota de IP privadas) · 16 importante: N1 · 17 importante: N2 · 18 importante: N3 · 19 menor: N4 · 20 menor: oráculo acotado · 21 importante: H2 `NUM_PROXIES`/`CACHES` · 22 menor: `crear_usuario` · 23 menor: `User.save` y `skip_history` · 24 menor: nonce de `test_csp` · 25 menor: `<style>` de `admin/change_list.html` · 26 menor: filtro de logging · 27 menor: tests de T2/T3 sin corrida roja · 28 observación: WeasyPrint · 29 observación: `test_base` `data-tema` · 30 observación: ejemplo de certificado · 31 observación: WhatsApp y horario · 32 observación: planillas `CampoPlanilla` · 33 observación: logo.

## Registro de verificación

commit_base: 071ecb5

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-03 | T1 | db4f2d5 | verificador: PASA 7/7 · verificador-b: PASA 7/7 | auditor-seguridad: sin bloqueantes; 3 importantes (default NUM_PROXIES=0 en prod, token fuera de los baldes de usuario, 10 IP o un /64 bloquean al administrador) y 3 menores (parser de NUM_PROXIES, dos fuentes de NUM_PROXIES, LocMem). Integrada en a9acc82. |
| 2026-10-03 | T4 | a8070b3 | verificador: PASA 12/12 · verificador-b: PASA 12/12 | Integrada en 9852214. |
| 2026-10-03 | T3 | 7c09024 | verificador: PASA 7/7 · verificador-b: PASA 7/7 | Integrada en ac5f7d0. |
| 2026-10-03 | T2 | edd90ae | verificador: 24/24 criterios PASA, veredicto FALLA solo por contrato MODIFICADO (387c9a7, decisión del usuario) · verificador-b: 26/26 PASA, mismo motivo | auditor-seguridad: sin bloqueantes; 2 importantes (throttles DRF sin agrupar IPv6 por /64; IPv4 mapeadas caen en ::/64) y 4 menores, pasan a pendientes del plan. Integrada en ff0bf06; tasa autenticacion quitada después. |
| 2026-10-03 | T5 | 0cf16e1 | verificador: 10/10 criterios PASA, veredicto FALLA solo por contrato MODIFICADO · verificador-b: igual | Integrada. |
| 2026-10-03 | TODO | 6123127 | verificador: FALLA 2/78 · verificador-b: FALLA 2/78 (mismos dos) | Contrato MODIFICADO (387c9a7, decisión del usuario). FALLA 1: `congelado.sh` exit 1 por ese motivo. FALLA 2: el criterio de integración de la ola 2 que exige 33 heredados abiertos; pasó al correrlo el principal en la ola 2 (33, sin avisos) y deja de pasar cuando este plan agrega sus `cierra:` (queda en 27, lo que exige el cierre global, que pasa). Los otros 76 en PASA. Pendientes: 42 abiertos. |

## Pendientes que deja este plan

### Problemas

- P-limites-ingreso-1 [importante] Auditoría de T2: `ThrottleToken` y `ThrottleRenovacion` (`apps/api/views.py`) identifican por la IP cruda de `ip_del_cliente`, sin el agrupado /64 de los baldes; con IPv6 se esquiva el 10/min del token rotando dentro del /64, y el token no usa el balde de fallos por IP (`solo_usuario=True`), así que es la puerta más débil para probar contra muchos usuarios a la vez. Corrección propuesta: `get_ident` devuelve `_grupo_de_ip(ip_del_cliente(request))` (función pública) y evaluar aplicar el balde por IP también al token. Cada usuario distinto crea claves de caché: con LocMem se pueden desalojar los baldes de la víctima.
- P-limites-ingreso-2 [importante] Auditoría de T2: las IPv4 mapeadas en IPv6 (`::ffff:a.b.c.d`) caen todas en el balde `::/64` (`apps/accounts/limites.py`, `_grupo_de_ip`): en un despliegue dual-stack, 20 fallos desde cualquier IPv4 bloquean el panel y el admin a todos, y 5 fallos bloquean a un usuario en todo internet. Corrección: desmapear con `direccion.ipv4_mapped` antes de agrupar, con test.
- P-limites-ingreso-3 [importante] Auditoría de T1: `NUM_PROXIES` tiene default 0 también en producción; detrás del proxy del hosting todas las peticiones comparten `REMOTE_ADDR` y 20 fallos anónimos dejan sin ingreso a todos (y el token comparte un 10/min). Hacer la variable obligatoria en `config/settings/prod.py` en el plan de despliegue (junto con P-pendientes-heredados-21).
- P-limites-ingreso-4 [menor] Auditoría de T2: en el JSON del token, un `username` entero (`12345678`) autentica igual (el `CharField` lo convierte) pero sus fallos van al balde de `""` (`apps/api/views.py`, `if not isinstance(usuario, str)`): duplica el cupo contra cuentas con usuario numérico. Usar la misma conversión que el serializer.
- P-limites-ingreso-5 [menor] Auditoría de T2: los baldes no son atómicos (leer, evaluar PBKDF2, `get`→`append`→`set`); con hilos o caché compartida una ráfaga concurrente supera el cupo. Pasa a importante cuando se resuelva `CACHES` compartida: reservar con `cache.add`/`incr` o un lock.
- P-limites-ingreso-6 [menor] Auditoría de T2: las claves de caché usan SHA-256 sin sal del usuario y de la IP; con una caché compartida legible se revierten por fuerza bruta. Usar `salted_hmac`.
- P-limites-ingreso-7 [menor] Auditoría de T2: el token no normaliza el usuario al autenticar (el panel sí): "Ana" con la clave correcta da 401 y cuenta como fallo de "ana". Normalizar en un `TokenObtainPairSerializer` propio (plan de API).
- P-limites-ingreso-8 [menor] Auditoría de T1: `leer_num_proxies` acepta `"1_0"` (10), dígitos no ASCII y números enormes; un valor mayor que los proxies reales permite falsear la IP con `X-Forwarded-For`. Aceptar solo `[0-9]` ASCII en un rango chico.
- P-limites-ingreso-9 [menor] Auditoría de T1: `NUM_PROXIES` vive en dos lugares (`settings.NUM_PROXIES`, que usa `ip_del_cliente`, y `REST_FRAMEWORK["NUM_PROXIES"]`); `override_settings(NUM_PROXIES=…)` en un test no cambia el de DRF. Hoy ningún throttle usa el `get_ident` de DRF, pero conviene una sola fuente.
- P-limites-ingreso-10 [menor] Auditoría de T1: 5 fallos desde cada una de 10 IP llenan el balde global de 50 y bloquean a un administrador 60 minutos, renovable (aceptado por diseño; decidir si un par usuario-IP con ingreso exitoso reciente queda exceptuado).
- P-limites-ingreso-11 [menor] `SitioAdministracion.login` (`config/admin.py`) copia `AdminSite.login` de Django 5.2 para usar el mixin de límites: revisarla al actualizar Django.
- P-limites-ingreso-12 [menor] `.claude/hooks/test_pendientes.py:99` emite `SyntaxWarning: invalid escape sequence '\W'` (`"C:\Windows"` sin `r`).
- P-limites-ingreso-13 [menor] `ruff format --check apps config` falla por `apps/visitas/tests/test_services.py:153` (preexistente; el de `apps/sitios/models.py:60` es P-pendientes-heredados-14).
- P-limites-ingreso-14 [observación] Los usernames existentes no se migran: un usuario guardado sin normalizar (mayúsculas, Unicode compatible) no puede ingresar hasta que se lo renombre a mano. Hoy no hay producción.
- P-limites-ingreso-15 [menor] Proceso: el contrato de este plan se modificó (387c9a7) para meter el token en los baldes; `congelado.sh` sale con 1, el hook de cierre no ejecuta sus criterios y el plan no puede llegar a TODO PASA (P-pendientes-heredados-9 sigue abierto). Los presupuestos sí se ejecutan gracias a `'<commit_base>'`.

### Decisiones

- 2026-10-03 — Los ingresos del panel, de `/admin/login/` y de `/api/v1/auth/token/` cuentan solo fallos en tres baldes de caché (IP 20 en 15 min, usuario e IP 5 en 15 min, usuario 50 en 60 min, IPv6 por /64), con 429 sin evaluar la clave si alguno está lleno; el token suma su throttle DRF `token` de 10/min por IP; la IP sale de `ip_del_cliente` con `NUM_PROXIES` (default 0) — N1-N4 de la re-auditoría de `autenticacion` y hallazgo del auditor sobre T1 — reemplaza a: los throttles `autenticacion` 10/min del plan `autenticacion`
- 2026-10-03 — El nombre de usuario se normaliza con NFKC + strip + casefold en el login, el token (baldes) y `crear_usuario`; los usernames existentes no se migran — N2 y restos de `autenticacion`; no hay producción — reemplaza a: (nada)
- 2026-10-03 — Los criterios de presupuesto escriben `'<commit_base>'` literal y entre comillas; `presupuesto.sh` y el hook lo resuelven desde la línea `commit_base:` del Registro, que debe ser un commit `docs(plan): <slug>` — los presupuestos con `"$(congelado.sh …)"` fallaban ante un contrato modificado — reemplaza a: la forma `"$(bash .claude/hooks/congelado.sh …)"`
- 2026-10-03 — Los problemas abiertos viven en la sección `## Pendientes que deja este plan` de cada plan (los de antes, en `pendientes-heredados`), se cierran con `cierra:` en el plan que los resuelve y se listan con `pendientes.py`; la bitácora ya no lleva la lista y a `decisiones.md` se copian solo las decisiones al fusionar en `main` — la lista de la bitácora crecía sin dueño — reemplaza a: la lista "Problemas abiertos" de `docs/bitacora.md`
- 2026-10-03 — El token entra a los baldes de usuario dentro de `limites-ingreso` con el contrato modificado (387c9a7), aunque el plan no pueda llegar a TODO PASA — decisión del usuario ante el hallazgo del auditor sobre T1 — reemplaza a: (nada)

### Cierra

- cierra: P-pendientes-heredados-16 — T2: los baldes cuentan solo fallos, con cupo estricto por (usuario, IP) y uno global por usuario más alto y largo.
- cierra: P-pendientes-heredados-17 — T2: `normalizar_usuario` (NFKC + strip + casefold) en la clave de los baldes y en el formulario.
- cierra: P-pendientes-heredados-18 — T2: `SitioAdministracion.login` usa el mismo mixin y los mismos baldes que el panel.
- cierra: P-pendientes-heredados-19 — T2: el token tiene su scope `token`; el panel ya no usa throttles DRF.
- cierra: P-pendientes-heredados-22 — T2: `crear_usuario` normaliza, hace `full_clean` y convierte la carrera en `CommandError`.
- cierra: P-pendientes-heredados-24 — T2: `CspTests.test_nonce_cambia_en_cada_respuesta`.
