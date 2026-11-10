# Registro de criterios normativos · TT300-C

| Ámbito | Criterio | Referencia | Justificación |
|---|---|---|---|
| Cadena de empuje (pasadores, uña, articulaciones, mejillas) | Tensiones admisibles Fy/Nd; corte Fy/(Nd·√3); aplastamiento 1,25Fy/Nd; soldaduras 0,60FEXX/(1,20Nd) | ASME BTH-1, Categoría de diseño B (Nd = 3,0, §3-1.3), §3-2 y §3-3; corte §3-2.3.6 | Decisión del usuario 30-10-2026. Se aplica por analogía (no es dispositivo bajo el gancho). Verificación a la fuerza de calado (área × presión de alivio). La flexión con Fy/Nd es más conservadora que BTH-1 §3-2.3.4 (1,25Fy/Nd para barras macizas redondas/cuadradas y secciones rectangulares macizas respecto del eje menor); ver «Verificación de citas (10-11-2026)» |
| Planchas de la mesa y de la base | σvm ≤ 0,6Fy (criterio del proyecto, más conservador que F11) | AISC 360-22 ASD; F11 da Mn = Mp = Fy·Z para barras rectangulares respecto de cualquier eje (≈ 1,5Fy·S), Ωb = 1,67, es decir ≈ 0,90Fy·S: no da 0,6Fy | Flexión local por FEA × k_malla 1,15 más membrana global axisimétrica |
| Plancha base bajo los soportes del cilindro (base de 20 mm con inserto de esquina) | σ_vM ≤ 1,25·Fy/Nd (Nd 3,0) a más de 100 mm de la huella rígida del soporte; mesa cargada hasta el calado y mesa vacía en servicio; atasco con la mesa vacía excluido (limitación de uso) | ASME BTH-1-2020 §3-2.3.4 (eje menor; ecuación: verificar); §3-2.3.6 corte | Decisión del mandante 10-11-2026; modelo calibrado con la FEA del verificador («Plancha base: base de 20 mm con inserto de esquina») |
| Corte en nervios | 0,6Fy·Aw·Cv1/Ω, Ω = 1,50 si h/t ≤ 2,24√(E/Fy) | AISC 360-22 G2.1(a), Ec. G2-1 | |
| Soldaduras de la mesa | 0,60FEXX/Ω, Ω = 2,00, sin aumento direccional | AISC 360-22 J2.4 | |
| Fluencia local de almas | q/t ≤ Fy/1,50 | AISC 360-22 J10.2 | Simplificación conservadora |
| Tamaño mínimo de filete | 3 / 5 / 6 / 8 mm según parte más gruesa (≤ 6 / ≤ 12 / ≤ 20 / > 20 mm) | AWS D1.1/D1.1M:2020 §7.13, Tabla 7.7 (en la edición 2020 la Tabla 5.8 es la de precalentamiento) | Usar la parte más gruesa es conservador: según la nota de la tabla (fuente secundaria, verificar texto), con procesos de bajo hidrógeno T es la parte más delgada |
| Fatiga | N ≤ 20 000: clase de servicio 0, sin verificación; si no, F_SR = 6,895·(Cf/N)^(1/3) ≥ F_TH (Cat. F: exponente 1/6) | ASME BTH-1 §3-4; AISC 360-22 Apéndice 3, Ec. A-3-1, Tabla A-3.1 | Cf de la tabla en ksi, convertido a MPa |
| Pandeo del vástago | F_calado ≤ Pcr/3, Euler biarticulado con longitud extendida y diámetro del vástago | Criterio conservador frente a ISO/TS 13725 | Confirmar con ficha del cilindro |
| Giro | FS = F_calado/F_diseño ≥ 1,25; p_diseño ≤ alarma; gira con μ contaminado y con contacto en el borde | Criterio del proyecto | Revisión independiente M1 |
| Presión nominal del cilindro | p_alivio ≤ p_nominal (10.000 psi ≙ 700 bar; 5.000 psi ≙ 350 bar, convención de catálogo); p_alarma ≤ 0,90·p_alivio; p_retorno ≤ p_nominal | ISO 4413:2010 (protección contra sobrepresión) y catálogo del fabricante | Confirmado por el revisor del proyecto (02-11-2026) |
| Interfaz con discos de acero inoxidable (opción A) | Disco como placa circular empotrada sobre un vacío local con carga uniforme: σ = 3qa²/(4t²) ≤ 0,6Fy; t_req = t_flex + sobreespesor (≥ mínimo constructivo); espesor comercial. Dilatación diferencial y retención por fricción | Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy (criterio del proyecto, más conservador que AISC 360-22 F11; ver fila 2); Fy según ASTM A240 | Pedido del mandante 04-11-2026. Ø de vacío, sobreespesor y μ son hipótesis de diseño; confirmar numeración en la edición vigente de Timoshenko |
| Interfaz con discos inoxidables y lámina UHMW (opción B) | Lámina: t ≥ E_ap·δ/(p_adm − q_máx), p_adm sostenida; PV, desgaste e juntas de dilatación | Datos de catálogo del proveedor de UHMW-PE (ASTM D4020) | Valores de partida: p_adm 5 MPa, E_ap 300 MPa, PV 0,05 MPa·m/s, μ 0,08 a 0,20; confirmar con ensayo del proveedor |
| Interfaz con placa de bronce con tapones de grafito (opción C) | Placa empotrada sobre un vacío local con ligamento entre tapones: σ = 3qa²/(4t²η) ≤ 0,6Fy_bz, η = (p − d)/p; presión sobre el bronce neto, PV, desgaste y profundidad del tapón; pareja con disco duro (ΔHB ≥ 100); retención por pegado; dilatación diferencial | Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy (criterio del proyecto, más conservador que AISC 360-22 F11; ver fila 2); Fy según ASTM B584 / B148; PV y desgaste de catálogo del proveedor | Pedido del mandante 05-11-2026. Valores de partida: C95400 (Fy 170 MPa), p_adm 20 MPa, PV 0,5 MPa·m/s, k 10⁻⁶ mm³/N·m, μ 0,08 a 0,20; confirmar con el proveedor y con ensayo |
| Sismo | No aplica (Ch = 0) | NCh2369 | Decisión del usuario 01-11-2026; para instalación permanente verificar con Ch |

## Temperatura (exposición solar, 80 °C)

Pedido del mandante 06-11-2026: verificar el cuerpo a 80 °C uniformes frente a 20 °C de referencia (ΔT = 60 K). Todo lo de esta sección es **propuesta del revisor, pendiente de decisión del mandante**; ningún valor se ha incorporado aún a `packages/core/tt300c.js`. Cuando se incorpore, cada verificación debe declarar `formula` y `ref` con la fuente de las tablas de abajo.

**Cómo se obtuvieron los datos.** Búsqueda web (sin acceso al texto de pago de AISC 360-22, ASME BTH-1, ASME II-D, EN 10088, ISO 898-1, ISO 4413, NCh1198). Lo que no pude leer en el documento original queda marcado.

**Escala de confianza:**

| Nivel | Significado |
|---|---|
| A | Transcripción de tabla/artículo contrastada con copia del editor de la norma o con dos copias independientes |
| B | Ficha técnica de fabricante, o valor coherente entre dos fuentes secundarias, o valor de memoria del revisor consistente con una verificación interna (p. ej. ecuación que da cero a 20 °C). Conviene confirmarlo contra el original |
| C | Fuente única secundaria (foro, vendedor, artículo divulgativo), valor de memoria sin contraste, o criterio de ingeniería / orden de magnitud sin fuente |

### Criterios propuestos

| Ámbito | Criterio | Referencia | Justificación |
|---|---|---|---|
| Acero estructural y cadena de empuje a 80 °C | Fy y E sin reducción (k = 1,00). Análisis de sensibilidad con k_Fy = 0,92 (criterio ASME II-D Tabla Y-1) hasta confirmar el valor | AISC 360-22 Apéndice 4, Tabla A-4.2.1 (el 80 °C = 176 °F queda en la zona de k = 1,00); EN 1993-1-2 Tabla 3.1 (k_y,θ = k_E,θ = 1,00 a 100 °C); ASME II-D Tabla Y-1 (por confirmar) | El Apéndice 4 es de exposición al fuego, no de servicio sostenido; sirve de cota, no de norma de servicio. La reducción a 80 °C es nula en AISC/EC3 y de ~8 % en la lectura de memoria de Y-1 |
| Alcance térmico de BTH-1 | 80 °C (176 °F) excede el rango estándar de BTH-1 (25 °F a 150 °F, es decir -4 °C a 66 °C). Requiere decisión de persona calificada y registro de la hipótesis | ASME BTH-1, sección por confirmar; resumen en Hoist Magazine y Tandemloc (secundarias) | Nd = 3,0 no incluye un margen térmico explícito. Si el mandante mantiene 80 °C, se aplica la sensibilidad k_Fy = 0,92 a la cadena de empuje |
| Dilatación libre | ε = α·ΔT con α = 12×10⁻⁶ /K (EN 1993-1-1 §3.2.6) o 11,7×10⁻⁶ /K (uso AISC); para acero ΔT = 60 K da 0,70 a 0,74 mm/m. Una dilatación libre no genera tensión; la restricción sí (σ = E·α·ΔT = 140 MPa uniaxial totalmente restringido) | EN 1993-1-1 §3.2.6; EN 1993-1-2 §3.4.1.1 | Verificar holguras de pasadores, guías y juntas, no resistencia, salvo que haya restricción |
| Gradiente entre plancha superior e inferior | Plancha superior al sol, inferior a la sombra: ΔT_g de 15 a 20 K como hipótesis. Curvatura κ = α·ΔT_g/h, con h = 230 mm | EN 1991-1-5 §6.1.4.1, Tabla 6.1 (acero tipo 1: ΔT_M,heat = 18 K, solo para tableros de puentes) | Cifra de otra tipología: orden de magnitud. Para ΔT_g = 18 K, κ = 9,2×10⁻⁴ /m y una flecha de 1 mm en una plancha libre de Ø3 m |
| Interfaz UHMW-PE (opción B) | **No admitir** UHMW-PE cargada a 80 °C hasta tener la curva del proveedor: 80 °C es el límite de servicio continuo de la ficha y coincide con el Vicat B50. Si se mantiene la opción B, p_adm y E_ap se reducen con el factor del proveedor | Fichas Quadrant/Mitsubishi TIVAR 1000, Ensinger TECAFINE PE1000, Röchling Polystone M (ver tabla); GUR 4120 Celanese | La ficha da 80 °C de servicio continuo (20 000 h) y HDT de 42 °C a 1,8 MPa. No hay curva de módulo ni de límite elástico a 80 °C publicada en las fichas que alcancé |
| Interfaz de bronce con grafito (opción C) | Sin reducción apreciable de resistencia a 80 °C en el bronce (criterio de ingeniería). La profundidad del tapón y la dilatación diferencial dominan | Bunting C93200 (Tmax 500 °F); proveedores de bronce grafitado (300 a 371 °C) | El registro de opción C usa C95400; la ficha de temperatura que alcancé es de C93200. Confirmar C95400 con el proveedor |
| Aceite atrapado por expansión térmica | Δp = (α_v − 3α_s)·ΔT / (1/K_aceite + 1/K_c). Si el aceite puede quedar entre una válvula de retención/bloqueo y un tope mecánico, prever válvula de alivio térmico | ISO 4413:2010 (reemplaza a EN 982), cláusula por confirmar; artículos técnicos de Power & Motion y AIChE/CCPS (secundarias) | Orden de magnitud para ΔT = 60 K: 600 a 1 000 bar en circuito rígido, 100 a 150 bar con mangueras largas (cálculo de abajo) |
| Madera dura | Aplicar Ct de NDS Tabla 2.3.3 como cota (Fc⊥: 0,70 seca / 0,50 húmeda a 125–150 °F). 80 °C queda **fuera** de la tabla | NDS 2018 Tabla 2.3.3 (copia AWC, Capítulo 2); NCh1198 sin confirmar | No hay factor tabulado sobre 150 °F (65,6 °C). Usar la cota o ensayo |

### Valores por material

