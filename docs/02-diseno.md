# MAControl — Sistema visual

Dirección elegida: **A · "Industrial certificada"**. Tableros de referencia (home y plantilla de servicio): https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk

Dos temas sobre los mismos tokens: **oscuro** para el sitio público, **claro** para el panel de gestión (los administradores lo usan horas; el fondo claro cansa menos y las tablas se leen mejor). El amarillo de marca es el mismo en ambos y se reserva para acciones, acentos y estado; nunca para grandes fondos de texto.

## Color

| Token | Oscuro (web) | Claro (panel) | Uso |
|---|---|---|---|
| `--bg` | `#0f1417` | `#f4f3ef` | fondo de página |
| `--surface` | `#161c21` | `#ffffff` | tarjetas, paneles, filas |
| `--surface-2` | `#1a2126` | `#eceae4` | placeholders, bloques secundarios |
| `--border` | `#22292e` | `#d9d6cf` | líneas divisorias, bordes de tarjeta |
| `--border-strong` | `#3a434a` | `#b9b5ab` | bordes de inputs, botones secundarios |
| `--text` | `#e8e6df` | `#15191c` | texto principal |
| `--text-muted` | `#b9b7ae` | `#4f565c` | texto secundario, descripciones |
| `--text-faint` | `#7f8890` | `#7f8890` | metadatos, etiquetas de marcador |
| `--brand` | `#ffc600` | `#ffc600` | amarillo del logo (medido sobre el PNG: rgb 255,198,0) |
| `--brand-hover` | `#ffd84d` | `#e6b200` | hover de enlaces y botones |
| `--on-brand` | `#0f1417` | `#0f1417` | texto sobre amarillo |
| `--on-brand-muted` | `#3a3410` | `#3a3410` | texto secundario sobre amarillo |
| `--brand-tint` | `#1a1a10` | `#fff7d6` | fondo de avisos con borde `#3a3410` / `#e6c95c` |

Estados (panel, semáforo de proyectos y visitas):

| Estado | Color | Uso |
|---|---|---|
| `--ok` | `#2e9e5b` | al día / visita realizada |
| `--warn` | `#ffc600` | próxima a vencer (usa el amarillo de marca) |
| `--danger` | `#d9463e` | vencida / incidencia |
| `--neutral` | `#7f8890` | sin programar / pausado |

Los marcadores del mapa Leaflet usan estos cuatro colores con el mismo significado.

## Tipografía

- **Display**: `Barlow Condensed` 600 / 700 / 800 — títulos, cifras grandes, botones. Mayúsculas en títulos de sección del sitio público; en el panel, mayúsculas solo en cifras y etiquetas.
- **Texto**: `Barlow` 400 / 500 / 600 — cuerpo, tablas, formularios.
- Fallback: `system-ui, sans-serif`. Se sirven desde Google Fonts en la web; en el panel se pueden autohospedar en `static/fonts/` para funcionar sin internet.

Escala (px):

| Rol | Tamaño / interlineado | Fuente |
|---|---|---|
| H1 web | 84 / 0.95, uppercase, tracking −0.01em | Barlow Condensed 800 |
| H2 web | 56 / 1.0, uppercase | Barlow Condensed 800 |
| H1 panel | 32 / 1.1 | Barlow Condensed 700 |
| H2 panel / título de tarjeta | 22–26 / 1.1 | Barlow Condensed 700 |
| Cifra destacada | 30–34 / 1.05 | Barlow Condensed 700, color `--brand` |
| Etiqueta ("eyebrow") | 13–14, uppercase, tracking 0.12–0.14em | Barlow 600, color `--brand` |
| Cuerpo | 15–17 / 1.5 | Barlow 400 |
| Texto de tabla | 14 / 1.4 | Barlow 400/500 |
| Metadato | 13 | Barlow 400, `--text-faint` |

## Espaciado y forma

- Base 4 px. Margen lateral de página: 64 px en escritorio, 20 px en móvil. Ancho máximo de contenido: 1280 px.
- Radio: 4 px (botones, inputs), 6 px (tarjetas), 8 px (bloques grandes). Sin píldoras salvo las etiquetas de estado (999 px).
- Bordes de 1 px con `--border`; sin sombras en el tema oscuro; en el claro, sombra suave opcional `0 1px 2px rgba(0,0,0,.06)`.
- Motivo de marca: **franja de advertencia** `repeating-linear-gradient(135deg, var(--brand) 0 18px, var(--bg) 18px 36px)`, 14 px de alto, solo en el borde superior de imágenes destacadas. No usar en el panel.

## Componentes

- **Botón primario**: fondo `--brand`, texto `--on-brand`, Barlow 700 15–16 px uppercase tracking 0.06em, alto 46–54 px, padding 0 22–28 px, radio 4.
- **Botón secundario**: transparente, borde 1.5 px `--border-strong`, texto `--text`.
- **Enlace**: color `--brand`, hover `--brand-hover`; en el panel, subrayado al hover.
- **Tarjeta**: fondo `--surface`, borde `--border`, radio 6, padding 22–24 px; número o etiqueta en `--brand` arriba, título 19 px 600, descripción 14 px `--text-muted`.
- **Tarjeta invertida** (bloque amarillo, solo web): fondo `--brand`, tarjetas hijas fondo `--bg`.
- **Tabla (panel)**: cabecera Barlow 600 13 px uppercase `--text-muted`; filas 44 px con borde inferior `--border`; hover `--surface-2`; estado con punto de color + texto.
- **Formulario**: etiqueta 13 px uppercase tracking 0.08em `--text-muted`; input alto 46–48 px, fondo `--bg` (web) o `--surface` (panel), borde `--border-strong`, radio 4, foco con borde `--brand`.
- **Etiqueta de estado**: 12 px 600 uppercase, padding 4 px 8 px, radio 999, fondo tenue del color del estado.
- **Bloque de contacto (web)**: teléfono en Barlow Condensed 800 56 px como elemento principal; botones "Llamar ahora" (primario) y "WhatsApp" (secundario). Sin formularios.

## Estructura de páginas (web)

Home: barra de navegación → hero (título, texto, dos botones, imagen con franja) → barra de cuatro respaldos (habilitación, Ley 10.699/88, director técnico, certificado) → servicios (grilla 3 columnas, 12 tarjetas numeradas) → franja "Mantenimiento edilicio" → sectores sobre fondo amarillo (8 tarjetas) → cómo trabajamos (texto + 4 pasos) → empresa (valores en tres círculos) → clientes (logotipos) → contacto → pie.

Página de servicio: migas → título con etiqueta de categoría y sectores aplicables → imagen ancha → "El problema" / "Cómo lo resolvemos" (tarjetas de métodos) → servicio adicional → preguntas frecuentes → lateral fijo: bloque de contacto, respaldo legal, servicios relacionados.

Responsive: a menos de 900 px las grillas pasan a 1 columna, el H1 baja a 48 px, el lateral de la página de servicio pasa debajo del contenido, y la barra de navegación se reduce a logo + botón de teléfono + menú.

## Recursos

- Logo: `static/img/logo.png` (amarillo, fondo transparente), `logo-blanco.png`, `logo-negro.png` para fondos donde el amarillo no contrasta. Provisorio: dice "Group"; la razón social es MAControl S.A.
- Fotos: no hay todavía. Los tableros usan marcadores; el sitio se publica con los marcadores reemplazados por fotos reales de la empresa (aplicación en planta, monitoreo de estaciones, sellado de techos, equipo con vehículo).
- Logotipos de clientes: la empresa los entrega; se guardan en `media/clientes/` y se administran desde `web.ClienteDestacado`.
