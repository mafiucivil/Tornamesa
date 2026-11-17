# TT300-BX · Tornamesa con disco inoxidable atornillado y pastillas de UHMW (módulo aparte)

Revisión 2 (16-11-2026, observaciones del revisor): disco de **304**, ΔT de servicio de la interfaz **30 K** (montaje a 20 °C, ambiente 0–50 °C),
tensión térmica tratada como **secundaria**, pastillas verificadas a **50 °C** (T_ifc_max) y 80 °C solo como **limitación de uso informativa**,
pastillas **cortadas de plancha** (router CNC o chorro de agua), sin tornear.

Módulo: `packages/core/tt300bx.js` (sobre `packages/core/tt300c.js`), agentes `packages/agents/agentes_bx.js`, exportador `tools/export_design_bx.js`,
pruebas `tests/test_tt300bx.js`. El núcleo TT300-C es bit-idéntico a `a67d98e` sin el gancho `P.__bx` (prueba JSON + subconjunto golden).

## 0. Por qué la revisión 1 pedía ≈ 1 208 tornillos con 304 (modelo corregido)

1. **ΔT = 60 K**: envolvente máx(dT del núcleo 40; 80 − 20; 20 − (−10)). Se usaron los 80 °C del sello como temperatura de la interfaz.
2. **Δα = 17,3 − 11,7 = 5,6×10⁻⁶/K** → ε = 3,4×10⁻⁴ (el doble del caso real).
3. **Mesa rígida, disco con la deformación anular impedida**, tornillos como resortes de Huth (k ≈ 2×10⁵ N/mm) y una cadena semi-infinita: toda la
   fuerza de borde caía en **un solo anillo** (el exterior).
4. Esa fuerza térmica se **sumaba vectorialmente al corte del par como carga primaria** de AISC J3.7 con FU ≤ 0,90. Como la fuerza de borde crece
   ∝ paso·√(E·t·k), el dimensionamiento redujo el paso hasta 50 mm → 1 208 tornillos. El disco de 12 mm salía del vacío «pastilla faltante»
   (radio 95 mm) calculado con el disco solo, sin el aporte de la plancha de la mesa.

Corrección (revisión 2): ΔT = 30 K y Δα = 17,3 − 12 = 5,3×10⁻⁶/K (σ = E·Δα·ΔT = 30,7 MPa uniaxial; 43,8 biaxial). La tensión térmica es secundaria
y autolimitante: se verifica como rango ≤ 2·Fy (ASME BPVC VIII-2 5.5.6.1, S_PS) y, conservador, ≤ Fy; más el pandeo del panel s × s entre tornillos.
Los tornillos se dimensionan con el corte primario del par (AISC J3.7). La componente térmica se informa aparte (franja radial con nudos en
**todos** los anillos y resortes de Huth: se reparte por rigidez entre anillos) y no entra como carga de resistencia (AISC J3.10: el disco acomoda
con la holgura del agujero y el aplastamiento local). El hueco «pastilla faltante» se calcula con disco y plancha de la mesa curvándose juntos.

## 1. Concepto (sin cambios)

Disco inoxidable Ø 2000 en dos semidiscos a plasma con CJP esmerilada (AWS D1.6), atornillado con ISO 10642 10.9 a la mesa; portador S355 a
plasma soldado a la base solo por sus bordes (filetes); pastillas de UHMW en sus agujeros, apoyadas en la base, retenidas con ISO 10642 8.8.

## 2. Criterios

Como la revisión 1 (tabla en `docs/normas/registro.md`, sección «TT300-BX»), con estos cambios:

| Elemento | Verificación | Referencia |
|---|---|---|
| Disco | Δσ térmica = E·Δα·ΔT/(1 − ν) ≤ 2·Fy y ≤ Fy | ASME VIII-2 5.5.6.1 |
| | Pandeo del panel s × s: σ ≤ 2·π²E/(12(1 − ν²))·(t_e/s)² | Timoshenko y Gere §9.5 |
| | Vacío local Ø100 (disco solo, como el núcleo); pastilla faltante o mayor hueco: el disco toma D_d/(D_d + D_mesa) del momento q·a²/8 | Timoshenko §16 |
| Tornillos | V_T = T_calado·r/Σr² ≤ Fnv·A_b/Ω (primario); térmica secundaria informativa por anillo | AISC 360-22 J3.7; J3.10; Huth (1986) |
| Pastillas | A T_ifc_max = 50 °C: presión, presión + sobrepresión (E·k_E), PV y pared con k_p = k_E = 1 − 0,60·30/60 = **0,70** (supuesto C) | registro «Temperatura» |
| | 80 °C: **limitación de uso informativa** (`verdict.limitaciones_uso`, id `BX-T-SELLO`), no afecta el veredicto | Decisión del mandante |
| | Espesor = plancha comercial (20/25/30/40/50) y h_p = H − t_portador; tolerancia de corte ± 0,2; variación de espesor entre pastillas 0,05 (suma a d_flat, C) | Criterio de taller |

## 3. Resultados con los valores por defecto (modo pivotado)

