# Propuesta: organizar MAControl para trabajo en paralelo con multiagentes

Fecha: 2026-10-02. Estado: aprobada por el usuario en conversación; se ejecuta con el plan `paralelismo`.

## Diagnóstico

Hay dos paralelismos distintos y el esquema actual frena los dos:

1. **Dentro de una sesión** (varios implementadores a la vez). `CLAUDE.md` lo permite pero lo trata como excepción, y la estructura del código lo impide en la práctica: cualquier funcionalidad toca `apps/api`, `apps/panel`, `templates/` y `config/`, y las migraciones de una app son lineales.
2. **Entre sesiones** (dos o tres Claude Code abiertos, cada uno con su plan). La bitácora asume un solo `Plan activo:`, `contexto.sh` y `verificar_plan.py` leen esa línea de la raíz, y un worktree no tiene `venv/`, así que los comandos canónicos fallan dentro de él.

## A. Cada app de dominio es dueña de todo lo suyo

Estructura objetivo (nombres de archivo fijos, para que la propiedad sea verificable por `grep`):

```
apps/<app>/
  models.py · services.py · admin.py · migrations/
  serializers.py · api_views.py · api_urls.py          # lo que hoy iría a apps/api
  panel_views.py · panel_urls.py · panel_forms.py      # lo que hoy iría a apps/panel
  templates/<app>/panel/… · templates/<app>/pdf/…      # con APP_DIRS; nada en templates/<app>
  tests/test_models.py · test_services.py · test_api.py · test_panel.py
```

- `apps/api` conserva solo lo transversal: autenticación JWT, clases de permiso base, paginación, manejo de excepciones, y `urls.py` como router de una línea por app: `path("sitios/", include("apps.sitios.api_urls"))`.
- `apps/panel` conserva el layout del panel, el login, el tablero y el mapa agregado (que lee de varias apps), y `urls.py` como router de una línea por app.
- `apps/web` es el sitio público entero; se paraleliza por página (home, servicio, empresa), no por dominio.
- `apps/informes` sigue siendo transversal (certificado, PDF), pero expone sus propios `api_urls`/`panel_urls`.

### Tabla de propiedad

| Archivo o carpeta | Dueño | Cuándo se toca |
|---|---|---|
| `apps/<app>/**` | la subtarea de esa app | en su worktree |
| `config/settings/*.py`, `config/urls.py`, `requirements.txt`, `pyproject.toml` | principal | subtarea de integración, nunca en paralelo |
| `apps/api/urls.py`, `apps/panel/urls.py` | principal | al integrar cada ola |
| `apps/api/**` (salvo `urls.py`), `apps/panel/**` (salvo `urls.py`) | subtarea "transversal" del plan que lo necesite | una por plan |
| `templates/base.html`, `templates/panel/base.html`, `static/src/**`, `static/css/**` | subtarea "diseño" | los implementadores de dominio la consumen, no la editan |
| `docs/bitacora.md`, `docs/decisiones.md` | principal de cada sesión | solo al cierre, con rebase |
| `docs/planes/<plan>.md` | principal de ese plan | nunca otra sesión |

`juez-plan` (c) pasa a verificar contra esta tabla: una subtarea cuyo `Puede tocar` incluya un archivo de otro dueño es bloqueante.

## B. Migraciones por olas

Las migraciones son lineales por app y una FK a otra app exige que la migración de esa app exista en el worktree. El trabajo se ordena en **olas** sobre el grafo de dependencias:

```
Ola 1: accounts, clientes, servicios, productos    (sin FK entre sí)
Ola 2: sitios        → clientes
Ola 3: proyectos     → sitios, servicios, accounts
Ola 4: visitas       → proyectos, productos, accounts
Ola 5: informes      → visitas, clientes
```

