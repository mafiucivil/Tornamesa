# Registro de criterios normativos · TT300-C

| Ámbito | Criterio | Referencia | Justificación |
|---|---|---|---|
| Cadena de empuje (pasadores, uña, articulaciones, mejillas) | Tensiones admisibles Fy/Nd; corte Fy/(Nd·√3); aplastamiento 1,25Fy/Nd; soldaduras 0,60FEXX/(1,20Nd) | ASME BTH-1, Categoría de diseño B (Nd = 3,0), §3-2 y §3-3 | Decisión del usuario 30-10-2026. Se aplica por analogía (no es dispositivo bajo el gancho). Verificación a la fuerza de calado (área × presión de alivio) |
| Planchas de la mesa y de la base | σvm ≤ 0,6Fy (criterio conservador rotulado F11) | AISC 360-22 ASD | Flexión local por FEA × k_malla 1,15 más membrana global axisimétrica |
| Corte en nervios | 0,6Fy·Aw·Cv1/Ω, Ω = 1,50 si h/t ≤ 2,24√(E/Fy) | AISC 360-22 G2.1(a), Ec. G2-1 | |
| Soldaduras de la mesa | 0,60FEXX/Ω, Ω = 2,00, sin aumento direccional | AISC 360-22 J2.4 | |
| Fluencia local de almas | q/t ≤ Fy/1,50 | AISC 360-22 J10.2 | Simplificación conservadora |
| Tamaño mínimo de filete | 3 / 5 / 6 / 8 mm según parte más gruesa (≤ 6 / ≤ 12 / ≤ 20 / > 20 mm) | AWS D1.1/D1.1M:2020 | |
| Fatiga | N ≤ 20 000: clase de servicio 0, sin verificación; si no, F_SR = 6,895·(Cf/N)^(1/3) ≥ F_TH (Cat. F: exponente 1/6) | ASME BTH-1 §3-4; AISC 360-22 Apéndice 3, Ec. A-3-1, Tabla A-3.1 | Cf de la tabla en ksi, convertido a MPa |
| Pandeo del vástago | F_calado ≤ Pcr/3, Euler biarticulado con longitud extendida y diámetro del vástago | Criterio conservador frente a ISO/TS 13725 | Confirmar con ficha del cilindro |
| Giro | FS = F_calado/F_diseño ≥ 1,25; p_diseño ≤ alarma; gira con μ contaminado y con contacto en el borde | Criterio del proyecto | Revisión independiente M1 |
| Presión nominal del cilindro | p_alivio ≤ p_nominal (10.000 psi ≙ 700 bar; 5.000 psi ≙ 350 bar, convención de catálogo); p_alarma ≤ 0,90·p_alivio; p_retorno ≤ p_nominal | ISO 4413:2010 (protección contra sobrepresión) y catálogo del fabricante | Confirmado por el revisor del proyecto (02-11-2026) |
| Interfaz con discos de acero inoxidable (opción A) | Disco como placa circular empotrada sobre un vacío local con carga uniforme: σ = 3qa²/(4t²) ≤ 0,6Fy; t_req = t_flex + sobreespesor (≥ mínimo constructivo); espesor comercial. Dilatación diferencial y retención por fricción | Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy según AISC 360-22 F11 (criterio del proyecto); Fy según ASTM A240 | Pedido del mandante 04-11-2026. Ø de vacío, sobreespesor y μ son hipótesis de diseño; confirmar numeración en la edición vigente de Timoshenko |
| Interfaz con discos inoxidables y lámina UHMW (opción B) | Lámina: t ≥ E_ap·δ/(p_adm − q_máx), p_adm sostenida; PV, desgaste e juntas de dilatación | Datos de catálogo del proveedor de UHMW-PE (ASTM D4020) | Valores de partida: p_adm 5 MPa, E_ap 300 MPa, PV 0,05 MPa·m/s, μ 0,08 a 0,20; confirmar con ensayo del proveedor |
| Interfaz con placa de bronce con tapones de grafito (opción C) | Placa empotrada sobre un vacío local con ligamento entre tapones: σ = 3qa²/(4t²η) ≤ 0,6Fy_bz, η = (p − d)/p; presión sobre el bronce neto, PV, desgaste y profundidad del tapón; pareja con disco duro (ΔHB ≥ 100); retención por pegado; dilatación diferencial | Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy según AISC 360-22 F11 (criterio del proyecto); Fy según ASTM B584 / B148; PV y desgaste de catálogo del proveedor | Pedido del mandante 05-11-2026. Valores de partida: C95400 (Fy 170 MPa), p_adm 20 MPa, PV 0,5 MPa·m/s, k 10⁻⁶ mm³/N·m, μ 0,08 a 0,20; confirmar con el proveedor y con ensayo |
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

