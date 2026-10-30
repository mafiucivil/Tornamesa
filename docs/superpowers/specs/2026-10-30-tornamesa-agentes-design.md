# TT300-B · Software de cálculo de tornamesa para cargas ultra pesadas
## Especificación de diseño: núcleo, agentes de desarrollo y agentes del producto

Fecha: 30-10-2026 · Estado: aprobado en conversación, pendiente de revisión escrita · Alcance: evolución de TT300-B

---

## 1. Objetivo

Software de cálculo y verificación normativa de la tornamesa hidráulica TT300-B (WLL 300 tf, disco cajón Ø2000, interfaz acero-acero con grasa grafitada, 2 cilindros de 50 t con trinquete sobre 36 barras Ø70), que:

1. Entrega resultados trazables, con norma, artículo y ecuación por cada fórmula.
2. Resuelve los hallazgos del revisor independiente (C1–C3, M1–M8, m1–m9; traspaso §11 y apéndice E) antes de re-emitir como **Rev. 1**.
3. Genera memoria de cálculo en Word y PDF, con letras negras, estructurada en hipótesis, desarrollo y resultado.
4. Mantiene una sola fuente de verdad: planos y memoria salen del mismo JSON del núcleo.

## 2. Alcance

| Dentro | Fuera |
|---|---|
| Accionamiento (cilindros, trinquete, guía, carrera) | Otros tonelajes o configuraciones (familia paramétrica) |
| Verificaciones normativas de elementos | Variantes TT500-A/B (se archivan, no se actualizan) |
| FEA propio del disco y del trinquete | Diseño de la losa o mats de apoyo (verificación por terceros) |
| Interfaz web, memoria Word/PDF, planos y 3D paramétricos | Agentes con modelo de lenguaje dentro del producto |

## 3. Hipótesis de partida

| Id | Hipótesis | Fuente |
|---|---|---|
| H1 | W = 300 tf = 2942 kN; e ≤ 150 mm; φd = 1,10 solo en resistencias | Traspaso §3 |
| H2 | Normas base: AISC 360-22 (ASD), ASME BTH-1 Cat. A (Nd = 2,0, por analogía), AWS D1.1/D1.1M:2020 | Traspaso §2.7 |
| H3 | μ estático de diseño 0,20; r_ef 0,80 m (a revisar por M1) | Traspaso §3 |
| H4 | La cadena de empuje se verifica a la fuerza de calado (A·p_alivio = 445,3 kN) | Traspaso §3, H9 |
| H5 | Unidades SI; resultados con 2–3 cifras significativas | Preferencias del usuario |

**Normas por incorporar y justificar:** NCh2369 (sismo, M8), AISC 360-22 Apéndice 3 (fatiga, M5), ISO/TS 13725 (pandeo del vástago). Pendiente de decisión del usuario: Categoría de diseño BTH-1 A (Nd = 2,0) frente a B (Nd = 3,0).

## 4. Línea base verificada

El código importado (rama `import-tt300`, commit `e74f07e`) reproduce el Apéndice A del traspaso: 25 verificaciones, 4 casos de accionamiento y benchmarks FEA (Navier 2,2178 frente a 2,2168 mm; voladizo −1,4 %). Esa salida pasa a ser el **golden file** de regresión (`tests/golden/`). Un cambio en un valor de referencia exige justificación escrita.

## 5. Arquitectura

| Carpeta | Contenido |
|---|---|
| `.claude/agents/` | Subagentes de desarrollo (sección 6) |
| `packages/core/` | Núcleo **TypeScript**, fuente única: FEA (MITC4, Q4), accionamiento, verificaciones. Corre en navegador y Node |
| `packages/agents/` | Módulos deterministas del producto (sección 7) |
| `packages/web/` | Interfaz web (reutiliza `ui.js`, `diag.js`, `geo.js`, `export.js`) |
| `cad/` | Planos y 3D en Python/CadQuery; leen el JSON del núcleo, sin parámetros duplicados |
| `tests/golden/` | Apéndice A y benchmarks |
| `docs/` | Registro de normas, especificaciones, memoria |

`calc.py` (obsoleto, pandeo con Ø90 y placas 67/70 MPa fijas) se archiva y no se usa como respaldo.

## 6. Subagentes de desarrollo

| # | Agente | Responsabilidad | Regla dura |
|---|---|---|---|
| 1 | `normativo-estructural` | Mapea cada chequeo a norma, artículo y ecuación. Mantiene `docs/normas/registro.md` | Chequeo sin referencia no entra |
| 2 | `nucleo-calculo` | Implementa y refactoriza el núcleo TypeScript con TDD | Todo cambio parte de un test que falla |
| 3 | `fea-benchmarks` | Valida el solver: Navier, placa empotrada, anillo sectorial, convergencia de malla, ΣF = ΣR | Sin benchmarks pasando no se acepta un cambio al FEA |
| 4 | `verificador-independiente` | Re-deriva en Python (base `indep.py`) sin leer el código del núcleo; tolerancia 0,01 % | No lee `calc.js`; solo enunciado y normas |
| 5 | `qa-regresion` | Golden file, tests de UI con Playwright, validación de rangos | Cambio de valor de referencia exige justificación |
| 6 | `memoria-calculo` | Memoria Word y PDF, letras negras, hipótesis → desarrollo → resultado, referencia de norma por fórmula | Formato del usuario, siempre |
| 7 | `planos-cad` | Planos y 3D desde el JSON del núcleo; control de revisión | Planos y cálculo comparten una única fuente |

