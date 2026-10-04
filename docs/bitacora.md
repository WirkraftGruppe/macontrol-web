# Bitácora de MAControl

## Estado actual
Plan activo: (ninguno)

Planes activos (los hooks derivan el plan de la rama; la línea `Plan activo:` de arriba es el respaldo para la raíz):

| plan | rama | ola actual | pendiente inmediato | sesión |
|---|---|---|---|---|

Siguiente: plan de despliegue, con los diferidos a despliegue (entre ellos P-contrato-app-2 y -6: límite de cuerpo en el proxy, que cubra también los logins). Antes de la etapa Expo: P-contrato-app-9 (documentar 400 y 415 en el contrato).

Problemas abiertos: ver `py -3 .claude/hooks/pendientes.py` (cada plan los declara en `## Pendientes que deja este plan`; los anteriores están en `docs/planes/2026-10-03-pendientes-heredados.md`).

## Entradas (la más reciente arriba)

### 2026-10-04 — Fusión en `main` de `herramientas-plan`
Hecho:
- `main` recibió `plan/herramientas-plan` con `merge --no-ff` (`bb8b5bb`), con la verificación TODO en PASA 0/46 (verificador y verificador-b, HEAD `7b62861`).
- Las 3 decisiones del plan se copiaron al final de `docs/decisiones.md` (integración numerada, reemplaza a 2026-10-03; presupuesto `--subtarea`; exit 3 de `worktree-integrar.sh`).
- `docs/pendientes-snapshot.json` (`pendientes.py --json`) generado para el triage desde Claude Desktop; sin versionar (excluido en `.git/info/exclude`).
Pendiente: triage de pendientes; después, plan de despliegue.

### 2026-10-04 — Plan `herramientas-plan`: presupuesto por subtarea, integración segura, plantilla y agentes registrados
Hecho:
- Plan congelado (`605202d`) tras `juez-plan` con 2 bloqueantes corregidos: un grep con backticks dentro del código en línea y un presupuesto `--subtarea T5` que pasaba siempre.
- T1: `presupuesto.sh … --subtarea T<n>` mide los commits no-merge `T<n>:`/`T<n>b:`; el modo por rutas sigue.
- T2: `worktree-integrar.sh` busca el worktree en `git worktree list` y aborta con exit 3 si el cwd está dentro.
- T3: `juez-plan` y `verificador-b` no se registraban porque su `description` sin comillas tenía `: ` (YAML inválido); entrecomillado y `test_agentes.py`. Tras integrar, la sesión los listó como tipos. El veredicto del verificador se cuenta sobre la lista.
- T4: la plantilla usa `### T<n> — Integración (principal)` por ola y `--subtarea T<n>`; CLAUDE.md § 4 y § 5 actualizados.
- Verificación TODO (HEAD `7b62861`): PASA 0/46 en `verificador` y `verificador-b`.
- Cierra P-contrato-app-3, -4, -5, -12 y P-limites-ingreso-17; deja P-herramientas-plan-1 a -3 (observaciones).
Pendiente: merge a `main` (lo decide el usuario); al fusionar, copiar las 3 decisiones a `docs/decisiones.md`.

### 2026-10-04 — Fusión en `main` de `contrato-app`
Hecho:
- `main` recibió `plan/contrato-app` con `merge --no-ff` (`811d19c`), con la verificación TODO en PASA (verificador y verificador-b, HEAD `52fc995`).
- Antes del merge, por decisión del usuario:
  - cierra P-contrato-app-7 (no aplica: no hay datos previos ni producción; la consulta queda en el pendiente);
  - cierra P-contrato-app-10 (aceptado; la regla de "Puede tocar" no cambia);
  - etiqueta P-contrato-app-2 y -6 como "Diferido a despliegue" y P-contrato-app-9 como "Antes de la etapa Expo";
  - registra P-contrato-app-12 (el total del veredicto del verificador debe calcularse sobre la lista).
