# Plan: cerrar el acceso (panel, API, admin) y la seguridad base

- **slug**: `autenticacion`
- **fecha**: 2026-10-03
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): autenticacion`. El hash se anota en `## Registro de verificación`.
- **objetivo**:
  - el panel exige sesión con rol administrador;
  - la API exige JWT, con rotación y blacklist del refresh;
  - el admin técnico acepta solo superusuarios;
  - el historial de `User` no guarda `password` ni `last_login`;
  - los logs no reciben datos personales;
  - todas las respuestas llevan CSP.
- **fuera de alcance**:
  - endpoints de negocio de la API;
  - recuperación de contraseña;
  - 2FA;
  - servir MEDIA autenticado;
  - despliegue: caché compartida para el throttling, `NUM_PROXIES`, HSTS completo y la barrera de `dev.py`;
  - `telefono`, `email` y nombre en el historial de `User` (queda abierto en la bitácora junto a H1-b).
- **áreas**: panel | api | dominio (accounts) | infraestructura
- **seguridad**: sí. Toca autenticación, roles y permisos, el admin, settings de producción y datos personales en logs y en el historial. Por eso corre también `auditor-seguridad`.

## Contexto mínimo

- `apps/accounts/models.py:5-27`: `User(AbstractUser)` con `rol`, `es_administrador` y `es_empleado`. No tiene historial.
- `apps/panel/views.py:6` y `apps/api/views.py:6` son vistas provisorias sin autenticación. `apps/web/tests/test_rutas.py:23-27` fija que respondan 200 anónimas.
- `config/settings/base.py`: falta `rest_framework` en `INSTALLED_APPS`, y no hay `REST_FRAMEWORK`, `SIMPLE_JWT`, `LOGGING` ni CSP. `HistoryRequestMiddleware` está activo (:41).
- `config/urls.py:7`: usa `admin.site` estándar, sin restricción a superusuarios.
- `templates/base.html:7-121`: `<style>` inline, fuentes locales y ningún script.
- Referencias: convenciones § Roles (L128-132) y § Rutas (L122-124); `docs/01-modelo-y-arquitectura.md` §2 y §6 (JWT con refresh largo).
- Diseño:
  - mixin con `UserPassesTestMixin`: anónimo → login, autenticado sin rol → 403;
  - JWT HS256 (access de 15 minutos, refresh de 7 días, `ROTATE_REFRESH_TOKENS` y `BLACKLIST_AFTER_ROTATION`);
  - `AdminSite` propio, montado con `AdminConfig.default_site`;
  - filtro de logging en el handler;
  - django-csp 4 con nonce.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 | config, requirements (migraciones de terceros: `token_blacklist`) |
| 2 | T2, T4 | accounts (`0002` historial) · diseño/web (sin migraciones) |
| 3 | T3 | panel, api (transversal; sin migraciones) |

## Subtareas

### T1 — Configurar DRF, SimpleJWT, CSP, LOGGING, contraseñas y AdminSite de superusuarios

- **Ola**: 1
- **Depende de**: —
- **Puede tocar** (T1 es la "subtarea de integración" de config que prevé la tabla de propiedad: única de la ola 1, nunca en paralelo; se delega porque escribe más de dos archivos no triviales):
  - `requirements.txt`, `config/settings/base.py`;
  - `config/admin.py`, `config/apps.py`, `config/registro.py` (los tres nuevos);
  - `config/tests/test_settings.py`, `config/tests/test_registro.py`, `config/tests/test_admin_site.py`.