| Pieza | Adoptado | FU |
|---|---|---|
| Disco | **304, t = 8 mm** (requerido 7,2 por la cabeza M10 + 0,5 + 0,5), 2 semidiscos de 98 kg | cabeza 0,90 (geo); vacío Ø100 0,45; hueco 0,16; celda 0,31; CJP 0,36; térmica: rango/2Fy 0,11, /Fy 0,21, pandeo 0,09 |
| Tornillos del disco | **140 × ISO 10642 M10 × 25 10.9**, malla 200 mm, anillos R169/369/569/769/969 | corte primario 0,45 (8,3 kN/18,4); aplastamiento 0,27; engrane 0,78. Térmica (inf.): 1,5/3,6/6,4/10,3/14,1 kN por anillo; combinación 16,4 kN |
| (alternativa M12) | 82 × M12 10.9 a 250 mm con disco de 10 mm | — |
| Pastillas | **105 × Ø140 (corte Ø140,5)**, de plancha de **40 mm**, saliente 15, radial a paso 165, interferencia 0,5 | 20 °C: p 0,66; PV 0,93 (aviso); **p + Δp 1,00 (falla por 0,4 %)**; pared 0,76. **50 °C: p 0,95; p + Δp 1,33; PV 1,32; pared 1,08 (fallan)** |
| Tornillo de pastilla | ISO 10642 M10 × 35 8.8 | corte (redundancia) 0,90; engrane 0,95 |
| Portador | S355, 25 mm, ligamento 25, filetes z8 | torsión 0,78; filete interior 0,69 |
| Global | δ = 48 mm; masa 3 724 kg (interfaz 540 kg) | — |

Estado global: **NO CUMPLE**, solo por las pastillas de UHMW (disco, tornillos, portador, mesa, base e izaje cumplen). Ningún tamaño de la
búsqueda (Ø 60–200, portador 10–30, plancha 20–50, ligamento ≥ t) cumple a 50 °C con k_p = 0,70: el área de pastillas posible con ligamentos de
plasma (cobertura ≈ 0,52) duplica la presión de la lámina continua y PV queda ≈ 1,3. Con ligamento 10 mm tampoco (PV50 ≈ 1,17).

Palancas cuantificadas:
- **PV a 50 °C** ∝ caudal: Q_bomba ≤ 7,6 L/min (FU 1,0) o ≤ 6,8 L/min (FU 0,9) con 10 hoy.
- **Dato del proveedor a 50 °C**: con k_p y k_E ≥ 0,93 cumplen presión + sobrepresión; la pared pide k_p ≥ 0,76.
- **Planitud**: con bx_tol_H = 0 (caras de las pastillas igualadas en sitio) la fila de 20 °C pasa; a 50 °C la sobrepresión sigue en 1,14.

## 4. Fabricación (cambio de la revisión 2)

Pastillas: **router CNC (o chorro de agua) desde plancha calibrada de UHMW de 40 mm**; la interferencia se logra en el corte (± 0,2); el agujero y el
avellanado del tornillo con el router en la misma sujeción; sin torneado. Limitación: la variación de espesor de la plancha entra a la sobrepresión
(0,05 supuesto). El resto de la tabla «antes → después» no cambia (ver `bx.fabricacion` del JSON).

## 5. Pendientes

1. UHMW a 50 °C: dato del proveedor (p_adm, PV, módulo) o caudal ≤ 6,8–7,6 L/min; sin eso el concepto de pastillas no cumple a 50 °C.
2. Tolerancia de espesor de la plancha calibrada y ligamento mínimo de plasma: criterios de taller por confirmar.
3. El optimizador de masa del núcleo no conoce las filas BX; generador de planos y HTML BX los hacen otros agentes (no se tocaron).

## 7. Revisión 3 (16-11-2026): pastillas CUADRADAS (`bx_forma = 1`, por defecto; `bx_forma = 0` conserva las redondas)

Geometría: agujeros cuadrados con esquinas R = máx(5; 0,5·t_portador) cortados con plasma HD; pastillas cuadradas de plancha comercial de UHMW
(router o chorro de agua) con esquinas R + 1 (apoyan en las caras, no en las esquinas), tornillo ISO 10642 al centro. Malla cartesiana de paso
s = lado + ligamento (ligamento ≥ máx(10; t)), con tres desfases probados; en el borde, pastillas **recortadas** por la corona R_i + lig … R_o − lig
(`bx_borde = 1`) o solo enteras (`bx_borde = 0`). Verificaciones recalculadas para la cuadrada: área A = a² − (4 − π)r², factor de forma
S = a/(4h_p), pared = lado × (t − 1), núcleo central a/6, celda equivalente s², hueco de pastilla faltante = círculo circunscrito al cuadrado
2s − a, torsión del portador con la fracción de acero por muestreo angular, ajuste y dilatación con el lado, y **esquinas** con
K_t = 1 + 2√((a/2)/r) frente a la categoría B de AISC 360-22 Apéndice 3 (borde cortado térmicamente).

