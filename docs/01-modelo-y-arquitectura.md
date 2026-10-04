# MAControl S.A. — Modelo de datos y arquitectura

Versión 0.2 · 29/09/2026 · incorpora respuestas de la administración · Base para `CLAUDE.md` y las migraciones iniciales.

## 1. Alcance

Un solo proyecto Django con tres superficies sobre una misma base de datos:

| Superficie | Quién la usa | Tecnología |
|---|---|---|
| Web pública (`macontrol.com.ar`) | Visitantes | Django templates + Tailwind |
| Panel de gestión (`/panel/`) | Administradores | Django templates + HTMX + Leaflet |
| API (`/api/v1/`) | App móvil Expo (última etapa) | Django REST Framework + JWT |

**Fuera de alcance (etapa 1):** presupuestos, facturación, acceso de clientes, notificaciones push/correo, diseño de rutas, QR para clientes.

## 2. Roles

Dos roles, sobre `AUTH_USER_MODEL` propio (`accounts.User`) con campo `rol`:

- **Administrador** — accede al panel. Crea clientes, sitios y proyectos; asigna visitas; carga visitas manuales; genera QR, informes y certificados; crea cuentas (no hay autorregistro).
- **Empleado** — accede solo a la API desde la app. Ve sus visitas asignadas, escanea QR, completa la planilla, consulta su historial y lo descarga.

El superusuario de Django es un administrador con acceso al `/admin/` técnico; el panel de gestión es una interfaz propia, no el admin.

## 3. Entidades

```
Cliente 1──n Sitio 1──n Proyecto 1──n Visita n──1 Empleado
                │                        │
                └── qr_codigo (uno)      └── n Foto, n ProductoAplicado
Proyecto n──1 TipoServicio 1──n CampoPlanilla
```

### 3.1 `clientes.Cliente`
`razon_social`, `cuit` (opcional), `contacto_nombre`, `contacto_telefono`, `contacto_email`, `notas`, `activo`, `creado`, `actualizado`.

### 3.2 `sitios.Sitio` — el lugar físico; lo que aparece en el mapa
- `cliente` (FK), `nombre` (ej. "Planta Chascomús"), `direccion`, `localidad`, `latitud`, `longitud`
- `sector` (choices: industria, puerto, gastronomía, hotelería, edificio, salud, educación, rural, espacio_verde, transporte, hogar, otro)
- `contacto_en_sitio`, `telefono_en_sitio`, `horario_acceso`, `notas`
- `qr_codigo` — UUID único, generado al crear; **es el contenido del QR**. Un QR por sitio.
- `qr_impreso_el` (fecha, opcional) para saber si la etiqueta ya fue colocada
- `activo`, `creado`, `actualizado`

Regla: el QR identifica al sitio, no al proyecto. Al escanear, la app recibe los proyectos activos de ese sitio y el empleado elige cuál está atendiendo (si hay uno solo, se abre directo).

### 3.3 `servicios.TipoServicio` — catálogo
`nombre`, `slug`, `descripcion`, `activo`. Sirve tanto al panel (planillas) como a la web pública (páginas de servicio). Carga inicial: los 12 servicios de la Carta de Servicios más mantenimiento edilicio.

### 3.4 `servicios.CampoPlanilla` — la planilla que aparece tras escanear
Cada tipo de servicio define sus campos; la app los renderiza dinámicamente y el panel los muestra en el historial.
- `tipo_servicio` (FK), `orden`, `etiqueta`, `clave` (slug interno)
- `tipo` (choices: texto, numero, booleano, opcion, opcion_multiple, fecha)
- `opciones` (JSON, para tipo opción), `obligatorio`, `ayuda`

Ejemplo — Control de roedores: `estaciones_revisadas` (número), `estaciones_con_consumo` (número), `cebo_repuesto` (booleano), `observaciones` (texto).
Ejemplo — Exclusión de aves: `estado_redes` (opción: bueno/dañado/no aplica), `estado_pinches` (opción), `sellado_realizado` (booleano).