- Las 4 decisiones del plan se copiaron al final de `docs/decisiones.md`; la primera reemplaza el 409 de P-api-movil-15 por un 201 con visita nueva marcada.
Pendiente: plan de despliegue.

### 2026-10-04 — Plan `contrato-app`: evidencia de pendientes, atraso máximo, token JSON y contrato OpenAPI
Hecho:
- Plan congelado (`51e92b0`) tras `juez-plan` con 2 bloqueantes corregidos: presupuestos con rutas disjuntas (T3 lleva sus tests a `test_atraso.py`) y la integración del principal como subtarea T4.
- T1 (token y renovación solo JSON, 415), T2 (una pendiente no lleva evidencia; la app crea una visita nueva con incidencia y responde 201) y T3 (`realizada_en` con más de `ATRASO_MAXIMO_HORAS` da 400), cada una en su worktree, verificadas por `verificador` y `verificador-b` y auditadas.
- Por decisión del usuario sobre la auditoría de T3: un reintento tardío con el mismo `cliente_uuid` responde 409 (chequeo en `validate()`) y `ATRASO_MAXIMO_HORAS` queda acotado a 1..8760.
- `docs/api/openapi-v1.yaml` versionado (`cb31993`) y bullet "Contrato de la app" en `docs/01-modelo-y-arquitectura.md` §6.
- Verificación TODO (HEAD `52fc995`): PASA en los dos verificadores; auditor final sin hallazgos de seguridad nuevos.
- Pendientes nuevos: P-contrato-app-1 a -11 (los importantes: -2 y -6, límite de cuerpo en despliegue; -4, `presupuesto.sh` por subtarea; -9, documentación de 400/415 en el contrato).
- Incidente: `worktree-integrar.sh` no pudo borrar el worktree de T1 porque el shell del principal estaba dentro; se limpió a mano (carpeta vacía y `branch -d`) tras `git status` en raíz y worktrees.
Pendiente: merge a `main` (lo decide el usuario).

### 2026-10-04 — Fusión en `main` de `api-movil`
Hecho:
- El usuario aceptó la corrida TODO con FALLA 1/84 (presupuesto de T6, 712/650), aprobada por escrito. `main` recibió `plan/api-movil` con `merge --no-ff` (`a77bbe9`).
- Las 4 decisiones del plan se copiaron al final de `docs/decisiones.md`, más 4 decisiones nuevas del usuario:
  - un exceso de presupuesto se parte en T<n> y T<n>b, y la aprobación escrita queda solo para contrato modificado o criterio defectuoso;
  - P-api-movil-15: una pendiente no puede tener evidencia;
  - P-api-movil-16: `ATRASO_MAXIMO_HORAS = 168`;
  - P-api-movil-20: token solo JSON.
- A precisar al planificar P-api-movil-15: la decisión dice "409 y crea una nueva con `incidencia_asignacion`". Un 409 no crea nada, así que hay que elegir entre 409 sin crear y 201 con la visita nueva marcada.
- Pendientes abiertos: 63 (`py -3 .claude/hooks/pendientes.py`).
Pendiente: plan corto antes de producción (P-api-movil-15, -16 y -20).

### 2026-10-04 — Plan `api-movil`: API `/api/v1/` para la app de empleados
Hecho:
- Plan `docs/planes/2026-10-03-api-movil.md` (rama `plan/api-movil`), 7 subtareas en 5 olas, todas integradas:
  - T1: drf-spectacular con sidecar, errores `{detalle, campos}`, paginación, throttles y token normalizado.
  - T2: catálogo con ETag.
  - T3: resolver QR.
  - T4: `cliente_uuid`, `recibida_en`, `incidencia_asignacion`, `Foto.codigo`, validador de planilla y memoria de imágenes.
  - T5: servicio `registrar_visita_desde_app`.
  - T6: endpoints de visitas, historial y fotos.
  - T7: flujo de punta a punta y esquema.
