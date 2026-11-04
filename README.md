# Consulta de notas 10°A — STJ

Sitio estático (GitHub Pages) donde cada estudiante de 10°A consulta **cuánto necesita en el tercer periodo** para aprobar cada área.

- URL: https://riskbreaker2077.github.io/notas-stj/
- Acceso: **código del portal estudiantes** (id interno de PuntoEdu) + **número de documento** como contraseña.
- El documento nunca se publica: solo viaja su hash SHA-256 con salt, y solo se usa para verificar el ingreso.

## Fuentes del corte 2026-11-04

- Consolidado PuntoEdu **P1 y P2** (`informe=2`, grupo interno 12) — nota por área y por asignatura (regla: solo el ÁREA decide; las sub-columnas con % son informativas).
- Consolidado oficial de PuntoEdu **"Notas necesarias último periodo"** — el valor que se publica tal cual; coincide con la fórmula del SIEE 2.1.17 (definitiva = P1×30% + P2×30% + P3×40%, se aprueba con ≥ 3.0).
- Base local `estudiantes_stj.db` — código (`id_puntoedu`) y documento (`num_doc`).

REL y COMP_SOC no se publican (religión no decide promoción; COMP_SOC es comportamiento), igual que en el Informe de Jornada de Recuperación.

## Actualizar a un nuevo corte

1. Descargar los consolidados P1/P2 actualizados y dejarlos en `_fuente/consolidado_excel_10_P1.xls` y `_P2.xls`.
2. Del PDF nuevo de "Notas necesarias último periodo": `python3 scripts/extraer_necesarias.py RUTA_DEL_PDF.pdf` (produce `_fuente/necesarias_10A.json`).
3. `python3 scripts/generar_data.py` (QA integrada: cruces, desajustes doc vs fórmula, estados).
4. Publicar: `git add -A && git commit -m "corte AAAA-MM-DD" && git push`.

## Notas de operación

- `scripts/extraer_necesarias.py` usa `extract_text(extraction_mode="layout")` de pypdf: estable entre versiones (el visitor por coordenadas cambió en pypdf 6.x).
- Avisos individuales (p. ej. León Rios, sin P1 cargado) viven en el diccionario `AVISOS` de `scripts/generar_data.py`.
- El repo es público por requisito de GitHub Pages gratuito. `data.js` contiene nombre, código, notas y hash del documento — nunca documento en claro ni datos de acudiente.
- `<meta robots="noindex">` para no aparecer en buscadores.
