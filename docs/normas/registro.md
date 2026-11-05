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

**Puntos a confirmar:** numeración exacta de ecuaciones de BTH-1 en la edición vigente; tabla de tamaño mínimo de filete en AWS D1.1:2020.
