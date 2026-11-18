# MAControl — Sistema visual

Dirección elegida: **A · "Industrial certificada"**. Tableros de referencia (home y plantilla de servicio): https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk

Tema **oscuro** para el sitio público. El amarillo de marca se reserva para acciones, acentos y estado; nunca para grandes fondos de texto.

## Color

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#0f1417` | fondo de página |
| `--surface` | `#161c21` | tarjetas, filas |
| `--surface-2` | `#1a2126` | placeholders, bloques secundarios |
| `--border` | `#22292e` | líneas divisorias, bordes de tarjeta |
| `--border-strong` | `#3a434a` | bordes de inputs, botones secundarios |
| `--text` | `#e8e6df` | texto principal |
| `--text-muted` | `#b9b7ae` | texto secundario, descripciones |
| `--text-faint` | `#7f8890` | metadatos, etiquetas de marcador |
| `--brand` | `#ffc600` | amarillo del logo (medido sobre el PNG: rgb 255,198,0) |
| `--brand-hover` | `#ffd84d` | hover de enlaces y botones |
| `--on-brand` | `#0f1417` | texto sobre amarillo |
| `--on-brand-muted` | `#3a3410` | texto secundario sobre amarillo |
| `--brand-tint` | `#1a1a10` | fondo de avisos con borde `#3a3410` |

## Tipografía

- **Display**: `Barlow Condensed` 600 / 700 / 800 — títulos, cifras grandes, botones. Mayúsculas en títulos de sección del sitio público.
- **Texto**: `Barlow` 400 / 500 / 600 — cuerpo, tablas, formularios.
- Fallback: `system-ui, sans-serif`. Se sirven desde `static/fonts/` (woff2, subconjunto latin, licencia OFL) en la web, sin pedidos a terceros.

Escala (px):

| Rol | Tamaño / interlineado | Fuente |
|---|---|---|
| H1 web | 84 / 0.95, uppercase, tracking −0.01em | Barlow Condensed 800 |
| H2 web | 56 / 1.0, uppercase | Barlow Condensed 800 |
| Título de tarjeta | 22–26 / 1.1 | Barlow Condensed 700 |
| Cifra destacada | 30–34 / 1.05 | Barlow Condensed 700, color `--brand` |
| Etiqueta ("eyebrow") | 13–14, uppercase, tracking 0.12–0.14em | Barlow 600, color `--brand` |
| Cuerpo | 15–17 / 1.5 | Barlow 400 |
| Metadato | 13 | Barlow 400, `--text-faint` |

## Espaciado y forma

- Base 4 px. Margen lateral de página: 64 px en escritorio, 20 px en móvil. Ancho máximo de contenido: 1280 px.
- Radio: 4 px (botones, inputs), 6 px (tarjetas), 8 px (bloques grandes).
- Bordes de 1 px con `--border`; sin sombras.
- Motivo de marca: **franja de advertencia** `repeating-linear-gradient(135deg, var(--brand) 0 18px, var(--bg) 18px 36px)`, 14 px de alto, solo en el borde superior de imágenes destacadas.

## Componentes

- **Botón primario**: fondo `--brand`, texto `--on-brand`, Barlow 700 15–16 px uppercase tracking 0.06em, alto 46–54 px, padding 0 22–28 px, radio 4.
- **Botón secundario**: transparente, borde 1.5 px `--border-strong`, texto `--text`.
- **Enlace**: color `--brand`, hover `--brand-hover`.
- **Tarjeta**: fondo `--surface`, borde `--border`, radio 6, padding 22–24 px; número o etiqueta en `--brand` arriba, título 19 px 600, descripción 14 px `--text-muted`.
- **Tarjeta invertida** (bloque amarillo, solo web): fondo `--brand`, tarjetas hijas fondo `--bg`.
- **Formulario**: etiqueta 13 px uppercase tracking 0.08em `--text-muted`; input alto 46–48 px, fondo `--bg`, borde `--border-strong`, radio 4, foco con borde `--brand`.
- **Barra de navegación**: la página actual lleva `aria-current="page"` y `.nav-actual` (texto y subrayado `--brand`); en `/servicio/…` se marca "Servicios". "Servicios" abre `.nav-desplegable-panel` con `:hover` y `:focus-within`, solo HTML y CSS. `section[id]` usa `scroll-margin-top: 100px` por la barra fija.
- **Barra móvil (≤ 900 px)**: logo de 40 px de alto con `width: auto` y `flex-shrink: 0` (proporción 3,96:1); teléfono como `.nav-telefono-icono` de 44×44 con `aria-label="Llamar al …"`; el menú desplegable ocupa todo el ancho del viewport.
- **Botón flotante `.whatsapp-flotante`**: círculo de 56 px fijo abajo a la derecha; solo existe si hay número de WhatsApp. En móvil el pie deja 96 px de margen inferior para que no lo tape.
- **Pie**: `.pie-marca` (logo, eslogan y redes), direcciones con enlace a Google Maps (`rel="noopener"`), dos teléfonos, WhatsApp, correo, horario y línea legal con CUIT, habilitación, director técnico y `© año MAControl S.A.`.
- **Tarjeta de servicio** (`.tarjeta-servicio`): altura igual por fila, `.tarjeta-icono` de 48×48 (borde `--on-brand-muted`, fondo `--brand-tint`, ícono `--brand`) y `.tarjeta-ver` "Ver servicio →" al pie.
- **Franja de sectores** (`.franja-sectores`): título a la izquierda y `.lista-sectores` a la derecha, 3 columnas con filete superior (2 en móvil).
- **Franja de clientes** (`.franja-clientes`): `.cliente-nombre` en Barlow Condensed 700, mayúsculas, con rombo `--brand` delante; salto de línea natural.
- **Portada con video** (`.hero`, solo en el inicio): `<video>` de fondo a todo el ancho (`muted loop playsinline autoplay`, `aria-hidden="true"`, `poster` = `portada-poster.webp`) con dos fuentes MP4: 480 p para `max-width: 900px` y 720 p para el resto. El poster se precarga con `fetchpriority="high"`.
  - **Velo** (`.hero-velo`): degradado de `--bg` de izquierda a derecha (0,94 → 0,86 → 0,35) con el texto a la izquierda; en móvil (≤ 900 px) el degradado va de arriba hacia abajo, el texto queda abajo y los botones ocupan todo el ancho. El contraste AA de título, párrafo y botones sobre todo el bucle se mide en el navegador (T5), no se asume.
  - **Pausa** (`.hero-pausa`): botón de 44×44 arriba a la derecha, con `hidden` en el HTML; el JS lo muestra y alterna `aria-pressed` y `aria-label`. El video se pausa solo cuando la portada sale del viewport y mientras el diálogo está abierto; se reanuda después, salvo que el usuario lo haya pausado.
  - **Diálogo** (`.video-dialogo`): "Ver video · 1 min" es un enlace al MP4 institucional; con JS abre un `<dialog>` modal con `<video controls preload="none">` y un botón de cerrar de 44×44. Cerrar (botón, Escape o clic en el fondo) pausa el institucional.
  - **Movimiento reducido**: con `prefers-reduced-motion: reduce` el JS pausa el fondo y lo vuelve al poster; el botón queda disponible para reanudarlo.
  - Sin JS, el fondo se reproduce solo y el enlace descarga el video institucional. Una sola excepción a "sin JavaScript": `static/js/portada.js`, sin dependencias, cargado solo por el inicio.
