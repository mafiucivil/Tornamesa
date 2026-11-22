# TT300-BX · Tornamesa con interfaz inoxidable–UHMW simplificada (módulo aparte)

> **Revisión 9b vigente (21-11-2026): carga de diseño 250 t, alivio 540 bar, alarma 480 bar, retorno limitado a 150 bar; ejes sin tratamientos térmicos de proceso; buje templado
> reemplazable en el seguidor del pasador Q (§13.6).** Las cifras de 290 t y 680/600 bar de las secciones §11 a §13.5 son el registro de las revisiones 7 y 8.

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

## 10. Revisión 6 (18-11-2026): calidad de acero POR PIEZA

Decisión del mandante: ASTM A572 Gr. 50 (Fy 345, Fu 450) en las piezas que gobernaban con A36 y espesores menores; ASTM A36 (Fy 250, Fu 400)
en el resto con los espesores de la rev. 5. Aceros especiales sin cambio.

### 10.1 Implementación

- Núcleo (`tt300c.js`), aditivo: claves OPCIONALES `Fy_pr/Fu_pr` (anillos de pasadores), `Fy_base/Fu_base` (plancha base), `Fy_boxE/Fu_boxE`
  (paredes traseras, muñones y tapas del soporte del ojal E) y `Fy_dbl/Fu_dbl` (refuerzo de esquina y atiesador), leídas con `fyOf/fuOf`: sin la
  clave o con valor ≤ 0 se usa el global `Fy/Fu`. El núcleo no las define en `PARAM_GROUPS` (golden y `params_defaults.json` sin cambio); sin ellas
  los resultados son bit-idénticos (prueba contra a67d98e y subconjunto golden). `thermalP` las reduce con k_Fy solo si existen.
- Módulo BX: las define en su grupo (`Fy_pr = Fy_base = Fy_boxE = 345`, `Fu_* = 450`; `Fy_bxc/Fu_bxc` del portador = 345/450; `Fy_dbl = 0`: A36).
- Filas que usan cada calidad: anillos (aplastamiento del agujero y la fila del empotramiento); tapas E (aplastamiento y los dos desgarros);
  paredes E (flexión, corte, CJP pared–pared); base (filas sin refuerzo, modo guiado, torsión, aplastamiento de los tornillos de la placa-guía
  con `Fu_base`); portador (ligamento, torsión: `Fy_bxc`); textos de material de `designDrive` y de la tabla de fabricación.
- Criterio con piezas de distinta calidad (explícito, conservador): la MENOR Fy de las partes involucradas.
  - Flexión base + refuerzo (sección compuesta) y crédito BX de la FEA: mín(Fy_base, Fy_dbl) = 250.
  - Asiento del pivote (base + collar A36): 250.
  - CJP paredes E–asiento (J-E1, J-E2, J-E6): en la línea de fusión la tracción y el corte de la pared pasan tal cual al asiento (tracción en el
    espesor del refuerzo), así que gobierna mín(Fy_boxE, Fy_dbl) = 250 (sin refuerzo: la base).
  - Atiesador tangencial: el del refuerzo (A36, RIB_T = 30 sin cambio).
  - Izaje (σvm de la base) y tornillos del disco del modo 0 (anillo o plancha inferior): el global (A36), del lado seguro.
- Anillos de distinto espesor: el núcleo verifica el pasador de empuje con un solo anillo t = máx(t_pr, t_top, t_bot) = 25. Con t_pr = 22 < t_top = 25
  el anillo superior queda de máx(t_pr, t_top) = 25 (como la masa del núcleo) y el inferior de máx(t_pr, t_bot) = 22. BX agrega (`ringRows`):
  aplastamiento en el anillo inferior de 22 (FU 0,927), flexión del pasador con la luz entre planos medios h − (25 + 22)/2 (0,921) y bisel de la
  soldadura en el anillo de 22 (S 16 ≤ 17: 0,941). Las filas del núcleo quedan (0,817 / 0,910 / 0,800).
- Base bajo el soporte E (t_base = 22): FEA de Mindlin del verificador (copia de `tests/indep_plancha_base_E.py` §4) sobre el JSON de diseño rev. 6
  (refuerzo automático de 65 mm, paredes de 25): nom/dis/cal 0,174/0,548/0,771 y retorno 0,848 con Fy 250, frente al núcleo 0,195/0,575/0,799/1,052.
  El factor del empuje de la rev. 5 (0,937) quedaba 3 % del lado inseguro: se adopta 0,965 (cociente máx. de la FEA rev. 6); el del retorno se deja en
  0,846 (la FEA da 0,806). Pico del retorno en la base sola (t = 22, A572: con Fy 345 FU 0,614) y del calado en la franja del atiesador (A36).
  Filas BX: calado 0,771, retorno 0,890.

### 10.2 Piezas, espesor y calidad

| Pieza | Espesor (mm) | Calidad |
|---|---|---|
| Anillos de pasadores (inferior / superior = máx(t_pr, t_top)) | 22 / 25 | A572 Gr. 50 |
| Plancha base | 22 | A572 Gr. 50 |
| Soporte E: paredes traseras y muñones / tapas | 25 / 25 | A572 Gr. 50 |
| Portador de pastillas (UHMW 30 → saliente 8) | 22 | A572 Gr. 50 |
| Mesa: plancha superior / inferior / almas y nervios | 25 / 20 / 8 | A36 |
| Refuerzo de esquina (automático) / atiesador tangencial | 65 / 30 | A36 + calidad Z (A770) |
| Collar del pivote, marco, orejas | 70, … | A36 |

### 10.3 FU gobernantes (con FEA de la mesa)

| Verificación | FU |
|---|---|
| **CJP paredes E–refuerzo (metal base, mín(345; 250))** | **1,020 — NO CUMPLE** |
| Tapas E: desgarro hacia las paredes / aplastamiento | 0,943 / 0,885 |
| Asiento del pivote con H·e (base 22 + collar 70, Fy 250) | 0,930 |
| Portador: torsión / ligamento | 0,927 / 0,834 |
| BX · anillo inferior de 22: aplastamiento / pasador con luz entre planos medios | 0,927 / 0,921 |
| Pasador entre anillos (núcleo) / anillo (núcleo, t = 25) | 0,910 / 0,817 |
| Refuerzo: tapones / atiesador 30 × 60 | 0,916 / 0,887 |
| Base bajo E (BX, FEA): retorno / calado | 0,890 / 0,771 |
| Pasador vertical E / paredes E flexión | 0,824 / 0,739 |
| Pastillas p + Δp / PV | 0,767 / 0,843 |
| Mesa: plancha superior / inferior (global + local) | 0,782 / 0,785 |

Cinemática sin cambio: carrera 0,959, sincronía 0,971 (peor caso 0,965), reenganche 0,904, luz entre anillos 0,938 (h − 2·25). Masa 3 843 kg
(rev. 5: 4 100). Con `Fy_dbl = 345` (refuerzo y atiesador de A572 Gr. 50 + A770) todo cumple (CJP 0,739; refuerzo automático más delgado; 3 760 kg);
con paredes E de 28 mm también (CJP 0,935), con 30 no (desgarro de las tapas 1,016).

### 10.4 Pendientes

1. Decisión del mandante sobre la CJP paredes E–refuerzo (FU 1,02 con el criterio de la menor): refuerzo y atiesador en A572 Gr. 50 + A770
   (`Fy_dbl = 345`), o paredes de 28 mm, u otro criterio justificado.
