# TT300-BX · Tornamesa con interfaz inoxidable–UHMW simplificada (módulo aparte)

> **Revisión 5 (18-11-2026, por defecto): lámina 304 espejo de 3 mm SOLDADA a la mesa (tapones + costura), acero A36 en todas las
> planchas, pastillas de ULTRA VST de 30 mm en portador A36 de 25 mm.** Ver §9. Las revisiones 1–4 (disco macizo atornillado) quedan
> como opción: `bx_disc_modo = 0` y `BX.defaults({ a36: false })`.

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

## 9. Revisión 5 (18-11-2026): lámina de 3 mm soldada, A36 en todas las planchas, ULTRA VST de 30 mm

Decisiones del mandante (ingeniero revisor), aplicadas como valores por defecto del módulo; lo anterior queda por parámetro.

### 9.1 Hipótesis

| Tema | Hipótesis / criterio | Referencia |
|---|---|---|
| Lámina | 304 espejo de **3 mm** (única del proveedor), `bx_disc_modo = 1`; formato `bx_fmt_a × bx_fmt_b` = **1500 × 3000** (el mayor; 1219 × 2438 también da 2 paneles); paneles = franjas paralelas a x de ancho ≤ formato − 2·10 → **2 paneles de 992 × 1984**; lámina R139…R992 (retiro de 8 mm para la costura) | Proveedor |
| Junta entre paneles | **A tope** sobre y = 0, ranura de penetración completa sobre respaldo permanente (la plancha inferior de la mesa), ER309L/E309L, esmerilada a ras y pulida. **No traslapada**: el traslapo deja un escalón de 3 mm y un canto libre en la cara de deslizamiento | AWS D1.6/D1.6M:2017 (unión disímil, WPS calificada) |
| Tapones | Agujero Ø14 (AISC J2.3a con t = 3: 11 ≤ Ø ≤ máx(14; 6,75)); relleno = t; separación ≥ 4Ø; borde ≥ máx(1,5Ø; Ω·V/(F_u·t)); Ø visible ≥ 9,5 | AISC 360-22 §J2.3; AISI S100-16 §J2.2 (= ASCE 8-02 §5.2.2); AWS D1.3 (detalle en lámina ≤ 4,8 mm, referencia) |
| Resistencia del tapón | Aporte: F_w = 0,60·F_EXX/(1,20·N_d) con F_EXX = 520 (E309L, AWS A5.4) sobre el área del agujero; lámina: AISI §J2.2.2.2, d_a = Ø − t_e, Ω = 2,20; t_e = t − sobreespesor = 2,5 mm | AISC J2.4; BTH-1 §3-3.4 |
| Carga | **Par de calado** T = 685,8 kN·m (μ máx.), reparto polar elástico **solo en los tapones** (sin costura); la costura exterior **sola** con todo el par más la membrana térmica (redundancia); arrastre local de la pastilla más cargada (μ_ef·p·A) en los tapones a ≤ d/2 + a/2 (mínimo en 24 posiciones del giro), sin el roce lámina–plancha (conservador) | Equilibrio |
| Pandeo | Compresión térmica restringida σ = E·Δα·ΔT/(1 − ν), **Δα = 5,3×10⁻⁶/K, ΔT = 20 K** (servicio vigente), panel = mayor hueco radial entre anillos de tapones y costuras o paso circunferencial, k = 2; combinado con el corte del arrastre τ = 2F/(π·d·t_e), k_s = 9,34: σ/σ_cr + (τ/τ_cr)² ≤ 1 | Timoshenko y Gere §9.5, §9.7, §9.9 |
| Contacto / despegue | La lámina queda apoyada en la plancha: la presión pasa por contacto. Requisito de fabricación **g₀ ≤ 0,2 mm** (galga) entre tapones y en ventana Ø100; la pastilla menos cargada (2,2 MPa) debe cerrarla: p_cierre = 64·D·g₀/a⁴; flexión de cierre secundaria ≤ 2Fy; fatiga cat. E (N = 32 500). El vacío local Ø100 del modo 0 se reemplaza por este cierre | Timoshenko §16; AISC Apéndice 3 |
| Pastilla faltante / celda | Las toma la **plancha inferior de la mesa con la lámina** (misma curvatura; la lámina en la cara de la plancha: cota de sección compuesta σ_s = E_s·κ·(t_inf/2 + t_e)) | Timoshenko §16–17 |
| Desgaste | Sobreespesor 0,5 mm ≥ pulido de tapones y juntas 0,2 mm + desgaste del inox (despreciable; dato pendiente) | Criterio del proyecto |
| Posición de los tapones | Anillos en las **bandas libres entre las pistas** de las pastillas (holgura 2 mm): el disco gira sobre pastillas fijas, así **ningún tapón pasa nunca bajo una pastilla** (no hay coincidencia sistemática); si el pandeo pidiera más anillos, irían en las pistas, esmerilados a ras | Geometría |
| Acero | **ASTM A36 (Fy 250, Fu 400) en todas las planchas** (parámetros Fy/Fu del núcleo). Se comprobó fila por fila (Fy 345 → 250) que esos parámetros solo los usan planchas; los aceros especiales tienen parámetro propio y no cambian | Decisión del mandante |
| UHMW | **ULTRA VST de 30 mm** (Plastigen: UHMW 9×10⁶ g/mol, ρ 0,97, Shore D 63, uso ≤ 90 °C). La ficha no trae p_adm, E, μ, PV ni α: **se mantienen los supuestos (pendiente dato del proveedor)**. Pastillas de cuadrados de 190 → **Ø de corte ≤ 185** (`bx_dp_max`); plancha 30 y portador A36 de 25 fijos (`bx_H_uh`, `bx_tc`) | Proveedor |
| Base bajo el soporte E | El núcleo calibra S = σ/M con t_base = 20 y no acredita una base más gruesa. Se usó la FEA de Mindlin de la base completa de `tests/indep_plancha_base_E.py` §4 sobre el diseño BX (h = 138 mm): crédito por espesor en filas BX (las del núcleo quedan informativas, «sustituidas») | ver 9.3 |

