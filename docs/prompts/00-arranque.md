# Prompt de arranque — esqueleto del proyecto

Para pegar en Claude Code, en modo plan, en la raíz del repositorio después de `git init` y del primer commit de la base.

```
Crear el esqueleto del proyecto Django de MAControl según docs/01-modelo-y-arquitectura.md §5 y §6, sin lógica de negocio todavía.

Leer antes de planificar: docs/01-modelo-y-arquitectura.md, .claude/skills/convenciones-proyecto/SKILL.md.

Alcance:
- config/ con settings/{__init__,base,dev,prod}.py seleccionados por DJANGO_ENV, urls.py con los prefijos /, /q/<uuid>/, /panel/, /admin/, /api/v1/ apuntando a vistas vacías (200 con texto).
- apps/ con las once apps de §5 (accounts, clientes, sitios, servicios, proyectos, visitas, productos, informes, panel, api, web), cada una con apps.py, models.py vacío, urls.py, tests/__init__.py.
- accounts.User como AUTH_USER_MODEL con campo rol (administrador | empleado), properties es_administrador y es_empleado, migración 0001.
- requirements.txt (Django 5, DRF, simplejwt, psycopg, django-environ, django-simple-history, django-storages, Pillow, WeasyPrint, segno, ruff) y pyproject.toml con la configuración de ruff.
- .env.example con las variables de convenciones-proyecto § Variables de entorno.
- templates/base.html con los tokens de docs/02-diseno.md como variables CSS (temas oscuro y claro por atributo data-tema) y static/img/logo*.png copiados desde la raíz del repo (Logo Imagen.png y variantes) si existen.
- manage.py check, makemigrations --check y test en verde con el runner de Django; ruff check sin errores.

Fuera de alcance:
- Modelos distintos de User; vistas reales; panel; API; serializers; Tailwind compilado; despliegue; app móvil.

Criterios de aceptación:
- [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check → exit 0
- [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run → exit 0
- [test] apps.accounts.tests.test_user.UserTests.test_rol_administrador_y_empleado_son_excluyentes
- [test] apps.accounts.tests.test_user.UserTests.test_is_staff_no_implica_administrador
- [grep-1] grep -n "AUTH_USER_MODEL = \"accounts.User\"" config/settings/base.py
- [grep-0] grep -rn "fields = \"__all__\"" apps/
- [existe] .env.example
- [cmd] ./venv/Scripts/python.exe -m ruff check . → exit 0
```

Supuestos: venv en `./venv` creado a mano antes de la sesión; PostgreSQL local o `DATABASE_URL` de SQLite para el arranque.