| Material | Propiedad | Valor a 20 °C | Valor a 80 °C | Factor 80/20 | Fuente y artículo | Conf. |
|---|---|---|---|---|---|---|
| Acero A36 | Fy | 250 MPa (36 ksi) | 250 MPa | 1,00 | AISC 360-22 App. 4, Tabla A-4.2.1; EN 1993-1-2 Tabla 3.1 | B |
| Acero A572 Gr50 | Fy | 345 MPa (50 ksi) | 345 MPa | 1,00 | Ídem | B |
| Acero A514 | Fy (t ≤ 65 mm) | 690 MPa (100 ksi) | 690 MPa | 1,00 | Ídem | B |
| Acero estructural | E | 200 000 MPa | 200 000 MPa | 1,00 | Ídem, k_E,θ | B |
| Acero al carbono (contraste) | Fy según ASME II-D Y-1 | 100 % | ~92 a 93 % | ~0,92 | ASME II-D Tabla Y-1, de memoria del revisor; no leída | C |
| Acero estructural | Alcance de AISC 360 App. 4 | n/a | Solo fuego (exposición temporal) | n/a | Modern Steel Construction, respuesta de quiz AISC (secundaria) | C |
| Acero estructural | Servicio sostenido: fluencia lenta (creep), grafitización, etc. | n/a | Solo relevante sobre ~700 a 750 °F (370 a 400 °C) | n/a | Modern Steel Construction (secundaria) | C |
| Acero estructural | Rango de servicio estándar BTH-1 | -4 a 66 °C (25 a 150 °F) | **Fuera de rango** (176 °F) | n/a | ASME BTH-1, §por confirmar; Hoist Magazine; Tandemloc | C |
| Acero estructural | α | 11,7×10⁻⁶ /K (AISC, uso) o 12×10⁻⁶ /K (EN 1993-1-1 §3.2.6) | Media 20 a 80 °C: 12,4×10⁻⁶ /K con EN 1993-1-2 §3.4.1.1 (Δl/l = 1,2×10⁻⁵θ + 0,4×10⁻⁸θ² − 2,416×10⁻⁴ = 7,44×10⁻⁴) | ε = 0,70 a 0,74 mm/m | AmesWeb (11,7); EN 1993-1-1 §3.2.6 y EN 1993-1-2 §3.4.1.1 de memoria. La ecuación da 0 a 20 °C | B |
| Inox 304 / 316 | Fy (ASTM A240) | 205 MPa (30 ksi) | ~165 a 175 MPa | 0,80 a 0,85 | EN 10088-2 / EN 10028-7: Rp0,2 mín. 1.4301 = 157 MPa y 1.4401 = 166 MPa a 100 °C (de memoria; no encontrado en la web); interpolación lineal 20→100 °C desde 210 MPa (plancha laminada en caliente, 1.4301). Cruce con ASME II-D Y-1 (~25 ksi a 200 °F, de memoria) | C |
| Inox 304 / 316 | E | 200 000 MPa | ~195 000 MPa | 0,975 | EN 10088-1: 194 GPa a 100 °C para 1.4301 (ficha matmatch, secundaria) | B |
| Inox 304 / 316 | α | 16,0 a 17,2×10⁻⁶ /K | Igual | 1,0 | EN 10088-1 (20–100 °C: 16,0, ficha lucefin); AmesWeb (304: 17,2; 316: 15,9) | B |
| UHMW-PE (TIVAR 1000) | Tensión de compresión a 1 % / 2 % / 5 % de deformación | 6,5 / 10,5 / ~17 MPa (ISO 604) | **Sin dato publicado** | Sin dato | Quadrant (Mitsubishi) TIVAR 1000, ficha en "colors" | B |
| UHMW-PE | Compresión 10 % (ASTM D695) | 20,7 MPa | **Sin dato** | Sin dato | Polymershapes / Mitsubishi TIVAR 1000 | B |
| UHMW-PE | Módulo de compresión (genérico) | 551 MPa (ASTM D695, otro compuesto) | **Sin dato** | Sin dato | CDI Products, ficha 748 | C |
| UHMW-PE | Módulo de tracción | 650 a 700 MPa | **Sin dato** | Sin dato | Ensinger PE1000 (680 a 700), Röchling Polystone M (> 650) | B |
| UHMW-PE | Temperatura de servicio continuo | 80 °C (20 000 h en aire); corto plazo 100 a 130 °C | Igual: **es el límite** | n/a | Quadrant TIVAR 1000; Ensinger PE1000; Röchling Polystone M (-250 a +80 °C) | B |
| UHMW-PE | Ablandamiento | HDT 42 °C a 1,8 MPa; 65 °C a 0,45 MPa; Vicat B50 = 80 °C | Ídem | n/a | Celanese GUR 4120 (listado Prospector); Polystone M EL negro: Vicat B 79 °C | B |
| UHMW-PE | Creep (tracción, 23 °C) | Módulo de fluencia 550 MPa a 1 h, 300 MPa a 1 000 h | **Sin dato** | 0,55 entre 1 h y 1 000 h a 23 °C | Lupolen UHM 5000 (Lyondell/Basell), ficha | B |
| UHMW-PE | Equivalencia tiempo-temperatura de creep | 23 °C con 4 MPa | ≈ 38 °C con 2,5 MPa (misma curva) | +15 K equivale a tensión × 0,63 | NIST IR 84-2808 (según resumen de búsqueda) | B |
| UHMW-PE | Reducción de capacidad a 80 °C | 1,00 | **No hay fuente**. Criterio de ingeniería: fluencia (yield) y módulo bajan a menos de la mitad; supongo factores 0,3 a 0,5 | ~0,3 a 0,5 | Ninguna; estimación del revisor. Exigir la curva al proveedor | C |
| UHMW-PE | α | 1,8×10⁻⁴ /K (23 a 60 °C, ISO 11359); 2×10⁻⁴ /K (GUR 4120) | ≥ 2×10⁻⁴ /K (crece con T) | ε = 1,08 a 1,2 % | Ensinger PE1000 (ISO 11359-1/2); Celanese GUR 4120 | B |
| UHMW-PE | PV límite (manguito, seco) | 0,08 (0,1 m/s) / 0,05 (1 m/s) MPa·m/s | Se anula cuando T_ambiente = T_límite | Ver nota | Quadrant TIVAR 1000, "Limiting PV". Fórmula de balance térmico: PV_adm(T) ≈ PV_adm(20 °C)·(80 − T)/(80 − 20) (criterio del revisor) | B / C |
| UHMW-PE | Desgaste | Coeficiente k de ficha | Aumenta con T; sin dato | Sin dato | No encontrado | C |
| Bronce SAE 660 / C93200 | Fy mín. (colada continua / centrífuga) | 138 MPa (20 ksi) / 97 MPa (14 ksi) | Sin reducción apreciable | ~1,0 (criterio) | Bunting, ficha C93200 (valores "no para especificación") | B / C |
| C93200 | Resistencia a compresión ("crushing") | 320 MPa | Ídem | ~1,0 (criterio) | MakeItFrom (secundaria); no es valor de diseño | C |
| C93200 | Temperatura máxima de servicio | 260 °C (500 °F) | Dentro del rango | n/a | Bunting, ficha C93200 | B |
| C93200 / C95400 | α | C93200: ~18×10⁻⁶ /K; C95400: ~16×10⁻⁶ /K | Igual | 1,0 | CDA, de memoria; no encontrado | C |
| Bronce grafitado (proveedores) | Temperatura máxima | -50 a 371 °C (700 °F), 300 °C | Dentro del rango | n/a | McMaster-Carr bronce 841; SVB Bearings (listado de vendedor) | C |
| Grasa NLGI 2 con MoS₂/grafito | Punto de goteo | 175 a 265 °C según producto (ASTM D2265): Mobilux EP 2 Moly 175; Mo-Lith 177; SKF LGEM 2 179; LUBREX RED 2 245 mín.; Pro Tac Plus 265 | Muy por debajo del punto de goteo (≥ 95 K de margen) | n/a | Fichas de cada producto | B |
| Grasa NLGI 2 | Rango de operación | Mo-Lith -23 a 127 °C; LGEM 2: -51 a 110 °C; EPLX-M 2: -30 a 175 °C | Dentro | n/a | Fichas de Lubriplate, SKF, Castrol | B |
| Grasa NLGI 2 | Viscosidad del aceite base y μ | Sin dato por producto | Disminuye mucho; la exudación crece. μ de película sólida: sin fuente | Sin dato | No encontrado. Criterio: μ de diseño 0,08 a 0,20 (registro) | C |
| Aceite ISO VG 46 | ν a 40 °C / 100 °C / IV | 46 mm²/s (41,4 a 50,6) / 6,8 / ~100 | ν a 80 °C ≈ 11 mm²/s (IV 100); ≈ 14,6 (IV 185) | ν ÷ 4,2 (IV 100) | ISO 3448 (grado); Eurol Hykrol EXL 46 (47,4 / 9,5 / 185); cálculo Walther, ASTM D341, del revisor | B / C |
| Aceite ISO VG 68 | ν a 40 °C / 100 °C / IV | 68 mm²/s (61,2 a 74,8) / 8,7 / 98 a 104 | ν a 80 °C ≈ 14,5 a 15 mm²/s | ν ÷ 4,6 | Eurol ISO VG 68 (65,8 / 8,7 / 104); cálculo Walther del revisor | B / C |
| Aceite mineral | Coeficiente de expansión volumétrica α_v | 7,0 a 7,5×10⁻⁴ /K | Igual (crece levemente con T) | 1,0 | Power & Motion (0,0007 /°C); industrialmonitordirect (7 a 8×10⁻⁴; la fuente dice "/°F", casi seguro error) | C |
| Aceite mineral HM 46 | Módulo volumétrico adiabático a 1 bar | 19 262 bar (1,93 GPa) | 14 319 bar (1,43 GPa) | 0,74 | Annals of the Faculty of Engineering Hunedoara 2016, vol. 1, tabla de módulo adiabático | B |
| Aceite mineral | Módulo volumétrico K a 700 bar, 80 °C | Sin dato | **Estimado 1,4 a 2,3 GPa** (tomo 1,9 GPa) | Sin dato | Sin fuente; la presión sube K, la temperatura lo baja; el adiabático es mayor que el isotérmico | C |
| Aceite + manguera | K combinado | Sin dato | ~327 MPa (47 500 psi) | Sin dato | Fuente técnica de aceite y manguera (resumen de búsqueda) | C |
| Sellos NBR | Servicio continuo | -30/-40 a 80/120 °C según fuente | 80 °C **en el límite bajo** de algunas fuentes | n/a | Ulman (-30 a +80); Machine Design (90 °C usual, 100 °C con compuestos selectos); Power & Motion (-40 a 120) | C |
| Sellos PU | Servicio continuo | Sin fuente de fabricante hallada | Criterio: 80 a 100 °C | n/a | Parker Prädifa N0 (-35 a 100 °C) es un juego de pistón, no un compuesto PU | C |
| Sellos FKM | Servicio continuo | -20 a 200/240 °C | Dentro | n/a | Ulman (-20 a +200); Power & Motion | C |
| Madera dura | Ct para Fc⊥ (T ≤ 100 °F / 100 a 125 °F / 125 a 150 °F) | 1,0 / 0,8 seca – 0,7 húmeda / 0,7 seca – 0,5 húmeda | 80 °C = 176 °F: **fuera de la tabla**. Cota: 0,70 seca, 0,50 húmeda | ≤ 0,70 / ≤ 0,50 | NDS 2018 Tabla 2.3.3, copia AWC, Capítulo 2 | A (tabla) / C (extrapolación) |
| Madera dura | Ct para Ft, E, Emin | 1,0 | Tabla: 0,9 hasta 150 °F | ~0,9 | NDS 2018 Tabla 2.3.3 | A |
| Madera dura | NCh1198 factor KT | Sin dato | Sin dato | Sin dato | No encontrado | C |
| Madera dura | Humedad por secado | Contenido de humedad de equilibrio | Baja al sol; sube la resistencia, aparecen grietas | Sin dato | Criterio de ingeniería | C |
| Soldadura E70XX | Fexx | 483 MPa (70 ksi) | Sin reducción | 1,00 | AWS D1.1 no da criterio térmico de servicio (foro AWS, secundaria); criterio del revisor | C |
| Pernos A325 / A490 | Resistencia | Nominal | Sin reducción apreciable; la reducción gradual comienza sobre 300 °C | ~1,0 | AISC Engineering Journal, ensayos de corte a alta temperatura (secundaria) | B |
| Pernos ISO 898-1 clase 10.9 | Rp0,2 a temperatura elevada | 940 MPa (nominal) | Norma: tabla informativa de temperatura elevada, valor a 100 °C no leído. De memoria: ~5 a 7 % menos | ~0,93 a 0,95 | ISO 898-1, anexo informativo sobre temperatura elevada (nº por confirmar) | C |
| Pintura de acero oscuro | Temperatura superficial al sol | Ambiente | Medidas: 58 a 70 °C. 80 °C = cota alta | n/a | Estudio Phoenix (137 a 140 °F); medida con pistola infrarroja 69,5 °C; resumen de ScienceInsights (secundarias) | C |
| Caja ~230 mm | Gradiente entre planchas | 0 K | 15 a 20 K (hipótesis) | n/a | EN 1991-1-5 Tabla 6.1, tipo 1 (18 K, calefacción), otra tipología | C |

### Cálculos del revisor

**Movimientos térmicos por metro para ΔT = 60 K** (α en 10⁻⁶ /K): acero 11,7 a 12 da 0,70 a 0,72 mm/m; inox 16,0 a 17,2 da 0,96 a 1,03 mm/m; bronce C93200 18 da 1,08 mm/m; UHMW-PE 180 a 200 da 10,8 a 12 mm/m; madera dura perpendicular a la fibra ~40 (valor de memoria, sin fuente) da ~2,4 mm/m. La diferencia UHMW-PE contra acero es de ~10 mm/m: obliga a juntas de dilatación y a retención por geometría, no solo por fricción.

**Viscosidad a 80 °C** (Walther, ASTM D341: log log(ν + 0,7) = A − B·log T, con 40 °C y 100 °C como puntos): VG 46 con ν₁₀₀ = 6,8 da B = 3,68 y ν₈₀ ≈ 11,1 mm²/s; VG 46 con IV 185 (Eurol: 47,4 y 9,5) da ≈ 14,6 mm²/s; VG 68 (65,8 y 8,7) da ≈ 14,6 mm²/s. El cálculo supone que los datos de 40 y 100 °C se cumplen en 80 °C; el error típico es de décimas de mm²/s. Un valor de 11 mm²/s es cercano al mínimo que suelen pedir los fabricantes de bombas (~10 mm²/s, cifra de memoria sin fuente).

**Presión por aceite atrapado.** Con volumen V₀ sellado entre una válvula de retención o bloqueo y un tope:

Δp = (α_v − 3α_s)·ΔT / (1/K_aceite + 1/K_c)

con α_v = 7,5×10⁻⁴ /K, 3α_s = 3,5×10⁻⁵ /K (volumétrico del acero), K_c la rigidez volumétrica del contenedor (pared del cilindro, tuberías, mangueras, aire libre). Para ΔT = 60 K:

| Caso | K efectivo | Δp | Observación |
|---|---|---|---|
| Aceite en recipiente rígido | K_aceite = 1,4 a 2,3 GPa | 60 a 99 MPa = 600 a 990 bar (con 1,9 GPa: 815 bar, o 13,6 bar/K) | Cota alta. Coincide con ">10 bar/°C" de Power & Motion |
| Cilindro Ø90 con tubo de pared b/a = 1,4 (Lamé, hipótesis del revisor) | K_c ≈ 30 GPa; K_efectivo ≈ 1,79 GPa | ≈ 770 bar | La pared del cilindro casi no alivia (-6 %). El espesor real es dato por confirmar |
| Línea toda de manguera | K ≈ 0,33 GPa | ≈ 140 bar | Cota baja. El aceite expandido absorbe el cambio en la manguera |
| 1 % de aire libre a 700 bar | aporta x/p ≈ 1,4×10⁻⁴ /MPa frente a 5,3×10⁻⁴ /MPa del aceite | ≈ -20 % | Aire disuelto o atrapado reduce la presión, pero no es un control |

Dilatación libre del aceite: 4,29 % (7,15×10⁻⁴ × 60). Para un cilindro Ø90 (A = 63,6 cm²), una columna de 1 m de aceite se expande 43 mm; 100 mm de columna, 4,3 mm.

**Si el pistón puede moverse bajo una carga muerta**, la presión se mantiene en W/A y la expansión se traduce en carrera. La sobrepresión aparece solo cuando el movimiento está restringido (tope mecánico, fin de carrera, bloqueo cinemático, calado). Eso incluye el caso de calado de la cadena de empuje: el 80 °C no cambia la fuerza de calado nominal (A × p_alivio), pero la sobrepresión térmica puede superar p_alivio si el alivio del sistema está aguas arriba de la válvula de retención. Un alivio de sistema no protege un tramo aislado.

**Práctica normativa.** EN 982 fue reemplazada por EN ISO 4413:2010 (confirmado el 10-11-2026 en las fichas de SIS, DIN y BSI: EN ISO 4413:2010 reemplaza a EN 982:1996+A1:2008; A). Que el diseño prevea válvula de alivio térmico en un tramo que puede quedar aislado y calentarse es práctica habitual (Power & Motion, AIChE/CCPS), pero **no pude confirmar la cláusula de ISO 4413** ni de ninguna otra norma que lo exija. La prueba de presión de cilindros ISO 10100 es 1,5 × p_nominal (de memoria; no confirmado).

**Flexión por gradiente.** κ = α·ΔT_g/h; flecha de plancha circular libre de diámetro D: s = κ·(D/2)²/2. Con ΔT_g = 18 K, h = 230 mm y D = 3 m: s ≈ 1 mm. Plancha totalmente restringida: σ = E·α·ΔT_g/(2(1 − ν)) ≈ 30 MPa (solución clásica, Timoshenko; el valor depende de la restricción real de la caja, no de la plancha aislada).

**Temperatura superficial estimada** por balance: T_s = T_a + α_s·G/h_total, con α_s ≈ 0,9, G ≈ 1 000 W/m², h_total ≈ 15 a 30 W/m²K. En aire quieto el aumento llega a 55 a 60 K; con viento de 5 m/s, a unos 30 K. Con T_a de 35 °C resultan 90 a 95 °C en aire quieto y unos 65 °C con viento de 5 m/s. 80 °C es plausible en la plancha superior horizontal en día muy caluroso y sin viento. Criterio del revisor (C).