**Práctica normativa.** EN 982 fue reemplazada por EN ISO 4413:2010 (de memoria, B). Que el diseño prevea válvula de alivio térmico en un tramo que puede quedar aislado y calentarse es práctica habitual (Power & Motion, AIChE/CCPS), pero **no pude confirmar la cláusula de ISO 4413** ni de ninguna otra norma que lo exija. La prueba de presión de cilindros ISO 10100 es 1,5 × p_nominal (de memoria; no confirmado).

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

**Puntos a confirmar:** numeración exacta de ecuaciones de BTH-1 en la edición vigente; tabla de tamaño mínimo de filete en AWS D1.1:2020; todo lo enumerado en «No pude confirmar con fuente primaria» (sección Temperatura).

## Uña de empuje: material y excepción del criterio FU ≤ 0,90

| Ítem | Valor | Referencia | Decisión |
|---|---|---|---|
| Material | 34CrNiMo6+QT, Re ≥ 800 MPa para 40 < t ≤ 100 mm (bloque 198 × 88 × 110, t gobernante 88 mm) | EN 10083-3, tabla de propiedades +QT | Corrige el Fy = 900 MPa anterior, que ese acero no alcanza con 88 mm |
| Flexión en la boca del patín | FU 0,907 (antes 0,807 con 900 MPa) | ASME BTH-1 Cat. B, Nd = 3,0, §3-2.3 | Aceptada por el mandante el 07-11-2026 como advertencia (FU ≤ 1,0). El criterio interno FU ≤ 0,90 se relaja solo para esta fila |
| Otras filas de la uña | Corte en la boca 0,448; corte en el contacto 0,801; flexión en el chaflán 0,627 | BTH-1 §3-2.2 y §3-2.3 | Cumplen ≤ 0,90 |


## Leva de reenganche positiva (modo guiado)

Pedido del mandante 07-11-2026 (Tarea 1). El riel-leva fijo reemplaza la dependencia exclusiva del resorte; el resorte queda como apoyo. Hipótesis de geometría (no hay espacio lateral junto al patín: el patín ocupa x = x_g ± w_s/2 entre la mesa y el marco): el seguidor es un rodillo sobre un perno vertical fijo en la uña, que sale por una ranura de la tapa del alojamiento (la ranura lo guía en y); el riel es una pletina horizontal sobre el patín (entre la cara superior del patín + 2 mm y la cara superior de la mesa), apoyada en dos soportes empernados a la bancada prolongada en cada extremo, por fuera del recorrido del patín y por fuera del cuerpo del cilindro. Una pletina por cilindro: se voltea para el otro sentido de giro.

