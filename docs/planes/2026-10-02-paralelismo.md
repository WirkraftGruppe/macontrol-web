# Plan: Paralelismo con multiagentes (worktrees, plan por rama, propiedad por app)

- **slug**: `paralelismo`
- **fecha**: 2026-10-02
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): paralelismo`; el hash se anota en `## Registro de verificación`.
- **objetivo**: varios implementadores (y varias sesiones) pueden trabajar a la vez, cada uno en su worktree con `venv`, con el plan derivado de la rama y con cada app de dominio dueña de sus rutas de API y de panel. Sin cambios de comportamiento en la aplicación.
- **fuera de alcance**:
  - Modelos, API real, panel real, autenticación, despliegue.
  - `presupuesto.sh`, `congelado.sh` y `cambios.sh` no se tocan: el control de alcance de la integración vive en `worktree-integrar.sh`.
  - `apps/accounts` no recibe `api_urls`/`panel_urls` (no figura en la lista del pedido).
- **áreas**: infraestructura | api (solo router) | panel (solo router)
- **seguridad**: sí — T1 cambia el origen del plan cuyos criterios ejecuta con `bash -c` el hook Stop (ahora derivado del nombre de la rama); T2 crea y borra junctions de directorio (riesgo de borrar el `venv` de la raíz a través de la junction). Corre `auditor-seguridad` al cierre.

## Contexto mínimo

- **Origen**: `docs/propuestas/2026-10-02-paralelismo.md` (aprobada), §A–§E.
- **Plan activo hoy**: `verificar_plan.py` lo lee de `Plan activo:` en `docs/bitacora.md` (`plan_activo()` L177-199, `validar_plan()` L154-174); `contexto.sh` con `grep -m1 '^Plan activo:'` (L24-25). Ninguno mira la rama.
- **Tests de hooks**: clases `unittest.TestCase` (70 tests). Por decisión del usuario se instala pytest en `py -3`; los tests nuevos son funciones de módulo estilo pytest. pytest corre también las clases existentes.
- **Rutas**: `apps/api/urls.py` solo tiene `path("", views.raiz, name="raiz")`; `apps/panel/urls.py` solo `path("", views.inicio, name="inicio")`. Las 7 apps de dominio tienen un `urls.py` con `urlpatterns = []` que nada incluye: se reemplazan por `api_urls.py`/`panel_urls.py` y se borran. `apps/web/tests/test_rutas.py` fija `/panel/`, `/api/v1/`, `api:raiz` y `panel:inicio`, y debe seguir pasando.
- **"Mover views.py a routers"**: `raiz` (raíz de la API) e `inicio` (tablero) son transversales y quedan en `apps/api/views.py` y `apps/panel/views.py`. Lo que cambia es `urls.py`, que pasa a ser un router de una línea por app (`path("<app>/", include("apps.<app>.api_urls"))`). Cada `api_urls`/`panel_urls` declara `app_name = "<app>"` (espacio de nombres anidado `api:sitios:…`, `panel:sitios:…`).
- **Templates**: `templates/` tiene `base.html` (bloque `tema`, por defecto `oscuro`) y `.gitkeep`; falta `templates/panel/base.html`.
- **Base de datos**: `config/settings/dev.py:46` usa SQLite en `BASE_DIR` sin `DATABASE_URL`; un worktree no tiene `.env`, así que usa su propia SQLite.

## Olas

```
Ola 1: T2 (scripts de worktree)        inline sobre plan/paralelismo: las herramientas todavía no existen
Ola 2: T1 · T3 · T4 en paralelo         cada una en su worktree (worktree-crear.sh / worktree-integrar.sh)
Ola 3: T5 (prueba de fuego)             el principal, con dos worktrees
```

## Subtareas

