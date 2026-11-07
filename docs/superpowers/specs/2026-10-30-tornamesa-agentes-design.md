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
| H2 | Normas base: AISC 360-22 (ASD), ASME BTH-1 **Categoría de diseño B (Nd = 3,0)**, por analogía, para elementos mecánicos de la cadena de empuje; AWS D1.1/D1.1M:2020. El traspaso usaba Cat. A (Nd = 2,0) | Decisión del usuario, 30-10-2026 |
| H2b | Soldadura de las barras 4f: tipo (filete, PJP o CJP) y ubicación (caras exteriores, interiores o ambas) son **parámetros de entrada**; el software verifica según AWS D1.1 y AISC 360-22 J2 y reporta el tipo mínimo que cumple FU ≤ 0,90. Valor por defecto: apoyo en caras exteriores (luz 160 mm), por ser lo habitual en barras pasantes de cajón cerrado. Supuesto a confirmar con el taller | Decisión del usuario, 30-10-2026 |
| H2c | Accionamiento **paramétrico**: número de cilindros (n), capacidad nominal, área del émbolo, diámetro del vástago, presión de alivio y carrera son entradas. Caso base: **2 cilindros de 50 t (445,3 kN a 700 bar)**. El software reporta presión, FS y μ_max para cualquier n y capacidad, y el `selector-comercial` filtra un catálogo cargado como dato, sin cifras inventadas | Decisión del usuario, 30-10-2026 |
| H2d | Carga máxima de servicio W (tf) es parámetro: casos de estudio 250 y 300 tf. TT300-B se mantiene en 300 tf hasta que el cliente defina otra cosa | Decisión del usuario, 30-10-2026 |
| H3 | μ estático de diseño 0,20; r_ef 0,80 m (a revisar por M1) | Traspaso §3 |
| H4 | La cadena de empuje se verifica a la fuerza de calado (A·p_alivio = 445,3 kN) | Traspaso §3, H9 |
| H5 | Unidades SI; resultados con 2–3 cifras significativas | Preferencias del usuario |

**Normas por incorporar y justificar:** NCh2369 (sismo, M8), AISC 360-22 Apéndice 3 (fatiga, M5), ISO/TS 13725 (pandeo del vástago).

**Consecuencia de la Categoría B (Nd = 3,0) sobre los valores del Apéndice A (F calado 445,3 kN):**

| Elemento | Demanda (MPa) | Fy/Nd, Cat. A | FU Cat. A | Fy/Nd, Cat. B | FU Cat. B |
|---|---|---|---|---|---|
| Trinquete, flexión en boca (vigas) | 343 | 400 | 0,86 | 267 | **1,29** |
| Trinquete, flexión en boca (FEA Q4) | 297 | 400 | 0,74 | 267 | **1,11** |
| Pasador, flexión en horquilla | 281 | 325 | 0,86 | 217 | **1,30** |
| Pasador, corte doble | 57,9 | 188 | 0,31 | 125 | 0,46 |

Con Cat. B el trinquete y el pasador **no cumplen** con la geometría actual. Estimación preliminar para FU ≤ 0,90, escalando la tensión con la geometría actual (indicativa, se recalcula en el núcleo): pasador Ø70 → ≈ Ø80; ancho del trinquete 85 → ≈ 95–102 mm. Este rediseño entra al backlog en prioridad 1.

**Verificación de la capacidad de cilindros (f. calado = área × 700 bar; K = 1,240; a = 936,4 mm; 2 cilindros):**

| Carga | Cilindros | Nominal μ 0,15, r 0,672 | Diseño μ 0,20, r 0,80 | Contaminado μ 0,25, r 0,80 |
|---|---|---|---|---|
| 250 tf | 2 × 20 t (177,9 kN) | FS 1,07 | **FS 0,68** | FS 0,54 |
| 250 tf | 2 × 50 t (445,3 kN) | FS 2,68 | FS 1,69 | FS 1,36 |
| 300 tf | 2 × 20 t | FS 0,89 | **FS 0,56** | FS 0,45 |
| 300 tf | 2 × 50 t | FS 2,24 | FS 1,41 | FS 1,13 |
| 300 tf | 2 × 55 t (489,3 kN) | FS 2,46 | FS 1,55 | FS 1,24 |

Con 250 tf y 2 × 20 t el caso nominal pasa con FS 1,07, pero el criterio de diseño (μ 0,20) no. La capacidad mínima por cilindro para 250 tf con FS 1,41 al diseño es ≈ 42 t (371 kN), es decir, 50 t como tamaño estándar. La referencia de proveedores (2 × 55 t para 500 t) es consistente con este modelo: 2 × 55 t vencen μ ≈ 0,22 con r_u = 0,672 (μ·r ≈ 0,15 m), pero con FS ≈ 0,94 frente al criterio de diseño μ·r = 0,16 m. La diferencia es de criterio (fricción nominal sin factor de seguridad frente a μ límite superior con r_ef = 0,80), no de física.

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
| 1 | C1 luz de barra y soldadura (FU 0,83 → 1,06–1,31 según luz); C2 libertad radial del asiento (3,58 mm frente a 1,0 mm de holgura); C3 margen de carrera (0,15 mm); **N1 rediseño de trinquete y pasador por Cat. B (FU 1,29–1,30)** |
| 2 | M1 r_ef (con r = 1,0 y μ 0,25, FS 0,91); M2 flexión global (8,6 frente a ≈ 23 MPa) y corte de nervios; M3 guía y volcamiento; M4 apoyo trinquete/carro (≈ 1,8 F) |
| 3 | M5 fatiga; M6 plancha superior con excentricidad; M7 suelo biaxial (0,988 MPa); M8 sismo NCh2369 |
| 4 | m1 tope 1,6·Fy·S; m2 Ωv = 1,67; m3 suma de reacciones con signo; m4 recuperación en apoyos; m5–m9 |