| Verificación | Criterio | Referencia | Ecuación / nota |
|---|---|---|---|
| Sincronía | holgura uña–pasador siguiente B con la uña apoyada en la rampa ≥ margen (cam_msync) | Geometría | Polígono de la uña (punta, chaflán β, cara trasera) frente al círculo de B; rampa a α desde η₀ + tramo, η₀ = −r − s_libre. Con s_libre = 10 mm no cabe la rampa (holgura < 0): s_libre pasa a 21 mm (carrera requerida 229,3 + 5 ≤ 235) |
| Bolsillo | máx u_nec ≤ recorrido de retorno Δx | Geometría | El bolsillo coincide con la zona de toma del pasador siguiente (B pasa a ser A): una leva posicional no distingue el sentido, de modo que en esa parte del empuje la uña queda con el resorte y el roce del alojamiento, como antes |
| Autobloqueo de la rampa | μ_ret·k_t·(sen α + μ_seg·cos α) < (cos α − μ_seg·sen α)·(1 − 2μ_ret·z_f/L_in) | Equilibrio de la cuña con fricción | k_t = 1 + 2(z_f − z_ranura)/h_uña (torsión de la uña por la fuerza del seguidor sobre la tapa); μ_seg = mu_roll (rodillo, familia 1) o el μ de la familia 2–4 |
| Fuerzas de atasco | cilindro tirando a p_ret con la uña trabada; cotas sin roce | Hidráulica | N_rampa = F_ret/sen α; N_toma = F_ret/tan β (chaflán sobre B a nivel de toma); F_ret = A_anular·p_ret |
| Contacto del rodillo | p₀ = √(q·E*/(π·r)) ≤ 1,67·Fy_sup, q = N/b | Hertz, contacto lineal; Tresca | Canto templado por inducción |
| Perno del seguidor | flexión N·l/(πd³/32) ≤ Fy/Nd; corte N/A ≤ Fy/(Nd√3) | ASME BTH-1 Cat. B §3-3.3, §3-2.3, §3-2.2 | l = altura del rodillo sobre la cara superior de la uña |
| Ranura de la tapa | F_ret/(d·t_tapa) ≤ 1,25·Fy_patín/Nd | ASME BTH-1 §3-3.3 | Aplastamiento |
| Riel-leva | N·k_M/(t·w_n²/6) + F_ret/(t·w_n) ≤ Fy/Nd, sección neta en el bolsillo | ASME BTH-1 §3-2.3 y §3-2.1 | Biapoyado entre soportes, carga en la peor posición del seguidor; 42CrMo4+QT (EN 10083-3, 16 < t ≤ 40: Re ≥ 750) |
| Soportes del riel | R_x·h/(l·b²/6) + R_y·h/(b·l²/6) ≤ Fy/Nd | ASME BTH-1 §3-2.3 | |
| Pórticos del riel (08-11-2026) | patas: (R_x/2)·h/(l·b²/6) + (R_y/2)·h/(b·l²/6) ≤ Fy/Nd; soldadura pata–asiento √[(M_x/S_x + M_y/S_y)² + (V/(a·2(b + l)))²] ≤ 0,60FEXX/(1,20Nd) | ASME BTH-1 §3-2.3, §3-3.4; AISC 360-22 §J2.4 | Reemplazan a los soportes empernados a la bancada: bajo el soporte trasero pasa el cuerpo del cilindro y no cabía un patrón de pernos con brazo de vuelco. Dos patas (x = x_g ∓ (D_cuerpo/2 + 5 + b/2)) soldadas a un asiento sobre la bancada prolongada y ensanchada; el riel lleva una aleta hacia adentro en la zona de apoyo (el seguidor no llega) |
| Pernos riel–pórtico | f_rv ≤ Fnv/Ω, Fnv = 0,45Fu (rosca incluida); aplastamiento R_n = 2,4·d·t·Fu, Ω = 2,00 | AISC 360-22 §J3.6, Tabla J3.2 (grupo 150 ≈ ISO 898-1 10.9); §J3.10 | Pernos verticales del riel a las tapas de las patas; sin tracción por vuelco (el pórtico la toma en las soldaduras) |
| Material del contacto | cam_mat = 0 → familia 1 en el modo guiado | Criterio del proyecto | Las familias 2–4 (zapata deslizante) se calculan, pero la rampa que exige la sincronía (~62°) se autobloquea con μ ≥ 0,15 y la presión de atasco supera p_adm |

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
| Bloque-uña | F/(b·h) + 6F·(e_cr + e)/(h·b²) ≤ Fy/Nd; corte 1,5·μ_s·F/(b·h) ≤ Fy/(Nd√3); pandeo F ≤ π²EI/(L_qp²·Nd); Hertz p₀ ≤ 1,67Fy_sup; horquilla en Q: aplastamiento 1,25Fy/Nd y desgarro | ASME BTH-1 §3-2.1, §3-2.2, §3-2.3, §3-3.3; Hertz | Cuerpo acodado e_cr hacia afuera para librar el pasador siguiente |
| Pasador Q | M = √[(F/2·(t/2 + g + b/4))² + (N_leva·l_Q)²] ≤ Fy/Nd·πd³/32; corte doble | ASME BTH-1 §3-3.3 | l_Q = horquilla inferior → mitad del espesor de la placa-leva |
| Ojal trasero E | pasador: flexión F/2·(t/2 + g + b/4), corte doble; tapas: aplastamiento (F/2)/(d·t) ≤ 1,25Fy/Nd, desgarro (F/2)/(2·t·a) ≤ Fy/(Nd√3) | ASME BTH-1 §3-3.3 | |
| Soporte del ojal E | cajón en U: F/2·(h_sup + h_inf)/S_U ≤ Fy/Nd; corte F/(2bt); soldadura √[(F/(4ba))² + (M/(a·b²))²] ≤ 0,60FEXX/(1,20Nd); filete mín./máx. | ASME BTH-1 §3-2.3, §3-2.2, §3-3.4; AISC 360-22 §J2.4, §J2.2b; AWS D1.1 Tabla 5.8 | Cajón centrado en E con ventana hacia la mesa (sección resistente en U) |
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
| Ligamento | σ = 6·(N·s/4)/(t·b²) ≤ Fy/Nd; τ = 1,5·(N/2)/(t·b) ≤ Fy/(Nd·√3); b = ligamento en el punto de carga | ASME BTH-1 §3-2.3, §3-2.2 | |
| Concentración de tensiones | K_t·σ_nom ≤ Fy (sin fluencia local), K_t = 1 + 2√(a/ρ) | Pilkey, Peterson's SCF Ec. 4.3 | BTH-1 no exige K_t en estática (material dúctil); la fatiga usa la categoría del detalle |
| Deformación | δ = N·s³/(48EI) + N·s/(4κGA) ≤ 0,1 mm | Viga de Timoshenko | No altera la sincronía |
| Tornillos | Grupo elástico (AISC Manual, Parte 7): V_i = F/n + M·r_i/Σr²; f_rv ≤ 0,45·Fu/2; aplastamiento en la placa con t_e = t − k/2 (k ≈ 0,56d) y en la base; tracción por vuelco con corte (J3.7); enganche de rosca 1,0·d ≤ t_base (8.8); distancia al borde (J3.4M); separación ≥ 3d (J3.3) | AISC 360-22 §J3.3, J3.4, J3.6, J3.7, J3.10; EN 1993-1-8 Tabla 3.4; VDI 2230-1 (orientativo) | ISO 10642 M16 8.8 (8 por placa) + 2 pasadores ISO 8734 Ø16 m6/H7 de posición |
| Fatiga | Recorte con radio ≥ 25 mm: categoría C; sección neta en agujeros: categoría D; rango con la carga de diseño, N = N_pin·vueltas·años | AISC 360-22 Apéndice 3, Tabla A-3.1 | |
| Vástago | Carga transversal: roce de los ojales E y Q (μ_E·F·d/2) y peso; la reacción de la placa no llega al vástago (miembro biarticulado de dos fuerzas). Flexocompresión a calado P_r/P_c + 8/9·B₁M_r/M_c ≤ 1 | AISC 360-22 §H1.1, §E3, Apéndice 8 | Fy del vástago y tipo de ojal: DATO DEL PROVEEDOR (hipótesis Fy = 520 MPa, μ = 0,20) |
| Topes soldados de la interfaz | Se dimensionan con máx(T_calado del empuje guiado; T_calado colineal de tmaxOf) | Criterio conservador | La colineal da el par mayor |