### T1 — Derivar el plan de la rama en verificar_plan.py y contexto.sh

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `.claude/hooks/verificar_plan.py`, `.claude/hooks/contexto.sh`, `.claude/hooks/test_verificar_plan.py`, `.claude/hooks/test_contexto.py`, `.claude/hooks/fixtures/`
- **No puede tocar**: `docs/planes/`, `docs/bitacora.md`, `.claude/hooks/presupuesto.sh`, `.claude/hooks/congelado.sh`, `.claude/hooks/cambios.sh`, `.claude/hooks/worktree-crear.sh`, `.claude/hooks/worktree-integrar.sh`, `.claude/hooks/test_worktree.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - Rama con `git -C <raíz> branch --show-current` (git por ruta absoluta, como ya hace el hook).
  - Si la rama es `plan/<slug>` o `<slug>-T<n>` (con `T<n>` = `T` + dígitos y sufijo opcional de una letra minúscula, p. ej. `T5a`): el slug debe cumplir `^[a-z0-9][a-z0-9-]*$`; el plan es el único `docs/planes/*-<slug>.md` (exactamente el slug tras el prefijo `AAAA-MM-DD-`), y pasa por `validar_plan()`.
  - Sin rama, slug inválido, cero o varias coincidencias, o validación fallida → se cae en `Plan activo:` de la bitácora (comportamiento actual), con aviso por stderr cuando el slug es inválido o hay varias coincidencias.
  - `contexto.sh`: la misma lógica en bash; el encabezado impreso dice el origen (`por rama` / `por bitácora`).
  - Actualizar el paso 3 del docstring de `verificar_plan.py` mencionando `plan/<slug>` y `<slug>-T<n>`.
  - Tests nuevos: funciones de módulo estilo pytest, con repo temporal (`git init -b main`, `git switch -c plan/demo`).
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_plan_se_deriva_de_rama_plan_slug -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_plan_se_deriva_de_rama_de_subtarea -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_rama_sin_plan_cae_en_bitacora -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_rama_con_slug_invalido_no_ejecuta_plan_ajeno -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_contexto.py::test_contexto_elige_plan_por_rama -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_contexto.py::test_contexto_sin_plan_de_rama_usa_bitacora -q`
  - `[grep-1]` `grep -n "branch --show-current" .claude/hooks/contexto.sh`
  - `[grep-1]` `grep -n "plan/<slug>" .claude/hooks/verificar_plan.py`
  - `[cmd]` `py -3 -m pytest .claude/hooks -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo)" 400 .claude/hooks/verificar_plan.py .claude/hooks/contexto.sh .claude/hooks/test_verificar_plan.py .claude/hooks/test_contexto.py .claude/hooks/fixtures`

### T2 — Scripts de worktree para Windows

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/worktree-crear.sh`, `.claude/hooks/worktree-integrar.sh`, `.claude/hooks/test_worktree.py`, `.gitignore`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/presupuesto.sh`, `.claude/hooks/congelado.sh`, `.claude/hooks/cambios.sh`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/contexto.sh`, `.claude/hooks/test_verificar_plan.py`, `.claude/hooks/test_contexto.py`, `.claude/hooks/test_presupuesto.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: no (bootstrap: las herramientas de worktree son esta subtarea)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  - `worktree-crear.sh <slug> <T<n>> [rama_base]`: valida slug (`^[a-z0-9][a-z0-9-]*$`) y `T<n>` (`^T[0-9]+[a-z]?$`); `git worktree add worktrees/<slug>-T<n> -b <slug>-T<n> <rama_base>` (por defecto la rama actual de la raíz); junction `venv` → `<raíz>/venv` con `cmd //c mklink /J` y rutas por `cygpath -w`; prueba de humo `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check` dentro del worktree. Humo fallido → exit ≠ 0 y el worktree queda para inspección. La raíz es `git rev-parse --show-toplevel` del directorio actual.
  - `worktree-integrar.sh <slug> <T<n>> <rama_destino> <ruta>...` (al menos una ruta):
    1. rechaza (exit ≠ 0, sin merge) si el worktree de la subtarea o el de destino tienen cambios sin commitear;
    2. imprime `bash .claude/hooks/cambios.sh <raíz> <rama_destino> --stat`;
    3. rechaza (exit 1, sin merge, worktree intacto) si `git diff --name-only <rama_destino>...<slug>-T<n>` contiene archivos fuera de los prefijos `<ruta>...`, listándolos;
    4. `git merge --no-ff -m "T<n>: integra <slug>-T<n>"` en el worktree donde está `<rama_destino>`;
    5. `makemigrations --check --dry-run` y `test --keepdb` con el prefijo canónico en ese worktree;
    6. borra la junction `venv` del worktree de la subtarea con `cmd //c rmdir` **antes** de `git worktree remove`;
    7. `git branch -d <slug>-T<n>`.
  - `.gitignore`: agregar la línea `venv` (sin barra) para que la junction también quede ignorada.
  - `test_worktree.py` (pytest, funciones de módulo): repo temporal con `manage.py` de juguete que sale con 0 y `venv` como junction al `venv` real del proyecto. El teardown borra primero las junctions (`os.rmdir`) y después el árbol. Ningún test puede borrar contenido del `venv` real.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_crear_hace_junction_de_venv -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_crear_corre_check_de_humo -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_mergea_rama_limpia_y_borra_worktree -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_rechaza_archivos_fuera_de_alcance -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_no_borra_el_venv_de_la_raiz -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_rechaza_worktree_con_cambios_sin_commitear -q`
  - `[grep-1]` `grep -n "mklink /J" .claude/hooks/worktree-crear.sh`
  - `[grep-1]` `grep -n "rmdir" .claude/hooks/worktree-integrar.sh`
  - `[grep-1]` `grep -nx "venv" .gitignore`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo)" 500 .claude/hooks/worktree-crear.sh .claude/hooks/worktree-integrar.sh .claude/hooks/test_worktree.py .gitignore`

### T3 — Rutas por app, routers de una línea y templates/panel/base.html

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/{sitios,clientes,servicios,proyectos,productos,visitas,informes,web}/api_urls.py`, `apps/{sitios,clientes,servicios,proyectos,productos,visitas,informes,web}/panel_urls.py`, `apps/{sitios,clientes,servicios,proyectos,productos,visitas,informes}/urls.py` (solo para borrarlos), `apps/api/urls.py`, `apps/api/tests/test_routers.py`, `apps/panel/urls.py`, `apps/panel/tests/test_routers.py`, `apps/panel/tests/test_base.py`, `templates/panel/base.html`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/web/urls.py`, `apps/web/tests/`, `templates/base.html`, `apps/api/views.py`, `apps/panel/views.py`, migraciones
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Estructura y § Mapa de rutas
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - Cada `api_urls.py` / `panel_urls.py`: docstring en español, `app_name = "<app>"`, `urlpatterns = []`.
  - `apps/api/urls.py` y `apps/panel/urls.py` conservan su ruta `""` y agregan una línea por app, en el orden de la lista: `path("<app>/", include("apps.<app>.api_urls"))` (o `panel_urls`).
  - Borrar los 7 `urls.py` vacíos de dominio; `apps/web/urls.py` queda.
  - `templates/panel/base.html`: `{% extends "base.html" %}` con `{% block tema %}claro{% endblock %}`.
  - Tests: los routers de api y panel incluyen exactamente un `URLResolver` por cada una de las 8 apps (por `urlconf_name`); `panel/base.html` rinde `<html lang="es" data-tema="claro">`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_routers.RoutersApiTests.test_api_incluye_un_router_por_app --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_routers.RoutersPanelTests.test_panel_incluye_un_router_por_app --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_base.PanelBaseTests.test_panel_base_usa_tema_claro --keepdb`
  - `[cmd]` `for a in sitios clientes servicios proyectos productos visitas informes web; do test -f apps/$a/api_urls.py && test -f apps/$a/panel_urls.py || exit 1; done`
  - `[existe]` `apps/sitios/api_urls.py`
  - `[existe]` `apps/sitios/panel_urls.py`
  - `[existe]` `apps/web/api_urls.py`
  - `[existe]` `apps/web/panel_urls.py`
  - `[cmd]` `for a in sitios clientes servicios proyectos productos visitas informes; do test ! -e apps/$a/urls.py || exit 1; done`
  - `[existe]` `apps/web/urls.py`
  - `[grep-1]` `grep -n 'include("apps.sitios.api_urls")' apps/api/urls.py`
  - `[grep-1]` `grep -n 'include("apps.sitios.panel_urls")' apps/panel/urls.py`
  - `[cmd]` `test "$(grep -c 'include("apps\.[a-z]*\.api_urls")' apps/api/urls.py)" -eq 8`
  - `[cmd]` `test "$(grep -c 'include("apps\.[a-z]*\.panel_urls")' apps/panel/urls.py)" -eq 8`
  - `[existe]` `templates/panel/base.html`
  - `[cmd]` `test "$(git ls-files templates | grep -v '\.gitkeep$' | sort | tr '\n' ' ')" = "templates/base.html templates/panel/base.html "`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web apps.api apps.panel --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo)" 300 'apps/*/api_urls.py' 'apps/*/panel_urls.py' 'apps/*/urls.py' apps/api/tests apps/panel/tests templates`