2. `packages/web/planos_export.js` (lista de materiales) sigue con un solo texto «A572 Gr.50 (Fy global)» para todo el acero; no se tocó (fuera del alcance).
3. Recalibrar `DBL_CAL` del núcleo con t_base = 22 (hoy crédito BX por cociente de la FEA independiente).
4. Herramientas HTML sin reconstruir (`Tornamesa_v*.html`, `Tornamesa_BX_v1.0.html`).

## 11. Revisión 7 (18-11-2026; reemplazada en carga y presiones por la rev. 9, §13.6): 290 t, 680/600 bar, todas las planchas en A572 Gr. 50 y de 22 mm (reemplaza a la rev. 6)

Configuración por defecto: W_tf = 290, p_relief = 680, p_alarm = 600; global Fy/Fu = 345/450 (ASTM A572 Gr. 50) y claves por pieza en 0 (= global,
siguen disponibles); t_top = t_bot = t_pr = t_base = bx_tc = pv_tbox = pv_tl = 22; atiesador tangencial 22 (clave nueva opcional del núcleo `rib_t`:
ausente o ≤ 0 = RIB_T = 30, bit-idéntico); almas y nervios 8, collar 70, orejas 18, marco 10, refuerzo de esquina automático (45 mm). Lámina 3 mm,
ULTRA VST 30 (saliente 8), 20 °C sin cambio. Capacidad en el bloque bx exportado (`capacidad_nominal_tf`, `revision`).

FU (con FEA de la mesa; sin fallas, gira): tapas E desgarro 0,999 / aplastamiento 0,977; base bajo E (BX, FEA) calado 0,962 / retorno 0,824; anillo
0,900, bisel 0,941; pasador entre anillos 0,905; portador torsión 0,900 / ligamento 0,810; alarma 0,980; paredes E flexión y CJP 0,794; pasador E 0,756;
asiento del pivote 0,653; atiesador 22 × 60: 0,482; pastillas p + Δp 0,747 / PV 0,815; mesa superior 0,692 / inferior 0,465. F_calado 432,6 kN;
FS nom/dis/borde/cont/seco 4,124/1,396/1,118/1,117/1,320. Cinemática: carrera 0,959, sincronía 0,971, reenganche 0,904, luz entre anillos 0,904.
Masa 3 721 kg. Las tapas E son lineales en p_relief (F_calado ∝ p): 1,006 × 680/700 = 0,977.

FEA de la base bajo el soporte E: con la malla de 40 mm de la calibración el sistema es singular (paredes de 22 mm); con 20/25/30/35 mm no converge en
malla (calado 0,865/0,900/0,962/0,816; retorno 0,824/0,654/0,666/0,471; núcleo 0,831/0,785). Se reemplaza el crédito por la envolvente (factor 1,158 en el
empuje y 1,050 en el retorno sobre la fila del núcleo, con t_base ≥ 22; sin crédito por espesor). Pendiente: estudio de convergencia de malla de la FEA
de la base (máscara rígida de soportes delgados) y recalibración de `DBL_CAL` con la geometría rev. 7.

### 11.1 Planos de fabricación (cad/, 18-11-2026)

`python3 cad/generar_paquete.py <JSON BX> --out <dir>` genera el juego BX rev. 7 desde el JSON (fuente única; sin valores a mano):

- **INT-021** (pieza nueva, solo con `bx_disc_modo = 1`): lámina inoxidable espejo soldada a la mesa: planta con los paneles y la junta, tabla
  de tapones por anillo, tabla de paneles, detalles de la junta a tope CJP (J30), del tapón Ø14 relleno = t esmerilado a ras (J34) y de las
  costuras perimetrales (J35 exterior, J36 interior), secuencia de soldadura por zonas (`disco.fabricacion`), g₀ ≤ 0,2 mm, WPS disímil 309L
  calificada (AWS D1.6; D1.3 como referencia del tapón en lámina ≤ 4,8 mm) y probeta de tapón antes de producción. INT-016 (disco) e INT-017
  (tornillos) quedan para el modo 0; en el modo 1 no hay roscas del disco en MES-003 / MES-004.
- Registros de códigos: variante «BX-L» (lámina soldada) en `VAR_CODIGOS` (base, placas-guía, mesa inferior y anillo, cubo, pivote, soporte E
  22, pasadores E y Q) y `VAR_REFUERZO` (BAS-045: refuerzo 550 × 550 × 45; BAS-046: atiesador 22 × 60 × 500).
- Materiales del soporte E, refuerzo (A770, calidad Z) y portador tal como los exporta el núcleo (A572 Gr. 50), sin «S355J2»; cajetín con la
  capacidad `W_tf` (290 t) y la presión de alivio `p_relief` (680 bar) del JSON.
- Sin bloque «bx» el juego TT300-C no cambia (DXF de GEN-001, GEN-003, GEN-005, GEN-008, GEN-012, CON-007, CON-009, BAS-001, BAS-012, MES-003
  y MES-011 comparados entidad por entidad con HEAD).

## 12. Revisión 7c (19-11-2026): mesa con una plancha completa por nivel (`bx_mesa_entera = 1`, por defecto)

Decisión del mandante (ingeniero revisor): cada nivel de la mesa (superior e inferior) es **una plancha completa Ø2000 × 22 de ASTM A572 Gr. 50**
con los 28 agujeros Ø85 H7 de los pasadores de empuje en la misma pieza, en lugar del disco Ø1720 (MES-001 / MES-003) más el anillo de pasadores
Ø2000/Ø1720 (MES-002 / MES-004) en 4 segmentos de 90° con empalmes CJP y unión soldada circunferencial plancha–anillo.

- Parámetro `bx_mesa_entera` (grupo BX): 1 = plancha entera (por defecto); 0 = disco + anillo (revisiones anteriores, sin cambios).
- Exige `t_pr = t_top = t_bot` (una sola plancha por nivel): si no, la fila geométrica «BX · Mesa de plancha entera: un solo espesor por nivel»
  falla (NO CUMPLE), el validador da un error y `BX.exportBX` lanza un error claro (no se emiten planos).
- Las uniones plancha–anillo y los empalmes CJP de los segmentos (que solo existían en el generador de planos: juntas J11–J13) no aplican: fila informativa.
- Masas: el núcleo (`massesMesa`) ya suma el disco Ø 2·R_anillo,int con t_top / t_bot y la corona R_anillo,int…R con máx(t_pr, t); con espesores
  iguales es exactamente la plancha completa (sin doble conteo en el traslape R860…R1000): fila informativa con el cálculo independiente.
- FEA de la mesa: sin cambio (mismos espesores y misma rigidez; la FEA del núcleo no modela la unión plancha–anillo). FU gobernante 0,999
  (tapas del cajón E, desgarro a calado), estado CUMPLE, igual con `bx_mesa_entera = 0`.
- JSON de diseño: bloque `bx.mesa = { plancha_entera, D, t, agujeros: { n, d, ajuste, R }, formato_min, masas, nota }` que el generador de planos usa para
  dibujar MES-001 / MES-003 como planchas completas y quitar MES-002 / MES-004 con sus soldaduras. Compra: plancha de 22 mm de al menos 2000 × 2000.

## 13. Revisión 7d (19-11-2026): cilindro hidráulico FABRICADO (`bx_cyl_on = 1`, por defecto)