### 3.5 `proyectos.Proyecto` — el trabajo recurrente en un sitio
- `sitio` (FK), `tipo_servicio` (FK), `titulo`, `detalle` (texto largo)
- `estado` (choices: activo, pausado, finalizado)
- `frecuencia_dias` (entero, opcional; null = sin frecuencia fija) y `proxima_visita` (fecha, opcional; editable a mano)
- `encargado_inicial` (FK User, se fija al crear) y `encargado_actual` (FK User; se actualiza con cada visita)
- `creado`, `actualizado` (= fecha/hora de la última visita o edición)

Propiedades derivadas (no columnas): `ultima_visita`, `estado_visita` (al día / próxima a vencer / vencida / sin programar), usadas para colorear el mapa.

### 3.6 `visitas.Visita` — cada intervención registrada
- `proyecto` (FK), `empleado` (FK User)
- `origen` (choices: `app` = escaneo de QR, `manual` = cargada por un administrador). La app **no puede** crear visitas sin escaneo válido; el administrador sí, con `origen=manual` y campo `motivo_manual` obligatorio (ej. "QR ilegible, datos enviados por WhatsApp")
- `programada_para` (fecha, opcional) y `asignada_por` (FK User, opcional): una visita puede existir antes de realizarse, como asignación del jefe
- `realizada_en` (datetime; null = pendiente), `estado` (pendiente, realizada, cancelada)
- `latitud`, `longitud`, `precision_m` — ubicación del teléfono al escanear
- `datos` (JSON) — respuestas a los `CampoPlanilla` del tipo de servicio, validadas contra la definición
- `observaciones`, `incidencia` (booleano) + `incidencia_detalle`
- `creado`, `actualizado`

Al guardar una visita realizada: `proyecto.encargado_actual = empleado`, `proyecto.actualizado = now`, y si `frecuencia_dias` está definida, `proxima_visita = realizada_en + frecuencia_dias`.

### 3.7 `visitas.Foto`
`visita` (FK), `imagen`, `tomada_en`, `orden`. Mínimo una foto por visita realizada desde la app (validación en el serializer).

### 3.8 `visitas.ProductoAplicado` — confirmado por la empresa
`visita` (FK), `producto` (FK a `productos.Producto`), `lote`, `dosis`, `unidad`, `cantidad`. La planilla de toda visita incluye una sección "Productos utilizados": el empleado **elige de la lista precargada** (no escribe nombres) y completa lote y dosis. Puede agregar varios. `CampoPlanilla` no la modela porque es común a todos los servicios; se define en el serializer.

### 3.9 `productos.Producto` — catálogo precargado por administradores
`nombre_comercial`, `principio_activo`, `registro` (ANMAT/SENASA), `presentacion`, `unidad_dosis_por_defecto`, `activo`. Los administradores lo mantienen desde el panel; la app lo descarga y lo guarda en caché para funcionar sin conexión.

### 3.10 `informes.Certificado` — generado automáticamente
Reemplaza el certificado que hoy se hace a mano. Se crea desde la ficha del proyecto o del cliente eligiendo un rango de fechas; toma:
- del cliente: `razon_social`, `cuit`, domicilio del sitio
- de las visitas del rango: fechas, tipo de servicio, productos aplicados con registro ANMAT/SENASA, lote y dosis, empleado que aplicó
- de la empresa: datos legales, habilitaciones, director técnico (desde `web.Configuracion`)

Campos: `proyecto` (FK) o `cliente` (FK), `desde`, `hasta`, `numero` (correlativo anual, ej. `2026-0041`), `generado_por`, `generado_el`, `pdf` (archivo), `visitas` (M2M con las incluidas). Una vez emitido no se edita; si hay que corregir, se emite uno nuevo que referencia al anterior. El diseño del PDF se ajusta cuando la empresa envíe un ejemplo del certificado actual; la estructura de datos no cambia.

