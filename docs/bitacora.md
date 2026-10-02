# Bitácora de MAControl

## Estado actual
Plan activo: (ninguno; `modelos-dominio` cerrado con TODO PASA 51/51)
Rama: main
Pendiente inmediato: decidir el hallazgo H1 del auditor (historial de Sitio con datos de contacto) antes de cargar datos reales; después, plan de Visita.
Problemas abiertos:
- [importante, abierto, decisión del usuario] Auditoría de `modelos-dominio`, H1: `HistoricalSitio` guarda `contacto_en_sitio`, `telefono_en_sitio`, dirección y coordenadas sin mecanismo de borrado. Ante una supresión (Ley 25.326, art. 16), la fila histórica queda. Opciones: (a) `excluded_fields=["contacto_en_sitio", "telefono_en_sitio"]`; (b) mantenerlos con un procedimiento de supresión o `clean_old_history --days N`. Las dos requieren una migración: conviene decidir antes de tener datos reales.
- [menor, abierto] Auditoría de `modelos-dominio`:
  - H2: el `limit_choices_to` de los encargados de Proyecto solo se aplica con `full_clean` (no en `create()`/`save()`) y no filtra `is_active`. Propuesta: validar en `save()` y usar `User.Rol.EMPLEADO`.
  - H3: `qr_codigo` no se puede rotar si la etiqueta se filtra. Propuesta: una acción `regenerar_qr()` en el plan de panel/QR.
  - H4: el CUIT no valida el dígito verificador (módulo 11).
- Para el plan de Visita (auditor): guardar una copia del esquema de planilla en cada Visita. `CampoPlanilla` no tiene historial, y cambiar una `clave` cambia cómo se leen las planillas viejas.
- [importante, abierto, diferido al plan de despliegue por decisión del usuario: hoy es solo desarrollo] La barrera de `config/settings/dev.py` solo mira `ALLOWED_HOSTS`. Con `DJANGO_ENV=development` y `ALLOWED_HOSTS` vacío en un hosting, el sitio arranca con `DEBUG=True` y la página técnica del 400 expone tracebacks y settings; con `runserver`, también `DATABASE_URL`, porque no coincide con el patrón de ocultamiento (comprobado por el auditor). Propuesta del auditor: abortar si hay variables propias del hosting (`RAILWAY_ENVIRONMENT`, `RENDER`, `DYNO`, `FLY_APP_NAME`, `K_SERVICE`…), que hay que ajustar al hosting real. [menor] Las IP privadas en `ALLOWED_HOSTS` no limitan quién se conecta (el Host lo elige el cliente). (El `.strip()` de `ALLOWED_HOSTS` ya está corregido: plan `hosts-espacios`.)
- El plan de autenticación tiene que invertir `test_panel_responde_200` y `test_api_v1_responde_200` (hoy fijan el acceso anónimo) y seguir la lista de condiciones del auditor: mixin por `es_administrador`, DRF con `IsAuthenticated` y JWT, `AdminSite` restringido, `simple_history` en `User` con `excluded_fields=["password", "last_login"]` (si no, copia el hash, y con el middleware de historial ya activo cada login genera un registro), LOGGING sin datos personales y CSP.
- WeasyPrint está instalado pero no se probó en tiempo de ejecución (en Windows suele necesitar GTK/Pango).
- Observación del verificador: `apps/web/tests/test_base.py:13` no distingue el atributo `data-tema="oscuro"` del selector CSS.
- Falta el ejemplo del certificado que la empresa entrega hoy (diseño y texto legal del PDF). Ver `docs/01-modelo-y-arquitectura.md` § 7.
- Falta confirmar si el 02241 49 6047 atiende WhatsApp y el horario de atención para el sitio público.
- Las planillas por servicio (`CampoPlanilla`) se cargan como fixtures provisorias y se editan a mano con lo que usen realmente los encargados y operarios.
- Logo: se usa provisoriamente el de "MAControl Group" (`static/img/logo.png`); la razón social en textos es MAControl S.A.

## Entradas (la más reciente arriba)

### 2026-10-02 — Modelos de dominio
Hecho:
- Commit aparte de los cambios a mano del usuario (bad5c80).
- Plan `docs/planes/2026-10-02-modelos-dominio.md`, congelado en ced3334. El juez-plan lo revisó en dos rondas: primero 3 bloqueantes, después 1. Todos se corrigieron antes de congelar.
- Ola 1, en paralelo con worktrees (junction `venv` → raíz, `venv` en `.git/info/exclude`), integrada en c4cb9cb:
  - T1: Cliente y Sitio con QR e historial; simple_history activado (d296031).
  - T2: TipoServicio, CampoPlanilla y fixture de 9 servicios (2215f95).
  - T3: Producto (a272650).