### T4 — Documentación del esquema de paralelismo (§E)

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `CLAUDE.md`, `docs/plantilla-plan.md`, `.claude/skills/convenciones-proyecto/SKILL.md`, `.claude/agents/juez-plan.md`, `.claude/agents/implementador.md`, `docs/01-modelo-y-arquitectura.md`
- **No puede tocar**: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `.claude/hooks/`, `apps/`, `templates/`
- **Skill a leer antes**: `writing-for-agents` (skill de usuario) y `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - `CLAUDE.md`: regla "worktree por defecto" para toda subtarea delegada que escriba código (inline solo lo pasivo o un único archivo de documentación); olas; ramas `plan/<slug>` y `<slug>-T<n>`; plan derivado de la rama con `Plan activo:` como respaldo; integración por ola con `.claude/hooks/worktree-crear.sh` / `worktree-integrar.sh` como trabajo del principal; sesiones paralelas (propuesta §D); `[test]` de hooks como `py -3 -m pytest <archivo>::<test> -q`.
  - `docs/plantilla-plan.md`: sección `## Olas`; campo `- **Ola**:` en cada subtarea; `Worktree: sí` por defecto; "Trabajo del principal" por ola; comentario del hook de cierre actualizado (plan por rama).
  - `convenciones-proyecto/SKILL.md`: estructura de apps de la propuesta §A; sección "Tabla de propiedad" (la de la propuesta); scripts de worktree con su uso; pytest en `py -3` para tests de hooks.
  - `juez-plan.md`: (c) verifica contra la tabla de propiedad de `convenciones-proyecto` (archivo de otro dueño en `Puede tocar` es bloqueante); (b) las olas respetan el grafo de FK de la propuesta §B.
  - `implementador.md`: trabaja siempre en el worktree que le indica el principal y hace `cd` al worktree en cada comando.
  - `docs/01-modelo-y-arquitectura.md` §5: árbol con `api_urls.py`/`panel_urls.py` por app y `templates/` con solo `base.html` y `panel/base.html`.