- Verificación TODO (verificador y verificador-b coinciden, HEAD `f0aa3e9`): FALLA 1/84. La única FALLA es el presupuesto de T6 (712/650), aprobada por escrito por el usuario: los topes y cortes de subida se agregaron después de congelar el plan.
- Correcciones fuera de la regla de severidad, por decisión del usuario: el formato de error (T1), NaN, textos largos y tipos desconocidos en la planilla (T4), y el corte por `Content-Length` y los topes de texto (T6).
- Cierra P-pendientes-heredados-3, P-limites-ingreso-4 y -7. Deja P-api-movil-1 a -22: tres importantes (15, 16 y 20) para un plan corto antes de producción.
- Incidentes:
  - el cwd de la sesión quedó un rato dentro del worktree de T1 (sin daño, `git status` limpio);
  - la sesión se cortó con T4 a medio informar (recuperado del worktree);
  - un test viejo de rutas (`productos/tests/test_rutas.py`) lo ajustó el principal por decisión del usuario.
Pendiente: decisión del usuario sobre el merge a `main`; al fusionar, copiar las decisiones del plan a `docs/decisiones.md`.

### 2026-10-04 — Fusión en `main` de `limites-ingreso`
Hecho:
- El usuario aprobó la corrida TODO con FALLA 2/78, con el mismo criterio que `menores-abiertos`. La primera FALLA es el contrato modificado (`387c9a7`), que él aprobó. La segunda es el criterio de la ola 2 con un recuento que el propio plan cambia (33 → 27): un defecto del plan, no del código. El cierre global con 27 pasa. Queda escrito en el Registro.
- Se agregaron P-limites-ingreso-16 (regla (b) del juez: recuentos relativos o en el cierre global) y -17 (`worktree-integrar.sh` tiene que abortar si el cwd está dentro del worktree). Los tres importantes de red quedan como "Diferido a despliegue".
- `main` recibió `plan/limites-ingreso` con `merge --no-ff` (`3583a00`). Las 5 decisiones del plan se copiaron al final de `docs/decisiones.md`, que es la primera aplicación de la regla nueva de cierre.
- Pendientes abiertos: 44 (`py -3 .claude/hooks/pendientes.py`).
Pendiente: plan de API.

### 2026-10-03 — Plan `limites-ingreso`: límites por fallos, `'<commit_base>'` desde el Registro y pendientes por plan
Hecho:
- Plan `docs/planes/2026-10-03-limites-ingreso.md` (rama `plan/limites-ingreso`), 5 subtareas en 3 olas, todas integradas.
  - T1: settings `NUM_PROXIES` y cupos.
  - T2: `apps/accounts/limites.py` con tres baldes que cuentan solo fallos, en el panel, `/admin/login/` y el token; `ip_del_cliente`; `crear_usuario` normaliza; test del nonce.
  - T3: `'<commit_base>'` resuelto del Registro.
  - T4: `pendientes.py` y `contexto.sh`.
  - T5: plantilla, `CLAUDE.md` y agentes.
- Contrato modificado (`387c9a7`) por decisión del usuario: el token entra en los baldes de usuario, tras un hallazgo del auditor sobre T1. Los presupuestos pasaron a `'<commit_base>'`. Desde ahí `congelado.sh` sale con 1 y los verificadores dan FALLA formal con todos los criterios en PASA (T2 24/24 y 26/26, T5 10/10).
- La lista de problemas de la bitácora pasó a `docs/planes/2026-10-03-pendientes-heredados.md` (33). Este plan cierra 6 y deja 15 propios (3 importantes: throttles DRF sin /64, IPv4 mapeadas en `::/64`, `NUM_PROXIES` obligatorio en producción).
- Incidente: la integración de T1 no pudo borrar la carpeta del worktree porque la sesión tenía su cwd adentro. Quedó vacía y sin junction, y se limpió con `rmdir` y `git branch -d`.
Pendiente: verificación TODO, decisión del usuario sobre el merge y copiar las decisiones del plan a `decisiones.md` al fusionar.