## Valor por defecto del accionamiento (08-11-2026)

Decisión del mandante: drive_mode = 2 (pivotado tipo KIET) es el valor por defecto; el guiado con leva de reenganche queda como alternativa (drive_mode = 1). Las pruebas del guiado fijan drive_mode = 1 y los verificadores independientes del accionamiento guiado (indep_tt300c, indep_accionamiento, indep_interfaz, indep_izaje_collar, indep_termica) comparan con tests/golden/tt300c_guiado.json.

Holguras geométricas del modo 2 (pedido del mandante: FU ≤ 0,95): el filete máximo del cajón del ojal baja a FU 0,913 (w = 21 mm). «Cajón del ojal E dentro de la base» (0,999) y «Q fuera de la mesa» (0,974) no pueden quedar ambos bajo 0,95 con B = 2.560: el cajón pide un R_E chico (≤ 1.515 mm con lado 260) y Q fuera de la mesa lo pide grande (≥ 1.645 mm). Con B = 2.760 la sugerencia de E (pv_fugeo = 0,95) da R_E = 1.645 mm, L_qp = 489 mm, FU 0,947 / 0,950, FS 1,456 y +162 kg. Queda para decisión del mandante (tamaño de la base).

## Tornillos avellanados del disco de la mesa (AF2)

Decisión del mandante 08-11-2026: en la opción A pegada (opt_ss = 1, fix_mode = 2) el par de la interfaz pasa del disco inoxidable de la mesa a la plancha inferior de la mesa con tornillos avellanados ISO 10642 clase 10.9 (M12 como punto de partida), roscados en la plancha.

| Verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Fuerza por tornillo | V = T_dis/(n·r) | Equilibrio | T_dis = par del caso de diseño; n automático = menor múltiplo del N° de ranuras radiales con FU ≤ 0,85; r = entre la ranura circunferencial exterior y el borde (cabeza a 5 mm de la ranura) |
| Corte del tornillo | V/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu (rosca en el plano de corte), Ω = 2,00 | AISC 360-22 §J3.6, Tabla J3.2 (grupo 150 ≈ 10.9) | A_b nominal |
| Aplastamiento en el disco | V ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 | AISC 360-22 §J3.10 Ec. J3-6a; EN 1993-1-8 Tabla 3.4 (espesor con avellanado) | Fu del inoxidable ASTM A240 304 = 515 MPa |
| Aplastamiento en la plancha de la mesa | V ≤ R_n/Ω con t = t_inf, Fu = 450 MPa | AISC 360-22 §J3.10 | Agujero roscado pasante |
| Separación | s = 2πr/n ≥ 3·d | AISC 360-22 §J3.3 | |
| Distancia al borde | R_o − r ≥ e_mín | AISC 360-22 §J3.4, Tabla J3.4M | La tabla empieza en M16; para M12 se toma 22 mm (conservador) |
| Avellanado | k + 0,5 + sobreespesor de relapeado ≤ t | ISO 10642 (k máx.); criterio del mandante | El disco de la mesa se dimensiona con este mínimo: con M12 pasa de 8 a 10 mm |
| Roscado | 1,25·d ≤ t_inf | VDI 2230 (orientativo, 10.9 en acero S355) | |
| Ranuras de engrase | holgura cabeza–ranura circunferencial ≥ 3 mm; tornillos a mitad de camino entre ranuras radiales | Geometría | |

## Cubierta de madera W (rebaje)