### No pude confirmar con fuente primaria

| Pendiente | Dónde buscar |
|---|---|
| Texto de la Tabla A-4.2.1 y numeración en AISC 360-22; alcance del Apéndice 4 | AISC 360-22 original |
| Sección de BTH-1 sobre temperatura de servicio (25 a 150 °F) y qué exige fuera de ese rango | ASME BTH-1-2023 original |
| ASME II-D Tabla Y-1 (A36/SA-36 a 200 °F) y Tabla TM-1 / TE-1 (E y α del inox) | ASME II-D original |
| Rp0,2 a 100 °C de 1.4301 y 1.4401 (157 y 166 MPa de memoria); hay una discrepancia con una página de EN 10269 que da 177 y 187 MPa para 1.4301 y 1.4404 | EN 10088-2, EN 10028-7 o Euro Inox Design Manual |
| Curva de módulo y de tensión de fluencia (yield) del UHMW-PE contra T entre 20 y 80 °C; creep a 80 °C; desgaste a T | Pedir a Quadrant/Mitsubishi, Ensinger, Röchling y Celanese la curva de su grado |
| Definición exacta de "servicio continuo 20 000 h" (de memoria: pérdida del 50 % de la resistencia a tracción por envejecimiento; no es capacidad bajo carga) | Pie de página de la ficha Quadrant |
| Temperatura de servicio y carga de bronce grafitado C95400 (el registro de opción C usa C95400, la información hallada es de C93200 y de vendedores) | Ficha del proveedor del bronce |
| Viscosidad y μ de la grasa con grafito/MoS₂ a 80 °C; punto de goteo del producto elegido | Ficha del proveedor |
| Módulo volumétrico isotérmico del aceite a 700 bar y 80 °C | Ficha del fabricante del aceite o tabla de laboratorio |
| Límite de PU continuo en sellos hidráulicos | Catálogo Parker/Trelleborg/Hallite del sello elegido |
| Cláusula de ISO 4413:2010 sobre alivio térmico | ISO 4413 original |
| NCh1198 (factor de temperatura KT o equivalente) y su nota de humedad | NCh1198 original (INN) |
| NDS 2018 §2.3.3: texto sobre exposición sostenida frente a intermitente | NDS 2018 original |
| ISO 898-1: tabla de Rp0,2 a 100 °C para clase 10.9 | ISO 898-1 original |
| AWS D1.1:2020: ausencia de criterio térmico de servicio | AWS D1.1 original y su comentario |
| Gradiente térmico de una caja de ~230 mm al sol (la cifra de 18 K es de puentes) | Medición o análisis térmico propio |
| Coeficientes α del bronce y de la madera | CDA y Wood Handbook (FPL) |

**Puntos a confirmar:** numeración exacta de ecuaciones de BTH-1 en la edición vigente (las cláusulas se revisaron el 10-11-2026: ver «Verificación de citas (10-11-2026)»); la tabla de filete mínimo de AWS D1.1:2020 es la Tabla 7.7 (§7.13); todo lo enumerado en «No pude confirmar con fuente primaria» (sección Temperatura).

## Uña de empuje: material y excepción del criterio FU ≤ 0,90

| Ítem | Valor | Referencia | Decisión |
|---|---|---|---|
| Material | 34CrNiMo6+QT, Re ≥ 800 MPa para 40 < t ≤ 100 mm (bloque 198 × 88 × 110, t gobernante 88 mm) | EN 10083-3, tabla de propiedades +QT | Corrige el Fy = 900 MPa anterior, que ese acero no alcanza con 88 mm |
| Flexión en la boca del patín | FU 0,907 (antes 0,807 con 900 MPa) | ASME BTH-1 Cat. B, Nd = 3,0, §3-2.3 | Aceptada por el mandante el 07-11-2026 como advertencia (FU ≤ 1,0). El criterio interno FU ≤ 0,90 se relaja solo para esta fila |
| Otras filas de la uña | Corte en la boca 0,448; corte en el contacto 0,801; flexión en el chaflán 0,627 | BTH-1 §3-2.3.6 (corte) y §3-2.3 (flexión) | Cumplen ≤ 0,90 |


## Leva de reenganche positiva (modo guiado)

Pedido del mandante 07-11-2026 (Tarea 1). El riel-leva fijo reemplaza la dependencia exclusiva del resorte; el resorte queda como apoyo. Hipótesis de geometría (no hay espacio lateral junto al patín: el patín ocupa x = x_g ± w_s/2 entre la mesa y el marco): el seguidor es un rodillo sobre un perno vertical fijo en la uña, que sale por una ranura de la tapa del alojamiento (la ranura lo guía en y); el riel es una pletina horizontal sobre el patín (entre la cara superior del patín + 2 mm y la cara superior de la mesa), apoyada en dos soportes empernados a la bancada prolongada en cada extremo, por fuera del recorrido del patín y por fuera del cuerpo del cilindro. Una pletina por cilindro: se voltea para el otro sentido de giro.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Sincronía | holgura uña–pasador siguiente B con la uña apoyada en la rampa ≥ margen (cam_msync) | Geometría | Polígono de la uña (punta, chaflán β, cara trasera) frente al círculo de B; rampa a α desde η₀ + tramo, η₀ = −r − s_libre. Con s_libre = 10 mm no cabe la rampa (holgura < 0): s_libre pasa a 21 mm (carrera requerida 229,3 + 5 ≤ 235) |
| Bolsillo | máx u_nec ≤ recorrido de retorno Δx | Geometría | El bolsillo coincide con la zona de toma del pasador siguiente (B pasa a ser A): una leva posicional no distingue el sentido, de modo que en esa parte del empuje la uña queda con el resorte y el roce del alojamiento, como antes |
| Autobloqueo de la rampa | μ_ret·k_t·(sen α + μ_seg·cos α) < (cos α − μ_seg·sen α)·(1 − 2μ_ret·z_f/L_in) | Equilibrio de la cuña con fricción | k_t = 1 + 2(z_f − z_ranura)/h_uña (torsión de la uña por la fuerza del seguidor sobre la tapa); μ_seg = mu_roll (rodillo, familia 1) o el μ de la familia 2–4 |
| Fuerzas de atasco | cilindro tirando a p_ret con la uña trabada; cotas sin roce | Hidráulica | N_rampa = F_ret/sen α; N_toma = F_ret/tan β (chaflán sobre B a nivel de toma); F_ret = A_anular·p_ret |
| Contacto del rodillo | p₀ = √(q·E*/(π·r)) ≤ 1,67·Fy_sup, q = N/b | Hertz, contacto lineal; Tresca | Canto templado por inducción |
| Perno del seguidor | flexión N·l/(πd³/32) ≤ Fy/Nd; corte N/A ≤ Fy/(Nd√3) | ASME BTH-1 Cat. B §3-3.3, §3-2.3, §3-2.3.6 | l = altura del rodillo sobre la cara superior de la uña |
| Ranura de la tapa | F_ret/(d·t_tapa) ≤ 1,25·Fy_patín/Nd | ASME BTH-1 §3-3.3 | Aplastamiento |
| Riel-leva | N·k_M/(t·w_n²/6) + F_ret/(t·w_n) ≤ Fy/Nd, sección neta en el bolsillo | ASME BTH-1 §3-2.3 y §3-2.1 | Biapoyado entre soportes, carga en la peor posición del seguidor; 42CrMo4+QT (EN 10083-3, 16 < t ≤ 40: Re ≥ 750) |
| Soportes del riel | R_x·h/(l·b²/6) + R_y·h/(b·l²/6) ≤ Fy/Nd | ASME BTH-1 §3-2.3 | |
| Pórticos del riel (08-11-2026) | patas: (R_x/2)·h/(l·b²/6) + (R_y/2)·h/(b·l²/6) ≤ Fy/Nd; soldadura pata–asiento √[(M_x/S_x + M_y/S_y)² + (V/(a·2(b + l)))²] ≤ 0,60FEXX/(1,20Nd) | ASME BTH-1 §3-2.3, §3-3.4; AISC 360-22 §J2.4 | Reemplazan a los soportes empernados a la bancada: bajo el soporte trasero pasa el cuerpo del cilindro y no cabía un patrón de pernos con brazo de vuelco. Dos patas (x = x_g ∓ (D_cuerpo/2 + 5 + b/2)) soldadas a un asiento sobre la bancada prolongada y ensanchada; el riel lleva una aleta hacia adentro en la zona de apoyo (el seguidor no llega) |
| Pernos riel–pórtico | f_rv ≤ Fnv/Ω, Fnv = 0,45Fu (rosca incluida); aplastamiento R_n = 2,4·d·t·Fu, Ω = 2,00 | AISC 360-22 §J3.7, Tabla J3.2 (grupo 150 ≈ ISO 898-1 10.9); §J3.11 (en 360-16 eran §J3.6 y §J3.10) | Pernos verticales del riel a las tapas de las patas; sin tracción por vuelco (el pórtico la toma en las soldaduras) |
| Material del contacto | cam_mat = 0 → familia 1 en el modo guiado | Criterio del proyecto | Las familias 2–4 (zapata deslizante) se calculan, pero la rampa que exige la sincronía (~62°) se autobloquea con μ ≥ 0,15 y la presión de atasco supera p_adm |
| Seguidor: perno y retención (10-11-2026) | El perno llega a la cara superior del rodillo; rodillo apoyado 2 mm sobre la cara inferior del riel y retenido por una arandela de tope de 4 mm con tornillo axial; 2 + b + 4 + 1 ≤ mín(t_riel; z_sup_mesa − z_inf_riel) | Geometría (la carga puede volar sobre el borde de la mesa) | El perno anterior (largo l + 30) terminaba en el eje del rodillo (z 208) y el rodillo llega a z 223 |
| Seguidor: grado del rodillo (10-11-2026) | 100Cr6 templado total 58–64 HRC, más duro que el canto (≥ 55 HRC): el Hertz usa Fy_sup del canto | ISO 683-17:2014 | Cojinete del rodillo: dato del proveedor (hipótesis: μ equivalente ≤ μ_rod) |
| Ranura de la tapa del patín (10-11-2026) | Ajuste deslizante sobre la misma medida nominal: ranura d H9 y perno Ø d f8 (50 H9/f8: juego 0,025…0,126 mm) | ISO 286-1:2010 (Tablas 1 y 2), ISO 286-2:2010 | La ranura de 51 rotulada «H9/f8» no era un ajuste ISO 286 (1 mm de juego) |
| Pernos riel–pórtico: rosca (10-11-2026) | Taladro ciego en la tapa de la pata con remanente 3 mm; rosca útil = taladro − 2·P (hipótesis: filetes incompletos y cono); 1,25·d ≤ l_e ≤ rosca útil − 2; espesor de la tapa = menor múltiplo de 5 mm que lo admite con un largo ISO 4762 (M20 → tapa 40 mm, M20 × 65, l_e 27 mm) | VDI 2230-1:2015 (orientativo, 10.9 en S355); criterio del registro (AF2) | La tapa de 15 mm daba un engrane < 1,25·d |
| Pórtico del riel: material y soldaduras (10-11-2026) | Patas y tapas de S355J2 (Fy 345): flexión de la pata ≤ Fy/Nd; pata–tapa: filetes a ambos lados z = w_mín(máx(b_pata; t_tapa)) con R a la altura del riel (brazo t_tapa); prolongación–base: filete perimetral w_bed_f con el vuelco R·(z_riel − t_base), S_x = a(l·b + b²/3), S_y = a(b·l + l²/3) | AWS D1.1/D1.1M:2020 Tabla 5.3 (metales base precalificados) y Tabla 7.7 (filete mínimo, §7.13); AISC 360-22 §J2.4; ASME BTH-1 §3-2.3, §3-3.4 | El 42CrMo4+QT soldado no es metal base precalificado (exigiría WPS calificado con PQR, precalentamiento y control de dureza de la ZAC): queda solo en el riel-leva, que se emperna |

## Accionamiento pivotado tipo KIET