### 2026-10-03 — Fusión en `main` de `menores-abiertos` y `autenticacion`
Hecho:
- `main` avanzó por fast-forward hasta `plan/menores-abiertos` y recibió `plan/autenticacion` con `merge --no-ff` (sin rebase, para conservar los hashes verificados). Los conflictos fueron solo de `docs/bitacora.md` y `docs/decisiones.md`.
- `menores-abiertos` entró con TODO en FALLA 5/49 (los 4 presupuestos y `congelado.sh`, todos por el contrato modificado `3478391`), aprobado por el usuario por escrito en el Registro del plan. Queda como decisión nueva en `docs/decisiones.md`.
- Los problemas de `paralelismo` que cerró `menores-abiertos` T3 (alcance por prefijo, merge que quedaba con tests en rojo, `rama_base` sin validar) se quitaron de la lista de `autenticacion` en vez de duplicarse.
- Se quitó la junction `venv` de `worktrees/autenticacion` con `cmd /c rmdir` y después el worktree.
Pendiente: plan `limites-ingreso`, en una sesión nueva sobre `main`.

### 2026-10-03 — Plan `autenticacion`: panel con rol administrador, API con JWT, admin solo superusuarios, CSP y LOGGING
Hecho:
- Plan `docs/planes/2026-10-03-autenticacion.md` (rama `plan/autenticacion`, worktree `worktrees/autenticacion`), 4 subtareas en 3 olas, todas integradas; verificación TODO en 6787a16: `verificador` 68/68 PASA, `verificador-b` sin FALLA. `auditor-seguridad` en cada subtarea.
- T1 (config): DRF solo JWT + `IsAuthenticated` + JSON; SimpleJWT 15 min / 7 días con rotación, blacklist y `CHECK_REVOKE_TOKEN`; django-csp 4 (`self` + nonce); `min_length` 12; `AdminSite` solo superusuarios (`config/admin.py`, `config/apps.py`); filtro `config/registro.py` recursivo por subcadena (incluye `telefono` y `contacto`), aplicado también a los loggers `django` y `django.server`; test de `check --deploy` que exige exactamente {W005, W021}.
- T2 (accounts): historial de `User` sin `password` ni `last_login` (y sin registro por login), `AdministradorRequeridoMixin`, `EsAdministrador`/`EsEmpleado`, comando `crear_usuario`.
- T4 (diseño/web): nonce en el `<style>` de `base.html`.
- T3 (panel/api): `/panel/ingresar/` y `/panel/salir/` (empleados rechazados en el formulario, límite por IP y por usuario), `/api/v1/auth/token/` y `/refresh/` con cupos propios, refresh rechazado tras cambio de contraseña, raíz de la API con rol; `test_rutas` invertido.
Incidentes:
- Otra sesión (`menores-abiertos`) cambió la raíz a su rama un segundo después de crear `plan/autenticacion`: los commits del plan cayeron en `plan/menores-abiertos`. Se pasaron por cherry-pick a `plan/autenticacion` (nuevo `commit_base` 6d22ff1) y `plan/menores-abiertos` volvió a cae1152 (con autorización del usuario). Desde ahí la sesión trabajó solo en `worktrees/autenticacion`.
- Integrar T2 falló al borrar el worktree ("Permission denied") porque el shell del principal estaba dentro: el merge sí quedó; se borró la carpeta vacía y la rama a mano (el caso de la decisión del 2026-10-02).
- La sesión se cortó con T2 a medias; se retomó el implementador sobre su worktree.
Pendiente: merge a `main` (decisión del usuario), plan `limites-ingreso`.

