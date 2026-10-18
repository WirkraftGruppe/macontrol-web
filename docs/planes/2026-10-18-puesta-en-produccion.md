# Plan: puesta-en-produccion — el sitio público listo y desplegado en Railway

<!-- Nivel Completo. Flujo: juez-plan → aprobación del usuario → commit `docs(plan): puesta-en-produccion`
→ commit_base en el Registro; congelado arriba del corte. Rama plan/puesta-en-produccion, creada desde
main f1cdc1b (merge de web-independiente). Se ejecuta en otra sesión. -->

<!-- Veredicto de juez-plan (1.ª pasada): 7 bloqueantes, 3 observaciones. Corregidos: grep del docstring de T2
(frase partida), fila NUM_PROXIES de T5, test nombrado de CheckDeploy, URL de T7 en línea propia `URL pública:`,
ancestro de T7 contra origin/main, commits T8 en la rama del plan, versiones exactas y ruff aparte. El bloqueante
de propiedad de T5 queda resuelto por la aprobación explícita del usuario (2026-10-18). -->

- **slug**: `puesta-en-produccion`
- **fecha**: 2026-10-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): puesta-en-produccion`. El hash se anota en `## Registro de verificación`.
- **objetivo**: que el sitio público de MAControl S.A. quede publicado en Railway con un dominio `*.up.railway.app`. Debe estar endurecido para producción (límites del login, proxy, caché compartida, tope de cuerpo, orígenes CSRF), con las fotos de servicio servidas desde un volumen y el código en un repositorio de GitHub propio.
- **fuera de alcance**:
  - **Datos de la empresa** (WhatsApp, horario, redes, número de habilitación, director técnico): los entrega el cliente más adelante y se cargan desde el admin. P-web-independiente-15 sigue abierto.
  - **Fotos de servicios y de la empresa**: las entrega el cliente más adelante. P-web-independiente-16 sigue abierto.
  - **Logos de clientes**: no se usan. El campo `ClienteDestacado.logo` queda en el modelo y no se carga; la portada muestra los nombres, como hoy.
  - **El dominio propio `macontrol.com.ar`**: se conecta en un plan posterior.
  - **`static/img/logo.png`** (logo oficial): no se modifica. Solo se agrega una copia reducida para la navegación.
  - El diseño aprobado (`static/css/web.css`), la CSP y la Referrer-Policy no cambian de valor.
  - `.claude/hooks/**`.
- **áreas**: web | admin | infraestructura
- **seguridad**: sí — toca la autenticación del admin (límites, `login_not_required`), la subida y el servido de imágenes (`/media/`), los settings de producción (proxy, caché, CSRF, `SITE_URL`, tope de cuerpo) y el despliegue público. Corre `auditor-seguridad` además de `verificador` y `verificador-b`.

## Contexto mínimo

Estado en `main` f1cdc1b: sitio solo (`apps/web` + `config/`), 98 tests, verificación TODO del plan `web-independiente` en PASA. Pendientes de origen: `docs/planes/2026-10-17-web-independiente.md` § Pendientes (P-web-independiente-1 a -21).
- **Media**: `config/urls.py:13-14` sirve `MEDIA_URL` solo en DEBUG; `prod.py:33-38` usa `FileSystemStorage`; nada sirve `/media/` en producción (P-1). El admin guarda con `commit=False`, así que `ReprocesaImagenesMixin.save` (`apps/web/forms.py:34-41`) nunca borra la imagen reemplazada; tampoco al borrar el objeto (P-7). `reprocesar_imagen` abre la imagen antes de mirar el tamaño (`apps/web/imagenes.py:23-24`, P-5).
- **Proxy y caché**: `NUM_PROXIES` sale de `leer_num_proxies()` (`base.py:15-24`, default 0, `int()` sin filtrar). No hay `CACHES`, así que se usa LocMem por proceso (P-2, P-4).
- **Login del admin** (`config/limites.py`):
  - `_grupo_de_ip` aplica /64 también a IPv4 mapeadas (42-51).
  - Los baldes son get→append→set (75, 96-99).
  - `_hash` es SHA-256 sin sal (38-39).
  - El docstring de `normalizar_usuario` está desactualizado (30-34).
  - `config/admin.py:24-25` no lleva `login_not_required` (P-20, P-21).
- **Settings de producción**:
  - `dev.py:12-16` aborta solo con `RAILWAY_ENVIRONMENT` (P-3).
  - `prod.py:22-24` no valida `CSRF_TRUSTED_ORIGINS`, y `base.py:113-114` no exige `https://` en `SITE_URL` (P-6).
  - El comentario de `SITE_URL` habla de QR (`base.py:110-112`, P-13).
- **Registro**: `config/registro.py:10-44` compara por subcadena sin normalizar tildes y no cubre `cookie`/`session` (P-14).
- **apps/web**:
  - `Configuracion.obtener()` hace `get_or_create` en un GET público (`models.py:85-88`, P-8).
  - La vista previa del admin copia la vista `servicio` (`admin.py:85-110` contra `views.py:70-89`, P-12).
  - La miniatura usa `style=`, que bloquea la CSP (`admin.py:17-24`, P-17).
  - `empresa.html:46-47` deja `<li>` vacíos (P-18).