Pedido del mandante 07-11-2026 (Tarea 2; drive_mode = 2; el valor por defecto sigue siendo 1). Referencia: docs/referencias/2026-10-30-kiet-400t-analisis.md. Dos cilindros de doble efecto pivotan sobre pasadores verticales E en ojales diagonales (φ_E y φ_E + 180°); para invertir el giro el cilindro pivota en el mismo ojal hacia el otro lado (imagen especular respecto de la diagonal); cuatro placas-leva (una por cilindro y sentido). El bloque-uña gira libre sobre el pasador vertical Q del vástago; el extremo inferior de Q es el seguidor y corre en el recorte cóncavo de la placa-leva, empernada a la base fuera de la mesa (la mesa apoya sobre la base hasta R_o = D/2: no hay lugar bajo ella).

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Cinemática | Q = P + L_qp·(E − P)/\|E − P\|; L = \|P − E\| − L_qp; a = (P × u)_z = dL/dθ; toma en L0 + s_libre | Estática del miembro de dos fuerzas | El bloque se alinea con E y P (normal del contacto por el centro del pasador) |
| Roce del contacto | a_ef = a − μ_s·\|v_s\|, v_s = −r·(1 − dψ/dθ), dψ/dθ = (P·u)/\|P − E\| | Potencia virtual | La resultante pasa por Q (bloque libre en Q): el roce inclina la resultante; F_cil·η·a = T/n + μ_s·F_n·\|v_s\| + μ_leva·T_leva·v |
| Fuerza del cilindro | Empuje guiado (09-11-2026): Q en el canto con \|P − Q\| = L_qp; F·u_c + H·(n − μ_leva·t) = F_n·b' (b' = Q→P girada asin(r·sen(atan μ_s)/L_qp) hacia la mesa: círculo de rozamiento); T/n = F_n·(Q × b'); F_cil = máx F/η; FS = F_calado/F_dis ≥ FS_mín | Equilibrio del pasador Q; potencia virtual como control (revisor cruzado, Δ < 0,1 %) | La cinemática colineal (F = T/(n·a_ef·η)·(1 + μ_leva·μ_s)) queda como referencia: el empuje guiado pide hasta 6,1 % más |
| Fuerza en la placa-guía | Empuje: H = h·F en cada θ (a calado: h·F_calado·η); retorno: atasco con el giro en E trabado en el primer contacto de la conducción, N = F_ret/sen φ₁ (sin roce: cota) | Equilibrio | La placa, los tornillos y el pasador Q se verifican con máx(N_atasco; H_calado); la zapata (familias 2–4) con H de diseño |
| Sugerencia de E | máx a_ef,mín con: cajón del ojal dentro de la base, s_req + margen ≤ carrera, Q a d_Q/2 + holgura fuera de la mesa, cuerpo del cilindro fuera de la mesa, bloque a ≥ pv_cB del pasador siguiente | Optimización por malla (10 mm, luego 1 mm) | Con los valores por defecto: R_E = 1.604 mm, L_qp = 440 mm (se adopta 432: 2 mm de margen sobre la holgura con el pasador siguiente) |
| Perfil de la placa-guía | Ver «Placa-guía curva (09-11-2026)»: W(L) ≥ w_nec(L; m + δ), W ≥ w_emp + c; flanco recto por (L0 + tramo, c) tangente a w_nec, biarcos tangentes; canto = desplazamiento exacto a d_Q/2 | Geometría | w = desplazamiento lateral de Q hacia afuera respecto de la recta E–P al inicio; bloque alineado con el vástago en el retorno (hipótesis conservadora) |
| Autobloqueo de la placa-guía | Retorno: μ_E·d_E/(2·L0)·(sen φ + μ·cos φ) < cos φ − μ·sen φ en cada punto de la conducción final; empuje: φ ≤ 90° − atan μ y H > 0 | Equilibrio con fricción | φ = ángulo entre el canto y la recta radial E–Q, punto a punto |
| Bloque-uña | F/(b·h) + 6F·(e_cr + e)/(h·b²) ≤ Fy/Nd; corte 1,5·μ_s·F/(b·h) ≤ Fy/(Nd√3); pandeo F ≤ π²EI/(L_qp²·Nd); Hertz p₀ ≤ 1,67Fy_sup; horquilla en Q: aplastamiento 1,25Fy/Nd y desgarro | ASME BTH-1 §3-2.1, §3-2.2 (compresión, pandeo), §3-2.3, §3-2.3.6 (corte), §3-3.3; Hertz | Cuerpo acodado e_cr hacia afuera para librar el pasador siguiente |
| Pasador Q | M = √[(F/2·(t/2 + g + b/4))² + (N_leva·l_Q)²] ≤ Fy/Nd·πd³/32; corte doble | ASME BTH-1 §3-3.3 | l_Q = horquilla inferior → mitad del espesor de la placa-leva |
| Ojal trasero E | pasador: flexión F/2·(t/2 + g + b/4), corte doble; tapas: aplastamiento (F/2)/(d·t) ≤ 1,25Fy/Nd, desgarro (F/2)/(2·t·a) ≤ Fy/(Nd√3) | ASME BTH-1 §3-3.3 | |
| Soporte del ojal E | Ver «Soporte del ojal E: cajón abierto (10-11-2026)» (reemplaza el cajón en U con ventana) | ASME BTH-1 §3-2; AISC 360-22 §J2; AWS D1.1/D1.1M:2020 | Cajón centrado en E, abierto hacia la mesa en todo el barrido del cilindro |
| Plancha base bajo el soporte E | Ver «Plancha base bajo el soporte del ojal E (10-11-2026)» y su revisión con la base completa | ASME BTH-1 §3-2.3, §3-2.3.6 | Sin anclaje NO cumple (filas «pend»: decisión del mandante; visibles en `verdict.estado_global` = «NO CUMPLE / PENDIENTE DE DECISIÓN») |
| Placa-guía: contacto | familia 1: Hertz p₀ ≤ 1,67Fy_sup con el radio real del canto en cada contacto (1/R_ef = 1/r_Q ± 1/R_c), capa templada ≥ 2·0,786·b; familias 2–4: p = T_dis/(l·t) ≤ p_adm, PV ≤ PV_adm (2 y 3), aplastamiento a calado ≤ 1,25·Fy_rev/Nd (3 y 4), respaldo de acero (2 y 3), zapata l ≤ 3·d_Q | Hertz; catálogo de cada material (opciones A, B, C de la interfaz); ASME BTH-1 §3-3.3 | Familia 2 (UHMW) no es practicable: la zapata que pide PV pasa de 3·d_Q. Familias 2–4 sobre el canto curvo: la forma de la cara de la zapata queda PENDIENTE (fila «pend») |
| Placa-guía: ligamento y tornillos | Ver «Placa-guía curva (09-11-2026)» | ASME BTH-1 §3-2; AISC 360-22 §J3 | 42CrMo4+QT (Fy 750, Fu 900); ISO 10642 M16 8.8 roscados en la base |
| Pandeo del cilindro | F_calado ≤ Pcr/3 con el vástago a L0 + carrera | Criterio conservador frente a ISO/TS 13725 | Dato del proveedor (la geometría del tubo no está en el núcleo) |
| Holguras | Q fuera de la mesa; cuerpo del cilindro fuera de la mesa; bloque libre del pasador siguiente; placas dentro de la base y a cada lado de la diagonal; bloque sobre la placa | Geometría | También a 80 °C con la mesa caliente (escenario térmico, alcance 2) |
| Pivote central | H = máx(H_ecc; Ch·N) + H_asim + H_cil; H_asim = máx\|F₁(μ_s + 0,05) + F₂(μ_s − 0,05)\| | ASME BTH-1 §3-2.3; equilibrio | Con el par en la diagonal las componentes radiales se anulan; con n impar el pivote recibe el empuje completo |
| Material del contacto | cam_mat = 0 → base 1, A 4, B 4, C 3 | Pedido del mandante 07-11-2026 | B → 4 porque la zapata de UHMW no cumple PV con la carga transversal del empuje |

### Placa-guía curva (09-11-2026)

Rediseño de las 4 placas-guía del modo 2 (detalle, cifras y trazabilidad: docs/qa/guia_curva_KIET/cambios.md). Concepto constructivo KIET (plano KIET-1024-REF-TT-400T): placa rectangular empernada a la base, junto a la cabeza del vástago, con recorte en media luna hacia la mesa; la curva sale de la cinemática del TT300-C (no se trasladan dimensiones de KIET).

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Estabilidad del empuje | La rodilla E–Q–P es inestable en compresión (rigidez lateral −F·(1/L + 1/L_qp)) y el roce de la cara la empuja hacia afuera: Q se apoya en el canto en todo el empuje; h = H/F ≥ 0,005 | Equilibrio del pasador Q | El bloque libre en Q es un miembro de dos fuerzas: su resultante pasa a r·sen(atan μ_s) del centro del pasador (círculo de rozamiento) |
| Requisitos de la trayectoria W(L) del centro del seguidor | W ≥ w_nec(L; m + δ) en el retorno, δ = tolerancia de posición (pv_tolg) + α·ΔT·R_pin (mesa a 80 °C, α medio 20–80 °C de EN 1993-1-2 §3.4.1.1); W ≥ w_emp + c en el empuje; W(L0 + tramo) = c (reenganche) | Geometría | w_nec por búsqueda (polígono del bloque frente al círculo del pasador) |
| Curva | Flanco recto por (L0 + tramo, c) con el ángulo mínimo φ_req ≤ α_máx tangente a w_nec + 0,3; dos biarcos (hombro–cresta y bajada–empalme) tangentes a la trayectoria de empuje en L_fin; salida tangente y cierre del bolsillo hacia la mesa | Geometría de biarcos (brazos iguales) | Tope del flanco elegido para minimizar máx(N_atasco; H_calado); nodos por búsqueda en malla con W ≥ requisito |
| Canto | Desplazamiento exacto de la trayectoria a d_Q/2 hacia la placa: arcos concéntricos (convexo R_c = R − d_Q/2, cóncavo R_c = R + d_Q/2) | Geometría | G1 por construcción (quiebre ≤ 0,01°); polilínea de exportación con flecha ≤ 0,1 mm |
| Sin socavado | R_canto,convexo ≥ pv_rmin (R_centro ≥ d_Q/2 + pv_rmin) | Geometría | |
| Sincronía | nominal ≥ m + δ en toda la conducción final; peor caso (nominal − δ) ≥ m | Geometría | Retorno: Q conserva ψ salvo que el pasador lo empuje (holgura 0); el canto lo conduce desde el primer contacto |
| Interferencias | Seguidor–placa (≥ 0 en todo el recorrido), bloque–pasadores en el empuje guiado ≥ pv_cB, cuerpo del cilindro–mesa, placa fuera de la mesa (R ≥ D/2 + pv_cQ), dentro de la base, libre del cajón E (≥ 5), sin solape entre sentidos (≥ 5 de la diagonal), cuerpo del cilindro sobre la placa (≥ 5 en z) | Geometría | Ambos cilindros y ambos sentidos por simetría (rotación de 180° y reflexión respecto de la diagonal) |
| Ligamento | σ = 6·(N·s/4)/(t·b²) ≤ Fy/Nd; τ = 1,5·(N/2)/(t·b) ≤ Fy/(Nd·√3); b = ligamento en el punto de carga | ASME BTH-1 §3-2.3, §3-2.3.6 | |
| Concentración de tensiones | K_t·σ_nom ≤ Fy (sin fluencia local), K_t = 1 + 2√(a/ρ) | Pilkey, Peterson's SCF Ec. 4.3 | BTH-1 no exige K_t en estática (material dúctil); la fatiga usa la categoría del detalle |
| Deformación | δ = N·s³/(48EI) + N·s/(4κGA) ≤ 0,1 mm | Viga de Timoshenko | No altera la sincronía |
| Tornillos | Grupo elástico (AISC Manual, Parte 7): V_i = F/n + M·r_i/Σr²; f_rv ≤ 0,45·Fu/2; aplastamiento en la placa con t_e = t − k/2 (k ≈ 0,56d) y en la base; tracción por vuelco con corte (J3.8); enganche de rosca 1,0·d ≤ t_base (8.8); distancia al borde (Tabla J3.4M); separación ≥ 3d (J3.4) | AISC 360-22 §J3.4, J3.5, J3.7, J3.8 (inferido de la renumeración: verificar texto), J3.11 (en 360-16: J3.3, J3.4, J3.6, J3.7, J3.10); EN 1993-1-8 Tabla 3.4; VDI 2230-1 (orientativo) | ISO 10642 M16 8.8 (8 por placa) + 2 pasadores ISO 8734 Ø16 m6/H7 de posición |
| Fatiga | Recorte con radio ≥ 25 mm: categoría C; sección neta en agujeros: categoría D; rango con la carga de diseño, N = N_pin·vueltas·años | AISC 360-22 Apéndice 3, Tabla A-3.1 | |
| Vástago | Carga transversal: roce de los ojales E y Q (μ_E·F·d/2) y peso; la reacción de la placa no llega al vástago (miembro biarticulado de dos fuerzas). Flexocompresión a calado P_r/P_c + 8/9·B₁M_r/M_c ≤ 1 | AISC 360-22 §H1.1, §E3, Apéndice 8 | Fy del vástago y tipo de ojal: DATO DEL PROVEEDOR (hipótesis Fy = 520 MPa, μ = 0,20) |
| Topes soldados de la interfaz | Se dimensionan con máx(T_calado del empuje guiado; T_calado colineal de tmaxOf) | Criterio conservador | La colineal da el par mayor |
| Cara del bloque-uña | Cara cilíndrica convexa en planta (R = pv_rface): e_c = R·sen γ, sen γ = (s₂·sen ρ + μ_Q·d_Q/2)/(s₂ − R), ρ = atan μ_s; e_c + b_Hertz ≤ b_f/2 − 3; Hertz con 1/R_ef = 1/r + 1/R; la excentricidad e_c entra al cuerpo (e_cr + e + e_c·s₁/s₂) y a la cara (e + e_c); holguras con el bloque girado δ = asin((R + r)·sen γ/L_qp) hacia afuera | Equilibrio del bloque libre en Q con roce; Hertz; ASME BTH-1 §3-2 | Con cara plana el contacto queda a s₂·tan ρ + μ_Q·d_Q/2 ≈ 67 mm (fuera de una cara de 80 mm) |

## Valor por defecto del accionamiento (08-11-2026)

Decisión del mandante: drive_mode = 2 (pivotado tipo KIET) es el valor por defecto; el guiado con leva de reenganche queda como alternativa (drive_mode = 1). Las pruebas del guiado fijan drive_mode = 1 y los verificadores independientes del accionamiento guiado (indep_tt300c, indep_accionamiento, indep_interfaz, indep_izaje_collar, indep_termica) comparan con tests/golden/tt300c_guiado.json.

Holguras geométricas del modo 2 (pedido del mandante: FU ≤ 0,95): el filete máximo del cajón del ojal baja a FU 0,913 (w = 21 mm). «Cajón del ojal E dentro de la base» (0,999) y «Q fuera de la mesa» (0,974) no pueden quedar ambos bajo 0,95 con B = 2.560: el cajón pide un R_E chico (≤ 1.515 mm con lado 260) y Q fuera de la mesa lo pide grande (≥ 1.645 mm). Con B = 2.760 la sugerencia de E (pv_fugeo = 0,95) da R_E = 1.645 mm, L_qp = 489 mm, FU 0,947 / 0,950, FS 1,456 y +162 kg. Queda para decisión del mandante (tamaño de la base).

## Tornillos avellanados del disco de la mesa (AF2)

Decisión del mandante 08-11-2026: en la opción A pegada (opt_ss = 1, fix_mode = 2) el par de la interfaz pasa del disco inoxidable de la mesa a la plancha inferior de la mesa con tornillos avellanados ISO 10642 clase 10.9 (M12 como punto de partida), roscados en la plancha.

| Verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Fuerza por tornillo | V = T_dis/(n·r) | Equilibrio | T_dis = par del caso de diseño. Rediseño 10-11-2026: r = R_pin (corona de pasadores) y tornillos en las bisectrices entre pasadores (k·360°/N_pin; pasadores en (k + ½)·360°/N_pin), sin las que caen sobre una ranura radial; n automático = todas las libres (24 con 28 pasadores y 12 ranuras). El círculo anterior (R949, n múltiplo de las ranuras) cortaba 8 de los 24 agujeros de los pasadores y la rosca caía en el anillo inferior |
| Corte del tornillo | V/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu (rosca en el plano de corte), Ω = 2,00 | AISC 360-22 §J3.7, Tabla J3.2 (grupo 150 ≈ 10.9) | A_b nominal |
| Aplastamiento en el disco | V ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 | AISC 360-22 §J3.11, Ec. J3-6a (aplastamiento, 2,4dtFu) y J3-6c (desgarro, 1,2l_c·t·Fu); EN 1993-1-8 Tabla 3.4 (espesor con avellanado) | Fu del inoxidable ASTM A240 304 = 515 MPa |
| Aplastamiento en la plancha de la mesa | V ≤ R_n/Ω con t = t_inf, Fu = 450 MPa | AISC 360-22 §J3.11 | Agujero roscado pasante |
| Separación | s = cuerda mínima entre tornillos contiguos ≥ 3·d | AISC 360-22 §J3.4 (en 360-16, §J3.3) | |
| Ligamento al agujero del pasador (10-11-2026) | c − d_pas/2 − d_h/2 ≥ 3·d − d_h (el ligamento libre que dejan dos agujeros a 3d) y c − d_pas/2 ≥ e_mín (el agujero del pasador se trata como borde); sin interferencia: c ≥ d_pas/2 + d_h/2 | AISC 360-22 §J3.4 y §J3.5, Tabla J3.4M | c = distancia tornillo–pasador más cercano (104,3 mm con los valores por defecto); agujero del pasador = d_pas (como en los planos) |
| Distancia al borde | R_o − r ≥ e_mín; r − R_anillo,int ≥ e_mín (unión anillo–plancha inferior) | AISC 360-22 §J3.5, Tabla J3.4M | Corrección 10-11-2026: la Tabla J3.4M de 360-22 agrega una fila para M12 (comparación AISC 360-22/360-16); «la tabla empieza en M16» vale para 360-16. Valor de M12 no leído: se mantiene 22 mm (valor de M16, presumiblemente conservador) hasta leer la tabla (verificar texto) |
| Avellanado | k + 0,5 + sobreespesor de relapeado ≤ t | ISO 10642 (k máx.); criterio del mandante | El disco de la mesa se dimensiona con este mínimo: con M12 pasa de 8 a 10 mm |
| Roscado (10-11-2026) | En la pieza real: anillo inferior de pasadores (MES-004, t_pr) si r − d/2 > R_anillo,int; si no, la plancha inferior. En el anillo: taladro ciego con remanente 3 mm (la punta no asoma a la luz entre anillos, por donde pasa el bloque-uña), rosca útil = taladro − 2·P (hipótesis), l_e = L − (t − 0,5 − sobreespesor) ≥ 1,25·d y l_e + 2 ≤ rosca útil (M12 × 25: l_e 16 mm) | VDI 2230-1:2015 (orientativo, 10.9 en acero S355) | Antes se verificaba 1,25·d ≤ t_inf en la plancha de 16 mm, que no es la pieza donde caía R949 |
| Aplastamiento en la pieza roscada | V ≤ R_n/Ω, R_n = mín(1,2·l_c·l_e·Fu; 2,4·d·l_e·Fu), l_c = mín(s − d_h; ligamento al agujero del pasador) | AISC 360-22 §J3.11 (Ec. J3-6a y J3-6c) | La fuerza es tangencial: el agujero del pasador más cercano está en esa dirección |
| Ranuras de engrase | holgura cabeza–ranura circunferencial ≥ 3 mm; tornillos a mitad de camino entre ranuras radiales | Geometría | |

## Soporte del ojal E: cajón abierto (10-11-2026)

Corrección pedida por el generador de planos: el cuerpo del cilindro (Ø D_cuerpo desde E + e_cuerpo = 75 mm) entraba en el cajón de semilado 130 mm, cuya ventana de 54 mm solo dejaba pasar el ojal, y el cajón no era construible (tapas de 260 × 260 entre paredes de 210 de luz; filete exterior z21 sin lugar frente al marco; filetes interiores y cara inferior de la tapa inferior en una cavidad cerrada; tapa superior a ras; unión pared–pared sin tamaño). Rediseño: cajón centrado en E con las paredes traseras en L hacia la esquina de la base, prolongadas pv_ext = 100 mm hacia la mesa a lo largo de los bordes (fuera del barrido), muñones de las paredes delanteras y **sin pared delantera en todo el barrido del cuerpo**; tapas inferior y superior ENTRE las paredes, recortadas en «nariz». El cuerpo ocupa toda la altura de las tapas (z_eje ± D/2), de modo que las piezas quedan a lateral ≥ D/2 + c de los ejes extremos del barrido o a s ≤ e_cuerpo − c de E (c = pv_cE = 8 mm de diseño). El barrido son los ψ de todos los estados (empuje con Q en el canto, aproximación, retorno, envolvente del canto y referencia colineal) y su reflejo para el giro horario; el cilindro 2 por rotación de 180°. e_cuerpo no se cambia: es un dato del cilindro comercial.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Cuerpo del cilindro libre del soporte | mín dist(huella del cuerpo; piezas que comparten cota) ≥ 5 mm en todos los estados, ambos sentidos | Geometría | 1.532 estados; holgura 8,0 mm (FU 0,625) |
| Flexión de las paredes en la base | σ = máx en las esquinas de la sección de rectángulos (paredes traseras con su prolongación + muñones), flexión biaxial con I_xx, I_yy, I_xy; M = F/2·(h_sup + h_inf) ⟂ −u en cada estado ≤ Fy/Nd | ASME BTH-1 §3-2.3 | Sin la prolongación la interfaz B (eje más alto) daba FU 1,22 |
| Corte en las paredes | τ = F/A_v, A_v = Σ t·L·cos²(pared; −u) ≤ Fy/(Nd·√3) | ASME BTH-1 §3-2.3.6 | |
| CJP paredes–base (J-E1, J-E2, J-E6) | TC-U4b (bisel 45° por el interior, resanado y respaldo por el exterior) + filete de refuerzo interior; resistencia = metal base: FU = máx(σ/(Fy/Nd); τ/(Fy/(Nd√3))) | AISC 360-22 §J2.4, Tabla J2.5; AWS D1.1/D1.1M:2020 Figura 5.1 (juntas CJP precalificadas; la Figura 5.4 de 2020 es la de juntas en T oblicuas) | El exterior de las paredes traseras se suelda desde fuera de la base: el marco se interrumpe frente al soporte (hasta b + pv_ext + 50 mm del eje E) |
| CJP pared–pared (J-E3 a J-E5) | τ = q/t, q = V·Q/I biaxial de la parte unida por la junta ≤ Fy/(Nd√3) | AISC 360-22 Tabla J2.5; ASME BTH-1 §3-2.3.6 | Juntas armadas en banco (ambas caras accesibles) |
| PJP tapas–paredes (J-E7, J-E8) | TC-P4 en bisel simple 45° soldada solo desde arriba, S = t_tapa − 8, E = S − 3; grupo elástico de líneas (cantos de la tapa sobre paredes y muñones) con F/2 en E: f = q_máx/E ≤ 0,60FEXX/(1,20Nd); el filete de refuerzo no se cuenta | AISC 360-22 §J2.1a (Tabla J2.1), §J2.4 (Tabla J2.5); AISC Steel Construction Manual, Parte 8; ASME BTH-1 §3-3.4 | La cara inferior de las tapas no se suelda (sin acceso); la carga de las tapas está en su plano |
| Garganta mínima de las PJP | E ≥ E_mín(parte más delgada) | AISC 360-22 §J2.1b, Tabla J2.3 | |
| Filete de refuerzo mínimo | w ≥ w_mín(máx(t_pared; t_base; t_tapa)) | AWS D1.1/D1.1M:2020 §7.13, Tabla 7.7 | z8 |
| Acceso | Exterior: w + 5 ≤ distancia de la pared trasera al borde de la base (marco interrumpido); tapa superior rebajada pv_rebt ≥ w bajo el borde de las paredes (rincón del filete) | AWS D1.1/D1.1M:2020 Cláusula 7 (Fabricación; subcláusula del resanado: verificar texto). La Figura 5.2 de 2020 es la de juntas PJP precalificadas: no corresponde al rincón del filete (referencia del filete en T: verificar texto) | Secuencia: (1) marco interrumpido; (2) paredes y muñones armados en banco (J-E3 a J-E5); (3) paredes a la base desde el interior sin tapas y respaldo exterior (J-E1, J-E2, J-E6); (4) tapa inferior sobre calzas, desde arriba (J-E7); (5) tapa superior (J-E8); (6) agujero Ø d_E H9 en línea después de soldar; (7) VT 100 %, UT 100 % de las CJP, MT de PJP y filetes (cláusula 8) |
| Tapas: desgarro | Hacia las paredes traseras: a = distancia del agujero a la cara interior de la pared en −u − d_E/2 (no hasta la cara exterior: la tapa termina en la pared); hacia la nariz con la tracción del retorno F_ret = A_anular·p_ret | ASME BTH-1 §3-3.3 | t_tapa 28 → 29 mm (con 28 el desgarro daba FU 0,909; con 30 la flexión del pasador E pasa de 0,90) |
| Fatiga | Pie de la CJP pared–base: categoría E (conservador); garganta de la PJP de las tapas: categoría F | AISC 360-22 Apéndice 3, Tabla A-3.1 | |

Espesores: paredes 25 → 30 mm. Masa por soporte 56,4 → 47,0 kg. La flexión de la plancha base de 18 mm bajo el momento del soporte (≈ 47 kN·m a calado en la opción por defecto), pendiente en esta corrección, se verifica desde el 10-11-2026 en «Plancha base bajo el soporte del ojal E (10-11-2026)»: sin anclaje NO cumple.

## Plancha base bajo el soporte del ojal E (10-11-2026)

> **Superada el 10-11-2026** por «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)». La verificación independiente mostró que la frase «ningún refuerzo local lo resuelve» es falsa: el inserto de esquina lo resuelve con la mesa cargada. Además, los FU de esta sección usan Fy/Nd (corresponde 1,25·Fy/Nd, BTH-1-2020 §3-2.3.4) e incluyen picos singulares. Se conserva como antecedente (modelo disponible con `ins_on = 0`).