### 2026-10-03 — Cierre de los menores de fotos, worktree y plantilla (`menores-abiertos`)
Hecho:
- Plan `docs/planes/2026-10-03-menores-abiertos.md`: una ola, 4 subtareas en paralelo, integradas en `plan/menores-abiertos` (`88a449c`). El juez del plan marcó 3 bloqueantes, corregidos antes de congelar.
  - T1: `imagenes.py` acepta solo JPEG, PNG, WebP y MPO, con tope por formato (16 MP para JPEG progresivo o CMYK), `load()` fuera del `try` y `exif_transpose(in_place=True)`.
  - T2: `clean_imagen` en el inline y en `FotoAdmin` (error de formulario en vez de 500), y `programada_para` y `asignada_por` de solo lectura en una visita cerrada (N5).
  - T3: `worktree-integrar.sh` rechaza prefijos vacíos, compara por segmento, exige un worktree registrado y deshace el merge si fallan los tests o las migraciones; `worktree-crear.sh` valida `rama_base`.
  - T4: la plantilla lleva la integración en `### Trabajo del principal (integración de la ola N)` y aclara que el hook solo ejecuta `### T<n>` y el cierre global.
- El auditor de seguridad encontró en T1:
  - 1 bloqueante: un MPO daba `KeyError` y un 500;
  - 2 importantes: un `ValueError` de un `zTXt` enorme daba un 500, y la memoria seguía sin acotarse.
- El usuario decidió corregir los tres con el contrato ampliado (commit `3478391`, `docs(plan): … — modificado`). Re-auditoría: MPO y `ValueError` cerrados; la memoria sigue abierta como importante (ver Problemas abiertos).
- Verificación final TODO en `88a449c`: `verificador` y `verificador-b` dan FALLA en 5 criterios:
  - todos por el contrato modificado: los 4 de presupuesto y el `congelado.sh` del cierre global;
  - el resto pasa, con 105 tests de Django y 90 de hooks;
  - los presupuestos medidos a mano contra `b437ec1` entran todos: T1 133/160, T2 96/200, T3 122/220, T4 50/100.
- T1 quedó `en curso` en el Registro porque su criterio de presupuesto no pasa. T2 a T4 quedaron `hecha`.
- Incidente: el principal hizo `cd` a un worktree desde su shell persistente, y la decisión del 2026-10-02 lo prohíbe. Se corrigió en el momento, con `git status` en la raíz y en los worktrees: sin daño.
- El merge a `main` queda pendiente de la revisión manual del usuario.

### 2026-10-03 — Correcciones de la auditoría de visitas y bloqueo de la reversión desde el historial; fusión en main
Hecho:
- Plan `docs/planes/2026-10-03-visitas-auditoria.md` (una ola, 4 subtareas en paralelo; TODO PASA 48/48): `procesar_imagen` con tope de píxeles, `draft()`, comentario descartado y `ValidationError` para no imágenes; historial de `ProductoAplicado` (`visitas/0002`) y borrado del archivo al borrar o reemplazar una foto; `registrar_visita_realizada` con `select_for_update`, sin retroceder el proyecto ante visitas atrasadas y sin fechas futuras (tolerancia 10 min); admin con `CAMPOS_EVIDENCIA` de solo lectura en visitas no pendientes, sin borrado de visitas ni fotos y con fotos/productos bloqueados. T4 necesitó una ronda de corrección del principal (inline de fotos sin borrado y `visita` de solo lectura en los admins sueltos).
- La re-auditoría encontró un bloqueante nuevo (N2): revertir desde el historial de simple_history devolvía una visita realizada a pendiente y reactivaba QR regenerados. Por decisión del usuario, plan `docs/planes/2026-10-03-historial-revert.md` (3 subtareas; TODO PASA): `history_form_view` niega el POST en `VisitaAdmin` y `SitioAdmin`; un EXIF corrupto ya no da 500. Re-auditoría: N2 cerrado; un menor nuevo (ver Problemas abiertos).
- `juez-plan` corrido como agente Plan en los dos planes: 1 bloqueante en `visitas-auditoria` (test de doble registro que pasaba antes del cambio), corregido antes de congelar; 0 en `historial-revert`.
- `main` avanzó por fast-forward hasta `plan/historial-revert` (incluye `visitas`, `visitas-auditoria` e `historial-revert`; 95 tests).
Pendiente: menores de fotos y N5 (Problemas abiertos), después el plan de API/autenticación.