- **Criterios**:
  - `[grep-1]` `grep -n "worktree por defecto" CLAUDE.md`
  - `[grep-1]` `grep -n "plan/<slug>" CLAUDE.md`
  - `[grep-1]` `grep -n "worktree-integrar.sh" CLAUDE.md`
  - `[grep-1]` `grep -n "^## Olas" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "\*\*Ola\*\*:" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "Tabla de propiedad" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "worktree-crear.sh" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "tabla de propiedad" .claude/agents/juez-plan.md`
  - `[grep-1]` `grep -n "worktree" .claude/agents/implementador.md`
  - `[grep-1]` `grep -n "api_urls.py" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo)" 400 CLAUDE.md docs/plantilla-plan.md .claude/skills .claude/agents docs/01-modelo-y-arquitectura.md`

### T5 — Prueba de fuego: dos worktrees en paralelo, integrados con los scripts

- **Ola**: 3
- **Depende de**: T1, T3, T4
- **Puede tocar**: `apps/clientes/tests/test_rutas.py` (rama `paralelismo-T5a`), `apps/productos/tests/test_rutas.py` (rama `paralelismo-T5b`)
- **No puede tocar**: `docs/planes/`, todo lo demás
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí (dos)
- **Ruta**: el principal crea e integra; un implementador por worktree escribe el test · Evidencia: … · Commit: …
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**:
  1. Desde la raíz en `plan/paralelismo`: `bash .claude/hooks/worktree-crear.sh paralelismo T5a` y `bash .claude/hooks/worktree-crear.sh paralelismo T5b`.
  2. Un implementador por worktree agrega un test que comprueba que `api_urls` y `panel_urls` de su app tienen `app_name` igual al nombre de la app y `urlpatterns` vacío.
  3. Commit `T5: …` en cada rama.
  4. `bash .claude/hooks/worktree-integrar.sh paralelismo T5a plan/paralelismo apps/clientes` y `bash .claude/hooks/worktree-integrar.sh paralelismo T5b plan/paralelismo apps/productos`.
  5. Salida literal de los cuatro comandos en el Registro.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_rutas.RutasClientesTests.test_routers_de_clientes_estan_vacios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_rutas.RutasProductosTests.test_routers_de_productos_estan_vacios --keepdb`
  - `[grep-1]` `git log --oneline --merges | grep "T5a: integra paralelismo-T5a"`
  - `[grep-1]` `git log --oneline --merges | grep "T5b: integra paralelismo-T5b"`
  - `[cmd-falla]` `git rev-parse --verify --quiet refs/heads/paralelismo-T5a`
  - `[cmd-falla]` `git rev-parse --verify --quiet refs/heads/paralelismo-T5b`
  - `[cmd]` `test "$(git worktree list | wc -l)" -eq 1`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo)" 80 apps/clientes/tests/test_rutas.py apps/productos/tests/test_rutas.py`

