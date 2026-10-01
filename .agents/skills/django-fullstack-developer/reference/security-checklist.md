# Security Checklist Django

## Settings Producción
- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` desde variable de entorno
- [ ] `ALLOWED_HOSTS` configurado
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_HSTS_SECONDS` configurado
- [ ] `X_FRAME_OPTIONS = 'DENY'`

## Autenticación JWT
- [ ] Access token: vida corta (1h)
- [ ] Refresh token: vida moderada (7d)
- [ ] Rotate refresh tokens
- [ ] Blacklist after rotation

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## API
- [ ] `permission_classes` en TODOS los ViewSets
- [ ] Throttling configurado
- [ ] Validación de input vía serializers
- [ ] No exponer IDs secuenciales (usar UUID)

## Queries
- [ ] No concatenar strings en queries (usar ORM)
- [ ] Validar parámetros de filtros
- [ ] Limitar resultados con paginación

## General
- [ ] No commitear `.env`
- [ ] Logging de errores (no `print()`)
- [ ] `python manage.py check --deploy` sin errores
