# Diseño y Tokens Visuales — Iteración 2 (Frontend M3)

**Tareas**: T701 y T702
**Worktree**: `oriannaf-t701-t703-design`
**Ruta de Vista Previa**: [`frontend/src/app/diseno/page.tsx`](file:///home/orianna/development/copilot-worktrees/2026-15-TPI/oriannaf-t701-t703-design/frontend/src/app/diseno/page.tsx)
**Módulo de Estilos**: [`frontend/src/app/diseno/diseno.module.css`](file:///home/orianna/development/copilot-worktrees/2026-15-TPI/oriannaf-t701-t703-design/frontend/src/app/diseno/diseno.module.css)

---

## 1. Contexto y Enfoque de Diseño

Conforme a la autorización de cambio de entregable (sustitución de Figma/Stitch por prototipo visual nativo en React dentro de una ruta aislada), el diseño de las cinco pantallas de la aplicación del conductor y sus tokens visuales se formaliza mediante un prototipo interactivo en Next.js (`/diseno`).

### Principios visuales aplicados
- **Profesional, sobrio y legible**: Enfoque pragmático pensado para conductores profesionales que operan en vehículos, priorizando tipografía nítida y jerarquía clara.
- **Alto contraste y accesibilidad (WCAG AA / AAA)**: Texto primario con ratio de contraste superior a 15:1 (`#0f172a` sobre fondo blanco/claro) y colores de estado con contraste > 5.5:1. Alertas semánticas con `role="alert"` y foco con anillo visible de 3px.
- **Sin mapas (conforme a contrato)**: En viaje y ubicación se priorizan tarjetas de datos legibles y telemetría explícita sin mapas ni dependencias pesadas.
- **Aislamiento total**: El prototipo no altera las pantallas de producto existentes, ni `layout.tsx`, ni `globals.css` (reservado para T703).

---

## 2. Cómo Abrir y Recorrer la Vista Previa

Para inspeccionar el prototipo visual:

1. Abrir terminal en la carpeta `frontend/`:
   ```bash
   cd frontend
   ```
2. Iniciar el servidor de desarrollo de Next.js:
   ```bash
   npm run dev
   ```
3. Abrir en el navegador:
   ```
   http://localhost:3000/diseno
   ```

### Capacidades del visor interactivo
- **Navegación por pantallas**: Selector superior para alternar entre:
  1. *Login (US1)*
  2. *Estado Conductor (US2)*
  3. *Pedidos Entrantes (US3)*
  4. *Viaje en Curso (US4)*
  5. *Ubicación Simulada (US5)*
  6. *Tokens Visuales* (muestrario completo de paleta, tipografía, spacing y radios).
- **Filtro de estados**:
  - `Ver los 4 estados`: Cuadrícula comparativa con las 4 variantes simultáneas (*Nominal*, *Carga*, *Error*, *Vacío*).
  - Pestañas individuales para visualización enfocada de cada estado.

---

## 3. Especificación y Decisiones por Pantalla

### 3.1. Iniciar Sesión (US1)
- **Nominal**: Formulario centralizado con inputs para usuario/identificador y contraseña, y botón de acción primario en azul marino sobrio (`#1e3a8a`).
- **Carga**: Inputs deshabilitados, botón con spinner animado y texto *"Verificando credenciales..."* con `aria-busy="true"`.
- **Error**: Alerta superior con borde rojo (`#fca5a5`), fondo (`#fef2f2`) y `role="alert"`, indicando credenciales inválidas y bordes de input destacados en rojo.
- **Vacío**: Formulario en estado limpio con tarjeta explicativa sobre el inicio de sesión para habilitar el turno de trabajo.

### 3.2. Estado del Conductor (US2)
- **Nominal**: Tarjeta de cabecera con identidad del conductor (DNI, vehículo activo `VEH-402`, calificación promedio `4.85 ★`), badge central de estado actual (`CONECTADO`) y botones de cambio operativo: `DESCONECTADO`, `CONECTADO` y `DISPONIBLE`.
  - *Regla de negocio*: `OCUPADO` nunca se ofrece manualmente al conductor; solo se activa al aceptar un viaje.
- **Carga**: Elementos con barras de esqueleto animadas (*shimmer*), spinner y botones deshabilitados con mensaje de actualización en curso.
- **Error**: Banner de error 422 (`CONDUCTOR_NO_HABILITADO`) ante intento de pasar a `DISPONIBLE` con habilitación no aprobada o sin vehículo asignado.
- **Vacío**: Alerta informativa cuando no se pueden recuperar los datos del conductor o no tiene vehículo activo asignado.

### 3.3. Pedidos Entrantes / Solicitudes (US3)
- **Nominal**: Lista de tarjetas de solicitudes con badge de estado, importe pactado destacado, origen, destino y pasajero.
  - Para solicitudes `PENDIENTE`: cuenta regresiva visible (`vence_en: Xs`), botón verde accesible para *"Aceptar Viaje"* y botón outline rojo para *"Rechazar"*.
  - Para solicitudes `ACEPTADO`: badge verde y detalle de confirmación.
  - Para solicitudes `VENCIDA`: badge gris/muted y botones de acción inhabilitados.
- **Carga**: Skeletons de tarjetas simulando la búsqueda de pedidos en tiempo real.
- **Error**: Banners para oferta vencida (error 410) o conflicto de asignación (error 409).
- **Vacío**: Estado limpio con tarjeta dashed y mensaje: *"No hay solicitudes. Mantente en estado DISPONIBLE para recibir viajes"*.

### 3.4. Viaje en Curso (US4)
- **Nominal**: Encabezado con ID de viaje (`#TRIP-7734`), estado `OCUPADO` destacado en ámbar, datos de pasajero y ruta. Incluye un *stepper* visual de progreso:
  1. *Conductor en camino al punto de partida* (completado [✓]).
  2. *Pasajero a bordo del vehículo* (en curso [●]).
  3. *Viaje hacia el destino final* (pendiente [○]).
  Acciones secuenciales: inicialmente solo se puede activar *"Pasajero subió"*; después de confirmarlo, se habilita el botón verde *"Finalizar viaje"*. El botón no anticipa el estado operativo siguiente.
- **Carga**: Spinner y botón bloqueado con mensaje *"Finalizando viaje y comunicando estado DISPONIBLE..."*.
- **Error**: Banner de alerta por fallo de conexión o error 500 al registrar el cierre, con botón de reintento.
- **Vacío**: Mensaje informativo de ausencia de viaje activo.

### 3.5. Ubicación Simulada (US5)
- **Nominal**: Tarjeta de telemetría GPS con indicador de transmisión periódica cada 5 segundos al módulo M4 (pulsing dot). Cuadrícula con Latitud, Longitud, Precisión (± 4.5 m) y Último Envío.
  - *Regla de negocio*: Conforme al contrato y spec, no se dibuja mapa.
- **Carga**: Skeletons de telemetría y spinner con mensaje de enlace con M4.
- **Error**: Banner de fallo en la transmisión periódica con indicación de reintento en el próximo intervalo (5s).
- **Vacío**: Cuando los tres campos de coordenadas son `null`, se muestra explícitamente el badge y texto *"Ubicación desconocida"*, nunca `(0, 0)`.

---

## 4. Tokens Visuales Concretos (Base para T703)

Estos valores deben ser trasladados a `frontend/src/app/globals.css` durante la ejecución de la tarea **T703** (OpenCode).

### 4.1. Colores

| Token CSS | Valor Hex / RGBA | Uso / Rol Semántico | Contraste |
|---|---|---|---|
| `--color-primary` | `#1e3a8a` | Azul marino 900. Color de marca y botones principales | > 10:1 s/ blanco |
| `--color-primary-hover` | `#172554` | Azul marino 950 para hover | > 12:1 s/ blanco |
| `--color-primary-light` | `#eff6ff` | Azul 50 para fondos tintados | — |
| `--color-primary-border` | `#bfdbfe` | Azul 200 para bordes suaves | — |
| `--color-bg-canvas` | `#f8fafc` | Slate 50. Fondo general de pantalla | — |
| `--color-bg-surface` | `#ffffff` | Blanco. Fondo de tarjetas, tablas e inputs | — |
| `--color-bg-subtle` | `#f1f5f9` | Slate 100. Fondos de cabecera y paneles | — |
| `--color-bg-muted` | `#e2e8f0` | Slate 200. Skeletons y divisores | — |
| `--color-border-default` | `#cbd5e1` | Slate 300. Bordes estándar | — |
| `--color-border-strong` | `#94a3b8` | Slate 400. Bordes destacados | — |
| `--color-border-focus` | `#2563eb` | Azul 600. Anillo de foco accesible | — |
| `--color-text-primary` | `#0f172a` | Slate 900. Tipografía principal de alto contraste | 16:1 s/ blanco |
| `--color-text-secondary` | `#475569` | Slate 600. Texto secundario accesible | 5.5:1 (Cumple AA) |
| `--color-text-muted` | `#64748b` | Slate 500. Metadatos y etiquetas secundarias | 4.6:1 s/ blanco |
| `--color-text-inverse` | `#ffffff` | Blanco. Texto sobre fondos oscuros o primarios | — |
| `--color-success-bg` | `#f0fdf4` | Verde 50. Fondo de estado DISPONIBLE / Aceptado | — |
| `--color-success-border` | `#86efac` | Verde 300. Borde de estado DISPONIBLE | — |
| `--color-success-text` | `#14532d` | Verde 900. Texto de estado DISPONIBLE | > 7:1 |
| `--color-success-solid` | `#15803d` | Verde 700. Botón de Aceptar Viaje / Finalizar | > 4.5:1 |
| `--color-warning-bg` | `#fffbeb` | Ámbar 50. Fondo de PENDIENTE / OCUPADO | — |
| `--color-warning-border` | `#fcd34d` | Ámbar 300. Borde de alerta y advertencia | — |
| `--color-warning-text` | `#78350f` | Ámbar 900. Texto de estado PENDIENTE / OCUPADO | > 7:1 |
| `--color-warning-solid` | `#b45309` | Ámbar 700. Badges de advertencia y tiempo | > 4.5:1 |
| `--color-danger-bg` | `#fef2f2` | Rojo 50. Fondo de error y alerta | — |
| `--color-danger-border` | `#fca5a5` | Rojo 300. Borde de error | — |
| `--color-danger-text` | `#7f1d1d` | Rojo 900. Texto de mensajes de error | > 8:1 |
| `--color-danger-solid` | `#b91c1c` | Rojo 700. Botón de rechazo o acción destructiva | > 4.5:1 |
| `--color-info-bg` | `#f0f9ff` | Celeste 50. Fondo de estado CONECTADO / Telemetría | — |
| `--color-info-border` | `#7dd3fc` | Celeste 300. Borde de información | — |
| `--color-info-text` | `#0c4a6e` | Celeste 900. Texto de estado CONECTADO | > 7:1 |
| `--color-info-solid` | `#0284c7` | Celeste 600. Indicador de pulso GPS | — |

### 4.2. Tipografía

- **Familia principal**:
  ```css
  --font-family-base: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  ```
- **Escala de tamaños**:
  - `--font-size-xs`: `0.75rem` (12px) — Badges, contadores, metadatos.
  - `--font-size-sm`: `0.875rem` (14px) — Textos secundarios, inputs compactos, botones secundarios.
  - `--font-size-base`: `1rem` (16px) — Cuerpo de texto, inputs principales, botones de acción.
  - `--font-size-lg`: `1.125rem` (18px) — Subtítulos y encabezados de tarjeta.
  - `--font-size-xl`: `1.25rem` (20px) — Títulos de sección.
  - `--font-size-2xl`: `1.5rem` (24px) — Título principal de pantalla.
- **Pesos**:
  - `--font-weight-regular`: `400`
  - `--font-weight-medium`: `500`
  - `--font-weight-semibold`: `600`
  - `--font-weight-bold`: `700`
- **Alturas de línea**:
  - `--line-height-tight`: `1.25`
  - `--line-height-normal`: `1.5`
  - `--line-height-relaxed`: `1.75`

### 4.3. Espaciados

| Token CSS | Rem | Píxeles | Uso típico |
|---|---|---|---|
| `--spacing-1` | `0.25rem` | 4px | Gaps mínimos, padding interno de badges |
| `--spacing-2` | `0.5rem` | 8px | Separación de botones pequeños, márgenes compactos |
| `--spacing-3` | `0.75rem` | 12px | Padding interno de inputs y tarjetas secundarias |
| `--spacing-4` | `1rem` | 16px | Padding estándar de tarjetas y márgenes entre secciones |
| `--spacing-5` | `1.25rem` | 20px | Separaciones destacadas |
| `--spacing-6` | `1.5rem` | 24px | Padding de contenedores de pantalla |
| `--spacing-8` | `2rem` | 32px | Separación vertical de bloques mayores |
| `--spacing-10` | `2.5rem` | 40px | Márgenes estructurales |

### 4.4. Radios de Borde

| Token CSS | Valor | Uso típico |
|---|---|---|
| `--radius-sm` | `0.25rem` (4px) | Badges compactos y checkboxes |
| `--radius-md` | `0.375rem` (6px) | Botones, inputs, tarjetas secundarias |
| `--radius-lg` | `0.5rem` (8px) | Tarjetas principales y paneles de contenido |
| `--radius-xl` | `0.75rem` (12px) | Contenedores modales o modulares |
| `--radius-full` | `9999px` | Badges tipo pill, avatares e indicadores circulares |

### 4.5. Sombras y Elevaciones

- `--shadow-sm`: `0 1px 2px 0 rgba(0, 0, 0, 0.05)`
- `--shadow-md`: `0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05)`
- `--shadow-lg`: `0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)`

---

## 5. Plantilla CSS para T703 (OpenCode)

Para implementar **T703** en `frontend/src/app/globals.css`, copiar el siguiente bloque `:root`:

```css
:root {
  /* Marca y primarios */
  --color-primary: #1e3a8a;
  --color-primary-hover: #172554;
  --color-primary-light: #eff6ff;
  --color-primary-border: #bfdbfe;

  /* Neutros y fondos */
  --color-bg-canvas: #f8fafc;
  --color-bg-surface: #ffffff;
  --color-bg-subtle: #f1f5f9;
  --color-bg-muted: #e2e8f0;
  --color-border-default: #cbd5e1;
  --color-border-strong: #94a3b8;
  --color-border-focus: #2563eb;

  /* Tipografía */
  --color-text-primary: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #64748b;
  --color-text-inverse: #ffffff;

  /* Estados semánticos */
  --color-success-bg: #f0fdf4;
  --color-success-border: #86efac;
  --color-success-text: #14532d;
  --color-success-solid: #15803d;
  --color-success-solid-hover: #166534;

  --color-warning-bg: #fffbeb;
  --color-warning-border: #fcd34d;
  --color-warning-text: #78350f;
  --color-warning-solid: #b45309;

  --color-danger-bg: #fef2f2;
  --color-danger-border: #fca5a5;
  --color-danger-text: #7f1d1d;
  --color-danger-solid: #b91c1c;
  --color-danger-solid-hover: #991b1b;

  --color-info-bg: #f0f9ff;
  --color-info-border: #7dd3fc;
  --color-info-text: #0c4a6e;
  --color-info-solid: #0284c7;

  /* Escala tipográfica */
  --font-family-base: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* Espaciados */
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-5: 1.25rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;
  --spacing-10: 2.5rem;

  /* Radios de borde */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 9999px;

  /* Sombras */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
}
```