Cierre de la hipótesis del rediseño del soporte E (la flexión de la plancha base no se verificaba). **Resultado: la plancha de 18 mm apoyada en la losa sin anclaje NO puede tomar el momento del soporte; ningún refuerzo local lo resuelve.** Las filas quedan con su FU y estado «pend» (no «fail») hasta la decisión del mandante, para no cambiar el veredicto del diseño por defecto sin esa decisión.

**Datos del proyecto.** Base «apoyada en losa o mats» (HANDOFF TT300-B, §9); no hay anclaje, pernos de fundación ni datos de la losa (f'c, espesor, armadura, bordes). Se declara: contacto unilateral (la losa solo comprime), losa rígida, sin anclaje, peso propio de la plancha despreciable (ρ·g·t = 0,0014 MPa).

**Transferencia de carga.** El soporte es un cuerpo rígido soldado a la plancha (CJP pared–base). La fuerza del cilindro F·f actúa en E a h = (h_sup + h_inf)/2 = altura del eje sobre la plancha (resultante de F/2 en cada tapa): M = F·h alrededor del eje horizontal ⟂ f. En planta F se cierra dentro de la tornamesa (el otro cilindro, a 180°, y el roce de la mesa forman un par horizontal): la losa no toma corte y la plancha lleva F en su plano. M tiene que bajar a la losa como un par vertical: compresión bajo el pie (paredes del lado de f) y retención del talón. Sin anclaje, lo único que retiene el talón es la mesa cargada (R ≤ D/2), a través de la flexión de la plancha. En el empuje (f = −u) el talón queda del lado de la mesa, a 0,3–0,5 m de ella y con el barrido del cilindro, las placas-guía y la oreja de izaje de la diagonal en medio; en el retorno (f = +u) el talón es la esquina de la base, con la mesa entera delante del pie: no hay retención detrás del talón y toda la M cruza la plancha.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Casos | Empuje a calado F_calado (−u) y atasco del retorno F_ret = A_anular·p_ret (+u); todos los estados del barrido (empuje, aproximación, retorno, envolvente del canto, colineal) en ambos sentidos | ASME BTH-1 §3-2 (Nd = 3) | Térmico: no aplica (F sale de las presiones de alivio y de retorno; la base queda a la sombra y h no cambia). Gobierna la interfaz B (eje más alto: h = 160 mm) |
| Flexión de la plancha (franja) | σ = 6·M_corte/(b·t²) ≤ Fy/Nd; M_corte = M·(1 − a/s_H) en la línea del talón (∥ al vector momento) si la mesa queda detrás del talón (s_H > a), M si no; b = w + a | ASME BTH-1 §3-2.3; equilibrio del cuerpo libre soporte + plancha del lado del pie | a = extensión de la huella de las paredes en f; w = ancho ⟂ f; s_H = brazo desde el pie hasta el borde MÁS LEJANO de la mesa (el brazo más largo: favorable para la retención T = M/s_H y conservador para M_corte, que crece con s_H); b: reparto a 45° desde el centro de la huella (criterio de ingeniería) |
| Corte de la franja | τ = 1,5·V/(b·t) ≤ Fy/(Nd·√3), V = M/a (cota superior: retención en el talón) | ASME BTH-1 §3-2.3.6 | Cumple con holgura (FU 0,21 / 0,32 con B) |
| Levantamiento | Anclaje a la losa | — | No definido en el proyecto: fila «pend» con el momento a anclar por soporte |
| Retención con la mesa vacía | n_cil·M/s_H ≤ W_mesa (W_d = mesa + disco rotatorio + ½ pivote, más los bloques-uña: cota superior) | Equilibrio | El calado no depende de la carga (atasco con la mesa vacía). Por defecto 38,6 kN pedidos frente a 15,0 kN de peso propio; con B, 58,9 frente a 18,8 kN: la retención por la mesa no es fiable ni con el brazo más largo. Se exporta en `plancha_base.mesa_vacia` |
| Punzonamiento / desgarro | — | — | Sin anclaje no hay carga concentrada que punzone la plancha (el pie apoya directo en la losa; el talón tira de la plancha a lo largo de las CJP, ya verificadas como metal base). Con anclaje se verifica la pieza que reciba el perno |
| Contraste (segundo método) | FEA propia de Mindlin (Q4, integración selectiva) con soporte rígido (3 grados de libertad maestros), contacto unilateral por conjunto activo y la huella de la mesa como apoyo bilateral | tests/indep_pivotado.py, sección 5c | fea.js no admite contacto unilateral, vínculos rígidos ni cargas nodales: no se modificó; se usa la franja en el núcleo y la FEA en el verificador |

Resultados (FU = σ/(Fy/Nd), Fy/Nd = 115 MPa):

| Interfaz | h (mm) | M empuje / retorno (kN·m) | Franja empuje | Franja retorno | FEA empuje / retorno (malla 40, por defecto) |
|---|---|---|---|---|---|
| Por defecto | 105 | 46,8 / 6,8 | 8,37 | 1,43 | 13,9 / 3,2 |
| A (inox) / C (bronce) | 135 | 60,1 / 8,8 | 10,8 | 1,84 | — |
| B (UHMW) | 160 | 71,3 / 10,4 | 12,8 | 2,19 | (malla 20: picos ≈ 27 / 6, percentil 99,5 ≈ 11 / 2,8) |

Aun con la capacidad plástica (m_p = Fy·t²/4) y sin factor de diseño, la franja del empuje por defecto da 962/(1,5·345) = 1,86 > 1. Sin anclaje, la franja pediría t ≥ 18·√8,37 ≈ 52 mm (por defecto) y ≈ 64 mm (B) en toda la zona entre el soporte y la mesa.

**Por qué no se aplicó una solución en el núcleo.** El caso que manda es el de la retención: sin anclaje, el par del soporte solo puede bajar a la losa a través de la plancha hasta un punto retenido, y el único es la mesa, que con la mesa vacía no alcanza (fila anterior). Un refuerzo local (cartela, plancha de refuerzo, espesor local) aumenta la resistencia de la plancha pero no crea retención, de modo que no cierra el caso. Las dos soluciones que sí lo cierran (anclaje o base rígida) piden datos o decisiones que el proyecto no tiene: la losa (f'c, espesor, armadura, bordes) o si la tornamesa debe poder apoyarse en mats. No se inventan.

**Soluciones (decisión del mandante; no se aplicó ninguna).**
1. Refuerzo local (cartelas hacia atrás, plancha de refuerzo bajo el soporte, aumento local de espesor): no resuelve. Lo que falta es la retención del talón; un refuerzo bajo el soporte o hacia atrás no la crea, y llevar el momento hasta la mesa pide una sección del orden de 50–60 mm de espesor (o nervios) a lo largo de 0,3–0,5 m entre el soporte y la mesa, justo donde barre el cilindro (el cuerpo pasa a 40 mm sobre la plancha por defecto), van las placas-guía y está la oreja de izaje de la diagonal.
2. Anclaje a la losa (mínimo en masa): pernos en bloques soldados al extremo de las paredes traseras prolongadas (fuera del barrido). Orden de magnitud con el pie en el eje de la pared opuesta: T ≈ M/0,38 m ≈ 120 kN por defecto y ≈ 185 kN con B en el empuje; ≈ 20–30 kN en el retorno. Consecuencias que hay que verificar antes de adoptarlo: (a) el cuerpo del soporte pasa a llevar ≈ 0,7·M en flexión vertical hasta el perno (paredes con las tapas como alas, estimación gruesa sin descontar el agujero del pasador: FU ≈ 0,8 por defecto y ≈ 1,0 con B; hay que reforzarlo); (b) la losa (arrancamiento, cono, bordes) la verifican terceros con f'c y espesor, datos que hoy no existen; (c) la tornamesa deja de poder apoyarse en mats.
3. Base rígida (sin anclaje): plancha de ≥ 52–64 mm o emparrillado bajo la base entre los soportes y la mesa; sube el eje y la masa (≈ +1,7 t con 52 mm y ≈ +2,4 t con 64 mm en toda la base).

### Revisión con la base completa: dos soportes (10-11-2026)

Estudio completo en `docs/qa/plancha_base_soporte_E.md`; scripts y salidas en `docs/qa/plancha_base_soporte_E/`.

**Modelo.** Los dos cilindros van en ojales diagonalmente opuestos, alimentados en paralelo con un alivio común, sin divisor de caudal ni válvulas por cilindro en el núcleo. F₂ = −F₁ y M₂ = −M₁: la base no vuelca como cuerpo libre. El par de un soporte llega al otro solo rodeando la mesa, y el vector momento, casi paralelo a un borde, se traslada en las dos direcciones del plano: es **torsión de la base**, con fuerzas de esquina ≈ M/B (las esquinas libres suben) y m_xy ≈ M/(2·B). Por defecto, V = 18,3 kN y τ = 6·m_xy/t² = 169 MPa en 18 mm (FU 2,55 frente a Fy/(Nd·√3)); con B, 27,8 kN y FU 3,9. Es una cota inferior: placa libre, sin peso ni contacto. Un calado con un solo cilindro es posible si el otro no tiene reacción (bloque-uña sin tomar o émbolo a fin de carrera).

**FEA de la base completa.** Mindlin Q4, los dos soportes rígidos, contacto unilateral en todos los nudos, peso propio de la plancha y mesa vacía en R_i…R_o, o la huella de la mesa bilateral si está cargada.

| Caso (malla 40) | Por defecto | Interfaz B |
|---|---|---|
| Mesa cargada, uno o dos cilindros | FU 13,8; levantamiento 20 mm junto al talón | FU 21,1; 31 mm |
| Mesa vacía, dos cilindros | FU 21 junto al soporte y 7,4 lejos; queda apoyada en los dos pies (279 mm lineal) | FU 33 y 11,5 (462 mm) |
| Mesa vacía, un cilindro | Sin equilibrio sin anclaje | Ídem |
| Retorno, mesa vacía | FU 3,2; la esquina del soporte sube 34 mm | FU 4,9; 58 mm |

Con la mesa cargada, la FEA coincide con la de d94d7c4 (13,9). La retención `mesa_vacia` (n_cil·M/s_H) queda como cota del modelo de un soporte, porque los pedidos de los dos soportes no se suman. La conclusión no cambia: NO cumple sin anclaje.

**Opciones** (malla 80; detalle en el estudio):

- **C, marco perimetral abierto continuo con cartelas.** No da rigidez a torsión: con 300×25 (603 kg) la plancha queda en 1,6 y el marco en 2,1, con 104 mm de levantamiento.
- **C, cajón cerrado de 70 mm de ancho.** Es lo que cabe entre el borde y el barrido. Con 70 × 250, t 16 (733 kg) cumple con la mesa vacía por defecto (0,92; 10 mm), pero no con la mesa cargada (1,40) ni con B (1,31).
- **D, nervios diagonales.** No dan torsión ni crean retención: con la mesa vacía, 7,6.
- **B, plancha de 64 mm.** Con +2,4 t queda en el límite por defecto (1,03; 4 mm) y no cumple con B (1,66).
- **A, anclaje.** A1, con 2 pernos por soporte, pide 116 kN por perno (177 con B). A2, con el marco 200×20 y 1 perno por esquina libre, pide 48 kN (75 con B), con el marco a redimensionar. Los pernos se diseñan con datos de la losa que no existen.

**Decisión.** No hay una solución C o D de < 600 kg sin interferencias, de modo que no se implementó ninguna geometría. Decide el mandante: anclaje (A2 es el de menor fuerza), base rígida o restricción del calado con la mesa vacía, por ejemplo con un alivio reducido sin carga.

**Estado global.** `analyze()` exporta `verdict.pendientes_criticos[]` (filas «pend» con FU > 1, con su referencia), `verdict.fuMaxPend` y `verdict.estado_global` («NO CUMPLE» / «NO CUMPLE / PENDIENTE DE DECISIÓN» / «CUMPLE»). TT.thermal agrega ambos en `byT[]`. `verdict.estructura` no cambia de significado: resume las verificaciones resueltas y la usa el generador de planos. La exportación del soporte agrega `plancha_base.revision_base_completa`.

### Estimación de A2 para la decisión del mandante (10-11-2026; no implementada)

Detalle en `docs/qa/plancha_base_soporte_E.md` §5; scripts `a2.py` y `anclaje_aci.py`.

| Ítem | Por defecto | Interfaz B | Criterio |
|---|---|---|---|
| Marco que cumple (pletina de canto) | 420 × 30, FU 0,99, ≈ 1,0 t | 550 × 40, FU 0,95, ≈ 1,8 t | ASME BTH-1 §3-2: √(σ_b² + 3τ_t²) ≤ Fy/Nd en el marco |
| Marco que cumple bajo la cara superior de la mesa (cajón de 80 mm de ancho) | 80 × 200, t 25: FU 1,00, ≈ 1,0 t | 80 × 250, t 35: FU 0,92, ≈ 1,6 t | Ídem |
| Fuerza característica por perno (a calado, envolvente de los marcos ≥ 200×20) | 48 kN de tracción, sin corte | 75 kN | FEA de la base completa, malla 80 |
| Orientación del anclaje (hipótesis f'c = 25 MPa, fisurado, lejos de los bordes, N_ua = 1,6·N_k) | Químico (ACI 355.4), M20 8.8, h_ef ≈ 250 mm, τ_cr ≥ 7,6 MPa | M24 8.8, h_ef ≈ 310 mm, τ_cr ≥ 7,9 MPa | ACI 318-19 §17.6.1, §17.6.2, §17.6.5, Tabla 17.5.3; orientativo (dependen de f'c, espesor, armadura y bordes, que no se conocen) |

Consecuencias no verificadas: las paredes traseras del soporte E pasan a ser parte del marco y toman 84–141 kN·m; la pletina sobresale de la cara superior de la mesa (conflicto si la carga vuela sobre el borde); la tracción se repite (ACI 318-19 cap. 17 no cubre la fatiga de alto ciclo). No se implementó ninguna geometría.

## Plancha base bajo la ménsula del ojal trasero (modo guiado, 10-11-2026)

> **Superada el 10-11-2026** por «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)»: inserto bajo cada ménsula, dimensionado igual. El estado «NO CUMPLE / PENDIENTE» de esta sección vale solo sin inserto (`ins_on = 0`).

Pregunta: ¿el modo guiado (drive_mode = 1) tiene el mismo problema que el soporte E del modo pivotado? Estudio completo en `docs/qa/plancha_base_modo_guiado.md`; scripts y salidas en `docs/qa/plancha_base_modo_guiado/`.

**Mecánica.**
- La ménsula del ojal trasero (dos mejillas soldadas a la plancha) recibe −F·ŷ a la altura del eje (h = 105 mm; con B, 160) en (x_g; y_ojal) = (1.140; −945).
- En el empuje la reacción la da la mesa (roce de la interfaz y el otro cilindro). La guía de la bancada solo toma las reacciones laterales del patín (a z_T = 31 mm), el roce y el vuelco del roce. El par de la ménsula no se cierra en la bancada: por cilindro quedan 44,4 kN·m en x y 6,7 en y sobre la base.
- Con los dos cilindros, M₂ = −M₁ entre las ménsulas diagonalmente opuestas, y el par cruza la base como torsión. Las bancadas corren en y y son secciones abiertas.
- El retorno con la uña trabada en la rampa del riel-leva se cierra en la franja de la bancada: ménsula, patín y pórticos están sobre la misma bancada y la suma por cilindro es cero.
- El atasco a nivel de toma cruza la base: h·√(F_ret² + N_toma²) = 8,4 kN·m.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Casos | Empuje a calado (F_calado) y retorno (F_ret = A_anular·p_ret, en la rampa y a nivel de toma); dos cilindros y uno; mesa vacía y cargada | ASME BTH-1 §3-2 (Nd = 3) | Térmico: no aplica. Gobierna la interfaz B |
| Flexión de la plancha bajo la ménsula (franja) | σ = 6·M_corte/(b·t²) ≤ Fy/Nd, con la huella de las mejillas (a = L_mejilla = 325, w = 200) y la retención en el borde más lejano de la mesa | ASME BTH-1 §3-2.3 | Mismo modelo que el soporte E; no cuenta la bancada. Empuje FU 12,1 (B 18,4); retorno 2,09 (B 3,18), sin retención detrás del talón. Estado «pend» |
| Corte de la franja | τ = 1,5·(M/a)/(b·t) ≤ Fy/(Nd·√3) | ASME BTH-1 §3-2.2 | 0,34 (B 0,52) |
| Torsión de la base entre las dos ménsulas | τ = 6·m_xy/t² ≤ Fy/(Nd·√3), m_xy = M/(2B) | ASME BTH-1 §3-2.2 | Cota inferior (placa libre): FU 2,55 (B 3,88). Estado «pend» |
| Levantamiento / anclaje | Anclaje no definido en el proyecto | — | Fila «pend» con el momento a anclar y la retención con la mesa vacía (45,4 kN pedidos frente a 14,0 kN de peso) |
| Contraste | FEA de Mindlin de la base completa: bancadas ortótropas con la sección real (J de Prandtl con la ranura abierta), ménsulas rígidas, contacto unilateral, peso propio | Estudio y tests/indep_accionamiento.py, prueba 9 | Malla 40, mesa vacía con dos cilindros: plancha lejos FU 2,0 (B 3,5), bancada 4,7 (B 7,6), esquinas libres a 0,13 m (B 0,23), junto a las mejillas 8,5 (21 con malla 20); mesa cargada 3,9 / 2,2 / 1,8; un cilindro con la mesa vacía, sin equilibrio; retorno 1,3–1,7 junto a las mejillas |

**Resultado: el modo guiado NO cumple sin anclaje ni base rígida.** Tiene el mismo mecanismo que el pivotado, con valores menores. Ningún refuerzo menor lo resuelve:
- Cerrar la franja de 52 mm de plancha sola entre las mejillas y la prolongación de la bancada deja la bancada en FU ≈ 4 con la mesa vacía y en 1,9 con la mesa cargada.
- Un perno por esquina libre pide ≈ 75 kN (126 con B), y la bancada sigue en 3,7 (B 5,8).

**Implementado.**
- Seis filas «Plancha base bajo la ménsula del ojal trasero: …» en «Articulaciones», con FU y estado «pend» en la franja (empuje y retorno) y en la torsión.
- Con eso el modo guiado pasa a `verdict.estado_global` = «NO CUMPLE / PENDIENTE DE DECISIÓN» (`fuMaxPend` 12,08).
- Exportación: `designDrive().guiado.plancha_base` (no va en `tools/export_design.js`, que tiene que coincidir con `packages/web/planos_export.js`).

Golden del modo guiado: agrega solo las cuatro filas con FU; no cambia ningún valor.

**Observación fuera del alcance.** Por defecto, el cuerpo del cilindro (Ø 130, eje a 105 mm) pasa sobre la prolongación de la bancada (cara superior a 40 mm) con 0 mm de holgura, y ninguna fila lo verifica. No se cambió.

## Plancha base: base de 20 mm con inserto de esquina (10-11-2026)

Decisión del mandante del 10-11-2026, tomada tras la verificación independiente (`tests/indep_plancha_base_E.py`). Estudio completo en `docs/qa/plancha_base_inserto.md`; scripts y salidas en `docs/qa/plancha_base_inserto/`.

**Qué corrige la verificación independiente.**
- La estática del núcleo era correcta: M = F·h, con h = 105 mm por defecto y 160 mm con la interfaz B.
- Los FU 8,37, 13,8, 21 y 33 de las secciones anteriores estaban inflados por tres causas:
  - picos singulares en la esquina de la huella rígida;
  - F_b = Fy/Nd en lugar de 1,25·Fy/Nd;
  - la afirmación de que «ningún refuerzo local resuelve», que es **falsa**: el inserto de esquina tipo KIET lo resuelve con la mesa cargada.

**Decisión 1. Base de 20 mm en toda la planta más un inserto de esquina bajo cada soporte del cilindro.**
- Modo 2: un inserto bajo cada soporte del ojal E. Modo 1: uno bajo cada una de las `n_br` ménsulas del ojal trasero.
- El inserto va al ras por debajo con la base y con la cara superior más alta.
- La interfaz B dimensiona su propio inserto: la geometría sale del cálculo.

**Decisión 2. El atasco a presión de alivio con la mesa vacía queda EXCLUIDO como caso de diseño.** Es una limitación de uso:

> No operar el accionamiento a presión de alivio con la mesa sin carga; ante un atasco sin carga, detener y liberar.

Se exporta en `verdict.limitaciones_uso[]` y en `inserto.limitaciones_uso[]`, y figura en una fila informativa del núcleo. La memoria y los planos tienen que citarla. Con la mesa vacía se verifica la fuerza de servicio.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Flexión de la plancha con el inserto | σ_vM ≤ F_b = 1,25·Fy/Nd, Nd = 3,0; FU objetivo interno ≤ 0,90 (advertencia hasta 1,0) | ASME BTH-1-2020 §3-2.3.4, flexión respecto del eje menor de barras y secciones rectangulares macizas (registro normativo 7030ee3; **número de ecuación: verificar**) | σ = κ·M·S(t_base; t_inserto), M = F·h. S = σ/M se tabula desde la FEA de Mindlin de la base completa del verificador: mesa cargada como cuerpo rígido con contacto unilateral, losa unilateral, dos soportes rígidos con M₂ = −M₁, inserto con su transición, malla de 40 mm. **σ a más de 100 mm de la huella rígida del soporte** (criterio de la verificación independiente, fuera de la singularidad de la esquina rígida). κ = 1,03. Retorno: S_ret propio (talón en la esquina libre). Mesa vacía: factor 1,8. Rebaje local: φ = 0,5 |
| Casos | Mesa cargada: nominal, diseño y calado (A·p_alivio = 445 kN a 700 bar); atasco del retorno con la mesa cargada (A_anular·p_ret); mesa vacía en servicio, F = 1,25·máx(F_dis; F_borde; F_cont)·W_d/N | Criterio del proyecto (decisión del mandante 10-11-2026) | El factor 1,25 es el FS de giro del proyecto (F_calado/F_diseño ≥ 1,25), usado como margen de arranque (parámetro `ins_fsv`). Caso térmico: no aplica |
| Corte bajo el soporte | τ = 1,5·(M/a)/(b·t_inserto) ≤ Fy/(Nd·√3) | ASME BTH-1-2020 §3-2.3.6 | Cota superior V = M/a |
| CJP inserto–base (J-I1) | Metal base de la parte más delgada: FU = σ/(1,25·Fy/Nd) con la tensión máxima de la plancha | AISC 360-22 §J2.4, Tabla J2.5; AWS D1.1/D1.1M:2020 Figura 5.1 (junta precalificada a tope en doble V, B-U3: **verificar designación**) | Se suelda por arriba; se voltea la base, se resana y se suelda por abajo; la cara inferior se amola al ras. UT 100 % |
| Transición de espesor | 1:2,5 en la cara superior del inserto, a lo largo de los bordes interiores | AWS D1.1/D1.1M:2020, cláusula 4 (transición de juntas a tope entre partes de distinto espesor; **verificar el número de cláusula y de figura, y si es exigible a una estructura cargada estáticamente**) | Se aplica porque la tensión de flexión en la junta supera 1/3 de la admisible (conservador). Ancho 2,5·Δ |
| Geometría | Triángulo de la esquina con la hipotenusa a D/2 + gap del centro, menos las muescas rectangulares que dejan libres (con `clr`) las piezas que apoyan en la base: placas-guía y trayectoria del cubo y pasador Q (modo 2) o banda del accionamiento guiado (modo 1). Rebaje local bajo las piezas móviles que no dejan 5 mm | Geometría | Variantes calibradas en orden de preferencia: gap 30 / clr 10 y gap 10 / clr 8 (modo 2); gap 10 / clr 8 (modo 1) |
| Holguras | En planta a placas-guía, cubo de Q o banda ≥ 5 mm; vertical a las partes móviles ≥ 5 mm (sobre la transición la cara está a t − d/2,5); hipotenusa a ≥ 5 mm de la mesa; tapa inferior del ojal E o suplemento de la ménsula sobre el inserto | Geometría | |
| Retención con la mesa vacía en servicio | n_cil·M/s_H ≤ W_mesa | Equilibrio | FU 0,014 (por defecto) |
| Espesor | El menor comercial con FU ≤ 0,90 y las holguras; si ninguno llega a 0,90, el primero con FU ≤ 1 | Criterio del proyecto | Lista 25…80, 90, 100, 110, 120 mm |

Resultados (FU con la mesa cargada a calado, que gobierna):

| Modelo | Inserto | Catetos | Rebaje | FU calado | Holgura vertical | Masa añadida |
|---|---|---|---|---|---|---|
| Por defecto (pivotado, h = 105) | 60 mm (gap 30) | 554 / 554 mm | 5 mm bajo el barrido del cuerpo del cilindro | 0,889 | 5,0 mm (cuerpo del cilindro) | 2 × 83,0 kg |
| Interfaz B (h = 160) | 90 mm (gap 10) | 556 / 556 mm | no | **0,985 (advertencia)** | 25 mm | 2 × 138,9 kg |
| Interfaces A y C (h = 135) | 90 mm (gap 30) | 554 / 554 mm | 5 mm | 0,882 | 5,0 mm | 2 × 130,6 kg |
| Guiado (h = 105) | 50 mm (gap 10) | 589 / 1.132 mm | no | 0,821 | 10 mm | 4 × 110,6 kg |
| Guiado B (h = 160) | 65 mm (gap 10) | 589 / 1.132 mm | no | 0,893 | 50 mm | 4 × 156,6 kg |

**Interfaz B.** La plancha de 20 mm bajo el borde de la mesa satura en FU ≈ 0,98 con cualquier espesor del inserto. Cumple el límite de 1,0, pero no el objetivo interno de 0,90. Queda como advertencia, **pendiente de aceptación del mandante**, igual que la uña (FU 0,907). La alternativa es una base mayor solo para la variante B.

**Implementado en el núcleo.**
- `cornerInsert` / `insertRows` / `insertExport`.
- Filas «… inserto de t mm sobre la base de 20 mm, flexión con la mesa cargada / vacía …», corte, CJP, transición, holguras, asiento, retención con la mesa vacía y la limitación de uso.
- Exportación en `pivotado.fabricacion.soporte_E.inserto` y `levaGuiada.fabricacion.inserto`: polígonos de cada esquina, espesor pleno, rebaje, juntas con tipo, tamaño y verificación, secuencia, masa, casos, holguras y candidatos.
- Las paredes del soporte E arrancan en la cara del inserto.
- La masa de los insertos va en `R.m.brackets` (con el soporte, para la lista de materiales); `R.m.insertos` es informativo.
- El marco se interrumpe a lo largo de los catetos.
- `verdict.limitaciones_uso`.
- Con `ins_on = 0` vuelve el modelo de la franja sin anclaje (pendiente), ahora con 1,25·Fy/Nd.

**Verificador.** `tests/indep_plancha_base_E.py`: §3b en modo rápido (entra a `npm test`) y §4 con la FEA completa de los cuatro modelos y cinco casos. Exige FU de la FEA ≤ 1 y no más del 2 % sobre el núcleo.

### Conflictos del generador de planos con el inserto (22-11-2026)

El generador de planos (378675e) encontró cinco conflictos al dibujar el inserto. Detalle en `docs/qa/plancha_base_inserto.md` §7.

| Conflicto | Corrección en el núcleo | Verificación (exigido ≥ 5 mm) |
|---|---|---|
| Pasador E bajo la cara del inserto (z 59 con t 60; z 89 con t 90 en A/C) | El pasador sobresale 10 mm sobre la tapa superior. Por debajo sobresale lo que deja 10 mm de diseño sobre la cara del inserto, desde 0 (al ras de la tapa inferior) hasta 10 mm. El asiento del inserto pasa a t + 5 ≤ z de la tapa inferior | Fila «Pasador vertical E: extremo inferior sobre la cara del inserto de esquina»: 9 mm por defecto y en A/C, 10 en AF2, 24 en B |
| Orejas de la diagonal sobre la transición | Orejas a (±930; ±930), con x_lug 850 → 930 y c_lug 430 → 350. En el inserto de 90 la transición de las muescas igual alcanzaba el pie: la esquina de cada muesca lleva un chaflán a 45° de lo que pide el pie, limitado por los obstáculos de la muesca con 5 + 1 mm. Así quedan 80,5 mm en A/C y 76,5 en B (12,5 en AF2, 0 por defecto) | Fila «Oreja: pie sobre el espesor pleno del inserto de esquina», con la huella 2R × (t + 2w) y el rebaje con su borde 1:2,5: 12,5 mm por defecto, 10,0 en AF2, 8,1 en A/B/C y ≥ 54 en el guiado. Holgura a las partes móviles: 85 → 25 mm. Izaje: flecha 0,37 → 0,62 del límite (guiado 0,43 → 0,72), σ 0,18 → 0,25 |
| Mejillas de la ménsula fuera del espesor pleno (30,5 mm en base_G, 55,5 en A_G) | Las mejillas, de L_ch, se corren δ hacia la esquina en múltiplos de 5 mm: 65 mm en G, 90 en A_G y 100 en B_G (máx. L_ch − saliente trasera − saliente delantera = 150). Las orejas quedan en el ojal. La franja de `guidedBasePlate` usa la posición corrida | Fila «… mejillas y suplemento sobre el espesor pleno del inserto», con los filetes w_br: 14,5 mm en G y A_G, 12,0 en B_G |
| Masa del inserto como cuña | Volumen exacto: V = ∫₀^Δ A(z) dz, con A el área del contorno desplazado 2,5·z (la regla de «esquinas_espesor_pleno»), menos el rebaje con su borde 1:2,5. Simpson compuesto. Diferencia con una integración propia en grilla de 2 mm < 0,1 % | Test del núcleo y verificador independiente (grilla numpy), tolerancia 0,5 % |
| J-I1 sin designación | B-U3b de AWS D1.1/D1.1M:2020 Figura 5.1: doble V simétrica a tope con resanado de raíz, R 0–3 mm, f 0–3 mm, α = β = 60°, SMAW/GMAW/FCAW. **Cita de memoria: verificar contra la figura.** La transición 1:2,5 lleva la cara del inserto a t_base en la línea de la junta, así que la CJP une 20 + 20 mm (T1 = t_base), no 20 + 60/70/90 | Fila informativa «inserto: J-I1: designación precalificada de la CJP»; `juntas[J-I1].designacion`, `designacion_estado`, `preparacion` |

Masas (añadidas por inserto, sobre la base de t_base):

| Modelo | Antes (cuña) | Ahora |
|---|---|---|
| Por defecto | 83,0 kg | 82,4 kg |
| AF2 | 104,1 kg | 101,9 kg |
| A / C | 130,6 kg | 130,7 kg |
| B | 138,9 kg | 136,4 kg |
| Guiado | 110,6 kg | 110,2 kg |
| Guiado A | 141,9 kg | 140,9 kg |
| Guiado B | 156,6 kg | 155,2 kg |

En A, B y C la masa incluye el chaflán de las muescas.

Masa total por defecto: 3.031,7 → 3.029,9 kg. Se compone de los insertos (−1,2 kg) y del pasador E acortado (−0,6 kg).

El FU de la flexión del inserto no cambia. La FEA del verificador (§4) repite el inserto de B con el chaflán y el guiado con las mejillas corridas, a partir de los polígonos y de `levaGuiada.fabricacion.mensula` exportados.

## Elementos sobre la base: holguras (10-11-2026)

Huellas en planta con su cota z: orejas de izaje (2R × (t + 2w) radial, hasta h + R sobre la base), soportes del ojal E (piezas reales), placas-guía (4: cilindro 1 y 2, ambos sentidos, por rotación de 180° y reflexión respecto de la diagonal), mesa con la interfaz y sus topes (círculo R = D/2) y, en el modo pivotado, las partes móviles en todos los estados del empuje y del retorno (cuerpo y vástago del cilindro, bloque-uña y cubo de Q). En el modo guiado, la banda de cada lado (bancada y prolongaciones, patín, cilindro, riel-leva y pórticos).

| Verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Placas-guía–orejas de izaje | ≥ 5 mm | Geometría | Con las orejas en (±600; ±1.030) la placa del sentido horario las cubría (−35 mm) y el bloque-uña del cilindro 2 en giro horario pasaba sobre ellas (−44 mm) |
| Placas-guía–soportes E y mesa | ≥ 5 mm | Geometría | |
| Orejas–partes móviles | ≥ 5 mm (todas comparten cota: la oreja llega a 182 mm) | Geometría | |
| Orejas–placas, soportes E y mesa (modo guiado: accionamiento) | ≥ 5 mm | Geometría | |

Corrección: orejas sobre las diagonales, x_lug 600 → 850 y c_lug 250 → 430 (centro en (±850; ±850), R 1.202 mm), entre los dos barridos del cilindro de cada esquina: holguras 214 mm a las placas, 85 mm a las partes móviles y 110 mm a la mesa. Las placas-guía no se mueven (sincronía y holguras verificadas sin cambios).

## Placa-guía: holgura mínima de sincronía y pasadores de posición (10-11-2026)

| Dato / verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Puntos de la holgura mínima de sincronía | Punto del bloque-uña (o del cubo de Q) y punto del pasador B más cercanos en el estado de holgura mínima del retorno (mesa detenida en θ_fin, Q contra el canto en L_sync, bloque alineado con E–Q); holgura nominal = distancia entre ambos; peor caso = nominal − δ | Geometría | Exportados en placas_leva.holgura_sincronia, en coordenadas globales de cada placa (rotación y reflexión) y en el marco de la placa (x' a lo largo de la cuerda del canto, y' hacia afuera) |
| Pasadores de posición de la placa-guía | ISO 8734 m6 en H7 escariado; alojamientos ciegos en la base (desde arriba) y en la placa (desde abajo) con remanente ≥ 3 mm y 2 mm de fondo libre bajo la punta; enganche ≥ 1,5·d en cada pieza | Criterio de diseño de pasadores de posición (enganche 1,5·d a 2·d por pieza; de memoria, sin norma de producto que lo fije); ISO 8734 (serie de largos) | Ø16 → Ø8: en la base de 18 mm, 18 − 3 − 2 = 13 mm de enganche admiten d ≤ 8,7. ISO 8734 – 8 m6 × 26: 13 mm en la base y 13 mm en la placa; alojamientos de 15 mm. Salida de aire de los agujeros ciegos: hipótesis (taladro lateral o pasador con plano). No toman carga |

## Pórtico del riel del modo guiado: patas de S355J2 (10-11-2026)

cam_px 30 → 40 mm: con las patas de S355J2 (Fy 345 en lugar de 750) la flexión de la pata con la interfaz B daba FU 1,20; con 40 mm, 0,75 (por defecto 0,53).

## Cubierta de madera W (rebaje)

Decisión del mandante 08-11-2026: la mesa conserva el anillo superior R_reb…R (plancha superior actual en esa zona, con los N_pin pasadores); dentro de R_reb una plancha rebajada continua bajada t_madera, una pared cilíndrica en R_reb y los tablones enrasados con el anillo. Se elimina el anillo de contención 10×50 (la contención la da el escalón) y la altura total no aumenta. Supuestos por defecto: R_reb = 840, t_reb = t_pared = t_top = 20. Ajustes: t_madera 50 → 45 (con 50 el buje del pivote no cabe bajo la plancha rebajada, 142 > 140 mm, y la plancha inferior pasa de FU 0,90 por la menor altura del cajón; 45 mm = 2" cepillado y paso del parámetro); el anillo se fabrica en una pieza de espesor máx(t_pr, t_top) = 27 desde R_reb (la franja R840…R860 de 20 mm quedaría como un aro de 20 mm de ancho); w_pared = 8 mm (el filete exterior de refuerzo toca el anillo de 27 mm).

| Verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Plancha rebajada (local) | σvm FEA × k_malla ≤ 0,6Fy | Criterio de la mesa (fila 2: 0,6Fy, más conservador que AISC 360-22 F11) | Modelo escalonado desarrollado (abajo); envolvente de dos variantes |
| Flexión global del cajón | σ = M_glob/(t·h_c) + σ_local ≤ 0,6Fy, h_c = h_mesa − t_madera − (t_reb + t_bot)/2 | Placa sándwich axisimétrica (rev. M2) | Sin aporte de la madera. Comprobado con solución cerrada en tests/indep_madera.py |
| Pared en R_reb: flexión | σ = k_malla·σ_FEA + 6·(N_r·h_c + M_lat)/t² ≤ 0,6Fy | Criterio de las planchas de la caja (fila 2: 0,6Fy, más conservador que AISC 360-22 F11) | N_r = M_r,glob(R_reb)/h_c (desvío del ala que cambia de nivel); M_lat = 3·(H/L_c)·h_c/16 (empuje de los tablones, viga empotrada-apoyada). Con ASME BTH-1 §3-2.3 (Fy/Nd) el FU sería ≈ 1,5: BTH-1 se aplica por analogía a la cadena de empuje, no a la caja de la mesa (fila 1 de este registro) |
| Pared en R_reb: corte | τ = 1,5·V/t ≤ 0,6Fy/1,50 | AISC 360-22 G2.1(a) | V = N_r + 11/16·H/L_c |
| Soldadura pared–plancha rebajada (J2) | 2 filetes: f = √[(M/(t·a))² + (V/(2a))²] ≤ 0,6FEXX/2,00 | AISC 360-22 J2.4 (como las soldaduras de la mesa) | Brazo = t_pared (conservador). Con BTH-1 §3-3.4 el FU sería ≈ 1,3 (informado en la fórmula) |
| Soldadura anillo–pared (J1) | PJP en bisel simple 45° desde el rebaje (S = t_pared/2, E = S − 3) + filete exterior: f = √[(M/(t·mín(a; E)))² + (V/(a + E))²] ≤ 0,6FEXX/2,00 | AISC 360-22 J2.1 (Tabla J2.1), J2.4 y Tabla J2.5 | El borde interior del anillo queda a ras con la cara interior de la pared: no hay rincón interior para filete. Geometría: S ≤ h_pared |
| Filetes mínimo y máximo | w_mín por la parte más gruesa (pared–plancha y pared–anillo); w ≤ t_pared − 2 | AWS D1.1/D1.1M:2020 §7.13, Tabla 7.7; AISC 360-22 §J2.2b | El anillo de 27 mm pide 8 mm |
| Madera: aplastamiento ⊥ a la fibra | q = φd·W/(f_apoyo·A)·(1 + 4e/R_carga) ≤ p_madera·C_t; A = π·(mín(R_carga; R_tablones)² − R_abertura²) | Datos de proveedor; NDS 2018 Tabla 2.3.3 (C_t, escenario térmico) | Apoyo continuo de los tablones sobre la plancha rebajada: misma presión en la cara inferior |
| Madera: apoyo lateral contra la pared | σ = H/(L_c·t_madera) ≤ p_madera (⊥, conservador), H = k_hmad·φd·W, L_c = 2·mín(R_carga; R_tablones) | Equilibrio | k_hmad = 0,10 (empuje de skidding): supuesto C por confirmar |
| Fijación de los tablones | ISO 4762 M10 8.8 (o A4-70) con arandela ISO 7093 en cajeado (cabeza 3 mm bajo la superficie), roscado en taladro ciego de la plancha rebajada (remanente 3 mm); engrane ≥ 1,0·d con punta ≥ 2 mm antes del fin de la rosca útil; ≥ 2 filas por pieza a ≥ 7d de los extremos, ≤ 600 mm | ISO 4762, ISO 7093-1, VDI 2230 (orientativo), EN 1995-1-1 §8.5 (de memoria) | Reemplaza el tornillo Ø8×80 que no cabía en 50 + 20 mm (revisión de planos) |
| Holgura perimetral | (α⊥ − α_acero)·ΔT·2R_tablones ≤ 2·c_mad + (n − 1)·j_tab; w_pared + 2 ≤ c_mad | Termoelasticidad (α⊥ = 30×10⁻⁶, C) | La humedad queda pendiente |
| Fatiga de la pared | N = 2·vueltas/año·vida ≤ 20 000: clase de servicio 0 | AISC 360-22 Apéndice 3 A-3.1; ASME BTH-1 §3-4 | Con N > 20 000 el núcleo verifica Cat. E en el pie del filete |

**Modelo FEA escalonado.** La plancha rebajada, la pared y el anillo se resuelven como una placa MITC4 desplegada: la pared es una corona de ancho L_dev = L·(t_reb/t_pared)³ con w = 0 en sus dos extremos (alma de R_reb abajo; anillo rígido en su plano arriba) y continuidad de giro y momento (uniones rígidas); el anillo sigue con los radios desplazados L_dev y los pasadores como apoyos. Envolvente de dos variantes: «anillo» (L = distancia entre planos medios, anillo con pasadores modelado con t_reb: menor restricción del vano) y «empotrada» (L = altura libre, pared empotrada en el anillo: mayor momento en la pared). Validación: (1) tests/test_tt300c.js compara el constructor de malla (TT.stepPlate) en un caso axisimétrico con la solución cerrada de Kirchhoff por tramos (flecha 2 %, M_r 4 %); (2) tests/indep_madera.py resuelve la piel axisimétrica con la pared como viga y como cáscara cilíndrica: con la pared fija radialmente en sus dos extremos la rigidez circunferencial cambia los momentos menos de 0,1 % (efecto ∝ (βh)⁴, βh ≈ 0,4). fea.js no se modificó.

Pendientes: drenaje del rebaje (bandeja bajo los tablones), hinchamiento por humedad, pudrición y acabado; k_hmad del sistema de skidding; los pernos y arandelas de los pasadores sobresalen de la cara superior del anillo (como sin cubierta): la huella de la carga debe quedar dentro de R_tablones.

## Verificación de citas (10-11-2026)

Revisión de las citas de ASME BTH-1, AWS D1.1/D1.1M:2020 y AISC 360-22 escritas de memoria. **No hubo acceso al texto oficial de pago de ninguna de las tres normas.** Fuentes usadas: documentos oficiales gratuitos de los editores (índice de D1.1:2020 en pubs.aws.org, fe de erratas AWS de 2022, comparación AISC 360-22/360-16 en aisc.org), copias no oficiales del texto de BTH-1 (2014, 2017 y 2020) y fuentes secundarias (manuales de software, foros). Lo que solo tiene fuente secundaria queda con «verificar texto». Ningún criterio numérico del núcleo cambia: las correcciones son de referencia, o el criterio del proyecto ya era más conservador.

| Cita del proyecto | Estado | Cita correcta | Fuente |
|---|---|---|---|
| BTH-1: corte Fy/(Nd·√3), §3-2.2 | Incorrecta (número) | §3-2.3.6 «Shear on Bars, Pins, and Plates», válida para h/t ≤ 2,45√(E/Fy); §3-2.2 es «Compression Members». Ecuación (3-23) en 2020 según copia con OCR dañado: verificar texto | Copias de BTH-1-2017/2020 (pdfcoffee); comentario C3-2.3.6 de BTH-1-2014 (yumpu); índice de BTH-1-2023 (madcad) |
| BTH-1: flexión de barra rectangular maciza respecto del eje menor, F_b = 1,25Fy/Nd, §3-2.3.5 | Valor correcto; cláusula incorrecta | §3-2.3.4 «Minor Axis Bending of Compact Sections, Solid Bars, and Rectangular Sections»: 1,25Fy/Nd para perfiles I/H con alas compactas respecto del eje menor, barras macizas redondas y cuadradas y secciones rectangulares macizas respecto del eje menor. §3-2.3.5 trata otros casos respecto del eje menor (tubos/cajones; texto no leído completo). Número de ecuación: verificar texto | Copia de BTH-1-2020 (pdfcoffee); BTH-1-2014 (yumpu, comentario C3-2.3.4) |
| BTH-1: Nd = 2,0 (A) y 3,0 (B), §3-1.3 | Correcta | §3-1.3 (3-1.3.1 según manual de SDC Verifier). Existe además la Categoría C (Nd = 6,00, desde 2017). En conexiones: 1,20Nd salvo aplastamiento | SDC Verifier, ASME BTH-1 Members (2020); ANSI Blog BTH-1-2023 |
| BTH-1: aplastamiento 1,25Fy/Nd, §3-3.3 | Correcta a nivel de sección | En BTH-1-2008 era §3-3.3.4, Ec. (3-53); para uniones que giran bajo carga un gran número de ciclos se pide 0,63Fy/Nd (condición exacta y numeración de 2020: verificar texto) | Eng-Tips (secundaria) |
| AWS D1.1:2020 Tabla 5.8: filete mínimo | Incorrecta para 2020 (numeración de 2015) | §7.13, Tabla 7.7 «Minimum Fillet Weld Sizes». En 2020 la Tabla 5.8 es «Prequalified Minimum Preheat and Interpass Temperature». Los valores 3/5/6/8 mm coinciden | Índice oficial de D1.1/D1.1M:2020 (pubs.aws.org); AWS Welding Digest, jun. 2025; fe de erratas AWS D1.1:2020 |
| AWS D1.1:2020 Tabla 5.3: metales base precalificados | Correcta | Tabla 5.3 | Índice oficial D1.1:2020; ANSI Blog (cambios de 2020) |
| AWS D1.1:2020 Figura 5.4 (TC-U4b, CJP) | Incorrecta | Figura 5.1 «Prequalified CJP Groove Welded Joint Details». La Figura 5.4 de 2020 es «Prequalified Skewed T-Joint Details (Nontubular)» | Índice oficial D1.1:2020; fe de erratas AWS 7-7-2022 |
| AWS D1.1:2020 Figura 5.2 (TC-P4, PJP) | Correcta | Figura 5.2 «Prequalified PJP Groove Welded Joint Details» | Índice oficial D1.1:2020; fe de erratas AWS 7-7-2022 |
| AWS D1.1:2020 Figura 5.2 para el rincón del filete en T | No corresponde | La Figura 5.2 es de PJP. Referencia del filete en T: verificar texto | Ídem |
| AWS D1.1:2020 §7 (acceso para el resanado) y cláusula 8 (END) | Correctas a nivel de cláusula | Cláusula 7 = Fabricación; Cláusula 8 = Inspección. Subcláusula del resanado: verificar texto | Índice oficial D1.1:2020 |
| AWS D1.1:2020 Tabla 5.11 (precalentamiento; en cad/hojas_gen.py, no en este registro) | Incorrecta para 2020 | En 2020 es la Tabla 5.8; la numeración 5.11 aparece en una guía de la edición 2025 (verificar texto) | AWS Welding Digest; open-exam-prep (secundaria) |
| AWS D1.1:2020 transición 1:2,5 en CJP a tope de espesores distintos (no se cita en este registro) | Parcial | Carga cíclica: Figura 4.17 «Transition of Butt Joints in Parts of Unequal Thickness (Cyclically Loaded Nontubular)», pendiente ≤ 1:2½ con tracción cíclica (subcláusula: verificar texto). Carga estática: Figura 4.8 «Transition of Thickness (Statically Loaded Nontubular)», §4.7.5 y §4.8.1. La condición «tracción > ⅓ de la admisible» viene de D1.1:2000 (§2.20) y no se confirmó para 2020: verificar texto | Índice oficial D1.1:2020; D1.1:2000 (secundaria); foro AWS |
| AISC 360-22 §J2.4 y Tabla J2.5 | Correctas | Sin renumeración en J2 (cambió el título de J2 y se agregó la Ec. J2-4 con k_ds) | Comparación AISC 360-22/360-16 (aisc.org) |
| AISC 360-22 §J3.3: separación mínima | Incorrecta (numeración de 360-16) | §J3.4 «Minimum Spacing» (§J3.3 es «Size and Use of Holes») | Comparación AISC 360-22/360-16 |
| AISC 360-22 §J3.4, Tabla J3.4M: distancia al borde; «empieza en M16» | Sección incorrecta; observación sobre M12 incorrecta | §J3.5 «Minimum Edge Distance», Tabla J3.4M, que en 360-22 agrega una fila para M12. Valores de M12 y M16: verificar texto | Comparación AISC 360-22/360-16 |
| AISC 360-22 §J3.6: corte y tracción de pernos | Incorrecta (numeración de 360-16) | §J3.7 «Tensile and Shear Strength of Bolts and Threaded Parts», Tabla J3.2 | Comparación AISC 360-22/360-16 |
| AISC 360-22 §J3.7: corte con tracción | Incorrecta (numeración de 360-16) | §J3.8 (inferido de la renumeración: verificar texto) | Comparación AISC 360-22/360-16 |
| AISC 360-22 §J3.10, Ec. J3-6a: aplastamiento | Sección incorrecta; ecuación incompleta | §J3.11 «Bearing and Tearout Strength at Bolt Holes». 2,4dtFu es la Ec. J3-6a (aplastamiento) y 1,2l_c·t·Fu es la Ec. J3-6c (desgarro) | Comparación AISC 360-22/360-16; AISC FRR 2024-04 (Denavit) |
| AISC 360-22 F11 como fuente de 0,6Fy | Incorrecta como cita | F11 (fluencia): Mn = Mp = Fy·Z para barras rectangulares respecto de cualquier eje en 360-22 (Ec. F11-1; F11-2 es para barras redondas), Ωb = 1,67; para el rectángulo Z = 1,5S, de modo que Mn/Ωb ≈ 0,90Fy·S. 0,6Fy es un criterio del proyecto, más conservador | Comparación AISC 360-22/360-16 (vía resumen secundario); texto de F11-1: verificar texto |
| AISC 360-22 H1-1a | Correcta (forma) | Pr/Pc + 8/9·(Mrx/Mcx + Mry/Mcy) ≤ 1,0 si Pr/Pc ≥ 0,2; si Pr/Pc < 0,2 se usa H1-1b. Sin cambios de 360-16 según fuentes secundarias | calcs.com, steelcalculator (secundarias): verificar texto |
| EN 982 → EN ISO 4413:2010 | Correcta | EN ISO 4413:2010 reemplaza a EN 982:1996+A1:2008 | SIS, DIN, BSI |
| EN 1993-1-2 §3.4.1.1 (Δl/l) | Fórmula consistente | La fórmula da 0,09984 % a 100 °C, igual al valor de referencia del benchmark SOFiSTiK BE32 y del ejemplo de COMSOL basado en EN 1993-1-2. Número de cláusula no leído | docs.sofistik.com (BE32); doc.comsol.com |
| ISO 10100: prueba a 1,5 × p | No verificada | La edición vigente es ISO 10100:2020; el factor 1,5 solo aparece en una fuente secundaria sin cláusula | iso.org; hydraulic-cylinders.net |
| Rango de temperatura BTH-1 (25 a 150 °F) | No verificada la cláusula | El valor coincide con Tandemloc y Hoist Magazine (secundarias) | Ídem |

Citas «de memoria» de ASME II-D Tabla Y-1, EN 10088-2/EN 10028-7, ISO 898-1 (temperatura elevada), CDA (α del bronce) y EN 1995-1-1 §8.5: no se revisaron en esta pasada; siguen como estaban.

**Efecto en el cálculo.** (1) La flexión de la cadena de empuje se verifica con Fy/Nd. BTH-1 §3-2.3.4 admite 1,25Fy/Nd para pasadores (barras redondas macizas) y secciones rectangulares macizas respecto del eje menor: el criterio actual es un 20 % más conservador en esos casos. No se cambia sin decisión del mandante y sin confirmar en el texto qué secciones del proyecto califican (la flexión respecto del eje mayor de barras rectangulares tiene límite de pandeo lateral). (2) 0,6Fy en las planchas es más conservador que F11 (≈ 0,90Fy·S). (3) Las demás correcciones son de numeración y no cambian ningún FU.

**Referencias en el código que siguen la numeración anterior** (no se modificaron en este cambio: solo se tocó este registro): `packages/core/tt300c.js` cita «AWS D1.1 Tabla 5.8» (filete mínimo), «Figura 5.4 (TC-U4b)», «Figura 5.2» para el filete en T, «AISC 360-22 F11 (0,6Fy)» y «ASME BTH-1 §3-2.5» para aplastamiento (§3-2.5 trata tensiones normales y de corte combinadas según fuentes secundarias: verificar texto); `cad/hojas_gen.py` cita «T5.8 filete mínimo, T5.11 precalentamiento» y «AWS D1.1 CL. 3» para WPS precalificados (en 2020 es la Cláusula 5).