- **Diseño**:
  - `logo.png` (928×235, 89 KB) se muestra a 206×52 en la navegación.
  - `404.html:12`, `500.html:12` y `qr.html:12` declaran `width="96" height="96"`, con la proporción mal.
  - El hero `inicio.html:15` no lleva `fetchpriority` (P-9).
- **Despliegue**:
  - `herramientas/humo_web.py:61-66` no fija `DJANGO_SETTINGS_MODULE` (P-10).
  - `requirements.txt` no fija versiones salvo gunicorn y whitenoise, e instala ruff.
  - `railway.json` no tiene `createcachetable` ni `--workers` (P-19).
  - `docs/despliegue.md:18-27` no lista `NUM_PROXIES` (P-21).
- **Remoto**: `origin` es el repositorio compartido con el repo detach (ramas `separacion-web-*`). Un push de `main` desde acá reemplazaría su `main`.

## Decisiones

- 2026-10-18 — Los datos de la empresa y las imágenes pendientes los entrega el cliente más adelante; este plan no los espera — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — No se usan logos de clientes; `ClienteDestacado.logo` queda en el modelo sin cargarse y la portada muestra los nombres — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — El logo oficial es `static/img/logo.png` — decisión del usuario — reemplaza a: 2026-09-28 (logo "MAControl Group" provisorio)
- 2026-10-18 — El plan incluye el despliegue real en Railway. Cada acción externa (crear proyecto, base, volumen, variables, push) se confirma con el usuario en el momento — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — Las fotos se guardan en un volumen de Railway (`MEDIA_ROOT=/data/media`) y las sirve la app por `/media/`, limitado a `servicios/` y `clientes/` y a extensiones de imagen, con `nosniff` y caché — decisión del usuario (volumen), forma decidida por Claude, revisable — reemplaza a: 2026-10-17 (media solo en DEBUG)
- 2026-10-18 — El código llega a Railway desde un repositorio nuevo de GitHub. El `origin` actual pasa a llamarse `detach`, y `origin` apunta al repositorio nuevo (la URL la da el usuario en T7). Nunca se hace push a `detach` — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — El sitio sale primero con el dominio `*.up.railway.app`; `macontrol.com.ar` va en un plan posterior — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — Caché compartida con `DatabaseCache` (tabla creada con `createcachetable` en el `preDeployCommand`), sin Redis. Los baldes del login pasan a contadores con `cache.add` + `cache.incr` — una dependencia y un servicio menos; el tráfico del admin es mínimo — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `NUM_PROXIES` es obligatorio en producción (sin default). Su valor en Railway lo fija T7 según la documentación de Railway sobre `X-Forwarded-For`, y queda anotado en `docs/despliegue.md` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — El tope de cuerpo es un middleware propio (`config/limite_cuerpo.py`) ubicado después de `SecurityMiddleware` y antes de `CsrfViewMiddleware`: 413 si `CONTENT_LENGTH` supera 3 MB. Una foto admite 2 MB más el formulario — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `requirements.txt` fija versiones exactas (las del venv verificado) y `ruff` pasa a `requirements-dev.txt` — producción no instala herramientas de desarrollo — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — La navegación usa `static/img/logo-nav.png`, una copia del logo oficial reducida a 412×104 (2× su tamaño de pantalla). `logo.png` queda intacto. El hero suma `fetchpriority="high"`; `srcset` y el CSS crítico quedan pendientes — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — Excepción a la tabla de propiedad: T5 (delegada) escribe `config/settings/*.py`, `config/urls.py` y `requirements*.txt`, que son del principal. Corre sola en su ola, así que se cumple "nunca en paralelo" — aprobada por el usuario el 2026-10-18 al aprobar el plan — reemplaza a: (nada)
- 2026-10-18 — El merge de `plan/puesta-en-produccion` en `main` y el push al repositorio nuevo ocurren en T7, después de verificar T1–T6, y solo con la autorización explícita del usuario en ese momento — frontera del esquema — reemplaza a: (nada)
- 2026-10-18 — Detrás de Railway la IP del cliente se toma de la cabecera que fija el borde (`IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`), con prioridad sobre `NUM_PROXIES`; se agregan T9 (delegada, `config/red.py`) y T10 (integración y setting, principal) antes del despliegue, que pasa a la ola 4 — decisión del usuario (opción a de P-puesta-en-produccion-7) — reemplaza a: (nada)

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4 (integración) | ninguna (T1 no cambia campos) |
| 2 | T5, T6 (integración y verificación previa al despliegue) | ninguna |
| 3 | T9 (IP del cliente por cabecera), T10 (integración, principal) | ninguna |
| 4 | T7 (despliegue, principal), T8 (cierre, principal) | ninguna |

## Subtareas