### 2026-10-03 — Registro de visitas (Visita, Foto, ProductoAplicado) y correcciones de Proyecto
Hecho (plan `docs/planes/2026-10-03-visitas.md`, rama `plan/visitas`, primer plan con olas y worktrees):
- Ola 1 en paralelo: T1 `Proyecto.__str__` tolera un sitio inexistente; T2 `suprimir_sitio` borra `Proyecto.history` del sitio; T3 modelos `Visita` (historial sin coordenadas ni `datos`, `esquema_planilla`, `clean()` de estado), `Foto` (uuid4, 1600 px, JPEG sin EXIF en `apps/visitas/imagenes.py`) y `ProductoAplicado`, con `visitas/0001_initial`.
- Ola 2 en paralelo: T4 `apps/visitas/services.py::registrar_visita_realizada` (valida origen, coordenadas, foto y motivo; copia el esquema; actualiza encargado y próxima visita en un `atomic`); T5 admin técnico con inlines y `estado`/`realizada_en`/`esquema_planilla` de solo lectura.
- Cada subtarea: PASA de `verificador` y `verificador-b`; TODO PASA 60/60 en `05b8cef` (77 tests). `juez-plan` (corrido como agente Plan, no está registrado como tipo) marcó 2 bloqueantes antes de congelar: presupuesto de T3 compartido con T5 y bloques `### Ola` que nadie ejecuta; se corrigieron moviendo el procesamiento de fotos a T3, el admin a T5 y los criterios de integración al cierre global.
- `auditor-seguridad`: 0 bloqueantes, 6 importantes, 8 menores (en Problemas abiertos).
- Incidente: un `cd` del principal al worktree de T3 desde el shell persistente (contra la decisión del 2026-10-02); se volvió a la raíz y `git status` de todos los árboles estaba limpio.
Pendiente: decidir el merge de `plan/visitas` a `main` y si los hallazgos importantes del auditor se corrigen antes, en un plan propio.

### 2026-10-02 — Paralelismo con multiagentes (worktrees, plan por rama, rutas por app)
Hecho:
- Plan `docs/planes/2026-10-02-paralelismo.md`, congelado en 2823e82 sobre la rama `plan/paralelismo`. El juez-plan encontró 4 bloqueantes y 1 observación; se corrigieron antes de congelar.
- Ola 1: T2, scripts `worktree-crear.sh` y `worktree-integrar.sh` (junction de `venv`, control de alcance, merge `--no-ff`). Se hizo inline porque era el bootstrap.
- Ola 2: T1 (el plan se deriva de la rama), T3 (`api_urls.py`/`panel_urls.py` por app, routers de una línea, `templates/panel/base.html`) y T4 (documentación). Las tres en paralelo, cada una en su worktree, integradas con los scripts.
- Ola 3: T5, prueba de fuego. Dos worktrees (clientes y productos), dos implementadores en paralelo, integración con exit 0 y salida literal en el Registro.
- pytest instalado en `py -3` por decisión del usuario.
- Cada subtarea dio PASA con verificador y verificador-b.
- auditor-seguridad: T1 sin hallazgos. En T2, 1 bloqueante (un renombre esquivaba el control de alcance), corregido en 1bf9878 con un test que se vio fallar antes del cambio. Los hallazgos menores quedan en Problemas abiertos.
- Incidente: en T3, `git worktree remove` dio "Permission denied" porque el shell del principal tenía el cwd dentro del worktree. Quedó anotado en el Registro y como decisión.
- Verificación final: TODO PASA 69/69 (verificador y verificador-b) en de25aee. El usuario aprobó el merge: `main` avanzó por fast-forward hasta 8ad718d y se borró la rama `plan/paralelismo`.

