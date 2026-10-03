# Bitácora de MAControl

## Estado actual
Plan activo: docs/planes/2026-10-03-visitas.md (TODO PASA 60/60 en `plan/visitas`, sin fusionar en `main`)

Planes activos (los hooks derivan el plan de la rama; la línea `Plan activo:` de arriba es el respaldo para la raíz):

| plan | rama | ola actual | pendiente inmediato | sesión |
|---|---|---|---|---|
| `visitas` | `plan/visitas` | cerrado (olas 1 y 2 integradas) | decidir merge a `main` y qué hallazgos del auditor se corrigen (ver abajo) | 2026-10-03 |

Después: plan de corrección de los hallazgos importantes del auditor de `visitas` (o directo a la API, si se difieren), y después el plan de API/autenticación.

Problemas abiertos:
- [menor, abierto, decisión del usuario] Auditoría de `paralelismo` sobre `worktree-integrar.sh`:
  - el control de alcance compara prefijos de texto, no segmentos de ruta: `apps/clientes` acepta `apps/clientes_v2/…`, y un argumento vacío (`""`) acepta cualquier archivo. Propuesta: rechazar prefijos vacíos y comparar `"$p"|"$p"/*`;
  - si fallan los tests o `makemigrations` después del merge, el commit de merge queda en el destino y el mensaje no lo dice;
  - `rama_base` de `worktree-crear.sh` no se valida (un valor que empiece con `-` se toma como opción), e integrar no comprueba que la ruta sea un worktree registrado;
  - si la prueba de humo falla, la junction queda viva en `worktrees/`: limpiar con `cmd /c rmdir <venv>` y después `git worktree remove`; nunca `Remove-Item -Recurse` de PowerShell 5.1, que sigue la junction y vacía el venv real.
  - Observaciones de T1: `RE_FECHA_SLUG` usa `\d` (acepta dígitos Unicode, `contexto.sh` usa `[0-9]`); `plan_de_rama` vuelve a la bitácora sin avisar cuando `validar_plan` rechaza el candidato; una rama con el slug de un plan viejo hace verificar ese plan congelado (el mismo riesgo que ya existía con `Plan activo:`).
- [importante, abierto, decisión del usuario] Auditoría de `visitas` (0 bloqueantes hoy; el 1 pasa a bloqueante cuando la API reciba fotos):
  1. Bomba de descompresión: `apps/visitas/imagenes.py` decodifica la imagen entera antes de reducir (un JPEG de 13000×13000 de 2,6 MB lleva el pico a 1,4 GB). Propuesta: tope de píxeles, `draft()` antes de `exif_transpose`, `DecompressionBombWarning` como error y test.
  2. El admin permite cambiar coordenadas, `datos`, `empleado`, `origen` y `proyecto` de una visita realizada; coordenadas y `datos` no tienen historial, así que no queda rastro. Propuesta: `get_readonly_fields` con todos los campos de evidencia cuando `estado != pendiente`.
  3. Fotos y productos de una visita realizada se cambian, borran o mueven desde el admin sin historial. Propuesta: permisos de cambio/alta/baja en `False` si la visita no está pendiente; `HistoricalRecords` en `ProductoAplicado`.
  4. Doble registro: `registrar_visita_realizada` comprueba `pendiente` sobre el objeto en memoria y sin bloqueo; un reintento o una instancia vieja vuelve a registrar y pisa la evidencia. Propuesta: `select_for_update` de visita y proyecto dentro del `atomic` y test de doble registro (resuelve también que la visita quede mutada en memoria si falla `full_clean`).
  5. Una visita offline que llega tarde hace retroceder `encargado_actual` y `proxima_visita`. Propuesta: actualizar el proyecto solo si `realizada_en` es la más reciente; rechazar `realizada_en` futura.
  6. Borrar una foto o una visita deja el JPEG en disco, y `HistoricalVisita` conserva texto libre tras una supresión. Propuesta: `has_delete_permission=False` en el admin de visitas y fotos, `post_delete` que borre el archivo; decisión legal sobre retención de visitas al suprimir un sitio (hoy `PROTECT` lo impide).
  - Menores: el comentario JPEG/GIF (marcador COM) sobrevive al reencodeo (`imagen.info = {}`); archivo no imagen da 500 por `Foto.objects.create` (relanzar como `ValidationError`); HEIC no se abre (la app debe mandar JPEG); el original con GPS pasa por el temporal del sistema si pesa más de 2,5 MB; el servicio no compara `empleado` con el asignado (definir en el plan de API); `HistoricalVisita` guarda `motivo_manual`, `observaciones` e `incidencia_detalle` (política de retención); MEDIA no se sirve y, cuando se sirva, tiene que ser con vista autenticada por permiso sobre la visita.
  - Observaciones de verificación: `ProyectoTests.test_str_tolera_sitio_inexistente` usa `count() + 99999` como pk inexistente; T3 y T4 escribieron los tests junto con el código (no se los vio fallar uno por uno); `Visita.Meta.ordering = ["-creado"]` se agregó sin estar en el plan; `datos` todavía no se valida contra el esquema (va con el serializer).