- Ola 2: T4, Proyecto con `estado_visita`, encargados empleados e historial (d126350).
- verificador y verificador-b dieron PASA en cada subtarea. Verificación final: TODO PASA 51/51 en 60d41f8, con 37 tests.
- auditor-seguridad: 0 bloqueantes, 1 importante (H1) y 3 menores, todos abiertos.

A medias:
- Los tests nuevos no se vieron fallar antes de implementar: los implementadores escribieron el test y el modelo juntos.
- El criterio literal `loaddata tipos_servicio` del pedido se reemplazó por un `[test]` que carga el fixture.

### 2026-10-01 — Espacios en ALLOWED_HOSTS
Hecho: plan `docs/planes/2026-10-01-hosts-espacios.md` (congelado en 734d06a, nivel chico, inline). `dev.py` y `prod.py` recortan espacios y descartan vacíos en `ALLOWED_HOSTS` (24e44a0); dos tests nuevos, vistos fallar antes del cambio. Verificación TODO PASA 12/12. El usuario decidió diferir la barrera por hosting y las IP privadas al plan de despliegue: hoy el proyecto es solo desarrollo. · A medias: nada.

### 2026-10-01 — Corrección de los hallazgos de la auditoría del esqueleto
Hecho: plan `docs/planes/2026-10-01-hallazgos-esqueleto.md` (congelado en 8f23dee; juez-plan en dos rondas, pasó de 7 bloqueantes a 1 y ese último se corrigió moviendo el trabajo del principal a T4). T1 barrera de hosts en `dev.py`, `.env.example` sin `DJANGO_ENV` fijo y HSTS de 3600 s sin subdominios ni preload (afdfc0e); T2 `app_name` en web, panel y api (a5f8b65); T3 fuentes Barlow en `static/fonts/` sin Google Fonts, y corrección del test de `data-tema` (a91fc9f); T4 decisiones y `docs/02-diseno.md` (338b81b, inline). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 43/43 en 1c43751. auditor-seguridad: hallazgos 2, 3 y 4 corregidos; el 1 corregido a medias (ver Problemas abiertos). · A medias: el hueco de la barrera, que depende de saber qué hosting se usa.

### 2026-10-01 — Arranque del repositorio y plan esqueleto
Hecho: pasos 2 a 5 de `docs/ARRANQUE.md`. Hooks y 16 skills copiados de TerritoryOS (tests de hooks: 70 OK), `git init`, venv con Python 3.13, `.gitattributes` (`*.sh` en LF), `images-for-content/` fuera de git. Plan `docs/planes/2026-10-01-esqueleto.md` (congelado en 37f1ec7, juez-plan en dos rondas: 4 bloqueantes corregidos antes de congelar): T1 base del proyecto y `accounts.User` con rol (fb08f0f), T2 diez apps y prefijos de URL con vistas provisorias (f9677fa), T3 `base.html` con tokens de ambos temas y logo (ced36a0). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 50/50 en b44c4bf; `check --deploy` con settings de producción sin avisos. auditor-seguridad: 0 bloqueantes, 4 hallazgos abiertos (ver Problemas abiertos). · A medias: nada del plan; los hallazgos del auditor quedan para decidir.

### 2026-09-29 — Base del repositorio
Hecho: se crea la carpeta del proyecto con el esquema de trabajo con agentes copiado de TerritoryOS y adaptado a un solo repositorio Django: `CLAUDE.md`, `.claude/agents/` (implementador, verificador, verificador-b, juez-plan, refutador, auditor-seguridad), `.claude/hooks/`, `.claude/skills/convenciones-proyecto/`, `docs/plantilla-plan.md`, `docs/decisiones.md`. Documentos fuente: `docs/00-contenido-fuente.md` (transcripción de la Carta de Servicios), `docs/01-modelo-y-arquitectura.md` (modelo de datos, roles, flujos, estructura), `docs/02-diseno.md` (tokens del tablero elegido, dirección A "Industrial certificada"). Diseños en el lienzo de claude.ai: https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk · A medias: no hay código; `git init` y primer commit pendientes.