### 9.2 Lámina, tapones y costura (por defecto)

114 tapones Ø14 en 3 anillos R357 (24), R566 (38) y R775 (52), paso 95 mm, ninguno en una pista; masa de la lámina 72 kg (2 × 36).

| Verificación | FU | | Verificación | FU |
|---|---|---|---|---|
| Tapones: corte del aporte (V = 11,4 kN) | **0,86** | | Pandeo térmico (panel 218 mm) | 0,64 |
| Tapones: lámina alrededor (AISI J2.2) | 0,77 | | Pandeo combinado con el arrastre | 0,67 |
| Tapones: arrastre local (3 tapones) | 0,70 | | Despegue entre tapones: cierre / flexión | 0,01 / 0,09 |
| Ø, separación, borde (geo) | 1,00 / 0,60 / 0,10 | | Vacío Ø100: cierre / flexión | 0,26 / 0,41 |
| Costura exterior z3 (par solo + térmica) | 0,72 | | Fatiga cat. E | 0,16 |
| Costura interior z3 (térmica) | 0,40 | | Pastilla faltante: lámina / plancha | 0,45 / 0,34 |
| Junta a tope | 0,24 | | Celda: lámina / plancha | 0,06 / 0,04 |
| Paneles en formato (geo) | 0,67 | | Sobreespesor (geo) | 0,40 |

δ = 25 + 5 + 3 = **33 mm** (antes 38); eje del cilindro h = 138 mm (antes 143).

### 9.3 Espesores A36 (antes → después)

