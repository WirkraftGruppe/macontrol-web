# Plan: Correcciones de la auditoría de modelos de dominio (H1–H4)

- **slug**: `auditoria-dominio`
- **fecha**: 2026-10-02
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): auditoria-dominio`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**:
  - el historial de sitios ya no guarda contacto ni teléfono;
  - un sitio se puede suprimir junto con todo su historial;
  - el QR de un sitio se puede regenerar desde el admin;
  - los encargados de un proyecto son siempre empleados activos;
  - el CUIT valida el dígito verificador.
- **fuera de alcance**:
  - `AdminSite` restringido por `es_administrador`, historial en `User` (plan de autenticación);
  - copia del esquema de planilla en Visita (plan de Visita);
  - cambios en `apps/accounts`, `apps/servicios`, `apps/productos`, `config/`;
  - vistas, API y panel;
  - la imagen del QR.
- **áreas**: dominio (modelos y servicios)
- **seguridad**: sí. Toca datos personales en el historial (H1), el QR (H3), los roles de encargados (H2) y los datos fiscales de clientes (H4). Corre `auditor-seguridad` al cierre.

## Contexto mínimo

- Origen: hallazgos H1–H4 del `auditor-seguridad` en el cierre de `docs/planes/2026-10-02-modelos-dominio.md`, anotados en `docs/bitacora.md` § Problemas abiertos.
- **H1:**
  - en `apps/sitios/models.py:60`, `history = HistoricalRecords()` copia `contacto_en_sitio` y `telefono_en_sitio` a `HistoricalSitio`;
  - borrar un sitio deja la fila `history_type="-"` con todos los datos;
  - decisión 2026-10-02: excluir esos dos campos del historial; `suprimir_sitio()` borra el sitio y sus filas históricas (dirección y coordenadas incluidas).
- **H2:**
  - en `apps/proyectos/models.py:59` y `:66`, `limit_choices_to={"rol": "empleado"}` solo actúa en `full_clean()`;
  - `Proyecto.objects.create(encargado_actual=<administrador>)` se guarda sin error;
  - tampoco filtra `is_active`.
- **H3:**
  - `qr_codigo` (`apps/sitios/models.py:54`) es `editable=False` y no hay forma de rotarlo si la etiqueta se filtra;
  - regenerarlo invalida la etiqueta impresa, por eso también se borra `qr_impreso_el`.
- **H4:** en `apps/clientes/models.py:15-17`, el CUIT solo valida 11 dígitos. Se agrega el dígito verificador por módulo 11:
  - pesos `5,4,3,2,7,6,5,4,3,2` sobre los primeros 10 dígitos;
  - `dv = 11 - suma % 11`, con 11 → 0 y 10 → 9.
- Las reglas van en `services.py` o en validadores, nunca en `admin.py`: `.claude/skills/convenciones-proyecto/SKILL.md:100`. Las migraciones las genera `makemigrations`, sin edición a mano.
- Las tres subtareas tocan apps disjuntas y corren en paralelo, cada una en su worktree con una junction a `venv/`. Una subtarea queda `hecha` recién después del merge, porque el hook corre los criterios desde la raíz.

## Subtareas

### T1 — Sacar el contacto del historial de Sitio, suprimir sitios y regenerar el QR

- **Depende de**: —
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/admin.py`, `apps/sitios/services.py`, `apps/sitios/migrations/`, `apps/sitios/tests/test_models.py`, `apps/sitios/tests/test_services.py`, `apps/sitios/tests/test_admin.py`
- **No puede tocar**: `docs/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/proyectos/`, `apps/servicios/`, `apps/productos/`, `apps/sitios/migrations/0001_initial.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones de código; `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices
- **Worktree**: sí (`worktrees/auditoria-dominio-T1`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 350 líneas agregadas (incluye la migración autogenerada)
- **Qué hacer**:
  - `history = HistoricalRecords(excluded_fields=["contacto_en_sitio", "telefono_en_sitio"])` y su migración `0002` generada con `makemigrations sitios`.
  - `apps/sitios/services.py`:
    - `suprimir_sitio(sitio)`: dentro de `transaction.atomic()`, guarda el `pk`, borra el sitio y después `Sitio.history.filter(id=pk).delete()`. Si el sitio tiene proyectos, el `PROTECT` levanta `ProtectedError` y no se borra nada, ni el sitio ni el historial.
    - `regenerar_qr(sitio)`: asigna `uuid.uuid4()` a `qr_codigo`, pone `qr_impreso_el = None` y hace `save()`, que deja rastro en el historial. Devuelve el nuevo código.
    - Docstrings en español.
  - Los tests que crean un `Proyecto` (por ejemplo, `test_suprimir_con_proyectos_no_borra_nada`) usan como encargado un usuario con `rol=User.Rol.EMPLEADO` y activo. Después del merge con T2 el modelo valida los encargados al guardar.
  - `apps/sitios/admin.py`: acción `regenerar_qr` (`@admin.action(description="Regenerar código QR (invalida la etiqueta impresa)")`). Llama a `services.regenerar_qr` por cada sitio seleccionado y avisa con `message_user`. Sin lógica propia.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_historial_no_guarda_contacto_ni_telefono --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.SuprimirSitioTests.test_suprimir_borra_sitio_e_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.SuprimirSitioTests.test_suprimir_con_proyectos_no_borra_nada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.RegenerarQrTests.test_regenerar_qr_cambia_codigo_y_borra_fecha_de_impresion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_accion_regenerar_qr_cambia_el_codigo --keepdb`
  - `[grep-1]` `grep -n 'excluded_fields=\["contacto_en_sitio", "telefono_en_sitio"\]' apps/sitios/models.py`
  - `[grep-1]` `grep -n "def suprimir_sitio" apps/sitios/services.py`
  - `[grep-1]` `grep -n "def regenerar_qr" apps/sitios/services.py`
  - `[grep-0]` `grep -n "uuid" apps/sitios/admin.py`
  - `[cmd]` `ls apps/sitios/migrations/0002_*.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/sitios`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-auditoria-dominio.md auditoria-dominio)" 350 apps/sitios`

### T2 — Validar en save() que los encargados sean empleados activos

- **Depende de**: —
- **Puede tocar**: `apps/proyectos/models.py`, `apps/proyectos/migrations/`, `apps/proyectos/tests/test_models.py`
- **No puede tocar**: `docs/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/sitios/`, `apps/servicios/`, `apps/productos/`, `apps/proyectos/migrations/0001_initial.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones de código; `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices
- **Worktree**: sí (`worktrees/auditoria-dominio-T2`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 200 líneas agregadas (incluye la migración autogenerada)
- **Qué hacer**:
  - Constante de módulo `FILTRO_ENCARGADO = {"rol": User.Rol.EMPLEADO, "is_active": True}`, con `from apps.accounts.models import User`, usada como `limit_choices_to` en los dos encargados. Su migración `0002` se genera con `makemigrations proyectos`.
  - `Proyecto.save()` valida antes de `super().save()`, con `self._meta.get_field(campo).validate(getattr(self, f"{campo}_id"), self)`, **solo los encargados que se asignan**:
    - al crear, `encargado_inicial` y `encargado_actual`;
    - al editar, solo el encargado cuyo `_id` cambió respecto del valor guardado en la base.

    Así levanta `ValidationError` aunque no se haya llamado a `full_clean()`. Además, dar de baja o cambiar de rol a un empleado ya asignado no bloquea guardados posteriores del proyecto: el encargado inicial "se fija al crear" (§3.5) y el flujo de visita guarda el proyecto (§3.6). Docstring en español.
  - El test existente `test_encargado_debe_ser_empleado` tiene que seguir en verde.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_create_con_encargado_administrador_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_encargado_inactivo_no_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_baja_del_encargado_no_bloquea_guardar_el_proyecto --keepdb`
  - `[grep-1]` `grep -n "FILTRO_ENCARGADO = " apps/proyectos/models.py`
  - `[grep-0]` `grep -n 'limit_choices_to={"rol": "empleado"}' apps/proyectos/models.py`
  - `[cmd]` `ls apps/proyectos/migrations/0002_*.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/proyectos`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-auditoria-dominio.md auditoria-dominio)" 200 apps/proyectos`

### T3 — Validar el dígito verificador del CUIT

- **Depende de**: —
- **Puede tocar**: `apps/clientes/models.py`, `apps/clientes/validators.py`, `apps/clientes/migrations/`, `apps/clientes/tests/test_models.py`
- **No puede tocar**: `docs/`, `config/`, `apps/accounts/`, `apps/sitios/`, `apps/proyectos/`, `apps/servicios/`, `apps/productos/`, `apps/clientes/migrations/0001_initial.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones de código
- **Worktree**: sí (`worktrees/auditoria-dominio-T3`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 150 líneas agregadas (incluye la migración autogenerada)
- **Qué hacer**:
  - `apps/clientes/validators.py` con `validar_cuit(valor)` por módulo 11, como dice el Contexto mínimo. Levanta `ValidationError("El dígito verificador del CUIT no es válido.")`.
  - El validador va en `Cliente.cuit.validators`, después del `RegexValidator`. Si el valor no tiene 11 dígitos, `validar_cuit` no hace nada: ese error ya lo da el regex. Migración `0002` generada con `makemigrations clientes`.
  - El test existente `test_cuit_valido_pasa` usa `20123456789`, que tiene el dígito verificador mal. Hay que cambiarlo por `20123456786`, que es válido: la suma ponderada da 148, 148 % 11 = 5 y 11 − 5 = 6.
  - `test_validar_cuit_solo_acepta_el_digito_correcto` llama directo a `apps.clientes.validators.validar_cuit` con `2012345678X` para X de 0 a 9. Solo X=6 pasa; los otros nueve levantan `ValidationError`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_models.ClienteTests.test_cuit_con_digito_verificador_invalido_no_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_models.ClienteTests.test_validar_cuit_solo_acepta_el_digito_correcto --keepdb`
  - `[grep-1]` `grep -n "def validar_cuit" apps/clientes/validators.py`
  - `[grep-1]` `grep -n "validar_cuit" apps/clientes/models.py`
  - `[cmd]` `ls apps/clientes/migrations/0002_*.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/clientes`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-auditoria-dominio.md auditoria-dominio)" 150 apps/clientes`

## Trabajo del principal (integración)

Al terminar la ola, el principal:
- revisa `bash .claude/hooks/cambios.sh . main`;
- mergea `auditoria-dominio-T1`, `-T2` y `-T3` a `main`;
- quita las junctions con `cmd //c rmdir`, los worktrees y las ramas;
- corre `git status` y `git worktree list`.

No lleva criterios propios, porque el hook no los ejecuta fuera de `### T<n>`. Lo que comprueba la integración es que los criterios de T1–T3 pasen en la raíz y los de cierre global.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-02-auditoria-dominio.md auditoria-dominio`

## Registro de verificación

commit_base: 4d8223d

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-02 | T1 | 1298e73 (worktree) · 9b2115d (main) | PASA (worktree: verificador 14/14, verificador-b 15/15 [conteo propio]; main: verificador 14/14) | ruta: delegada · commit T1: 1298e73 · merge c5174c1 · `# noqa: E501` en models.py:60 por el grep de una línea |
| 2026-10-02 | T2 | 20456ae (worktree) · 9b2115d (main) | PASA (worktree: verificador 10/10, verificador-b 10/10; main: verificador 10/10) | ruta: delegada · commit T2: 20456ae · merge 99c2008 |
| 2026-10-02 | T3 | 07e536e (worktree) · 9b2115d (main) | PASA (worktree: verificador 9/9, verificador-b 9/9; main: verificador 9/9) | ruta: delegada · commit T3: 07e536e · merge 9b2115d |
| 2026-10-02 | TODO | 64fb555 | PASA (verificador 40/40: T1 14, T2 10, T3 9, cierre global 7) | auditor-seguridad: H2 y H4 CERRADOS; H1 y H3 CERRADO PARCIAL; nuevos H1-a y H3-a importantes, abiertos en la bitácora |