### 3.11 `accounts.User`
Extiende `AbstractUser`: `rol` (administrador/empleado), `telefono`, `activo`. Los empleados no tienen `is_staff`.

### 3.12 `web` — contenido de la web pública
`web.PaginaServicio` (1:1 con `TipoServicio`): `titulo_seo`, `resumen`, `problema`, `metodos` (JSON: título + descripción), `adicional`, `faq` (JSON), `sectores` (M2M a choices), `imagen_portada`, `publicado`. `web.Cliente destacado`: `nombre`, `logo`, `orden`. `web.Configuracion` (singleton): teléfono, WhatsApp, correo, direcciones, horario, redes. Toda la web pública lee de aquí; nada queda escrito en plantillas.

## 4. Flujos

### 4.1 Empleado (app)
1. Inicia sesión (JWT). `GET /api/v1/me/visitas/?estado=pendiente` → lista de asignaciones.
2. Escanea QR → `POST /api/v1/qr/{codigo}/resolver/` → devuelve sitio + proyectos activos + planilla de cada uno. Si el sitio no existe o está inactivo, error explícito.
3. Elige proyecto (o se abre directo si es único). Si tiene una visita pendiente asignada para ese proyecto, la app la usa; si no, crea una nueva (`origen=app`).
4. Completa planilla, agrega los productos utilizados eligiendo del catálogo (lote y dosis), saca ≥1 foto (la app redimensiona a 1600 px de lado mayor antes de subir: el servidor rechaza JPEG progresivos de más de 16 MP y WebP de más de 8 MP), opcionalmente marca incidencia. `POST /api/v1/visitas/` con multipart (JSON + fotos + geolocalización). Sin conexión: se guarda local y se reintenta; el servidor acepta `realizada_en` del cliente y guarda además `recibida_en`.
5. `GET /api/v1/me/historial/` y `GET /api/v1/me/historial.pdf` para descargar su propio historial.

### 4.2 Administrador (panel)
- **Mapa** (`/panel/mapa/`): todos los sitios activos, color por peor `estado_visita` de sus proyectos; popup con proyectos, última visita, encargado actual, botón "asignar visita".
- **Proyectos** (`/panel/proyectos/`): tabla filtrable (cliente, sitio, servicio, estado, encargado, vencidos), ordenable por `proxima_visita`.
- **Ficha de proyecto**: datos, historial de visitas con fotos y planilla, línea de tiempo, botones "asignar visita", "cargar visita manual", "generar certificado".
- **Asignar visita**: elige empleado y fecha → crea `Visita` pendiente. El empleado la ve en su lista.
- **Sitios**: alta con geocodificación asistida (mapa clicable para fijar el punto) y botón "descargar QR" (PNG/PDF con nombre del sitio y logo, listo para plastificar).
- **Usuarios**: alta manual de administradores y empleados.
- **Productos**: catálogo con alta/baja y registro ANMAT/SENASA; lo que el empleado ve en la app.
- **Certificados**: desde la ficha del proyecto o del cliente, rango de fechas → PDF numerado con cliente, CUIT, fechas, productos con registro, lote y dosis. Se guarda y se puede volver a descargar.
- **Informes**: por cliente y rango de fechas → PDF con visitas, planillas, fotos y productos (más detallado que el certificado, uso interno o para el cliente).

## 5. Estructura del repositorio