| Pieza | Parámetro | Antes (A572) | Después (A36) | FU gobernante con A36 antes → después |
|---|---|---|---|---|
| Plancha superior de la mesa | `t_top` | 20 | **25** | global + local 1,174 → **0,782** (FEA) |
| Plancha inferior de la mesa | `t_bot` | 16 | **20** | global + local 1,164 → **0,785** (FEA) |
| Almas y nervios / filete | `t_web`, `t_rib`, `w_web` | 6 / 6 / 6 | **8 / 8 / 8** | filete mínimo con la plancha de 25 (AWS D1.1 T7.7: 8 > alma de 6) → 1,00 (geo) |
| Anillos de pasadores | `t_pr` | 27 | **30** | aplastamiento del agujero 1,045 → **0,942** (advertencia; con 32 baja a 0,88 pero la sobrepresión de las pastillas del anillo exterior sube a 0,97) |
| Plancha base | `t_base` | 20 | **25** | base bajo el soporte E (atasco del retorno) 1,055 → **0,713** (crédito FEA, núcleo 1,055 sustituido); calado 0,823 → 0,729 |
| Refuerzo de esquina + atiesador | automáticos | 65 / h 60 | 60 / h 60 | (dentro de la fila anterior) |
| Collar del pivote | `h_boss` | 60 | **70** | asiento con H·e 1,135 → **0,890** |
| Tapas del cajón E | `pv_tl` | 29 | **36** | desgarro 1,208 → **0,973**; aplastamiento 1,053 → 0,848 |
| Paredes del soporte E | `pv_tbox` | 30 | 30 | 0,888 (con δ = 33 la altura baja; con 32 el desgarro de la tapa pasa a 1,004) |
| Portador | `bx_tc` | 25 | 25 (fijo) | ver 9.4 |

FU de la FEA de Mindlin (σ a > 100 mm de la huella) de la base bajo el soporte E, diseño BX:

| t_base | nom | dis | cal | ret |
|---|---|---|---|---|
| 20 (núcleo) | 0,193 (0,201) | 0,611 (0,593) | 0,860 (0,823) | 1,002 (1,055) |
| 22 | 0,174 | 0,548 | 0,771 | 0,848 |
| 25 | 0,172 | 0,520 | 0,728 | 0,677 |

Factor aplicado a la fila del núcleo: empuje 1,045·FEA(t)/FEA(20) (la FEA supera al núcleo en 4,5 % a calado con 20 mm), retorno FEA(t)/FEA(20).
Advertencias que quedan (0,90 < FU < 1): **pasador vertical E en flexión 0,992** (acero especial, el brazo crece con la tapa) y **desgarro de la
tapa 0,973**: con el cajón limitado por la base (fila «Soporte del ojal E dentro de la base» 0,999) no hay espesor de tapa que deje ambos ≤ 0,95
(35 mm: desgarro 1,001; 38 mm: pasador 1,02). Se adopta 36 mm (plancha de 38 planeada, como las tapas de 29). Masa total **3 684 → 4 100 kg**
(mesa +229, base +260, soportes E con sus refuerzos +47, lámina −124, portador +5, pastillas +1).

### 9.4 UHMW y portador

Con A36 la torsión de la sección neta del anillo exterior de agujeros del portador pasaba a 1,15 (Ø180, 67 pastillas). Sin cambiar el espesor:
- **Tapones en los ligamentos: no caben** (Ø ≥ t + 8 = 33 mm con ligamento ≥ t = 25 a cada agujero; el mayor círculo libre en el tresbolillo es Ø76).
- Soldadura perimetral mayor o cordones intermedios: no alivian la sección neta (partir el portador en anillos soldados por ambos cantos pide ≥ d + 2·25 + 20 ≈ 250 mm entre anillos de pastillas: con Ø170 cabe pero el área de pastillas baja ≈ 8 % y la presión sube ≈ 9 % (estimación), con lo que presión + planitud pasa de 0,93).
- Agujeros de soldadura en lugar de pastillas (`bx_nw`): ligamento 1,10–1,12 y PV 1,01–1,02.
- **Adoptado: patrón radial con pastillas quitadas del anillo crítico** (más acero en su sección neta; cada paso es un candidato): Ø180, **66 pastillas** (1 menos en el anillo exterior), Ø de corte 180,5 ≤ 185.

