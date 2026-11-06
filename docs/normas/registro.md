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