Decisión del mandante: el cilindro deja de ser comercial (ACC-013 especificación de compra) y se fabrica según su croquis. Parámetros nuevos `bx_cyl_*`
(grupo «TT300-BX · cilindro hidráulico fabricado»); el núcleo recibe `d_rod = 65`, `pv_Fyrod = 520`, `c_rod = 84` y `m_cyl = 45` como valores por defecto
del módulo (tt300c.js sin cambios; `BX.defaults({ cyl: false })` vuelve al comercial). Verificaciones en el grupo **«Cilindro»** (58 filas, `sys = est`);
bloque **`bx.cilindro`** del JSON = fuente única de las láminas (cotas, tolerancias, Ra, alojamientos de sellos, puertos, pares, secuencia).

### 13.1 Hipótesis y criterios

| Tema | Hipótesis / criterio | Referencia |
|---|---|---|
| Presiones | Servicio a p_alivio 680 bar; prueba hidráulica a 1,25·p_alivio = **850 bar** (cada cámara, pistón a tope) | Decisión del mandante |
| Admisibles | Servicio: Fy/1,5 (corte Fy/(1,5·√3)); prueba: 0,9·Fy (corte 0,9·Fy/√3); aplastamiento de contacto 0,9·Fy en ambos (AISC J7, conservador) | Criterio del proyecto |
| Fuerzas | Calado p·A = 432,6 kN; cámara anular p·(90² − 65²)·π/4 = 207,0 kN (retorno con p_alivio, conservador frente a 200 bar); tapa delantera: el mayor entre p·A (fin de carrera con el vástago libre) y p·A_an | Equilibrio |
| Camisa | Barra hueca ST-52 (St 52-3 ≈ S355J2) 132 × 80 maquinada a Ø130 × Ø90 H8 bruñida; Fy 345, Fu 470 | Mandante |
| Fondo | Copa (placa + falda de 44) torneada de plancha de 80; con S355J2 (Fy 325 a 63 < t ≤ 80) UG-34 pide **28 mm** y el cuerpo deja c_vástago 77 < 83 (no cabe el cuello del ojal del vástago entre las mejillas del bloque-uña): se adopta **S460NL (EN 10025-3, Fy 410) de 21 mm** (UG-34 pide 20,92). La CJP con la camisa queda a 45 mm de la placa (zona de membrana) y lleva el puerto A | ASME VIII-1 UG-34 (C = 0,33·m ≥ 0,20) con S = Fy/1,5; Roark Tabla 11.2 caso 10b |
| Tapa | M110 × 2 en 30 (L_e = 23 descontando garganta, salida y chaflán); sellos y o'ring estático (espiga Ø89,5 f7) por DENTRO de la rosca: la zona roscada (pared 10) no ve presión. Por eso la tapa mide 57 (espiga 12 + rosca 30 + reborde 15) y no 45: el croquis pedía la espiga y la rosca en los mismos 30 mm, lo que no es construible (se eligió lo conservador: la rosca completa de 30) | FED-STD-H28 (áreas de arranque) |
| Pistón | 28 mm (sello de doble efecto ISO 7425-1 entre dos guías ISO 10766, resaltes de 3 mm) + tuerca ranurada M48 × 2 de 20 = 50; la tuerca es el tope del retraído contra el fondo y deja el hueco del puerto A | VDI 2230 (F_S = F_V + Φ_n·F_A, Φ_n 0,25, F_V = 207 kN, M_A 1430 N·m) |
| Vástago | Ø65 f7 cromado común (Fy 520: dato confirmado por el mandante 19-11-2026; Fu 700 supuesto, no gobierna), cromo ≥ 20 µm, Ra ≤ 0,2; ojal soldado por fricción (ISO 15620, procedimiento calificado WPS-CIL-03 aceptado por el mandante 19-11-2026) a 95 mm del eje del ojal, rectificado y cromado después | AISC 360-22 H1/E3 |
| Ojales | Trasero: orejeta R80 × 50 (S355J2) soldada al fondo (CJP en K) con rótula **GE70ES** (d 70 = pasador E, D 105, B 49 ≤ 54 entre tapas, C 40; C₀ = 1200 kN, dato confirmado por el mandante 19-11-2026). Vástago: R68 × 50 con agujero Ø90 H9 **sin rótula**: la GE90ES (D 130, B 60) no cabe en Ø ≤ 136 ni en la horquilla de 54 | ASME BTH-1 §3-3.3 (N_d = 3) |
| Puertos | G 3/8 (ISO 1179-1): el retorno saca 20,9 L/min por cilindro por el puerto A (G 1/4 con paso Ø8 daría 6,9 m/s > 5) | Criterio del proyecto (≤ 5 m/s) |
| Amortiguación | No lleva: retorno al tope a 54,8 mm/s < 0,1 m/s (criterio usual de catálogos Parker/Bosch Rexroth, confianza C); masa en movimiento ≈ 78 kg, E_c ≈ 0,12 J; el avance (10,5 mm/s) no llega a la tapa (s_usada 220,4 de 235) | ISO 4413 §5.4 |

### 13.2 Resultados (FU servicio / prueba)

Camisa Lamé 0,983 / 0,911 (Pm ASME VIII-2 0,827; p_y 1037 bar); fondo Roark 0,857 / 0,793, UG-34 0,992 / 0,846; CJP fondo–camisa 0,499 / 0,462;
rosca de la tapa (camisa / tapa) 0,468 / 0,434 y 0,574 / 0,532; tracción de la camisa en la rosca 0,499 / 0,462; vástago flexocompresión 0,846 (núcleo igual),
Euler 0,428, garganta de la rosca M48 0,468 / 0,364, filetes 0,798 / 0,621, tuerca 0,522; resalte 0,655 / 0,819; pistón (resalte de la ranura) 0,775 / 0,718;
soldadura por fricción 0,793; ojal del vástago 0,698 / 0,537 / 0,710; ojal trasero 0,721 / 0,567 / 0,738, CJP en K 0,526, cuello 0,592; rótula 0,721.
Largo: e_cuerpo 75 + cuerpo 361 (fondo 21 + interior 283 + espiga 12 + rosca 30 + reborde 15) + c_vástago 84 = 520; camisa 279 (corte 285).
Estado global con FEA: CUMPLE (FU máx. 0,999, tapas del cajón E, sin cambio).

### 13.3 Revisión 7e (19-11-2026): confirmaciones del mandante, fila térmica y esquema

- Datos confirmados por el mandante 19-11-2026: C₀ de la GE70ES = 1200 kN; sellos 680 bar de trabajo y 850 bar de prueba (la fila pendiente pasa a dos
  verificaciones: p_alivio ≤ 680 y p_prueba ≤ 850, FU 1,000); vástago cromado común Fy 520; soldadura por fricción con procedimiento calificado WPS-CIL-03.
- Escenario térmico: con el cilindro fabricado la fila «aceite atrapado tras el calado» compara con p_prueba = 1,25·p_alivio = 850 bar (gancho P.__bx.p_prueba_cil;
  sin __bx el núcleo no cambia): FU 0,648 → 0,800 a 20 °C y 1,375 → 1,698 a 80 °C (fila fuera del alcance térmico, informativa). Las filas p_hold + Δp y
  p_ret + Δp siguen con p_max_cil = 700 bar (10 000 psi); para el cilindro fabricado la presión de trabajo confirmada de los sellos es 680 bar (pendiente de decisión:
  bajar p_max_cil a 680 o mantener 700); a 80 °C la válvula de alivio térmico del tramo aislado sigue siendo necesaria.