Resultado del barrido (lado 100–300, portador 10–30, plancha 20–50, ligamento ≥ t; k = 0,70 a 50 °C): **ningún candidato cumple FU ≤ 0,90
a 50 °C, ni todos a 20 °C**. La cobertura alcanzable con ligamento ≥ t y el borde circular es 0,62–0,68 (no 0,75–0,80); con pastillas grandes
fallan además la pared (μ·p·a/(t − 1)) y el tornillo M10 (μ·p·a²).

| Caso | Pastilla | Portador | Cobertura / p_máx | 20 °C (FU) | 50 °C (FU) | PV 50 °C: caudal para FU 0,9 |
|---|---|---|---|---|---|---|
| Por defecto (menor FU) | 100 × 100, R11, plancha 40 (h_p 20), 204 | 20 mm, paso 120 | 0,64 / 3,70 MPa | p 0,74; p + Δp **1,16**; PV **1,08**; pared 0,96 | p **1,06**; p + Δp **1,50**; PV **1,54**; pared **1,38** | 5,9 L/min |
| Lado 200, borde recortado | 200 × 200, R17, plancha 50 (h_p 20), 60 | 30 mm, paso 230 | 0,68 / 4,06 | p + Δp 1,03; PV 1,16; pared 1,39; tornillo 2,86 | p 1,16; p + Δp 1,42; PV 1,66; pared 1,99 | 5,4 L/min |
| Lado 200, solo enteras | 200 × 200, R11, plancha 40, 48 | 20 mm, paso 220 | 0,62 / 3,64 | PV 0,88; pared 1,91; tornillo 2,57; ligamento 1,87 | p 1,04; p + Δp 1,10; PV 1,26; pared 2,73 | 7,2 L/min |

El disco (304, 8 mm), los 140 tornillos M10 y el portador (torsión, filetes, esquinas en fatiga) cumplen en todos los casos. La forma redonda de la
revisión 2 sigue siendo la mejor a 20 °C (`bx_forma = 0`). El caudal por defecto no se cambió (10 L/min).

## 8. Revisión 4 (16-11-2026): vuelta a pastillas REDONDAS (`bx_forma = 0` por defecto; la cuadrada queda en `bx_forma = 1`)

Búsqueda final: Ø 60–300, portador 10–30, plancha UHMW comercial (20/25/30/40/50), ligamento ≥ espesor del portador (criterio de taller sin
relajar), patrón radial por anillos y triangular (hexagonal) con anillo de borde y relleno de la franja de unión (`bx_pat = 0`: se prueban los dos).
Sin cambios en d_flat, p_uhmw, kT ni el caudal. Selección: todos los candidatos que cumplen a 20 °C y, entre ellos, el de menor FU máximo a 50 °C.

Camino del arrastre por la cara inferior: la pastilla apoya en la base con N_i; su cara inferior seca toma μ_b·N_i y la pared y el tornillo
reciben el residual (μ_top,máx − μ_b)·N_i. μ_b = 0,10 (`bx_mu_base`): límite inferior del rango de UHMW sobre acero seco de las fichas de
fabricante (p. ej. TIVAR 1000, Mitsubishi Chemical: 0,10–0,20, ASTM D1894), confianza C; requiere asiento seco y desengrasado.
`bx_mu_base_on = 0` vuelve a «la pared toma todo». El portador (torsión y filetes) sigue con el arrastre completo con μ_ef (conservador).

| Caso | Patrón | Ø | n | Portador | Plancha / saliente | Cobertura | FU máx. 20 °C | FU a 50 °C (gobierna) | Pared 20/50 °C y tornillo con μ_b (sin μ_b) |
|---|---|---|---|---|---|---|---|---|---|
| **Adoptado (μ_b = 0,10)** | radial | **180** | 67 | 25 mm, paso 205 | 40 / 15 | 0,55 | 0,85 (PV) | **PV 1,21**; p + Δp 1,15; p 0,88 | 0,55 / 0,78; 0,84 (0,91 / 1,30; 1,39) |
| Sin μ_b (pared toma todo) | radial | 140 | 105 | 25, paso 165 | 40 / 15 | 0,52 | 1,00 (p + Δp) | p + Δp 1,33; PV 1,32 | 0,76 / 1,08; 0,90 |
| Triangular forzado | triangular | 160 | 74 | 25, paso 185 | 40 / 15 | 0,48 | 0,98 | PV 1,40; p + Δp 1,34 | 0,56 / 0,79; 0,75 |

Cumple todo a 20 °C (FU ≤ 0,90; la mayor es PV 0,85). A 50 °C, con k = 0,70, gobierna **PV = 1,21**; luego presión + planitud 1,15.
Para cumplir a 50 °C con FU ≤ 0,90 haría falta: **caudal de la bomba ≤ 7,4 L/min** (PV; con 10 hoy), o un factor del proveedor a 50 °C
**k_p ≥ 0,94** para PV (≥ 0,85 para FU 1,0) y **k_p, k_E ≥ ≈ 0,89** para presión + planitud (con 0,70 supuesto). El disco (304, 8 mm),
los 140 tornillos M10 y el portador no cambian. δ = 48 mm; masa total 3 710 kg (interfaz 526 kg).