### T1 — Imágenes, media pública y ajustes de apps/web

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/web/admin.py`, `apps/web/forms.py`, `apps/web/imagenes.py`, `apps/web/views.py`, `apps/web/urls.py`, `apps/web/models.py` (solo `Configuracion.obtener`), `apps/web/templates/web/paginas/empresa.html`, `apps/web/tests/test_admin.py`, `apps/web/tests/test_modelos.py`, `apps/web/tests/test_publicas.py`, `apps/web/tests/test_media.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/**`, `apps/web/migrations/`, `templates/web/**`, `static/**`, `apps/web/templates/404.html`, `apps/web/templates/500.html`, `apps/web/templates/web/paginas/{inicio,qr,servicio}.html`, `apps/web/tests/test_diseno.py`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (subida y servido de archivos), `.agents/skills/django-expert/SKILL.md` (admin), `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí (`worktrees/puesta-en-produccion-T1`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer** (resuelve P-5 en su parte de imágenes, P-7, P-8, P-11, P-12, P-17 y P-18):
  1. **Borrado de archivos** (P-7): `ServicioAdmin` y `ClienteDestacadoAdmin` borran el archivo reemplazado o quitado en `save_model` y los archivos del objeto en `delete_model`/`delete_queryset`. El borrado usa `transaction.on_commit`. Se quita el borrado muerto del mixin del formulario.
  2. **Tamaño antes de abrir** (P-5): `reprocesar_imagen` rechaza con `ValidationError` un archivo de más de `TAMANO_MAXIMO_IMAGEN` antes de abrirlo.
  3. **Vista `media_publica`** en `views.py`, con ruta `media/<path:ruta>` en `apps/web/urls.py`:
     - sirve solo archivos de `MEDIA_ROOT/servicios/` y `MEDIA_ROOT/clientes/` con extensión png, jpg, jpeg o webp;
     - responde 404 a todo lo demás, incluidos `..`, rutas absolutas y otras carpetas;
     - agrega `X-Content-Type-Options: nosniff` y `Cache-Control: public, max-age=86400`.
  4. **`Configuracion.obtener()`** (P-8) no escribe en la base: devuelve la fila o una instancia sin guardar.
  5. **Contexto compartido** (P-12): `contexto_servicio(servicio)` en `views.py`, usado por la vista pública y por la vista previa.
  6. **Plantillas y tests**:
     - P-17: la miniatura del admin usa atributos `width`/`height` en lugar de `style`.
     - P-18: `empresa.html` no deja `<li>` vacíos.
     - P-11: tests de regresión.
     - Se reemplaza `test_obtener_crea_la_fila_vacia` por el test nuevo de P-8.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_reemplazar_foto_borra_la_anterior_al_confirmar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_borrar_servicio_borra_su_foto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_gif_renombrado_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_archivo_mayor_al_tope_se_rechaza_sin_abrirlo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminImagenesTests.test_logo_de_cliente_conserva_alfa_sin_metadatos_y_nombre_uuid --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminConfiguracionTests.test_red_http_o_con_credenciales_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.VistaPreviaTests.test_pk_inexistente_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.VistaPreviaTests.test_vista_previa_y_publica_comparten_contexto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_admin.AdminEspanolTests.test_miniatura_sin_atributo_style --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.FotoServicioTests.test_foto_rechaza_extension_tamano_y_usa_uuid --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_modelos.ConfiguracionTests.test_obtener_no_escribe_en_la_base --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_publicas.PaginasPublicasTests.test_empresa_sin_datos_legales_no_deja_items_vacios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_media.ServirMediaTests.test_sirve_imagen_de_servicios_con_nosniff_y_cache --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_media.ServirMediaTests.test_rechaza_rutas_fuera_de_carpetas_publicas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_media.ServirMediaTests.test_inexistente_da_404 --keepdb`
  - `[grep-0]` `grep -n "style=" apps/web/admin.py`
  - `[grep-0]` `grep -n "get_or_create" apps/web/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T1`

### T2 — Login del admin, tope de cuerpo y registro

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `config/limites.py`, `config/red.py`, `config/admin.py`, `config/registro.py`, `config/limite_cuerpo.py` (nuevo), `config/tests/test_limites.py`, `config/tests/test_admin_site.py`, `config/tests/test_registro.py`, `config/tests/test_limite_cuerpo.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/settings/**`, `config/urls.py`, `config/tests/test_settings.py`, `config/tests/test_ajustes_ingreso.py`, `apps/**`, `templates/**`, `static/**`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (autenticación, cabeceras), `.agents/skills/python-best-practices/SKILL.md`
- **Worktree**: sí (`worktrees/puesta-en-produccion-T2`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer** (resuelve P-4 salvo `leer_num_proxies`, que va en T5; P-14, P-20 y P-21 en su parte de docstring; y el middleware de P-5):
  1. **IPv4 mapeadas**: `_grupo_de_ip` las desmapea con `ipv4_mapped` antes de agrupar.
  2. **Claves**: pasan a `salted_hmac("config.limites", …)`.
  3. **Contadores atómicos**: los baldes pasan a contadores por ventana con `cache.add` + `cache.incr`, sin get→set.
  4. **`normalizar_usuario`**: el docstring describe el comportamiento real con `auth.User` e incluye la frase "solo arma las claves de los límites".
  5. **Login del admin**: `SitioAdministracion.login` lleva `@method_decorator(login_not_required)`.
  6. **Filtro de registro**: normaliza claves (NFKD sin tildes) y compara por segmento, no por subcadena; suma `cookie`, `session`, `sessionid`, `csrftoken`, `correo` y `email`.
  7. **`LimiteCuerpoMiddleware`** en `config/limite_cuerpo.py`: responde 413 si `CONTENT_LENGTH` supera `settings.LIMITE_CUERPO_BYTES` (default 3 MB vía `getattr`). Lo registra T5; los tests lo montan con `override_settings(MIDDLEWARE=…)`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites.LimitesAdminTests.test_ipv4_mapeada_usa_su_propio_balde --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites.LimitesAdminTests.test_claves_de_cache_usan_hmac_con_sal --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limites.LimitesAdminTests.test_registrar_fallo_usa_incremento_atomico --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_admin_site.AdminSiteTests.test_login_del_admin_no_requiere_sesion_con_login_required_middleware --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.FiltroAuditoriaTests.test_claves_con_tilde_cookie_y_sesion_se_ocultan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.FiltroAuditoriaTests.test_claves_inocuas_no_se_ocultan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limite_cuerpo.LimiteCuerpoTests.test_post_con_content_length_excesivo_da_413_antes_de_csrf --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_limite_cuerpo.LimiteCuerpoTests.test_post_dentro_del_tope_sigue_su_curso --keepdb`
  - `[grep-1]` `grep -n "solo arma las claves de los límites" config/limites.py`
  - `[grep-0]` `grep -n "hashlib.sha256" config/limites.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`

### T3 — Logo oficial en todas las páginas y carga del hero

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `static/img/logo-nav.png` (nuevo), `templates/web/base_web.html`, `apps/web/templates/404.html`, `apps/web/templates/500.html`, `apps/web/templates/web/paginas/qr.html`, `apps/web/templates/web/paginas/inicio.html` (solo el `<img>` del hero), `apps/web/tests/test_diseno.py`
- **No puede tocar**: `docs/planes/`, `static/img/logo.png`, `static/css/web.css`, `config/**`, `apps/web/*.py`, las demás plantillas
- **Skill a leer antes**: `.agents/skills/web-design-guidelines/SKILL.md` (imágenes), `docs/02-diseno.md`
- **Worktree**: sí (`worktrees/puesta-en-produccion-T3`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer** (resuelve P-9 en la parte del logo y el hero):
  1. **`logo-nav.png`**: se genera con Pillow desde `logo.png` a 412×104 (LANCZOS, RGBA, sin metadatos, optimizado). Lo usa `base_web.html` con `width="206" height="52"`.
  2. **404, 500 y QR**: usan `logo-nav.png` con `width` y `height` en la proporción real (por ejemplo `96`×`24`).
  3. **Hero**: el `<img>` del hero de `inicio.html` suma `fetchpriority="high"` y sus `width`/`height` reales, y no lleva `loading="lazy"`.
- **Criterios**:
  - `[existe]` `static/img/logo-nav.png`
  - `[cmd]` `git diff --quiet "$(git log --format=%h --grep='^docs(plan): puesta-en-produccion' | tail -1)" -- static/img/logo.png static/css/web.css`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno.DisenoWebTests.test_logo_de_errores_y_qr_respeta_proporcion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno.DisenoWebTests.test_logo_de_navegacion_es_version_reducida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_diseno.DisenoWebTests.test_hero_con_fetchpriority_alta --keepdb`
  - `[grep-0]` `grep -rn 'width="96" height="96"' apps/web/templates/`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T3`

### T4 — Integración (principal)

- **Ola**: 1 (después de verificar T1, T2 y T3, y de auditar T1 y T2)
- **Depende de**: T1, T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/puesta-en-produccion` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh puesta-en-produccion T<n> plan/puesta-en-produccion <rutas>` por cada una.
  3. Crear `worktrees/puesta-en-produccion-T5` desde `plan/puesta-en-produccion`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puesta-en-produccion | grep -q "T1: integra puesta-en-produccion-T1"`
  - `[cmd]` `git log --oneline plan/puesta-en-produccion | grep -q "T2: integra puesta-en-produccion-T2"`
  - `[cmd]` `git log --oneline plan/puesta-en-produccion | grep -q "T3: integra puesta-en-produccion-T3"`

### T5 — Settings de producción, dependencias y archivos de despliegue

- **Ola**: 2 (sola en su ola)
- **Depende de**: T4
- **Puede tocar**: `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`, `config/urls.py`, `config/tests/test_settings.py`, `config/tests/test_ajustes_ingreso.py`, `requirements.txt`, `requirements-dev.txt` (nuevo), `railway.json`, `.env.example`, `herramientas/humo_web.py`, `docs/despliegue.md`
- **No puede tocar**: `docs/planes/`, `apps/**`, `templates/**`, `static/**`, `config/limites.py`, `config/admin.py`, `config/registro.py`, `config/limite_cuerpo.py`, `.claude/**`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (despliegue y settings), `.claude/skills/convenciones-proyecto/SKILL.md` (variables de entorno). Para Railway: `railway.json` y la documentación oficial (`mcp__plugin_railway_railway__search-docs`, solo lectura).
- **Worktree**: sí (`worktrees/puesta-en-produccion-T5`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer** (resuelve P-2, P-3, P-4 en `leer_num_proxies`, P-5 con el registro del middleware, P-6, P-10, P-13 y P-19 en lo que es código, y la tabla de P-21):
  1. **`base.py`**:
     - `leer_num_proxies` acepta solo dígitos ASCII (`re.fullmatch(r"[0-9]+")`).
     - Registra `config.limite_cuerpo.LimiteCuerpoMiddleware` después de `SecurityMiddleware` y antes de `CsrfViewMiddleware`, con `LIMITE_CUERPO_BYTES = 3 * 1024 * 1024`.
     - El comentario de `SITE_URL` habla de canonical, Open Graph y sitemap.
  2. **`dev.py`**: aborta si existe cualquiera de estas variables: `RAILWAY_ENVIRONMENT`, `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID`, `RAILWAY_PUBLIC_DOMAIN`, `RENDER`, `FLY_APP_NAME`, `DYNO`, `K_SERVICE`.
  3. **`prod.py`**:
     - `NUM_PROXIES` obligatorio (sin default).
     - `CACHES` con `DatabaseCache` (tabla `cache_sitio`).
     - `CSRF_TRUSTED_ORIGINS` solo con `https://` y sin `*` ni ruta.
     - `SITE_URL` obligatoria y con `https://`.
     - Si alguno falla, `ImproperlyConfigured`.
  4. **`config/urls.py`**: sin `static(MEDIA_URL)`, porque `/media/` lo sirve `apps.web` (T1).
  5. **Dependencias**: `requirements.txt` con versiones exactas (`==`) de Django, django-environ, django-csp, Pillow, psycopg[binary], whitenoise y gunicorn; `requirements-dev.txt` con `-r requirements.txt` y `ruff`.
  6. **`railway.json`**:
     - `preDeployCommand` con `migrate --noinput` y `createcachetable`.
     - `startCommand` con `--workers 2`.
     - Que el build de `collectstatic` tenga las variables que exige `prod.py` (documentarlo).
  7. **`.env.example` y `docs/despliegue.md`**: suman `NUM_PROXIES`, `SITE_URL` obligatoria y el volumen.
  8. **`humo_web.py`**: fija `DJANGO_SETTINGS_MODULE=config.settings` y quita del entorno heredado `RAILWAY_*`, `NUM_PROXIES`, `ALLOWED_HOSTS`, `SECRET_KEY` y `MEDIA_ROOT`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_exige_num_proxies --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_usa_cache_en_base_de_datos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_rechaza_csrf_trusted_origins_inseguros --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DespliegueTests.test_prod_exige_site_url_https --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_aborta_con_variables_de_hosting --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_limite_de_cuerpo_registrado_antes_de_csrf --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_ingreso.AjustesIngresoTests.test_num_proxies_solo_digitos_ascii --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.CheckDeployTests.test_check_deploy_con_variables_de_produccion_completas --keepdb`
  - `[grep-0]` `grep -n "static(settings.MEDIA_URL" config/urls.py`
  - `[grep-0]` `grep -n "QR" config/settings/base.py`
  - `[grep-0]` `grep -nvE "==|^#|^$" requirements.txt`
  - `[grep-0]` `grep -ni "^ruff" requirements.txt`
  - `[grep-1]` `grep -n "^ruff" requirements-dev.txt`
  - `[grep-1]` `grep -n "createcachetable" railway.json`
  - `[grep-1]` `grep -n -- "--workers" railway.json`
  - `[grep-1]` `grep -nE "^\| .NUM_PROXIES. \|" docs/despliegue.md`
  - `[grep-1]` `grep -n '"DJANGO_SETTINGS_MODULE": "config.settings"' herramientas/humo_web.py`
  - `[cmd]` `./venv/Scripts/python.exe herramientas/humo_web.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T5`

### T6 — Integración y verificación previa al despliegue (principal)

- **Ola**: 2 (después de verificar y auditar T5)
- **Depende de**: T5
- **Pasos**:
  1. Revisar `cambios.sh` de T5 e integrarla con `worktree-integrar.sh`.
  2. Correr `verificador` y `verificador-b` sobre T1–T6 y los criterios de cierre global, y `auditor-seguridad` sobre `commit_base..HEAD`, con el plan en esta rama. Un bloqueante abierto frena el despliegue.
  3. Actualizar en `docs/bitacora.md` la línea `Plan activo: docs/planes/2026-10-18-puesta-en-produccion.md` y la tabla de estado, en un commit `registro:`.
  4. Presentar al usuario los informes y las decisiones "decidida por Claude" de las olas 1 y 2, y pedir la autorización para T7: merge en `main`, cambio de remotos, push y acciones en Railway.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puesta-en-produccion | grep -q "T5: integra puesta-en-produccion-T5"`
  - `[cmd]` `test -z "$(git worktree list | grep puesta-en-produccion-T)"`

### T9 — IP del cliente por la cabecera del borde

- **Ola**: 3
- **Depende de**: T6
- **Puede tocar**: `config/red.py`, `config/tests/test_red.py`
- **No puede tocar**: `docs/planes/`, `config/settings/**`, `config/limites.py`, `config/admin.py`, `config/urls.py`, `.env.example`, `docs/**`, `apps/**`, `templates/**`, `static/**`, `.claude/**`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (autenticación), `.agents/skills/python-best-practices/SKILL.md`
- **Worktree**: sí (`worktrees/puesta-en-produccion-T9`)
- **Ruta**: delegada (`implementador`)
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer** (resuelve P-puesta-en-produccion-7 en el código):
  1. `ip_del_cliente` lee `getattr(settings, "IP_CLIENTE_CABECERA", "")`. Vacío: el comportamiento actual con `NUM_PROXIES` queda igual.
  2. Con un valor: debe cumplir `^HTTP_[A-Z0-9_]+$` (nombre de `request.META`); si no, `ImproperlyConfigured`. Se toma `request.META[<valor>]` sin espacios y, si es una IP válida según `ipaddress.ip_address`, se devuelve esa; `X-Forwarded-For` y `NUM_PROXIES` se ignoran.
  3. Si la cabecera falta o no es una IP válida, se devuelve `REMOTE_ADDR` (nunca un valor que elija el cliente sin validar).
  4. El docstring explica el modo por cabecera y por qué en Railway es `HTTP_X_REAL_IP`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_red.IpDelClienteTests.test_cabecera_configurada_tiene_prioridad_sobre_x_forwarded_for --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_red.IpDelClienteTests.test_cabecera_con_valor_que_no_es_ip_usa_la_direccion_remota --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_red.IpDelClienteTests.test_cabecera_ausente_usa_la_direccion_remota --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_red.IpDelClienteTests.test_nombre_de_cabecera_invalido_lanza_improperlyconfigured --keepdb`
  - `[grep-1]` `grep -n "IP_CLIENTE_CABECERA" config/red.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T9`

### T10 — Integración y setting de la cabecera (principal)

- **Ola**: 3 (después de verificar y auditar T9)
- **Depende de**: T9
- **Pasos**:
  1. Revisar `cambios.sh` de T9 e integrarla con `worktree-integrar.sh puesta-en-produccion T9 plan/puesta-en-produccion config/red.py config/tests/test_red.py`.
  2. En un commit `T10: …` (el principal es dueño de `config/settings/*.py`): `config/settings/base.py` suma `IP_CLIENTE_CABECERA = env.str("IP_CLIENTE_CABECERA", default="")` con su comentario; `.env.example` suma `IP_CLIENTE_CABECERA=`; `docs/despliegue.md` suma su fila en la tabla de variables y la sección "`NUM_PROXIES` en Railway" explica que en Railway se usa `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`.
  3. `verificador` y `verificador-b` sobre T9 y T10, y `auditor-seguridad` sobre los commits de T9 y T10.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T10`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puesta-en-produccion | grep -q "T9: integra puesta-en-produccion-T9"`
  - `[cmd]` `test -z "$(git worktree list | grep puesta-en-produccion-T)"`
  - `[grep-1]` `grep -n '^IP_CLIENTE_CABECERA = env.str("IP_CLIENTE_CABECERA", default="")' config/settings/base.py`
  - `[grep-1]` `grep -n "^IP_CLIENTE_CABECERA=" .env.example`
  - `[grep-1]` `grep -nE "^\| .IP_CLIENTE_CABECERA. \|" docs/despliegue.md`
  - `[cmd]` `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from django.conf import settings; assert settings.IP_CLIENTE_CABECERA == 'HTTP_X_REAL_IP'"`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T10`

### T7 — Despliegue en Railway (principal, con confirmación del usuario en cada acción externa)

- **Ola**: 4
- **Depende de**: T10 y la autorización explícita del usuario
- **Pasos**:
  1. **Remotos y repositorio**:
     - `git remote rename origin detach`.
     - `git remote add origin <URL del repositorio nuevo que da el usuario>`.
     - Merge `--no-ff` de `plan/puesta-en-produccion` en `main` (`Merge plan/puesta-en-produccion: …`).
     - `git push -u origin main`. Nunca a `detach`.
  2. **Railway** (plugin o CLI, cada paso confirmado), siguiendo `docs/despliegue.md`:
     - proyecto nuevo, PostgreSQL y servicio conectado al repositorio nuevo, rama `main`;
     - volumen en `/data`;
     - variables: `DJANGO_ENV=production`, `SECRET_KEY` generada, `DATABASE_URL` referenciada, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `MEDIA_ROOT=/data/media`, `NUM_PROXIES` (valor según la documentación de Railway sobre `X-Forwarded-For`, citada en `docs/despliegue.md`) e `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`;
     - prueba con `curl` que el borde pisa un `X-Real-IP` falsificado: fallos de login con la misma cabecera falsificada y distintos valores no deben esquivar el cupo por (usuario, IP); el resultado queda anotado en `docs/despliegue.md`;
     - dominio `*.up.railway.app`.
  3. **Datos iniciales**:
     - `loaddata contenido_inicial` por `railway run` o `railway ssh`, confirmado.
     - El superusuario lo crea el usuario: `! railway ssh -- python manage.py createsuperuser`.
  4. **Documentación**: `docs/despliegue.md` suma una línea propia `URL pública: https://<dominio>.up.railway.app` (sola en su línea) más el valor de `NUM_PROXIES` con su fuente y la fecha del primer despliegue, en un commit `T7: …` en `plan/puesta-en-produccion`; después merge `--no-ff` de la rama en `main` y push de `main` a `origin`. Ninguna otra subtarea escribe una línea `URL pública:`.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T7`
- **Criterios**:
  - `[cmd]` `git remote get-url detach`
  - `[cmd]` `test "$(git remote get-url origin)" != "$(git remote get-url detach)"`
  - `[cmd]` `git fetch -q origin && git merge-base --is-ancestor "$(git log --format=%H --grep='^T7: ' -1 plan/puesta-en-produccion)" origin/main`
  - `[grep-1]` `grep -nE "^URL pública: https://[a-z0-9-]+\.up\.railway\.app$" docs/despliegue.md`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && test "$(curl -s -o /dev/null -w '%{http_code}' "$u/")" = 200`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && test "$(curl -s -o /dev/null -w '%{http_code}' "$u/servicio/control-plagas-urbanas/")" = 200`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && test "$(curl -s -o /dev/null -w '%{http_code}' "$u/admin/login/")" = 200`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && test "$(curl -s -o /dev/null -w '%{http_code}' "$u/panel/")" = 404`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && test "$(curl -s -o /dev/null -w '%{http_code}' "$u/media/servicios/no-existe.jpg")" = 404`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && curl -sI "$u/" | grep -qi "^strict-transport-security:"`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && curl -sI "$u/" | grep -qi "^content-security-policy: default-src 'self'"`
  - `[cmd]` `u=$(sed -n "s|^URL pública: \(https://[a-z0-9-]*\.up\.railway\.app\)$|\1|p" docs/despliegue.md | head -1); test -n "$u" && curl -sI "$u/" | grep -qi "^referrer-policy: strict-origin-when-cross-origin"`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T7`

### T8 — Cierre (principal)

- **Ola**: 4 (después de T7)
- **Depende de**: T7
- **Pasos**:
  1. En `## Pendientes que deja este plan`:
     - `### Cierra` con los P-web-independiente resueltos;
     - `### Problemas` con lo que quede: P-9 restante (`srcset` del hero, CSS crítico), P-15 (datos de la empresa), P-16 (imágenes), el dominio propio y lo que digan los auditores;
     - `### Decisiones` con las tomadas durante la ejecución.
  2. Copiar las decisiones del plan a `docs/decisiones.md` (está en `main`). Agregar la entrada de sesión a `docs/bitacora.md` con la URL pública y actualizar "Estado actual".
  3. Verificación `TODO` con `verificador` y `verificador-b`, y `auditor-seguridad` final sobre `commit_base..HEAD` y sobre el sitio público desplegado.
  4. Los cambios de los pasos 1 y 2 van en commits `T8: …` en `plan/puesta-en-produccion`; la verificación `TODO` corre en esa rama (el `Plan activo:` de la bitácora apunta a este plan desde T6); al final, con autorización del usuario, merge en `main` y push a `origin`.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T8`
- **Criterios**:
  - `[grep-0]` `py -3 .claude/hooks/pendientes.py | grep -E "^- P-web-independiente-(1|2|3|4|5|6|7|8|9|10|11|12|13|14|17|18|19|20|21) "`
  - `[grep-1]` `py -3 .claude/hooks/pendientes.py | grep -E "^- P-web-independiente-(15|16) "`
  - `[grep-1]` `grep -n "puesta-en-produccion" docs/bitacora.md`
  - `[grep-1]` `grep -n "reemplaza a: 2026-09-28 (logo" docs/decisiones.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T8`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-18-puesta-en-produccion.md puesta-en-produccion`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): puesta-en-produccion — modificado: <motivo>`. -->

commit_base: a5d491f

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |
| T7 | pendiente |
| T8 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-18 | T3 (verificador, verificador-b) | 0bb8f78 | PASA 8/8 | — |
| 2026-10-18 | T1 (verificador, verificador-b) | e53f14a | PASA 20/20 | auditor-seguridad: 0 bloqueantes (1 menor, 2 observaciones) |
| 2026-10-18 | T2 (verificador, verificador-b) | ad7ec4d | PASA 12/12 | auditor-seguridad: 1 bloqueante (incr de DatabaseCache reinicia el vencimiento) → ronda 1 |
| 2026-10-18 | T2 ronda 1 (verificador, verificador-b) | 4b7b2a9 | PASA 12/12 | reauditoría: bloqueante cerrado, sin bloqueantes nuevos |
| 2026-10-18 | T4 (principal) | 21238a8 | PASA 3/3 | integraciones 795d81f (T1), 62046e9 (T3), 21238a8 (T2); 127 tests |
| 2026-10-18 | T5 (verificador, verificador-b) | 1142e12 | PASA 21/21 | auditor-seguridad: 0 bloqueantes (1 importante, 2 menores, 3 observaciones); integrada en T6 con 135 tests |
| 2026-10-18 | T1–T6 + cierre global (verificador, verificador-b) | 704116d | PASA 72/72 | auditor-seguridad integrado: 0 bloqueantes para desplegar, 1 observación (P-13) |

## Pendientes que deja este plan

### Problemas

- P-puesta-en-produccion-1 [menor] Por el admin, `forms.ImageField.to_python` abre y verifica la imagen con todos los plugins de Pillow antes de que `reprocesar_imagen` controle tamaño y formato (`apps/web/forms.py`, `clean_foto`/`clean_logo`): el tope de P-5 se cumple en la función pero no en el flujo del admin. Usar un `FileField` propio vía `field_classes` y un test por POST al admin con `Image.open` simulado (auditor-seguridad T1).
- P-puesta-en-produccion-2 [observación] `_borrar_al_confirmar` (`apps/web/admin.py`) borra en un único callback de `on_commit` no robusto: si un `storage.delete` falla (p. ej. `PermissionError` en el volumen), el admin ve un 500 con la base ya confirmada y el resto queda sin borrar. `robust=True` o `try/except OSError` por nombre con aviso en el registro (auditor-seguridad T1). `media_publica` sirve con `FileResponse`, sin `X-Accel-Redirect` (implementador T1).
- P-puesta-en-produccion-3 [menor] `config/limites.py`: el docstring del módulo dice que `cache.add` + `cache.incr` es "atómico entre procesos", pero con `DatabaseCache` `incr` es get→set (más `touch`) y bajo concurrencia se pierden incrementos, acotado por la cantidad de workers; además `baldes_llenos` se consulta antes del hash de la contraseña. Corregir el docstring o pasar a una tabla propia con `F("cuenta") + 1` (auditor-seguridad T2).
- P-puesta-en-produccion-4 [menor] El filtro de `config/registro.py` compara por segmento y dejó de ocultar plurales y compuestos que antes se ocultaban: `accesstoken`, `refreshtoken`, `userpassword`, `passwords`, `tokens`, `telefonos`, `contraseñas`, `HTTPCookie`, `cookies`, `emails`, `e-mail`. Fragmentos fuertes por subcadena y débiles por segmento con plural quitado (auditor-seguridad T2). Hoy no hay emisor propio que los registre.
- P-puesta-en-produccion-5 [observación] Límites con ventana fija: ráfaga de hasta 2× el máximo en el borde, con la misma tasa sostenida; el docstring de `config/tests/test_limites.py` dice "ventana deslizante"; `test_incremento_con_databasecache_conserva_el_fin_de_ventana` solo acota el vencimiento por abajo (auditor-seguridad T2).
- P-puesta-en-produccion-6 [observación] El docstring de `LoginAdministracion` (`config/admin.py`) menciona "el del panel", que ya no existe en este repositorio (auditor-seguridad T2).
- P-puesta-en-produccion-7 [importante] `config/red.py` solo sabe leer `X-Forwarded-For` con `NUM_PROXIES`; la documentación de Railway (https://docs.railway.com/networking/public-networking/specs-and-limits) garantiza `X-Real-IP` y no `X-Forwarded-For`. Si el borde no agrega su salto, `NUM_PROXIES=1` deja falsificar la IP y saltear los baldes por IP; `NUM_PROXIES=0` comparte la IP del borde y 20 fallos anónimos bloquean el login a todos. `docs/despliegue.md` pide confirmarlo "mirando un `X-Forwarded-For` real", sin mecanismo para hacerlo. Propuesta del auditor: modo por cabecera (`IP_CLIENTE_CABECERA`) en `config/red.py` y prueba en T7 con `curl` falsificando ambas cabeceras (auditor-seguridad T5). Se decide antes de T7.
- P-puesta-en-produccion-8 [menor] El cull de `DatabaseCache` borra por orden alfabético de clave, no por antigüedad: con un flujo sostenido desde muchas /64 (≈2 500 grupos llenan 100 000 entradas) los culls terminan alcanzando `ingreso:usuario:<admin>` y reinician su balde. Caché aparte para el login (`cache_ingreso`, `MAX_ENTRIES` muy alto) o, como mínimo, corregir el comentario de `prod.py` (auditor-seguridad T5).
- P-puesta-en-produccion-9 [menor] `railway.json` declara `preDeployCommand` como array de dos comandos sin fuente que confirme que Railway ejecuta cada elemento por separado; si no, no se crea `cache_sitio` y todo POST al login da 500. Confirmar con la documentación o unirlos con `&&` (auditor-seguridad T5).
- P-puesta-en-produccion-10 [observación] Sin control automático de CVE de las versiones fijadas en `requirements.txt` (`pip-audit` no instalado) (auditor-seguridad T5).
- P-puesta-en-produccion-11 [observación] `prod.py` acepta valores mal formados que fallan cerrados: `CSRF_TRUSTED_ORIGINS` con credenciales, mayúsculas o espacios; `SITE_URL` con ruta, consulta o `#`; `ALLOWED_HOSTS="*"`; `MEDIA_ROOT` sin definir (las fotos irían al disco efímero) (auditor-seguridad T5).
- P-puesta-en-produccion-12 [observación] No se confirmó que Railpack pase las variables del servicio al `buildCommand` (`collectstatic` exige las de `prod.py`); se ve en el primer despliegue (implementador T5).
- P-puesta-en-produccion-13 [observación] `MEDIA_ROOT=` definida vacía no cae al default (`config/settings/base.py`, django-environ devuelve `''`): las fotos irían a `/app/servicios` fuera del volumen y se perderían en el siguiente despliegue. `env(...) or default` en `base.py` y abortar en `prod.py` si `MEDIA_ROOT` no es absoluta (auditor-seguridad, integración T6).

### Decisiones

- 2026-10-18 — `registrar_fallo` fija el vencimiento de cada contador al fin de su ventana (`cache.touch` después de `incr`), porque `DatabaseCache.incr` lo reinicia al TIMEOUT por defecto — bloqueante de auditor-seguridad en T2, decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — La caché `DatabaseCache` de producción lleva `OPTIONS["MAX_ENTRIES"]` alto (100 000) para que el cull no borre contadores activos del login — hallazgo importante de auditor-seguridad en T2, va como indicación a T5 sin cambiar criterios; decidida por Claude, revisable — reemplaza a: (nada)

### Cierra