- **No puede tocar**: `docs/planes/`, `apps/`, `templates/`, `config/settings/dev.py`, `config/settings/prod.py`, `config/urls.py`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Production settings, Password, DRF, CSP, Logging; `.agents/skills/jwt-security/SKILL.md` § Token lifetime, Refresh tokens
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - `requirements.txt`: agregar `django-csp>=4.0,<5`. Instalar con `./venv/Scripts/python.exe -m pip install -r requirements.txt`.
  - `INSTALLED_APPS`:
    - agregar `rest_framework`, `rest_framework_simplejwt.token_blacklist` y `csp`;
    - reemplazar `django.contrib.admin` por `config.apps.AdminMAControlConfig`, cuyo `default_site` es `config.admin.SitioAdministracion`;
    - `SitioAdministracion.has_permission` devuelve `request.user.is_active and request.user.is_superuser`.
  - `MIDDLEWARE`: agregar `csp.middleware.CSPMiddleware`.
  - `REST_FRAMEWORK`:
    - `"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"]`;
    - `"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]`;
    - `DEFAULT_RENDERER_CLASSES` solo JSON;
    - `DEFAULT_THROTTLE_RATES = {"autenticacion": "10/min"}`.
  - `SIMPLE_JWT`:
    - `ACCESS_TOKEN_LIFETIME=15 min` y `REFRESH_TOKEN_LIFETIME=7 días`;
    - `ROTATE_REFRESH_TOKENS=True` y `BLACKLIST_AFTER_ROTATION=True`;
    - `UPDATE_LAST_LOGIN=False`, `ALGORITHM="HS256"` y `CHECK_REVOKE_TOKEN=True`.
  - `CONTENT_SECURITY_POLICY` (formato de django-csp 4):
    - `default-src 'self'`, `style-src 'self'` + NONCE, `script-src 'self'`;
    - `img-src 'self' data:`, `font-src 'self'`;
    - `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, `form-action 'self'`.
  - `AUTH_PASSWORD_VALIDATORS`: `MinimumLengthValidator` con `"min_length": 12`.
  - `LOGIN_URL = "/panel/ingresar/"`, `LOGIN_REDIRECT_URL = "/panel/"` y `LOGOUT_REDIRECT_URL = "/panel/ingresar/"`, como rutas literales: T2 prueba el mixin antes de que T3 cree la ruta, y un nombre de URL daría `NoReverseMatch`.
  - `LOGGING`:
    - handler de consola con el filtro `config.registro.FiltroDatosPersonales`;
    - el filtro reemplaza por `"[oculto]"` los valores de las claves `password`, `token`, `latitud`, `longitud` y `cuit`, en `record.args` (dict o tupla de dicts) y en los atributos extra del record;
    - también reemplaza las instancias de `Model` que aparezcan en `args` por `"<app.Modelo pk=N>"`, para que el formateador nunca las reciba.
  - Tests:
    - `config/tests/test_admin_site.py`: un usuario con rol administrador, `is_staff` y sin `is_superuser` recibe redirección al login del admin; un superusuario recibe 200.
    - `config/tests/test_settings.py`: corre `check --deploy` en un subproceso con `DJANGO_ENV=production` y un `SECRET_KEY` largo, `ALLOWED_HOSTS` y `DATABASE_URL` de prueba, siguiendo el patrón `_HEREDADAS` del archivo. Exige código de salida 0 y que el conjunto de IDs `security.W…` sea exactamente `{"security.W005", "security.W021"}`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_admin_site.AdminSiteTests.test_administrador_sin_superuser_no_entra_al_admin --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_admin_site.AdminSiteTests.test_superusuario_entra_al_admin --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.RegistroTests.test_filtro_oculta_claves_sensibles --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.RegistroTests.test_filtro_reemplaza_instancias_de_modelo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.RegistroTests.test_handler_de_consola_usa_el_filtro --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.CheckDeployTests.test_check_deploy_solo_avisa_hsts_diferido --keepdb`
  - `[grep-1]` `grep -n '"DEFAULT_PERMISSION_CLASSES"' config/settings/base.py`
  - `[grep-1]` `grep -n '"min_length": 12' config/settings/base.py`
  - `[grep-1]` `grep -n 'BLACKLIST_AFTER_ROTATION' config/settings/base.py`
  - `[grep-1]` `grep -n 'csp.middleware.CSPMiddleware' config/settings/base.py`
  - `[grep-0]` `grep -n "SessionAuthentication\|BasicAuthentication\|TokenAuthentication" config/settings/base.py`
  - `[grep-0]` `grep -n "unsafe-inline" config/settings/base.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check config`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-autenticacion.md autenticacion)" 350 requirements.txt config`

### T2 — Historial de User, mixin, permisos DRF y comando `crear_usuario`

