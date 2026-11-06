# Lista de verificación para el revisor · TT300-C

Fecha de emisión: 06-11-2026 · Interfaz: Opción C-3: pastillas de bronce con tapones de grafito + disco duro

**ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.**

| N° | Plano | Título | Qué verificar | Contra qué cálculo |
|---|---|---|---|---|
| 1 | TT300C-GEN-001-B | NOTAS GENERALES, NORMAS Y ÍNDICE DE LÁMINAS | Advertencia obligatoria, notas de viento y anclaje, presión máxima de trabajo, normas, procedimiento de limpieza y engrase. | Decisiones del mandante; P.p_rated, p_relief, p_alarm; D['derivados'].tRev |
| 2 | TT300C-GEN-002-B | CONJUNTO GENERAL: PLANTA, CORTES Y VISTAS | Planta, corte A-A y datos técnicos coinciden con el núcleo (masa, WLL, presiones, altura total). | D['derivados'] (masas, Fstall, q_max); verificación «Altura total sobre el piso» |
| 3 | TT300C-GEN-003-B | ISOMÉTRICA EXPLOSIONADA CON GLOBOS | Todas las posiciones del despiece tienen globo; el sentido de montaje de cada pieza es coherente. | Despiece GEN-005; geometría del ensamble 3D |
| 4 | TT300C-GEN-004-B | SECUENCIA DE ENSAMBLAJE | Secuencia constructible: topes antes del rectificado, mesa izada por medios del montajista, cilindros al final. | Notas de la interfaz del núcleo (soldar topes antes del alivio); brecha de izaje de la mesa |
| 5 | TT300C-GEN-005-B | DESPIECE (LISTA DE MATERIALES), MASA Y CENTRO DE GRAVEDAD | Cantidades, materiales y masas; masa total y CG; diferencia con el núcleo dentro de la tolerancia o explicada. | D['derivados'].masas; verificaciones de materiales |
| 6 | TT300C-GEN-006-B | LISTA DE CORTE | Dimensiones brutas con sobremetal razonable y cantidades iguales al despiece. | Parámetros P (B, t_base, t_pr, d_pin, …) |
| 7 | TT300C-GEN-007-B | PROGRAMA DE SOLDADURAS (ISO 2553 / ISO 5817 / AWS D1.1) | Tipo, tamaño y END de cada soldadura; tamaños de P frente a los de las láminas; mínimos AWS donde P no fija. | Verificaciones «Soldaduras» y filetes de collar, orejas y topes (w_web, w_br, w_bed_f, w_collar, w_ear, w_tope) |
| 8 | TT300C-GEN-008-B | TOLERANCIAS, AJUSTES, MATERIALES E INSPECCIÓN | Ajustes ISO 286, tolerancias, materiales con certificado, puntos de inspección y torques A DEFINIR. | Registro de normas (docs/normas/registro.md); verificaciones de pasadores y uña |
| 9 | TT300C-GEN-009-B | SUPUESTOS DEL DIBUJANTE Y BRECHAS CON EL CÁLCULO | Supuestos de dibujo y decisiones adoptadas por el mandante; brechas abiertas (A DEFINIR): el calculista debe aceptarlas o corregir el cálculo. | Informe de brechas del paquete |
| 10 | TT300C-BAS-001-B | BASE SOLDADA: PLANCHA, COLLAR, MARCO, MÉNSULAS Y BANCADAS | Base soldada: B, t_base, marco, collar Ø D_boss × h_boss con agujero H7, bancadas, planitud 0,20, filetes. | P.B, t_base, rim_*, h_boss, D_boss; verificaciones «Pivote» (collar) y «Base» |
| 11 | TT300C-BAS-005-B | MÉNSULA DE CILINDRO (CONJUNTO SOLDADO) | Ménsula: L_ch, saliente trasera, luz Win, altura H, orejas H9, filetes w_br. | D['derivados'].bracket; verificaciones «Articulaciones» |
| 12 | TT300C-IZA-001-B | OREJA DE IZAJE (4 UNIDADES) | Oreja R92: e, 2R × h + semicírculo, Ø agujero, altura del centro, filete w_ear, ubicación, plano radial; nota de ramales (L ≥ d/cos 60°). | Verificaciones «Orejas de izaje» (AISC D5.2, filetes mínimo y máximo, ramales) y «Base» (izaje) |
| 13 | TT300C-ACC-001-B | BANCADA DE GUÍA CON RANURA T | Bancada: ancho, espesor, ranura T (cuello H8, cabeza), fondo, largo L_bed. | D['derivados'].K (L_bed, Y_bed); P.w_slot, h_slot, w_tee, h_tee |
| 14 | TT300C-ACC-002-B | PATÍN GUIADO CON LENGÜETA T Y MARCO DE BOCA | Patín: L_s, w_s, lengüeta T, alojamiento de la uña, marco de boca e = t_fw. | D['derivados'].K; verificaciones «Patín y guía» |
| 15 | TT300C-ACC-003-B | UÑA DE EMPUJE (CARA PLANA TEMPLADA, CHAFLÁN DE RETORNO) | Uña: largo, b, h, chaflán de retorno β, temple por inducción ≥ 55 HRC (Fy_sup), alivio de borde 10 mm con cota (k_edge). | Verificaciones «Uña» (Hertz con k_borde, profundidad de temple); P.Fy_surf, P.k_edge |
| 16 | TT300C-ACC-004-B | PASADORES DE ARTICULACIÓN, CILINDRO HIDRÁULICO Y ESPECIFICACIÓN | Pasadores de articulación f8, cilindro (Ø, carrera, presión de trabajo), circuito. | P.D_bore, d_rod, stroke, p_rated; verificaciones «Articulaciones» |
| 17 | TT300C-MES-001-B | MESA GIRATORIA: CONJUNTO SOLDADO (PLANTA Y CORTE RADIAL) | Mesa: Ø, altura, almas, nervios, pasadores (PCD, paso), corte radial. | P.D_top, h_disc, rings, N_rib, N_pin, R_pin; verificaciones «Mesa» |
| 18 | TT300C-MES-002-B | PLANCHAS Y ANILLOS DE LA MESA (SUPERIOR E INFERIOR) | Planchas y anillos: espesores t_top, t_bot, t_pr, agujero Ø200, rebaje Ø240, agujero pasante Ø D_rebaje_bot (collar + 2 c_boss_r), agujeros de pasadores. | Verificaciones «Mesa (FEA)»; P.t_top, t_bot, t_pr |
| 19 | TT300C-MES-003-B | CUBO, ALMAS ANULARES Y NERVIOS RADIALES | Cubo con rebaje inferior Ø D_rebaje × h_rebaje_cubo (holguras c_boss_r, c_boss_a); almas y nervios (largos de tramo; anillos del JSON). | interfazGeom (D_rebaje_bot, h_rebaje_cubo); verificación del collar «pared del rebaje ≥ 25 mm»; masas de almas y nervios |
| 20 | TT300C-MES-004-B | PASADOR DE EMPUJE Y PERNO DE RETENCIÓN | Pasador Ø85 m6 × h_disc, temple por inducción ≥ 55 HRC (Fy_sup), alivio de borde, perno M20. | Verificaciones «Pasadores de empuje»; P.Fy_surf, P.k_edge |
| 21 | TT300C-PIV-001-B | PIVOTE, BUJE, TAPA RETENEDORA Y TAPA DE INSPECCIÓN | Pivote, buje, tapas: asiento t_base + h_boss, buje desde t_base + h_boss + g_buje, holguras reales del collar (radial c_boss_r, axial al techo), brazo e = 42, ajustes p6/H7. | Verificaciones «Pivote» (asiento, brazo efectivo, buje, flexión, rebaje del collar) |
| 22 | TT300C-INT-001-B | INTERFAZ C (BRONCE): CONJUNTO Y CORTE | Capas de la interfaz y alturas (Δ); topes, tornillos y ranuras según la alternativa; NO desmontable si fix_mode = 2. | D['apoyo'].interfaz; D['interfazChecks']; verificaciones «Interfaz inox/bronce» |
| 23 | TT300C-INT-002-B | INTERFAZ C (BRONCE): SECTORES | Sectores: ángulo, juntas, muescas, tornillos, ranuras de engrase, rugosidad y planitud. | P.n_sec, d_tor, h_gr, w_gr, n_gr_rad, n_gr_circ; verificaciones de sector y tornillo |
| 24 | TT300C-INT-003-B | INTERFAZ: BARRAS DE TOPE, TORNILLOS, ENGRASE Y ESPECIALES | Barras de tope: L, b_tope, h = t − a_sup, a_inf, h_c, w_tope ≥ w_mín; secciones A-A/B-B(/C-C en B); tornillos ISO 10642, graseras, UHMW/bronce con tapones. | interfazGeom.topes (geometría resuelta) y verificaciones de tope «alivio inferior», «filete dentro de la altura de barra», «filete mínimo» |

## Verificaciones transversales
- Todas las láminas llevan la advertencia obligatoria, cajetín completo, estado «EMITIDO PARA REVISIÓN» y tabla de revisiones.
- Cotas verificadas automáticamente contra el modelo 3D: ver `chequeo_cotas.csv` y el informe del paquete.
- Masas 3D frente al núcleo, centro de gravedad e interferencias: ver `informe_paquete.md`.
- Supuestos S## y brechas B-## de GEN-009: aceptar o corregir antes de aprobar.