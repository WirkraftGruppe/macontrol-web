# DRF API Patterns

## ViewSet con múltiples serializers

```python
class MyViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateSerializer
        return DetailSerializer

    def get_queryset(self):
        return Model.objects.select_related('fk').prefetch_related('m2m').order_by('-created_at')
```

## Permisos Custom

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user
```

## Throttling

```python
class BurstThrottle(UserRateThrottle):
    rate = '60/min'

# En ViewSet
throttle_classes = [BurstThrottle]
```

## Paginación

```python
# settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

## Filtros

```python
class MyViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'status']
```

## Respuestas consistentes

```python
# Éxito
return Response(serializer.data, status=status.HTTP_201_CREATED)

# Error
return Response({'error': 'Mensaje claro'}, status=status.HTTP_400_BAD_REQUEST)
```

## Cache en endpoints

```python
from django.core.cache import cache

@action(detail=False)
def cached_list(self, request):
    cache_key = f'list_{request.query_params}'
    data = cache.get(cache_key)
    if data:
        return Response(data)
    queryset = self.get_queryset()
    serializer = self.get_serializer(queryset, many=True)
    cache.set(cache_key, serializer.data, timeout=300)
    return Response(serializer.data)
```