### 2026-10-02 — Acciones de Sitio por rol administrador (H1-a, H3-a)
Hecho:
- Plan `docs/planes/2026-10-02-acciones-sitio.md`, congelado en e6f47e4. El juez-plan dio 0 bloqueantes y 1 observación, que se aplicó.
- Decisiones del usuario: H1-a con la opción (b) y H3-a aprobado. Las dos quedaron en `docs/decisiones.md`.
- T1 (084e253):
  - "Suprimir datos (Ley 25.326)" es una acción separada, con confirmación, que borra el sitio y su historial e informa qué sitios tienen proyectos.
  - `regenerar_qr` exige rol administrador, pide confirmación, acepta como máximo 20 sitios y guarda el motivo en el historial con `update_fields`.
- El test de permisos se vio fallar antes del cambio. Los tests de confirmación del admin no se corrieron antes de implementar.
- verificador y verificador-b dieron PASA 18/18. Verificación final: TODO PASA 25/25 en 1d03e23, 54 tests.
- auditor-seguridad: H1-a, H3-a y H3-b CERRADOS. Hay un hallazgo nuevo menor, sobre el historial de Proyecto de un sitio suprimido (ver Problemas abiertos).

Incidente: el implementador corrió `ruff format` y tocó `apps/sitios/models.py`, que no tenía permitido. Lo restauró, y el diff del commit sobre ese archivo está vacío.

A medias: nada del plan.

### 2026-10-02 — Correcciones de la auditoría de dominio (H1–H4)
Hecho:
- Plan `docs/planes/2026-10-02-auditoria-dominio.md`, congelado en 4d8223d. El juez-plan dio 0 bloqueantes y 3 observaciones, aplicadas antes de congelar. Decisión de H1 en `docs/decisiones.md`.
- Una ola en paralelo con worktrees, integrada en 9b2115d:
  - T1: historial de Sitio sin contacto ni teléfono, `suprimir_sitio`, `regenerar_qr` y la acción del admin (1298e73).
  - T2: encargados validados en `save()` como empleados activos, solo al asignarlos (20456ae).
  - T3: dígito verificador del CUIT (07e536e).
- T1 y T2 vieron fallar sus tests antes de implementar; T3, uno de los dos.
- verificador y verificador-b dieron PASA en cada subtarea. Verificación final: TODO PASA 40/40 en 64fb555, con 47 tests.
- auditor-seguridad: H2 y H4 CERRADOS; H1 y H3 CERRADO PARCIAL, con dos hallazgos nuevos importantes (H1-a y H3-a) y varios menores (ver Problemas abiertos).

A medias: H1-a y H3-a, que esperan una decisión del usuario.

### 2026-10-02 — Modelos de dominio
Hecho:
- Commit aparte de los cambios a mano del usuario (bad5c80).
- Plan `docs/planes/2026-10-02-modelos-dominio.md`, congelado en ced3334. El juez-plan lo revisó en dos rondas: primero 3 bloqueantes, después 1. Todos se corrigieron antes de congelar.
- Ola 1, en paralelo con worktrees (junction `venv` → raíz, `venv` en `.git/info/exclude`), integrada en c4cb9cb:
  - T1: Cliente y Sitio con QR e historial; simple_history activado (d296031).
  - T2: TipoServicio, CampoPlanilla y fixture de 9 servicios (2215f95).
  - T3: Producto (a272650).
- Ola 2: T4, Proyecto con `estado_visita`, encargados empleados e historial (d126350).
- verificador y verificador-b dieron PASA en cada subtarea. Verificación final: TODO PASA 51/51 en 60d41f8, con 37 tests.
- auditor-seguridad: 0 bloqueantes, 1 importante (H1) y 3 menores, todos abiertos.