## Trabajo del principal (integración)

- **Antes de la ola 1**: propuesta commiteada aparte; rama `plan/paralelismo`; pytest instalado en `py -3`; este plan → `juez-plan` → commit `docs(plan): paralelismo` → commit `registro:` con `commit_base` y `Plan activo:` en la bitácora.
- **Ola 1**: T2 inline sobre `plan/paralelismo` → commit `T2: …` → `verificador` y `verificador-b` sobre T2.
- **Ola 2**: `worktree-crear.sh paralelismo T1|T3|T4`; delegar en paralelo; commit `T<n>: …` en cada rama; `worktree-integrar.sh paralelismo T<n> plan/paralelismo <rutas de Puede tocar>`; `verificador` y `verificador-b` sobre T1, T3, T4.
- **Ola 3**: T5 según su subtarea.
- **Cierre**: bitácora con "Estado actual" como tabla `| plan | rama | ola actual | pendiente inmediato | sesión |` conservando la línea `Plan activo:`; decisiones nuevas; `auditor-seguridad` sobre T1 y T2; `verificador` TODO. El merge de `plan/paralelismo` a `main` lo decide el usuario después de TODO en PASA.
- **Criterios**: el hook de cierre solo ejecuta criterios de `### T<n>` y de cierre global, así que los del principal (bitácora y decisión de pytest) están en `## Criterios de cierre global`. La decisión se registra con el texto literal `- 2026-10-02 — Los tests de hooks se escriben con pytest`.

## Criterios de cierre global

- `[cmd]` `py -3 -m pytest .claude/hooks -q`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git worktree list | wc -l)" -eq 1`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-02-paralelismo.md paralelismo`
- `[grep-1]` `grep -n "^| plan | rama | ola actual | pendiente inmediato | sesión |" docs/bitacora.md`
- `[grep-1]` `grep -n "^Plan activo:" docs/bitacora.md`
- `[grep-1]` `grep -n "^- 2026-10-02 — Los tests de hooks se escriben con pytest" docs/decisiones.md`

## Registro de verificación

commit_base: 2823e82

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-02 | T2 | b988235 | PASA (verificador 10/10; verificador-b 10/10) | ruta: delegada, inline sobre plan/paralelismo (bootstrap) · commit T2: b988235 · fuera del contrato: `MSYS2_ARG_CONV_EXCL="*" cmd /c` en vez de `cmd //c` (Git Bash convertía `/J` en ruta) |
| 2026-10-02 | T3, T4 | 001e553 | PASA (verificador 30/30: T3 19, T4 11; verificador-b 32/32) | ruta: delegada en worktrees · T3: c2c7a90, merge 4b9ab09 · T4: 559dc87, merge 001e553 · incidente T3: `worktree-integrar.sh` exit 1 en `git worktree remove` por "Permission denied" (el shell del principal tenía el cwd dentro del worktree); merge, makemigrations y tests ya habían pasado y la junction estaba quitada; el principal borró el directorio vacío y la rama `paralelismo-T3` a mano. Regla aplicada desde entonces: el principal no hace `cd` a worktrees, usa `git -C` |
| 2026-10-02 | T1 | f0dd286 | PASA (verificador 10/10; verificador-b 10/10) | ruta: delegada en worktree · T1: 094fb8c, merge f0dd286 · skip preexistente: test de symlink en test_contexto.py |

### Prueba de fuego (T5): salida literal

Commits de las ramas: T5a 18ebe6d, T5b 7ee924a. Merges: `T5a: integra paralelismo-T5a`, `T5b: integra paralelismo-T5b`.

