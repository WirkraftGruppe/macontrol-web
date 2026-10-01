# Django Patterns Avanzados

## Custom Manager + QuerySet

```python
class MyQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_counts(self):
        return self.annotate(items_count=Count('items'))

class MyManager(models.Manager):
    def get_queryset(self):
        return MyQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()
```

## Signals (usar con moderación)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=MyModel)
def on_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Creado: {instance}")
```

## Data Migrations

```python
def forward(apps, schema_editor):
    Model = apps.get_model('app', 'Model')
    Model.objects.filter(old_field=True).update(new_field='value')

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
```

## Split Settings

```
settings/
├── __init__.py    # from .dev import * (o prod)
├── base.py        # Común
├── dev.py         # DEBUG=True, SQLite
└── prod.py        # DEBUG=False, PostgreSQL
```

## Middleware Custom

```python
class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"{request.method} {request.path}")
        return self.get_response(request)
```