- **Portada de servicio** (`.campo-imagen-portada`): `aspect-ratio: 16 / 9`, imagen con `object-fit: cover`.
- **Bloque de contacto (web)**: teléfono en Barlow Condensed 800 56 px como elemento principal; botones "Llamar ahora" (primario) y "WhatsApp" (secundario). Sin formularios.

## Estructura de páginas (web)

Home: barra de navegación → portada con video de fondo (título, primera oración de la presentación, botones "Llamar ahora", "Ver video · 1 min" y "Ver servicios", botón de pausa) → barra de cuatro respaldos (habilitación, Ley 10.699/88, director técnico, certificado) → servicios (grilla 3 columnas, 9 tarjetas numeradas, una por servicio) → franja "Mantenimiento edilicio" → sectores sobre fondo amarillo (8 tarjetas; los sectores de la Carta son 12) → cómo trabajamos (texto + 4 pasos) → empresa (valores en tres círculos) → clientes (logotipos) → contacto → pie.

Página de servicio: migas → título con etiqueta de categoría y sectores aplicables → imagen ancha → "El problema" / "Cómo lo resolvemos" (tarjetas de métodos) → servicio adicional → preguntas frecuentes → lateral fijo: bloque de contacto, respaldo legal, servicios relacionados.

Responsive: a menos de 900 px las grillas pasan a 1 columna, el H1 baja a 48 px, el lateral de la página de servicio pasa debajo del contenido, y la barra de navegación se reduce a logo + botón de teléfono + menú.

## Recursos

- Logo: `static/img/logo.png` (amarillo, fondo transparente), `logo-blanco.png`, `logo-negro.png` para fondos donde el amarillo no contrasta. Provisorio: dice "Group"; la razón social es MAControl S.A.
- Fotos: la empresa entregó cinco (originales en `images-for-content/edited-with-ai/`, fuera de git). Antes de usarlas en el sitio se copian a `static/img/` convertidas a WebP, máximo 1600 px de lado mayor, sin metadatos EXIF, con nombre descriptivo. Asignación prevista:

| Original | Orientación | Contenido | Uso previsto | Nombre en `static/img/` |
|---|---|---|
| `image1.jpg` | vertical | Pulverización con mochila en un quincho | Hero de la home (marcador vertical) o sector Hogares | `hero-pulverizacion-quincho.webp` |
| `image2.jpg` | horizontal | Operario preparando equipo en la oficina, logo en la pared | Bloque Empresa / Cómo trabajamos | `empresa-oficina-equipo.webp` |
| `image3.webp` | vertical | Hidrolavado de fachada desde andamio, con arnés | Franja Mantenimiento edilicio; página de exclusión de aves | `mantenimiento-fachada-andamio.webp` |
| `image4.jpg` | vertical | Termonebulización en una cocina | Cabecera de Desinfección y de Fumigaciones; alternativa de hero | `fumigacion-termonebulizacion-cocina.webp` |
| `image5.jpg` | horizontal | Camioneta y utilitario ploteados frente a contenedores | Sector Industria y puertos; respalda "logística propia" | `flota-vehiculos-industria.webp` |

  Faltan todavía fotos de monitoreo de estaciones cebaderas y de sellado de techos; esos marcadores se mantienen hasta que la empresa las entregue.
- Video de la portada: `static/img/portada-poster.webp` (poster y precarga), `static/video/portada-bucle-480.mp4` y `portada-bucle-720.mp4` (bucle de fondo, sin sonido) y `static/video/video-institucional-720.mp4` (institucional de 1 min, solo se pide al abrir el diálogo). WhiteNoise los sirve con `Range` (206).
- Logotipos de clientes: la empresa los entrega; se guardan en `media/clientes/` y se administran desde `web.ClienteDestacado`.
