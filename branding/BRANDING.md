# Marca de knowman

Fuente de la marca para el sitio, las diapositivas, el diagrama y el panel.
Inspirada en Lufthansa: azul profundo (`#05164d`), llamada amarilla
(`#ffad00`) y esquinas casi rectas (2 px). Tipografía Public Sans (OFL), en
local, sin peticiones a terceros. Lufthansa Head y Lufthansa Text no tienen
licencia libre y no se copian.

## Archivos

| Archivo | Quién lo edita | Uso |
| --- | --- | --- |
| `tokens.json` | tú | **Fuente.** Paleta, tokens semánticos en claro y oscuro, tipografía y forma |
| `brand.css` | generado | Variables. `:root` es claro y `[data-theme="dark"]` oscuro; también sigue la preferencia del sistema |
| `aliases.css` | generado | Los nombres que ya usaban el sitio y el panel (`--bg`, `--ink`, `--brand`…), apuntando a los de la marca. Transitorio |
| `fonts.css` y `fonts/` | tú | `@font-face` de Public Sans y sus woff2 con la licencia |
| `theme-knowman.css` | tú | La identidad del proyecto: llamada amarilla, piezas rectas, filo azul, foco |
| `preview.html` | tú | Referencia visual estática, claro y oscuro. Ábrela directamente en el navegador |

## Cómo cambiar la marca

1. Edita `tokens.json`.
2. Desde `core/`: `python3 scripts/build_brand.py --sync`.
3. Abre `preview.html` y comprueba claro y oscuro.
4. `python3 scripts/build_brand.py --check` debe decir "Marca al día".

`--sync` copia `brand.css`, `aliases.css`, `fonts.css`, `theme-knowman.css` y
`fonts/` a `../site/site/branding/` y escribe el mismo bloque dentro de
`src/knowman/static/dashboard.html`, entre los marcadores `brand:start` y
`brand:end`. **Esas copias no se editan.** `--check` falla si alguna difiere.

## Dónde se usa

| Pieza | Cómo recibe la marca |
| --- | --- |
| Sitio y diapositivas | `@import` de `branding/` desde `style.css` y `deck.css`, más `theme-knowman.css` |
| Diagrama de arquitectura | Las clases del SVG usan las variables; las esquinas son de 2 px |
| Panel (`/dashboard`) | Bloque con las variables dentro de `dashboard.html`; sin fuentes web (cae a Arial) |

## Reglas

- Nunca escribas un color o una fuente fuera de `branding/`: usa `var(--…)`.
- El amarillo `#ffad00` es relleno (botones, filo); no se lee como texto sobre
  blanco. Para texto amarillo en claro está `--color-accent` (`#996600`).
- Esquinas: `var(--shape-radius)`, siempre. No pongas radios a mano.
- El PDF se renderiza en claro.
- Contraste mínimo de 4,5:1 en texto. Los pares de `tokens.json` ya lo cumplen.