Decisión del mandante 08-11-2026: la mesa conserva el anillo superior R_reb…R (plancha superior actual en esa zona, con los N_pin pasadores); dentro de R_reb una plancha rebajada continua bajada t_madera, una pared cilíndrica en R_reb y los tablones enrasados con el anillo. Se elimina el anillo de contención 10×50 (la contención la da el escalón) y la altura total no aumenta. Supuestos por defecto: R_reb = 840, t_reb = t_pared = t_top = 20. Ajustes: t_madera 50 → 45 (con 50 el buje del pivote no cabe bajo la plancha rebajada, 142 > 140 mm, y la plancha inferior pasa de FU 0,90 por la menor altura del cajón; 45 mm = 2" cepillado y paso del parámetro); el anillo se fabrica en una pieza de espesor máx(t_pr, t_top) = 27 desde R_reb (la franja R840…R860 de 20 mm quedaría como un aro de 20 mm de ancho); w_pared = 8 mm (el filete exterior de refuerzo toca el anillo de 27 mm).

| Verificación | Criterio | Referencia | Nota |
|---|---|---|---|
| Plancha rebajada (local) | σvm FEA × k_malla ≤ 0,6Fy | AISC 360-22 F11 (criterio de la mesa) | Modelo escalonado desarrollado (abajo); envolvente de dos variantes |
| Flexión global del cajón | σ = M_glob/(t·h_c) + σ_local ≤ 0,6Fy, h_c = h_mesa − t_madera − (t_reb + t_bot)/2 | Placa sándwich axisimétrica (rev. M2) | Sin aporte de la madera. Comprobado con solución cerrada en tests/indep_madera.py |
| Pared en R_reb: flexión | σ = k_malla·σ_FEA + 6·(N_r·h_c + M_lat)/t² ≤ 0,6Fy | AISC 360-22 F11, como las planchas de la caja | N_r = M_r,glob(R_reb)/h_c (desvío del ala que cambia de nivel); M_lat = 3·(H/L_c)·h_c/16 (empuje de los tablones, viga empotrada-apoyada). Con ASME BTH-1 §3-2.3 (Fy/Nd) el FU sería ≈ 1,5: BTH-1 se aplica por analogía a la cadena de empuje, no a la caja de la mesa (fila 1 de este registro) |
| Pared en R_reb: corte | τ = 1,5·V/t ≤ 0,6Fy/1,50 | AISC 360-22 G2.1(a) | V = N_r + 11/16·H/L_c |
| Soldadura pared–plancha rebajada (J2) | 2 filetes: f = √[(M/(t·a))² + (V/(2a))²] ≤ 0,6FEXX/2,00 | AISC 360-22 J2.4 (como las soldaduras de la mesa) | Brazo = t_pared (conservador). Con BTH-1 §3-3.4 el FU sería ≈ 1,3 (informado en la fórmula) |
| Soldadura anillo–pared (J1) | PJP en bisel simple 45° desde el rebaje (S = t_pared/2, E = S − 3) + filete exterior: f = √[(M/(t·mín(a; E)))² + (V/(a + E))²] ≤ 0,6FEXX/2,00 | AISC 360-22 J2.1 (Tabla J2.1), J2.4 y Tabla J2.5 | El borde interior del anillo queda a ras con la cara interior de la pared: no hay rincón interior para filete. Geometría: S ≤ h_pared |
| Filetes mínimo y máximo | w_mín por la parte más gruesa (pared–plancha y pared–anillo); w ≤ t_pared − 2 | AWS D1.1/D1.1M:2020 Tabla 5.8; AISC 360-22 §J2.2b | El anillo de 27 mm pide 8 mm |
| Madera: aplastamiento ⊥ a la fibra | q = φd·W/(f_apoyo·A)·(1 + 4e/R_carga) ≤ p_madera·C_t; A = π·(mín(R_carga; R_tablones)² − R_abertura²) | Datos de proveedor; NDS 2018 Tabla 2.3.3 (C_t, escenario térmico) | Apoyo continuo de los tablones sobre la plancha rebajada: misma presión en la cara inferior |
| Madera: apoyo lateral contra la pared | σ = H/(L_c·t_madera) ≤ p_madera (⊥, conservador), H = k_hmad·φd·W, L_c = 2·mín(R_carga; R_tablones) | Equilibrio | k_hmad = 0,10 (empuje de skidding): supuesto C por confirmar |
| Fijación de los tablones | ISO 4762 M10 8.8 (o A4-70) con arandela ISO 7093 en cajeado (cabeza 3 mm bajo la superficie), roscado en taladro ciego de la plancha rebajada (remanente 3 mm); engrane ≥ 1,0·d con punta ≥ 2 mm antes del fin de la rosca útil; ≥ 2 filas por pieza a ≥ 7d de los extremos, ≤ 600 mm | ISO 4762, ISO 7093-1, VDI 2230 (orientativo), EN 1995-1-1 §8.5 (de memoria) | Reemplaza el tornillo Ø8×80 que no cabía en 50 + 20 mm (revisión de planos) |
| Holgura perimetral | (α⊥ − α_acero)·ΔT·2R_tablones ≤ 2·c_mad + (n − 1)·j_tab; w_pared + 2 ≤ c_mad | Termoelasticidad (α⊥ = 30×10⁻⁶, C) | La humedad queda pendiente |
| Fatiga de la pared | N = 2·vueltas/año·vida ≤ 20 000: clase de servicio 0 | AISC 360-22 Apéndice 3 A-3.1; ASME BTH-1 §3-4 | Con N > 20 000 el núcleo verifica Cat. E en el pie del filete |

**Modelo FEA escalonado.** La plancha rebajada, la pared y el anillo se resuelven como una placa MITC4 desplegada: la pared es una corona de ancho L_dev = L·(t_reb/t_pared)³ con w = 0 en sus dos extremos (alma de R_reb abajo; anillo rígido en su plano arriba) y continuidad de giro y momento (uniones rígidas); el anillo sigue con los radios desplazados L_dev y los pasadores como apoyos. Envolvente de dos variantes: «anillo» (L = distancia entre planos medios, anillo con pasadores modelado con t_reb: menor restricción del vano) y «empotrada» (L = altura libre, pared empotrada en el anillo: mayor momento en la pared). Validación: (1) tests/test_tt300c.js compara el constructor de malla (TT.stepPlate) en un caso axisimétrico con la solución cerrada de Kirchhoff por tramos (flecha 2 %, M_r 4 %); (2) tests/indep_madera.py resuelve la piel axisimétrica con la pared como viga y como cáscara cilíndrica: con la pared fija radialmente en sus dos extremos la rigidez circunferencial cambia los momentos menos de 0,1 % (efecto ∝ (βh)⁴, βh ≈ 0,4). fea.js no se modificó.

Pendientes: drenaje del rebaje (bandeja bajo los tablones), hinchamiento por humedad, pudrición y acabado; k_hmad del sistema de skidding; los pernos y arandelas de los pasadores sobresalen de la cara superior del anillo (como sin cubierta): la huella de la carga debe quedar dentro de R_tablones.