Los agentes reutilizan como criterio los skills `revisor-calculo-estructural` y `revisor-aashto-lrfd-9ed` del usuario.

### Backlog inicial (agente 2, en orden)

| Prioridad | Hallazgos |
|---|---|
| 1 | C1 luz de barra y ubicación de la soldadura (FU 0,83 → 1,06–1,31 según luz); C2 libertad radial del asiento (3,58 mm frente a 1,0 mm de holgura); C3 margen de carrera (0,15 mm) |
| 2 | M1 r_ef (con r = 1,0 y μ 0,25, FS 0,91); M2 flexión global (8,6 frente a ≈ 23 MPa) y corte de nervios; M3 guía y volcamiento; M4 apoyo trinquete/carro (≈ 1,8 F) |
| 3 | M5 fatiga; M6 plancha superior con excentricidad; M7 suelo biaxial (0,988 MPa); M8 sismo NCh2369 |
| 4 | m1 tope 1,6·Fy·S; m2 Ωv = 1,67; m3 suma de reacciones con signo; m4 recuperación en apoyos; m5–m9 |

## 7. Agentes deterministas del producto

Módulos del núcleo, sin red ni LLM: mismas entradas, mismas salidas, aptos para respaldar una memoria firmada.

| # | Módulo | Función | Resuelve |
|---|---|---|---|
| 1 | `validador-entradas` | Rangos y consistencia geométrica antes de calcular (N_barras/N_nervios entero, margen de carrera ≥ 5 mm, luz de barra según soldadura) | C1, C3, m8 |
| 2 | `auditor-normativo` | Cada chequeo declara norma, artículo, ecuación, Ω o φ y clasificación del FU (≤ 0,90 / 0,90–1,00 / > 1,00). Sin referencia, falla el build | Trazabilidad |
| 3 | `revisor-cruzado` | Recalcula magnitudes clave con un modelo simplificado independiente; marca diferencia > 1 % | Apéndice E automatizado |
| 4 | `escenarios` | Casos de borde en lote: r_ef 0,67/0,80/0,94/1,00; μ 0,15–0,25; sismo; un solo cilindro | M1, M8 |
| 5 | `ensayo-aceptacion` | μ_real = (p·A·2a/K − T_piv)/(N·r_ef); cumple si μ_real ≤ 0,20 | Traspaso §4.8 |
| 6 | `generador-memoria` | Memoria con hipótesis, desarrollo y resultado, exportada a Word y PDF en negro | Preferencias |

**Flujo:** entradas → `validador-entradas` → núcleo → `auditor-normativo` + `revisor-cruzado` → `escenarios` → `generador-memoria`. Una advertencia crítica de los módulos 1 a 3 bloquea la emisión de la memoria.

## 8. Criterios de aceptación

| # | Criterio |
|---|---|
| A1 | Núcleo TypeScript reproduce el golden file del Apéndice A (diferencia < 0,01 %) antes de iniciar cualquier corrección |
| A2 | Cada verificación lleva norma, artículo y ecuación; el build falla si falta |
| A3 | C1, C2 y C3 resueltos y cubiertos por tests antes de cualquier emisión |
| A4 | `verificador-independiente` reproduce los resultados del núcleo con diferencia < 0,01 % |
| A5 | Benchmarks FEA pasan, incluido uno de placa empotrada que ejercite picos en apoyos (m4) |
| A6 | Memoria Word y PDF generada con letras negras desde el JSON del núcleo |
| A7 | Planos Rev. 1 generados desde el mismo JSON, sin parámetros duplicados |

## 9. Riesgos y decisiones abiertas

| Tema | Riesgo | Acción |
|---|---|---|
| Ubicación de la soldadura de barras (C1) | Define la luz de 100, 130 o 160 mm; cambia la conclusión de cumple a no cumple | Decisión de diseño del usuario antes de corregir |
| Categoría BTH-1 | A (Nd 2,0) frente a B (Nd 3,0) cambia los FU del trinquete y el pasador (hoy 0,86) | Justificar en `docs/normas/registro.md` |
| Parámetros sísmicos NCh2369 | No definidos (zona, suelo, categoría del equipo) | Preguntar al usuario al llegar a M8 |
| Datos del cilindro | Vástago dibujado Ø90 frente a Ø63 supuesto en pandeo | Confirmar con catálogo del proveedor |
| Migración JS → TS | Pérdida de equivalencia numérica | Golden file en cada paso, un módulo a la vez |

## 10. Fuera de esta especificación

La especificación detallada de cada corrección (C1–C3, M1–M8) se escribe y aprueba por separado. Este documento fija la arquitectura, los roles y el orden de trabajo.
