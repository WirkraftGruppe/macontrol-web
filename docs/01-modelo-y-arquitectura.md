# MAControl S.A. — Modelo de contenido y arquitectura del sitio

Versión 0.4 · 17/10/2026 · el repositorio queda solo con el sitio público (`docs/planes/2026-10-17-web-independiente.md`) · Base para `CLAUDE.md` y las migraciones de `apps/web`.

## 1. Alcance

Este repositorio es el sitio público de MAControl S.A. (`macontrol.com.ar`): un proyecto Django con una sola app de contenido, `apps/web`.

| Superficie | Quién la usa | Tecnología |
|---|---|---|
| Sitio público (`/`) | Visitantes | Django templates + CSS propio (`static/css/web.css`) |
| Admin de Django (`/admin/`) | Quien edita el contenido | `django.contrib.admin` con vista previa |

El panel de gestión, la API y la app móvil viven en otro repositorio y no comparten código ni base de datos con este.

**Fuera de alcance:** formularios de contacto o presupuesto (el contacto es el teléfono y WhatsApp), cuentas de clientes, comentarios, buscador, panel de contenido propio.

## 2. Acceso

No hay roles. El único acceso es el del superusuario de `django.contrib.auth.User`, que entra a `/admin/` para editar el contenido. Las cuentas se crean con `createsuperuser`; no hay autorregistro ni recuperación de contraseña pública. El login del admin tiene límite de intentos por IP y usuario (`config/limites.py`, `config/red.py`).

## 3. Modelo de contenido

Tres modelos independientes (`Configuracion`, `Servicio`, `ClienteDestacado`) y una lista de opciones (`Sector`); ninguno tiene claves foráneas.

Toda la web pública lee de estos modelos; los textos fijos que deja el diseño aprobado (`_respaldos.html`, `servicio.html`) son la única excepción.

### Servicio
Una página de servicio (`/servicio/<slug>/`). Campos: `nombre`, `slug` (único), `titulo_seo`, `resumen`, `problema` (el texto principal), `metodos` (JSON: título + descripción de cada método), `adicional` (servicio adicional, opcional), `faq` (JSON: pregunta + respuesta; puede estar vacía), `sectores` (JSON con valores de `Sector`, validada), `foto` (imagen ancha de la página), `orden` y `publicado`. El fixture trae 9 servicios: los 8 de la Carta de Servicios más mantenimiento edilicio (`docs/00-contenido-fuente.md`).

### ClienteDestacado
Un logotipo de la franja de clientes. Campos: `nombre`, `logo`, `orden` y `activo`. Solo se publican los logos que la empresa entrega.

### Configuracion
Datos de la empresa, en una sola fila (pk=1). Campos: `razon_social`, `eslogan`, `presentacion`, `telefono`, `whatsapp`, `correo`, `horario`, `direcciones` (JSON: localidad + dirección), `redes` (JSON: nombre + url), y los datos legales de `/empresa/`: `habilitacion`, `ley` y `director_tecnico`. Si `director_tecnico` está vacío, la página muestra "Director técnico matriculado" (la Carta no da nombre).

### Sector
`TextChoices` con los 12 sectores donde trabaja la empresa (Carta de Servicios). No es una tabla: `Servicio.sectores` guarda los valores aplicables a cada servicio.

## 4. Flujos

### 4.1 Edición desde el admin
1. La persona entra a `/admin/` con su cuenta de superusuario.
2. Edita `Configuracion`, los `Servicio` y los `ClienteDestacado`. Los formularios del admin son los de `apps/web/forms.py`: reprocesan las imágenes al subirlas (Pillow, sin EXIF) y validan `redes`.
3. Un cambio de un servicio publicado se ve en el sitio al guardar.

### 4.2 Vista previa y publicación
- Un servicio nuevo nace con `publicado=False`: `/servicio/<slug>/` da 404 .
- La vista previa es una URL del propio ModelAdmin, `/admin/web/servicio/<pk>/vista-previa/`, protegida con `admin_site.admin_view`. Renderiza la plantilla pública aunque el servicio no esté publicado y responde con `X-Robots-Tag: noindex`.
- Publicar es marcar `publicado`. Despublicar lo devuelve al 404 sin borrar el contenido.

### 4.3 Media
- `media/` guarda solo contenido público: logos de clientes y fotos de servicios. No hay fotos de personas ni datos de empleados.
- En desarrollo (`DEBUG`), `config/urls.py` sirve `MEDIA_URL`. En producción el servido de `media/` queda pendiente de decisión; `MEDIA_ROOT` apunta a un volumen (ver `docs/despliegue.md`).

### 4.4 Contenido inicial
`apps/web/fixtures/contenido_inicial.json` carga la configuración, los 9 servicios publicados y los clientes. Una base nueva se llena con `loaddata contenido_inicial`; después se edita desde el admin.

## 5. Estructura del repositorio

```
macontrol-web/
├── CLAUDE.md
├── .claude/                 # skills, agentes y hooks de Claude Code
├── docs/
│   ├── bitacora.md · decisiones.md · plantilla-plan.md · planes/
│   ├── 00-contenido-fuente.md        # transcripción de la Carta de Servicios
│   ├── 01-modelo-y-arquitectura.md   # este documento
│   └── 02-diseno.md                  # tokens del sistema visual
├── config/                  # settings (base/dev/prod), urls, admin con límite de intentos
├── apps/web/                # modelos, admin, vistas, plantillas, fixture y tests del sitio
├── templates/web/           # base_web.html (404.html y 500.html están en apps/web/templates/)
├── static/                  # css/web.css, fuentes, logo y fotos
├── herramientas/humo_web.py # prueba de humo del sitio
├── media/                   # logos y fotos subidos (fuera de git)
├── pyproject.toml           # ruff; dependencias en requirements.txt
└── .env.example
```

## 6. Decisiones técnicas

- **Python 3.13, Django 5.x, PostgreSQL** (SQLite por defecto en desarrollo si no hay `DATABASE_URL`).
- **Admin de Django, no un panel propio**: el contenido cambia pocas veces y lo edita una persona; el admin alcanza y reduce la superficie de ataque.
- **Usuario estándar** (`django.contrib.auth.User`): sin roles ni modelo propio.
- **Imágenes**: reprocesadas al subir con Pillow (sin EXIF); almacenamiento local en un volumen.
- **Seguridad**: CSP con `django-csp`, `Referrer-Policy` con `SecurityMiddleware`, estáticos con `whitenoise`, servidor `gunicorn`.
- **QR impresos**: `/q/<uuid>/` se conserva porque puede haber etiquetas que apuntan al dominio; abierta en un navegador solo muestra "Sitio de MAControl S.A. — use la app" y no consulta la base.
- **Tests**: runner de Django (`manage.py test --keepdb`) y `herramientas/humo_web.py` para la prueba de humo.
- **Calidad**: `ruff` para lint y formato.

## 7. Pendientes de definición

1. Si el número 02241 49 6047 atiende WhatsApp.
2. Horario de atención para la web.
3. Nombre y matrícula del director técnico (hoy la página muestra "Director técnico matriculado").
4. Servido de `media/` en producción.
