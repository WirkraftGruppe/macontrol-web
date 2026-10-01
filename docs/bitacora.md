# Bitácora de MAControl

## Estado actual
Plan activo: (ninguno)
Rama: main (repositorio recién creado, sin código Django todavía)
Pendiente inmediato: ejecutar el prompt de arranque `docs/prompts/00-arranque.md` en modo plan para crear el esqueleto del proyecto (T1 del plan que resulte).
Problemas abiertos:
- Falta el ejemplo del certificado que la empresa entrega hoy (diseño y texto legal del PDF). Ver `docs/01-modelo-y-arquitectura.md` § 7.
- Falta confirmar si el 02241 49 6047 atiende WhatsApp y el horario de atención para el sitio público.
- Las planillas por servicio (`CampoPlanilla`) se cargan como fixtures provisorias y se editan a mano con lo que usen realmente los encargados y operarios.
- Logo: se usa provisoriamente el de "MAControl Group" (`static/img/logo.png`); la razón social en textos es MAControl S.A.

## Entradas (la más reciente arriba)

### 2026-09-29 — Base del repositorio
Hecho: se crea la carpeta del proyecto con el esquema de trabajo con agentes copiado de TerritoryOS y adaptado a un solo repositorio Django: `CLAUDE.md`, `.claude/agents/` (implementador, verificador, verificador-b, juez-plan, refutador, auditor-seguridad), `.claude/hooks/`, `.claude/skills/convenciones-proyecto/`, `docs/plantilla-plan.md`, `docs/decisiones.md`. Documentos fuente: `docs/00-contenido-fuente.md` (transcripción de la Carta de Servicios), `docs/01-modelo-y-arquitectura.md` (modelo de datos, roles, flujos, estructura), `docs/02-diseno.md` (tokens del tablero elegido, dirección A "Industrial certificada"). Diseños en el lienzo de claude.ai: https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk · A medias: no hay código; `git init` y primer commit pendientes.
