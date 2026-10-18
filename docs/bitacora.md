# Bitácora del sitio público de MAControl

## Estado actual
Plan activo: docs/planes/2026-10-17-web-independiente.md

Planes activos (los hooks derivan el plan de la rama; la línea `Plan activo:` de arriba es el respaldo para la raíz):

| plan | rama | ola actual | pendiente inmediato | sesión |
|---|---|---|---|---|
| web-independiente | plan/web-independiente | 3 (cierre) | verificación TODO; el usuario decide el merge a `main` | sesión 2026-10-18 |

Problemas abiertos: ver `py -3 .claude/hooks/pendientes.py` (cada plan los declara en `## Pendientes que deja este plan`).

## Entradas (la más reciente arriba)

### 2026-10-18 — Plan `web-independiente`: el repositorio queda solo con el sitio público
Hecho:
- Plan Completo `web-independiente` (`seguridad: sí`, commit_base da3eef5), tres olas; cada subtarea con verificador, verificador-b y auditor-seguridad.
  - T1: se retiran el panel, la API, las apps de dominio y `accounts`; `auth.User`; `config/limites.py` y `config/red.py` conservan el límite de intentos del login del admin; requirements sin DRF, SimpleJWT, spectacular, simple-history, WeasyPrint, segno, pypdfium2, storages ni jsonschema.
  - T3: `apps/web` con modelo propio (`Servicio`, `ClienteDestacado`, `Configuracion` con datos legales), una sola migración, fixture con los 9 servicios de la Carta (textos idénticos al anterior) y `herramientas/humo_web.py` (runserver, `/` → 200).
  - T4: `CLAUDE.md`, `convenciones-proyecto`, `juez-plan`, `auditor-seguridad`, la plantilla de planes y `docs/01`, `docs/02`, despliegue y arranque reescritos para el sitio solo.
  - T6: admin en español con vista previa de servicios no publicados, imágenes sin EXIF y redes solo https.
- Los planes viejos (30) están en `docs/planes/historico/`; la bitácora y las decisiones del proyecto completo, en `docs/historico/`. `pendientes.py` lee solo `docs/planes/*.md`: los pendientes del sitio se re-declararon como `P-web-independiente-<n>`.
- Entorno: esta copia no traía `venv/`; se creó con Python 3.13 e `requirements.txt` del proyecto completo (sobran paquetes en el venv local, no en requirements). El `db.sqlite3` local, si existe, es de la estructura vieja: recrearlo con `migrate` y `loaddata contenido_inicial`.
Pendiente: verificación TODO y la decisión del usuario sobre el merge a `main`.
