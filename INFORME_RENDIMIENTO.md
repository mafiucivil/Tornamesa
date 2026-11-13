# INFORME DE RENDIMIENTO — Tornamesa_v1.5.html (TT300-C)

Rama local `perf-rendimiento` (sin push). Base: `fafa4f9`. Fecha: 2026-11-13.

## 1. Tiempos antes / después

### 1.1 Navegador (Chromium headless, `Tornamesa_v1.5.html`)

| Evento | Antes (s) | Después (s) |
|---|---|---|
| Carga → badges + pestaña activa | 67,6 | 1,5 |
| Edición μ = 0,35 → render de la pestaña activa (incluye 600 ms de debounce) | 65,0 | 1,9–2,0 |

### 1.2 Node, variante `def`, una llamada por función (ms)

| Función | Antes | Después |
|---|---|---|
| validate | 31 | 13 |
| analyze (con FEA) | 3017 | 2789 |
| crossCheck | 32 | 33 |
| audit | 0,5 | 0,6 |
| scenarios | 5463 | 5485 |
| analyze noFEA | 565 | 560 |
| market | 76518 | 77027 |
| capacityByCyl | 97466 | 46714 |
| thermal | 40834 | 36903 |
| optimizeGen (variante `opt`, completa) | 64578 | 65551 |

Las diferencias de ±5 % se deben a la carga de la CPU. La ganancia real en el navegador viene de diferir el cálculo y renderizar de forma perezosa (§3), no de la velocidad de cada función.

### 1.3 Node, variante `seq` (def, mu035, def, bz2, def en un mismo proceso; ms)

| Función | Antes | Después |
|---|---|---|
| market | 388449 | 219856 |
| capacityByCyl | 504430 | 146552 |
| thermal | 200715 | 145144 |
| scenarios | 22697 | 11382 |

Aquí la memorización acelera lo que se repite al volver a una variante ya calculada.

## 2. Comparación numérica

`cmp` se hace sobre JSON normalizado, quitando las claves `ms`. Esas claves son tiempos de reloj del FEA y no son deterministas ni siquiera entre dos corridas de la base.

| Variante | ¿Idéntico? |
|---|---|
| def | SÍ |
| mu035 | SÍ |
| n1 | SÍ |
| bz2 | SÍ |
| seq (A, B, A, C, A) | SÍ |
| opt (optimizeGen completo) | SÍ |

Interfaz: el `innerText` de las 13 pestañas y de los badges es idéntico al de la versión previa, tanto con los valores por defecto como con μ = 0,35. Con μ = 0,35 aparece «✗ NO GIRA · FS 0,760». Los bloques diferidos (comercial, capacidad por cilindros y escenarios) también dan el mismo texto.

## 3. Cambios

| # | Cambio | Estado | Motivo |
|---|---|---|---|
| 1 | Memorización LRU pura de `capacityW`, `market` y `capacityByCyl` (200 entradas) | Mantenido | Resultado bit-idéntico |
| 2 | Memorización LRU de `compute` y `analyze {noFEA}` (20 entradas, no 200) | Mantenido con límite reducido | Con 200 entradas la memoria llegaba a ≈1,8 GB, porque cada resultado pesa ≈5 MB |
| 3 | `analyze` con FEA sin memorizar | No aplicado | Tiene estado oculto (`ms`); se mantiene por conservadurismo |
| 4 | Cálculo diferido de scenarios, market y capacityByCyl, solo al hacerse visibles («Calculando…») | Mantenido | — |
| 5 | crossCheck y audit se calculan en cada recalc | Se mantienen en recalc | Alimentan el badge y cuestan ≤ 14 ms |
| 6 | Render solo de los badges y la pestaña activa (las demás quedan marcadas como pendientes y se renderizan en `showTab`) | Mantenido | — |
| 7 | Debounce de 600 ms con cancelación por generación (`RGEN`) | Mantenido | — |
| 8 | TT_IMG perezoso | No aplicado | Requiere un cambio no trivial en `build_tt300c.py`, y la imagen ya se decodifica solo al abrir su pestaña |

No hubo reversiones.

## 4. npm test y Playwright (Fase 3)

`npm test` se corrió por partes por el límite de 900 s, con 3 a 4 procesos en paralelo en 4 CPU.

| Bloque | Resultado |
|---|---|
| `test_tt300c.js`, 99 tests por grupos (incluye golden) | PASA |
| `test_planos_export.js`: casos rápidos (7), termica, madera c0–c2, tapones v0–v6, topes v0, v1, v3, v4, v5 | PASA |
| planos «JSON de diseño: mismo contenido que tools/export_design.js» | **FALLA, igual que en la base** (preexistente) |
| planos topes v2 y v6 | Sin verificar (timeout de 900 s, 2 veces) |
| indep_tt300c, accionamiento, izaje_collar, termica, pivotado, madera, plancha_base_E (--rapido) | PASA |
| indep_interfaz | Sin verificar (timeout de 900 s, 2 veces; 892 líneas parciales idénticas, sin discrepancias) |

Detalle del fallo preexistente: `buildDesign` en `packages/web/planos_export.js` no exporta `pasadores_empuje` y `tools/export_design.js` sí. Ninguno de los dos archivos se tocó.

Playwright:

| Prueba | Resultado |
|---|---|
| 13 pestañas en tema claro y oscuro | OK |
| Consola | Sin errores. Solo aparece `ERR_CONNECTION_REFUSED` a `127.0.0.1:8765` (generador de planos local), igual que en la base |
| «NO GIRA» con μ = 0,35 | OK |
| Bloques diferidos frente a la versión previa | Idénticos |

Observación preexistente, sin relación con este cambio: a 400 px hay scroll horizontal en Modelo, Accionamiento y Agentes. Los anchos son los mismos en la base.

## 5. Archivos modificados

- `packages/core/tt300c.js` (solo memorización)
- `packages/web/ui.js`
- `Tornamesa_v1.5.html` (regenerado con `python3 tools/build_tt300c.py`)
- `INFORME_RENDIMIENTO.md` (este archivo)

## 6. Commits (locales, rama `perf-rendimiento`)

| Commit | Contenido |
|---|---|
| `262342a` | Núcleo: memorización LRU |
| `a9565e2` | Interfaz: cálculo diferido, render perezoso, debounce |

Además, un commit con este informe.

## 7. Cuello de botella restante (PROPUESTA, no implementada)

| Pendiente | Tiempo |
|---|---|
| Tabla de comparación comercial, al desplazarse hasta ella | ≈40 s |
| Tabla de capacidad por cilindros | ≈26 s |
| Pestaña Tapones (`TT.tapones`, igual en la base) | ≈300–350 s |

El perfil de CPU muestra que `PG.segDist`, `edgeDist` y `dist` (barrido de distancias a polígono, usado en `cornerInsert` y `toC`) se llevan ≈80 % del tiempo de `market()`. La propuesta es memorizar la parte geométrica de `cornerInsert` según los parámetros geométricos, que no dependen de W_tf. Antes requiere un análisis de pureza y un `cmp` bit-idéntico.

## 8. Cómo volver atrás

- Volver a la rama de trabajo:

  ```bash
  git checkout claude/dreamy-allen-r5dzqu
  ```

- O, estando en `perf-rendimiento`, restaurar solo los archivos del cambio:

  ```bash
  git checkout fafa4f9 -- packages tools tests Tornamesa_v1.5.html
  ```

- O restaurar desde el respaldo: copiar `../_backup_pre_rendimiento/{packages,tools,tests}` sobre el repo y regenerar el HTML con `python3 tools/build_tt300c.py`.