## 7. Agentes deterministas del producto (8 módulos)

Módulos del núcleo, sin red ni LLM: mismas entradas, mismas salidas, aptos para respaldar una memoria firmada.

| # | Módulo | Función | Resuelve |
|---|---|---|---|
| 1 | `validador-entradas` | Rangos y consistencia geométrica antes de calcular (N_barras/N_nervios entero, margen de carrera ≥ 5 mm, luz de barra según soldadura) | C1, C3, m8 |
| 2 | `auditor-normativo` | Cada chequeo declara norma, artículo, ecuación, Ω o φ y clasificación del FU (≤ 0,90 / 0,90–1,00 / > 1,00). Sin referencia, falla el build | Trazabilidad |
| 3 | `revisor-cruzado` | Recalcula magnitudes clave con un modelo simplificado independiente; marca diferencia > 1 % | Apéndice E automatizado |
| 4 | `escenarios` | Casos de borde en lote: r_ef 0,67/0,80/0,94/1,00; μ 0,15–0,25; sismo; un solo cilindro | M1, M8 |
| 5 | `ensayo-aceptacion` | μ_real = (p·A·2a/K − T_piv)/(N·r_ef); cumple si μ_real ≤ 0,20 | Traspaso §4.8 |
| 6 | `generador-memoria` | Memoria con hipótesis, desarrollo y resultado, exportada a Word y PDF en negro | Preferencias |
| 7 | `selector-comercial` | Con la fuerza de calado, la presión, la carrera y el pandeo del vástago, filtra el catálogo de cilindros cargado como dato (diámetros de émbolo y vástago, presión nominal, carrera, ojales) y propone los que cumplen | Datos del cilindro, H2c |
| 8 | `selector-soldadura` | Para cada junta soldada evalúa filete, PJP y CJP según AWS D1.1 y AISC 360-22 J2 y devuelve el tipo mínimo con FU ≤ 0,90 para la ubicación elegida | C1, H2b |

**Flujo:** entradas → `validador-entradas` → núcleo (con `selector-comercial` y `selector-soldadura`) → `auditor-normativo` + `revisor-cruzado` → `escenarios` → `generador-memoria`. Una advertencia crítica de los módulos 1 a 3 bloquea la emisión de la memoria.

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

## 9. Riesgos y decisiones

| Tema | Estado | Acción |
|---|---|---|
| Categoría BTH-1 | **Resuelto: B (Nd = 3,0).** Trinquete (FU 1,29) y pasador (FU 1,30) no cumplen con la geometría actual | Rediseño en backlog N1; registrar la justificación en `docs/normas/registro.md` |
| Soldadura de barras (C1) | **Resuelto como parámetro:** tipo y ubicación son entradas; defecto caras exteriores (luz 160) | Confirmar con el taller si se puede soldar por el interior antes de cerrar el cajón |
| Cilindro | **Resuelto como criterio:** lo define el cálculo y la disponibilidad comercial | Cargar el catálogo del proveedor como dato; con Cat. B el cálculo de pandeo y el vástago reales deben confirmarse con ficha técnica |
| Parámetros sísmicos NCh2369 | Abierto: zona, suelo y categoría del equipo no definidos | Preguntar al usuario al llegar a M8 |
| Migración JS → TS | Riesgo de pérdida de equivalencia numérica | Golden file en cada paso, un módulo a la vez |

## 10. Fuera de esta especificación

La especificación detallada de cada corrección (C1–C3, M1–M8) se escribe y aprueba por separado. Este documento fija la arquitectura, los roles y el orden de trabajo.


## 11. Decisiones posteriores (30-10-2026, tarde)

| Tema | Decisión |
|---|---|
| Arquitectura del accionamiento | **Tipo KIET verificada (TT300-C):** cilindro pivotado en la base con uña pivotada en el vástago, sin carro ni guía. Referencia: `docs/referencias/2026-10-30-kiet-400t-analisis.md` |
| Capacidad | 300 tf |
| Cilindros | 2 × Ø85/Ø55, carrera 235, 700 bar (como KIET), paramétricos |
| Entregable de software | Herramienta HTML autónoma `Tornamesa_v<VERSION>.html` en la raíz (hoy `Tornamesa_v1.1.html`; antes `dist/TT300-C_Verificacion.html`, que ya no existe): ingreso de parámetros, verificación completa en vivo, veredicto de giro y de estructura, optimizador de peso |
| Objetivos | Peso mínimo (transporte) con giro asegurado |
| Entregable final | Planos de fabricación completos, generados desde el mismo JSON de parámetros |
| Lenguaje del núcleo | JavaScript (continuidad con el código existente), sin dependencias, con tests en Node y verificación independiente en Python |
