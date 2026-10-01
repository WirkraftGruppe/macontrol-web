# Skill: Django Full Stack Developer

Conocimiento experto en Django, DRF, Celery, Redis y Railway para desarrollo full stack.

## ⚡ Economía de Tokens

- NO generar documentación a menos que se solicite
- Docstrings breves (1 línea)
- Código autodocumentado sobre comentarios extensos
- Preguntar: "¿Deseas que genere documentación?"

## Cuándo Usar

Cualquier tarea genérica de Django:
- Modelos, vistas, serializers, URLs
- APIs REST con DRF
- Optimización de queries
- Seguridad y autenticación JWT
- Celery tasks y Redis cache
- Testing y debugging
- Deploy en Railway

## Convenciones

### Imports (orden)
```python
import uuid                              # stdlib
from django.db import models             # django
from rest_framework import serializers   # third-party
from .models import MyModel              # local
```

### Naming
- Modelos: `PascalCase`
- Views/Serializers: `PascalCase` con sufijo descriptivo
- Funciones/variables: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Docstrings/comentarios: **español**

### Logger obligatorio
```python
import logging
logger = logging.getLogger(__name__)
```

## Django Patterns

### Modelos
- `UUIDField` para PKs públicas
- `verbose_name` en campos y Meta
- Índices en campos frecuentemente filtrados
- Custom Manager/QuerySet para queries reutilizables
- Validators en campos numéricos

### Queries - Evitar N+1
```python
# ❌ Malo
for obj in MyModel.objects.all():
    print(obj.related.name)  # query por iteración

# ✅ Bueno
for obj in MyModel.objects.select_related('related'):
    print(obj.related.name)  # 0 queries extra

# ✅ Anotar conteos
MyModel.objects.annotate(items_count=Count('items'))
```

### Serializers DRF
- `ModelSerializer` para CRUD estándar
- Validación en `validate()` o `validate_<field>()`
- `SerializerMethodField` para campos computados
- Serializers separados por acción (Create, Update, List)

### ViewSets DRF
- `get_queryset()` optimizado con select/prefetch
- `get_serializer_class()` según acción
- `@action` para endpoints custom
- Permisos con `permission_classes`
- Throttling para rate limiting

### Seguridad
- Nunca hardcodear secrets → `os.environ.get()`
- JWT con `djangorestframework-simplejwt`
- Permisos en TODOS los ViewSets
- Validar input con serializers
- CSRF/XSS protección activa

## Celery

### Task pattern
```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def my_task(self, arg):
    try:
        # lógica
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

## Redis Cache

```python
from django.core.cache import cache

cache.set('key', data, timeout=300)  # 5 min
cached = cache.get('key')
cache.delete('key')  # invalidar
```

## Testing

```python
from rest_framework.test import APITestCase

class MyAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get('/api/resource/')
        self.assertEqual(response.status_code, 200)
```

## Deploy Railway

- `Procfile`: `web: gunicorn project.wsgi --bind 0.0.0.0:$PORT`
- `requirements.txt` actualizado
- WhiteNoise para static files
- Variables de entorno para secrets
- `python manage.py check --deploy` antes de deployar

## Comandos Frecuentes

```bash
python manage.py check                    # validar config
python manage.py check --deploy           # validar producción
python manage.py makemigrations           # crear migraciones
python manage.py migrate                  # aplicar migraciones
python manage.py test --parallel          # tests
python manage.py makemigrations --check   # verificar pendientes
```