A medias:
- Los tests nuevos no se vieron fallar antes de implementar: los implementadores escribieron el test y el modelo juntos.
- El criterio literal `loaddata tipos_servicio` del pedido se reemplazó por un `[test]` que carga el fixture.

### 2026-10-01 — Espacios en ALLOWED_HOSTS
Hecho: plan `docs/planes/2026-10-01-hosts-espacios.md` (congelado en 734d06a, nivel chico, inline). `dev.py` y `prod.py` recortan espacios y descartan vacíos en `ALLOWED_HOSTS` (24e44a0); dos tests nuevos, vistos fallar antes del cambio. Verificación TODO PASA 12/12. El usuario decidió diferir la barrera por hosting y las IP privadas al plan de despliegue: hoy el proyecto es solo desarrollo. · A medias: nada.

### 2026-10-01 — Corrección de los hallazgos de la auditoría del esqueleto
Hecho: plan `docs/planes/2026-10-01-hallazgos-esqueleto.md` (congelado en 8f23dee; juez-plan en dos rondas, pasó de 7 bloqueantes a 1 y ese último se corrigió moviendo el trabajo del principal a T4). T1 barrera de hosts en `dev.py`, `.env.example` sin `DJANGO_ENV` fijo y HSTS de 3600 s sin subdominios ni preload (afdfc0e); T2 `app_name` en web, panel y api (a5f8b65); T3 fuentes Barlow en `static/fonts/` sin Google Fonts, y corrección del test de `data-tema` (a91fc9f); T4 decisiones y `docs/02-diseno.md` (338b81b, inline). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 43/43 en 1c43751. auditor-seguridad: hallazgos 2, 3 y 4 corregidos; el 1 corregido a medias (ver Problemas abiertos). · A medias: el hueco de la barrera, que depende de saber qué hosting se usa.

### 2026-10-01 — Arranque del repositorio y plan esqueleto
Hecho: pasos 2 a 5 de `docs/ARRANQUE.md`. Hooks y 16 skills copiados de TerritoryOS (tests de hooks: 70 OK), `git init`, venv con Python 3.13, `.gitattributes` (`*.sh` en LF), `images-for-content/` fuera de git. Plan `docs/planes/2026-10-01-esqueleto.md` (congelado en 37f1ec7, juez-plan en dos rondas: 4 bloqueantes corregidos antes de congelar): T1 base del proyecto y `accounts.User` con rol (fb08f0f), T2 diez apps y prefijos de URL con vistas provisorias (f9677fa), T3 `base.html` con tokens de ambos temas y logo (ced36a0). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 50/50 en b44c4bf; `check --deploy` con settings de producción sin avisos. auditor-seguridad: 0 bloqueantes, 4 hallazgos abiertos (ver Problemas abiertos). · A medias: nada del plan; los hallazgos del auditor quedan para decidir.

### 2026-09-29 — Base del repositorio
Hecho: se crea la carpeta del proyecto con el esquema de trabajo con agentes copiado de TerritoryOS y adaptado a un solo repositorio Django: `CLAUDE.md`, `.claude/agents/` (implementador, verificador, verificador-b, juez-plan, refutador, auditor-seguridad), `.claude/hooks/`, `.claude/skills/convenciones-proyecto/`, `docs/plantilla-plan.md`, `docs/decisiones.md`. Documentos fuente: `docs/00-contenido-fuente.md` (transcripción de la Carta de Servicios), `docs/01-modelo-y-arquitectura.md` (modelo de datos, roles, flujos, estructura), `docs/02-diseno.md` (tokens del tablero elegido, dirección A "Industrial certificada"). Diseños en el lienzo de claude.ai: https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk · A medias: no hay código; `git init` y primer commit pendientes.