Reglas:
- Dentro de una ola, todas las subtareas en paralelo, cada una con sus migraciones en su worktree.
- Al cerrar una ola, el principal integra (merge en la rama del plan, `makemigrations --check`, `test --keepdb`) y la ola siguiente ramifica desde ese commit.
- La plantilla de plan declara las olas; cada subtarea lleva `Ola: <n>`.
- Dos subtareas de la misma ola nunca crean migraciones en la misma app (ya era regla; ahora es consecuencia de la propiedad).

## C. Worktrees que funcionen en Windows

- `.claude/hooks/worktree-crear.sh <slug> <T<n>> [rama_base]`: `git worktree add worktrees/<slug>-T<n> -b <slug>-T<n> <rama_base>`, junction `venv` → `<raíz>/venv` (`cmd //c mklink /J`), y `manage.py check` como prueba de humo. SQLite se crea por worktree (`BASE_DIR`), así que los tests no se pisan.
- `.claude/hooks/worktree-integrar.sh <slug> <T<n>> <rama_destino>`: `cambios.sh` contra la rama destino, merge, `makemigrations --check`, `test --keepdb`, `git worktree remove`, borrado de la rama.
- `.gitignore`: `worktrees/` ya está; se agrega `venv` dentro de worktrees (la junction no es un archivo, pero `git status` de un worktree puede listarla).
- Regla nueva en `CLAUDE.md`: **worktree por defecto** para toda subtarea delegada que escriba código; inline solo para lo pasivo o lo que escribe un único archivo de documentación.

## D. Varias sesiones a la vez

1. **Una rama por plan**: `plan/<slug>`. Los worktrees de subtareas cuelgan de ella. `main` solo recibe planes con verificación `TODO` en PASA. Cada sesión abre Claude Code en el worktree de su plan (`worktrees/<slug>`), no en la raíz.
2. **El plan se deriva de la rama**: `contexto.sh` y `verificar_plan.py` buscan primero `git branch --show-current`; si es `plan/<slug>` o `<slug>-T<n>`, el plan es `docs/planes/*-<slug>.md`; si no, caen en `Plan activo:` de la bitácora (compatibilidad). Con tests nuevos en `test_contexto.py` y `test_verificar_plan.py`.
3. **Bitácora con varios planes**: "Estado actual" pasa a una tabla `| plan | rama | ola actual | pendiente inmediato | sesión |`; `Plan activo:` se conserva como línea de compatibilidad para la raíz.
4. **Comunicación entre sesiones**: solo por git y por el Registro de cada plan. Una sesión no edita el plan de otra ni su worktree. Las decisiones se agregan al final de `docs/decisiones.md` al cerrar cada plan, con rebase.
5. **Caché del hook** (`.claude/.ultimo-verificado`): vive por worktree (ya es relativo a la raíz del proceso), así que no se pisa.

## E. Qué cambia en la documentación

- `CLAUDE.md`: worktree por defecto; olas; ramas `plan/<slug>`; tabla de propiedad; integración por ola como trabajo del principal; sesiones paralelas.
- `docs/plantilla-plan.md`: sección `## Olas`; campo `Ola:` por subtarea; `Worktree: sí` por defecto; "Trabajo del principal" por ola.
- `.claude/skills/convenciones-proyecto/SKILL.md`: estructura nueva y tabla de propiedad.
- `.claude/agents/juez-plan.md`: (c) verifica contra la tabla de propiedad; (b) verifica que las olas respeten el grafo de FK.
- `.claude/agents/implementador.md`: trabaja siempre en el worktree que le indican; `cd` al worktree en cada comando.
- `docs/01-modelo-y-arquitectura.md` §5: estructura de apps actualizada.

## Alcance y expectativas

Cinco de los ocho planes del camino (API por app, panel por app, páginas del sitio, informes por tipo, despliegue por entorno) se vuelven paralelizables. Visitas e informes siguen siendo lineales por dependencia. El paralelismo compra tiempo de reloj en las olas anchas, no en las etapas encadenadas.