- **Ola**: 2
- **Depende de**: T1
- **Puede tocar**: `apps/accounts/` (incluye `migrations/0002_*.py` generada con `makemigrations`, `mixins.py`, `permisos.py`, `management/commands/crear_usuario.py`, `tests/`)
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `apps/accounts/migrations/0001_initial.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Authentication, Authorization; `.agents/skills/django-rest-framework/SKILL.md` § Permissions
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 380 líneas agregadas
- **Qué hacer**:
  - Historial en `User`:
    - `history = HistoricalRecords(excluded_fields=["password", "last_login"])` en una sola línea, más su migración generada.
    - simple_history no mira `excluded_fields` al decidir si guarda: el `save(update_fields=["last_login"])` de `update_last_login` crearía un registro en cada login. `User.save` activa `skip_history_when_saving` cuando `update_fields` es exactamente `{"last_login"}` y lo quita al terminar.
    - Test: un login con `self.client.login` no crea un registro histórico, y `HistoricalUser` no tiene los campos `password` ni `last_login`.
  - `mixins.AdministradorRequeridoMixin(UserPassesTestMixin)`:
    - `test_func` devuelve `user.is_authenticated and user.is_active and user.es_administrador`;
    - con el `handle_no_permission` estándar: anónimo → `LOGIN_URL`, autenticado → 403;
    - se prueba con una vista de prueba montada en el test con `RequestFactory`, sin URLs; el anónimo debe redirigir a `/panel/ingresar/?next=…` (el `LOGIN_URL` real, sin `override_settings`).
  - `permisos.EsAdministrador` y `EsEmpleado` (`BasePermission`): `is_authenticated` y el rol correspondiente.
  - `crear_usuario <username> --rol administrador|empleado [--nombre --apellido --email]`:
    - pide la contraseña dos veces con `getpass` y la valida con `validate_password`;
    - crea el usuario con `is_staff=False` e `is_superuser=False`;
    - rechaza un usuario existente con `CommandError`;
    - los tests mockean `getpass`.
  - Sin la palabra `is_staff` salvo en el comando y sus tests.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_historial.HistorialUserTests.test_historial_no_guarda_password_ni_last_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_historial.HistorialUserTests.test_cambio_de_rol_queda_en_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_mixins.AdministradorRequeridoMixinTests.test_anonimo_redirige_al_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_mixins.AdministradorRequeridoMixinTests.test_empleado_recibe_403 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_permisos.PermisosTests.test_es_administrador_rechaza_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_permisos.PermisosTests.test_es_empleado_rechaza_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_crear_usuario.CrearUsuarioTests.test_crea_empleado_sin_is_staff --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_crear_usuario.CrearUsuarioTests.test_rechaza_contrasena_de_11_caracteres --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_crear_usuario.CrearUsuarioTests.test_rechaza_usuario_existente --keepdb`
  - `[grep-1]` `grep -n 'excluded_fields=\["password", "last_login"\]' apps/accounts/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/accounts`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-autenticacion.md autenticacion)" 380 apps/accounts`

### T4 — Nonce de CSP en la plantilla base (diseño + web)

- **Ola**: 2
- **Depende de**: T1
- **Puede tocar**: `templates/base.html`, `apps/web/tests/test_csp.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/web/tests/test_base.py`, `apps/web/tests/test_rutas.py`, `templates/panel/`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § CSP
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**:
  - `<style nonce="{{ request.csp_nonce }}">` en `base.html`, sin mover los estilos, porque `test_base.py` los busca en el HTML.
  - `test_csp`:
    - `GET /` lleva `Content-Security-Policy` con `default-src 'self'` y sin `unsafe-inline`;
    - el nonce de la cabecera coincide con el atributo del `<style>`;
    - `GET /admin/login/` responde 200 con la cabecera.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_csp.CspTests.test_cabecera_csp_presente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_csp.CspTests.test_style_de_base_lleva_el_nonce_de_la_cabecera --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_csp.CspTests.test_login_del_admin_lleva_csp --keepdb`
  - `[grep-1]` `grep -n 'nonce="{{ request.csp_nonce }}"' templates/base.html`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/web`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-autenticacion.md autenticacion)" 80 templates/base.html apps/web/tests/test_csp.py`

### T3 — Login del panel, vistas JWT y raíz de la API (transversal)

- **Ola**: 3
- **Depende de**: T1, T2
- **Puede tocar**:
  - `apps/panel/views.py`, `apps/panel/forms.py`, `apps/panel/tests/test_acceso.py`, `templates/panel/ingresar.html`;
  - `apps/api/views.py`, `apps/api/tests/test_auth.py`;
  - **excepción declarada a la tabla de propiedad**: `apps/panel/urls.py`, `apps/api/urls.py` y `apps/web/tests/test_rutas.py`. Es la única subtarea de la ola 3 y no hay escritores en paralelo.