- Lámina nueva ACC-036: esquema retraído / extendido a la misma escala (1:2,5), alineados por el eje E, con las medidas ojo a ojo 520 / 755, carrera 235,
  cuerpo 361, e_cuerpo 75 y c_vástago 84 / 319. La rótula comercial pasa al código ACC-045 (ACC-036 es la lámina del esquema).

### 13.4 Estudio del ojal del vástago (rev. 7e) y revisión 7f (19-11-2026)

En planta el mecanismo es plano (pasadores verticales E y Q): una rótula en Q no cambia la cinemática. El ojal liso H9/f8 de 50 puede tomar momento en alzado
por (i) la componente axial de la reacción H de la placa-guía por el brazo l_Q = 74,5 (máximo del empuje a calado: H = 94,0 kN con φ = 41,7°, H·sen φ = 62,5 kN,
**M_H = 4,66 kN·m**; cota con los 94 kN axiales: 7,0 kN·m) y (ii) un desnivel Δz entre los ejes E y Q (M = k_c·Δz/L).
Script del estudio: `scratchpad/bx7e/estudio_ojal.js` (no forma parte del repositorio; solo evaluación).

| Opción | FU vástago (100 % de M: 4,66 / 7,0) | FU soldadura por fricción | Cambios |
|---|---|---|---|
| **Adoptada: Ø65, ojal liso H9/f8** | 0,846 con el reparto real (el bloque-uña toma M_H) · 1,024 / 1,181 si todo fuera al vástago | 0,793 · 1,025 / 1,233 | Tolerancia Δz E–Q ≤ ±1 mm |
| GE90ES en el ojal del vástago | ≈ 0,846 | 0,793 | Ojal R 85,5, horquilla 64, R_cubo 87,5, c_vástago ≥ 91 (no cabe con 520), cajón E con b_ojal 60 (base bajo E 1,019): no cumple sin rediseño |
| GE70ES + pasador Q escalonado | ≈ 0,846 (pasador Ø70: 0,86) | 0,793 | Ojal R 75 y R_cubo ≥ 77 (parámetro nuevo en el núcleo) |
| Vástago Ø70, ojal liso | 0,677 · 0,810 / 0,927 | 0,844 / 1,011 | Alojamientos nuevos; pared de 4,7 mm bajo la espiga |

Reparto: el bloque-uña toma M_H por el contacto contra el pasador P sin despegue (F·h/6 = 466,8·140/6 = 10,9 kN·m ≥ 4,66; presión de borde × 1,43, Hertz × 1,20);
su rigidez rotacional (≈ 8×10⁹ N·mm/rad, orden de magnitud) es ≈ 4,5 veces la del cilindro articulado en E (k_c ≈ 1,8–2,2×10⁹), y con el giro libre del ajuste
H9/f8 (0,72…3,54 mrad) al vástago le llega ≈ 0 (≤ 18 % sin holgura). **Recomendación: mantener la opción adoptada con la tolerancia de desnivel.**

Revisión 7f (aprobada por el mandante 19-11-2026):
- **Tolerancia de desnivel E–Q ±1 mm** (`bx_cyl_dz`): cada eje a su cota ± 0,5 sobre la base (cota en CON-010; nota en BAS-012, ACC-020, CON-007, CON-010 y ACC-036).
  Filas geo del grupo «Cilindro»: Δz 1,0 ≤ Δz_adm = M_adm·L/k_c con holgura nula en el retraído (el más rígido) = 1,00 mm (FU 0,996; el estudio daba 1,27 mm a
  L = 544, posición del M_H máximo; con el giro libre mínimo del ajuste 1,38 mm), M_adm = 4,26 kN·m; reparto del momento M_H 4,66 ≤ F·h/6 10,89 kN·m (FU 0,427).
- **p_max_cil = 680 bar** en los valores por defecto del módulo (CYL_CORE; el núcleo sin __bx no cambia). Filas que dependen de p_max_cil (todas del escenario
  térmico, fuera del alcance térmico, informativas): p_hold + Δp 0,696 → 0,716 (20 °C) y 1,786 → 1,839 (80 °C); p_ret + Δp 0,286 → 0,294 y 1,376 → 1,417; válvula de
  alivio térmico «no hay» 0,696 → 0,716 y 1,786 → 1,839 (a 80 °C: instalar alivio térmico); «tras el calado» compara con 850 bar (sin cambio: 0,800 / 1,698).
  «Alivio dentro de la presión nominal» usa p_rated (10 000 psi = 700 bar): 0,971 sin cambio. Veredicto: CUMPLE (sin cambio).

### 13.5 Revisión 8 (20-11-2026): observaciones del fabricante hidráulico (aprobadas por el mandante)

- **Fondo rediseñado** (criterio: ningún sello del pistón pasa sobre la soldadura ni su ZAC; el pistón trabaja solo en la camisa bruñida): bloque macizo de
  **S355J2 (EN 10025-2), t = 37 mm** = pestaña Ø130 h11 × 10 + espiga Ø90 g6 × 27 que entra en la camisa (ajuste con juego; su cara es el tope del retraído,
  la tuerca del pistón apoya contra ella); torneado de plancha de 40 (Fy 345 a t ≤ 40). Sin falda. Ojal trasero (ACC-030) soldado al bloque (J38, sin cambio).
- **Soldadura fondo–camisa J37: CJP en J de un lado** (bisel J en el extremo de la camisa, hombro de la pestaña a escuadra, la espiga integral hace de
  respaldo permanente; separación de raíz 3). Se eligió CJP y no PJP + filete porque la unión retiene presión y empotra la camisa (flexión de borde P + Q):
  la CJP da sección plena, se inspecciona por UT y no deja raíz sin fundir expuesta a la fatiga; lleva un filete de refuerzo z6 en el pie del lado del bloque
  (suaviza la transición; no se cuenta en la resistencia).
  FU primaria 0,272 / 0,252 (prueba); P + Q (ASME VIII-2 §5.5.6.1, ≤ S_PS = 2·Sy; prueba ≤ 0,9·2·Sy) 0,583 / 0,809. UG-34 con C = 0,33·m ≥ 0,20 para la junta nueva (croquis (g) con espiga integral).
- **Distancia del plano de la soldadura a la cara trasera del pistón en el retraído = 47 mm** (espiga 27 + tuerca 20) ≥ 20 mm (fila geo, FU 0,426); el primer
  sello recorre solo la camisa bruñida (fila geo, FU 0,659). Bruñido del Ø90 H8 en toda la carrera DESPUÉS de soldar y del alivio de tensiones (nota en ACC-028).
- **Puerto A**: en el bloque no es factible con L0 = 520: el refrentado Ø34 de G 1/2 necesita ≥ 40 mm de bloque fuera de la camisa (cuerpo + 18 mm; e_cuerpo
  bajaría a 56 y el ligamento de la orejeta a 3,5 mm). Se dejó **en la camisa, junto al fondo**, sobre el hueco de la tuerca en el retraído (paso Ø12; refrentado
  lejos de la CJP, FU 0,876; paso libre, FU 0,800). Desviación de lo pedido: queda para decisión del mandante / fabricante.
- **Largos** (L0 = 520 y carrera 235 se mantienen): e_cuerpo 65 + cuerpo 377 (fondo 37 + interior 283 + espiga de la tapa 12 + rosca 30 + reborde 15) +
  c_vástago 78 = 520; camisa 349 (corte 355). El cajón E sigue cumpliendo (holgura sin cambio).