```
$ bash .claude/hooks/worktree-crear.sh paralelismo T5a
Preparing worktree (new branch 'paralelismo-T5a')
HEAD is now at 257a7fc registro: T1 de paralelismo hecha (PASA 10/10)
System check identified no issues (0 silenced).
worktree listo: C:/Users/Emanuel/Desktop/WEB/MaControl/worktrees/paralelismo-T5a (rama paralelismo-T5a)
exit: 0
```

```
$ bash .claude/hooks/worktree-crear.sh paralelismo T5b
Preparing worktree (new branch 'paralelismo-T5b')
HEAD is now at 257a7fc registro: T1 de paralelismo hecha (PASA 10/10)
System check identified no issues (0 silenced).
worktree listo: C:/Users/Emanuel/Desktop/WEB/MaControl/worktrees/paralelismo-T5b (rama paralelismo-T5b)
exit: 0
```

```
$ bash .claude/hooks/worktree-integrar.sh paralelismo T5a plan/paralelismo apps/clientes
=== worktree: C:/Users/Emanuel/Desktop/WEB/MaControl (rama: plan/paralelismo) ===
-- diff --stat contra plan/paralelismo (plan/paralelismo...HEAD) --
-- sin commitear (git status --porcelain) --
  (nada sin commitear)
-- diff --stat de lo sin commitear (contra HEAD) --

=== worktree: C:/Users/Emanuel/Desktop/WEB/MaControl/worktrees/paralelismo-T5a (rama: paralelismo-T5a) ===
-- diff --stat contra plan/paralelismo (plan/paralelismo...HEAD) --
 apps/clientes/tests/test_rutas.py | 22 ++++++++++++++++++++++
 1 file changed, 22 insertions(+)
-- sin commitear (git status --porcelain) --
  (nada sin commitear)
-- diff --stat de lo sin commitear (contra HEAD) --

=== worktree: C:/Users/Emanuel/Desktop/WEB/MaControl/worktrees/paralelismo-T5b (rama: paralelismo-T5b) ===
-- diff --stat contra plan/paralelismo (plan/paralelismo...HEAD) --
 apps/productos/tests/test_rutas.py | 17 +++++++++++++++++
 1 file changed, 17 insertions(+)
-- sin commitear (git status --porcelain) --
  (nada sin commitear)
-- diff --stat de lo sin commitear (contra HEAD) --

Merge made by the 'ort' strategy.
 apps/clientes/tests/test_rutas.py | 22 ++++++++++++++++++++++
 1 file changed, 22 insertions(+)
 create mode 100644 apps/clientes/tests/test_rutas.py
No changes detected
Using existing test database for alias 'default'...
..........................................................
----------------------------------------------------------------------
Ran 58 tests in 6.793s

OK
Preserving test database for alias 'default'...
Found 58 test(s).
System check identified no issues (0 silenced).
Deleted branch paralelismo-T5a (was 18ebe6d).
integrada paralelismo-T5a en plan/paralelismo
exit: 0
```

```
$ bash .claude/hooks/worktree-integrar.sh paralelismo T5b plan/paralelismo apps/productos
=== worktree: C:/Users/Emanuel/Desktop/WEB/MaControl (rama: plan/paralelismo) ===
-- diff --stat contra plan/paralelismo (plan/paralelismo...HEAD) --
-- sin commitear (git status --porcelain) --
  (nada sin commitear)
-- diff --stat de lo sin commitear (contra HEAD) --

=== worktree: C:/Users/Emanuel/Desktop/WEB/MaControl/worktrees/paralelismo-T5b (rama: paralelismo-T5b) ===
-- diff --stat contra plan/paralelismo (plan/paralelismo...HEAD) --
 apps/productos/tests/test_rutas.py | 17 +++++++++++++++++
 1 file changed, 17 insertions(+)
-- sin commitear (git status --porcelain) --
  (nada sin commitear)
-- diff --stat de lo sin commitear (contra HEAD) --

Merge made by the 'ort' strategy.
 apps/productos/tests/test_rutas.py | 17 +++++++++++++++++
 1 file changed, 17 insertions(+)
 create mode 100644 apps/productos/tests/test_rutas.py
No changes detected
Using existing test database for alias 'default'...
...........................................................
----------------------------------------------------------------------
Ran 59 tests in 6.697s

OK
Preserving test database for alias 'default'...
Found 59 test(s).
System check identified no issues (0 silenced).
Deleted branch paralelismo-T5b (was 7ee924a).
integrada paralelismo-T5b en plan/paralelismo
exit: 0
```