| Verificación | FU | Verificación | FU |
|---|---|---|---|
| Presión | 0,64 | Portador: torsión de la sección neta | **0,950** (adv.) |
| Presión + planitud | **0,933** (adv.) | Portador: ligamento de entrada | **0,929** (adv.) |
| PV | 0,876 | Filetes perimetrales ext. / int. | 0,36 / 0,68 |
| Pared (residual) / tornillo | 0,57 / 0,87 | Ø de corte ≤ 185 (geo) | 0,98 |

Barrido (Ø 172–184, ligamento 25–27, con quita de pastillas): el menor FU máximo posible es ≈ 0,91 (Ø178, ligamento 26) y siempre gobiernan
presión + planitud de las pastillas o la torsión del portador; no hay combinación con todo ≤ 0,90 con plancha de 30 y portador A36 de 25.

### 9.5 Cinemática con δ = 33 mm (antes 38)

| Verificación | Antes | Después |
|---|---|---|
| Carrera requerida con margen | 0,959 | 0,959 |
| Sincronía del retorno / peor caso | 0,971 / 0,965 | 0,971 / 0,965 |
| Flanco de reenganche (α ≤ α_máx) | 0,904 | 0,904 |
| Garra: toma / labio en la aproximación / salida / retorno sin traba | 0,440 / 0,135 / 0,150 / 0,428 | sin cambio |
| Bloque-uña libre del pasador siguiente (empuje) / en el empuje guiado | 0,821 / 0,737 | sin cambio |
| Placa-guía libre del seguidor / sin autobloqueo | 0,500 / 0,037 | sin cambio |
| Pasador Q fuera de la mesa | 0,974 | 0,974 |
| Bloque-uña dentro de la luz libre entre anillos (h_disc − 2·t_anillo) | 0,962 | **1,000** (150 = 140 + 10; geo ≤ 1) |
| Bloque-uña sobre la placa-leva / cuerpo sobre la placa-guía (alzado) | 0,559 / 0,561 | 0,613 / 0,612 |
| Cuerpo del cilindro libre sobre la base / oreja inferior E sobre la base | 0,490 / 0,187 | 0,507 / 0,250 |
| Pasador E sobre el refuerzo | 0,185 | 0,500 |
| Soporte E / placas-guía dentro de la base; placas fuera de la mesa | 0,999 / 0,936 / 0,961 | sin cambio |

Gira en todos los casos (FS 0,900 de diseño; contaminada 0,900; borde 0,899: sin cambio). Las verificaciones en planta no dependen de δ; las de
alzado mejoran porque el eje baja 5 mm.

### 9.6 Pendientes

1. ULTRA VST: p_adm, E, μ, PV y α del proveedor (hoy supuestos); desgaste del inox espejo frente al UHMW.
2. WPS disímil 304–A36 con ER309L (AWS D1.6) y probeta de tapón en lámina de 3 mm; verificar g₀ ≤ 0,2 mm en la primera mesa.
3. Base > 20 mm: el núcleo no tiene calibración propia (el crédito BX sale de la FEA de Mindlin del verificador independiente sobre este diseño);
   recalibrar `DBL_CAL` con t_base = 25 si se cambia la geometría.
4. Textos de material del núcleo (exportación de planos) siguen diciendo «S355J2» con el Fy del parámetro (250); el refuerzo pide calidad Z en
   el espesor (con A36: ASTM A770). El generador de planos (`cad/bx3d.py`, `cad/bx_notas.py`) y `Tornamesa_BX_v1.0.html` no se tocaron: el
   modo 1 exporta `disco.tornillos` vacío y los bloques nuevos `disco.lamina`, `disco.tapones` y `disco.costura`.