- **Puertos G 1/2** (ISO 228-1, ISO 1179-1, sello ED) A y B. B cabe en la pared de 20: fondo de la rosca a r 48,7 ≥ 47 (FU 0,964), el agujero roscado termina
  en x = 287,8 < 295 (inicio del refrentado de la M110, FU 0,976), paso Ø8 libre del pistón en la carrera (FU 0,996).
- **S3 (o'ring estático pistón–vástago)**: o'ring métrico **50 × 4 NBR 90 con anillo de apoyo** (ISO 3601-2), ranura en el agujero del pistón Ø56,4 H9 × 8,2
  sobre la espiga Ø50 (el vástago no se ranura). Nota: el fabricante mencionó «Ø42», a confirmar.
- **Tabla «Datos técnicos y capacidad del cilindro»** (bloque `bx.cilindro.capacidad`, 16 filas) en ACC-013, resumen en ACC-036 y especificación hidráulica en
  GEN-008: empujes 432,6 kN (680), 381,7 (600), 309,8 a 487 bar (diseño), 387,3 a 609 bar (grasa contaminada), retracción 60,9 / 207,0 kN (200 / 680), prueba
  540,7 kN (850); caudales, velocidades (10,5 / 54,8 mm/s) y volúmenes (1,495 / 0,715 L); sellos 680 / 850; mangueras 3/8" de 10 000 psi (690 ≥ 680);
  racores G 1/2 con reducción a 3/8"; línea A 4,9 m/s ≤ 5 con 3/8" (preferible 1/2"); cilindros en paralelo, alivio común, bomba con compensador de presión, SIN
  divisor de caudal (iguala desplazamientos y puede intensificar la presión en un cilindro trabado); compra comercial: ≥ 45 t a 700 bar, con 50 t regular el
  alivio para F ≤ 432,6 kN.
- Desnivel E–Q (rev. 7f) con el cuerpo nuevo: con holgura nula en el ojal la fila da 1,048 y pasa a **informativa**; la fila de verificación usa el giro libre
  mínimo garantizado del ajuste H9/f8 (0,72 mrad): Δz 1,0 ≤ 1,329 mm (FU 0,753).
- Láminas: ACC-013 con la tabla de capacidad (3 columnas de pares dato–valor) y el corte a 1:2,5 (antes 1:2) para que quepa en A1; ACC-028 con los puertos A y B
  G 1/2 (núcleo Ø18,6), ACC-029 rehecha (bloque con espiga), ACC-032 con la ranura del o'ring S3 50 × 4, ACC-036 con el resumen de capacidad, GEN-008 con la
  especificación hidráulica; par de los racores G 1/2 con sello ED 130 N·m (valor usual de catálogo, a confirmar con el racor). Paquete: exit 0, controles en 0.

| Fila (FU servicio / prueba) | Rev. 7f | Rev. 8 |
|---|---|---|
| Fondo, flexión de placa (Roark) | 0,857 / 0,793 | 0,328 / 0,304 |
| Fondo, UG-34 | 0,992 / 0,846 | 0,467 / 0,394 |
| CJP fondo–camisa (primaria) | 0,499 / 0,462 | 0,272 / 0,252 |
| CJP fondo–camisa P + Q (nueva) | — | 0,583 / 0,809 |
| Distancia soldadura → pistón (nueva, ≥ 20 mm) | — | 47 mm (0,426) |
| Puerto A, refrentado lejos de la CJP | 0,957 | 0,876 |
| Puerto A, velocidad en el paso | 0,887 | 0,616 |
| Desnivel E–Q | 0,996 | 0,753 (holgura nula 1,048, informativa) |
| Ojal trasero libre del soporte E | 0,881 | 0,806 |
| Cuello del ojal del vástago | 0,988 | 0,987 |

### 13.6 Revisión 9 (20-11-2026): carga de diseño 250 t, alivio 540 bar, ejes sin tratamiento térmico y buje templado del seguidor (decisiones del mandante)

**Valores por defecto** (`A36_DESPUES` de tt300bx.js y grupo BX): `W_tf` 250 t (rev. 7–8: 290), `p_relief` 540 bar y `p_alarm` 480 bar (rev. 7–8: 680 / 600). FS del giro en el caso
de diseño 1,267 ≥ 1,25 (FU 0,987); con 530 bar no cumple (prueba en tests/test_tt300bx.js). La geometría del cilindro (Ø130 × Ø90, vástago Ø65, L0 520, carrera 235) no cambia;
`p_max_cil` de los sellos sigue en 680 bar.

**Ganchos aditivos del núcleo** (tt300c.js lee `P.__bx`; sin `__bx` es bit-idéntico: `tests/indep_tt300c.py` «sin diferencias», prueba de la base a67d98e y golden):

| Clave de `P.__bx` | Efecto | Norma |
|---|---|---|
| `Fb_redondo` = 1,25 (`bx_Fb_red`) | Flexión de pasadores macizos Fb = 1,25·Fy/Nd: pasador E, pasador Q, pasador de empuje (biapoyado) y pivote | ASME BTH-1-2020 §3-2.3.3 (confirmado por el mandante) |
| `kFy_pQ` = Fy_Q / Fy_pp | Pasador Q con su propio Fy (315) y el E con `Fy_pp` (325); cociente: en el escenario térmico se aplica al Fy reducido a T | EN 10025-2 (S355J2+N, 63 < t ≤ 80: 325; 80 < t ≤ 100: 315) |
| `brg_min` | Aplastamiento con mín(Fy pasador, Fy plancha): tapas del cajón E, horquilla del bloque-uña en Q, asiento del pivote (y ojal del vástago en el módulo) | AISC 360-22 §J7 |
| `mq_split` | Pasador Q por combinaciones simultáneas: (a) empuje a calado F_calado + H del empuje guiado; (b) retorno F_ret + N_atasco (el atasco ocurre al retraer). Gobierna la mayor | ASME BTH-1 §3-3.3 / §3-2.3.3 |
| `k_base`, `td_min` | El refuerzo de esquina se elige con el mismo factor de la FEA de la base que aplica la fila BX y no baja del espesor de la calibración (45 mm) | ASME BTH-1 §3-2.3; docs/bx §11 |

**Materiales (sin tratamientos térmicos de proceso)** — bloque `bx.materiales` del JSON (fuente única de las láminas):

| Pieza | Material | Fy de cálculo |
|---|---|---|
| Pasador E Ø70 (ACC-014) | S355J2+N barra redonda (EN 10025-2), sin bonificado ni temple | 325 (63 < t ≤ 80) |
| Pasador Q Ø90 (ACC-016) | S355J2+N barra redonda, sin tratamiento; extremo rebajado Ø70 k6 | 315 (80 < t ≤ 100) |
| Pasadores de empuje Ø85 (MES-012) | 42CrMo4+QT / AISI 4140 bonificado de stock (EN 10083-3), SIN temple por inducción | 650 (40 < d ≤ 100); Fy_surf = 650 |
| Pivote Ø120 (PIV-001) | C45+N (EN 10083-2), sin tratamiento (confirmar con el fabricante del buje autolubricado Ø150/Ø120 × 80 la dureza mínima del eje) | 275 (100 < d ≤ 250) |
| Bloque-uña (ACC-027) | 34CrNiMo6+QT; asiento SIN temple: Hertz conforme con Fy_sup = mín(650, 800) = 650 → FU 0,319 (cumple) | 800 |
| Placas-guía (ACC-020/024) | 42CrMo4+QT (pista del seguidor), canto desnudo fresado y engrasado, SIN revestimiento inoxidable | 750 |
| Buje del seguidor (ACC-046, nuevo) | 42CrMo4+QT templado por inducción 55–60 HRC, capa ≥ 4 mm, revenido 180 °C | núcleo 750 |

Pasadores de empuje soldados: CE_IIW ≈ 0,80 (composición típica; ≈ 0,90 con los máximos): no precalificado (AWS D1.1:2020 Tabla 5.3), WPS por ensayo, precalentamiento por el
método de control de hidrógeno del Anexo B (Zona III, H4, restricción alta: del orden de 250–300 °C, con el CE del certificado 3.1), interpase ≤ 300 °C y bajo la temperatura de revenido.

**Buje del seguidor** (`bx_buje = 1`): copa Ø90 f7 × 46 (fondo 8) sobre el extremo del pasador Q rebajado a Ø70 k6 (H7/k6), hombro a z = 70 con acuerdo r 3, retenida por un
tornillo ISO 10642 M12 × 25 10.9 con fijador medio; Ø exterior = d_Q, así el seguidor no cambia. Se eligió 42CrMo4 templado por inducción y no 16MnCr5 cementado: la profundidad del
corte máximo de Hertz pide capa ≥ 2·0,786·b y la cementación usual (CHD 0,8–1,2) no la da. Filas nuevas (sustituyen a las de la zapata: presión p = H/(l·t), revestimiento, largo y la
pendiente de la zapata plana sobre el canto curvo): Hertz de línea buje–canto en TODO el contorno real (61 posiciones del empuje con N = h(μ)·F_calado·η y el retorno guiado completo
con N = F_ret/sen φ(L)), radio local del canto (1/R_ef = 1/r + 1/R_c), largo de contacto t − 2 = 28 mm, p₀ ≤ 1,67·Fy del canto (750).
μ: la cinemática, la sincronía y el autobloqueo siguen con μ_A,d = 0,20 (inox–inox), mayor que el acero–acero engrasado, conservador en esas filas; las cargas del seguidor se evalúan
con 0,20 y con `bx_mu_ss` = 0,10 y cada fila toma la mayor (con 0,10 la H máxima sube 12,6 %: 80,7 → 90,9 kN; gobierna el pasador Q y el Hertz del empuje).

**Fila anómala** (plancha base bajo el soporte E, empuje a calado, FU 1,003 con 540 bar): el núcleo elige el espesor del refuerzo de esquina con su FU (objetivo ≤ 0,90) SIN el factor
1,158 de la envolvente de la FEA que aplica `baseCredit`; con menos presión el núcleo bajaba el refuerzo de 45 a 35 mm (FU núcleo 0,866) y la fila BX quedaba en 0,866 × 1,158 = 1,003.
Corrección: ganchos `k_base` (el núcleo elige con el mismo factor) y `td_min` = 45 (el factor se calibró con 45 mm; fuera de esa geometría no está validado). Resultado: 45 mm,
FU 0,764 (rev. 8: 0,962 a 680 bar; sin `td_min`, con solo `k_base`, quedaba 40 mm y 0,873).

Otros: con 540 bar el paso automático de los tapones de la lámina subía de 95 a 175 mm (232 → 133 tapones) y la separación mínima quedaba ∞ (FU 0: ningún par en la
malla de búsqueda; ahora se calcula la distancia exacta). Se fija `bx_s_tap` = 95 mm: se conserva el patrón de 232 tapones de las rev. 7–8 (INT-021 sin cambio de geometría),
más conservador (corte del aporte 0,432 → 0,343; arrastre local 0,572 → 0,454).
La curva de la placa-guía la elige el núcleo con las cargas (mín. de máx(H·F_calado, N_atasco)): con 540 bar cambia (tope del flanco 539 → 541 mm, hombro R79,1 → R75,4, cresta R221 → R286;
N_atasco 97,2 → 86,7 kN, H 74,6 → 80,7 kN): ACC-020/024 y el pasador Q pasan a la clase de geometría «BX-L9».

| Fila (FU) | Rev. 8 | Rev. 9 |
|---|---|---|
| FS del accionamiento en el caso de diseño | 0,895 | 0,987 (FS 1,267) |
| Alarma bajo el alivio / presión de diseño frente a la alarma | 0,980 / 0,812 | 0,988 / 0,888 |
| Pasador vertical E: flexión / corte | 0,756 / 0,449 | 0,961 / 0,714 |
| Pasador Q: flexión (horquilla) | 0,686 | 0,918 (μ 0,20) → **0,976** (μ 0,10, gobierna (a)) |
| Pasador Q: corte doble | 0,272 | 0,445 |
| Pasador Q: flexión / corte en el hombro del rebaje Ø70 (nuevas) | — | 0,679 / 0,520 |
| Buje–pasador Q: aplastamiento (lineal con excentricidad, nueva) | — | 0,836 |
| Tapas del cajón E: aplastamiento (pasador más blando) | 0,977 | 0,824 |
| Horquilla del bloque-uña en Q: aplastamiento | 0,168 | 0,338 |
| Ojal del vástago sobre el pasador Q: aplastamiento | 0,710 | 0,582 |
| Pasador de empuje: flexión / corte / aplastamiento en el anillo | 0,905 / 0,369 / 0,900 | 0,707 / 0,361 / 0,715 |
| Bloque-uña: Hertz conforme del asiento (sin temple) | 0,155 (templado) | 0,319 |
| Pivote: flexión / aplastamiento en el asiento / asiento con momento | 0,176 / 0,097 / 0,653 | 0,281 / 0,103 / 0,692 |
| Hertz buje–canto, empuje a calado (cresta cóncava R286, μ 0,10) | — | 0,970 |
| Hertz buje–canto, atasco del retorno (primer contacto, hombro R75,4) | — | 0,786 |
| **Hertz buje–canto, atasco del retorno en el flanco recto (envolvente)** | — | **1,145 — PENDIENTE** |
| Capa templada del buje (2·0,786·b ≤ 4 mm) | — | 0,464 |
| Plancha base bajo E, empuje a calado (BX) | 0,962 (45 mm) | 0,764 (45 mm; anómala sin corregir: 1,003 con 35) |
| Sellos: alivio / prueba frente a 680 / 850 | 1,000 / 1,000 | 0,794 / 0,794 (prueba 675 bar) |
| Camisa Lamé (servicio / prueba) | 0,983 / 0,911 | 0,781 / 0,723 |
| Vástago flexocompresión | 0,846 | 0,657 |
| Aceite atrapado tras el calado (20 / 80 °C, frente a 1,25·p_alivio) | 0,800 / 1,698 | 0,800 / 1,931 (informativa) |
| p_hold + Δp (20 / 80 °C) | 0,716 / 1,839 | 0,627 / 1,750 (a 80 °C: válvula de alivio térmico) |
| Pastillas: presión / con planitud / PV / pared | 0,834 / 0,949 / 0,884 / 0,861 | 0,720 / 0,835 / 0,763 / 0,743 |
| Portador: torsión / ligamento; costura exterior de la lámina | 0,612 / 0,523; 0,708 | 0,486 / 0,415; 0,612 |

**Decisión pendiente del mandante**: el contacto buje–canto en el atasco del retorno, en el flanco recto de reenganche (R = ∞, φ = 55,3°, N = 74,1 kN), da p₀ = 1434 MPa > 1,67·750
(FU 1,145) con el canto sin templar. La estimación a mano (R79 cóncavo, FU ≈ 0,85) corresponde al primer contacto (0,786 con la curva nueva); la envolvente encuentra el flanco.
Opciones: (a) temple por inducción del canto en el flanco y el hombro (Fy superficial ≥ 859 MPa); (b) placa-guía de 40 mm (FU ≈ 0,98); (c) p_ret ≤ 150 bar (FU ≈ 0,99).
Estado global: «NO CUMPLE / PENDIENTE DE DECISIÓN» (único pendiente crítico; giro y estructura cumplen). El Hertz del empuje (0,970) y el pasador Q (0,976) quedan en advertencia.

Planos (`python3 cad/generar_paquete_bx.py --out scratchpad/bx9/out`): ACC-046 nueva (buje: corte, vista inferior, tabla y notas); ACC-014 con el rebaje de Q y los materiales
S355J2+N; ACC-020/024 sin capa templada (detalle B del canto desnudo y nota del buje); MES-012 sin banda templada y con la soldabilidad del 42CrMo4; PIV-001 C45+N con la nota del
buje; ACC-027 asiento sin temple; GEN-005/006 (materiales y tratamientos) con los grados del mandante; GEN-008 y ACC-013 con la capacidad a 540 bar.

#### Revisión 9b (21-11-2026): presión de retorno limitada a 150 bar (opción C del mandante)

`p_ret` = 150 bar en `A36_DESPUES` (núcleo: 200), con una válvula reductora de presión y un alivio propio en la línea B del retorno, regulados y precintados
(fila «Circuito» de la tabla de capacidad en ACC-013/036 y GEN-008). Es el mayor valor redondo con el Hertz buje–canto del atasco ≤ 1: 150 bar → 0,990;
155 bar → 1,006; 200 bar → 1,145. Fuerza de retracción: 45,7 kN a 150 bar (antes 60,9 kN a 200 bar).

- La curva de la placa-guía la elige el núcleo con máx(H·F_calado, N_atasco): con 150 bar vuelve EXACTAMENTE a la curva de la rev. 8 (tope del flanco 539 mm,
  hombro R79,1, cresta R221,3; contorno idéntico al de ad59755). ACC-020/024 vuelven a su clase «BX-L»; solo el pasador Q queda en «BX-L9».
- Refuerzo de esquina: con 150 bar el núcleo pasaba a 50 mm sin atiesador (fuera de la geometría de la calibración de la FEA de la base). Gancho aditivo
  `rib_req`: con `k_base` se exige la configuración calibrada (45 mm + atiesador 22 × 60). Sin `P.__bx` el núcleo no cambia.
- **Destrabe y conducción del retorno a 150 bar** (fila nueva «BX · Retorno con p_ret 150 bar»): F_req = F_arranque de los sellos (A_anular·20 bar, conservador frente
  a los 5–10 bar de catálogo; ISO 10100) + μ·(m_bloque + m_cil)·g/η, con η = (cos φ − μ sen φ) − k_E(sen φ + μ cos φ) = 0,334 en el peor punto de la conducción
  (μ = 0,20, el mayor) → 6,73 kN ≤ 45,7 kN, FU 0,147. El bloque-uña se destraba girando libre en Q por la rampa del dorso (sin resorte): la fila geométrica
  «Garra: retorno sin traba» (0,428) y «Placa-guía sin autobloqueo» (0,037) no dependen de la presión. La mesa está detenida durante el retorno.
- FS del giro: 1,285 (curva de la rev. 8). Con ella el FS a 530 bar sería 1,261; el alivio se mantiene en 540 bar (decisión del mandante).
- Estado global: **CUMPLE** (sin pendientes críticos; FU máx. 0,990, el Hertz del atasco sobre el flanco).

| Fila (FU) | Rev. 9 | Rev. 9b |
|---|---|---|
| Hertz buje–canto, atasco del retorno (envolvente; flanco recto) | 1,145 (PENDIENTE) | 0,990 |
| Hertz buje–canto, atasco en el primer contacto (hombro) | 0,786 (R75,4) | 0,746 (R79,1) |
| Hertz buje–canto, empuje a calado (envolvente) | 0,970 | 0,956 |
| Pasador Q: flexión en la horquilla (μ 0,10) / (μ 0,20) | 0,976 / 0,918 | 0,931 / 0,885 |
| Pasador Q en el hombro: flexión / corte; aplastamiento buje–pasador | 0,679 / 0,520; 0,836 | 0,620 / 0,475; 0,764 |
| Capa templada del buje | 0,464 | 0,399 |
| FS del giro (FU) / gira contaminado / borde | 0,987 / 0,987 / 0,986 | 0,973 / 0,973 / 0,972 |
| Plancha base bajo E, atasco del retorno (BX) | 0,773 | 0,580 |
| Tapas del cajón E, desgarro hacia la nariz con el retorno | 0,474 | 0,355 |
| Atiesador tangencial: flexión | 0,416 | 0,383 |
| Tornillos de la placa-guía: corte | 0,625 | 0,569 |
| Retorno dentro de la presión nominal | 0,286 | 0,214 |
| Retorno con p_ret 150 bar: fuerza de retracción (nueva) | — | 0,147 |

### 13.7 Revisión 9c (21-11-2026): uniones soldadas (auditoría de 26 hallazgos)

Corrige las 26 observaciones de la auditoría de soldaduras de la rev. 9b. El núcleo TT300-C no cambia sin `P.__bx` (único cambio en `tt300c.js`:
gancho aditivo `juntasE_asiento`); el diámetro y el material del pasador de empuje no cambian (J-P1 sigue paramétrica en `d_pin`).

**Decisiones de la rev. 9c, por defecto, a confirmar por el mandante:**

1. **Códigos de lámina únicos.** Las hojas de continuación de las tablas ya no toman `num0 + n` (pisaban la lámina siguiente: GEN-007 h. 2 = GEN-008,
   GEN-005 h. 2 = GEN-006). Números propios: GEN-015/016 (GEN-007), GEN-017/024 (GEN-005), GEN-018 (GEN-006), GEN-019 (GEN-003), GEN-020 (GEN-009);
   GEN-014 lleva siempre (en BX) las notas y secuencias del programa de soldaduras, y las láminas de conjunto (CON-006, CON-007, BAS-001) remiten a GEN-014.
   El índice (GEN-001) lista las continuaciones; un control nuevo rechaza códigos repetidos.
2. **J17a / J17b (cubo–planchas).** No se necesita CJP: el núcleo no tenía fila de la unión y la nueva fila BX con la reacción del pivote a calado
   (H = 129,9 kN completa en cada plancha, q = H/(π·r)) pide garganta 3,3 mm. J17a: PJP en T con bisel simple 45° × 11 en la pared del cubo (27 mm junto al
   rebaje), E = 8 (= S − 3, AISC 360-22 Tabla J2.1; mínimo de la Tabla J2.3 por la parte más delgada de 22: 8) más filete de refuerzo z8, sin placa de apoyo,
   soldada desde arriba antes de cerrar: FU 0,408. J17b: el canto exterior del cubo queda dentro de la mesa cerrada; la unión pasa a un filete z10 todo
   alrededor en el agujero central Ø200 de la plancha superior, sobre la cara del cubo, hecho desde arriba con la mesa cerrada: FU 0,716 (z8 daba 0,896);
   holgura a la tapa retenedora Ø180: 3 mm. El buje se monta después de soldar y aliviar.
3. **J14 / J15.** Filetes solo a la plancha inferior y en los extremos de los nervios (longitudes a la mitad en las líneas de plancha); la plancha superior
   va solo por J18. Los extremos de los nervios del tramo 1 contra el cubo pasan a la junta J15b (precalentamiento por la pared de 80 del cubo).
   La fila del núcleo «Soldadura alma/nervio–plancha (2 filetes)» queda para la plancha inferior (anotada) y se agregan filas BX para la superior.
4. **J18 (AISC 360-22 §J2.3b) — CONFIRMADO por el mandante el 21-11-2026 (detalle A, ranura rellena; se descarta la variante de lengüetas pasantes del alma).** Soldadura de ranura rellena (no CJP): ancho 30 (≥ t + 8, ≤ 2,25·22), extremos semicirculares, largo 125 (≤ 10·22),
   relleno completo 22, separación entre centros ≥ 2L = 250 en cada línea; en el tramo 1 los nervios convergen y la ranura va en nervios alternados
   (separación transversal 141 ≥ 4·30). 77 ranuras, 9618 mm. Geometría derivada de `t_top` en `bx.mesa.soldaduras.ranuras`. Filas: corte en el área de
   la ranura en el plano de contacto (FU 0,294) y traspaso del flujo de corte al canto del alma de 8 mm (franja t × L; FU 0,893, el tramo 1 con la ranura
   cada 2 nervios); seis filas geométricas de §J2.3b. Respaldo permanente INCORPORADO en la rev. 9d (ver abajo): tiras 15 × 6 a ambos
   lados del canto del alma o nervio, punteadas antes de cerrar; la WPS exige probeta de calificación con macroataque de la raíz.
5. **Precalentamiento (AWS D1.1:2020 Tabla 5.8, Grupo II, cat. B, por la parte más gruesa)** en una sola función (`propuestas.pre_of`): J10 65 °C
   (refuerzo 45 bajo 2 orejas; 10 °C en las otras), J14/J15 10 °C (plancha 22), J15b, J17a y J17b 110 °C (cubo 80), J-E1/J-E2/J-E6 65 °C (refuerzo 45, no la
   cota 67). J37 y J38: 100 °C del procedimiento del cilindro (fuente única `bx.cilindro.fondo.cjp.precalentamiento_C`; la Tabla 5.8 pediría 10 y 65 °C).
   42CrMo4 de J-P1: Anexo B.
6. **WPS.** WPS-P16 con el material del JSON (42CrMo4+QT); WPS-P20 sobre fondo S355J2+N; nota 5 de GEN-012: solo se suelda el pasador de empuje
   bonificado (J-P1, Anexo B), el bloque-uña no se suelda, E, Q y el pivote no tienen tratamiento. J16 pasa a B-U2a (V 45°, R = 6, f = 0, respaldo
   permanente 6×40). Se elimina la combinación no precalificada «raíz 2 con respaldo» (J16, J17). Las J-E van como TC-U4b sin respaldo.
7. **J-E3/J-E4/J-E5: 152 por soporte** (304 en total; antes 197): gancho aditivo `P.__bx.juntasE_asiento` (alto real de las paredes sobre el refuerzo).
8. **Destijer de los nervios contra el cubo:** 20 × 20 en la esquina inferior del tramo 1 (≥ máx(19; cordón de J17a S + 3 y z + 3 más 5 mm); AISC 360-22
   §J1.6); 15 × 15 en las demás esquinas.
9. **Textos:** inox 309L de la lámina INT-021 (J30, J34–J36) en GEN-003 y GEN-012; «CJP al refuerzo» en las paredes del soporte E; TC-U4b; WPS-P21 de
   fricción sin parámetros de arco; columna FCAW «no aplica» en las WPS inoxidables y de J-P1; filete mínimo rotulado por la parte más delgada;
   §J2.2b solo donde hay borde (se quita la observación de J14 y la brecha de GEN-009); MES-012 (enrasado bajo la lámina) y ACC-029 (hombro a escuadra);
   JSON: `t_revestimiento` = 0 y «soldado a ambas planchas».
10. **Artículos:** donde no hay certeza del número exacto de AWS D1.1:2020 (tapones y ranuras, agujeros de acceso, B-U2a-GF) se escribe «verificar … en la
    edición vigente»; no se inventan números.
11. **Pasador de empuje (estudio FEA; Ø85 y 42CrMo4+QT sin cambio).** La fila del núcleo «Flexión (biapoyado entre anillos…)» usaba c = mín(dog_h, L) = 110,
    el alto de la uña del modo guiado; en el pivotado la carga del bloque-uña se reparte en su alto pv_hu = 140 (gancho aditivo `c_pv_hu`): FU 0,707 → 0,628.
    La fila informativa «Pasadores a ras del disco… soldados» decía «34CrNiMo6+QT con temple por inducción»: en BX lee el texto de la rev. 9 (gancho
    `pin_mat_txt`: 42CrMo4+QT de stock, sin temple por inducción). Sin `P.__bx` ambas filas del núcleo no cambian.

#### Revisión 9d (21-11-2026): respaldo permanente de las ranuras J18 (detalle A confirmado por el mandante)

- **Tiras de respaldo MES-015** (pieza nueva, permanente, S275JR / ASTM A36 de plancha de 6, plasma): dos por ranura, una a cada lado del canto superior del
  alma o nervio y a ras de él; sección 15 × 6 (cubre el vuelo de la ranura (30 − 8)/2 = 11 con 2 mm de apoyo); largo = L + 2 × 10 = 145 (rectas en los
  nervios de los tramos 2 y 3; en el tramo 1, 124, recortadas a 1 mm del cubo: el extremo interior de la ranura apoya 7 mm sobre la cara del cubo) y
  arcos de 145 mm (medidos en el eje del alma) en las almas (R281–296 / R304–319, R571–586 / R594–609, R821–836 / R844–859). 154 tiras, 15,6 kg (fuera del núcleo: < 0,01 % de la
  carga). Geometría paramétrica en `bx.mesa.soldaduras.ranuras.tiras` (del ancho y largo de la ranura y de t_alma); 8 geometrías → códigos MES-015-1…8.
- **Punteo J18r:** filete discontinuo z4 por debajo de cada tira contra el alma o nervio (3 tramos de 25 mm), con la mesa abierta, antes de montar la plancha
  superior (mín. 3 por la tira de 6, máx. t − 2 = 4). Sin precalentamiento (parte más gruesa 8). J18 pasa a «ranura rellena con respaldo permanente» (M) y su
  WPS exige probeta de calificación con la geometría real y macroataque de la raíz (AWS D1.1:2020 cláusula 6: verificar el artículo en la edición vigente).
- **Interferencias** (filas geométricas nuevas «BX · Tiras de respaldo J18 …» y control de interferencias del modelo 3D): las tiras de las almas cruzan los
  nervios por el destijer superior de 22 × 22 de sus extremos contra las almas (15 + 6 + 1 = 22; antes 15 × 15, ya sin filetes arriba desde la rev. 9c);
  el extremo superior del nervio contra el cubo queda sin destijer; los extremos de las ranuras de los nervios quedan fuera del destijer (a t_alma/2 + 1 + 22
  del eje del alma; tramos de 125 mm sin cambio de FU); las tiras de los nervios se recortan fuera de la zona de las tiras del alma; los filetes J14/J15 y
  los destijeres inferiores no cambian. Separación entre ranuras sin cambio (77 ranuras).