- [menor, abierto] Los bloques `### Ola` de `docs/plantilla-plan.md` no los ejecuta ni `verificar_plan.py` ni `verificador`: en `visitas` los criterios de integración se pusieron en el cierre global. Corregir la plantilla o el hook.
- [menor, abierto] Re-auditoría de `auditoria-dominio`:
  - H1-b: `notas` y `horario_acceso` siguen en el historial (texto libre que puede contener contactos).
  - Las columnas borradas por `sitios/0002` siguen en disco hasta un `VACUUM FULL` y siguen en los backups (decisión de retención).
  - H2: `bulk_create`/`update()` saltean la validación de encargados. Hoy no se usan.
  - H4: ante resto 10 se acepta 9 aunque AFIP nunca emite ese caso con el mismo prefijo, y los CUIT ya cargados no se revalidan.
- [menor] `apps/sitios/models.py:60` lleva `# noqa: E501` porque el criterio del plan exigía la línea de `excluded_fields` en una sola línea; `ruff format` la partiría.
- [importante, abierto, diferido al plan de despliegue por decisión del usuario: hoy es solo desarrollo] La barrera de `config/settings/dev.py` solo mira `ALLOWED_HOSTS`. Con `DJANGO_ENV=development` y `ALLOWED_HOSTS` vacío en un hosting, el sitio arranca con `DEBUG=True` y la página técnica del 400 expone tracebacks y settings; con `runserver`, también `DATABASE_URL`, porque no coincide con el patrón de ocultamiento (comprobado por el auditor). Propuesta del auditor: abortar si hay variables propias del hosting (`RAILWAY_ENVIRONMENT`, `RENDER`, `DYNO`, `FLY_APP_NAME`, `K_SERVICE`…), que hay que ajustar al hosting real. [menor] Las IP privadas en `ALLOWED_HOSTS` no limitan quién se conecta (el Host lo elige el cliente). (El `.strip()` de `ALLOWED_HOSTS` ya está corregido: plan `hosts-espacios`.)
- El plan de autenticación tiene que invertir `test_panel_responde_200` y `test_api_v1_responde_200` (hoy fijan el acceso anónimo) y seguir la lista de condiciones del auditor: mixin por `es_administrador`, DRF con `IsAuthenticated` y JWT, `AdminSite` restringido, `simple_history` en `User` con `excluded_fields=["password", "last_login"]` (si no, copia el hash, y con el middleware de historial ya activo cada login genera un registro), LOGGING sin datos personales y CSP.
- WeasyPrint está instalado pero no se probó en tiempo de ejecución (en Windows suele necesitar GTK/Pango).
- Observación del verificador: `apps/web/tests/test_base.py:13` no distingue el atributo `data-tema="oscuro"` del selector CSS.
- Falta el ejemplo del certificado que la empresa entrega hoy (diseño y texto legal del PDF). Ver `docs/01-modelo-y-arquitectura.md` § 7.
- Falta confirmar si el 02241 49 6047 atiende WhatsApp y el horario de atención para el sitio público.
- Las planillas por servicio (`CampoPlanilla`) se cargan como fixtures provisorias y se editan a mano con lo que usen realmente los encargados y operarios.
- Logo: se usa provisoriamente el de "MAControl Group" (`static/img/logo.png`); la razón social en textos es MAControl S.A.

## Entradas (la más reciente arriba)

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
