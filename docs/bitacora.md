# Bitácora de MAControl

## Estado actual
Plan activo: (ninguno)
Rama: main
Pendiente inmediato: decidir qué hacer con los hallazgos abiertos del auditor (abajo) y planificar el siguiente: modelos de dominio (clientes, sitios, servicios, proyectos, productos), según `docs/ARRANQUE.md` paso 6.
Problemas abiertos:
- Auditoría del esqueleto (2026-10-01), sin corregir, a decisión del usuario: [importante] `.env.example` presenta `DJANGO_ENV=development` como requerida y `dev.py` arranca con `DEBUG=True` sin barrera contra hosts no locales; [menor] los nombres de URL `inicio` de `apps/web` y `apps/panel` chocan (sin `app_name`); [menor] `base.html` carga Google Fonts de un tercero (IP de visitantes, CSP futura); [menor] `prod.py` activa HSTS con subdominios y preload desde el primer despliegue.
- El plan de autenticación tiene que invertir `test_panel_responde_200` y `test_api_v1_responde_200` (hoy fijan el acceso anónimo) y seguir la lista de condiciones del auditor: mixin por `es_administrador`, DRF con `IsAuthenticated` y JWT, `AdminSite` restringido, `simple_history` en `User`, LOGGING sin datos personales y CSP.
- WeasyPrint está instalado pero no se probó en tiempo de ejecución (en Windows suele necesitar GTK/Pango).
- Inconsistencia de infraestructura: `CLAUDE.md` y `docs/plantilla-plan.md` piden `[test]` con la ruta punteada sola, pero `verificar_plan.py` ejecuta el criterio tal cual con bash; en este plan se escribieron como comando completo de `manage.py test`.
- Observación del verificador: `apps/web/tests/test_base.py:13` no distingue el atributo `data-tema="oscuro"` del selector CSS.
- Falta el ejemplo del certificado que la empresa entrega hoy (diseño y texto legal del PDF). Ver `docs/01-modelo-y-arquitectura.md` § 7.
- Falta confirmar si el 02241 49 6047 atiende WhatsApp y el horario de atención para el sitio público.
- Las planillas por servicio (`CampoPlanilla`) se cargan como fixtures provisorias y se editan a mano con lo que usen realmente los encargados y operarios.
- Logo: se usa provisoriamente el de "MAControl Group" (`static/img/logo.png`); la razón social en textos es MAControl S.A.

## Entradas (la más reciente arriba)

### 2026-10-01 — Arranque del repositorio y plan esqueleto
Hecho: pasos 2 a 5 de `docs/ARRANQUE.md`. Hooks y 16 skills copiados de TerritoryOS (tests de hooks: 70 OK), `git init`, venv con Python 3.13, `.gitattributes` (`*.sh` en LF), `images-for-content/` fuera de git. Plan `docs/planes/2026-10-01-esqueleto.md` (congelado en 37f1ec7, juez-plan en dos rondas: 4 bloqueantes corregidos antes de congelar): T1 base del proyecto y `accounts.User` con rol (fb08f0f), T2 diez apps y prefijos de URL con vistas provisorias (f9677fa), T3 `base.html` con tokens de ambos temas y logo (ced36a0). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 50/50 en b44c4bf; `check --deploy` con settings de producción sin avisos. auditor-seguridad: 0 bloqueantes, 4 hallazgos abiertos (ver Problemas abiertos). · A medias: nada del plan; los hallazgos del auditor quedan para decidir.

### 2026-09-29 — Base del repositorio
Hecho: se crea la carpeta del proyecto con el esquema de trabajo con agentes copiado de TerritoryOS y adaptado a un solo repositorio Django: `CLAUDE.md`, `.claude/agents/` (implementador, verificador, verificador-b, juez-plan, refutador, auditor-seguridad), `.claude/hooks/`, `.claude/skills/convenciones-proyecto/`, `docs/plantilla-plan.md`, `docs/decisiones.md`. Documentos fuente: `docs/00-contenido-fuente.md` (transcripción de la Carta de Servicios), `docs/01-modelo-y-arquitectura.md` (modelo de datos, roles, flujos, estructura), `docs/02-diseno.md` (tokens del tablero elegido, dirección A "Industrial certificada"). Diseños en el lienzo de claude.ai: https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk · A medias: no hay código; `git init` y primer commit pendientes.
