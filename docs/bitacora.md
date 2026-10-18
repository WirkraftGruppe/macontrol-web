# Bitácora del sitio público de MAControl

## Estado actual
Plan activo: docs/planes/2026-10-18-puesta-en-produccion.md

Planes activos (los hooks derivan el plan de la rama; la línea `Plan activo:` de arriba es el respaldo para la raíz):

| plan | rama | ola actual | pendiente inmediato | sesión |
|---|---|---|---|---|
| web-independiente | main (fusionada f1cdc1b) | cerrado, TODO en PASA | — | sesión 2026-10-18 cerrada |
| puesta-en-produccion | plan/puesta-en-produccion | 1 (sin empezar) | ejecutar T1, T2 y T3 en paralelo (otra sesión) | plan commiteado a5d491f, commit_base a5d491f |

Problemas abiertos: ver `py -3 .claude/hooks/pendientes.py` (cada plan los declara en `## Pendientes que deja este plan`).

## Entradas (la más reciente arriba)

### 2026-10-18 — Fusión de `web-independiente` en `main` y plan `puesta-en-produccion`
Hecho:
- `plan/web-independiente` fusionada en `main` local (f1cdc1b), con la suite en verde (98 tests). `origin/main` traía la fusión de `demo-portatil`; sus agregados a la bitácora y las decisiones fueron a `docs/historico/`. Sin push.
- `origin` es compartido con el repo detach (ramas `separacion-web-*`): no se hace push de `main` desde acá. El plan nuevo renombra ese remoto a `detach` y usa un repositorio nuevo de GitHub.
- Plan Completo `puesta-en-produccion` (commit a5d491f) en tres olas: imágenes y media (T1), login del admin y tope de cuerpo (T2), logo y hero (T3), settings de producción (T5) y despliegue real en Railway (T7) con dominio `*.up.railway.app` y volumen. juez-plan: 7 bloqueantes corregidos; excepción de propiedad de T5 aprobada por el usuario.
- Decisiones del usuario: los datos de la empresa y las imágenes llegan más adelante; no se usan logos de clientes (el campo queda); el logo oficial es `static/img/logo.png`.
Pendiente: ejecutar el plan en otra sesión desde `plan/puesta-en-produccion`; en T7 el usuario crea el repositorio en GitHub y autoriza cada acción externa.

### 2026-10-18 — Plan `web-independiente`: el repositorio queda solo con el sitio público
Hecho:
- Plan Completo `web-independiente` (`seguridad: sí`, commit_base da3eef5), tres olas; cada subtarea con verificador, verificador-b y auditor-seguridad.
  - T1: se retiran el panel, la API, las apps de dominio y `accounts`; `auth.User`; `config/limites.py` y `config/red.py` conservan el límite de intentos del login del admin; requirements sin DRF, SimpleJWT, spectacular, simple-history, WeasyPrint, segno, pypdfium2, storages ni jsonschema.
  - T3: `apps/web` con modelo propio (`Servicio`, `ClienteDestacado`, `Configuracion` con datos legales), una sola migración, fixture con los 9 servicios de la Carta (textos idénticos al anterior) y `herramientas/humo_web.py` (runserver, `/` → 200).
  - T4: `CLAUDE.md`, `convenciones-proyecto`, `juez-plan`, `auditor-seguridad`, la plantilla de planes y `docs/01`, `docs/02`, despliegue y arranque reescritos para el sitio solo.
  - T6: admin en español con vista previa de servicios no publicados, imágenes sin EXIF y redes solo https.
- Los planes viejos (30) están en `docs/planes/historico/`; la bitácora y las decisiones del proyecto completo, en `docs/historico/`. `pendientes.py` lee solo `docs/planes/*.md`: los pendientes del sitio se re-declararon como `P-web-independiente-<n>`.
- Entorno: esta copia no traía `venv/`; se creó con Python 3.13 e `requirements.txt` del proyecto completo (sobran paquetes en el venv local, no en requirements). El `db.sqlite3` local, si existe, es de la estructura vieja: recrearlo con `migrate` y `loaddata contenido_inicial`.
- Verificación TODO: una FALLA (7 criterios) por `__pycache__` ignorados de las apps retiradas en la raíz; borrados, PASA 83/83 con verificador y verificador-b sobre 0bb077f. auditor-seguridad sin bloqueantes en T1, T3, T6 y la integración.
Pendiente: el merge a `main` lo decide el usuario; 21 pendientes P-web-independiente-1 a -21 (4 importantes: media en producción, NUM_PROXIES y caché, barrera de dev.py, borrado de imágenes reemplazadas).