```
macontrol/
├── CLAUDE.md
├── .claude/                 # skills y comandos de Claude Code (etapa siguiente)
├── docs/
│   ├── bitacora.md · decisiones.md · plantilla-plan.md · planes/
│   ├── 00-contenido-fuente.md        # transcripción de la Carta de Servicios
│   ├── 01-modelo-y-arquitectura.md   # este documento
│   └── 02-diseno.md                  # tokens del sistema visual (dirección A)
├── config/                  # settings (base/dev/prod), urls, asgi/wsgi
├── apps/
│   │                        # cada app de dominio es dueña de lo suyo:
│   │                        #   models · services · admin · migrations
│   │                        #   serializers · api_views · api_urls.py (app_name = "<app>")
│   │                        #   panel_views · panel_urls.py · panel_forms
│   │                        #   templates/<app>/{panel,pdf}/… · tests/
│   ├── accounts/            # User, roles, permisos
│   ├── clientes/
│   ├── sitios/              # Sitio, QR, geocodificación
│   ├── servicios/           # TipoServicio, CampoPlanilla
│   ├── proyectos/
│   ├── visitas/             # Visita, Foto, ProductoAplicado, reglas de actualización
│   ├── productos/
│   ├── informes/            # generación de PDF (informes, certificados, historial, QR)
│   ├── panel/               # layout, login, tablero, mapa; urls.py = router de una línea por app
│   ├── api/                 # transversal: JWT, permisos base, paginación; urls.py = router por app
│   └── web/                 # sitio público: páginas, contenido, SEO
├── templates/               # solo base.html y panel/base.html
├── static/                  # tailwind, htmx, leaflet, logo
├── media/                   # fotos de visitas, logos, QR generados (fuera de git)
├── pyproject.toml           # ruff; dependencias en requirements.txt
├── docker-compose.yml       # postgres + app
└── .env.example
```

## 6. Decisiones técnicas

- **Python 3.13, Django 5.x, PostgreSQL (SQLite por defecto en desarrollo si no hay `DATABASE_URL`).** Sin PostGIS en etapa 1: lat/lng como `DecimalField`; el mapa es Leaflet con OpenStreetMap (sin costo ni clave de API). Si más adelante hacen falta consultas espaciales, migrar a PostGIS es directo.
- **Panel con templates + HTMX**, no un frontend separado: menos superficie de mantenimiento y coherente con el sitio público.
- **API versionada** (`/api/v1/`) desde el primer día aunque la app llegue al final: el panel también puede consumirla para el mapa.
- **JWT** (`djangorestframework-simplejwt`) con refresh largo para el empleado.
- **Contrato de la app**: `docs/api/openapi-v1.yaml` es el contrato de `/api/v1/` que consume la app. Todo cambio de respuesta, de parámetro o de versión de drf-spectacular exige regenerarlo en el mismo commit con `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file docs/api/openapi-v1.yaml`; un criterio de cierre lo compara con el generado.
- **Fotos**: redimensionadas al subir (máx. 1600 px) con `Pillow`; almacenamiento local en etapa 1, backend intercambiable (`django-storages`) para S3/R2.
- **PDF**: WeasyPrint desde templates HTML (`templates/pdf/`), mismo sistema visual que la web.
- **QR**: `segno` o `qrcode`, contenido `https://macontrol.com.ar/q/{uuid}`. Abierto en un navegador común muestra solo "Sitio de MAControl S.A. — use la app"; la app intercepta la URL.
- **Auditoría**: `django-simple-history` en Proyecto, Sitio y Visita para saber quién cambió qué.
- **Tests**: runner de Django (`manage.py test --keepdb`), un `tests/` por app; los flujos 4.1 y 4.2 tienen tests de integración desde el inicio.
- **Calidad**: `ruff` para lint y formato.

## 7. Pendientes de definición

1. Un ejemplo del certificado que entregan hoy, para respetar su diseño y texto legal (una foto o PDF alcanza).
2. Si lote y dosis son obligatorios siempre o pueden quedar vacíos en algún servicio (por defecto: obligatorios).
3. Campos concretos de la planilla para cada uno de los 12 servicios (propongo un borrador y la empresa corrige).
4. Si el número 02241 49 6047 atiende WhatsApp.
5. Horario de atención para la web.