- **No puede tocar**: `docs/planes/`, `config/`, `apps/accounts/`, `templates/base.html`, `templates/panel/base.html`, `apps/panel/tests/test_routers.py`, `apps/api/tests/test_routers.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Authentication, Throttling; `.agents/skills/jwt-security/SKILL.md` § Refresh tokens
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 380 líneas agregadas
- **Qué hacer**:
  - Panel:
    - `inicio` pasa a ser una vista de clase con `AdministradorRequeridoMixin`.
    - `IngresarView(LoginView)` usa `templates/panel/ingresar.html` (que extiende `panel/base.html`) y un `FormularioIngreso` cuyo `confirm_login_allowed` rechaza a quien no es administrador con el mensaje "Esta cuenta no tiene acceso al panel."
    - `SalirView(LogoutView)` (solo POST).
    - Rutas directas (`URLPattern`, no `include`): `ingresar/` y `salir/` en `apps/panel/urls.py`.
  - API:
    - `raiz` pasa a `APIView`: con los defaults de DRF, anónimo → 401; autenticado → `{"usuario": username, "rol": rol}`.
    - `ObtenerToken(TokenObtainPairView)` y `RenovarToken(TokenRefreshView)` con `throttle_classes = [ThrottleAutenticacion]`, donde `ThrottleAutenticacion` es una `AnonRateThrottle` con `scope = "autenticacion"`.
    - Rutas `auth/token/` y `auth/token/refresh/` en `apps/api/urls.py`.
    - Si SimpleJWT renueva el refresh de un usuario desactivado, `RenovarToken` lo rechaza con 401.
  - Tests:
    - limpian la caché en `setUp`, por el throttle;
    - sin la palabra `is_staff` en `apps/panel` ni en `apps/api`.
  - `test_rutas.py`: `test_panel_responde_200` pasa a `test_panel_anonimo_redirige_al_login` (302 a `/panel/ingresar/`) y `test_api_v1_responde_200` pasa a `test_api_v1_anonimo_recibe_401`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoPanelTests.test_anonimo_redirige_al_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoPanelTests.test_empleado_recibe_403 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoPanelTests.test_administrador_recibe_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoPanelTests.test_empleado_no_inicia_sesion_en_el_panel --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoPanelTests.test_salir_cierra_la_sesion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_anonimo_recibe_401 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_autenticado_recibe_su_rol --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_token_y_refresh_funcionan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_refresh_usado_queda_en_blacklist --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_usuario_inactivo_no_obtiene_token --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_refresh_de_usuario_desactivado_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_token_limita_intentos_anonimos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_sesion_django_no_autentica_la_api --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_panel_anonimo_redirige_al_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_api_v1_anonimo_recibe_401 --keepdb`
  - `[grep-0]` `grep -rn "is_staff" apps/panel apps/api`
  - `[grep-0]` `grep -rn "AllowAny" apps/ --include=*.py`
  - `[grep-0]` `grep -n "def test_panel_responde_200\|def test_api_v1_responde_200" apps/web/tests/test_rutas.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/panel apps/api apps/web`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-autenticacion.md autenticacion)" 380 apps/panel apps/api templates/panel/ingresar.html apps/web/tests/test_rutas.py`

## Trabajo del principal (integración)

- Ola 1: `worktree-crear.sh autenticacion T1 plan/autenticacion`. Integrar T1 con sus rutas.
- Ola 2: crear T2 y T4 desde el commit de integración de la ola 1 e integrarlos en este orden: T2, T4.
- Ola 3: crear T3 desde la integración de la ola 2 e integrarlo.
- Los criterios de integración van en el cierre global, porque los bloques `### Ola` no los ejecuta ningún hook (problema abierto en la bitácora).

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-03-autenticacion.md autenticacion`
- `[cmd]` `./venv/Scripts/python.exe -c "import csp"`
- `[grep-1]` `grep -n "django-csp" requirements.txt`
- `[grep-1]` `grep -n "^SESSION_COOKIE_SECURE = True" config/settings/prod.py`   # resguardo: ya existe hoy
- `[grep-1]` `grep -n "^CSRF_COOKIE_SECURE = True" config/settings/prod.py`   # resguardo: ya existe hoy

## Registro de verificación

commit_base: 6d22ff1

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T4 | hecha |
| T3 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-03 | T1 | 2325ed9 | PASA (verificador y verificador-b, 16/16) | auditor: sin bloqueantes; I1, I2, M1, M2 en el filtro de logging |
| 2026-10-03 | T1 (corrección) | d516a7e | PASA (verificador y verificador-b, 16/16) | auditor: I1, I2, M1, M2 cerrados; integrada en 59ac5ca |
| 2026-10-03 | T2 | d238292 | PASA (verificador y verificador-b, 14/14) | auditor: sin bloqueantes ni importantes; 3 menores (skip_history borrado si lo puso quien llama, crear_usuario sin normalize_username/full_clean, carrera exists/save); integrada en 15264d2 |
| 2026-10-03 | T4 | cb01217 | PASA (verificador y verificador-b, 7/7) | auditor: sin bloqueantes; menores: falta test de unicidad del nonce; `<style>` inline del changelist del admin queda bloqueado por la CSP; integrada en cd5e5ce |
| 2026-10-03 | T3 | cd209f0 | PASA (verificador y verificador-b, 21/21) | auditor: H1 login del panel sin límite (importante), H2 XFF/NUM_PROXIES (importante, diferido a despliegue), H3 refresh tras cambio de contraseña, H4 balde compartido |
| 2026-10-03 | T3 (corrección) | a56f9d7 | PASA (verificador y verificador-b, 21/21) | auditor: H1, H3, H4 cerrados; nuevos N1 DoS de cuenta, N2 NFKC, N3 /admin/login/ sin límite, N4 balde por IP compartido → plan siguiente `limites-ingreso` (decisión del usuario); integrada en 5a71d9e |
| | TODO | | | |
