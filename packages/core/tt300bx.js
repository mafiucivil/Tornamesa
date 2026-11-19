/* TT300-BX · Módulo aparte del núcleo TT300-C (16-11-2026): tornamesa con interfaz de giro simplificada para fabricar con plasma y soldadura.
   - Disco inoxidable macizo Ø D_top atornillado a la plancha inferior de la mesa con tornillos avellanados ISO 10642 (cabeza bajo la cara con el
     sobreespesor de desgaste), fabricado en dos semidiscos cortados con plasma y unidos con una CJP a tope esmerilada a ras (AWS D1.6). No hay disco en la base.
   - Portador de plancha de acero cortado con plasma, soldado a la plancha base, con agujeros circulares; en cada agujero una pastilla de UHMW-PE
     a presión, apoyada en la base, que sobresale h_p y se retiene con un tornillo avellanado a la base. El disco de la mesa desliza sobre las pastillas.
   Reutiliza TODO el motor de tt300c.js (cinemática, accionamiento, FEA de la mesa, casos de giro, térmica, masas): el núcleo recibe la geometría ya
   dimensionada por el gancho aditivo P.__bx (opción B, opt_uhmw = 1); sin P.__bx el núcleo no cambia. Este archivo agrega el dimensionamiento,
   las verificaciones propias (grupo «Interfaz inox», formato de tt300c) y la tabla de fabricación.
   Unidades internas N, mm, MPa; salida en kN, kN·m, kg y bar. Sin dependencias: navegador (TT global) o Node (require). */
const BX = (() => {
  const TT_ = (typeof TT !== "undefined") ? TT : require("./tt300c.js");
  const G = TT_.G, D2R = Math.PI / 180;
  const RHO = 7.85e-6, AL_S = 11.7e-6, E_BOLT = 205000, NU_UH = 0.45;
  const SS_COMM = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25];                   // plancha inoxidable (como el núcleo)
  const CS_COMM = [8, 10, 12, 15, 16, 20, 25, 30];                            // plancha de acero al carbono para el portador
  const ISO10642_K = { 3: 1.86, 4: 2.48, 5: 3.1, 6: 3.72, 8: 4.96, 10: 6.2, 12: 7.44, 14: 8.4, 16: 8.8, 20: 10.16 };   // altura máx. de la cabeza (núcleo)
  const ISO10642_DK = { 3: 6, 4: 8, 5: 10, 6: 12, 8: 16, 10: 20, 12: 24, 14: 27, 16: 30, 20: 36 };
  const ISO10642_L = [8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100];
  const PITCH = { 5: 0.8, 6: 1, 8: 1.25, 10: 1.5, 12: 1.75, 14: 2, 16: 2, 20: 2.5 };
  const isoK = (d) => ISO10642_K[Math.round(d)] || 0.62 * d, isoDk = (d) => ISO10642_DK[Math.round(d)] || 2 * d, pitchOf = (d) => PITCH[Math.round(d)] || 0.15 * d;
  const J34M = (d) => d <= 16 ? 22 : d <= 20 ? 26 : d <= 22 ? 28 : d <= 24 ? 30 : d <= 27 ? 34 : d <= 30 ? 38 : 46;   // AISC 360-22 Tabla J3.4M (M16 para menores, como el núcleo)
  const wMinAWS = (T) => T <= 6 ? 3 : T <= 12 ? 5 : T <= 20 ? 6 : 8;    // AWS D1.1/D1.1M:2020 Tabla 7.7 (parte más gruesa)
  const wMaxJ = (t) => t < 6 ? t : t - 2;                               // AISC 360-22 §J2.2b (borde de plancha)
  const nf = (v, d) => (isFinite(v) ? (+v).toFixed(d == null ? 2 : d) : String(v)).replace(".", ",");
  const ACC_GRPS = ["Pasadores de empuje", "Uña", "Patín y guía", "Articulaciones", "Fatiga", "Leva de reenganche", "Soporte del ojal E", "Placas-leva"];   // como el núcleo
  const GRP = "Interfaz inox";
  const REFU = "Proveedor de UHMW-PE: Plastigen ULTRA VST (ficha: UHMW 9×10⁶ g/mol, densidad 0,97, Shore D 63, uso hasta 90 °C; sin p_adm, E, μ, PV ni α: se mantienen los supuestos del proyecto, PENDIENTE DATO DEL PROVEEDOR); ASTM D4020; confirmar con ensayo";
  const REG = "docs/normas/registro.md, «TT300-BX: disco inoxidable atornillado y pastillas de UHMW (16-11-2026)»";

  /* ---------------- Parámetros propios (se suman a los del núcleo) ---------------- */
  const BX_GROUP = { id: "bx", t: "TT300-BX · disco inoxidable (modo 1: lámina 3 mm soldada; modo 0: disco atornillado) y pastillas de UHMW en portador soldado a la base", p: [
    ["bx_disc_modo", "Disco: modo. 1 = lámina inoxidable 304 acabado espejo de 3 mm (única plancha espejo del proveedor) en paneles del formato comercial con juntas a tope, SOLDADA a la plancha inferior de la mesa con tapones (plug) distribuidos y costura perimetral, sin tornillos (por defecto: decisión del mandante 18-11-2026); 0 = disco macizo atornillado con ISO 10642 (2 semidiscos con CJP; revisiones 1–4)", "–", 1, 0, 1, 1],
    ["bx_t_lam", "Lámina (modo 1): espesor de la plancha espejo del proveedor", "mm", 3, 1.5, 4.8, 0.5],
    ["bx_fmt_a", "Lámina (modo 1): formato comercial de la plancha espejo, ancho (por defecto el mayor, 1500 × 3000; alternativa típica 1219 × 2438)", "mm", 1500, 900, 2000, 1],
    ["bx_fmt_b", "Lámina (modo 1): formato comercial de la plancha espejo, largo", "mm", 3000, 1800, 6000, 1],
    ["bx_c_lam", "Lámina (modo 1): retiro del borde de la lámina respecto de R_o y R_i (asiento del filete perimetral sobre la plancha de la mesa)", "mm", 8, 4, 30, 1],
    ["bx_d_tap", "Lámina (modo 1): Ø del agujero de los tapones (AISC 360-22 §J2.3a: t + 8 ≤ Ø ≤ máx(Ø_mín + 3; 2,25·t); AWS D1.3 y AISI S100 §J2.2: Ø visible ≥ 9,5)", "mm", 14, 9.5, 20, 0.5],
    ["bx_s_tap", "Lámina (modo 1): paso circunferencial de los tapones (0 = automático: el mayor que cumple FU ≤ 0,90)", "mm", 0, 0, 400, 5],
    ["bx_w_lam", "Lámina (modo 1): filete de la costura perimetral exterior e interior a la plancha de la mesa (AISC §J2.2b: w ≤ t con t < 6 mm)", "mm", 3, 2, 4.8, 0.5],
    ["bx_FEXX_ss", "Lámina (modo 1): FEXX del aporte disímil inox–carbono E309L-16 / ER309L (AWS A5.4: E309L ≥ 520 MPa; ER309L de AWS A5.9 sin mínimo: se toma el del electrodo)", "MPa", 520, 400, 700, 5],
    ["bx_g0", "Lámina (modo 1): separación máxima lámina–plancha después de soldar (galga en ventana Ø vacío local y entre tapones; requisito de fabricación e inspección)", "mm", 0.2, 0.05, 1, 0.05],
    ["bx_pul", "Lámina (modo 1): material retirado al esmerilar a ras y pulir tapones y juntas (se descuenta del sobreespesor ss_allow)", "mm", 0.2, 0, 1, 0.05],
    ["bx_c_pista", "Lámina (modo 1): holgura radial del borde de los tapones a la pista que barren las pastillas", "mm", 2, 0, 10, 0.5],
    ["bx_ss_mat", "Disco: material. 1 = inoxidable austenítico 304/316L (Fy_ss y Fu_ss del núcleo; α = 17,3×10⁻⁶/K); 2 = dúplex 2205 (UNS S32205, ASTM A240; α ≈ 13,0×10⁻⁶/K). Revisión del mandante 16-11-2026: 304", "–", 1, 1, 2, 1],
    ["bx_al_st", "Acero al carbono de la mesa: α para la dilatación diferencial con el disco (revisión del mandante: 12; Δα = 17,3 − 12 = 5,3×10⁻⁶/K con 304)", "×10⁻⁶/K", 12, 10, 14, 0.1],
    ["T_ifc_max", "Interfaz de giro: temperatura máxima de servicio (ambiente; revisión del mandante 17-11-2026: 20 °C de uso; antes 50 °C; los 80 °C son del sello hidráulico)", "°C", 20, 20, 80, 1],
    ["T_ifc_min", "Interfaz de giro: temperatura mínima de servicio (ambiente)", "°C", 0, -40, 20, 1],
    ["bx_Fy_dx", "Disco dúplex 2205: Fy (ASTM A240 S32205: 450)", "MPa", 450, 300, 700, 5],
    ["bx_Fu_dx", "Disco dúplex 2205: Fu (ASTM A240 S32205: 655)", "MPa", 655, 500, 900, 5],
    ["bx_t_ss", "Disco: espesor (0 = automático: el mayor entre cabeza avellanada + sobreespesor, flexión entre pastillas y sobre el vacío local)", "mm", 0, 0, 25, 1],
    ["bx_d_tss", "Disco: Ø de los tornillos avellanados ISO 10642 clase 10.9 disco–mesa", "mm", 10, 6, 16, 1],
    ["bx_s_tss", "Disco: paso de la malla de tornillos (0 = automático: el mayor que cumple FU ≤ 0,90 con par y dilatación)", "mm", 0, 0, 400, 5],
    ["bx_c_cjp", "Disco: franja libre de tornillos a cada lado del eje de la CJP entre semidiscos (cordón, ZAC y esmerilado)", "mm", 30, 10, 100, 5],
    ["bx_c_alma", "Disco: holgura entre el agujero roscado de la mesa y el pie del filete de almas, nervios y cubo", "mm", 3, 0, 20, 1],
    ["bx_forma", "Pastillas: forma. 0 = redondas (por defecto: decisión del mandante, revisión 4 del 16-11-2026; patrón bx_pat); 1 = cuadradas con esquinas redondeadas en malla cartesiana (revisión 3: no cumplía)", "–", 0, 0, 1, 1],
    ["bx_borde", "Pastillas cuadradas en el borde de la corona: 1 = recortadas por el círculo (pastilla y agujero con el contorno R_o − lig y R_i + lig, cortados igual por plasma y router); 0 = solo pastillas enteras (la franja queda con el portador)", "–", 1, 0, 1, 1],
    ["bx_fmin", "Pastillas recortadas: fracción mínima del cuadrado (las menores no se ponen)", "–", 0.35, 0.1, 0.9, 0.05],
    ["bx_rc", "Pastillas cuadradas: radio de esquina del agujero del portador (0 = automático: máx(5; 0,5·t_portador), radio mínimo del plasma HD, criterio de taller); la pastilla lleva r + 1 (apoya en las caras, no en las esquinas)", "mm", 0, 0, 40, 0.5],
        ["bx_pat", "Pastillas redondas: patrón. 0 = automático (el de menor FU entre los dos); 1 = triangular (hexagonal) anclado al centro con un anillo en cada borde y relleno de la franja de unión; 2 = radial: anillos concéntricos repartidos entre el borde exterior y el interior a paso ≥ s", "–", 0, 0, 2, 1],
    ["bx_mu_base", "Pastillas: μ de límite inferior de la cara inferior del UHMW contra la plancha base de acero seca y desengrasada (toma parte del arrastre: el residual (μ_top,máx − μ_b)·N va a la pared y al tornillo). Supuesto 0,10: límite inferior del rango de μ de UHMW sobre acero seco de las fichas de fabricante (p. ej. TIVAR 1000, Mitsubishi Chemical: 0,10–0,20, ASTM D1894), confianza C", "–", 0.10, 0, 0.3, 0.01],
    ["bx_mu_base_on", "Pastillas: camino del arrastre por la cara inferior (1 = sí, con μ_b; 0 = la pared toma todo)", "–", 1, 0, 1, 1],
    ["bx_dp", "Pastillas: Ø (0 = automático, con Ø de corte ≤ bx_dp_max)", "mm", 0, 0, 250, 5],
    ["bx_dp_max", "Pastillas: Ø de corte máximo (se cortan de cuadrados de bx_cuad_uh del proveedor; decisión del mandante 18-11-2026: Ø ≤ 185)", "mm", 185, 60, 300, 1],
    ["bx_cuad_uh", "Pastillas: lado de los cuadrados de UHMW del proveedor de los que se cortan (ULTRA VST 190 × 190)", "mm", 190, 60, 400, 1],
    ["bx_rho_uh", "UHMW: densidad (ULTRA VST, ficha Plastigen: 0,97; antes 0,94)", "g/cm³", 0.97, 0.9, 1, 0.01],
    ["bx_tc", "Portador: espesor de la plancha (rev. 6/7, decisión del mandante 18-11-2026: 22 mm de A572 Gr. 50 fijo; rev. 5: 25 mm de A36; 0 = automático)", "mm", 22, 0, 40, 1],
    ["Fy_bxc", "Portador: Fy del acero (rev. 7: 0 = el global, A572 Gr. 50; rev. 6: 345)", "MPa", 0, 0, 690, 5],
    ["Fu_bxc", "Portador: Fu del acero (rev. 7: 0 = el global; rev. 6: 450)", "MPa", 0, 0, 800, 5],
    ["Fy_pr", "Calidad por pieza: Fy de los anillos de pasadores superior e inferior (rev. 7: 0 = el global, A572 Gr. 50; rev. 6: 345)", "MPa", 0, 0, 690, 5],
    ["Fu_pr", "Calidad por pieza: Fu de los anillos de pasadores (rev. 7: 0 = el global; rev. 6: 450)", "MPa", 0, 0, 800, 5],
    ["bx_mesa_entera", "Mesa: planchas superior e inferior de UNA pieza por nivel (rev. 7c, decisión del mandante 19-11-2026). 1 = plancha completa Ø D_top × t con los N_pin agujeros Ø d_pin H7 de los pasadores en la misma pieza (exige t_pr = t_top = t_bot; sin anillo de pasadores, sin empalmes CJP de segmentos y sin unión plancha–anillo); 0 = disco Ø 2·R_anillo,int + anillo de pasadores en 4 segmentos de 90° con empalmes CJP y unión soldada plancha–anillo (revisiones anteriores)", "–", 1, 0, 1, 1],
    ["Fy_base", "Calidad por pieza: Fy de la plancha base (rev. 7: 0 = el global, A572 Gr. 50; rev. 6: 345). Con el refuerzo de esquina o el collar (globales) se usa la menor", "MPa", 0, 0, 690, 5],
    ["Fu_base", "Calidad por pieza: Fu de la plancha base (rev. 7: 0 = el global; rev. 6: 450)", "MPa", 0, 0, 800, 5],
    ["Fy_boxE", "Calidad por pieza: Fy del soporte del ojal E: paredes traseras, muñones y tapas superior e inferior (rev. 7: 0 = el global, A572 Gr. 50; rev. 6: 345). CJP de las paredes sobre el refuerzo: la menor", "MPa", 0, 0, 690, 5],
    ["Fu_boxE", "Calidad por pieza: Fu del soporte del ojal E (rev. 7: 0 = el global; rev. 6: 450)", "MPa", 0, 0, 800, 5],
    ["Fy_dbl", "Calidad por pieza: Fy del refuerzo de esquina BAS-030 y del atiesador tangencial (0 = el global: rev. 7 A572 Gr. 50 con calidad Z ASTM A770)", "MPa", 0, 0, 690, 5],
    ["Fu_dbl", "Calidad por pieza: Fu del refuerzo de esquina y del atiesador (0 = el global)", "MPa", 0, 0, 800, 5],
    ["bx_lig", "Portador: ligamento mínimo entre agujeros (rev. 7b, decisión del mandante 18-11-2026: 50 mm, más acero en el portador — 44 pastillas en vez de 67; 0 = automático: máx(10; t_portador), criterio de taller para corte por plasma)", "mm", 50, 0, 60, 1],
    ["bx_nw", "Portador: unión a la base. 0 = solo filetes perimetrales exterior e interior (por defecto: el portador lleva el par a torsión hasta sus bordes); ≥ 1 = además agujeros de soldadura con filete interior en lugar de algunas pastillas (1: los elige la regla de un salto; 7: subred √7 o cada 7.ª posición del anillo, completada con la regla de un salto)", "–", 0, 0, 13, 1],
    ["bx_w_h", "Portador: filete interior de los agujeros de soldadura (agujero del mismo Ø que el de las pastillas, filete en todo el contorno a la base, sin pastilla)", "mm", 6, 3, 16, 1],
    ["bx_hp", "Pastillas: saliente sobre el portador (0 = automático)", "mm", 0, 0, 40, 0.5],
    ["bx_hp_max", "Pastillas: saliente máximo de la búsqueda automática", "mm", 20, 3, 40, 1],
    ["bx_g_min", "Holgura mínima disco–portador al final de la vida (descontados desgaste, fluencia, planitud y flecha entre pastillas)", "mm", 1, 0.5, 5, 0.5],
    ["bx_tol_h", "Portador: tolerancia ± del Ø de los agujeros (plasma de alta definición; criterio de taller por confirmar)", "mm", 0.3, 0.05, 1, 0.05],
    ["bx_tol_p", "Pastillas: tolerancia ± del Ø de corte (router CNC o chorro de agua desde plancha: 0,2, criterio de taller por confirmar; torneado: 0,05)", "mm", 0.2, 0.01, 0.5, 0.01],
    ["bx_H_uh", "Pastillas: espesor de la plancha comercial de UHMW de la que se cortan (decisión del mandante 18-11-2026: ULTRA VST de 30 mm fija; 0 = automático entre 20, 25, 30, 40 y 50 mm); saliente = espesor − t_portador", "mm", 30, 0, 60, 1],
    ["bx_tol_H", "Pastillas: variación de espesor entre pastillas de la misma plancha calibrada (se suma a d_flat; supuesto, confianza C)", "mm", 0.05, 0, 0.5, 0.01],
    ["bx_i", "Pastillas: interferencia diametral nominal (0 = automática: la menor que retiene a 20 °C y cumple en frío y en caliente)", "mm", 0, 0, 3, 0.05],
    ["bx_E_ct", "UHMW: módulo a corto plazo para el ajuste a presión (ficha 600–800, confianza C)", "MPa", 700, 200, 1500, 10],
    ["bx_eps_max", "Pastillas: deformación radial máxima por interferencia a T_máx (criterio del proyecto: el ajuste relaja por fluencia; la retención la da el tornillo)", "%", 2.5, 0.5, 10, 0.1],
    ["bx_al_uh", "UHMW: coeficiente de dilatación (×10⁻⁶/K; valor del mandante 190)", "–", 190, 100, 250, 1],
    ["bx_Tmin", "Pastillas: temperatura mínima de almacenaje para el ajuste en frío", "°C", -10, -40, 20, 1],
    ["bx_Tmax", "Temperatura de la limitación de uso informativa (sello hidráulico; no es de la interfaz)", "°C", 80, 20, 120, 1],
    ["bx_d_sp", "Pastillas: Ø del tornillo avellanado ISO 10642 clase 8.8 (zinc laminar) que las retiene a la base (rev. 7b: M12, el M10 no alcanza al corte con 44 pastillas; base de 22 mm: taladro ciego con engrane ≥ 1,0·d; M10: con la base de 20 mm el taladro ciego admite el engrane ≥ 1,0·d; M12 no)", "mm", 12, 5, 12, 1],
    ["bx_c_sp", "Pastillas: holgura radial del agujero del tornillo en la pastilla", "mm", 1, 0.25, 3, 0.25],
    ["bx_u_min", "Pastillas: UHMW mínimo bajo la cabeza del tornillo (criterio del proyecto)", "mm", 3, 1, 10, 0.5],
    ["bx_Fu_sp", "Tornillos de las pastillas: Fu (ISO 898-1 clase 8.8: 800)", "MPa", 800, 400, 1200, 10],
    ["bx_w_c", "Portador: filete perimetral (borde exterior e interior) a la base (AWS D1.1 Tabla 7.7: con el portador o la base de 20–25 mm, mínimo 8)", "mm", 8, 3, 16, 1],
    ["bx_bow", "Portador: falta de planitud admitida después de soldar (solo bordes soldados; criterio de taller): se descuenta de la holgura disco–portador", "mm", 1, 0, 5, 0.5],
  ] };
  const PARAM_GROUPS = TT_.PARAM_GROUPS.concat([BX_GROUP]);   // + CYL_GROUP (más abajo)
  // Rev. 5 (decisión del mandante 18-11-2026): acero ASTM A36 (Fy 250, Fu 400) en TODAS las planchas estructurales (mesa, base y su refuerzo y atiesadores,
  // soporte del ojal E, collar del pivote, portador, orejas…; parámetros «Fy»/«Fu» del núcleo, que solo usan planchas: comprobado fila por fila) y los
  // espesores comerciales que hacen falta con A36. Los aceros especiales (pasadores, bloque-uña, placa-guía, leva, pivote, vástago, tornillos) tienen su propio
  // parámetro y no cambian. «antes» = valores del núcleo (A572 Gr. 50): BX.defaults({ a36: false }) los conserva como opción.
  // Rev. 6 (decisión del mandante 18-11-2026): calidad de acero POR PIEZA. ASTM A572 Gr. 50 (Fy 345, Fu 450; parámetros Fy_pr/Fu_pr, Fy_base/Fu_base,
  // Fy_boxE/Fu_boxE del grupo BX, que el núcleo lee con fyOf/fuOf, y Fy_bxc/Fu_bxc del portador): anillos de pasadores t_pr = 22, plancha base t_base = 22,
  // soporte del ojal E (paredes traseras y muñones pv_tbox = 25, tapas pv_tl = 25) y portador bx_tc = 22. ASTM A36 (Fy 250, Fu 400; el global Fy/Fu): todo
  // el resto con los espesores de la rev. 5 (mesa 25/20, almas y nervios 8, refuerzo de esquina con su espesor automático, atiesador 30, collar 70, orejas…).
  // Filas con piezas de distinta calidad: la menor (base + refuerzo, base + collar, CJP de las paredes E sobre el refuerzo; ver tt300c.js, fyOf).
  // Rev. 7 (decisión del mandante 18-11-2026, reemplaza a la rev. 6 como valores por defecto): capacidad 290 t, alivio 680 bar (alarma 600); TODAS las
  // planchas estructurales en ASTM A572 Gr. 50 (global Fy/Fu = 345/450; claves por pieza en 0 = global, siguen disponibles); planchas de la mesa, anillos,
  // base, portador, paredes y tapas del cajón E y atiesador tangencial (clave rib_t del núcleo) de 22 mm; almas y nervios 8, collar 70, refuerzo de
  // esquina automático. El nombre A36_DESPUES / BX.A36 se conserva por compatibilidad (bloque «después» de los valores del núcleo).
  const A36_DESPUES = { W_tf: 290, p_relief: 680, p_alarm: 600, Q_pump: 8, Fy: 345, Fu: 450, t_top: 22, t_bot: 22, t_web: 8, t_rib: 8, w_web: 8, t_pr: 22, t_base: 22, h_boss: 70, pv_tl: 22, pv_tbox: 22, rib_t: 22 };
  const A36 = { despues: A36_DESPUES, antes: (() => { const D = TT_.defaults(), o = {}; for (const k in A36_DESPUES) o[k] = D[k]; return o; })(),
    nota: { W_tf: "capacidad nominal 290 t (rev. 7)", p_relief: "alivio 680 bar (rev. 7)", p_alarm: "alarma 600 bar", rib_t: "atiesador tangencial del refuerzo de esquina de 22 mm (rev. 7; núcleo: 30)", Fy: "A572 Gr. 50 en todas las planchas (rev. 7; rev. 5/6: A36 global)", Fu: "A572 Gr. 50", t_top: "plancha superior de la mesa (FEA global + local)", t_bot: "plancha inferior de la mesa (FEA global + local)", t_web: "almas: el filete mínimo con la plancha de 25 (AWS D1.1 T7.7: 8) no cabe en un alma de 6", t_rib: "nervios: ídem", w_web: "filete almas/nervios–planchas (T > 20: 8)",
      t_pr: "anillos de pasadores (rev. 6: A572 Gr. 50, 22 mm; el anillo superior queda de máx(t_pr, t_top) = 25): aplastamiento del agujero del pasador de empuje", t_base: "plancha base (rev. 6: A572 Gr. 50, 22 mm; bajo el soporte del ojal E; asiento del pivote)", h_boss: "collar de asiento del pivote (profundidad del asiento con H·e)", pv_tl: "tapas del cajón del ojal E (rev. 6: A572 Gr. 50, 25 mm; rev. 5: A36, 36 mm): desgarro y aplastamiento", pv_tbox: "paredes traseras y muñones del soporte del ojal E (rev. 6: A572 Gr. 50, 25 mm)" } };
  function defaults(o) {
    const P = TT_.defaults();
    BX_GROUP.p.forEach((q) => { P[q[0]] = q[3]; });
    if (!(o && o.a36 === false)) Object.assign(P, A36_DESPUES);
    CYL_GROUP.p.forEach((q) => { P[q[0]] = q[3]; });
    if (!(o && o.cyl === false)) Object.assign(P, CYL_CORE); else P.bx_cyl_on = 0;   // rev. 7d: cilindro fabricado (vástago Ø65 cromado común, c_rod y m_cyl del cuerpo resultante)
    return Object.assign(P, { opt_uhmw: 1, opt_ss: 0, opt_bz: 0 });
  }
  const bxDefaults = () => Object.fromEntries(BX_GROUP.p.concat(CYL_GROUP.p).map((q) => [q[0], q[3]]));
  const ifOpt = (P) => P.opt_bz > 0.5 ? 3 : (P.opt_uhmw > 0.5 ? 2 : (P.opt_ss > 0.5 ? 1 : 0));
  const active = (P) => ifOpt(P) === 2;
  const lamOn = (P) => Math.round(P.bx_disc_modo == null ? 1 : P.bx_disc_modo) === 1;   // modo 1: lámina de 3 mm soldada (por defecto)
  const meOn = (P) => Math.round(P.bx_mesa_entera == null ? 1 : P.bx_mesa_entera) === 1;   // rev. 7c: mesa de plancha entera por nivel (por defecto)
  const meOk = (P) => P.t_pr === P.t_top && P.t_top === P.t_bot;                              // la plancha entera tiene un solo espesor
  const meMsg = (P) => "TT300-BX: mesa de plancha entera (bx_mesa_entera = 1) exige t_pr = t_top = t_bot (una sola plancha por nivel con los agujeros de los pasadores); hay t_pr = " + P.t_pr + ", t_top = " + P.t_top + ", t_bot = " + P.t_bot + " mm. Iguale los espesores o use bx_mesa_entera = 0 (disco + anillo de pasadores en segmentos)";
  // Bloque «mesa» del JSON (generador de planos): plancha entera por nivel o disco + anillo. Las masas del núcleo (massesMesa) ya suman el disco Ø 2·R_anillo,int
  // (t_top / t_bot) y la corona R_anillo,int…R (máx(t_pr, t)) sin traslape: con t_pr = t_top = t_bot son exactamente las de la plancha entera (sin doble conteo).
  function mesaOf(P, R) {
    if (!meOn(P)) return { plancha_entera: false, nota: "disco Ø 2·R_anillo,int + anillo de pasadores en 4 segmentos de 90° (empalmes CJP y unión plancha–anillo)" };
    const rpr = TT_.prIn(P), Rt = P.D_top / 2, N = Math.round(P.N_pin), aH = N * Math.PI / 4 * P.d_pin ** 2;
    return { plancha_entera: true, D: P.D_top, t: P.t_top, t_sup: P.t_top, t_inf: P.t_bot, material: astm(P.Fy, P.Fu),
      agujeros: { n: N, d: P.d_pin, ajuste: "H7", R: P.R_pin, paso_deg: 360 / N, mecanizado: "taladro y mandrinado/escariado EN LÍNEA de las dos planchas (superior e inferior) con la mesa armada y aliviada, a Ø" + P.d_pin + " H7" },
      R_anillo_int_anterior: rpr, formato_min: [P.D_top, P.D_top],
      masa_sup: R && R.m ? R.m.top : null, masa_inf: R && R.m ? R.m.bot : null, area_neta_agujeros: aH, R_ext: Rt,
      nota: "una plancha completa Ø" + P.D_top + " × " + P.t_top + " por nivel (" + astm(P.Fy, P.Fu) + ") con los " + N + " agujeros Ø" + P.d_pin + " H7 de los pasadores en la misma pieza: sin anillo de pasadores (MES-002 / MES-004), sin empalmes CJP de segmentos ni unión plancha–anillo; compra: plancha de " + P.t_top + " mm de al menos " + P.D_top + " × " + P.D_top + " (decisión del mandante 19-11-2026)" };
  }
  const fyC = (P) => (P.Fy_bxc > 0 ? P.Fy_bxc : P.Fy), fuC = (P) => (P.Fu_bxc > 0 ? P.Fu_bxc : P.Fu);   // acero del portador (0 = el global)
  const astm = (Fy, Fu) => (Fy === 345 && Fu === 450 ? "ASTM A572 Gr. 50" : Fy === 250 && Fu === 400 ? "ASTM A36" : "acero estructural") + " (Fy " + Fy + ", Fu " + Fu + " MPa)";
  const full = (P) => { const d = bxDefaults(), Q = Object.assign({}, P); for (const k in d) if (!(k in Q)) Q[k] = d[k]; return Q; };   // P del núcleo sin claves bx_: valores por defecto

  /* ---------------- Cilindro hidráulico FABRICADO (rev. 7d, decisión del mandante 19-11-2026) ---------------- */
  // Reemplaza el cilindro comercial (ACC-013) por uno fabricado: camisa de barra hueca ST-52 132 × 80 maquinada a Ø130 × Ø90, fondo trasero de copa
  // (placa + falda) soldado con CJP a la camisa con el ojal trasero (orejeta con rótula GE70ES) soldado, tapa delantera roscada M110 × 2 con los sellos
  // del vástago y el o'ring estático en una espiga Ø89,5 por DENTRO de la rosca, pistón con tuerca ranurada en el vástago (la tuerca es el tope del
  // retraído), vástago Ø65 cromado (cromado común, Fy 520: dato confirmado por el mandante 19-11-2026) con el ojal del vástago soldado. Las verificaciones van al grupo
  // «Cilindro» (filas bx); el núcleo recibe d_rod, pv_Fyrod, c_rod y m_cyl como parámetros (sin cambios en tt300c.js).
  const CYL_GRP = "Cilindro";
  const CYL_GROUP = { id: "bx_cyl", t: "TT300-BX · cilindro hidráulico fabricado (rev. 7d: camisa ST-52, fondo de copa soldado, tapa roscada M110 × 2, vástago Ø65 cromado)", p: [
    ["bx_cyl_on", "Cilindro: 1 = FABRICADO según el croquis del mandante (19-11-2026, por defecto); 0 = comercial (filas del cilindro fuera, núcleo como antes)", "–", 1, 0, 1, 1],
    ["bx_cyl_Fy_t", "Camisa: Fy de la barra hueca ST-52 (DIN 17100 St 52-3 ≈ S355J2; pared 16 < t ≤ 40)", "MPa", 345, 235, 700, 5],
    ["bx_cyl_Fu_t", "Camisa: Fu (St 52-3: ≥ 470)", "MPa", 470, 340, 900, 5],
    ["bx_cyl_kt", "Prueba hidráulica: p_prueba = k·p_alivio (decisión del mandante: 1,25)", "–", 1.25, 1, 1.5, 0.05],
    ["bx_cyl_t_f", "Fondo: espesor de la placa (0 = automático: el menor entero que cumple Roark y ASME VIII-1 UG-34 en servicio y en prueba)", "mm", 0, 0, 60, 1],
    ["bx_cyl_Fy_f", "Fondo de copa: Fy (S460NL, EN 10025-3, de plancha de 80 mm, 63 < t ≤ 80: 410; con S355J2 (325) el fondo pide 28 mm y el cuerpo no deja lugar al cuello del ojal del vástago)", "MPa", 410, 235, 700, 5],
    ["bx_cyl_Fu_f", "Fondo de copa: Fu (S460NL: ≥ 540)", "MPa", 540, 340, 900, 5],
    ["bx_cyl_L_sk", "Fondo de copa: largo de la falda (lleva el puerto A lejos de la CJP fondo–camisa, que queda en zona de membrana)", "mm", 45, 20, 80, 1],
    ["bx_cyl_L_t", "Tapa delantera: largo de la rosca M110 × 2 en la camisa (decisión del mandante: 30)", "mm", 30, 15, 50, 1],
    ["bx_cyl_d_t", "Tapa delantera: rosca métrica fina, Ø nominal", "mm", 110, 95, 120, 1],
    ["bx_cyl_P_t", "Tapa delantera: paso de la rosca", "mm", 2, 1.5, 3, 0.5],
    ["bx_cyl_L_s", "Tapa delantera: espiga Ø89,5 f7 con el o'ring estático, por dentro de la rosca (la rosca no ve presión)", "mm", 12, 8, 30, 1],
    ["bx_cyl_t_r", "Tapa delantera: reborde Ø130 fuera de la camisa", "mm", 15, 10, 30, 1],
    ["bx_cyl_Fy_tp", "Tapa delantera: Fy (S355J2 de plancha de 63 mm, 40 < t ≤ 63: 335)", "MPa", 335, 235, 700, 5],
    ["bx_cyl_L_pc", "Pistón: largo del cuerpo (sellos y guías; resaltes de 3 mm a cada lado del sello)", "mm", 28, 20, 60, 1],
    ["bx_cyl_h_n", "Pistón: alto de la tuerca ranurada (la tuerca es el tope del retraído contra el fondo; pistón + tuerca = 50)", "mm", 20, 10, 40, 1],
    ["bx_cyl_d_g", "Vástago: Ø del asiento del pistón (resalte Ø_vástago → Ø_asiento)", "mm", 50, 30, 60, 1],
    ["bx_cyl_d_th", "Vástago: rosca de la tuerca del pistón, Ø nominal (M48 × 2)", "mm", 48, 30, 60, 1],
    ["bx_cyl_P_th", "Vástago: paso de la rosca de la tuerca del pistón", "mm", 2, 1.5, 3, 0.5],
    ["bx_cyl_Fy_p", "Pistón y tuerca: Fy (42CrMo4+QT, EN 10083-3, 40 < d ≤ 100: 650)", "MPa", 650, 235, 1000, 5],
    ["bx_cyl_Fu_rod", "Vástago: Fu (barra cromada común; supuesto 700 ≥ Fy 520 confirmado por el mandante 19-11-2026; solo entra en el ojal y no gobierna)", "MPa", 700, 400, 1200, 10],
    ["bx_cyl_mu_t", "Apriete de la tuerca del pistón: μ en rosca y en asiento (aceitado; VDI 2230)", "–", 0.12, 0.05, 0.25, 0.01],
    ["bx_cyl_phi", "Unión pistón–vástago: factor de carga Φ_n (fracción de la carga externa que llega a la rosca con la tuerca apretada; VDI 2230, unión rígida)", "–", 0.25, 0.05, 1, 0.05],
    ["bx_cyl_RQ", "Ojal del vástago: radio exterior (≤ R_cubo − holgura de la horquilla del bloque-uña)", "mm", 68, 50, 100, 0.5],
    ["bx_cyl_Fy_oQ", "Ojal del vástago: Fy (S355J2 de plancha de 80, 63 < t ≤ 80: 325; ojal y cuello de 50 fresados, espiga Ø65 torneada)", "MPa", 325, 235, 1000, 5],
    ["bx_cyl_Fu_oQ", "Ojal del vástago: Fu", "MPa", 470, 340, 1200, 5],
    ["bx_cyl_xw", "Unión vástago–ojal: distancia de la soldadura por fricción (ISO 15620) al eje del ojal (en la espiga Ø del vástago, más allá del cuello de 50; se rectifica y croma después de soldar)", "mm", 95, 60, 150, 0.5],
    ["bx_cyl_RE", "Ojal trasero (orejeta soldada al fondo): radio exterior alrededor de E", "mm", 80, 60, 110, 0.5],
    ["bx_cyl_wE", "Ojal trasero: semiancho del cuello sobre el fondo (CJP en K)", "mm", 50, 30, 60, 0.5],
    ["bx_cyl_Fy_oE", "Ojal trasero: Fy (S355J2 de plancha de 50: 335)", "MPa", 335, 235, 700, 5],
    ["bx_cyl_Fu_oE", "Ojal trasero: Fu", "MPa", 470, 340, 900, 5],
    ["bx_cyl_C0", "Rótula del ojal trasero GE70ES (d 70, D 105, B 49, C 40; ISO 12240-1 serie E): capacidad estática C0 = 1200 kN (dato confirmado por el mandante 19-11-2026)", "kN", 1200, 200, 5000, 10],
    ["bx_cyl_s0", "Rótula: factor estático mínimo C0/P0 (criterio del proyecto)", "–", 2, 1, 4, 0.1],
    ["bx_cyl_FEXX", "Aporte de las soldaduras del cilindro (E7018 / ER70S-6: 490)", "MPa", 490, 400, 700, 10],
    ["bx_cyl_vmax", "Puertos: velocidad máxima del aceite en el paso del puerto (criterio del proyecto)", "m/s", 5, 2, 10, 0.5],
    ["bx_cyl_dA", "Puerto A (fondo): Ø del paso a la cámara (rosca G 3/8)", "mm", 10, 5, 14, 0.5],
    ["bx_cyl_dB", "Puerto B (camisa, lado vástago): Ø del paso a la cámara (rosca G 3/8)", "mm", 8, 5, 14, 0.5],
    ["bx_cyl_dz", "Tolerancia de desnivel entre los ejes E (soporte E) y Q (bloque-uña sobre la placa-guía), aprobada por el mandante 19-11-2026", "mm", 1, 0, 5, 0.1],
    ["bx_cyl_vam", "Amortiguación: velocidad del pistón sobre la cual se recomienda (criterio usual de la industria, confianza C)", "m/s", 0.1, 0.02, 0.5, 0.01],
  ] };
  const cylOn = (P) => Math.round(P.bx_cyl_on == null ? 1 : P.bx_cyl_on) === 1;
  const cylDef = () => Object.fromEntries(CYL_GROUP.p.map((q) => [q[0], q[3]]));
  const thr = (d, Pp) => ({ d, P: Pp, d2: d - 0.649519 * Pp, d3: d - 1.226869 * Pp, D1: d - 1.082532 * Pp, As: Math.PI / 4 * ((2 * d - 0.649519 * Pp - 1.226869 * Pp) / 2) ** 2 });
  // Geometría del cilindro (mm; s desde el eje del ojal trasero E hacia el vástago) y tensiones de las verificaciones
  function cylGeo(P0) {
    const P = Object.assign(cylDef(), P0), a = P.D_bore / 2, b = P.D_body / 2, tw = b - a, p = P.p_relief / 10, kt = P.bx_cyl_kt, pt = kt * p, dr = P.d_rod;
    const Ab = Math.PI * a * a, Ar = Math.PI / 4 * dr * dr, Aan = Ab - Ar, Fcal = p * Ab, Fann = p * Aan, FretN = P.p_ret / 10 * Aan;
    // camisa: Lamé (extremos cerrados) en el radio interior
    const k2 = b * b / (b * b - a * a), vmK = Math.sqrt(3) * k2, sT = (q) => vmK * q;
    const lame = { sth: p * (b * b + a * a) / (b * b - a * a), sr: -p, sz: p * a * a / (b * b - a * a), vm: sT(p), vm_prueba: sT(pt), p_y: P.bx_cyl_Fy_t / vmK * 10, Pm_vm: Math.sqrt(((p * a / tw + p / 2) ** 2 + (-p / 2 - p * a * a / (b * b - a * a)) ** 2 + (p * a * a / (b * b - a * a) - p * a / tw) ** 2) / 2) };
    // fondo: Roark (placa empotrada) y UG-34 (C = 0,33·m ≥ 0,20; t_r de UG-27; S = Fy/1,5 en servicio, 0,9·Fy en prueba; E = 1)
    const Ff = P.bx_cyl_Fy_f, ug = (q, S) => { const tr = q * a / (S - 0.6 * q), m = tr / tw, C = Math.max(0.2, 0.33 * m); return { tr, m, C, t: 2 * a * Math.sqrt(C * q / S), S }; };
    const U1 = ug(p, Ff / 1.5), U2 = ug(pt, 0.9 * Ff), tRk = (q, S) => Math.sqrt(0.75 * q * a * a / S);
    const tReq = Math.max(U1.t, U2.t, tRk(p, Ff / 1.5), tRk(pt, 0.9 * Ff)), tf = P.bx_cyl_t_f > 0 ? P.bx_cyl_t_f : Math.ceil(tReq - 1e-9);
    const roark = (q) => 0.75 * q * a * a / (tf * tf), ugS = (q, U) => U.C * q * (2 * a) ** 2 / (tf * tf);
    // largos
    const Lpc = P.bx_cyl_L_pc, hn = P.bx_cyl_h_n, Lp = Lpc + hn, Lint = Lp + P.stroke, Lt = P.bx_cyl_L_t, Ls = P.bx_cyl_L_s, tr_ = P.bx_cyl_t_r, Lsk = P.bx_cyl_L_sk;
    const Lbody = tf + Lint + Ls + Lt + tr_, cRod = P.L0 - P.e_body - Lbody;
    const s = { fondo_ext: P.e_body, fondo_int: P.e_body + tf, cjp: P.e_body + tf + Lsk, espiga: P.e_body + tf + Lint, rosca_ini: P.e_body + tf + Lint + Ls, camisa_fin: P.e_body + tf + Lint + Ls + Lt, cuerpo_fin: P.e_body + Lbody };
    const Ltube = s.camisa_fin - s.cjp;
    // rosca de la tapa (camisa hembra M110 × 2-6H, tapa macho 6g): largo efectivo L − 2P (entrada y salida)
    const TT_t = thr(P.bx_cyl_d_t, P.bx_cyl_P_t), Le = Lt - 7,   // L_e = L − garganta de la tapa (4) − salida de la camisa (2) − chaflán (1)
      An = Math.PI * Le * TT_t.d * (0.5 + 0.57735 * (TT_t.d - TT_t.d2) / TT_t.P), Asx = Math.PI * Le * TT_t.D1 * (0.5 + 0.57735 * (TT_t.d2 - TT_t.D1) / TT_t.P);
    const Atr = Math.PI / 4 * (P.D_body ** 2 - TT_t.d ** 2), Ftap = Math.max(Fcal, Fann);   // fin de carrera con el vástago libre (p·A) o cámara anular (p·A_an)
    // vástago–pistón: asiento Ø d_g, rosca M48 × 2 de la tuerca; garganta de salida DIN 76 (Ø d3 − 0,5)
    const TV = thr(P.bx_cyl_d_th, P.bx_cyl_P_th), dgr = TV.d3 - 0.5, Agr = Math.PI / 4 * dgr * dgr, LeN = hn - 5;   // tuerca: avellanado de 4 sobre la garganta del vástago + chaflán 1
    const AnN = Math.PI * LeN * TV.d * (0.5 + 0.57735 * (TV.d - TV.d2) / TV.P), AsR = Math.PI * LeN * TV.D1 * (0.5 + 0.57735 * (TV.d2 - TV.D1) / TV.P);
    const FV = Fann, FS = (FA) => FV + P.bx_cyl_phi * FA, Dn = Math.min(64, P.D_bore - 26);   // tuerca: Ø exterior 64 (≤ Ø de las guías − holgura)
    const muT = P.bx_cyl_mu_t, DKm = (Dn - 2 + P.bx_cyl_d_th + 1) / 2, MA = FV * (0.16 * TV.P + 0.58 * TV.d2 * muT + DKm / 2 * muT);
    const Fsh = p * (Ab - Math.PI / 4 * P.bx_cyl_d_g ** 2), Ash = Math.PI / 4 * ((dr - 2 * 3 * Math.tan(20 * D2R)) ** 2 - (P.bx_cyl_d_g + 2) ** 2);   // chaflán de entrada de sellos 20° × 3 en el resalte; chaflán 1 × 45° del pistón
    const Abn = Math.PI / 4 * ((Dn - 2) ** 2 - (P.bx_cyl_d_th + 2) ** 2);   // cara de la tuerca contra el fondo (tope del retraído)
    // pistón: sello de doble efecto ISO 7425-1 (D 80–132,9: fondo D − 15,5, ancho 6,3), guías ISO 10766 (banda 2,5: fondo D − 5, ancho 5,6), o'ring estático en el agujero
    const dGl = P.D_bore - 15.5, land = 3, Fland = pt * Math.PI / 4 * (P.D_bore ** 2 - dGl ** 2), Aland = Math.PI * dGl * land;
    // ojal del vástago (sin rótula: GE90ES D 130 no cabe en Ø ≤ 2·R_cubo − 2·g): ASME BTH-1 §3-3.3 con Nd del proyecto
    const Nd = P.Nd, RQ = P.bx_cyl_RQ, Dh = P.pv_dq, tQ = P.b_eye, beQ = RQ - Dh / 2, FyQ = P.bx_cyl_Fy_oQ, FuQ = P.bx_cyl_Fu_oQ, CrQ = 1 - 0.275 * Math.sqrt(1 - ((Dh - 0.1) / Dh) ** 2);
    const beffQ = Math.min(4 * tQ, beQ, 0.6 * FuQ / FyQ * Math.sqrt(Dh / beQ) * beQ), phQ = 55 * D2R, AvQ = 2 * (beQ + Dh / 2 * (1 - Math.cos(phQ))) * tQ;
    const eyeQ = { Pt: CrQ * FuQ * 2 * tQ * beffQ / (1.2 * Nd), Pv: 0.7 * FuQ * AvQ / (1.2 * Nd), Pp: 1.25 * FyQ * Dh * tQ / Nd, be: beQ, beff: beffQ, Cr: CrQ, Av: AvQ };
    // unión vástago–ojal (soldadura por fricción, sección Ø65): axial + momento de roce del pasador Q (μ·F·d_Q/2)
    const Ard = Ar, Srd = Math.PI * dr ** 3 / 32, MQc = P.pv_muE * Fcal * P.pv_dq / 2, MQr = P.pv_muE * Fann * P.pv_dq / 2;
    // ojal trasero (orejeta con rótula GE70ES: alojamiento Ø105 de 40 de ancho en la orejeta de b_ojal): BTH-1 con t = C de la rótula (conservador)
    const DE = 105, CE = 40, RE = P.bx_cyl_RE, beE = RE - DE / 2, FyE = P.bx_cyl_Fy_oE, FuE = P.bx_cyl_Fu_oE, phE = 55 * D2R;
    const beffE = Math.min(4 * CE, beE, 0.6 * FuE / FyE * Math.sqrt(DE / beE) * beE), AvE = 2 * (beE + DE / 2 * (1 - Math.cos(phE))) * CE;
    const eyeE = { Pt: FuE * 2 * CE * beffE / (1.2 * Nd), Pv: 0.7 * FuE * AvE / (1.2 * Nd), Pp: 1.25 * FyE * DE * CE / Nd, be: beE, beff: beffE, Av: AvE };
    const wE = P.bx_cyl_wE, Aw = 2 * wE * P.b_eye, Sw = P.b_eye * (2 * wE) ** 2 / 6, ME_c = P.pv_muE * Fcal * P.pv_dE / 2, ME_r = P.pv_muE * Fann * P.pv_dE / 2;
    // CJP fondo–camisa: tracción axial F = p·π·a² más el momento de borde de la placa amortiguado a x = L_falda (Timoshenko, cilindro: e^(−βx)|cos βx − sin βx|)
    const Rm = (a + b) / 2, beta = Math.pow(3 * (1 - 0.09) / (Rm * Rm * tw * tw), 0.25), kM = Math.exp(-beta * Lsk) * Math.abs(Math.cos(beta * Lsk) - Math.sin(beta * Lsk)), Aw0 = Math.PI * (b * b - a * a);
    const cjp = (q) => q * Ab / Aw0 + 6 * kM * (q * a * a / 8) / (tw * tw);
    // puertos: caudal por cilindro (A: salida del retorno Q_ret/n·A/A_an; B: entrada del retorno Q_ret/n)
    const n = P.n_cyl, Qr = (P.Q_ret > 0 ? P.Q_ret : P.Q_pump) / n, QA = Math.max(P.Q_pump / n, Qr * Ab / Aan), QB = Math.max(Qr, P.Q_pump / n * Aan / Ab);
    const vA = QA / 60000 / (Math.PI / 4 * P.bx_cyl_dA ** 2 * 1e-6), vB = QB / 60000 / (Math.PI / 4 * P.bx_cyl_dB ** 2 * 1e-6);
    const xA = hn - P.bx_cyl_dA / 2 - 2, xB = Lint - P.bx_cyl_dB / 2 - 0.5, relF = Lpc - (1 + 5.6 + land + 6.3 + land + 5.6 + 1);   // ejes de los pasos desde la cara interior del fondo; alivio frontal del pistón
    // masas (kg, ρ = 7850)
    const rho = 7.85e-6, cylV = (D, d, L) => Math.PI / 4 * (D * D - d * d) * L;
    const mCam = rho * (cylV(P.D_body, P.D_bore, Ltube) - Math.PI / 4 * (TT_t.d ** 2 - P.D_bore ** 2) * Lt);
    const mFon = rho * (Math.PI / 4 * P.D_body ** 2 * tf + cylV(P.D_body, P.D_bore, Lsk));
    const mOE = rho * P.b_eye * (Math.PI * RE * RE / 2 + Array.from({ length: 200 }, (_, i) => { const x = (i + 0.5) * P.e_body / 200; return Math.max(x < RE ? 2 * Math.sqrt(RE * RE - x * x) : 0, 2 * wE) * P.e_body / 200; }).reduce((u, v) => u + v, 0) - Math.PI / 4 * DE * DE);   // círculo R_E ∪ cuello recto de ancho 2w hasta el fondo
    const mTap = rho * (Math.PI / 4 * P.D_body ** 2 * tr_ + Math.PI / 4 * TT_t.d ** 2 * Lt + Math.PI / 4 * 89.5 ** 2 * Ls - Math.PI / 4 * dr * dr * (tr_ + Lt + Ls));
    const mPis = rho * cylV(P.D_bore, P.bx_cyl_d_g, Lpc), mTu = rho * cylV(Dn, P.bx_cyl_d_th, hn);
    const Lrod = P.L0 - P.bx_cyl_xw - s.fondo_int + 0;   // del extremo de la rosca (cara de la tuerca, retraído en la cara del fondo) a la soldadura del ojal
    const mRod = rho * (Ar * (Lrod - Lp) + Math.PI / 4 * P.bx_cyl_d_g ** 2 * Lpc + Math.PI / 4 * P.bx_cyl_d_th ** 2 * hn);
    const xn = P.pv_dq / 2 + 25 + 10, mOQ = rho * P.b_eye * (Math.PI * (RQ * RQ - Dh * Dh / 4) + dr * (xn - Math.sqrt(RQ * RQ - (dr / 2) ** 2))) + rho * Ar * (P.bx_cyl_xw - xn);   // cuello de 50 × Ø_vástago hasta R_cubo + 10 (bloque-uña) y espiga redonda
    const mOil = 0.87e-6 * (Ab * Lint), mRot = 1.6;
    const masas = { camisa: mCam, fondo: mFon, ojal_trasero: mOE, tapa: mTap, piston: mPis, tuerca: mTu, vastago: mRod, ojal_vastago: mOQ, rotula: mRot, aceite: mOil };
    const mTot = Object.values(masas).reduce((x, y) => x + y, 0);
    return { P, a, b, tw, p, pt, kt, Ab, Ar, Aan, Fcal, Fann, FretN, lame, U1, U2, tRk: [tRk(p, Ff / 1.5), tRk(pt, 0.9 * Ff)], tReq, tf, roark, ugS, Lp, Lpc, hn, Lint, Lt, Ls, tr: tr_, Lsk, Lbody, cRod, s, Ltube,
      TT_t, Le, An, Asx, Atr, Ftap, TV, dgr, Agr, LeN, AnN, AsR, FV, FS, Dn, MA, Fsh, Ash, Abn, dGl, land, Fland, Aland, eyeQ, Ard, Srd, MQc, MQr, eyeE, DE, CE, RE, wE, Aw, Sw, ME_c, ME_r, beta, kM, cjp, Aw0,
      QA, QB, vA, vB, xA, xB, relF, xn, masas, mTot, Nd };
  }
  // Valores por defecto del núcleo que fija el cilindro fabricado (rev. 7d): vástago Ø65 cromado común (Fy 520, dato confirmado por el mandante 19-11-2026), c_rod y m_cyl del cuerpo resultante
  PARAM_GROUPS.push(CYL_GROUP);
  const CYL_CORE = (() => { const P = Object.assign(TT_.defaults(), A36_DESPUES, cylDef(), { d_rod: 65, pv_Fyrod: 520, pv_tbox: A36_DESPUES.pv_tbox }), g = cylGeo(P);
    return { d_rod: 65, pv_Fyrod: 520, c_rod: Math.floor(g.cRod + 1e-9), m_cyl: Math.ceil(g.mTot + 1), p_max_cil: 680 }; })();   // rev. 7f: p_max_cil = 680 (presión de trabajo de los sellos, aprobado por el mandante 19-11-2026)   // m_cyl: piezas + 1 kg (sellos, racores)
  function cylRows(P, R) {
    const out = []; if (!cylOn(P) || TT_.driveMode(P) !== 2) return out;
    const g = cylGeo(P), Q = g.P, add = (o) => out.push(Object.assign({ kind: "fu", grp: CYL_GRP, sys: "est", bx: true }, o, { name: "BX · Cilindro: " + o.name, fu: o.kind === "info" || o.kind === "pend" ? null : (o.cap > 0 && o.dem >= 0 ? o.dem / o.cap : Infinity) }));
    const FyT = Q.bx_cyl_Fy_t, FuT = Q.bx_cyl_Fu_t, FyF = Q.bx_cyl_Fy_f, FyR = P.pv_Fyrod, FyP = Q.bx_cyl_Fy_p, FyTp = Q.bx_cyl_Fy_tp, pb = P.p_relief, ptb = g.kt * pb, k = g.kt, s3 = Math.sqrt(3), kN = (v) => v / 1e3;
    const RP = "Criterio del proyecto (decisión del mandante 19-11-2026): servicio a p_alivio con Fy/1,5; prueba hidráulica a " + nf(k, 2) + "·p_alivio = " + nf(ptb, 0) + " bar con 0,9·Fy (corte: /√3)";
    const RT = "Rosca métrica ISO 68-1/ISO 965-1 (dimensiones básicas); áreas de arranque del filete según FED-STD-H28/2 (A_n = π·L_e·d·[½ + 0,57735·(d − d₂)/P], A_s = π·L_e·D₁·[½ + 0,57735·(d₂ − D₁)/P]); L_e = L − 2P (entrada y salida)";
    const BTH = "ASME BTH-1-2020 §3-3.3 (conexiones con pasador: tracción en el área neta, corte de doble plano y aplastamiento), N_d = " + nf(g.Nd, 1) + " del proyecto";
    /* camisa */
    add({ name: "camisa Ø" + P.D_body + " × Ø" + P.D_bore + " (barra hueca ST-52 132 × 80 maquinada, pared " + g.tw + "): von Mises de Lamé en el radio interior a p_alivio", formula: "σ_vM = √3·p·b²/(b² − a²) (extremos cerrados: σ_θ = " + nf(g.lame.sth, 1) + ", σ_r = " + nf(g.lame.sr, 1) + ", σ_z = " + nf(g.lame.sz, 1) + " MPa) ≤ Fy/1,5; Fy = " + FyT + " MPa (St 52-3, 16 < t ≤ 40)", dem: g.lame.vm, cap: FyT / 1.5, unit: "MPa", ref: "Lamé (Timoshenko, Strength of Materials II §75; Roark 9.ª ed. Tabla 13.5 caso 1c); " + RP });
    add({ name: "camisa: von Mises de Lamé en la prueba hidráulica (" + nf(ptb, 0) + " bar)", formula: "σ_vM = √3·p_prueba·b²/(b² − a²) ≤ 0,9·Fy", dem: g.lame.vm_prueba, cap: 0.9 * FyT, unit: "MPa", ref: "Lamé; " + RP });
    add({ name: "camisa: tensión de membrana linealizada (referencia ASME VIII-2)", formula: "P_m (vM de σ_θ = p·a/t, σ_r = −p/2, σ_z) ≤ S = mín(Fu/2,4; Fy/1,5) = " + nf(Math.min(FuT / 2.4, FyT / 1.5), 1) + " MPa; P_m + P_b = Lamé en la cara interior ≤ 1,5·S (" + nf(g.lame.vm / (1.5 * Math.min(FuT / 2.4, FyT / 1.5)), 3) + ")", dem: g.lame.Pm_vm, cap: Math.min(FuT / 2.4, FyT / 1.5), unit: "MPa", ref: "ASME BPVC VIII-2:2023 §5.2.2 (criterio elástico, P_m ≤ S, P_L + P_b ≤ 1,5·S), referencia" });
    add({ kind: "info", name: "camisa: presión de inicio de fluencia en la cara interior (informativa)", formula: "p_y = Fy·(b² − a²)/(√3·b²) frente a la prueba " + nf(ptb, 0) + " bar", dem: g.lame.p_y, cap: ptb, unit: "bar", ref: "Lamé con von Mises" });
    /* fondo */
    const tf = g.tf, ugs = (U, q) => U.C * q * (2 * g.a) ** 2 / (tf * tf);
    add({ name: "fondo plano de copa t = " + tf + " mm (S460NL, Fy " + FyF + "): flexión de placa circular empotrada a p_alivio", formula: "σ = 0,75·p·a²/t² (a = " + g.a + ") ≤ Fy/1,5; t_req = " + nf(g.tRk[0], 1) + " mm" + (Q.bx_cyl_t_f > 0 ? "" : "; t adoptado = el menor entero que cumple Roark y UG-34 en servicio y prueba (t_req = " + nf(g.tReq, 2) + ")"), dem: g.roark(g.p), cap: FyF / 1.5, unit: "MPa", ref: "Roark's Formulas for Stress and Strain 9.ª ed., Tabla 11.2 caso 10b (borde empotrado, carga uniforme); " + RP });
    add({ name: "fondo: flexión de placa empotrada en la prueba hidráulica", formula: "σ = 0,75·p_prueba·a²/t² ≤ 0,9·Fy; t_req = " + nf(g.tRk[1], 1) + " mm", dem: g.roark(g.pt), cap: 0.9 * FyF, unit: "MPa", ref: "Roark Tabla 11.2 caso 10b; " + RP });
    add({ name: "fondo: fondo plano según ASME VIII-1 UG-34 a p_alivio (equivalente en tensión)", formula: "σ = C·P·d²/t² ≤ S·E (⇔ t ≥ d·√(C·P/(S·E)) = " + nf(g.U1.t, 2) + " mm); d = " + 2 * g.a + ", C = 0,33·m ≥ 0,20 = " + nf(g.U1.C, 3) + " (m = t_r/t_s = " + nf(g.U1.tr, 2) + "/" + g.tw + ", t_r de UG-27(c)(1)), S = Fy/1,5 = " + nf(g.U1.S, 1) + " MPa (criterio del proyecto, en vez de Fu/3,5), E = 1 (copa maquinada, CJP con RT/UT)", dem: ugs(g.U1, g.p), cap: g.U1.S, unit: "MPa", ref: "ASME BPVC VIII-1:2023 UG-34, croquis (b-2)/(g) (C = 0,33·m, mín. 0,20); UG-27(c)(1); " + RP });
    add({ name: "fondo: UG-34 en la prueba hidráulica", formula: "σ = C·P·d²/t² ≤ 0,9·Fy (t ≥ " + nf(g.U2.t, 2) + " mm; C = " + nf(g.U2.C, 3) + ")", dem: ugs(g.U2, g.pt), cap: g.U2.S, unit: "MPa", ref: "ASME VIII-1 UG-34; " + RP });
    add({ name: "CJP fondo–camisa (circunferencial a " + g.Lsk + " mm de la cara interior del fondo, en la falda): tracción axial más el momento de borde amortiguado, a p_alivio", formula: "σ = p·π·a²/(π·(b² − a²)) + 6·k·(p·a²/8)/t²; F = " + nf(kN(g.Fcal), 1) + " kN; k = e^(−βx)·|cos βx − sin βx| = " + nf(g.kM, 3) + " (β = " + nf(g.beta, 4) + "/mm, x = " + g.Lsk + "); CJP = metal base (aporte E7018/ER70S-6 de resistencia igual o mayor) ≤ Fy/1,5", dem: g.cjp(g.p), cap: FyT / 1.5, unit: "MPa", ref: "AWS D1.1/D1.1M:2020 Tabla 4.3 (CJP: resistencia del metal base); Timoshenko y Woinowsky-Krieger §114 (borde del cilindro); " + RP });
    add({ name: "CJP fondo–camisa en la prueba hidráulica", formula: "σ con p_prueba (F = " + nf(kN(g.Fcal * k), 1) + " kN) ≤ 0,9·Fy", dem: g.cjp(g.pt), cap: 0.9 * FyT, unit: "MPa", ref: "AWS D1.1 Tabla 4.3; " + RP });
    /* ojal trasero */
    const E_ = g.eyeE;
    add({ name: "ojal trasero (orejeta R" + g.RE + " × " + P.b_eye + ", S355J2) con rótula GE70ES (alojamiento Ø" + g.DE + " × " + g.CE + "): tracción en el área neta al retorno con p_alivio en la cámara anular", formula: "P_t = C_r·Fu·2·t·b_ef/(1,20·N_d); t = C de la rótula = " + g.CE + " (conservador), b_e = " + nf(E_.be, 1) + ", b_ef = " + nf(E_.beff, 1) + " mm; F = p·A_an = " + nf(kN(g.Fann), 1) + " kN", dem: kN(g.Fann), cap: kN(E_.Pt), unit: "kN", ref: BTH });
    add({ name: "ojal trasero: corte de doble plano (desgarro) al retorno", formula: "P_v = 0,70·Fu·A_v/(1,20·N_d); A_v = 2·(a + D/2·(1 − cos φ))·t = " + nf(E_.Av, 0) + " mm², φ = 55°", dem: kN(g.Fann), cap: kN(E_.Pv), unit: "kN", ref: BTH });
    add({ name: "ojal trasero: aplastamiento del alojamiento de la rótula a calado", formula: "P_p = 1,25·Fy·D·C/N_d; F_calado = p·A = " + nf(kN(g.Fcal), 1) + " kN", dem: kN(g.Fcal), cap: kN(E_.Pp), unit: "kN", ref: BTH });
    add({ name: "ojal trasero: CJP en K orejeta–fondo (" + 2 * g.wE + " × " + P.b_eye + ") al retorno: tracción más el momento de roce de la articulación", formula: "σ = F/A + M/S ≤ Fy/N_d; M = μ·F·d_E/2 = " + nf(g.ME_r / 1e6, 2) + " kN·m (μ = " + nf(P.pv_muE, 2) + ", como el núcleo); A = " + g.Aw + " mm², S = " + nf(g.Sw, 0) + " mm³; CJP = metal base", dem: g.Fann / g.Aw + g.ME_r / g.Sw, cap: Q.bx_cyl_Fy_oE / g.Nd, unit: "MPa", ref: "ASME BTH-1-2020 §3-3.4 (CJP: metal base); AWS D1.1 Tabla 4.3" });
    { const Pc = Q.bx_cyl_Fy_oE * g.Aw / 1.67, Mc = Q.bx_cyl_Fy_oE * g.Sw / 1.67, r1 = g.Fcal / Pc, r2 = g.ME_c / Mc, rat = r1 >= 0.2 ? r1 + 8 / 9 * r2 : r1 / 2 + r2;
      add({ name: "ojal trasero: cuello de la orejeta a calado (compresión por contacto pleno contra el fondo más el momento de roce)", formula: "P_r/P_c + 8/9·M_r/M_c ≤ 1; P_c = Fy·A/1,67, M_c = Fy·S/1,67 (bloque corto); M = μ·F·d_E/2 = " + nf(g.ME_c / 1e6, 2) + " kN·m", dem: rat, cap: 1, unit: "–", ref: "AISC 360-22 §H1.1 (Ec. H1-1a), ASD" }); }
    add({ name: "rótula GE70ES del ojal trasero: carga estática a calado", formula: "s₀·F_calado ≤ C₀; s₀ = " + nf(Q.bx_cyl_s0, 1) + " (criterio del proyecto), C₀ = " + Q.bx_cyl_C0 + " kN (dato confirmado por el mandante 19-11-2026)", dem: Q.bx_cyl_s0 * kN(g.Fcal), cap: Q.bx_cyl_C0, unit: "kN", ref: "ISO 12240-1 (rótulas radiales, serie E); catálogo SKF de rótulas (C₀)" });
    add({ kind: "geo", name: "rótula GE70ES: anillo interior B = 49 entre las tapas del soporte E", formula: "B ≤ b_ojal + 2·holgura = " + (P.b_eye + 2 * P.g_ch) + "; d = 70 = Ø pasador E (f8); C = 40 ≤ b_ojal; D = 105 = alojamiento N7 con resalte y anillo elástico DIN 472", dem: 49, cap: P.b_eye + 2 * P.g_ch, unit: "mm", ref: "ISO 12240-1 serie E (d 70: D 105, B 49, C 40)" });
    add({ kind: "geo", name: "rótula: Ø del pasador E igual al agujero del anillo interior", formula: "d_rótula = 70 frente a d_E", dem: 70, cap: P.pv_dE, unit: "mm", fu: Math.abs(70 - P.pv_dE) < 1e-9 ? 1 : 9, ref: "ISO 12240-1" });
    add({ kind: "info", name: "ojal del vástago SIN rótula: la GE90ES (ISO 12240-1 serie E: D 130, B 60) no cabe en el ojal Ø ≤ 2·(R_cubo − holgura) = " + 2 * (P.pv_dq / 2 + 25 - P.g_ch) + " (pared 3 mm) ni en la horquilla de " + (P.b_eye + 2 * P.g_ch) + " (B = 60)", formula: "agujero Ø" + P.pv_dq + " H9 liso sobre el pasador Q f8, engrasado (grasera M8 × 1); la desalineación la toma la rótula del ojal trasero", dem: 130, cap: 2 * g.P.bx_cyl_RQ, unit: "mm", ref: "ISO 12240-1; geometría del bloque-uña del núcleo (R_cubo)" });
    /* tapa delantera roscada */
    const TT = g.TT_t;
    add({ name: "rosca M" + TT.d + " × " + TT.P + " de la tapa delantera (L = " + g.Lt + ", L_e = L − garganta 4 − salida 2 − chaflán 1 = " + g.Le + "): arranque de los filetes de la camisa (hembra 6H) a p_alivio", formula: "τ = F/A_n ≤ Fy/(1,5·√3); F = máx(p·A [fin de carrera con el vástago libre] = " + nf(kN(g.Fcal), 1) + "; p·A_an [cámara anular] = " + nf(kN(g.Fann), 1) + ") kN; A_n = " + nf(g.An, 0) + " mm²", dem: g.Ftap / g.An, cap: FyT / (1.5 * s3), unit: "MPa", ref: RT + "; " + RP });
    add({ name: "rosca de la tapa: arranque de los filetes de la camisa en la prueba hidráulica", formula: "τ = k·F/A_n ≤ 0,9·Fy/√3", dem: k * g.Ftap / g.An, cap: 0.9 * FyT / s3, unit: "MPa", ref: RT + "; " + RP });
    add({ name: "rosca de la tapa: arranque de los filetes de la tapa (macho 6g, S355J2 Fy " + FyTp + ") a p_alivio", formula: "τ = F/A_s ≤ Fy/(1,5·√3); A_s = " + nf(g.Asx, 0) + " mm²", dem: g.Ftap / g.Asx, cap: FyTp / (1.5 * s3), unit: "MPa", ref: RT + "; " + RP });
    add({ name: "rosca de la tapa: arranque de los filetes de la tapa en la prueba hidráulica", formula: "τ = k·F/A_s ≤ 0,9·Fy/√3", dem: k * g.Ftap / g.Asx, cap: 0.9 * FyTp / s3, unit: "MPa", ref: RT + "; " + RP });
    add({ name: "camisa en la zona roscada (pared " + nf((P.D_body - TT.d) / 2, 1) + " mm, sin presión): tracción en el fondo de la rosca a p_alivio", formula: "σ = F/(π/4·(D² − d²)) ≤ Fy/1,5; A = " + nf(g.Atr, 0) + " mm²", dem: g.Ftap / g.Atr, cap: FyT / 1.5, unit: "MPa", ref: RP });
    add({ name: "camisa en la zona roscada: tracción en la prueba hidráulica", formula: "σ = k·F/A ≤ 0,9·Fy", dem: k * g.Ftap / g.Atr, cap: 0.9 * FyT, unit: "MPa", ref: RP });
    add({ kind: "geo", name: "sellos de la tapa DENTRO de la rosca: el o'ring estático va en la espiga Ø89,5 f7, en el Ø" + P.D_bore + " H8 de la camisa más allá de la rosca (la zona roscada de pared " + nf((P.D_body - TT.d) / 2, 1) + " mm no ve presión)", formula: "borde exterior de la ranura del o'ring (+ anillo de respaldo) + resalte ≤ largo de la espiga: 3 + 6,0 + 1,5 ≤ L_espiga", dem: 3 + 6 + 1.5, cap: g.Ls, unit: "mm", ref: "Requisito del mandante; ISO 3601-2 (alojamiento radial estático con anillo de respaldo)" });
    /* vástago */
    { const Lc = P.L0 + P.stroke, d = P.d_rod, Ar = g.Ar, Ir = Math.PI * d ** 4 / 64, rg = d / 4, Pr = g.Fcal, Fe_ = Math.PI ** 2 * P.E / (Lc / rg) ** 2, Fcr = FyR / Fe_ <= 2.25 ? Math.pow(0.658, FyR / Fe_) * FyR : 0.877 * Fe_, Pc = Fcr * Ar / 1.67, Mc = FyR * d ** 3 / 6 / 1.67;
      const MQ = P.pv_muE * Pr * P.pv_dq / 2, Mw = P.m_cyl * G * Lc / 8, Pe1 = Math.PI ** 2 * P.E * Ir / Lc ** 2, B1 = 1 / Math.max(1e-6, 1 - 1.6 * Pr / Pe1), Mr = B1 * Math.hypot(MQ, Mw), rat = Pr / Pc >= 0.2 ? Pr / Pc + 8 / 9 * Mr / Mc : Pr / (2 * Pc) + Mr / Mc;
      add({ name: "vástago Ø" + d + " cromado (Fy " + FyR + ": cromado común, dato confirmado por el mandante 19-11-2026): flexocompresión a calado (como el núcleo)", formula: "P_r/P_c + 8/9·B₁·M_r/M_c ≤ 1; KL = L0 + carrera = " + Lc + "; P_c = " + nf(kN(Pc), 1) + " kN; M_r = B₁·√(M_Q² + M_w²) = " + nf(Mr / 1e6, 2) + " kN·m (B₁ = " + nf(B1, 3) + ")", dem: rat, cap: 1, unit: "–", ref: "AISC 360-22 §H1.1, §E3, Apéndice 8" });
      add({ name: "vástago: pandeo de Euler biarticulado (como el núcleo)", formula: "F_calado ≤ π²EI/(3·L²), L = L0 + carrera", dem: kN(Pr), cap: kN(Math.PI ** 2 * P.E * Ir / Lc ** 2 / 3), unit: "kN", ref: "Euler, FS 3" }); }
    const TV = g.TV, FSs = g.FS(g.Fann), FSt = g.FS(k * g.Fann);
    add({ name: "vástago: garganta de la rosca M" + TV.d + " × " + TV.P + " de la tuerca del pistón (Ø" + nf(g.dgr, 2) + ") al retorno con p_alivio", formula: "σ = F_S/A_garganta ≤ Fy/1,5; F_S = F_V + Φ_n·F_A = " + nf(kN(g.FV), 1) + " + " + nf(Q.bx_cyl_phi, 2) + "·" + nf(kN(g.Fann), 1) + " = " + nf(kN(FSs), 1) + " kN (precarga F_V = p_alivio·A_an)", dem: FSs / g.Agr, cap: FyR / 1.5, unit: "MPa", ref: "VDI 2230-1:2015 (F_S = F_V + Φ_n·F_A); " + RP });
    add({ name: "vástago: garganta de la rosca en la prueba hidráulica de la cámara anular", formula: "σ = (F_V + Φ_n·k·F_A)/A ≤ 0,9·Fy", dem: FSt / g.Agr, cap: 0.9 * FyR, unit: "MPa", ref: "VDI 2230-1; " + RP });
    add({ name: "vástago: arranque de los filetes de la rosca M" + TV.d + " × " + TV.P + "-6g (L_e = alto de la tuerca − avellanado 4 − chaflán 1 = " + g.LeN + ")", formula: "τ = F_S/A_s ≤ Fy/(1,5·√3); A_s = " + nf(g.AsR, 0) + " mm²", dem: FSs / g.AsR, cap: FyR / (1.5 * s3), unit: "MPa", ref: RT + "; " + RP });
    add({ name: "vástago: arranque de los filetes en la prueba", formula: "τ = F_S,prueba/A_s ≤ 0,9·Fy/√3", dem: FSt / g.AsR, cap: 0.9 * FyR / s3, unit: "MPa", ref: RT + "; " + RP });
    add({ name: "tuerca ranurada del pistón M" + TV.d + " × " + TV.P + "-6H (42CrMo4+QT, alto " + g.hn + "): arranque de los filetes", formula: "τ = F_S/A_n ≤ Fy/(1,5·√3); A_n = " + nf(g.AnN, 0) + " mm²", dem: FSs / g.AnN, cap: FyP / (1.5 * s3), unit: "MPa", ref: RT + "; " + RP });
    add({ name: "resalte del vástago (Ø" + P.d_rod + " → Ø" + Q.bx_cyl_d_g + ") contra el pistón: aplastamiento a calado", formula: "σ = p·(A − π/4·d_asiento²)/A_contacto ≤ 0,9·mín(Fy_vástago; Fy_pistón); F = " + nf(kN(g.Fsh), 1) + " kN, A_contacto = π/4·((d − 2·3·tan 20°)² − (d_asiento + 2)²) = " + nf(g.Ash, 0) + " mm² (chaflán de entrada 20° × 3 del vástago y 1 × 45° del pistón)", dem: g.Fsh / g.Ash, cap: 0.9 * Math.min(FyR, FyP), unit: "MPa", ref: "AISC 360-22 §J7 (contacto mecanizado: R_n = 1,8·Fy·A, Ω = 2,00)" });
    add({ name: "resalte del vástago contra el pistón: aplastamiento en la prueba", formula: "σ = k·F/A ≤ 0,9·mín(Fy)", dem: k * g.Fsh / g.Ash, cap: 0.9 * Math.min(FyR, FyP), unit: "MPa", ref: "AISC 360-22 §J7 (conservador: mismo límite)" });
    add({ name: "tuerca contra el fondo (tope del retraído) con p_alivio en la cámara anular", formula: "σ = p·A_an/A_cara ≤ 0,9·Fy_fondo; A_cara = " + nf(g.Abn, 0) + " mm²", dem: g.Fann / g.Abn, cap: 0.9 * FyF, unit: "MPa", ref: "AISC 360-22 §J7" });
    add({ kind: "info", name: "tuerca del pistón: par de apriete", formula: "M_A = F_V·(0,16·P + 0,58·d₂·μ_G + D_Km/2·μ_K), μ = " + nf(Q.bx_cyl_mu_t, 2) + " (aceitado), F_V = " + nf(kN(g.FV), 1) + " kN; seguro: 2 prisioneros ISO 4026 M6 con pastilla de latón en la rosca + fijador anaeróbico", dem: g.MA / 1e6, unit: "kN·m", ref: "VDI 2230-1:2015 Ec. (R13/1)" });
    /* pistón */
    add({ name: "pistón (42CrMo4+QT): corte del resalte entre la ranura del sello y la guía a p_alivio", formula: "τ = p·π/4·(D² − d_ranura²)/(π·d_ranura·b) ≤ Fy/(1,5·√3); d_ranura = " + nf(g.dGl, 1) + ", b = " + g.land, dem: g.Fland / k / g.Aland, cap: FyP / (1.5 * s3), unit: "MPa", ref: RP });
    add({ name: "pistón: corte del resalte en la prueba", formula: "τ con p_prueba ≤ 0,9·Fy/√3", dem: g.Fland / g.Aland, cap: 0.9 * FyP / s3, unit: "MPa", ref: RP });
    /* unión vástago–ojal y ojal del vástago */
    add({ name: "unión vástago–ojal (soldadura por fricción a " + Q.bx_cyl_xw + " mm del eje del ojal, sección Ø" + P.d_rod + ") a calado", formula: "σ = F/A + M_Q/S ≤ Fy/1,5; M_Q = μ·F·d_Q/2 = " + nf(g.MQc / 1e6, 2) + " kN·m; eficiencia de la unión 1,0: procedimiento calificado WPS-CIL-03 (ensayos de tracción y doblado) aceptado por el mandante 19-11-2026", dem: g.Fcal / g.Ard + g.MQc / g.Srd, cap: FyR / 1.5, unit: "MPa", ref: "ISO 15620:2019 (soldadura por fricción); " + RP });
    add({ name: "unión vástago–ojal al retorno con p_alivio", formula: "σ = F_an/A + μ·F_an·d_Q/2/S ≤ Fy/1,5", dem: g.Fann / g.Ard + g.MQr / g.Srd, cap: FyR / 1.5, unit: "MPa", ref: "ISO 15620; " + RP });
    const Q_ = g.eyeQ;
    add({ name: "ojal del vástago (R" + Q.bx_cyl_RQ + " × " + P.b_eye + ", S355J2, agujero Ø" + P.pv_dq + " H9): tracción en el área neta al retorno", formula: "P_t = C_r·Fu·2·t·b_ef/(1,20·N_d); b_e = " + nf(Q_.be, 1) + ", b_ef = " + nf(Q_.beff, 1) + ", C_r = " + nf(Q_.Cr, 3), dem: kN(g.Fann), cap: kN(Q_.Pt), unit: "kN", ref: BTH });
    add({ name: "ojal del vástago: corte de doble plano al retorno", formula: "P_v = 0,70·Fu·A_v/(1,20·N_d); A_v = " + nf(Q_.Av, 0) + " mm²", dem: kN(g.Fann), cap: kN(Q_.Pv), unit: "kN", ref: BTH });
    add({ name: "ojal del vástago: aplastamiento sobre el pasador Q a calado", formula: "P_p = 1,25·Fy·D·t/N_d", dem: kN(g.Fcal), cap: kN(Q_.Pp), unit: "kN", ref: BTH });
    /* geometría */
    const RQmax = P.pv_dq / 2 + 25 - P.g_ch;
    add({ kind: "geo", name: "largo: e_cuerpo + cuerpo + c_vástago ≤ L0 (cuerpo = fondo " + tf + " + interior " + g.Lint + " (pistón " + g.Lpc + " + tuerca " + g.hn + " + carrera " + P.stroke + ") + espiga " + g.Ls + " + rosca " + g.Lt + " + reborde " + g.tr + " = " + g.Lbody + ")", formula: P.e_body + " + " + g.Lbody + " + " + P.c_rod + " ≤ " + P.L0 + " (c_vástago resultante = " + nf(g.cRod, 1) + ")", dem: P.e_body + g.Lbody + P.c_rod, cap: P.L0, unit: "mm", ref: "Geometría (L0 y carrera del núcleo)" });
    add({ kind: "geo", name: "ojal del vástago libre de la tapa delantera en el retraído", formula: "R_ojal + 5 ≤ c_vástago", dem: Q.bx_cyl_RQ + 5, cap: P.c_rod, unit: "mm", ref: "Geometría" });
    add({ kind: "geo", name: "cuello del ojal del vástago (50 de espesor, entre las mejillas de la horquilla del bloque-uña hasta R_cubo + 10) fuera de la tapa en el retraído", formula: "R_cubo + 10 + 3 ≤ c_vástago (el vástago Ø" + P.d_rod + " empieza a " + g.xn + " mm del eje del ojal; la soldadura por fricción a " + Q.bx_cyl_xw + " mm queda en la zona rectificada y cromada)", dem: g.xn + 3, cap: P.c_rod, unit: "mm", ref: "Geometría del núcleo (bloque-uña: R_cubo = d_Q/2 + 25; cuello del ojal, supuesto S21)" });
    add({ kind: "geo", name: "ojal del vástago dentro de la horquilla del bloque-uña", formula: "R_ojal ≤ R_cubo − holgura = " + RQmax, dem: Q.bx_cyl_RQ, cap: RQmax, unit: "mm", ref: "Geometría del núcleo (bloque-uña, supuesto S21)" });
    add({ kind: "geo", name: "ojal trasero (R" + g.RE + ", cuello " + 2 * g.wE + ") libre de las paredes del soporte E en todo el giro", formula: "máx(R_E; √(e_cuerpo² + w²)) + 5 ≤ lado/2 − t_pared = " + (P.pv_box / 2 - P.pv_tbox), dem: Math.max(g.RE, Math.hypot(P.e_body, g.wE)) + 5, cap: P.pv_box / 2 - P.pv_tbox, unit: "mm", ref: "Geometría del soporte del ojal E (núcleo)" });
    add({ kind: "geo", name: "puerto A (fondo, G 3/8): paso Ø" + Q.bx_cyl_dA + " dentro del hueco que deja la tuerca en el retraído", formula: "x_A + d/2 ≤ alto de la tuerca (x desde la cara interior del fondo; x_A = " + nf(g.xA, 1) + ")", dem: g.xA + Q.bx_cyl_dA / 2, cap: g.hn, unit: "mm", ref: "Geometría" });
    add({ kind: "geo", name: "puerto A: refrentado Ø28 lejos de la CJP fondo–camisa", formula: "x_A + 14 + semiancho del cordón (" + nf(g.tw * Math.tan(30 * D2R) + 1.5, 1) + ") + 3 ≤ L_falda", dem: g.xA + 14 + g.tw * Math.tan(30 * D2R) + 1.5 + 3, cap: g.Lsk, unit: "mm", ref: "Geometría; ISO 1179-1" });
    add({ kind: "geo", name: "puerto B (camisa, G 3/8): paso Ø" + Q.bx_cyl_dB + " libre del pistón en toda la carrera de servicio", formula: "frente del pistón en servicio = L_pistón + s_req + margen ≤ x_B − d/2", dem: g.Lp + (R && R.camP ? R.camP.sReqG : R && R.K ? R.K.s_req : P.stroke) + P.s_margin, cap: g.xB - Q.bx_cyl_dB / 2, unit: "mm", ref: "Geometría (cinemática del núcleo)" });
    add({ name: "puerto A: velocidad del aceite en el paso (salida del retorno, Q = " + nf(g.QA, 1) + " L/min por cilindro)", formula: "v = Q/A_paso ≤ v_máx (G 1/4 con paso Ø8 daría " + nf(g.QA / 60000 / (Math.PI / 4 * 64e-6), 1) + " m/s: se adopta G 3/8)", dem: g.vA, cap: Q.bx_cyl_vmax, unit: "m/s", ref: "Criterio del proyecto (práctica usual: líneas de presión 4–6 m/s); ISO 1179-1 (puertos G)" });
    add({ name: "puerto B: velocidad del aceite en el paso (entrada del retorno, Q = " + nf(g.QB, 1) + " L/min por cilindro)", formula: "v = Q/A_paso ≤ v_máx", dem: g.vB, cap: Q.bx_cyl_vmax, unit: "m/s", ref: "Criterio del proyecto; ISO 1179-1" });
    /* amortiguación, masa y prueba */
    const vR = (P.Q_ret > 0 ? P.Q_ret : P.Q_pump) / 60000 / (P.n_cyl * g.Aan * 1e-6), vE = P.Q_pump / 60000 / (P.n_cyl * g.Ab * 1e-6), mMov = (R && R.blk && R.blk.m || 0) + g.masas.vastago + g.masas.piston + g.masas.tuerca + g.masas.ojal_vastago, KE = 0.5 * mMov * vR * vR;
    const sU = R && R.camP ? R.camP.sReqG : R && R.K ? R.K.s_req : NaN;
    add({ kind: "geo", name: "amortiguación de fin de carrera: NO se requiere (el retorno llega al tope a " + nf(vR * 1000, 1) + " mm/s; el avance no llega a la tapa: s_usada " + nf(sU, 1) + " de " + P.stroke + " mm)", formula: "v_retorno = Q_ret/(n·A_an) ≤ " + nf(Q.bx_cyl_vam, 2) + " m/s (sobre ~0,1 m/s la industria recomienda amortiguación: catálogos de cilindros Parker/Bosch Rexroth, confianza C); masa en movimiento ≈ " + nf(mMov, 1) + " kg (bloque-uña y pasador Q + vástago, pistón, tuerca y ojal), E_c = ½·m·v² = " + nf(KE, 3) + " J; avance v = " + nf(vE * 1000, 1) + " mm/s. Fin de carrera: retraído contra el tope mecánico (tuerca contra el fondo) y presostato/posición del control; extendido por control (la tapa es tope de seguridad)", dem: vR, cap: Q.bx_cyl_vam, unit: "m/s", ref: "Criterio usual de la industria (confianza C); ISO 4413:2010 §5.4 (velocidad y fin de carrera controlados)" });
    { // rev. 7f (estudio del ojal del vástago, rev. 7e): momento en alzado en el ojal liso H9/f8
      const Lc = P.L0 + P.stroke, d = P.d_rod, Ar = g.Ar, Ir = Math.PI * d ** 4 / 64, Pr = g.Fcal, Fe_ = Math.PI ** 2 * P.E / (Lc / (d / 4)) ** 2, Fcr = FyR / Fe_ <= 2.25 ? Math.pow(0.658, FyR / Fe_) * FyR : 0.877 * Fe_;
      const Pc = Fcr * Ar / 1.67, Mc = FyR * d ** 3 / 6 / 1.67, MQ = P.pv_muE * Pr * P.pv_dq / 2, Mw = P.m_cyl * G * Lc / 8, B1 = 1 / Math.max(1e-6, 1 - 1.6 * Pr / (Math.PI ** 2 * P.E * Ir / Lc ** 2));
      const fx = (M) => { const Mr = B1 * Math.hypot(MQ, Mw + M); return Pr / Pc >= 0.2 ? Pr / Pc + 8 / 9 * Mr / Mc : Pr / (2 * Pc) + Mr / Mc; };
      let lo = 0, hi = 5e7; for (let i = 0; i < 80; i++) { const m = (lo + hi) / 2; if (fx(m) <= 1) lo = m; else hi = m; }
      const L = P.L0, EIx = (x) => (x < P.e_body ? 1e12 * P.E : x < P.e_body + g.Lbody ? P.E * Math.PI * (P.D_body ** 4 - P.D_bore ** 4) / 64 : P.E * Ir);
      let th = 0; for (let i = 0; i < 2000; i++) { const x = (i + 0.5) * L / 2000; th += (x / L) ** 2 / EIx(x) * L / 2000; }
      const kc = 1 / th, dzA = lo / kc * L, REFE = "Estudio del ojal del vástago (rev. 7e, docs/bx/README_BX.md §13.4): ojal liso H9/f8, giro libre nulo (conservador)";
      add({ kind: "geo", name: "desnivel especificado entre los ejes E y Q frente al admisible del vástago (ojal liso, holgura nula)", formula: "Δz_esp = " + nf(Q.bx_cyl_dz, 1) + " mm ≤ Δz_adm = M_adm·L/k_c = " + nf(dzA, 2) + " mm; M = k_c·Δz/L (k_c = rigidez rotacional en Q del cilindro articulado en E, cuerpo Ø" + P.D_body + "/" + P.D_bore + " + vástago Ø" + d + ": " + nf(kc / 1e9, 2) + "×10⁹ N·mm/rad ≥ 3EI/L del vástago solo; L = largo retraído " + L + "), M_adm = " + nf(lo / 1e6, 2) + " kN·m (flexocompresión del vástago = 1 con μ y peso); en el retraído (el más rígido) el admisible es el menor: el estudio daba 1,27 mm a L = 544 (posición del M_H máximo); con el giro libre mínimo del ajuste H9/f8 (0,036/50 = 0,72 mrad) Δz_adm = " + nf(dzA + 0.036 / 50 * L, 2) + " mm; tolerancia aprobada por el mandante 19-11-2026", dem: Q.bx_cyl_dz, cap: dzA, unit: "mm", ref: REFE + "; AISC 360-22 §H1.1" });
      let MH = 0; (R && R.stroke || []).forEach((q) => { const Hc = q.H_guia * (R.Fstall / q.F), m = Hc * Math.sin(q.phi_guia * D2R) * (R.blk ? R.blk.lq : 0) * 1e3; if (m > MH) MH = m; });
      const Fp = R && R.stallMax ? R.stallMax.Fp * 1e3 : 0, Mb = Fp * P.pv_hu / 6;
      if (MH > 0 && Mb > 0) add({ kind: "geo", name: "reparto del momento en alzado de la placa-guía: lo toma el bloque-uña por el contacto contra el pasador P (sin despegue)", formula: "M_H = H_calado·sen φ·l_Q = " + nf(MH / 1e6, 2) + " kN·m (máximo del empuje) ≤ F_calado·h/6 = " + nf(Fp / 1e3, 1) + "·" + P.pv_hu + "/6 = " + nf(Mb / 1e6, 2) + " kN·m (resultante en el núcleo central de la altura de contacto); con k_bloque ≈ 4,5·k_c y el giro libre H9/f8 al vástago le llega ≈ 0 (≤ 18 % sin holgura)", dem: MH / 1e6, cap: Mb / 1e6, unit: "kN·m", ref: REFE });
    }
    add({ kind: "geo", name: "masa del cilindro fabricado frente a la masa por cilindro del núcleo (m_cyl)", formula: "Σ piezas (camisa " + nf(g.masas.camisa, 1) + ", fondo " + nf(g.masas.fondo, 1) + ", ojales " + nf(g.masas.ojal_trasero + g.masas.ojal_vastago, 1) + ", tapa " + nf(g.masas.tapa, 1) + ", pistón y tuerca " + nf(g.masas.piston + g.masas.tuerca, 1) + ", vástago " + nf(g.masas.vastago, 1) + ", rótula y aceite) ≤ m_cyl", dem: g.mTot, cap: P.m_cyl, unit: "kg", ref: "Geometría (ρ = 7850 kg/m³)" });
    add({ kind: "info", name: "prueba hidráulica de fábrica de cada cilindro", formula: "p_prueba = " + nf(k, 2) + "·p_alivio = " + nf(ptb, 0) + " bar en cada cámara por separado (pistón a tope), 10 min sin caída ni fugas; la fila térmica del núcleo «aceite atrapado tras el calado» sigue comparando con 1,5·p_max (pendiente de pasar a " + nf(ptb, 0) + " bar en el escenario térmico)", dem: ptb, cap: pb, unit: "bar", ref: "Decisión del mandante; ISO 10100:2020 (ensayo de aceptación de cilindros, referencia)" });
    add({ kind: "geo", name: "sellos: presión de trabajo del alivio frente a la nominal de trabajo de los sellos (S1 a S8)", formula: "p_alivio ≤ p_trabajo,sellos = 680 bar (dato confirmado por el mandante 19-11-2026; con las holguras de extrusión de las láminas)", dem: pb, cap: 680, unit: "bar", ref: "ISO 7425-1/-2, ISO 5597, ISO 3601-3; dato confirmado por el mandante 19-11-2026" });
    add({ kind: "geo", name: "sellos: presión de prueba hidráulica frente a la de prueba de los sellos (S1 a S8)", formula: "p_prueba = " + nf(k, 2) + "·p_alivio ≤ p_prueba,sellos = 850 bar (dato confirmado por el mandante 19-11-2026)", dem: ptb, cap: 850, unit: "bar", ref: "ISO 7425-1/-2, ISO 5597, ISO 3601-3; dato confirmado por el mandante 19-11-2026" });
    return out;
  }
  // Bloque «cilindro» del JSON (fuente única de las láminas del cilindro fabricado): cotas, tolerancias, rugosidades, alojamientos de sellos, puertos,
  // soldaduras, materiales, pares, secuencia, notas y masas. Ejes: s desde el eje del ojal trasero E (mm); cada pieza trae además sus cotas locales.
  function cylExport(P, R, checks) {
    if (!cylOn(P) || TT_.driveMode(P) !== 2) return null;
    const g = cylGeo(P), Q = g.P, r1 = (v) => Math.round(v * 10) / 10, D = P.D_body, B = P.D_bore, dr = P.d_rod, TT = g.TT_t, TV = g.TV, tf = g.tf;
    const t30 = Math.tan(30 * D2R), wCjp = r1(g.tw * t30 * 2 + 2);
    const sellos = [
      { pos: "S1", nombre: "Sello de pistón de doble efecto (anillo de PTFE con bronce + o'ring energizador NBR 70)", norma: "ISO 7425-1", designacion: "pistón D " + B + ", alojamiento d " + r1(g.dGl) + " × " + "6,3", alojamiento: { d_fondo: g.dGl, tol_fondo: "h9", ancho: 6.3, tol_ancho: "+0,2/0", radio_fondo: 0.4, Ra_fondo: 1.6, Ra_flancos: 3.2, holgura_extrusion_max: 0.2 }, material: "PTFE + bronce 40 % / NBR 70", cantidad: 1, pieza: "piston", presion: "680 bar de trabajo y 850 bar de prueba (dato confirmado por el mandante 19-11-2026)" },
      { pos: "S2", nombre: "Anillo guía del pistón (banda de 2,5 × 5,6)", norma: "ISO 10766", designacion: "D " + B + " × 5,6 × 2,5", alojamiento: { d_fondo: B - 5, tol_fondo: "h8", ancho: 5.6, tol_ancho: "+0,2/0", Ra_fondo: 3.2 }, material: "PTFE + bronce o tejido de poliéster con resina", cantidad: 2, pieza: "piston" },
      { pos: "S3", nombre: "O'ring estático pistón–vástago con 2 anillos de respaldo", norma: "ISO 3601-1 / ISO 3601-2", designacion: "ISO 3601-1 50,17 × 3,53 (AS568-226) NBR 90 + 2 anillos de respaldo de PTFE", alojamiento: { tipo: "hembra (en el agujero del pistón)", d_fondo: 55.6, tol_fondo: "H9", ancho: 7.6, tol_ancho: "+0,2/0", radio_fondo: 0.4, radio_borde: 0.2, Ra_fondo: 1.6, Ra_contacto: 0.8 }, material: "NBR 90 Shore A; respaldo PTFE", cantidad: 1, pieza: "piston" },
      { pos: "S4", nombre: "O'ring estático tapa–camisa (espiga Ø89,5) con anillo de respaldo del lado de la rosca", norma: "ISO 3601-1 / ISO 3601-2", designacion: "ISO 3601-1 81,92 × 3,53 (AS568-236) NBR 90 + 1 anillo de respaldo de PTFE", alojamiento: { tipo: "macho (en la espiga)", d_fondo: 84.4, tol_fondo: "h9", ancho: 6.0, tol_ancho: "+0,2/0", radio_fondo: 0.4, radio_borde: 0.2, Ra_fondo: 1.6, Ra_contacto: 0.8, compresion_pct: r1((3.53 - (B - 84.4) / 2) / 3.53 * 100), estiramiento_pct: r1((84.4 / 81.92 - 1) * 100) }, material: "NBR 90 Shore A; respaldo PTFE", cantidad: 1, pieza: "tapa" },
      { pos: "S5", nombre: "Sello de vástago principal (anillo escalonado de PTFE + o'ring energizador)", norma: "ISO 7425-2", designacion: "vástago d " + dr + ", alojamiento D " + (dr + 11) + " × 4,2", alojamiento: { d_fondo: dr + 11, tol_fondo: "H9", ancho: 4.2, tol_ancho: "+0,2/0", radio_fondo: 0.4, Ra_fondo: 1.6 }, material: "PTFE + bronce / NBR 70", cantidad: 1, pieza: "tapa", presion: "680 bar de trabajo y 850 bar de prueba (dato confirmado por el mandante 19-11-2026)" },
      { pos: "S6", nombre: "Sello de vástago secundario (copa en U de poliuretano, en tándem)", norma: "ISO 5597", designacion: "U " + dr + " × " + (dr + 15) + " × 12", alojamiento: { d_fondo: dr + 15, tol_fondo: "H11", ancho: 12.5, tol_ancho: "+0,2/0", radio_fondo: 0.4, Ra_fondo: 1.6 }, material: "PU 93 Shore A", cantidad: 1, pieza: "tapa" },
      { pos: "S7", nombre: "Anillos guía del vástago", norma: "ISO 10766", designacion: "d " + dr + " × 9,7 × 2,5 y d " + dr + " × 5,6 × 2,5", alojamiento: { d_fondo: dr + 5, tol_fondo: "H9", ancho: [9.7, 5.6], tol_ancho: "+0,2/0", Ra_fondo: 3.2 }, material: "PTFE + bronce", cantidad: 2, pieza: "tapa" },
      { pos: "S8", nombre: "Rascador de doble labio", norma: "ISO 6195 (tipo D)", designacion: "d " + dr + " × " + (dr + 10) + " × 7", alojamiento: { d_fondo: dr + 10, tol_fondo: "H11", ancho: 7, tol_ancho: "+0,2/0", d_labio: dr + 3, Ra_fondo: 3.2 }, material: "PU 93 Shore A", cantidad: 1, pieza: "tapa" },
    ];
    // tapa: cotas locales w desde la cara interior (cara de la espiga) hacia afuera
    const Lt = g.Lt, Ls = g.Ls, tr = g.tr, Ltap = Ls + Lt + tr;
    const tapa = { largo: Ltap, espiga: { d: 89.5, tol: "f7", w: [0, Ls], chaflan_entrada: "15° × 1,5", ranura_oring: { w: [3, 9], ref: "S4" } },
      rosca: { designacion: "M" + TT.d + " × " + TT.P + "-6g", w: [Ls, Ls + Lt - 4], util: Lt - 4 - 1, chaflan: "1 × 45° en la entrada", garganta: { w: [Ls + Lt - 4, Ls + Lt], d: r1(TT.d3 - 0.7), radio: 1, norma: "DIN 76-1 (salida de rosca exterior)" }, d2: TT.d2, d3: TT.d3 },
      reborde: { d: D, tol: "h11", w: [Ls + Lt, Ltap], agujeros_llave: { n: 4, d: 10, prof: 8, pcd: 110, norma: "llave de gancho articulada con espiga DIN 1810 forma B" }, cara_asiento: "cara interior del reborde contra el extremo de la camisa, perpendicularidad 0,03 a la espiga" },
      agujero: { d: dr, tol: "H9", Ra: 1.6, nota: "holgura de extrusión radial máx. " + r1(((dr + 0.074) - (dr - 0.076)) / 2 * 100) / 100 + " mm con el vástago f7" },
      alojamientos_vastago: [{ ref: "S7", w: [3, 12.7], d: dr + 5, ancho: 9.7 }, { ref: "S5", w: [15.7, 19.9], d: dr + 11, ancho: 4.2 }, { ref: "S6", w: [22.9, 35.4], d: dr + 15, ancho: 12.5 }, { ref: "S7", w: [38.4, 44], d: dr + 5, ancho: 5.6 }, { ref: "S8", w: [47, 54], d: dr + 10, ancho: 7, labio: { w: [54, Ltap], d: dr + 3 } }],
      material: "S355J2+N (EN 10025-2) de plancha de 63 mm (Fy " + Q.bx_cyl_Fy_tp + ")", par_apriete_Nm: 600, antigiro: "1 prisionero ISO 4026 M8 × 10 con pastilla de latón, radial por la camisa en la zona roscada (a 15 mm del extremo), con fijador anaeróbico de resistencia media",
      masa: g.masas.tapa };
    const camisa = { D, tol_D: "h11", d: B, tol_d: "H8", Ra_d: 0.4, acabado: "bruñido (honing) después de soldar el fondo y de aliviar tensiones; Rz ≤ 2,5", cilindricidad: 0.02, rectitud: "0,03 / 300", largo: g.Ltube - 1, largo_corte: g.Ltube - 1 + 6, separacion_raiz: 2,
      material: "barra hueca ST-52 (DIN 17100 St 52-3 ≈ S355J2, EN 10294-1 E355) 132 × 80 maquinada a Ø" + D + " × Ø" + B + " (pared " + g.tw + "); Fy " + Q.bx_cyl_Fy_t + ", Fu " + Q.bx_cyl_Fu_t,
      bisel_trasero: { tipo: "V a 30° (60° total con el de la falda del fondo)", ang: 30, talon: 2, separacion: 2, largo_bisel: r1((g.tw - 2) * t30), respaldo: "anillo cerámico interior desechable (raíz eliminada en el bruñido)" },
      rosca: { designacion: "M" + TT.d + " × " + TT.P + "-6H", prof: Lt - 2, salida: 2, chaflan_entrada: "1,5 × 30° en el extremo", D1: TT.D1 },
      chaflan_sellos: { ang: 15, largo: 2.5, x_desde_extremo: Lt, nota: "entrada de los sellos del pistón y del o'ring de la espiga al Ø" + B + " H8, aristas redondeadas R0,5 y pulidas, sin rebabas" },
      puerto_B: { rosca: "G 3/8 (ISO 228-1)", norma: "ISO 1179-1 (asiento de sello ED)", refrentado: 28, prof_rosca: 12, paso: Q.bx_cyl_dB, x_desde_extremo_trasero: r1(g.xB - g.Lsk - 1), x_desde_extremo_delantero: r1(g.Lint + g.Ls + g.Lt - g.xB), orientacion: "arriba (+z)", Ra_refrentado: 3.2 },
      prisionero_tapa: { d: "M8", x_desde_extremo: 15 }, masa: g.masas.camisa };
    const fondo = { t: tf, t_req: g.tReq, falda: g.Lsk - 1, D, d: B, largo: tf + g.Lsk - 1, radio_interior: 3, material: "S460NL (EN 10025-3) de plancha de 80 mm (63 < t ≤ 80: Fy " + Q.bx_cyl_Fy_f + ", Fu " + Q.bx_cyl_Fu_f + "); con S355J2 (Fy 325) haría falta t = 28 y no cabe el cuello del ojal del vástago",
      bisel: { tipo: "V a 30° en el extremo de la falda", ang: 30, talon: 2, separacion: 2, largo_bisel: r1((g.tw - 2) * t30) },
      puerto_A: { rosca: "G 3/8 (ISO 228-1)", norma: "ISO 1179-1 (asiento de sello ED)", refrentado: 28, prof_rosca: 12, paso: Q.bx_cyl_dA, x_desde_cara_interior: r1(g.xA), orientacion: "arriba (+z)", Ra_refrentado: 3.2 },
      cjp: { ancho_cara: wCjp, simbolo: "V con respaldo, CJP, perfil a ras exterior (AWS A2.4)", end: "UT 100 % (AWS D1.1 cláusula 8, o ISO 17640 nivel 2) + MT 100 % después del alivio", wps: "WPS-CIL-01", proceso: "GTAW raíz + SMAW/FCAW relleno, E7018 / ER70S-6 (resistencia de la camisa S355), unión S460NL–S355J2, precalentamiento 100 °C, alivio de tensiones 580–620 °C antes del bruñido" },
      ojal: { R: g.RE, ancho: P.b_eye, cuello: 2 * g.wE, alojamiento: { d: g.DE, tol: "N7", ancho: g.CE, resalte: { d: 98, ancho: 3 }, ranura: { norma: "DIN 472 (anillo 105 × 4)", d: 109, ancho: 4.15, tol_ancho: "H13", w: [3 + g.CE, 3 + g.CE + 4.15] } },
        material: "S355J2+N de plancha de 50 (Fy " + Q.bx_cyl_Fy_oE + ")", soldadura: { tipo: "CJP en K (doble bisel 45°, talón 2) más filete de refuerzo z6 en todo el contorno", simbolo: "K con filete, todo alrededor (AWS A2.4)", end: "MT 100 % + UT 100 %", wps: "WPS-CIL-02" },
        rotula: { designacion: "GE70ES (ISO 12240-1 serie E; SKF GE 70 ES o equivalente)", d: 70, D: 105, B: 49, C: 40, C0_kN: Q.bx_cyl_C0, montaje: "a presión en el alojamiento N7, contra el resalte; anillo elástico DIN 472-105 × 4 del otro lado (anillo de posición: la rótula queda entre las tapas del soporte E)" } },
      masa: g.masas.fondo, masa_ojal: g.masas.ojal_trasero };
    const xs = Math.sqrt(Q.bx_cyl_RQ ** 2 - (dr / 2) ** 2);
    const piston = { D: 89.8, tol_D: "f8", largo: g.Lpc, d: Q.bx_cyl_d_g, tol_d: "H8", material: "42CrMo4+QT (EN 10083-3), Fy " + Q.bx_cyl_Fy_p,
      u: { chaflan: [0, 1], guia1: [1, 6.6], sello: [9.6, 15.9], guia2: [18.9, 24.5], alivio: [25.5, g.Lpc], d_alivio: 80, ranura_oring: [8.95, 16.55] }, Ra_D: 1.6, perpendicularidad: 0.02, coaxialidad: "Ø0,03 del Ø" + 89.8 + " con el agujero",
      tuerca: { designacion: "tuerca ranurada M" + TV.d + " × " + TV.P + "-6H (de fabricación)", D: g.Dn, alto: g.hn, ranuras: { n: 4, ancho: 8, prof: 4 }, avellanado: { d: 51, prof: 4 }, material: "42CrMo4+QT", seguro: "2 prisioneros ISO 4026 M6 × 8 con pastilla de latón a 180° + fijador anaeróbico de alta resistencia", par_Nm: Math.round(g.MA / 1e3 / 10) * 10, F_V_kN: g.FV / 1e3 },
      masa: g.masas.piston, masa_tuerca: g.masas.tuerca };
    const Lrod = P.L0 - Q.bx_cyl_xw - g.s.fondo_int;
    const vastago = { d: dr, tol: "f7", largo: r1(Lrod), material: "barra de acero cromada (cromado común; Fy " + P.pv_Fyrod + ", Fu " + Q.bx_cyl_Fu_rod + " MPa; Fy dato confirmado por el mandante 19-11-2026)", cromo: { espesor_min_um: 20, dureza: "850–1050 HV", Ra: 0.2, norma: "ISO 6158 (cromo duro)" }, rectitud: "0,05 / 1000",
      asiento: { d: Q.bx_cyl_d_g, tol: "g6", largo: g.Lpc, resalte_chaflan: "20° × 3 (entrada de los sellos del vástago)" }, garganta: { d: r1(g.dgr), ancho: 4, radio: 1, norma: "DIN 76-1" },
      rosca: { designacion: "M" + TV.d + " × " + TV.P + "-6g", largo: g.hn - 4, chaflan: "1,5 × 45°" }, extremo_ojal: { tipo: "soldadura por fricción (ISO 15620)", x_desde_eje_ojal: Q.bx_cyl_xw, nota: "rebaba eliminada; rectificado y cromado DESPUÉS de soldar" }, masa: g.masas.vastago };
    const ojal_vastago = { R: Q.bx_cyl_RQ, ancho: P.b_eye, d: P.pv_dq, tol_d: "H9", Ra_d: 1.6, cuello: { ancho: dr, espesor: P.b_eye, x0: r1(xs), x1: g.xn }, espiga: { d: dr, x0: g.xn, x1: Q.bx_cyl_xw }, grasera: "DIN 71412 M8 × 1 radial con ranura de engrase 3 × 1,5", material: "S355J2+N de plancha de 80 (Fy " + Q.bx_cyl_Fy_oQ + "): ojal y cuello fresados a 50, espiga Ø" + dr + " torneada", rotula: "no lleva (la GE90ES, D 130, no cabe en Ø" + 2 * Q.bx_cyl_RQ + ")", soldadura: { tipo: "soldadura por fricción con el vástago (ISO 15620), procedimiento calificado WPS-CIL-03 con ensayos de tracción y doblado (aceptado por el mandante 19-11-2026)", end: "UT 100 % + MT" }, masa: g.masas.ojal_vastago };
    const rows = (checks || []).filter((c) => c.grp === CYL_GRP).map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref }));
    return { modo: "fabricado", revision: "rev. 7d (19-11-2026): cilindro fabricado según el croquis del mandante", n: P.n_cyl, D_camisa: B, d_vastago: dr, carrera: P.stroke, L0: P.L0, L_ext: P.L0 + P.stroke, e_cuerpo: P.e_body, c_vastago: P.c_rod, c_vastago_resultante: g.cRod, cuerpo: g.Lbody, interior: g.Lint,
      p_alivio: P.p_relief, p_alarma: P.p_alarm, p_retorno: P.p_ret, p_prueba: g.kt * P.p_relief, k_prueba: g.kt, F_calado_kN: g.Fcal / 1e3, F_anular_kN: g.Fann / 1e3, F_tapa_kN: g.Ftap / 1e3,
      s: g.s, camisa, fondo, tapa, piston, vastago, ojal_vastago, sellos,
      aceite: "aceite hidráulico mineral HLP 46 (ISO 6743-4 HM, ISO VG 46), limpieza ISO 4406 18/16/13",
      pares: [["Tapa delantera M" + TT.d + " × " + TT.P + " (llave de gancho)", tapa.par_apriete_Nm + " N·m"], ["Tuerca del pistón M" + TV.d + " × " + TV.P, piston.tuerca.par_Nm + " N·m (F_V ≈ " + Math.round(g.FV / 1e3) + " kN, μ " + Q.bx_cyl_mu_t + ")"], ["Prisioneros M6 de la tuerca", "4 N·m"], ["Prisionero M8 antigiro de la tapa", "10 N·m"], ["Puertos G 3/8 (racor con sello ED)", "60 N·m (dato del racor)"]],
      secuencia: ["Soldar el fondo de copa a la camisa (WPS-CIL-01, CJP con respaldo cerámico) y la orejeta trasera al fondo (WPS-CIL-02); UT y MT; alivio de tensiones 580–620 °C.",
        "Mecanizar después de soldar: Ø" + B + " H8 bruñido Ra ≤ 0,4 de la falda y la camisa en una sola pasada, rosca M" + TT.d + " × " + TT.P + "-6H, chaflán de entrada de sellos 15°, alojamiento Ø105 N7 de la rótula en línea con el eje, puertos A y B.",
        "Vástago: soldar el ojal por fricción (WPS-CIL-03), eliminar la rebaba, rectificar Ø" + dr + " f7, cromar ≥ 20 µm y pulir Ra ≤ 0,2; mecanizar el agujero Ø" + P.pv_dq + " H9 del ojal referido al eje del vástago.",
        "Montar en la tapa el rascador, las guías, la copa en U y el sello escalonado (herramienta de montaje, sin aristas); el o'ring S4 y su respaldo en la espiga.",
        "Pasar la tapa por el extremo roscado del vástago (protector cónico sobre la rosca y el resalte de 20°).",
        "Montar el pistón con S1, S2 y S3 en el asiento Ø" + Q.bx_cyl_d_g + ", la tuerca con fijador y apretar a " + piston.tuerca.par_Nm + " N·m; apretar los prisioneros M6.",
        "Introducir el conjunto pistón–vástago en la camisa por el extremo roscado (casquillo de montaje cónico), roscar la tapa hasta asentar el reborde con " + tapa.par_apriete_Nm + " N·m y fijar el prisionero M8.",
        "Montar la rótula GE70ES a presión en el ojal trasero y su anillo elástico; prueba hidráulica a " + g.kt * P.p_relief + " bar (cada cámara, pistón a tope, 10 min) y prueba de fugas a 10 bar."],
      notas: ["Cilindro FABRICADO (decisión del mandante 19-11-2026); reemplaza la especificación de compra ACC-013 comercial.", "Largo retraído " + P.L0 + " mm entre ejes de ojales (tuerca contra el fondo: tope mecánico del retraído); extendido " + (P.L0 + P.stroke) + " mm = retraído + carrera (pistón contra la espiga de la tapa: tope de seguridad, no se alcanza en servicio).",
        "Sin amortiguación de fin de carrera: retorno a " + nf((P.Q_ret > 0 ? P.Q_ret : P.Q_pump) / 60000 / (P.n_cyl * g.Aan * 1e-6) * 1000, 1) + " mm/s < 0,1 m/s; fin de carrera por presostato/posición del control.", "Los sellos van por dentro de la rosca de la tapa: la rosca y la pared de 10 mm de la camisa no ven presión.",
        "Prueba hidráulica de fábrica a " + g.kt * P.p_relief + " bar (" + nf(g.kt, 2) + " × p_alivio " + P.p_relief + " bar) con certificado; alivio del sistema " + P.p_relief + " bar, alarma " + P.p_alarm + " bar."],
      masas: g.masas, masa_total: g.mTot, verificaciones: rows,
      dz_tol: Q.bx_cyl_dz, dz_adm: (() => { const r = (checks || []).find((c) => /desnivel especificado/.test(c.name)); return r ? r.cap : null; })(),
      dz_nota: "Desnivel entre los ejes E (soporte E) y Q (bloque-uña sobre la placa-guía): |z_E − z_Q| ≤ " + nf(Q.bx_cyl_dz, 1) + " mm (cada eje a su cota ± " + nf(Q.bx_cyl_dz / 2, 1) + " sobre la base), medido con nivel óptico en el montaje; aprobado por el mandante 19-11-2026. Criterio: estudio del ojal del vástago (rev. 7e), Δz admisible 1,3 mm sin holgura (1,0 mm en el retraído, fila «Cilindro» del núcleo BX)" };
  }


  /* ---------------- Material del disco ---------------- */
  function matOf(P) {
    const k = P.__th ? P.__th.k : null;
    if (Math.round(P.bx_ss_mat) === 2) return { id: 2, nombre: "dúplex 2205 (UNS S32205, ASTM A240)", Fy: P.bx_Fy_dx * (k ? k.Fy_ss : 1), Fu: P.bx_Fu_dx, al: 13.0e-6, E: 200000 * (k ? k.E_ss : 1), rho: 7.80e-6, nu: 0.3,
      aporte: "ER2209 (AWS A5.9) / E2209 (AWS A5.4)", fuente: "ASTM A240 (S32205: Fy ≥ 450, Fu ≥ 655 MPa); α 20–100 °C ≈ 13,0×10⁻⁶/K y E ≈ 200 GPa (ficha de fabricante, confianza B)" };
    return { id: 1, nombre: "austenítico 304/316L (ASTM A240)", Fy: P.Fy_ss, Fu: P.Fu_ss, al: 17.3e-6, E: 193000 * (k ? k.E_ss : 1), rho: 7.93e-6, nu: 0.3,   // P.Fy_ss ya viene reducido por TT.thermalP
      aporte: "ER308L / ER316L (AWS A5.9)", fuente: "ASTM A240; α y E como el núcleo (17,3×10⁻⁶/K; 193 GPa)" };
  }

  /* ---------------- Mecánica: placa anular, rigidez de tornillos, fuerza térmica de borde ---------------- */
  // Celda equivalente de la malla de pastillas (Timoshenko y Woinowsky-Krieger §17, flexión simétrica de placas anulares): anillo a ≤ r ≤ b con
  // carga uniforme q, borde interior empotrado sobre la pastilla (r = a = d/2: w = w' = 0) y borde exterior guiado por simetría (r = b, π·b² = área
  // tributaria: w' = 0, corte nulo). w = q·r⁴/(64D) + A + B·r² + C·ln r + E·r²·ln r, con E = −q·b²/(8D) (corte nulo en b). Devuelve M_r en a y en b
  // (N·mm/mm) y la flecha relativa w(b) − w(a).
  function cellPlate(q, a, b, D, nu) {
    const E = -q * b * b / (8 * D), F = (r) => q * r ** 3 / (16 * D) + E * (2 * r * Math.log(r) + r);
    const Cc = (-F(a) / a + F(b) / b) / (1 / (a * a) - 1 / (b * b)), Bc = (-F(a) / a - Cc / (a * a)) / 2;   // 2B·a + C/a = −F(a); 2B·b + C/b = −F(b)
    const w2 = (r) => 3 * q * r * r / (16 * D) + 2 * Bc - Cc / (r * r) + E * (2 * Math.log(r) + 3);
    const Ma = -D * w2(a), Mb = -D * w2(b);                               // w'(a) = w'(b) = 0: M_r = −D·w''
    const w = q * (b ** 4 - a ** 4) / (64 * D) + Bc * (b * b - a * a) + Cc * Math.log(b / a) + E * (b * b * Math.log(b) - a * a * Math.log(a));
    return { Ma, Mb, Mmax: Math.max(Math.abs(Ma), Math.abs(Mb)), w, B: Bc, C: Cc, E, nu };
  }
  // Flexibilidad de una unión atornillada a simple corte (Huth 1986, ASTM STP 927): C = ((t1 + t2)/(2d))^(2/3)·3,0·[1/(t1E1) + 1/(t2E2) + 1/(2t1E3) + 1/(2t2E3)]
  function huth(t1, E1, t2, E2, d) {
    const C = Math.pow((t1 + t2) / (2 * d), 2 / 3) * 3.0 * (1 / (t1 * E1) + 1 / (t2 * E2) + 1 / (2 * t1 * E_BOLT) + 1 / (2 * t2 * E_BOLT));
    return 1 / C;
  }
  // Fuerza del tornillo del borde por la dilatación diferencial disco–mesa (mesa rígida, conservador): franja radial del disco de ancho s_t (rigidez
  // E·t·s_t/(1 − ν²), deformación libre (1 + ν)·ε con la deformación anular impedida, conservador) sobre resortes k_b cada s_r. Cadena semi-infinita con
  // extremo libre: u_i = U·ρ^(n−i), ρ raíz < 1 de k̄ρ² − (2k̄ + k_b)ρ + k̄ = 0, k̄ = EA/s_r; F = k_b·U = k_b·k̄·e₀·s_r/(k̄(1 − ρ) + k_b). Acotada por la
  // restricción total σ = E·ε/(1 − ν) sobre t·s_t.
  function edgeForce(o) {
    const EA = o.E * o.t * o.st / (1 - o.nu * o.nu), kbar = EA / o.sr, e0 = (1 + o.nu) * Math.abs(o.eps), kb = o.kb;
    const bq = 2 * kbar + kb, rho = (bq - Math.sqrt(bq * bq - 4 * kbar * kbar)) / (2 * kbar);
    const F = kb * kbar * e0 * o.sr / (kbar * (1 - rho) + kb), Fcap = o.E * Math.abs(o.eps) / (1 - o.nu) * o.t * o.st;
    return Math.min(F, Fcap);
  }
  // Módulo aparente de la parte libre de la pastilla con el factor de forma S = d/(4·h) (como TT uhConf) y módulo confinado M (parte dentro del agujero)
  const Mf = (1 - NU_UH) / ((1 + NU_UH) * (1 - 2 * NU_UH));
  const EcOf = (E, S) => E * (1 + (Mf - 1) * S * S / (1 + S * S));

  /* ---------------- Contexto de carga y geometría desde el resultado del núcleo ---------------- */
  function ctxOf(P, R) {
    const Ro = P.D_top / 2, Ri = TT_.riOf(P), collar = P.h_boss > 0;
    const Rci = collar ? Math.max(Ri, P.D_boss / 2 + P.w_collar + 2) : Ri, Rco = Ro - 5;   // el portador libra el filete del collar y queda dentro de la huella de la mesa
    const kq = 4 * P.e * Ro / (Ro * Ro + Ri * Ri), Tcal = R.TmaxTopes || R.Tmax;
    const muMax = Math.max(R.mu.d, R.mu.cont, R.mu.dry), muEff = Math.max(muMax, Tcal * 1e6 / (R.N * 1e3 * R.r_u));
    const vcyl = P.Q_pump * 1e6 / 60 / (P.n_cyl * R.A), omega = vcyl / R.K.armMin;   // mm/s y rad/s (como la fila PV del núcleo: v = R·v_cil/a_mín)
    return { Ro, Ri, Rci, Rco, kq, muU: muMax, muRes: P.bx_mu_base_on >= 0.5 ? Math.max(0, muMax - P.bx_mu_base) : muMax, muB: P.bx_mu_base_on >= 0.5 ? P.bx_mu_base : 0, qa: R.q_avg, qmax: R.q_max, ND: R.ND, N: R.N, Tcal, muMax, muEff, vcyl, omega, prIn: TT_.prIn(P), dist: P.life * P.turns_yr * 2 * Math.PI / 1000 };
  }

  /* ---------------- Malla de pastillas y tapones ---------------- */
  const mod = (a, n) => ((a % n) + n) % n;
  function weldSite(q, r, nw) {   // subred de agujeros de soldadura en coordenadas axiales (q, r) de la red triangular (nw = 1: ninguno; los elige oneHop)
    if (nw <= 1) return false;
    if (nw === 3) return mod(q - r, 3) === 0;
    if (nw === 4) return mod(q, 2) === 0 && mod(r, 2) === 0;
    if (nw === 9) return mod(q, 3) === 0 && mod(r, 3) === 0;
    if (nw === 13) return mod(q + 4 * r, 13) === 0;
    return mod(q + 3 * r, nw) === 0;                                       // 7: código perfecto (cada sitio vecino de exactamente un tapón)
  }
  function sites(P, C, d, s, lig, nw, pat, dPlug, tc, drops) {
    if (Math.round(P.bx_forma) === 1) {   // cuadradas: malla cartesiana de paso s alineada con x (la CJP del disco); solo pastillas enteras (la franja de borde queda con el portador: conservador)
      const S0 = shp(P, d, tc || lig), best = [];
      for (const [ox, oy] of [[0, 0], [0.5, 0], [0.5, 0.5]]) {
        const o = [], n = Math.ceil(C.Rco / s) + 1;
        const r1 = C.Rco - lig, r0 = C.Rci + lig, ns = 16;
        for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) {
          const x = (i + ox) * s, y = (j + oy) * s;
          if (S0.rMax(x, y) <= r1 + 1e-9 && S0.rMin(x, y) >= r0 - 1e-9) { o.push({ x, y, r: Math.hypot(x, y), w: false, off: [ox, oy], hx: x, hy: y, f: 1 }); continue; }
          if (!(P.bx_borde >= 0.5) || S0.rMin(x, y) > r1 || S0.rMax(x, y) < r0) continue;
          let k = 0, sx = 0, sy = 0;   // pastilla recortada por el círculo: fracción y centroide por muestreo 16 × 16
          for (let u = 0; u < ns; u++) for (let v = 0; v < ns; v++) { const px = x - d / 2 + (u + 0.5) * d / ns, py = y - d / 2 + (v + 0.5) * d / ns, rr = Math.hypot(px, py); if (rr <= r1 && rr >= r0) { k++; sx += px; sy += py; } }
          const f = k / (ns * ns); if (f < P.bx_fmin) continue;
          const gx = sx / k, gy = sy / k; o.push({ x: gx, y: gy, r: Math.hypot(gx, gy), w: false, off: [ox, oy], hx: x, hy: y, f, trim: true });
        }
        const area = o.reduce((a, q) => a + q.f, 0);
      if (!best.length || area > best.area + 1e-9) { best.length = 0; o.forEach((q) => best.push(q)); best.area = area; }
      }
      return best;
    }
    const out = [], fitP = (r) => r - d / 2 >= C.Rci + lig - 1e-9 && r + d / 2 <= C.Rco - lig + 1e-9, fitW = fitP;   // el agujero de soldadura tiene el Ø de las pastillas
    const rO = C.Rco - lig - d / 2, rI = C.Rci + lig + d / 2;               // anillos de borde (exterior e interior): sin franjas de borde sin apoyo
    if (pat === 2) {
      const dr = s;                                                           // anillos a ≥ s: sin conflicto entre anillos de distinto N (no hay tresbolillo entre anillos)
      const nR = Math.floor((rO - rI) / dr + 1e-9) + 1, drE = nR > 1 ? (rO - rI) / (nR - 1) : 0;   // anillos repartidos entre el borde exterior y el interior
      for (let k = 0; k < nR; k++) {
        const r = rO - k * drE;
        const n = Math.floor(2 * Math.PI * r / s) - ((drops && drops[k]) || 0); if (n < 3) continue;   // drops: pastillas quitadas del anillo k (alivio de la torsión del portador en ese anillo)
        const edgeRing = k === 0 || k === nR - 1;                                // los anillos de borde entregan al filete perimetral: sin agujeros de soldadura
        for (let j = 0; j < n; j++) { const a = (j + (k % 2) * 0.5) * 2 * Math.PI / n, w = !edgeRing && nw > 1 && mod(j - 3 * k, nw) === 0; out.push({ x: r * Math.cos(a), y: r * Math.sin(a), r, w, ring: k }); }
      }
      return minDist(out, s);
    }
    // red triangular interior (anclada al centro) y un anillo de pastillas en cada borde (sin franjas de borde sin apoyo); los sitios de la red a menos de s
    // de una pastilla del anillo se descartan
    // anillo de pastillas en cada borde (r_O y r_I: sin franjas de borde sin apoyo), red triangular anclada al centro sin los sitios a menos de s del
    // anillo, y relleno voraz de la franja de unión (radios r_O − 0,6s … r_O − 2s y simétrico en el interior, ángulos finos): se agrega una pastilla
    // donde quede a ≥ s de todas
    const ringOf = (r) => { const n = Math.floor(2 * Math.PI * r / s); return n < 3 ? [] : Array.from({ length: n }, (_, j) => { const a = (j + 0.5) * 2 * Math.PI / n; return { x: r * Math.cos(a), y: r * Math.sin(a), r, w: false, ring: true }; }); };
    const twoR = rO - rI > 2 * s;
    ringOf(rO).concat(twoR ? ringOf(rI) : []).forEach((q) => out.push(q));
    const H0 = hashOf(out, s), free = (x, y) => { const cx = Math.floor(x / s), cy = Math.floor(y / s); for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) { const L = H0.get((cx + i) + "," + (cy + j)); if (L) for (const k of L) if (Math.hypot(out[k].x - x, out[k].y - y) < s - 1e-6) return false; } return true; };
    const put = (o) => { out.push(o); const k = Math.floor(o.x / s) + "," + Math.floor(o.y / s); if (!H0.has(k)) H0.set(k, []); H0.get(k).push(out.length - 1); };
    const h = s * Math.sqrt(3) / 2, J = Math.ceil(C.Rco / h) + 1, I = Math.ceil(C.Rco / s) + 2;
    for (let j = -J; j <= J; j++) for (let i = -I; i <= I; i++) {
      const x = i * s + mod(j, 2) * s / 2, y = j * h, r = Math.hypot(x, y), q = i - (j - mod(j, 2)) / 2, w = weldSite(q, j, nw);
      if (fitP(r) && free(x, y)) put({ x, y, r, w });
    }
    const fill = (r) => { if (r < rI - 1e-9 || r > rO + 1e-9) return; const n = Math.max(16, Math.ceil(2 * Math.PI * r / (s / 10))); for (let j = 0; j < n; j++) { const a = j * 2 * Math.PI / n, x = r * Math.cos(a), y = r * Math.sin(a); if (free(x, y)) put({ x, y, r, w: false, ring: true }); } };
    for (let k = 0; k <= 12; k++) fill(rO - 0.6 * s - k * s / 8);
    if (twoR) for (let k = 0; k <= 12; k++) fill(rI + 0.6 * s + k * s / 8);
    return minDist(out, s);
  }
  // separación mínima entre centros = s (ligamento ≥ lig): se descartan, en orden, los sitios que quedan a menos de s de uno ya aceptado
  function minDist(pts, s) {
    const acc = [], H = new Map(), key = (x, y) => Math.floor(x / s) + "," + Math.floor(y / s);
    pts.forEach((p) => { const cx = Math.floor(p.x / s), cy = Math.floor(p.y / s); for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) { const L = H.get((cx + i) + "," + (cy + j)); if (L) for (const q of L) if (Math.hypot(q.x - p.x, q.y - p.y) < s - 1e-6) return; }
      acc.push(p); const k = key(p.x, p.y); if (!H.has(k)) H.set(k, []); H.get(k).push(p); });
    return acc;
  }
  function hashOf(pts, cs) { const H = new Map(); pts.forEach((p, i) => { const k = Math.floor(p.x / cs) + "," + Math.floor(p.y / cs); if (!H.has(k)) H.set(k, []); H.get(k).push(i); }); return H; }
  function nearest(H, pts, cs, x, y) {
    const cx = Math.floor(x / cs), cy = Math.floor(y / cs);
    for (let R = 1; R <= 4; R++) {
      let best = -1, bd = Infinity;
      for (let i = -R; i <= R; i++) for (let j = -R; j <= R; j++) { const L = H.get((cx + i) + "," + (cy + j)); if (L) for (const k of L) { const dd = (pts[k].x - x) ** 2 + (pts[k].y - y) ** 2; if (dd < bd) { bd = dd; best = k; } } }
      if (best >= 0 && Math.sqrt(bd) <= R * cs) return best;
    }
    return -1;
  }
  // Presión de cada pastilla: la carga q(x, y) del núcleo (distribución lineal de Navier, q = q_med·(1 + k_q·x·û/R_o) con la excentricidad dirigida
  // hacia la pastilla: el peor caso para cada una) sobre su área tributaria (punto de muestreo → pastilla más cercana), dividida por el área de la cara.
  // Un salto: toda pastilla es vecina (a ≤ 1,3·s) de un agujero de soldadura o del borde del portador; las que no, se convierten en agujero de soldadura
  // (primero la que más pastillas sin camino directo tiene alrededor). Así el ligamento lleva solo el arrastre de una pastilla.
  function oneHop(all, s, C, d, lig) {
    const H = hashOf(all, s), thr = 1.3 * s, edge = (p) => C.Rco - (p.r + d / 2) <= 1.5 * lig + 1e-9 || p.r - d / 2 - C.Rci <= 1.5 * lig + 1e-9;
    const nb = all.map((p) => { const o = [], cx = Math.floor(p.x / s), cy = Math.floor(p.y / s); for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) { const L = H.get((cx + i) + "," + (cy + j)); if (L) L.forEach((m) => { if (all[m] !== p && Math.hypot(all[m].x - p.x, all[m].y - p.y) <= thr) o.push(m); }); } return o; });
    const bad = (m) => !all[m].w && !edge(all[m]) && !nb[m].some((v) => all[v].w);
    for (let guard = 0; guard < all.length; guard++) {
      const B = all.map((p, m) => m).filter(bad); if (!B.length) break;
      let best = -1, bs = -1;
      B.forEach((m) => { const sc = 1 + nb[m].filter(bad).length - (edge(all[m]) ? 10 : 0); if (sc > bs) { bs = sc; best = m; } });
      all[best].w = true; all[best].extra = true;
    }
    return all;
  }
  function layout(P, C, d, s, lig, nw, pat, dPlug, hs, tc, drops) {
    const s0 = sites(P, C, d, s, lig, nw, pat, dPlug, tc, drops), all = nw >= 1 ? oneHop(s0, s, C, d, lig) : s0, pucks = all.filter((q) => !q.w), welds = all.filter((q) => q.w);
    if (!pucks.length) return null;
    const SH = shp(P, d, tc || lig), H = hashOf(pucks, s), Ap = SH.Ap, n = Math.ceil(C.Ro / hs), dA = hs * hs;
    const acc = pucks.map(() => ({ A: 0, M: 0, Mx: 0, My: 0 }));
    for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) {
      const x = (i + 0.5) * hs, y = (j + 0.5) * hs, r = Math.hypot(x, y);
      if (r < C.Ri || r > C.Ro) continue;
      const k = nearest(H, pucks, s, x, y); if (k < 0) continue;
      const a = acc[k]; a.A += dA; a.Mx += x * dA; a.My += y * dA;
    }
    let pMax = 0, Nsum = 0, iMax = 0, Aint = 0;
    const lista = pucks.map((q, i) => {
      const a = acc[i], ur = q.r > 1e-9 ? [q.x / q.r, q.y / q.r] : [1, 0];
      const N = C.qa * (a.A + C.kq * (a.Mx * ur[0] + a.My * ur[1]) / C.Ro);   // N_i = ∫q dA con la excentricidad hacia la pastilla
      const Ai = Ap * (q.f || 1), p = N / Ai; Nsum += C.qa * a.A;
      if (p > pMax) { pMax = p; iMax = i; }
      if (q.r > C.Rci + 2 * s && q.r < C.Rco - 2 * s) Aint = Math.max(Aint, a.A);
      return { x: q.x, y: q.y, r: q.r, A: a.A, N, p, off: q.off, Ai, f: q.f || 1, trim: !!q.trim, hx: q.hx != null ? q.hx : q.x, hy: q.hy != null ? q.hy : q.y };
    });
    const FA = Math.max(...lista.map((q) => q.p * q.Ai)), Asum = lista.reduce((a, q) => a + q.Ai, 0);
    return { lig, drops: drops || null, all, pucks: lista, welds, pMax, iMax, Nsum, Ap, Aint: Aint || Math.max(...lista.map((q) => q.A)), cov: Asum / (Math.PI * (C.Ro * C.Ro - C.Ri * C.Ri)), SH, FA, Asum };
  }
  // Camino del arrastre en el portador: cada pastilla empuja la pared de su agujero; el portador lo lleva por los ligamentos hasta el tapón más cercano
  // (árbol de saltos: búsqueda en anchura desde los tapones; cada pastilla entrega a un vecino un salto más cerca). F_lig = mayor flujo por un ligamento;
  // demanda del tapón = suma de su grupo.
  function flow(L, s, F, C, d, lig) {
    const sitesA = L.pucks.map((q, i) => ({ x: q.x, y: q.y, i, w: false })).concat(L.welds.map((q, k) => ({ x: q.x, y: q.y, k, w: true })));
    const H = hashOf(sitesA, s), thr = 1.3 * s, nb = sitesA.map((p) => { const out = [], cx = Math.floor(p.x / s), cy = Math.floor(p.y / s);
      for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) { const Lc = H.get((cx + i) + "," + (cy + j)); if (Lc) Lc.forEach((m) => { if (sitesA[m] !== p && Math.hypot(sitesA[m].x - p.x, sitesA[m].y - p.y) <= thr) out.push(m); }); }
      return out.sort((a, b) => Math.hypot(sitesA[a].x - p.x, sitesA[a].y - p.y) - Math.hypot(sitesA[b].x - p.x, sitesA[b].y - p.y)); });
    const hop = sitesA.map((p) => (p.w ? 0 : Infinity)), parent = sitesA.map(() => -1), root = sitesA.map((p, m) => (p.w ? m : -1)), Qq = [];
    sitesA.forEach((p, m) => { if (p.w) Qq.push(m); });
    // pastillas del borde: su ligamento al canto del portador (≥ lig) lleva el arrastre al filete perimetral (1 salto)
    const edge = (p) => { const r = Math.hypot(p.x, p.y); return C.Rco - (r + d / 2) <= 1.5 * lig + 1e-9 || r - d / 2 - C.Rci <= 1.5 * lig + 1e-9; };
    sitesA.forEach((p, m) => { if (!p.w && edge(p)) { hop[m] = 1; parent[m] = -2; Qq.push(m); } });
    for (let h = 0; h < Qq.length; h++) { const m = Qq[h]; for (const v of nb[m]) if (hop[v] === Infinity) { hop[v] = hop[m] + 1; parent[v] = m; root[v] = root[m]; Qq.push(v); } }
    const order = sitesA.map((p, m) => m).filter((m) => !sitesA[m].w).sort((a, b) => hop[b] - hop[a]), fl = sitesA.map((p) => (p.w ? 0 : F(p.i)));
    let Flig = 0, hMax = 0, nAdj = Infinity, edgeMax = 0, nEdge = 0;
    order.forEach((m) => { if (!isFinite(hop[m])) return; hMax = Math.max(hMax, hop[m]); Flig = Math.max(Flig, fl[m]); if (parent[m] === -2) { edgeMax = Math.max(edgeMax, fl[m]); nEdge++; } else fl[parent[m]] += fl[m]; });
    const unreached = order.filter((m) => !isFinite(hop[m])).length;
    const plugF = sitesA.filter((p) => p.w).map((p, k) => fl[L.pucks.length + k]);
    sitesA.forEach((p, m) => { if (p.w) nAdj = Math.min(nAdj, nb[m].filter((v) => !sitesA[v].w).length); });
    return { Flig, hMax, unreached, plugMax: plugF.length ? Math.max(...plugF) : 0, plugF, nAdj: isFinite(nAdj) ? nAdj : 0, edgeMax, nEdge };
  }

  // Transferencia perimetral (sin agujeros de soldadura): el portador es una plancha perforada soldada a la base solo por sus bordes exterior e interior
  // (filetes continuos). Cada pastilla entrega F_i = μ_ef·p_i·A_p (tangencial) al portador; el par se reparte entre los bordes según la flexibilidad a
  // torsión de la corona perforada, C(ρ₁, ρ₂) = ∫ dr/(r³·η(r)) (η = fracción de acero del círculo de radio r, exacta con las cuerdas de los agujeros);
  // la pastilla en ρ manda al borde exterior la fracción C_int(ρ)/(C_int + C_ext). Corte en el círculo r: τ(r) = T_cruza(r)/(2π·r²·t·η(r)).
  function torsion(L, C, d, t, Ffn, coarse) {
    const a = C.Rci, b = C.Rco, nG = coarse ? 120 : L.SH && L.SH.sq ? 300 : 600, hG = (b - a) / nG, R = d / 2, P_ = L.pucks.concat(L.welds.map((q) => ({ x: q.x, y: q.y, r: q.r, hole: true })));
    const eta = new Float64Array(nG + 1), rr = new Float64Array(nG + 1), SQ = L.SH && L.SH.sq, cs = d, HH = SQ ? hashOf(P_.map((q) => Object.assign({}, q, { x: q.hx != null ? q.hx : q.x, y: q.hy != null ? q.hy : q.y, cxq: q.x })), d) : null, lig0 = L.lig || 0;
    for (let k = 0; k <= nG; k++) {
      const r = a + k * hG; rr[k] = r; let arc = 0;
      if (SQ) {   // agujeros cuadrados: fracción del círculo dentro de los agujeros por muestreo angular (paso ≤ 2 mm)
        const nA = coarse ? Math.max(180, Math.ceil(2 * Math.PI * r / 8)) : Math.max(360, Math.ceil(2 * Math.PI * r / 3)); let inn = 0;
        for (let j = 0; j < nA; j++) { const t = (j + 0.5) * 2 * Math.PI / nA, x = r * Math.cos(t), y = r * Math.sin(t), cx = Math.floor(x / cs), cy = Math.floor(y / cs); let hit = false;
          for (let i2 = -1; i2 <= 1 && !hit; i2++) for (let j2 = -1; j2 <= 1 && !hit; j2++) { const Lh = HH.get((cx + i2) + "," + (cy + j2)); if (Lh) for (const q of Lh) if (L.SH.inHole(x, y, q.hx != null ? q.hx : q.x, q.hy != null ? q.hy : q.y) && (!q.trim || (r <= C.Rco - lig0 && r >= C.Rci + lig0))) { hit = true; break; } }
          if (hit) inn++; }
        arc = inn / nA * 2 * Math.PI * r;
      } else for (const q of P_) { if (Math.abs(q.r - r) >= R) continue; const c = (r * r + q.r * q.r - R * R) / (2 * r * q.r); arc += 2 * Math.acos(Math.max(-1, Math.min(1, c))) * r; }
      eta[k] = Math.max(1e-3, 1 - arc / (2 * Math.PI * r));
    }
    const cum = new Float64Array(nG + 1);                                  // ∫_a^r dr/(r³η)
    for (let k = 1; k <= nG; k++) cum[k] = cum[k - 1] + hG * 0.5 * (1 / (rr[k - 1] ** 3 * eta[k - 1]) + 1 / (rr[k] ** 3 * eta[k]));
    const Ctot = cum[nG], at = (r) => { const x = Math.max(0, Math.min(nG, (r - a) / hG)), k = Math.min(nG - 1, Math.floor(x)); return cum[k] + (cum[k + 1] - cum[k]) * (x - k); };
    const T = L.pucks.map((q, i) => ({ r: q.r, Tq: Ffn(i) * q.r, fo: at(q.r) / Ctot }));
    let Tout = 0, Tin = 0; T.forEach((o) => { Tout += o.Tq * o.fo; Tin += o.Tq * (1 - o.fo); });
    let tauMax = 0, rCrit = b, etaCrit = 1, Tcrit = 0;
    for (let k = 0; k <= nG; k++) {
      const r = rr[k]; let To = 0, Ti = 0;
      T.forEach((o) => { if (o.r < r) To += o.Tq * o.fo; else Ti += o.Tq * (1 - o.fo); });
      const Tc = Math.max(To, Ti), tau = Tc / (2 * Math.PI * r * r * t * eta[k]);
      if (tau > tauMax) { tauMax = tau; rCrit = r; etaCrit = eta[k]; Tcrit = Tc; }
    }
    return { tauMax, rCrit, etaCrit, Tcrit, Tout, Tin, Ttot: Tout + Tin };
  }

  /* ---------------- Malla de tornillos disco–mesa ---------------- */
  function boltLayout(P, C, d, sb, tss) {
    const rings = TT_.parseRings(P.rings), dk = isoDk(d), cA = P.bx_c_alma, out = [];
    const bandOf = (r) => { for (const rw of rings) { const h = P.t_web / 2 + P.w_web + d / 2 + cA; if (Math.abs(r - rw) < h) return rw + h; } const hp = 10 + d / 2; if (Math.abs(r - C.prIn) < hp) return C.prIn + hp; return null; };
    const eIn = Math.max(J34M(d), 1.5 * d), eOut = Math.max(J34M(d), 1.5 * d);
    const r0 = Math.max(P.D_hub / 2 + P.w_web + d / 2 + cA, C.Ri + eIn), r1 = C.Ro - eOut, radii = [];
    let r = r0, guard = 0;
    while (r <= r1 + 1e-9 && guard++ < 200) { const b = bandOf(r); if (b != null) { r = b; continue; } radii.push(r); r += sb; }
    if (radii.length && r1 - radii[radii.length - 1] > 0.5 * sb && bandOf(r1) == null) radii.push(r1);       // anillo de borde
    const ribAng = Array.from({ length: P.N_rib }, (_, k) => k * 2 * Math.PI / P.N_rib), pins = Array.from({ length: P.N_pin }, (_, k) => (k + 0.5) * 2 * Math.PI / P.N_pin).map((a) => [P.R_pin * Math.cos(a), P.R_pin * Math.sin(a)]);
    const okPt = (x, y, rr) => {
      if (Math.abs(y) < P.bx_c_cjp) return false;                                                       // franja de la CJP (eje x)
      if (rr <= P.R_rib + P.t_rib / 2 + P.w_web + d / 2 + cA) for (const a of ribAng) { const along = x * Math.cos(a) + y * Math.sin(a), lat = Math.abs(-x * Math.sin(a) + y * Math.cos(a)); if (along > 0 && lat < P.t_rib / 2 + P.w_web + d / 2 + cA) return false; }
      for (const p of pins) if (Math.hypot(x - p[0], y - p[1]) < P.d_pin / 2 + d / 2 + 3 + d) return false;   // ligamento ≥ d al agujero del pasador
      return true;
    };
    radii.forEach((rr, k) => {
      const nmin = Math.max(4, Math.ceil(2 * Math.PI * rr / sb)), sym = rr < C.prIn ? P.N_rib : P.N_pin, n = Math.ceil(nmin / sym) * sym;
      let best = null;
      for (const off of [0.5, 0.25, 0.75, 0]) { const pts = []; for (let j = 0; j < n; j++) { const a = (j + off) * 2 * Math.PI / n, x = rr * Math.cos(a), y = rr * Math.sin(a); if (okPt(x, y, rr)) pts.push({ x, y, r: rr, ring: k, a: a / D2R }); } if (!best || pts.length > best.length) best = pts; }
      best.forEach((b) => out.push(b));
    });
    // pieza roscada: anillo inferior de pasadores (ciego, remanente 3 mm) o plancha inferior (pasante)
    out.forEach((b) => { b.anillo = b.r - d / 2 > C.prIn + 1e-9; });
    let sMin = Infinity; const H = hashOf(out, Math.max(sb, 40));
    out.forEach((b) => { const cx = Math.floor(b.x / Math.max(sb, 40)), cy = Math.floor(b.y / Math.max(sb, 40)); for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) { const L = H.get((cx + i) + "," + (cy + j)); if (L) L.forEach((m) => { if (out[m] !== b) sMin = Math.min(sMin, Math.hypot(out[m].x - b.x, out[m].y - b.y)); }); } });
    const ringR = [...new Set(out.map((b) => b.r))].sort((a, b) => a - b);
    return { lista: out, radii: ringR, sMin, dk, eIn, eOut };
  }
  function boltForces(P, C, R, M, d, sb, t, BL, dTd) {
    const Ab = Math.PI / 4 * d * d, n = BL.lista.length, rr = BL.lista.map((b) => b.r), J = rr.reduce((s, r) => s + r * r, 0), T = C.Tcal * 1e6;
    BL.lista.forEach((b) => { b.VT = T * b.r / J; });
    const ringsR = BL.radii, nOf = (r) => BL.lista.filter((b) => Math.abs(b.r - r) < 1e-6).length;
    const tb = (b) => (b.anillo ? P.t_pr : P.t_bot), eps = (M.al - P.bx_al_st * 1e-6) * dTd;
    // Componente térmica (SECUNDARIA, autolimitante): franja radial de ancho w = paso tangencial del anillo exterior, nudos en los anillos (r = 0 fijo por
    // simetría, borde libre en R_o), barra E·t·w/(1 − ν²) con deformación libre (1 + ν)·ε (deformación anular impedida, conservador) y en cada anillo
    // los resortes de sus tornillos (Huth) dentro de la franja: la fuerza se reparte entre los anillos según su rigidez (mesa rígida, conservador).
    const ringsSt = ringsR.map((r) => 2 * Math.PI * r / Math.max(1, nOf(r))), wS = ringsSt[ringsSt.length - 1], EA = M.E * t * wS / (1 - M.nu * M.nu), e0 = (1 + M.nu) * Math.abs(eps);
    const kbR = ringsR.map((r) => huth(t, M.E, r - d / 2 > C.prIn ? P.t_pr : P.t_bot, P.E, d)), Ks = ringsR.map((r, i) => kbR[i] * wS / ringsSt[i]);
    const m = ringsR.length, A_ = [], B_ = [], C_ = [], R_ = [];
    for (let i = 0; i < m; i++) { const Li = ringsR[i] - (i ? ringsR[i - 1] : 0), kL = EA / Li, kR = i < m - 1 ? EA / (ringsR[i + 1] - ringsR[i]) : 0;
      A_.push(-kL); B_.push(kL + kR + Ks[i]); C_.push(-kR); R_.push(kL * e0 * Li - (i < m - 1 ? kR * e0 * (ringsR[i + 1] - ringsR[i]) : 0)); }
    const cp_ = [], dp_ = [], u = new Array(m);
    for (let i = 0; i < m; i++) { const den = B_[i] - (i ? A_[i] * cp_[i - 1] : 0); cp_[i] = C_[i] / den; dp_[i] = (R_[i] - (i ? A_[i] * dp_[i - 1] : 0)) / den; }
    for (let i = m - 1; i >= 0; i--) u[i] = dp_[i] - (i < m - 1 ? cp_[i] * u[i + 1] : 0);
    const Fring = u.map((x, i) => Math.abs(kbR[i] * x));
    const out = { F: Fring[m - 1] || 0, st: wS, sr: m > 1 ? ringsR[m - 1] - ringsR[m - 2] : 0, kb: kbR[m - 1] || 0, porAnillo: Fring }, inn = { F: Fring[0] || 0, kb: kbR[0] || 0 };
    BL.lista.forEach((b) => { const i = ringsR.findIndex((r) => Math.abs(r - b.r) < 1e-6); b.Vth = i >= 0 ? Fring[i] : 0; b.V = Math.hypot(b.VT, b.Vth); });
    const worst = BL.lista.reduce((w, b) => (!w || b.V > w.V ? b : w), null);
    const Fnv = 0.45 * P.Fu_bolt, capV = Fnv / 2 * Ab;                        // AISC J3.7: Fnv = 0,45·Fu (rosca en el plano), Ω = 2,00; Fu_bolt del núcleo (10.9)
    const k = isoK(d), te = t - k / 2, dh = d + 1, lcEdge = (C.Ro - ringsR[ringsR.length - 1]) - dh / 2, lcIn = (ringsR[0] - C.Ri) - dh / 2;
    const RnSS = (lc) => Math.min(1.2 * lc * te * M.Fu, 2.4 * d * te * M.Fu);
    const capT = 0.75 * P.Fu_bolt / 2 * Ab, Tup = P.phi_lift * (M.rho * Math.PI * (C.Ro ** 2 - C.Ri ** 2) * t) * G / n;   // tracción: disco colgado al izar la mesa
    const wP = BL.lista.reduce((w, b) => (!w || b.VT > w.VT ? b : w), null);
    return { n, Ab, J, T, worst, wP, V_prim: wP.VT, V_comb: worst.V, VT_max: Math.max(...BL.lista.map((b) => b.VT)), Fth_out: out.F, Fth_in: inn.F, th_out: out, th_in: inn, capV, Fnv, eps, dTd,
      te, dh, lcEdge, lcIn, RnSS_edge: RnSS(lcEdge), RnSS_in: RnSS(lcIn), RnSS_int: RnSS(Math.max(BL.sMin - dh, 0)), capT, Tup, k };
  }

  /* ---------------- Dimensionamiento ---------------- */
  const LIST_D = [60, 80, 100, 120, 140, 160, 170, 180, 184, 200, 240, 300];   // Ø nominales del agujero; se usan los de Ø + 1 ≤ bx_dp_max (la interferencia ≤ 1 mm entra en el corte)
  const LIST_A = [100, 125, 150, 175, 200, 225, 250, 275, 300];   // el mandante pidió 150–300; se agregan 100 y 125 porque la pared y el tornillo limitan el lado                      // lado de la pastilla cuadrada
  // Geometría de la pastilla según la forma: d = Ø (redonda) o lado (cuadrada); r_c = radio de esquina del agujero, la pastilla r_c + 1
  function shp(P, d, tc) {
    const sq = Math.round(P.bx_forma) === 1, rc = sq ? (P.bx_rc > 0 ? P.bx_rc : Math.max(5, 0.5 * tc)) : 0, rcp = sq ? rc + 1 : 0;
    const Ap = sq ? d * d - (4 - Math.PI) * rcp * rcp : Math.PI * d * d / 4, ApH = sq ? d * d - (4 - Math.PI) * rc * rc : Math.PI * d * d / 4;
    const inHole = (x, y, cx, cy) => { if (!sq) return Math.hypot(x - cx, y - cy) < d / 2; const u = Math.abs(x - cx), v = Math.abs(y - cy), h = d / 2; if (u > h || v > h) return false; if (u <= h - rc || v <= h - rc) return true; return Math.hypot(u - (h - rc), v - (h - rc)) <= rc; };
    return { sq, rc, rcp, Ap, ApH, kern: sq ? d / 6 : d / 8, aEq: Math.sqrt(Ap / Math.PI), inHole, rMax: (x, y) => sq ? Math.hypot(Math.abs(x) + d / 2, Math.abs(y) + d / 2) : Math.hypot(x, y) + d / 2,
      rMin: (x, y) => sq ? Math.hypot(Math.max(0, Math.abs(x) - d / 2), Math.max(0, Math.abs(y) - d / 2)) : Math.max(0, Math.hypot(x, y) - d / 2) };
  }
  const LIST_SB = [250, 225, 200, 175, 150, 125, 100, 75, 50];
  const UH_PL = [20, 25, 30, 40, 50];                                     // espesores comerciales de plancha UHMW para cortar las pastillas
  function puckEval(P, C, M, L, d, s, tc, lig, nw, hp, tss, dPlug, kE) {
    // magnitudes por pastilla (las que dependen de h_p y del espesor) y peor caso; kE: factor del módulo del UHMW a la temperatura evaluada
    const Ap = L.Ap, E = P.E_uhmw * (kE || 1), dF = P.d_flat + P.bx_tol_H, S = d / (4 * hp), Ec = EcOf(E, S), Mc = E * Mf, cp = hp / Ec + (tc - 1) / Mc;   // flexibilidad por unidad de área (mm/MPa)
    const Dm = (tm) => P.E * tm ** 3 / (12 * (1 - P.nu ** 2)), Dss = M.E * tss ** 3 / (12 * (1 - M.nu ** 2));
    let worst = { pd: -1 }, PVm = 0, iPV = 0;
    L.pucks.forEach((q, i) => {
      const tm = q.r > C.prIn ? Math.max(P.t_pr, P.t_bot) : P.t_bot, kpl = 16 * Math.PI * (Dss + Dm(tm)) / (s * s), dp = dF / (cp + (q.Ai || Ap) / kpl);
      if (q.p + dp > worst.pd) worst = { pd: q.p + dp, dp, i, kpl, tm };
      const pv = q.p * q.r * C.omega / 1000; if (pv > PVm) { PVm = pv; iPV = i; }
    });
    const pM = L.pMax, Fi = C.muEff * (L.FA || pM * Ap), FiU = C.muRes * (L.FA || pM * Ap), FiU0 = C.muU * (L.FA || pM * Ap), creep = pM * cp, wear = P.k_wear * 1e-7 * pM * C.dist * Math.max(...L.pucks.map((q) => q.r));
    return { S, Ec, Mc, cp, worst, PVm, iPV, Fi, FiU, FiU0, creep, wear };
  }
  function cellOf(P, C, M, L, d, tss, s) {
    const sq = L.SH && L.SH.sq, Acell = sq ? s * s : s * s * Math.sqrt(3) / 2 * 7 / 6;   // celda (cuadrada: s²; triangular con el reparto del sitio soldado vecino); los huecos irregulares van en el vacío local
    const b = Math.sqrt(Acell / Math.PI), a = sq ? L.SH.aEq : d / 2, te = tss - P.ss_allow, Ds = M.E * te ** 3 / (12 * (1 - M.nu ** 2));
    if (lamOn(P)) {   // modo 1: la lámina soldada no flexiona sola: plancha inferior de la mesa + lámina con la misma curvatura (la plancha toma D_m/(D_m + D_s)
      // del momento; la lámina, solidaria por los tapones, sigue la deformación de la cara de la plancha: σ_s = E_s·κ·(t_inf/2 + t_e), cota de sección compuesta)
      const tb = P.t_bot, Dm = P.E * tb ** 3 / (12 * (1 - P.nu ** 2)), D = Dm + Ds;
      const c = b > a + 1e-6 ? cellPlate(C.qmax, a, b, D, P.nu) : { Mmax: 0, w: 0, Ma: 0, Mb: 0 };
      const sigPl = 6 * c.Mmax * Dm / D / (tb * tb), sigSs = M.E * c.Mmax / D * (tb / 2 + te);
      return { a, b, te, D, Dm, Ds, c, sig: sigSs, sigPl, sigSs, w: Math.abs(c.w), fu: Math.max(sigSs / (0.6 * M.Fy), sigPl / (0.6 * P.Fy)), lam: true };
    }
    const D = Ds, c = b > a + 1e-6 ? cellPlate(C.qmax, a, b, D, M.nu) : { Mmax: 0, w: 0, Ma: 0, Mb: 0 }, sig = 6 * c.Mmax / (te * te);
    return { a, b, te, D, c, sig, w: Math.abs(c.w), fu: sig / (0.6 * M.Fy) };
  }
  // Espesor del disco: (1) cabeza avellanada + 0,5 + sobreespesor; (2) vacío local Ø ss_void sin contacto con el respaldo (disco solo, como el núcleo);
  // (3) hueco de la malla (pastilla faltante o mayor hueco, radio a_g): el disco y la plancha de la mesa se curvan juntos (están atornillados y en
  // contacto) y el disco toma la fracción D_disco/(D_disco + D_mesa) del momento de la placa empotrada q·a²/8; (4) celda entre pastillas; (5) t_mín.
  function discT(P, C, M, L, d, s, tHead, tFix) {
    const sad = 0.6 * M.Fy, aV = P.ss_void / 2, tVoid = aV * Math.sqrt(0.75 * C.qmax / sad), aG = Math.max(L.SH && L.SH.sq ? (2 * s - d) / Math.SQRT2 : s - d / 2, Math.sqrt(Math.max(...L.pucks.map((q) => q.A)) / Math.PI));   // cuadrada: pastilla faltante = hueco cuadrado de lado 2s − a, se toma el círculo circunscrito
    const Dm = P.E * P.t_bot ** 3 / (12 * (1 - P.nu ** 2));
    const gap = (t) => { const te = t - P.ss_allow, Ds = M.E * te ** 3 / (12 * (1 - M.nu ** 2)), sh = Ds / (Ds + Dm); return { sh, sig: 6 * C.qmax * aG * aG / 8 * sh / (te * te) }; };
    if (lamOn(P)) {   // modo 1: espesor fijo de la plancha espejo; pastilla faltante: plancha de la mesa + lámina (misma curvatura, lámina en la cara de la plancha)
      const t = tFix != null ? tFix : P.bx_t_lam, te = t - P.ss_allow, tb = P.t_bot, Ds = M.E * te ** 3 / (12 * (1 - M.nu ** 2)), Mg = C.qmax * aG * aG / 8;
      const sigPl = 6 * Mg * Dm / (Dm + Ds) / (tb * tb), sigSs = M.E * Mg / (Dm + Ds) * (tb / 2 + te), sh = Ds / (Ds + Dm);
      return { t, tReq: t, aV, tVoid: 0, aG, gap: { sh, sig: sigSs, sigPl, M: Mg, fu: Math.max(sigSs / sad, sigPl / (0.6 * P.Fy)) }, sad, lam: true };
    }
    const tReq = Math.max(tHead, tVoid + P.ss_allow, P.ss_tmin);
    const ok = (t) => t >= tReq - 1e-9 && gap(t).sig <= sad && cellOf(P, C, M, L, d, t, s).sig <= sad;
    const t = tFix != null ? tFix : (SS_COMM.find(ok) || SS_COMM[SS_COMM.length - 1]);
    return { t, tReq, aV, tVoid, aG, gap: gap(t), sad };
  }
  /* ---------------- Modo 1: lámina de 3 mm soldada con tapones y costura perimetral ---------------- */
  const LIST_SP = [300, 275, 250, 225, 200, 175, 150, 140, 130, 120, 110, 100, 95, 90, 85, 80, 75, 70, 65, 60];
  // Paneles: franjas paralelas a x de ancho ≤ formato − 2·margen (juntas a tope sobre y = cte; con 2 franjas la junta es el eje x, como la CJP del modo 0)
  function lamPanels(P, Rlo, rho) {
    const m = 10, a = P.bx_fmt_a - 2 * m, b = P.bx_fmt_b - 2 * m, n = Math.max(1, Math.ceil(2 * Rlo / a - 1e-9)), w = 2 * Rlo / n, out = [], juntas = [];
    for (let k = 0; k < n; k++) {
      const y0 = -Rlo + k * w, y1 = y0 + w, yc = y0 <= 0 && y1 >= 0 ? 0 : Math.min(Math.abs(y0), Math.abs(y1)), largo = 2 * Math.sqrt(Math.max(0, Rlo * Rlo - yc * yc));
      const seg = (y) => { const c = Math.max(-1, Math.min(1, y / Rlo)); return Rlo * Rlo * (Math.asin(c) + c * Math.sqrt(1 - c * c)); };   // área del círculo bajo y (×2/2)
      const area = seg(y1) - seg(y0);
      out.push({ id: "L" + (k + 1), y0, y1, ancho: w, largo, area_bruta: area, cabe: w <= a + 1e-9 && largo <= b + 1e-9 });
      if (k) juntas.push(y0);
    }
    return { m, n, w, paneles: out, juntas, cabe: out.every((q) => q.cabe), largo_juntas: juntas.reduce((s, y) => s + 2 * Math.sqrt(Math.max(0, Rlo * Rlo - y * y)), 0) };
  }
  // Tapones: anillos en las bandas libres entre las pistas que barren las pastillas (el disco gira sobre pastillas fijas: un tapón fuera de las pistas
  // no pasa nunca bajo una pastilla) y anillos adicionales donde el hueco radial entre apoyos (costuras y anillos) supera el paso de pandeo s_r,máx.
  function lamDesign(P, C, M, L, d, tss, dTd, spFix) {
    const t = tss, te = t - P.ss_allow, D = P.bx_d_tap, e = 1.5 * D, Rlo = C.Ro - P.bx_c_lam, Rli = C.Ri + P.bx_c_lam, cl = P.bx_c_pista, Nd = P.Nd, SH = L.SH;
    const dAl = Math.abs(M.al - P.bx_al_st * 1e-6), sTh1 = M.E * dAl * dTd, sTh = sTh1 / (1 - M.nu), Kp = Math.PI ** 2 * M.E / (12 * (1 - M.nu ** 2));
    const srMax = sTh > 0 ? Math.min(400, te * Math.sqrt(2 * Kp * 0.8 / sTh)) : 400;   // panel cuadrado k = 2 con σ/σ_cr = 0,8
    const PN = lamPanels(P, Rlo);
    const tr = L.pucks.map((q) => [SH.rMin(q.hx, q.hy) - cl, SH.rMax(q.hx, q.hy) + cl]).sort((a, b) => a[0] - b[0]), trk = [];
    tr.forEach(([a, b]) => { const l = trk[trk.length - 1]; if (l && a <= l[1]) l[1] = Math.max(l[1], b); else trk.push([a, b]); });
    const inTrack = (r) => trk.some(([a, b]) => r + D / 2 > a && r - D / 2 < b);
    const lo = Rli + e, hi = Rlo - e, free = []; let cur = lo;
    for (const [a, b] of trk) { const f1 = Math.min(a - D / 2, hi); if (f1 >= cur - 1e-9) free.push([cur, f1]); cur = Math.max(cur, b + D / 2); if (cur > hi) break; }
    if (cur <= hi + 1e-9) free.push([cur, hi]);
    const base = free.map(([a, b]) => (a + b) / 2), sup = [Rli].concat(base, [Rlo]), radii = [];
    for (let i = 0; i < sup.length - 1; i++) {
      if (i > 0) radii.push({ r: sup[i], pista: false });
      const g = sup[i + 1] - sup[i], k = Math.max(0, Math.ceil(g / srMax - 1e-9) - 1);
      for (let j = 1; j <= k; j++) { const r = Math.max(lo, Math.min(hi, sup[i] + g * j / (k + 1))); radii.push({ r, pista: inTrack(r), extra: true }); }
    }
    radii.sort((a, b) => a.r - b.r);
    const pins = Array.from({ length: P.N_pin }, (_, k) => (k + 0.5) * 2 * Math.PI / P.N_pin).map((a) => [P.R_pin * Math.cos(a), P.R_pin * Math.sin(a)]);
    const yJ = PN.juntas, cJ = Math.max(P.bx_c_cjp, e);
    const okPt = (x, y) => yJ.every((yj) => Math.abs(y - yj) >= cJ - 1e-9) && pins.every((p) => Math.hypot(x - p[0], y - p[1]) >= P.d_pin / 2 + D / 2 + 3 + D);
    const T = C.Tcal * 1e6, Fw = P.bx_FEXX_ss * (P.__th && P.__th.k ? P.__th.k.weld : 1) * 0.60 / (1.20 * Nd), Aw = Math.PI / 4 * D * D, capW = Fw * Aw;
    // lámina alrededor del tapón: AISI S100-16 §J2.2.2.2 (= ASCE 8-02 §5.2.2 para inoxidable), d_a = Ø − t; Ω de la especificación
    const da = D - te, lam_ = da / te, rEF = Math.sqrt(M.E / M.Fu), PnS = lam_ <= 0.815 * rEF ? 2.20 * te * da * M.Fu : lam_ < 1.397 * rEF ? 0.280 * (1 + 5.59 * rEF / lam_) * te * da * M.Fu : 1.40 * te * da * M.Fu, OmS = lam_ <= 0.815 * rEF ? 2.20 : 2.80, capS = PnS / OmS;
    const cap = Math.min(capW, capS), Fpk = L.pucks.map((q) => C.muEff * q.p * q.Ai);
    const evalSp = (sc) => {
      const pts = [], rings = [];
      radii.forEach((R0, k) => {
        const r = R0.r, nMax = Math.floor(Math.PI / Math.asin(Math.min(1, 2 * D / r)) + 1e-9), n = Math.max(3, Math.min(Math.ceil(2 * Math.PI * r / sc - 1e-9), nMax));
        let best = null;
        for (const off of [0.5, 0.25, 0.75, 0]) { const q = []; for (let j = 0; j < n; j++) { const a = (j + off) * 2 * Math.PI / n, x = r * Math.cos(a), y = r * Math.sin(a); if (okPt(x, y)) q.push({ x, y, r, ring: k, pista: R0.pista }); } if (!best || q.length > best.length) best = q; }
        best.forEach((q) => pts.push(q)); rings.push({ r, n: best.length, n_div: n, pista: R0.pista, extra: !!R0.extra, paso: 2 * Math.PI * r / n });
      });
      if (!pts.length) return null;
      const J = pts.reduce((s, q) => s + q.r * q.r, 0); pts.forEach((q) => { q.V = T * q.r / J; });
      const Vmax = Math.max(...pts.map((q) => q.V));
      // apoyos radiales y paso máximo: panel de pandeo y de despegue
      const supR = [Rli].concat(rings.map((q) => q.r), [Rlo]); let gapR = 0; for (let i = 1; i < supR.length; i++) gapR = Math.max(gapR, supR[i] - supR[i - 1]);
      const arc = Math.max(...rings.map((q) => q.paso)), ap = Math.max(gapR, arc);
      // separación mínima entre tapones
      let sMin = Infinity; const cs = Math.max(4 * D, 20), H = hashOf(pts, cs);
      pts.forEach((q) => { const cx = Math.floor(q.x / cs), cy = Math.floor(q.y / cs); for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) { const Lc = H.get((cx + i) + "," + (cy + j)); if (Lc) Lc.forEach((m) => { if (pts[m] !== q) sMin = Math.min(sMin, Math.hypot(pts[m].x - q.x, pts[m].y - q.y)); }); } });
      if (!isFinite(sMin)) sMin = Infinity;
      // arrastre local: tapones a ≤ d/2 + a_p/2 del centro de la pastilla, mínimo sobre 24 posiciones relativas del disco (gira) dentro de un paso
      const rho = d / 2 + ap / 2, phMax = 2 * Math.PI / Math.max(...rings.map((q) => q.n_div)); let loc = { F: 0, n: Infinity, V: 0, i: -1 };
      L.pucks.forEach((q, i) => { let nmin = Infinity;
        for (let k = 0; k < 24; k++) { const ph = k * phMax / 24, c = Math.cos(ph), s_ = Math.sin(ph); let n = 0; pts.forEach((p) => { const x = p.x * c - p.y * s_, y = p.x * s_ + p.y * c; if (Math.hypot(x - q.x, y - q.y) <= rho) n++; }); nmin = Math.min(nmin, n); }
        const V = Fpk[i] / Math.max(nmin, 1e-9); if (V > loc.V) loc = { F: Fpk[i], n: nmin, V, i }; });
      const sCr = 2 * Kp * (te / ap) ** 2, tCr = 9.34 * Kp * (te / ap) ** 2, Fmax = Math.max(...Fpk), tau = 2 * Fmax / (Math.PI * d * te);
      const inter = sTh / sCr + (tau / tCr) ** 2;
      const eReq = Math.max(1.5 * D, 2.0 * Vmax / (M.Fu * te)), eAv = Math.min(...pts.map((q) => Math.min(Rlo - q.r, q.r - Rli)));
      const Dp = M.E * te ** 3 / (12 * (1 - M.nu ** 2)), blist = (a) => ({ a, pc: 64 * Dp * P.bx_g0 / a ** 4, sig: 4 * M.E * te * P.bx_g0 / ((1 - M.nu ** 2) * a * a) });
      const bP = blist(ap / 2), pMin = Math.min(...L.pucks.map((q) => q.p));
      const fus = [Vmax / capW, Vmax / capS, loc.V / cap, sTh / sCr, inter, bP.sig / (2 * M.Fy)].map((f) => f / 0.9).concat([bP.pc / pMin, 4 * D / sMin, eReq / eAv]);
      return { sc, pts, rings, J, Vmax, gapR, arc, ap, sMin, rho, loc, sCr, tCr, tau, inter, eReq, eAv, bP, pMin, fus, fu: Math.max(...fus), Fmax };
    };
    let best = null;
    if (spFix) best = evalSp(spFix);
    else for (const sc of (P.bx_s_tap > 0 ? [P.bx_s_tap] : LIST_SP.filter((x) => x >= 4 * D))) { const r = evalSp(sc); if (!r) continue; best = r; if (r.fu <= 1 + 1e-9) break; }
    const Dp = M.E * te ** 3 / (12 * (1 - M.nu ** 2)), aV = P.ss_void / 2, bV = { a: aV, pc: 64 * Dp * P.bx_g0 / aV ** 4, sig: 4 * M.E * te * P.bx_g0 / ((1 - M.nu ** 2) * aV * aV) };
    const qT = T / (2 * Math.PI * Rlo * Rlo), qTh = sTh * te, w = P.bx_w_lam, capSeamW = Fw * 0.707 * w, capSeamS = 0.75 * te * M.Fu / 3.05;   // AISI S100 §J2.5 (L/t ≥ 25)
    const area = Math.PI * (Rlo * Rlo - Rli * Rli) - (best ? best.pts.length : 0) * 0, mass = M.rho * area * t;
    return Object.assign({ t, te, D, e, Rlo, Rli, PN, trk, free, radii, srMax, sTh, sTh1, dAl, Kp, Fw, Aw, capW, capS, cap, da, OmS, PnS, Fpk, qT, qTh, w, capSeamW, capSeamS, bV, area, mass }, best || {});
  }
  function size(P, R, fz) {
    P = full(P);
    const C = ctxOf(P, R), M = matOf(P), Nd = P.Nd, Fw = P.FEXX * 0.60 / (1.20 * Nd), FvC = fyC(P) / (Nd * Math.sqrt(3));
    const pats = fz ? [fz.pat || (Math.round(P.bx_pat) === 1 ? 1 : 2)] : Math.round(P.bx_forma) === 1 ? [1] : Math.round(P.bx_pat) > 0 ? [Math.round(P.bx_pat)] : [2, 1], nws = fz ? [fz.nw] : P.bx_nw > 0 ? [Math.round(P.bx_nw)] : [0], kSp = isoK(P.bx_d_sp);
    const capWh = (d) => Fw * 0.707 * P.bx_w_h * Math.PI * (d - P.bx_w_h);   // filete interior del agujero de soldadura (largo en el centro de la garganta ≈ π(d − w), conservador)
    const tcMin = Math.ceil(0.5 + kSp + P.bx_u_min);
    const tcs = fz ? [fz.t_c] : P.bx_tc > 0 ? [P.bx_tc] : CS_COMM.filter((t) => t >= tcMin && wMaxJ(t) >= Math.max(P.bx_w_h, P.bx_w_c));
    const capSp = 0.45 * P.bx_Fu_sp / 2 * Math.PI / 4 * P.bx_d_sp ** 2, M0 = matOf(P), dT0 = P.bx_d_tss, tHead0 = isoK(dT0) + 0.5 + P.ss_allow;
    const SQ = Math.round(P.bx_forma) === 1, ds = fz ? [fz.d] : P.bx_dp > 0 ? [P.bx_dp] : (SQ ? LIST_A : LIST_D.filter((x) => x + 1 <= P.bx_dp_max + 1e-9));
    const ligOf = (tc) => fz ? fz.lig : P.bx_lig > 0 ? P.bx_lig : Math.max(10, tc);
    const plugOf = (tc) => Math.floor(Math.max(tc + 8 + 3, 2.25 * Math.min(tc, 16)));   // AISC J2.3a: Ø ≥ t + 8 y ≤ máx(Ø_mín + 3; 2,25·t_soldadura); se toma el máximo (más área)
    const tssGuess = fz ? fz.t_ss : lamOn(P) ? P.bx_t_lam : P.bx_t_ss > 0 ? P.bx_t_ss : 8;
    const kI = P.__th ? { p_uh: 1, E_uh: 1 } : TT_.thermalFactors(P, P.T_ifc_max).k;   // UHMW a T_ifc_max (interpolado entre 1,0 a T_ref y kT_* a 80 °C; confianza C); en el escenario térmico P ya viene reducido
    const dFl = P.d_flat + P.bx_tol_H;
    const cand = [], lays = new Map();
    for (const pat of pats) for (const nw of nws) for (const tc of tcs) for (const d of ds) {
      const lig = ligOf(tc), s = fz ? fz.s : d + lig, dPlug = d;
      const layK = (dr) => { const key = [d, s, lig, nw, SQ ? tc : 0, pat, (dr || []).join(",")].join("|"); if (!lays.has(key)) lays.set(key, layout(P, C, d, s, lig, nw, pat, dPlug, fz ? 4 : 8, tc, dr)); return lays.get(key); };
      const L0 = layK(fz ? (fz.drops || null) : null); if (!L0) continue;
      const crs = !fz && !(ds.length === 1 && tcs.length === 1);   // malla fina de la torsión si la geometría está fijada (Ø y espesor dados): la selección ve el FU definitivo
      const tq0 = nw >= 1 ? null : torsion(L0, C, d, tc, (i) => C.muEff * L0.pucks[i].p * L0.pucks[i].Ai, crs), vars = [[fz ? (fz.drops || null) : null, L0, tq0]];
      // Patrón radial: mientras el corte por torsión del portador pase de 0,80·F_v, se quita una pastilla del anillo crítico (más acero en su sección neta);
      // cada paso es un candidato más (rev. 5, 18-11-2026: A36 y portador fijo de 25 mm; las demás filas deciden cuál sirve)
      if (tq0 && pat === 2 && !fz && !SQ) { let dr0 = null, Lc = L0, tqc = tq0;
        for (let it = 0; it < 16 && tqc.tauMax / FvC > 0.80; it++) {
          const rr = [...new Set(Lc.all.map((q) => q.ring))].map((k) => ({ k, r: Lc.all.find((q) => q.ring === k).r })), kc = rr.reduce((m, o) => (!m || Math.abs(o.r - tqc.rCrit) < Math.abs(m.r - tqc.rCrit) ? o : m), null).k;
          const dr = (dr0 || []).slice(); for (let i = 0; i <= kc; i++) dr[i] = dr[i] || 0; dr[kc]++;
          const L2 = layK(dr); if (!L2) break; const tq2 = torsion(L2, C, d, tc, (i) => C.muEff * L2.pucks[i].p * L2.pucks[i].Ai, crs);
          dr0 = dr; Lc = L2; tqc = tq2; vars.push([dr, L2, tq2]);
        } }
      for (const [drops, L, tq] of vars) {
      const fl = nw >= 1 ? flow(L, s, () => C.muEff * L.pMax * L.Ap, C, d, lig) : { Flig: C.muEff * L.pMax * L.Ap, plugMax: 0, edgeMax: 0, unreached: 0, hMax: 1, nEdge: 0 };
      const fuT = tq ? [tq.tauMax / FvC / 0.9, tq.Tout / (2 * Math.PI * C.Rco ** 2) / (0.707 * P.bx_w_c) / Fw / 0.9, tq.Tin / (2 * Math.PI * C.Rci ** 2) / (0.707 * P.bx_w_c) / Fw / 0.9] : [];
      // espesor de la pastilla = plancha comercial (corte con router o chorro de agua): h_p = H − t_portador; el menor H que cumple
      const hps = fz ? [fz.h_p] : P.bx_hp > 0 ? [P.bx_hp] : (P.bx_H_uh > 0 ? [P.bx_H_uh] : UH_PL).map((H) => H - tc).filter((h) => h >= 2 - 1e-9 && h <= P.bx_hp_max + 1e-9);
      if (!hps.length) break;
      let pick = null;
      for (const hp of hps) {
        const e = puckEval(P, C, M, L, d, s, tc, lig, nw, hp, tssGuess, dPlug), cell = cellOf(P, C, M, L, d, tssGuess, s), e50 = puckEval(P, C, M, L, d, s, tc, lig, nw, hp, tssGuess, dPlug, kI.E_uh);
        const fus = [L.pMax / P.p_uhmw / 0.9, e.worst.pd / P.p_uhmw / 0.9, e.PVm / P.PV_uh / 0.9, e.FiU / (d * (tc - 1)) / P.p_uhmw / 0.9, fl.Flig / ((s - d) * tc) / FvC / 0.9, fl.plugMax / capWh(d) / 0.9,
          fl.edgeMax / (0.707 * P.bx_w_c * s * Fw) / 0.9, (P.bx_g_min + P.bx_bow + e50.wear + e50.creep + dFl + cell.w) / hp, C.muU * (hp + tc / 2) / L.SH.kern, cell.w / Math.min(P.d_flat, 0.1 * hp), fl.unreached ? 99 : 0,
          L.pMax / (kI.p_uh * P.p_uhmw) / 0.9, e50.worst.pd / (kI.p_uh * P.p_uhmw) / 0.9, e.PVm / (kI.p_uh * P.PV_uh) / 0.9, e.FiU / (d * (tc - 1)) / (kI.p_uh * P.p_uhmw) / 0.9];
        if (fl.unreached) fus.push(99);
        fuT.forEach((f) => fus.push(f));
        fus.push(e.FiU / capSp / 0.9);
        const f50 = fus.slice(11, 15), f20 = fus.slice(0, 11).concat(fus.slice(15)), fuMax = Math.max(...fus), fu20 = Math.max(...f20), fu50 = Math.max(...f50);
        const ok20 = fu20 <= 1 + 1e-9, better = (q) => { if (!q) return true; const q20 = q.fu20 <= 1 + 1e-9; if (ok20 !== q20) return ok20; return ok20 ? fu50 < q.fu50 - 1e-9 : fu20 < q.fu20 - 1e-9; };
        if (better(pick)) pick = { hp, fuMax, fu20, fu50, e, fus };
        if (fuMax <= 1 + 1e-9) break;
      }
      const H = tc + pick.hp, nP = L.pucks.length, nW = L.welds.length;
      const mPuck = P.bx_rho_uh * 1e-6 * L.Asum * H, mCar = RHO * tc * (Math.PI * (C.Rco ** 2 - C.Rci ** 2) - L.Asum * L.SH.ApH / L.SH.Ap);
      const tss0 = discT(P, C, M0, L, d, s, tHead0, null).t;
      const mSS0 = M0.rho * Math.PI * (C.Ro ** 2 - C.Ri ** 2) * tss0;      // el disco entra al costo: el hueco mayor de la malla fija su espesor
      cand.push({ drops, pat, dTot: tc + pick.hp + tss0, fu20: pick.fu20, fu50: pick.fu50, mSS0, fus: pick.fus, nw, tc, d, s, lig, dPlug, L, fl, hp: pick.hp, fuMax: pick.fuMax, H, mPuck, mCar, cost: mPuck + mCar + mSS0, ok: pick.fuMax <= 1 + 1e-9 });
      }
    }
    const okC = cand.filter((c) => c.ok), best = okC.length ? okC.reduce((b, c) => (!b || (SQ ? (c.dTot < b.dTot - 1e-9 || (Math.abs(c.dTot - b.dTot) <= 1e-9 && c.cost < b.cost)) : (c.cost < b.cost - 1e-6 || (Math.abs(c.cost - b.cost) <= 1e-6 && c.tc + c.hp < b.tc + b.hp))) ? c : b), null)   // cuadradas: menor espesor total δ (mandante); redondas: menor masa
      : (() => {   // sin candidato que cumpla todo: primero los que cumplen a 20 °C (FU ≤ 0,90; si no hay, ≤ 1,00) y entre ellos el de menor FU a T_ifc,máx; si no, el de menor FU a 20 °C
        const lim = cand.some((c) => c.fu20 <= 1 + 1e-9) ? 1 : cand.some((c) => c.fu20 <= 1 / 0.9 + 1e-9) ? 1 / 0.9 : Infinity, pool = cand.filter((c) => c.fu20 <= lim + 1e-9);
        const by50 = isFinite(lim) && pool.length;
        return (by50 ? pool : cand).reduce((b, c) => (!b || (by50 ? c.fuMax < b.fuMax - 1e-9 : c.fu20 < b.fu20 - 1e-9) ? c : b), null); })();   // rev. 5: en el grupo, el menor FU de todas las filas
    // malla definitiva con muestreo fino y h_p recalculado con ella
    if (!best) throw new Error("TT300-BX: ninguna combinación de portador y pastillas es geométricamente posible (¿espesor del portador ≥ espesor de la plancha de UHMW? el saliente debe ser > 0)");
    let { tc, d, s, lig, dPlug, hp, nw, pat, drops } = best;
    const L = fz ? best.L : layout(P, C, d, s, lig, nw, pat, dPlug, 4, tc, drops);
    const fl = nw >= 1 ? flow(L, s, (i) => C.muEff * L.pucks[i].p * L.Ap, C, d, lig) : { Flig: C.muEff * L.pMax * L.Ap, plugMax: 0, edgeMax: 0, unreached: 0, hMax: 1, nEdge: 0, plugF: [] };
    const tq = nw >= 1 ? null : torsion(L, C, d, tc, (i) => C.muEff * L.pucks[i].p * L.pucks[i].Ai);
    // disco: espesor y tornillos
    const dT = P.bx_d_tss, kT = isoK(dT), tHead = kT + 0.5 + P.ss_allow, sad = 0.6 * M.Fy;
    const DT = discT(P, C, M, L, d, s, tHead, fz ? fz.t_ss : !lamOn(P) && P.bx_t_ss > 0 ? P.bx_t_ss : null), aV = DT.aV, tVoid = DT.tVoid, aG = DT.aG, tReq = DT.tReq;
    let tss = DT.t;
    if (!fz && !(P.bx_hp > 0)) {   // h_p definitivo con la malla fina y el espesor del disco
      const hl = (P.bx_H_uh > 0 ? [P.bx_H_uh] : UH_PL).map((H) => H - tc).filter((h) => h >= 2 - 1e-9 && h <= P.bx_hp_max + 1e-9);
      for (const h of hl) { const e = puckEval(P, C, M, L, d, s, tc, lig, nw, h, tss, dPlug), e5 = puckEval(P, C, M, L, d, s, tc, lig, nw, h, tss, dPlug, kI.E_uh), ce = cellOf(P, C, M, L, d, tss, s);
        if (e.worst.pd <= 0.9 * P.p_uhmw && e5.worst.pd <= 0.9 * kI.p_uh * P.p_uhmw && (P.bx_g_min + P.bx_bow + e5.wear + e5.creep + dFl + ce.w) <= h && C.muU * (h + tc / 2) <= L.SH.kern && ce.w <= Math.min(P.d_flat, 0.1 * h)) { hp = h; break; } hp = h; }
    }
    const dTd = Math.max(P.T_ifc_max - P.T_ref, P.T_ref - P.T_ifc_min);   // ΔT de servicio disco–mesa (revisión del mandante: montaje a 20 °C, servicio 0–50 °C: 30 K)
    let sb = fz ? fz.sb : P.bx_s_tss > 0 ? P.bx_s_tss : null, BL, BF, PL = null;
    const LAM = lamOn(P);
    if (LAM) {   // modo 1: lámina soldada (tapones + costura perimetral); sin tornillos
      PL = lamDesign(P, C, M, L, d, tss, dTd, fz ? fz.sp : null); sb = 0;
      BL = { lista: [], radii: [], sMin: Infinity, eIn: 0, eOut: 0, dk: 0 }; BF = null;
    } else {
    const tryS = (x) => { const bl = boltLayout(P, C, dT, x, tss), bf = boltForces(P, C, R, M, dT, x, tss, bl, dTd); return { bl, bf, ok: bf.V_prim <= 0.9 * bf.capV && bf.V_prim <= 0.9 * bf.RnSS_edge / 2 && bl.sMin >= 3 * dT }; };   // el corte de diseño es el del par (primario); la componente térmica es secundaria (fila informativa)
    if (sb == null) { let last = null; for (const x of LIST_SB) { const r = tryS(x); last = r; sb = x; if (r.ok) break; } BL = last.bl; BF = last.bf; }
    else { const r = tryS(sb); BL = r.bl; BF = r.bf; }
    }
    // ajuste a presión
    const dal = P.bx_al_uh * 1e-6 - P.bx_al_st * 1e-6, tolS = P.bx_tol_h + P.bx_tol_p, dCold = dal * (P.T_ref - P.bx_Tmin) * d, dHot = dal * (P.T_ifc_max - P.T_ref) * d;   // caliente: temperatura máxima de la interfaz (50 °C)
    const iLo = Math.max(tolS, tolS + dCold - 2 * (P.bx_c_sp - 0.2)), iHi = P.bx_eps_max / 100 * d - tolS - dHot;
    const delta = fz ? fz.i : P.bx_i > 0 ? P.bx_i : Math.ceil(iLo / 0.05 - 1e-9) * 0.05;
    const H = tc + hp, nP = L.pucks.length, nW = L.welds.length, Ap = L.Ap;
    const holeSp = P.bx_d_sp + 2 * P.bx_c_sp, dkSp = isoDk(P.bx_d_sp);
    const SHf = L.SH, Acut = SHf.sq ? (d + delta) ** 2 - (4 - Math.PI) * SHf.rcp ** 2 : Math.PI / 4 * (d + delta) ** 2;
    const mPuck1 = P.bx_rho_uh * 1e-6 * (Acut * H - Math.PI / 4 * holeSp ** 2 * H - Math.PI / 4 * (dkSp ** 2 - holeSp ** 2) * (hp + 0.5));   // descontado el agujero y el alojamiento de la cabeza (cilindro, conservador)
    const fSum = L.Asum / L.Ap, mCarPl = RHO * tc * (Math.PI * (C.Rco ** 2 - C.Rci ** 2) - fSum * SHf.ApH), mFil = RHO * P.bx_w_c ** 2 / 2 * 2 * Math.PI * (C.Rco + C.Rci);
    const A_ss = LAM ? PL.area : Math.PI * (C.Ro ** 2 - C.Ri ** 2), mSS = M.rho * A_ss * tss;
    const bx = { t_ss: tss, t_ss_req: tReq, t_flex: tVoid, delta: tc + hp + tss, mTop: mSS, mSS, mUH: fSum * mPuck1, mCar: mCarPl + mFil, t_c: tc, h_p: hp };
    const geo = { DT, kI, dFl, tq, drops: drops || null, candList: cand.map((c) => ({ d: c.d, tc: c.tc, s: c.s, hp: c.hp, nw: c.nw, fuMax: c.fuMax, fus: c.fus, cost: c.cost })), capWh: capWh(d), C, M, pat, nw, tc, d, s, lig, dPlug, hp, H, delta, iLo, iHi, dCold, dHot, tolS, dal, L, fl, tss, tReq, tHead, tVoid, aV, sad, dT, kT, sb, BL, BF, PL, LAM, dTd, nP, nW, Ap, holeSp, dkSp, mPuck1, mCarPl, mFil, mSS, A_ss, tcMin, cand: cand.length, candOk: okC.length };
    return { bx, geo, frozen: { t_c: tc, d, s, lig, h_p: hp, t_ss: tss, sb, sp: PL ? PL.sc : null, i: delta, nw, pat, drops: drops || null } };
  }
  const sameBx = (a, b) => ["t_ss", "t_c", "h_p"].every((k) => a[k] === b[k]) && Math.abs(a.mTop - b.mTop) < 1e-9 && Math.abs(a.mCar - b.mCar) < 1e-9 && Math.abs(a.mUH - b.mUH) < 1e-9;
  const designCache = new Map();
  // Diseño completo: el núcleo da la carga (q, N, par) con la geometría BX y el dimensionamiento se repite hasta que la geometría no cambia (≤ 4 pasadas;
  // la masa de la interfaz cambia N en < 0,1 %). fz: geometría congelada (escenario térmico).
  function design(P, fz) {
    if (!active(P)) return null;
    P = full(P);
    const key = JSON.stringify(P, (k, v) => (k === "__th" ? (v ? { T: v.T, k: v.k, dT: v.dT } : v) : (typeof v === "number" && !isFinite(v) ? String(v) : v))) + "|" + JSON.stringify(fz || null);
    if (designCache.has(key)) return designCache.get(key);
    const Pb = Object.assign({}, P); delete Pb.__bx;
    // 1) búsqueda con la carga de una geometría provisional (la masa de la interfaz cambia N en < 0,1 %); 2) geometría congelada y carga recalculada
    //    con ella hasta que las masas no cambian (≤ 3 pasadas)
    let bx = { t_ss: 8, t_ss_req: 8, t_flex: 0, delta: 12 + 6 + 8, mTop: 200, mSS: 200, mUH: 40, mCar: 150, t_c: 12, h_p: 6 }, S = null, R = null, frz = fz ? fz.frozen : null;
    if (fz) bx = fz.bx;
    if (!frz) { R = TT_.compute(Object.assign({}, Pb, { __bx: bx })); S = size(Pb, R, null); frz = S.frozen; bx = S.bx; }
    for (let it = 0; it < 3; it++) {
      R = TT_.compute(Object.assign({}, Pb, { __bx: bx }));
      S = size(Pb, R, frz);
      if (sameBx(S.bx, bx)) break;
      bx = S.bx;
    }
    if (!sameBx(S.bx, bx)) { bx = S.bx; R = TT_.compute(Object.assign({}, Pb, { __bx: bx })); }
    const out = build(Pb, R, S);
    if (designCache.size > 60) designCache.clear();
    designCache.set(key, out);
    return out;
  }
  function coreP(P) { if (!active(P)) return P; const G0 = design(P); return Object.assign({}, full(P), { __bx: G0.bx }); }

  // Bloque «disco» del modo 1 (lámina soldada): paneles, junta a tope, tapones, costura, celda, hueco, despegue y fabricación
  function discoLam(P, C, M, g, ce) {
    const PL = g.PL, PN = PL.PN, nT = PL.pts.length, nPi = PL.pts.filter((q) => q.pista).length;
    return { modo: 1, t: g.tss, t_req: g.tss, t_e: PL.te, R_ext: PL.Rlo, R_int: PL.Rli, R_mesa: C.Ro, R_i_interfaz: C.Ri, material: M.nombre + ", acabado espejo (plancha del proveedor)", Fy: M.Fy, Fu: M.Fu, alfa: M.al, E: M.E,
      aporte: "E309L-16 (AWS A5.4) / ER309L (AWS A5.9): unión disímil inox–acero al carbono", fuente_material: M.fuente, masa: g.mSS, semidiscos: 0,
      lamina: { espesor: g.tss, formato: [P.bx_fmt_a, P.bx_fmt_b], margen_corte: PN.m, R_ext: PL.Rlo, R_int: PL.Rli, retiro_borde: P.bx_c_lam, n_paneles: PN.n,
        paneles: PN.paneles.map((q) => Object.assign({}, q, { masa: M.rho * q.area_bruta * g.tss })),
        junta: { tipo: "a tope (borde recto cortado a láser o cizalla, separación de raíz 0–1 mm) con soldadura de ranura de penetración completa sobre respaldo permanente (la plancha inferior de la mesa), esmerilada a ras y pulida; NO traslapada (el traslapo deja un escalón de " + nf(g.tss, 0) + " mm y un canto libre en la cara de deslizamiento)",
          aporte: "ER309L (AWS A5.9) / E309L-16 (AWS A5.4)", lineas_y: PN.juntas, largo: PN.largo_juntas, norma: "AWS D1.6/D1.6M:2017 (inoxidable y unión disímil; WPS calificada); AISC 360-22 Tabla J2.5 (CJP)",
          END: "VT 100 % y PT 100 % después de esmerilar", acabado: "esmerilado a ras (± 0,05 mm) y pulido al grano del espejo (Ra ≤ 0,4 µm) en la franja de la junta" },
        acabado: "espejo del proveedor (film protector hasta el montaje; se retira solo en los tapones, la junta y la costura)" },
      tapones: { tipo: "tapón (plug) en agujero Ø" + nf(PL.D, 1) + " taladrado o punzonado en la lámina, relleno en todo el espesor (" + nf(g.tss, 0) + " mm) y fundido a la plancha de la mesa; esmerilado a ras y pulido", d: PL.D, relleno: g.tss, n: nT, paso: PL.sc,
        anillos: PL.rings, en_pistas: nPi, s_min: PL.sMin, e_min: PL.eAv, e_req: PL.eReq, V_max: PL.Vmax, cap_soldadura: PL.capW, cap_lamina: PL.capS, cap: PL.cap, F_pastilla_max: PL.loc.F, n_local_min: PL.loc.n, V_local: PL.loc.V,
        lista: PL.pts.map((q) => ({ x: q.x, y: q.y, r: q.r, anillo: q.ring, pista: q.pista, V: q.V })),
        norma: "AISC 360-22 §J2.3 (Ø, separación ≥ 4·Ø, relleno = t), §J2.4 (corte en el área del agujero); AISI S100-16 §J2.2 / ASCE 8-02 §5.2.2 (lámina alrededor del tapón; distancia al borde); AWS D1.6/D1.6M:2017 (WPS disímil); AWS D1.3/D1.3M:2018 (detalle de tapones en lámina ≤ 4,8 mm, referencia)" },
      costura: { w: PL.w, exterior: { R: PL.Rlo, largo: 2 * Math.PI * PL.Rlo }, interior: { R: PL.Rli, largo: 2 * Math.PI * PL.Rli }, q_par: PL.qT, q_termica: PL.qTh, cap_soldadura: PL.capSeamW, cap_lamina: PL.capSeamS, tipo: "filete continuo z" + nf(PL.w, 1) + " en el canto de la lámina a la plancha de la mesa (sella el intersticio lámina–plancha)" },
      tornillos: { n: 0, d: null, lista: [], anillos: [], nota: "modo 1: sin tornillos avellanados (lámina soldada)" },
      celda: { a: ce.a, b: ce.b, sigma: ce.sig, sigma_lamina: ce.sigSs, sigma_plancha: ce.sigPl, flecha: ce.w, M_a: ce.c.Ma, M_b: ce.c.Mb, D: ce.D, compuesta: true },
      vacio: { a: PL.bV.a, g0: P.bx_g0, sigma: PL.bV.sig, p_cierre: PL.bV.pc }, despegue_panel: { a: PL.bP.a, g0: P.bx_g0, sigma: PL.bP.sig, p_cierre: PL.bP.pc, p_min_pastilla: PL.pMin },
      hueco: { a: g.DT.aG, fraccion_disco: g.DT.gap.sh, sigma: g.DT.gap.sig, sigma_plancha: g.DT.gap.sigPl },
      termico: { dT: g.dTd, alfa_acero: P.bx_al_st * 1e-6, sigma_uniaxial: PL.sTh1, sigma_biaxial: PL.sTh, panel: PL.ap, sigma_cr: PL.sCr, tau_arrastre: PL.tau, tau_cr: PL.tCr, interaccion: PL.inter, s_r_max: PL.srMax,
        criterio: "secundaria: rango ≤ 2Fy (ASME VIII-2 5.5.6.1) y ≤ Fy; pandeo del panel entre apoyos (k = 2) con el arrastre (k_s = 9,34): σ/σ_cr + (τ/τ_cr)² ≤ 1" },
      fabricacion: lamFab(P, PL) };
  }
  function lamFab(P, PL) {
    return "1) planear la cara inferior de la mesa (planitud d_flat) y desengrasar; 2) cortar los " + PL.PN.n + " paneles del formato " + P.bx_fmt_a + " × " + P.bx_fmt_b + " con film protector y taladrar los " + PL.pts.length + " agujeros Ø" + nf(PL.D, 1) + " con plantilla; "
      + "3) presentar los paneles con la mesa invertida, apretados contra la plancha con prensas o peso distribuido (o vacío) en todo el panel; 4) tapones por zonas desde el centro hacia afuera, alternando cuadrantes y saltando posiciones (1 de cada 3 por pasada), "
      + "temperatura entre pasadas ≤ 150 °C, sin precalentar el inox; 5) junta a tope sobre la plancha en tramos alternados; 6) costura perimetral exterior e interior por retroceso (backstep) en tramos ≤ 150 mm; 7) esmerilar a ras y pulir tapones, junta y costura; "
      + "8) control: separación lámina–plancha ≤ " + nf(P.bx_g0, 2) + " mm con galga en todo el contorno de los paneles y entre tapones (golpeteo y galga), planitud de la cara con regla, PT de tapones y juntas; 9) decapado y pasivado local (ASTM A380 / A967)";
  }
  /* ---------------- Geometría exportable (fuente única para el generador de planos) ---------------- */
  function build(P, R, S) {
    const g = S.geo, C = g.C, M = g.M, L = g.L, BF = g.BF, BL = g.BL;
    const e = puckEval(P, C, M, L, g.d, g.s, g.tc, g.lig, g.nw, g.hp, g.tss, g.dPlug), ce = cellOf(P, C, M, L, g.d, g.tss, g.s);
    const Fmax = C.muEff * L.pMax * g.Ap;
    const LspList = ISO10642_L, kSp = isoK(P.bx_d_sp), zHead = g.tc - 0.5, pSp = pitchOf(P.bx_d_sp), hd = P.t_base - 3, hu = hd - 2 * pSp;
    const Lsp = LspList.filter((x) => x - zHead >= P.bx_d_sp - 1e-9 && x - zHead + 2 <= hu + 1e-9).pop() || LspList.find((x) => x - zHead >= P.bx_d_sp) || 20;
    const dT = g.dT, pT = pitchOf(dT), rec = 0.5 + P.ss_allow;
    const Lof = (b) => { const tb = b.anillo ? P.t_pr : P.t_bot; if (b.anillo) { const hdT = tb - 3, huT = hdT - 2 * pT; const Ls = ISO10642_L.filter((x) => x - (g.tss - rec) >= 1.25 * dT - 1e-9 && x - (g.tss - rec) + 2 <= huT + 1e-9); return { L: Ls.length ? Ls[Ls.length - 1] : null, ciego: true, prof: hdT, util: huT, tb }; }
      const L0 = ISO10642_L.find((x) => x - (g.tss - rec) >= tb - 1e-9) || null; return { L: L0, ciego: false, prof: tb, util: tb, tb }; };
    const bolts = BL.lista.map((b) => { const l = Lof(b); return { x: b.x, y: b.y, r: b.r, ang: b.a, anillo: b.anillo, L: l.L, ciego: l.ciego, prof: l.prof, rosca_util: l.util, t_pieza: l.tb, le: l.L != null ? Math.min(l.L - (g.tss - rec), l.tb) : NaN, VT: b.VT, Vth: b.Vth, V: b.V }; });
    const fz = { t_c: g.tc, d: g.d, s: g.s, lig: g.lig, h_p: g.hp, t_ss: g.tss, sb: g.sb, sp: g.PL ? g.PL.sc : null, i: g.delta, nw: g.nw, pat: g.pat, drops: g.drops || null };
    const iPV = e.iPV;
    return {
      version: 1, material: M.nombre, frozen: fz, bx: S.bx,
      disco: g.LAM ? discoLam(P, C, M, g, ce) : { modo: 0, t: g.tss, t_req: g.tReq, t_cabeza: g.tHead, t_vacio: g.tVoid + P.ss_allow, R_ext: C.Ro, R_int: C.Ri, material: M.nombre, Fy: M.Fy, Fu: M.Fu, alfa: M.al, E: M.E, aporte: M.aporte, fuente_material: M.fuente,
        masa: g.mSS, masa_semidisco: g.mSS / 2, semidiscos: 2, linea_cjp: "eje x (y = 0), sobre el nervio de 0°/180°",
        cjp: { tipo: "CJP a tope en V doble (o V simple con respaldo cerámico retirado) en todo el espesor, esmerilada a ras en ambas caras", norma: "AWS D1.6/D1.6M:2017 (acero inoxidable); WPS calificada", aporte: M.aporte, largo: 2 * (C.Ro - C.Ri), END: "VT 100 % y PT 100 % de la cara de deslizamiento después de esmerilar; RT o UT según AWS D1.6 (propuesta, a confirmar por el inspector)", acabado: "cara de deslizamiento: esmerilado a ras y pulido Ra ≤ 0,8 µm en la franja de la CJP" },
        acabado: "cara de deslizamiento en estado de laminación 2B (EN 10088-2) si existe en el espesor; si no, 1D con pulido a Ra ≤ 0,8 µm (sin rectificado); planitud: el disco copia la cara inferior planeada de la mesa al apretar los tornillos",
        tornillos: { designacion_base: "ISO 10642 M" + dT + " clase 10.9 (zinc laminar ISO 10683)", d: dT, n: bolts.length, paso_malla: g.sb, anillos: BL.radii, s_min: BL.sMin, d_cabeza: isoDk(dT), k: g.kT, cabeza_bajo_cara: rec, avellanado: "90°, Ø" + isoDk(dT) + ", taladrado y avellanado (no plasma)", agujero_disco: dT + 1,
          e_min_ext: BL.eOut, e_min_int: BL.eIn, lista: bolts, V_comb: BF.V_comb, V_primario: BF.V_prim, Vth_anillos: BF.th_out.porAnillo, capV: BF.capV, VT_max: BF.VT_max, Fth_ext: BF.Fth_out, Fth_int: BF.Fth_in, k_b: BF.th_out.kb, dT_diseno: BF.dTd,
          nota: "taladros roscados en la mesa por plantilla (el disco ya cortado sirve de plantilla: taladrado coincidente); rosca pasante en la plancha inferior (la punta entra ≤ 5 mm en el cajón cerrado) o ciega en el anillo inferior de pasadores (remanente 3 mm: la punta no asoma a la luz entre anillos)" },
        celda: { a: ce.a, b: ce.b, sigma: ce.sig, flecha: ce.w, M_a: ce.c.Ma, M_b: ce.c.Mb }, vacio: { a: g.aV, sigma: 0.75 * C.qmax * (g.aV / (g.tss - P.ss_allow)) ** 2 },
        hueco: { a: g.DT.aG, fraccion_disco: g.DT.gap.sh, sigma: g.DT.gap.sig },
        termico: { dT: g.BF.dTd, alfa_acero: P.bx_al_st * 1e-6, sigma_uniaxial: M.E * Math.abs(M.al - P.bx_al_st * 1e-6) * g.BF.dTd, sigma_biaxial: M.E * Math.abs(M.al - P.bx_al_st * 1e-6) * g.BF.dTd / (1 - M.nu), criterio: "secundaria: rango ≤ 2Fy (ASME VIII-2 5.5.6.1) y ≤ Fy; pandeo del panel s×s (k = 2)" } },
      portador: { t: g.tc, R_int: C.Rci, R_ext: C.Rco, material: astm(fyC(P), fuC(P)) + " (rev. 6, decisión del mandante 18-11-2026: calidad por pieza; parámetros Fy_bxc/Fu_bxc)", corte: "plasma de alta definición (contorno y agujeros de pastillas y tapones), tolerancia del Ø ± " + nf(P.bx_tol_h, 2) + " mm",
        paso: g.s, ligamento: g.lig, patron: { tipo: g.pat === 2 ? "radial" : "triangular", paso: g.s, nw: g.nw, saltos_max: g.fl.hMax, sin_camino: g.fl.unreached, pastillas_al_borde: g.fl.nEdge, pastillas_quitadas_por_anillo: g.drops || [], nota: g.pat === 2 ? "anillos concéntricos repartidos entre el borde exterior y el interior a paso ≥ s; n por anillo = ⌊2πr/s⌋ menos las quitadas (alivio de la torsión del portador A36 en el anillo crítico: " + JSON.stringify(g.drops || []) + ")" + (g.nw >= 1 ? "; cada " + g.nw + ".ª posición del anillo es un agujero de soldadura" : "") : "red triangular anclada al centro (fila alterna desplazada s/2); agujeros de soldadura en la subred de índice " + g.nw + " (coordenadas axiales q, r: " + (g.nw === 13 ? "(q + 4r) mod 13 = 0" : g.nw === 7 ? "(q + 3r) mod 7 = 0" : "ver weldSite") + "); las pastillas del borde entregan al filete perimetral" },
        agujeros: { d: L.SH.sq ? null : g.d, forma: L.SH.sq ? "cuadrada" : "redonda", lado: L.SH.sq ? g.d : null, r_esquina: L.SH.sq ? L.SH.rc : null, area: L.SH.ApH, n: g.nP, posiciones: L.pucks.map((q) => [q.hx, q.hy]), recortadas: L.pucks.map((q, i) => (q.trim ? { i, centro: [q.hx, q.hy], fraccion: q.f, contorno: "cuadrado ∩ corona R" + nf(C.Rci + g.lig, 0) + "…R" + nf(C.Rco - g.lig, 0) } : null)).filter(Boolean),
          orientacion: L.SH.sq ? "lados paralelos a x e y (malla cartesiana de paso " + g.s + "; desplazamiento " + JSON.stringify(L.pucks[0] && L.pucks[0].off || [0, 0]) + "·s)" : null },
        tapones: { tipo: "agujero de soldadura del mismo Ø que el de las pastillas, sin pastilla, con filete interior en todo el contorno a la base", d: g.dPlug, w: P.bx_w_h, n: g.nW, posiciones: L.welds.map((q) => [q.x, q.y]), demanda_max: g.fl.plugMax, capacidad: g.capWh,
          norma: "AISC 360-22 §J2.2 (filete en agujeros; largo efectivo en el centro de la garganta ≈ π(Ø − w)), §J2.4; AWS D1.1/D1.1M:2020 Tabla 7.7; ASME BTH-1-2020 §3-3.4", acabado: "el filete queda bajo la cara superior del portador (w ≤ t − 2): no toca el disco" },
        filetes: { w: P.bx_w_c, exterior: { R: C.Rco, largo: 2 * Math.PI * C.Rco }, interior: { R: C.Rci, largo: 2 * Math.PI * C.Rci } },
        F_lig_max: g.fl.Flig, masa: S.bx.mCar, masa_plancha: g.mCarPl, masa_filetes: g.mFil,
        secuencia: "1) planear la cara de la base bajo el portador (planitud d_flat); 2) presentar el portador centrado con el agujero del pivote; 3) filetes de los agujeros de soldadura en secuencia simétrica desde el centro, alternando cuadrantes; 4) filetes perimetrales en tramos alternados; 5) control de planitud de los fondos de los agujeros (la base) y taladrado y roscado de los alojamientos de los tornillos de las pastillas por los agujeros del portador" },
      pastillas: { forma: L.SH.sq ? "cuadrada" : "redonda", lado: L.SH.sq ? g.d : null, lado_corte: L.SH.sq ? g.d + g.delta : null, r_esquina: L.SH.sq ? L.SH.rcp : null, r_esquina_agujero: L.SH.sq ? L.SH.rc : null, area: L.Ap,
        d: L.SH.sq ? null : g.d, d_torneado: L.SH.sq ? null : g.d + g.delta, interferencia: g.delta, H: g.H, h_p: g.hp, n: g.nP, densidad: P.bx_rho_uh, cuadrado_proveedor: P.bx_cuad_uh, d_corte_max: P.bx_dp_max, material: "UHMW-PE ULTRA VST (Plastigen) de 30 mm, virgen (ISO 15527 / ASTM D4020); p_adm, E, μ, PV y α: supuestos del proyecto, pendiente dato del proveedor", chaflan_inferior: "1 × 45°", chaflan_superior: "1 × 45°",
        agujero_tornillo: g.holeSp, cabeza: { d_k: g.dkSp, k: kSp, cara_superior_cabeza_bajo_cara: g.hp + 0.5 }, tolerancias: { d: "± " + nf(P.bx_tol_p, 2), H: "± 0,05 (torneado)" },
        proceso: "router CNC o chorro de agua desde plancha calibrada de UHMW de " + g.H + " mm (sin torneado)", H_plancha: g.H,
        temperatura: { T_ifc_max: P.T_ifc_max, k_p: g.kI.p_uh, k_E: g.kI.E_uh, nota: "k interpolado linealmente entre 1,0 a T_ref y kT_* a 80 °C (supuesto sin curva del proveedor, confianza C); 80 °C: limitación de uso informativa" },
        masa_unit: g.mPuck1, masa_total: S.bx.mUH, cobertura: L.cov, p_max: L.pMax, PV_max: e.PVm, i_PV: iPV, F_max: Fmax, suma_N_kN: L.Nsum / 1e3, i_max: L.iMax,
        lista: L.pucks.map((q) => ({ x: q.x, y: q.y, r: q.r, A: q.A, p: q.p, area: q.Ai, fraccion: q.f, recortada: q.trim, centro_agujero: [q.hx, q.hy] })), sobrepresion: { dp: e.worst.dp, p_total: e.worst.pd, i: e.worst.i, k_placa: e.worst.kpl, t_mesa: e.worst.tm, flexibilidad: e.cp, S: e.S, E_c: e.Ec, M: e.Mc },
        fluencia: e.creep, desgaste: e.wear,
        ajuste: { delta: g.delta, delta_min_20: g.delta - g.tolS, d_dil_frio: g.dCold, d_dil_caliente: g.dHot, holgura_frio: Math.max(0, -(g.delta - g.tolS - g.dCold)) / 2, eps_caliente: (g.delta + g.tolS + g.dHot) / g.d, rango: [g.iLo, g.iHi],
          p_ajuste_20: P.bx_E_ct * (g.delta + g.tolS) / g.d / (1 - NU_UH), montaje: "a prensa con guía (o enfriando la pastilla); la interferencia relaja por fluencia: la retención la da el tornillo" },
        tornillo: { designacion: "ISO 10642 M" + P.bx_d_sp + " × " + Lsp + " clase 8.8 (zinc laminar ISO 10683)", d: P.bx_d_sp, L: Lsp, z_cara_cabeza: zHead, engrane: Lsp - zHead, taladro_ciego: hd, rosca_util: hu, remanente: P.t_base - hd, n: g.nP, apriete: "par bajo (retención, no precarga: el UHMW fluye); fijador de rosca de resistencia media" } },
      soldaduras: [
        g.LAM ? { id: "BX-W1", union: "panel–panel de la lámina inoxidable (sobre la plancha inferior de la mesa)", tipo: "ranura a tope de penetración completa sobre respaldo permanente (plancha de la mesa), ER309L/E309L, esmerilada a ras", norma: "AWS D1.6/D1.6M:2017 (unión disímil, WPS calificada)", largo: g.PL.PN.largo_juntas }
          : { id: "BX-W1", union: "semidisco–semidisco (inoxidable)", tipo: "CJP a tope, esmerilada a ras", norma: "AWS D1.6/D1.6M:2017", largo: 2 * (C.Ro - C.Ri) },
        { id: "BX-W2", union: "portador–base (agujeros de soldadura)", tipo: "filete z" + P.bx_w_h + " interior en todo el contorno del agujero Ø" + g.dPlug, norma: "AISC 360-22 §J2.2, §J2.4; AWS D1.1/D1.1M:2020 Tabla 7.7", n: g.nW, largo_cada: Math.PI * g.dPlug },
        { id: "BX-W3", union: "portador–base (borde exterior)", tipo: "filete z" + P.bx_w_c + " continuo", norma: "AWS D1.1/D1.1M:2020 Tabla 7.7; AISC 360-22 §J2.2b", largo: 2 * Math.PI * C.Rco },
        { id: "BX-W4", union: "portador–base (borde interior)", tipo: "filete z" + P.bx_w_c + " continuo", norma: "AWS D1.1/D1.1M:2020 Tabla 7.7; AISC 360-22 §J2.2b", largo: 2 * Math.PI * C.Rci },
      ].concat(g.LAM ? [
        { id: "BX-W5", union: "lámina inoxidable–plancha inferior de la mesa (tapones)", tipo: "tapón Ø" + nf(g.PL.D, 1) + " relleno " + nf(g.tss, 0) + " mm, ER309L/E309L, esmerilado a ras", norma: "AISC 360-22 §J2.3, §J2.4; AISI S100-16 §J2.2; AWS D1.6/D1.6M:2017", n: g.PL.pts.length },
        { id: "BX-W6", union: "lámina inoxidable–plancha inferior de la mesa (costura exterior)", tipo: "filete z" + nf(g.PL.w, 1) + " continuo, ER309L/E309L", norma: "AISC 360-22 §J2.2b, §J2.4; AISI S100-16 §J2.5; AWS D1.6/D1.6M:2017", largo: 2 * Math.PI * g.PL.Rlo },
        { id: "BX-W7", union: "lámina inoxidable–plancha inferior de la mesa (costura interior)", tipo: "filete z" + nf(g.PL.w, 1) + " continuo, ER309L/E309L", norma: "AISC 360-22 §J2.2b, §J2.4; AISI S100-16 §J2.5; AWS D1.6/D1.6M:2017", largo: 2 * Math.PI * g.PL.Rli }] : []),
      fabricacion: fabricacion(P, R, g),
      diseno: { candidatos: g.cand, candidatos_ok: g.candOk, mu_eff: C.muEff, mu_max: C.muMax, T_calado: C.Tcal, q_med: C.qa, q_max: C.qmax, kq: C.kq, omega: C.omega, dist_vida_m_por_mm: C.dist,
        nota: "búsqueda sobre Ø de pastilla, espesor del portador (paso = Ø + ligamento) y saliente; se elige la menor masa portador + pastillas con todas las verificaciones con FU ≤ 0,90 (geométricas ≤ 1)" },
      _geo: g, _e: e, _ce: ce,
    };
  }

  /* ---------------- Tabla de fabricación: antes → después ---------------- */
  function fabricacion(P, R, g) {
    const pv = TT_.driveMode(P) === 2, hr = R.hubG;
    const rows = [
      g.LAM ? ["Discos inoxidables de la interfaz (opción B: disco de la base y de la mesa, 24 sectores cada uno)", "Corte por plasma/láser de 48 sectores con muescas y chaflanes; rectificado/lapeado de la cara deslizante (Ra 0,4) en rectificadora plana (subcontrato); avellanados en taladro radial",
        "Lámina 304 espejo de " + g.tss + " mm (plancha del proveedor) en " + g.PL.PN.n + " paneles del formato " + P.bx_fmt_a + " × " + P.bx_fmt_b + " con junta a tope sobre la plancha, soldada a la plancha inferior de la mesa con " + g.PL.pts.length + " tapones Ø" + nf(g.PL.D, 1) + " (ER309L) y costura perimetral z" + nf(g.PL.w, 1) + "; sin tornillos ni rectificado",
        "simplificada", "Elimina 47 piezas, el rectificado, las muescas y los tornillos; el proveedor solo tiene plancha espejo de 3 mm (decisión del mandante 18-11-2026)", "Lámina: tapones, costura, pandeo, despegue, celda y hueco con la plancha de la mesa (filas «BX · Lámina …» y «BX · Tapones …»)"] :
      ["Discos inoxidables de la interfaz (opción B: disco de la base y de la mesa, 24 sectores cada uno)", "Corte por plasma/láser de 48 sectores con muescas y chaflanes; rectificado/lapeado de la cara deslizante (Ra 0,4) en rectificadora plana (subcontrato); avellanados en taladro radial",
        "Un disco Ø" + P.D_top + " × " + g.tss + " mm (" + g.M.nombre + ") en 2 semidiscos cortados con plasma, CJP a tope esmerilada a ras; cara 2B o 1D pulida (sin rectificado); " + g.BL.lista.length + " agujeros taladrados y avellanados", "simplificada",
        "Elimina 47 piezas, el rectificado y las muescas; no hay disco en la base", "Disco: flexión entre pastillas y sobre el vacío local, espesor ≥ cabeza avellanada + desgaste, CJP, dilatación restringida (filas «BX · Disco …»)"],
      ["Lámina UHMW sectorizada (24 sectores con rebaje)", "Corte CNC/ruteador o chorro de agua de 24 sectores con rebaje para la barra",
        g.nP + " pastillas " + (g.L.SH.sq ? "cuadradas de " + nf(g.d + g.delta, 2) + " (esquinas R" + nf(g.L.SH.rcp, 1) + ")" : "Ø" + nf(g.d + g.delta, 2)) + " cortadas con router CNC (o chorro de agua) de plancha comercial calibrada de UHMW de " + nf(g.H, 0) + " mm (sin tornear: interferencia lograda en el corte, ± " + nf(P.bx_tol_p, 2) + " mm; agujero y avellanado del tornillo con el router en la misma sujeción; caras de la plancha sin mecanizar)", "simplificada",
        "Pieza única repetitiva, reemplazable de a una con la mesa izada; sin juntas de dilatación entre sectores", "Pastillas: presión, sobrepresión por planitud, PV, desgaste y holgura, aplastamiento contra la pared, núcleo central, ajuste en frío y caliente (filas «BX · Pastillas …»)"],
      ["Portador de las pastillas (nuevo)", "—", "Plancha " + g.tc + " mm de " + astm(fyC(P), fuC(P)) + " cortada con plasma de alta definición (" + g.nP + " agujeros " + (g.L.SH.sq ? "cuadrados de " + g.d + " con esquinas R" + nf(g.L.SH.rc, 1) : "Ø" + g.d) + (g.nW ? " y " + g.nW + " agujeros de soldadura Ø" + g.dPlug + " con filete interior" : "") + "), soldada a la base " + (g.nW ? "con esos filetes y " : "solo ") + "con filetes perimetrales exterior e interior z" + P.bx_w_c, "nueva",
        "Reemplaza los sectores, sus topes y la lámina: la pared del agujero toma el arrastre y el portador lo lleva a torsión hasta sus bordes soldados", "Portador: ligamento, corte por torsión en la sección neta, filetes perimetrales (filas «BX · Portador …»)"],
      ["Barras de tope soldadas de los sectores (inoxidable y acero) y sus muescas", "Barras cortadas, soldadas al disco de la base y a la mesa antes del rectificado; muescas y chaflanes en cada sector", "—", "eliminada",
        g.LAM ? "El par pasa por los tapones y la costura de la lámina (mesa) y por los agujeros del portador (base)" : "El par pasa por los tornillos del disco (mesa) y por los agujeros del portador (base)", g.LAM ? "BX · Tapones y costura de la lámina; BX · Portador (ligamento y torsión)" : "BX · Tornillos del disco (par + dilatación); BX · Portador (ligamento y tapones)"],
      g.LAM ? ["Tornillos de posición ISO 10642 de los sectores", "2 por sector (48 + 24)", "Sin tornillos en la lámina (tapones soldados); tornillos ISO 10642 M" + P.bx_d_sp + " 8.8 de las pastillas (" + g.nP + ")", "simplificada",
        "La lámina se suelda: el par pasa por los tapones y la costura", "BX · Tapones y costura; BX · Pastillas: tornillo"] :
      ["Tornillos de posición ISO 10642 de los sectores", "2 por sector (48 + 24)", "Tornillos ISO 10642 M" + g.dT + " 10.9 de la malla del disco (" + g.BL.lista.length + ") y M" + P.bx_d_sp + " 8.8 de las pastillas (" + g.nP + "); roscas taladradas por plantilla", "simplificada",
        "Los tornillos del disco toman el par y la dilatación: dejan de ser solo de posición", "BX · Tornillos del disco: corte J3.7, aplastamiento J3.11, despegue, engrane; BX · Pastillas: tornillo"],
      ["Cara de apoyo de la base (Ø" + (P.D_top + 20) + ") planeada", "Planeado en mandrinadora (planitud 0,20; Ra 3,2)", "Se mantiene el planeado bajo el portador: las pastillas apoyan en la base y la sobrepresión por planitud depende de d_flat", "se mantiene",
        "La sobrepresión p + Δp con d_flat = " + nf(P.d_flat, 2) + " mm gobierna la saliente de la pastilla; sin planear no hay dato de planitud local", "BX · Pastillas: presión más sobrepresión por planitud (y la sensibilidad d_flat crítico en el README)"],
      ["Cara inferior de la mesa planeada", "Planeado 3 mm (planitud 0,20)", g.LAM ? "Se mantiene: la lámina de " + g.tss + " mm se suelda apretada contra la cara (separación ≤ " + nf(P.bx_g0, 2) + " mm) y la presión de las pastillas la mantiene en contacto" : "Se mantiene: el disco de " + g.tss + " mm copia la cara al apretar los tornillos", "se mantiene", "Misma razón: d_flat del contacto disco–pastillas", "BX · Pastillas: sobrepresión por planitud"],
      ["Placas-guía curvas (placa-leva, 42CrMo4+QT)", "Corte láser/agua con sobremetal, fresado CNC del canto, temple por inducción y rectificado; pasadores de posición H7", "Sin cambio", "se mantiene",
        "El canto es un contacto de Hertz templado y su tolerancia de perfil (± 0,2) entra en el margen de sincronía; con plasma ± 0,5 y sin temple no cumple", "Núcleo: Placas-leva (Hertz, capa templada, sincronía con pv_tolg)"],
      ["Pasadores de posición ISO 8734 de las placas-guía", "Agujeros H7 escariados ciegos en placa y base", "Sin cambio", "se mantiene", "Fijan la posición del canto (± 0,2): ajuste H7/m6 indispensable", "Núcleo: Placas-leva (pasadores de posición)"],
      ["Bloque-uña con garra (34CrNiMo6+QT)", "Forja o bloque; oxicorte con sobremetal, asiento fresado a R, horquilla fresada, agujero Q mandrinado", "Sin cambio", "se mantiene",
        "Asiento conforme templado (Hertz) y horquilla H9/f8 del ojal; 34CrNiMo6 no admite construcción soldada sin WPS calificada y tratamiento", "Núcleo: Bloque-uña (Hertz conforme, cuerpo acodado)"],
      ["Pasadores E y Q, pasadores de empuje (Ø" + P.d_pin + "), pivote (p6/f7)", "Barra rectificada y torno horizontal; pivote rectificado en dos zonas", "Sin cambio", "se mantiene", "Ajustes f8, m6, p6/f7 indispensables (articulaciones, calado y buje)", "Núcleo: Articulaciones, Pasadores de empuje, Pivote"],
      ["Agujeros de los pasadores de empuje en " + (meOn(P) ? "las planchas enteras de la mesa" : "los anillos") + " (Ø" + P.d_pin + " H7, mandrinados en línea)", "Taladro y mandrinado en línea con la mesa armada", meOn(P) ? "Sin cambio (en las dos planchas enteras, rev. 7c: pretaladro Ø80 y mandrinado/escariado en línea)" : "Sin cambio", "se mantiene", "La posición del círculo de pasadores entra en la sincronía de la placa-guía; ajuste m6/H7 antes de soldar", "Núcleo: Placas-leva (sincronía); Pasadores de empuje"],
      ["Tapas del soporte del ojal E (agujero Ø" + P.pv_dE + " H9 en línea)", "Corte plasma del contorno; agujero mandrinado en línea después de soldar", "Sin cambio (el resto del soporte ya es plancha cortada y soldada)", "se mantiene", "Ajuste H9/f8 y coaxialidad 0,10 de las dos tapas", "Núcleo: Soporte del ojal E"],
      ["Collar de asiento del pivote", "Oxicorte de disco Ø" + (P.D_boss + 10) + " desde plancha de " + (P.h_boss + 5) + " mm; caras planeadas; Ø exterior torneado; H7 mandrinado en línea con la base",
        "Ø exterior cortado (oxicorte/plasma) sin tornear; caras sin planear; se mantiene solo el H7 en línea con la base (calado p6 del pivote)", "simplificada",
        "El Ø exterior solo da la holgura radial c_boss_r = " + P.c_boss_r + " mm con el rebaje del cubo (tolerancia de corte ± 0,5 < holgura) y la cara superior no es apoyo (holgura axial c_boss_a)", "Núcleo: Pivote (rebaje del cubo: holguras radial y axial; buje sobre el collar)"],
      ["Rebaje del collar en la mesa", "Agujero Ø" + nf(hr.Drb, 0) + " en la plancha inferior y rebaje del cubo en mandrinadora (" + nf(hr.hHub, 0) + " mm en el cubo con la interfaz BX)",
        hr.hHub > 0 ? "Agujero de la plancha inferior a plasma (holgura radial); el rebaje de " + nf(hr.hHub, 0) + " mm en el cubo sigue en mandrinadora (o bajar h_collar a " + nf(P.h_boss - hr.hHub, 0) + " mm para eliminarlo: pendiente de verificar el pivote)" : "Agujero de la plancha inferior a plasma; sin rebaje en el cubo", hr.hHub > 0 ? "simplificada" : "simplificada",
        "La holgura radial c_boss_r admite el corte térmico; el rebaje del cubo depende de δ", "Núcleo: Pivote (rebaje: h_collar − δ + c_boss_a)"],
      ["Orejas de izaje", "Perfil a plasma; agujero H12 taladrado y mandrinado", "Sin cambio", "se mantiene", "Pasador de grillete: ASME BTH-1 pide agujero liso; no hay verificación del agujero a plasma en el núcleo", "Núcleo: Orejas de izaje (AISC D5)"],
      ...(meOn(P) ? [["Planchas de la mesa (superior e inferior) y anillos de pasadores (rev. 7c, decisión del mandante 19-11-2026)", "Por nivel: disco Ø" + nf(2 * TT_.prIn(P), 0) + " (MES-001 / MES-003) + anillo de pasadores Ø" + P.D_top + "/Ø" + nf(2 * TT_.prIn(P), 0) + " (MES-002 / MES-004) en 4 segmentos de 90° con empalmes CJP (UT 100 %) y unión soldada circunferencial plancha–anillo",
        "Una plancha completa Ø" + P.D_top + " × " + P.t_top + " por nivel (" + astm(P.Fy, P.Fu) + ") con los " + Math.round(P.N_pin) + " agujeros Ø" + P.d_pin + " H7 en la misma pieza (taladrados y mandrinados en línea con la mesa armada); compra: plancha de " + P.t_top + " mm de al menos " + P.D_top + " × " + P.D_top, "simplificada",
        "Elimina 2 piezas (8 segmentos), 8 empalmes CJP y 2 uniones circunferenciales con su UT; requiere plancha de formato ≥ " + P.D_top + " × " + P.D_top + "; masas y rigidez iguales (t_pr = t_top = t_bot)", "BX · Mesa de plancha entera (espesor único, uniones que no aplican, masa); núcleo: Mesa (FEA), Pasadores de empuje"]] : []),
      ["Refuerzos de esquina, soporte del ojal E (paredes y muñones), marco perimetral, mesa (planchas, almas, nervios" + (meOn(P) ? ")" : ", anillos)"), "Plancha cortada y soldada (con alivio de tensiones de los conjuntos)", "Sin cambio: ya son plasma + soldadura", "se mantiene", "—", "Núcleo: Base, Mesa (FEA), Soldaduras"],
      ["Calidad del acero de las planchas (rev. 7, decisión del mandante 18-11-2026)", "Rev. 5: ASTM A36 en todas las planchas; rev. 6: A572 Gr. 50 en anillos, base, soporte E y portador y A36 en el resto",
        "Por pieza: " + (meOn(P) ? "zona de pasadores de las planchas enteras de la mesa t_pr = t_top = t_bot = " + P.t_pr + " (" + astm(P.Fy_pr > 0 ? P.Fy_pr : P.Fy, P.Fu_pr > 0 ? P.Fu_pr : P.Fu) + "; rev. 7c: sin anillos)" : "anillos de pasadores t_pr = " + P.t_pr + " (" + astm(P.Fy_pr > 0 ? P.Fy_pr : P.Fy, P.Fu_pr > 0 ? P.Fu_pr : P.Fu) + "; el superior queda de máx(t_pr, t_top) = " + Math.max(P.t_pr, P.t_top) + ")") + ", plancha base " + P.t_base + " (" + astm(P.Fy_base > 0 ? P.Fy_base : P.Fy, P.Fu_base > 0 ? P.Fu_base : P.Fu) + "), soporte del ojal E: paredes y muñones " + P.pv_tbox + ", tapas " + P.pv_tl + " (" + astm(P.Fy_boxE > 0 ? P.Fy_boxE : P.Fy, P.Fu_boxE > 0 ? P.Fu_boxE : P.Fu) + "), portador " + g.tc + " (" + astm(fyC(P), fuC(P)) + "); el resto, " + astm(P.Fy, P.Fu) + ": mesa (planchas " + P.t_top + "/" + P.t_bot + ", almas y nervios " + P.t_web + "/" + P.t_rib + "), collar " + P.h_boss + ", marco, orejas; refuerzo de esquina y atiesador " + astm(P.Fy_dbl > 0 ? P.Fy_dbl : P.Fy, P.Fu_dbl > 0 ? P.Fu_dbl : P.Fu) + " con calidad Z (ASTM A770)",
        "se mantiene", "Cada pieza con su calidad; las filas con dos piezas usan la menor (base + refuerzo, base + collar, CJP de las paredes E sobre el refuerzo); identificar y trazar las planchas A572 (marcado de colada) para que no se mezclen con las A36", "Núcleo con Fy_pr, Fy_base, Fy_boxE, Fy_dbl; BX · Portador (Fy_bxc); docs/bx/README_BX.md §10"],
      ["Ranuras de engrase y graseras de la interfaz", "Fresadas en el disco de la mesa (opción A); graseras en el borde", "—: UHMW sobre inoxidable sin ranuras (μ de la opción B); engrase opcional de montaje", "eliminada", "La opción B ya no las usa", "Interfaz: μ de la opción B (muB_*)"],
    ];
    if (pv && cylOn(full(P))) { const cg = cylGeo(full(P));
      rows.push(["Cilindros hidráulicos (2), rev. 7d (decisión del mandante 19-11-2026)", "Comerciales: especificación de compra ACC-013 (Ø" + P.D_bore + "/Ø63, 10 000 psi, ojales con rótula, marca A DEFINIR POR CATÁLOGO)",
        "FABRICADOS: camisa de barra hueca ST-52 132 × 80 maquinada a Ø" + P.D_body + " × Ø" + P.D_bore + " H8 bruñida, fondo de copa S460NL t = " + cg.tf + " soldado (CJP) con el ojal trasero (rótula GE70ES), tapa roscada M" + full(P).bx_cyl_d_t + " × " + full(P).bx_cyl_P_t + " con los sellos por dentro de la rosca, pistón y tuerca 42CrMo4+QT, vástago Ø" + P.d_rod + " cromado con el ojal soldado por fricción; prueba a " + nf(cg.kt * P.p_relief, 0) + " bar (láminas ACC-013 y ACC-028 a ACC-035)",
        "nueva", "Decisión del mandante: el cilindro se fabrica según su croquis; largo retraído " + P.L0 + " y carrera " + P.stroke + " sin cambio (cuerpo " + cg.Lbody + ", c_vástago " + P.c_rod + ")", "Grupo «Cilindro» (Lamé, fondo Roark/UG-34, roscas, vástago, ojales BTH-1, rótula, puertos, amortiguación)"]); }
    if (!pv) rows.push(["Accionamiento guiado (patín, bancada con ranura T, uña, riel-leva)", "Patín y uña mecanizados, ranura T fresada", "Sin cambio (BX no modifica el accionamiento)", "se mantiene", "Ajustes H9/f8 y contactos templados", "Núcleo: Patín y guía, Uña, Leva de reenganche"]);
    return rows.map(([pieza, antes, despues, estado, motivo, verificacion]) => ({ pieza, antes, despues, estado, motivo, verificacion }));
  }

  // Filas del modo 1 (lámina de 3 mm soldada con tapones y costura perimetral)
  function lamRows(P, C, M, L, g, ce, add, D, th) {
    const PL = g.PL, pfx = "BX · ", te = PL.te, nT = PL.pts.length, sad = 0.6 * M.Fy, nPi = PL.pts.filter((q) => q.pista).length;
    const RW = "AISC 360-22 §J2.3 (tapones: Ø, separación, relleno), §J2.4 (F_nw = 0,60·F_EXX sobre el área del agujero) con F_w = 0,60·F_EXX/(1,20·N_d) del proyecto (ASME BTH-1-2020 §3-3.4); aporte E309L (AWS A5.4) / ER309L (AWS A5.9); WPS disímil según AWS D1.6/D1.6M:2017";
    const RS = "AISI S100-16 §J2.2.2.2 (= ASCE 8-02 §5.2.2, inoxidable conformado en frío): lámina alrededor de un tapón, d_a = Ø − t";
    const REFD = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16 (placa circular empotrada, carga uniforme)";
    const REFC = "Timoshenko y Woinowsky-Krieger §17 (placa anular, flexión simétrica): celda equivalente de área tributaria, con la rigidez de la plancha inferior más la lámina";
    const pista = nPi === 0 ? "ningún tapón queda en una pista: los anillos de tapones van en las bandas libres entre pistas (el disco gira sobre pastillas fijas: esos tapones nunca pasan bajo una pastilla)" : nPi + " de " + nT + " tapones en pistas (anillos agregados por pandeo): pasan bajo las pastillas esmerilados a ras y pulidos; no hay coincidencia sistemática con un radio de pastilla (cada pista barre su ancho completo)";
    add({ sys: "est", name: pfx + "Tapones: corte del metal de aporte (" + nT + " × Ø" + nf(PL.D, 1) + ") con el par de calado (reparto polar elástico, sin la costura)", formula: "V = T_calado·r/Σr² ≤ F_w·π·Ø²/4; F_w = 0,60·" + P.bx_FEXX_ss + "/(1,20·" + P.Nd + ") = " + nf(PL.Fw, 1) + " MPa; T_calado = " + nf(C.Tcal, 1) + " kN·m (μ máx.); paso circunferencial " + PL.sc + " mm, anillos R" + PL.rings.map((q) => nf(q.r, 0)).join("/R"), dem: PL.Vmax / 1e3, cap: PL.capW / 1e3, unit: "kN", ref: RW });
    add({ sys: "est", name: pfx + "Tapones: aplastamiento y desgarro de la lámina alrededor del tapón", formula: "V ≤ P_n/Ω; d_a/t = " + nf(PL.da / te, 2) + " ≤ 0,815√(E/F_u) → P_n = 2,20·t_e·d_a·F_u = " + nf(PL.PnS / 1e3, 1) + " kN, Ω = " + nf(PL.OmS, 2) + "; t_e = t − sobreespesor = " + nf(te, 2) + " mm", dem: PL.Vmax / 1e3, cap: PL.capS / 1e3, unit: "kN", ref: RS });
    add({ sys: "est", name: pfx + "Tapones: arrastre local de la pastilla más cargada repartido en los tapones cercanos (" + PL.loc.n + " a ≤ " + nf(PL.rho, 0) + " mm del centro, mínimo en 24 posiciones del giro)", formula: "V = μ_ef·p_i·A_p/n_local ≤ mín(soldadura; lámina); μ_ef = " + nf(C.muEff, 3) + "; F = " + nf(PL.loc.F / 1e3, 1) + " kN (sin el roce lámina–plancha bajo la pastilla, conservador)", dem: PL.loc.V / 1e3, cap: PL.cap / 1e3, unit: "kN", ref: RW + "; " + RS });
    add({ sys: "est", kind: "geo", name: pfx + "Tapones: Ø del agujero para la lámina de " + nf(g.tss, 1) + " mm (mínimo y máximo) y relleno", formula: "t + 8 ≤ Ø ≤ máx(Ø_mín + 3; 2,25·t) = " + nf(g.tss + 8, 1) + " … " + nf(Math.max(g.tss + 11, 2.25 * g.tss), 1) + "; Ø ≥ 9,5 (AISI S100 §J2.2.1); relleno = t (t ≤ 16, §J2.3b)", dem: Math.max((g.tss + 8) / PL.D, 9.5 / PL.D, PL.D / Math.max(g.tss + 11, 2.25 * g.tss)), cap: 1, fu: Math.max((g.tss + 8) / PL.D, 9.5 / PL.D, PL.D / Math.max(g.tss + 11, 2.25 * g.tss)), unit: "–", ref: "AISC 360-22 §J2.3a, §J2.3b; AISI S100-16 §J2.2.1; AWS D1.3/D1.3M:2018 (referencia de detalle)" });
    add({ sys: "est", kind: "geo", name: pfx + "Tapones: separación entre centros", formula: "4·Ø ≤ s_mín", dem: 4 * PL.D, cap: PL.sMin, unit: "mm", ref: "AISC 360-22 §J2.3a" });
    add({ sys: "est", kind: "geo", name: pfx + "Tapones: distancia al borde de la lámina (costuras exterior e interior; la junta a tope queda a ≥ " + nf(Math.max(P.bx_c_cjp, PL.e), 0) + " mm)", formula: "e ≥ máx(1,5·Ø; Ω·V/(F_u·t_e)), Ω = 2,0 (F_u/F_y ≥ 1,08)", dem: PL.eReq, cap: PL.eAv, unit: "mm", ref: "AISI S100-16 §J2.2.2.1 y §J2.2.1 (= ASCE 8-02 §5.2.2)" });
    add({ sys: "est", kind: "info", name: pfx + "Tapones: posición respecto de las pistas de las pastillas", formula: pista + "; bandas libres R " + PL.free.map(([a, b]) => nf(a - PL.D / 2, 0) + "–" + nf(b + PL.D / 2, 0)).join(", ") + " mm (holgura " + nf(P.bx_c_pista, 1) + " mm a la pista)", dem: nPi, cap: nT, unit: "en pistas / total", ref: "Geometría; criterio del proyecto (esmerilado a ras y pulido de todos los tapones)" });
    const qE = Math.hypot(PL.qT, PL.qTh), capE = Math.min(PL.capSeamW, PL.capSeamS);
    add({ sys: "est", name: pfx + "Costura perimetral exterior de la lámina z" + nf(PL.w, 1) + " (R" + nf(PL.Rlo, 0) + "): todo el par de calado sola (redundancia de los tapones) más la membrana térmica", formula: "q = √((T/(2πR²))² + (σ_t·t_e)²) = √(" + nf(PL.qT, 1) + "² + " + nf(PL.qTh, 1) + "²) ≤ mín(F_w·0,707·w; 0,75·t_e·F_u/3,05)", dem: qE, cap: capE, unit: "N/mm", ref: "AISC 360-22 §J2.4; AISI S100-16 §J2.5 (lámina, filete longitudinal L/t ≥ 25); ASME BTH-1-2020 §3-3.4" });
    add({ sys: "est", name: pfx + "Costura perimetral interior de la lámina z" + nf(PL.w, 1) + " (R" + nf(PL.Rli, 0) + "): membrana térmica", formula: "q = σ_t·t_e = " + nf(PL.qTh, 1) + " ≤ mín(F_w·0,707·w; 0,75·t_e·F_u/3,05) (el par va a los tapones y a la costura exterior)", dem: PL.qTh, cap: capE, unit: "N/mm", ref: "AISC 360-22 §J2.4; AISI S100-16 §J2.5" });
    const wMin = Math.min(wMinAWS(P.t_bot), g.tss), fW = Math.max(wMin / PL.w, PL.w / g.tss);
    add({ sys: "est", kind: "geo", name: pfx + "Costura perimetral: tamaño del filete en el canto de la lámina", formula: "mín(w_mín(T = " + P.t_bot + "); t) ≤ w ≤ t (canto de " + nf(g.tss, 1) + " mm < 6 mm)", dem: fW, cap: 1, fu: fW, unit: "–", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7 (el tamaño mínimo no necesita superar el espesor de la parte más delgada); AISC 360-22 §J2.2b" });
    const cjpS = Math.max(PL.sTh, ce.sigSs);
    add({ sys: "est", name: pfx + "Lámina: junta a tope entre paneles (ranura de penetración completa sobre la plancha) con la mayor tensión de membrana o de flexión", formula: "máx(σ_térmica restringida; σ_lámina en la celda) ≤ 0,6·F_y; " + PL.PN.n + " paneles, junta(s) en y = " + PL.PN.juntas.map((y) => nf(y, 0)).join(", "), dem: cjpS, cap: sad, unit: "MPa", ref: "AWS D1.6/D1.6M:2017; AISC 360-22 Tabla J2.5 (CJP: resistencia del metal base)" });
    add({ sys: "est", kind: "geo", name: pfx + "Lámina: paneles dentro del formato comercial " + P.bx_fmt_a + " × " + P.bx_fmt_b + " (margen de corte " + PL.PN.m + " mm)", formula: PL.PN.n + " franjas de " + nf(PL.PN.w, 0) + " × " + nf(Math.max(...PL.PN.paneles.map((q) => q.largo)), 0) + " mm", dem: Math.max(...PL.PN.paneles.map((q) => Math.max(q.ancho / (P.bx_fmt_a - 2 * PL.PN.m), q.largo / (P.bx_fmt_b - 2 * PL.PN.m)))), cap: 1, fu: Math.max(...PL.PN.paneles.map((q) => Math.max(q.ancho / (P.bx_fmt_a - 2 * PL.PN.m), q.largo / (P.bx_fmt_b - 2 * PL.PN.m)))), unit: "–", ref: "Formato del proveedor" });
    add({ sys: "est", name: pfx + "Lámina: tensión térmica de membrana (secundaria, autolimitante) como rango frente a 2·Fy (adaptación)", formula: "Δσ = E·Δα·ΔT/(1 − ν) ≤ 2·F_y; Δα = " + nf(PL.dAl * 1e6, 1) + "×10⁻⁶/K, ΔT = " + nf(g.dTd, 0) + " K", dem: PL.sTh, cap: 2 * M.Fy, unit: "MPa", ref: "ASME BPVC VIII-2 (2023) 5.5.6.1; " + M.fuente });
    add({ sys: "est", name: pfx + "Lámina: tensión térmica de membrana frente a Fy (conservador: sin plastificación)", formula: "σ = E·Δα·ΔT/(1 − ν) ≤ F_y", dem: PL.sTh, cap: M.Fy, unit: "MPa", ref: "Termoelasticidad; criterio del revisor" });
    add({ sys: "est", name: pfx + "Lámina: pandeo por la compresión térmica entre apoyos (panel " + nf(PL.ap, 0) + " mm: mayor hueco radial entre anillos de tapones y costuras o paso circunferencial)", formula: "σ ≤ σ_cr = 2·π²E/(12(1 − ν²))·(t_e/a)² (compresión biaxial igual, bordes simplemente apoyados; sin el apoyo unilateral de la plancha, conservador)", dem: PL.sTh, cap: PL.sCr, unit: "MPa", ref: "Timoshenko y Gere, Theory of Elastic Stability §9.5" });
    add({ sys: "est", name: pfx + "Lámina: pandeo combinado (compresión térmica + corte del arrastre de la pastilla más cargada)", formula: "σ/σ_cr + (τ/τ_cr)² ≤ 1; τ = 2F/(π·d·t_e) = " + nf(PL.tau, 1) + " MPa, τ_cr = 9,34·π²E/(12(1 − ν²))·(t_e/a)² = " + nf(PL.tCr, 0) + " MPa", dem: PL.inter, cap: 1, unit: "–", ref: "Timoshenko y Gere §9.7 (placa en corte, k_s = 9,34) y §9.9 (interacción)" });
    add({ sys: "est", kind: "geo", name: pfx + "Lámina: despegue entre tapones (separación g₀ = " + nf(P.bx_g0, 2) + " mm sobre el panel de radio " + nf(PL.bP.a, 0) + "): la presión de la pastilla la cierra", formula: "p_cierre = 64·D·g₀/a⁴ ≤ p_mín de las pastillas = " + nf(PL.pMin, 2) + " MPa (la presión pasa a la mesa por contacto, sin flexión libre de la lámina)", dem: PL.bP.pc, cap: PL.pMin, unit: "MPa", ref: REFD });
    add({ sys: "est", name: pfx + "Lámina: despegue entre tapones: flexión al cerrar la separación (secundaria) frente a 2·Fy", formula: "σ = 4·E·t_e·g₀/((1 − ν²)·a²) ≤ 2·F_y (deformación impuesta, autolimitante)", dem: PL.bP.sig, cap: 2 * M.Fy, unit: "MPa", ref: REFD + "; ASME BPVC VIII-2 5.5.6.1" });
    add({ sys: "est", kind: "geo", name: pfx + "Lámina: vacío local Ø" + P.ss_void + " sin contacto (separación g₀ = " + nf(P.bx_g0, 2) + " mm): la presión de la pastilla lo cierra", formula: "p_cierre = 64·D·g₀/a⁴ ≤ p_mín = " + nf(PL.pMin, 2) + " MPa; a = " + nf(PL.bV.a, 0) + " mm (reemplaza la flexión libre del disco sobre el vacío del modo 0)", dem: PL.bV.pc, cap: PL.pMin, unit: "MPa", ref: REFD });
    add({ sys: "est", name: pfx + "Lámina: vacío local Ø" + P.ss_void + ": flexión al cerrar (secundaria) frente a 2·Fy", formula: "σ = 4·E·t_e·g₀/((1 − ν²)·a²) ≤ 2·F_y", dem: PL.bV.sig, cap: 2 * M.Fy, unit: "MPa", ref: REFD + "; ASME BPVC VIII-2 5.5.6.1" });
    const Nf = P.turns_yr * P.life * Math.max(...(() => { const m = new Map(); L.pucks.forEach((q) => { const k = Math.round(q.r); m.set(k, (m.get(k) || 0) + 1); }); return [...m.values()]; })());
    add({ sys: "est", name: pfx + "Lámina: fatiga en el borde de los tapones por el cierre cíclico de la separación entre tapones (cat. E, N = " + Math.round(Nf) + ")", formula: "Δσ = σ_cierre ≤ F_SR(E, N); N = vueltas/año·vida·pastillas por anillo", dem: PL.bP.sig, cap: TT_.FSR("E", Nf), unit: "MPa", ref: "AISC 360-22 Apéndice 3, Tabla A-3.1 (metal base junto a tapones: cat. E)" });
    add({ sys: "est", name: pfx + "Lámina: flexión de la celda entre pastillas (" + M.nombre + ", solidaria con la plancha inferior de " + P.t_bot + " mm)", formula: "σ_s = E_s·κ·(t_inf/2 + t_e) ≤ 0,6·F_y,s; κ = M_máx/(D_m + D_s); M de la placa anular a = d/2 … b = " + nf(ce.b, 1) + " mm con q_máx", dem: ce.sigSs, cap: sad, unit: "MPa", ref: REFC });
    add({ sys: "est", name: pfx + "Plancha inferior de la mesa: flexión de la celda entre pastillas (con la lámina)", formula: "σ_m = 6·M_máx·D_m/(D_m + D_s)/t_inf² ≤ 0,6·F_y (t_inf = " + P.t_bot + " mm)", dem: ce.sigPl, cap: 0.6 * P.Fy, unit: "MPa", ref: REFC });
    add({ sys: "est", kind: "geo", name: pfx + "Lámina: flecha de la celda entre pastillas", formula: "w ≤ mín(d_flat; 0,1·h_p)", dem: ce.w, cap: Math.min(P.d_flat, 0.1 * g.hp), unit: "mm", ref: REFC + "; criterio del proyecto" });
    add({ sys: "est", name: pfx + "Lámina sobre la pastilla faltante o el mayor hueco de la malla (la toma la plancha de la mesa con la lámina)", formula: "σ_s = E_s·(q·a_g²/8)/(D_m + D_s)·(t_inf/2 + t_e) ≤ 0,6·F_y,s; a_g = " + nf(g.DT.aG, 1) + " mm", dem: g.DT.gap.sig, cap: sad, unit: "MPa", ref: REFD + "; placas apiladas solidarias (cota de sección compuesta)" });
    add({ sys: "est", name: pfx + "Plancha inferior de la mesa sobre la pastilla faltante (con la lámina)", formula: "σ_m = 6·(q·a_g²/8)·D_m/(D_m + D_s)/t_inf² ≤ 0,6·F_y", dem: g.DT.gap.sigPl, cap: 0.6 * P.Fy, unit: "MPa", ref: REFD });
    add({ sys: "est", kind: "geo", name: pfx + "Lámina: sobreespesor disponible frente al pulido de tapones y juntas y al desgaste", formula: "pulido " + nf(P.bx_pul, 2) + " + desgaste del inox (despreciable frente al UHMW; dato pendiente) ≤ sobreespesor " + nf(P.ss_allow, 2) + " mm (la resistencia se verifica con t_e = t − sobreespesor = " + nf(te, 2) + " mm)", dem: P.bx_pul, cap: P.ss_allow, unit: "mm", ref: "Criterio del proyecto" });
    const Tup = P.phi_lift * g.mSS * G / nT, capTw = Math.PI / 4 * PL.D ** 2 * P.bx_FEXX_ss / 2.5, capTs = 0.8 * (M.Fu / M.Fy) ** 2 * te * PL.da * M.Fu / 2.5;
    add({ sys: "est", name: pfx + "Lámina: tracción de los tapones al izar la mesa con la lámina colgada", formula: "T = φ_izaje·m_lámina·g/n ≤ mín(π·Ø²/4·F_EXX; 0,8(F_u/F_y)²·t·d_a·F_u)/Ω, Ω = 2,50", dem: Tup / 1e3, cap: Math.min(capTw, capTs) / 1e3, unit: "kN", ref: "AISI S100-16 §J2.2.3" });
    add({ sys: "est", kind: "info", name: pfx + "Lámina: planitud después de soldar (nota de fabricación: secuencia y tapones por zonas)", formula: lamFab(P, PL), dem: P.bx_g0, cap: P.d_flat, unit: "mm (g₀ / d_flat)", ref: "AWS D1.6/D1.6M:2017; criterio del proyecto" });
    add({ sys: "est", kind: "info", name: pfx + "Lámina: masa (" + PL.PN.n + " paneles de " + nf(g.mSS / PL.PN.n, 0) + " kg)", formula: "m = ρ·π(R_ext² − R_int²)·t", dem: g.mSS, cap: g.mSS / PL.PN.n, unit: "kg / kg por panel", ref: "Geometría" });
  }
  /* ---------------- Verificaciones propias (formato de tt300c: grupo «Interfaz inox») ---------------- */
  function bxRows(P, R, D) {
    P = full(P);
    const out = [], add = (o) => out.push(Object.assign({ kind: "fu", grp: GRP, bx: true }, o, { fu: o.kind === "info" || o.kind === "pend" ? (o.fu != null && o.kind === "pend" ? o.fu : null) : (o.fu != null ? o.fu : ((o.cap > 0 && o.dem >= 0) ? o.dem / o.cap : Infinity)) }));
    const S = size(P, R, D.frozen), g = S.geo, C = g.C, M = g.M, L = g.L, BF = g.BF, BL = g.BL, Nd = P.Nd, Fw = P.FEXX * 0.60 / (1.20 * Nd), FvC = fyC(P) / (Nd * Math.sqrt(3));
    const e = puckEval(P, C, M, L, g.d, g.s, g.tc, g.lig, g.nw, g.hp, g.tss, g.dPlug), ce = cellOf(P, C, M, L, g.d, g.tss, g.s), fl = g.fl;
    const th = P.__th, T = th ? th.T : P.T_ref, dTu = T - P.T_ref, FA = L.FA || L.pMax * L.Ap, Fi = C.muRes * FA, Fi0 = C.muU * FA, sad = 0.6 * M.Fy, te = g.tss - P.ss_allow;
    const REFD = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16 (placa circular empotrada, carga uniforme); 0,6Fy (criterio del proyecto, como el núcleo)";
    const REFC = "Timoshenko y Woinowsky-Krieger §17 (placa anular, flexión simétrica): celda equivalente de área tributaria, borde interior empotrado sobre la pastilla y exterior guiado; solución cerrada verificada por diferencias finitas (tests/test_tt300bx.js)";
    const pfx = "BX · ";
    /* --- Pastillas de UHMW --- */
    add({ sys: "est", name: pfx + "Pastillas: presión máxima (q sobre el área tributaria, excentricidad hacia la pastilla) frente a la admisible sostenida", formula: "p = ∫q·dA_trib / A_pastilla ≤ p_adm,UHMW; q = q_med·(1 + k_q·x·û/R_o) (Navier, como el núcleo); A_pastilla = π·d²/4 con d = " + g.d + " mm; cobertura " + nf(L.cov * 100, 1) + " %", dem: L.pMax, cap: P.p_uhmw, unit: "MPa", ref: REFU });
    add({ sys: "est", name: pfx + "Pastillas: presión más sobrepresión por falta de planitud (pastilla alta entre vecinas)", formula: "p + Δp ≤ p_adm; Δp = d_flat/(c_p + A_p/k_placa); c_p = h_p/E_c(S) + (t_portador − 1)/M (S = d/(4h_p), M = E(1−ν)/((1+ν)(1−2ν)), ν = 0,45, E = E_UHMW aparente); k_placa = 16π(D_disco + D_mesa)/s² (placa empotrada en las vecinas con carga puntual; t_mesa = " + e.worst.tm + " mm)", dem: e.worst.pd, cap: P.p_uhmw, unit: "MPa", ref: REFU + "; Timoshenko §19 (carga concentrada, placa empotrada: w = P·a²/(16πD)); módulo confinado como TT uhConf" });
    if (!th) {   // a la temperatura máxima de servicio de la interfaz (ambiente, T_ifc_max): capacidades del UHMW interpoladas (supuesto C, sin curva del proveedor)
      const kI = g.kI, Ti = P.T_ifc_max, e5 = puckEval(P, C, M, L, g.d, g.s, g.tc, g.lig, g.nw, g.hp, g.tss, g.dPlug, kI.E_uh), R5 = REFU + "; k a " + Ti + " °C interpolado linealmente entre 1,0 a " + P.T_ref + " °C y kT_p_uh/kT_E_uh a 80 °C (registro «Temperatura», confianza C)";
      add({ sys: "est", name: pfx + "Pastillas a " + Ti + " °C: presión máxima frente a k_p·p_adm (k_p = " + nf(kI.p_uh, 2) + ")", formula: "p ≤ k_p(T_ifc,máx)·p_adm; k_p = 1 − (1 − kT_p_uh)·(T − T_ref)/(80 − T_ref)", dem: L.pMax, cap: kI.p_uh * P.p_uhmw, unit: "MPa", ref: R5 });
      add({ sys: "est", name: pfx + "Pastillas a " + Ti + " °C: presión más sobrepresión por planitud (módulo k_E·E)", formula: "p + Δp ≤ k_p·p_adm; Δp con E_UHMW·k_E (k_E = " + nf(kI.E_uh, 2) + ")", dem: e5.worst.pd, cap: kI.p_uh * P.p_uhmw, unit: "MPa", ref: R5 });
      add({ sys: "est", name: pfx + "Pastillas a " + Ti + " °C: valor PV frente a k_p·PV_adm", formula: "PV = p_i·v_i ≤ k_p·PV_adm", dem: e.PVm, cap: kI.p_uh * P.PV_uh, unit: "MPa·m/s", ref: R5 });
      add({ sys: "est", name: pfx + "Pastillas a " + Ti + " °C: aplastamiento contra la pared del agujero (arrastre residual)", formula: "σ = (μ_máx − μ_b)·p·A_p/(d·(t − 1)) ≤ k_p·p_adm; sin μ_b: FU " + nf(Fi0 / (g.d * (g.tc - 1)) / (kI.p_uh * P.p_uhmw), 2), dem: Fi / (g.d * (g.tc - 1)), cap: kI.p_uh * P.p_uhmw, unit: "MPa", ref: R5 });
      const kp8 = TT_.thermalFactors(P, P.bx_Tmax).k.p_uh;
      add({ sys: "est", kind: "info", name: pfx + "LIMITACIÓN DE USO: la interfaz no se verifica a " + P.bx_Tmax + " °C (temperatura del sello hidráulico, no de la interfaz); con k_p = " + nf(kp8, 2) + " la presión de las pastillas daría FU " + nf(L.pMax / (kp8 * P.p_uhmw), 2), formula: "Servicio de la interfaz limitado a T ≤ " + Ti + " °C ambiente (decisión del mandante 16-11-2026); a " + P.bx_Tmax + " °C solo informativo", dem: L.pMax, cap: kp8 * P.p_uhmw, unit: "MPa", ref: R5, limitacion: true });
    }
    add({ sys: "est", name: pfx + "Pastillas: valor PV en la pastilla más exigida (durante la carrera)", formula: "PV = p_i·v_i ≤ PV_adm; v_i = r_i·v_cil/a_mín, v_cil = Q/(n·A) (como el núcleo)", dem: e.PVm, cap: P.PV_uh, unit: "MPa·m/s", ref: REFU });
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: saliente frente a desgaste, fluencia, planitud y flecha entre pastillas al final de la vida", formula: "h_p ≥ g_mín + planitud del portador + h_desgaste + δ_fluencia + d_flat + w_celda = " + nf(P.bx_g_min, 2) + " + " + nf(P.bx_bow, 2) + " + " + nf(e.wear, 4) + " + " + nf(e.creep, 3) + " + " + nf(P.d_flat, 2) + " + " + nf(ce.w, 4) + "; h_desgaste = k·p·s (s = vida·vueltas·2π·r); δ = p·c_p", dem: P.bx_g_min + P.bx_bow + e.wear + e.creep + P.d_flat + ce.w, cap: g.hp, unit: "mm", ref: REFU + "; criterio del proyecto (el disco no toca el portador ni las cabezas)" });
    add({ sys: "est", kind: "info", name: pfx + "Pastillas: factor de forma de la parte libre, módulo aparente y confinado, fluencia", formula: "S = d/(4·h_p); E_c = E[1 + (M/E − 1)S²/(1 + S²)]; M = E(1 − ν)/((1 + ν)(1 − 2ν)); δ = p·[h_p/E_c + (t_portador − 1)/M]", dem: e.S, cap: e.Ec, unit: "– / MPa", ref: REFU + "; Gent y Lindley (bloques confinados), como TT uhConf" });
    add({ sys: "est", name: pfx + "Pastillas: aplastamiento contra la pared del agujero del portador (arrastre residual (μ_máx − μ_b)·N)", formula: "σ = F/(" + (L.SH.sq ? "lado" : "d") + "·(t_portador − 1)) ≤ p_adm (cara embebida); F = (μ_máx − μ_b)·p·A_p = (" + nf(C.muU, 2) + " − " + nf(C.muB, 2) + ")·N (la cara inferior apoyada en la base con N toma μ_b·N); sin μ_b: FU " + nf(Fi0 / (g.d * (g.tc - 1)) / P.p_uhmw, 2) + "; chaflán inferior 1 mm", dem: Fi / (g.d * (g.tc - 1)), cap: P.p_uhmw, unit: "MPa", ref: REFU + "; equilibrio" + (C.muB > 0 ? "; μ_b = " + nf(C.muB, 2) + ": límite inferior de UHMW sobre acero seco (fichas de fabricante, p. ej. TIVAR 1000, ASTM D1894; confianza C); el asiento de la pastilla queda seco y desengrasado" : "") });
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: resultante en el núcleo central del pie (sin despegue por el par del arrastre)", formula: "e = F·(h_p + t_portador/2)/N = μ_máx·(h_p + t/2) ≤ " + (L.SH.sq ? "a/6 (núcleo central de la sección cuadrada)" : "d/8 (núcleo central de la sección circular)") + "; la pared reacciona a media altura del portador", dem: C.muU * (g.hp + g.tc / 2), cap: L.SH.kern, unit: "mm", ref: "Resistencia de materiales (núcleo central r/4 = d/8); equilibrio" });
    const capSp = 0.45 * P.bx_Fu_sp / 2 * Math.PI / 4 * P.bx_d_sp ** 2;
    add({ sys: "est", name: pfx + "Pastillas: tornillo M" + P.bx_d_sp + " 8.8 al corte si tomara todo el arrastre residual (μ_máx − μ_b)·N (camino alternativo, redundancia)", formula: "V = F ≤ Fnv·A_b/Ω; Fnv = 0,45·Fu (rosca en el plano), Ω = 2,00; sin μ_b: FU " + nf(Fi0 / capSp, 2), dem: Fi / 1e3, cap: capSp / 1e3, unit: "kN", ref: "AISC 360-22 §J3.7, Tabla J3.2" });
    const fit = D.pastillas.ajuste;
    const holgF = Math.max(0, -(g.delta - g.tolS - g.dal * (P.T_ref - P.bx_Tmin) * g.d)) / 2;
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: el tornillo queda fuera del camino del arrastre (holgura del agujero del tornillo frente a la holgura en frío a " + P.bx_Tmin + " °C)", formula: "c_tornillo − 0,2 ≥ holgura radial en frío = máx(0; −(δ − tol − Δd_frío))/2; Δd_frío = (α_UHMW − α_acero)·(T_ref − T_mín)·d", dem: holgF + 0.2, cap: P.bx_c_sp, unit: "mm", ref: "Criterio del proyecto; α_UHMW = " + P.bx_al_uh + "×10⁻⁶/K (mandante)" });
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: interferencia mínima a la temperatura de montaje (" + P.T_ref + " °C)", formula: "δ − tol_agujero − tol_pastilla ≥ 0 (la pastilla queda retenida al montar); δ = " + nf(g.delta, 2) + " mm", dem: g.tolS, cap: g.delta, unit: "mm", ref: "Criterio del proyecto" });
    const epsT = (g.delta + g.tolS + Math.max(0, g.dal * dTu * g.d)) / g.d, epsH = (g.delta + g.tolS + g.dHot) / g.d;
    add({ sys: "est", name: pfx + "Pastillas: deformación radial por interferencia a " + (th ? T : P.T_ifc_max) + " °C (máxima: tolerancias y dilatación)", formula: "ε = (δ + tol + (α_UHMW − α_acero)·ΔT·d)/d ≤ ε_adm = " + nf(P.bx_eps_max, 1) + " %; la presión del ajuste relaja por fluencia (p_20 = E_ct·ε/(1 − ν) = " + nf(fit.p_ajuste_20, 1) + " MPa)", dem: (th ? epsT : epsH) * 100, cap: P.bx_eps_max, unit: "%", ref: "Criterio del proyecto (como p_adm ≈ ¼ del esfuerzo al 10 % de deformación)" });
    add({ sys: "est", kind: "info", name: pfx + "Pastillas: dilatación libre (cada pastilla en su agujero: sin juntas entre piezas de UHMW) y crecimiento de la saliente", formula: "Δd = (α_UHMW − α_acero)·ΔT·d en frío (" + P.bx_Tmin + " °C) / en caliente (" + P.T_ifc_max + " °C); Δh = α_UHMW·(T_ifc,máx − T_ref)·H = " + nf(P.bx_al_uh * 1e-6 * (P.T_ifc_max - P.T_ref) * g.H, 3) + " mm", dem: g.dCold, cap: g.dHot, unit: "mm", ref: REFU });
    const kSp = isoK(P.bx_d_sp), tp = D.pastillas.tornillo;
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: cabeza del tornillo bajo la cara del portador con UHMW mínimo debajo", formula: "t_portador − 0,5 − k ≥ u_mín (cabeza a h_p + 0,5 bajo la cara de la pastilla: el disco toca el portador antes que la cabeza)", dem: P.bx_u_min, cap: g.tc - 0.5 - kSp, unit: "mm", ref: "ISO 10642 (k); criterio del proyecto" });
    add({ sys: "est", kind: "geo", name: pfx + "Pastillas: engrane del tornillo en la base (taladro ciego, remanente 3 mm)", formula: "1,0·d ≤ l_e = L − (t_portador − 0,5) = " + nf(tp.engrane, 1) + " mm y l_e + 2 ≤ rosca útil = t_base − 3 − 2P = " + nf(tp.rosca_util, 1) + " mm (" + tp.designacion + ")", dem: P.bx_d_sp, cap: Math.min(tp.engrane, tp.rosca_util - 2), unit: "mm", ref: "VDI 2230-1:2015 (orientativo, 8.8 en S355; criterio del núcleo para la placa-guía)" });
    add({ sys: "est", kind: "info", name: pfx + "Pastillas: geometría y cantidad", formula: g.nP + " pastillas Ø" + g.d + " (torneado Ø" + nf(g.d + g.delta, 2) + ") × " + nf(g.H, 1) + " (saliente " + nf(g.hp, 1) + "), patrón " + (g.pat === 2 ? "radial" : "triangular") + " a paso " + g.s + " mm, " + g.nW + " tapones", dem: g.nP, cap: g.d, unit: "– / mm", ref: REG });
    if (!L.SH.sq) add({ sys: "est", kind: "geo", name: pfx + "Pastillas: Ø de corte dentro del límite del mandante (se cortan de cuadrados de " + P.bx_cuad_uh + " × " + P.bx_cuad_uh + " de ULTRA VST)", formula: "d + δ ≤ Ø_máx = " + P.bx_dp_max + " mm y ≤ lado − 2·2,5 (router); d + δ = " + nf(g.d + g.delta, 2) + " mm", dem: g.d + g.delta, cap: Math.min(P.bx_dp_max, P.bx_cuad_uh - 5), unit: "mm", ref: "Decisión del mandante 18-11-2026; criterio de taller" });
    /* --- Portador --- */
    if (g.nw >= 1) {   // variante con agujeros de soldadura (regla de un salto)
      add({ sys: "est", name: pfx + "Portador: ligamento entre agujeros al corte (flujo del arrastre hacia el agujero de soldadura o el borde)", formula: "τ = F_lig/((s − d)·t) ≤ Fy/(Nd·√3); F_lig = mayor flujo por un ligamento en el árbol de saltos (máx. " + fl.hMax + " salto(s)); F = μ_ef·p_i·A_p, μ_ef = máx(μ_máx; T_calado/(N·r_u)) = " + nf(C.muEff, 3) + " (criterio de los topes de acero del núcleo)", dem: fl.Flig / ((g.s - g.d) * g.tc), cap: FvC, unit: "MPa", ref: "ASME BTH-1-2020 §3-2.3.6 (corte); equilibrio" });
      add({ sys: "est", name: pfx + "Portador: filete interior z" + P.bx_w_h + " de los agujeros de soldadura (grupo de pastillas que entrega a cada uno)", formula: "ΣF_grupo ≤ 0,60FEXX/(1,20Nd)·0,707w·π(Ø − w); F = μ_ef·p_i·A_p con μ_ef = " + nf(C.muEff, 3) + " (par de calado)", dem: fl.plugMax / 1e3, cap: g.capWh / 1e3, unit: "kN", ref: "AISC 360-22 §J2.2 (filetes en agujeros), §J2.4; ASME BTH-1-2020 §3-3.4" });
      add({ sys: "est", kind: "geo", name: pfx + "Portador: filete interior de los agujeros: mínimo por la parte más gruesa y máximo en el borde del portador", formula: "w_mín(T = " + Math.max(P.t_base, g.tc) + ") ≤ w ≤ t − 2", dem: Math.max(wMinAWS(Math.max(P.t_base, g.tc)) / P.bx_w_h, P.bx_w_h / wMaxJ(g.tc)), cap: 1, fu: Math.max(wMinAWS(Math.max(P.t_base, g.tc)) / P.bx_w_h, P.bx_w_h / wMaxJ(g.tc)), unit: "–", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7; AISC 360-22 §J2.2b" });
      add({ sys: "est", name: pfx + "Portador: filete perimetral con el arrastre de las pastillas del borde (" + fl.nEdge + ")", formula: "F_borde ≤ Fw·0,707·w·s (largo tributario = paso)", dem: fl.edgeMax / 1e3, cap: 0.707 * P.bx_w_c * g.s * Fw / 1e3, unit: "kN", ref: "AISC 360-22 §J2.4; ASME BTH-1-2020 §3-3.4" });
      const Tcap = (L.welds.reduce((s, w) => s + g.capWh * w.r, 0) + Fw * 0.707 * P.bx_w_c * 2 * Math.PI * (C.Rco ** 2 + C.Rci ** 2)) / 1e6;
      add({ sys: "est", name: pfx + "Portador: transferencia del par a la base (agujeros de soldadura + filetes perimetrales)", formula: "T_calado ≤ ΣR_agujero·r + Fw·0,707w·2π(R_ext² + R_int²) (suma plástica, cada soldadura a su resistencia)", dem: C.Tcal, cap: Tcap, unit: "kN·m", ref: "AISC 360-22 §J2.4; ASME BTH-1-2020 §3-3.4; equilibrio" });
      add({ sys: "est", kind: "geo", name: pfx + "Portador: todas las pastillas tienen camino a un agujero de soldadura o al borde", formula: "pastillas sin camino = 0", dem: fl.unreached, cap: 0, fu: fl.unreached ? Infinity : 0, unit: "–", ref: "Geometría" });
    } else {           // transferencia perimetral (por defecto): sin soldaduras interiores
      const tq = g.tq, Fl = C.muEff * L.pMax * L.Ap;
      add({ sys: "est", name: pfx + "Portador: ligamento junto a la pastilla más cargada al corte (entrada del arrastre)", formula: "τ = F/(lig·t) ≤ Fy/(Nd·√3); F = μ_ef·p·A_p, μ_ef = máx(μ_máx; T_calado/(N·r_u)) = " + nf(C.muEff, 3) + " (criterio de los topes de acero del núcleo)", dem: Fl / (g.lig * g.tc), cap: FvC, unit: "MPa", ref: "ASME BTH-1-2020 §3-2.3.6 (corte); equilibrio" });
      add({ sys: "est", name: pfx + "Portador: corte por torsión en la sección neta crítica (círculo r = " + nf(tq.rCrit, 0) + " mm, acero η = " + nf(tq.etaCrit, 3) + ")", formula: "τ = T_cruza(r)/(2π·r²·t·η(r)) ≤ Fy/(Nd·√3); η(r) = 1 − Σ cuerdas de los agujeros/(2πr); reparto del par entre los bordes según C = ∫dr/(r³η) (la pastilla en ρ manda al borde exterior C_int(ρ)/C_total)", dem: tq.tauMax, cap: FvC, unit: "MPa", ref: "ASME BTH-1-2020 §3-2.3.6; torsión de una corona (Timoshenko, Strength of Materials); equilibrio" });
      add({ sys: "est", name: pfx + "Portador: filete perimetral exterior z" + P.bx_w_c + " con el par que llega al borde exterior", formula: "f = T_ext/(2π·R_ext²)/(0,707·w) ≤ 0,60FEXX/(1,20Nd); T_ext = " + nf(tq.Tout / 1e6, 1) + " kN·m de " + nf(tq.Ttot / 1e6, 1), dem: tq.Tout / (2 * Math.PI * C.Rco ** 2) / (0.707 * P.bx_w_c), cap: Fw, unit: "MPa", ref: "AISC 360-22 §J2.4; ASME BTH-1-2020 §3-3.4" });
      add({ sys: "est", name: pfx + "Portador: filete perimetral interior z" + P.bx_w_c + " con el par que llega al borde interior", formula: "f = T_int/(2π·R_int²)/(0,707·w) ≤ 0,60FEXX/(1,20Nd); T_int = " + nf(tq.Tin / 1e6, 1) + " kN·m", dem: tq.Tin / (2 * Math.PI * C.Rci ** 2) / (0.707 * P.bx_w_c), cap: Fw, unit: "MPa", ref: "AISC 360-22 §J2.4; ASME BTH-1-2020 §3-3.4" });
      if (L.SH.sq) {   // esquinas de los agujeros cuadrados: concentración solo en fatiga (resistencia estática dúctil sin Kt)
        const Nc = P.turns_yr * P.life * P.N_pin, Kt = 1 + 2 * Math.sqrt((g.d / 2) / L.SH.rc), FSRb = TT_.FSR("B", Nc);
        add({ sys: "est", name: pfx + "Portador: esquinas de los agujeros cuadrados (r = " + nf(L.SH.rc, 1) + " mm): rango de tensión con concentración frente a la categoría B", formula: "Δσ = K_t·τ_neta ≤ F_SR(B, N); K_t = 1 + 2√((a/2)/r) (agujero alargado de Inglis, cota alta) = " + nf(Kt, 2) + "; N = vueltas/año·vida·N_pas = " + Math.round(Nc) + " empujes (estático: material dúctil, sin K_t)", dem: Kt * tq.tauMax, cap: FSRb, unit: "MPa", ref: "AISC 360-22 Apéndice 3, Tabla A-3.1 (sección 1.2: borde cortado térmicamente, categoría B); Inglis (1913)" });
      }
      add({ sys: "est", kind: "info", name: pfx + "Portador: pandeo por corte de la plancha entre bordes soldados (referencia)", formula: "τ_cr = 5,35·π²E/(12(1 − ν²))·(t/b)², b = R_ext − R_int (sin agujeros: solo orden de magnitud)", dem: tq.tauMax, cap: 5.35 * Math.PI ** 2 * P.E / (12 * (1 - P.nu ** 2)) * (g.tc / (C.Rco - C.Rci)) ** 2, unit: "MPa", ref: "Timoshenko y Gere, Theory of Elastic Stability §9 (placa larga en corte)" });
    }
    add({ sys: "est", kind: "geo", name: pfx + "Portador: ligamento mínimo para el corte por plasma", formula: "máx(10; t) ≤ s − d", dem: Math.max(10, g.tc), cap: g.s - g.d, unit: "mm", ref: "Criterio de taller (corte térmico de agujeros contiguos; por confirmar con el taller)" });
    add({ sys: "est", kind: "geo", name: pfx + "Portador: filete perimetral mínimo (parte más gruesa = base de " + P.t_base + " mm)", formula: "w_mín(T) ≤ w", dem: wMinAWS(Math.max(P.t_base, g.tc)), cap: P.bx_w_c, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7" });
    add({ sys: "est", kind: "geo", name: pfx + "Portador: filete perimetral máximo en el borde del portador", formula: "w ≤ t − 2 (t ≥ 6)", dem: P.bx_w_c, cap: wMaxJ(g.tc), unit: "mm", ref: "AISC 360-22 §J2.2b" });
    add({ sys: "est", kind: "geo", name: pfx + "Portador: libra el filete del collar del pivote", formula: "D_collar/2 + w_collar + 2 ≤ R_int,portador", dem: P.h_boss > 0 ? P.D_boss / 2 + P.w_collar + 2 : 0, cap: C.Rci, unit: "mm", ref: "Geometría" });
    /* --- Disco inoxidable --- */
    if (g.LAM) lamRows(P, C, M, L, g, ce, add, D, th);
    else {
    add({ sys: "est", kind: "geo", name: pfx + "Disco: espesor frente a la cabeza avellanada M" + g.dT + " más el sobreespesor de desgaste", formula: "k + 0,5 + sobreespesor ≤ t; k = " + nf(g.kT, 2) + " mm (ISO 10642)", dem: g.tHead, cap: g.tss, unit: "mm", ref: "ISO 10642; criterio del mandante (cabeza ≤ espesor − 0,5 mm también tras el relapeado)" });
    add({ sys: "est", name: pfx + "Disco: flexión de la celda entre pastillas (" + M.nombre + ")", formula: "σ = 6·M_máx/t_e² ≤ 0,6·Fy; M de la placa anular a = d/2 (empotrada) … b = √(A_celda/π) = " + nf(ce.b, 1) + " mm (guiada), A_celda = s²·√3/2·7/6, con q_máx; t_e = t − sobreespesor", dem: ce.sig, cap: sad, unit: "MPa", ref: REFC });
    add({ sys: "est", kind: "geo", name: pfx + "Disco: flecha de la celda entre pastillas", formula: "w ≤ mín(d_flat; 0,1·h_p) (no suma sobrepresión ni consume la holgura)", dem: ce.w, cap: Math.min(P.d_flat, 0.1 * g.hp), unit: "mm", ref: REFC + "; criterio del proyecto" });
    add({ sys: "est", name: pfx + "Disco: flexión sobre el vacío local sin contacto con el respaldo (Ø" + P.ss_void + ", disco solo, como el núcleo)", formula: "σ = 3·q·a²/(4·t_e²) ≤ 0,6·Fy; a = Ø_vacío/2 = " + nf(g.DT.aV, 1) + " mm", dem: 0.75 * C.qmax * (g.DT.aV / te) ** 2, cap: sad, unit: "MPa", ref: REFD });
    add({ sys: "est", name: pfx + "Disco: flexión sobre la pastilla faltante o el mayor hueco de la malla (disco y plancha de la mesa se curvan juntos)", formula: "σ = 6·(q·a_g²/8)·D_disco/(D_disco + D_mesa)/t_e² ≤ 0,6·Fy; a_g = máx(s − d/2; √(A_trib,máx/π)) = " + nf(g.DT.aG, 1) + " mm; fracción del disco " + nf(g.DT.gap.sh, 3) + " (D_mesa con t_inf = " + P.t_bot + " mm)", dem: g.DT.gap.sig, cap: sad, unit: "MPa", ref: REFD + "; placas apiladas en contacto con la misma curvatura (reparto por rigidez)" });
    add({ sys: "est", kind: "geo", name: pfx + "Disco: espesor adoptado frente al requerido", formula: "t ≥ máx(k + 0,5 + sobreespesor; t_vacío + sobreespesor; t_mín) y la celda cumple; espesores comerciales ASTM A240", dem: g.tReq, cap: g.tss, unit: "mm", ref: "ASTM A240 (plancha inoxidable)" });
    const dAl = Math.abs(M.al - P.bx_al_st * 1e-6), sTh1 = M.E * dAl * BF.dTd, sTh = sTh1 / (1 - M.nu);   // uniaxial (E·Δα·ΔT) y biaxial con restricción total (÷(1 − ν), conservador)
    const sCr = 2 * Math.PI ** 2 * M.E / (12 * (1 - M.nu ** 2)) * (te / g.sb) ** 2;   // panel cuadrado s×s simplemente apoyado en compresión biaxial igual: k = 2
    add({ sys: "est", name: pfx + "Disco: CJP a tope entre semidiscos (metal base) con la mayor tensión de membrana o de flexión", formula: "máx(σ_térmica restringida = E·Δα·ΔT/(1 − ν); σ_celda) ≤ 0,6·Fy (conservador: la térmica es secundaria); ΔT = " + nf(BF.dTd, 0) + " K", dem: Math.max(sTh, ce.sig), cap: sad, unit: "MPa", ref: "AWS D1.6/D1.6M:2017 (CJP con aporte compatible = metal base); AISC 360-22 Tabla J2.5 (CJP)" });
    add({ sys: "est", name: pfx + "Disco: tensión térmica de membrana (secundaria, autolimitante) como rango frente a 2·Fy (adaptación)", formula: "Δσ = E·Δα·ΔT/(1 − ν) ≤ S_PS = 2·Fy; Δα = " + nf(dAl * 1e6, 1) + "×10⁻⁶/K, ΔT = " + nf(BF.dTd, 0) + " K (E·Δα·ΔT uniaxial = " + nf(sTh1, 1) + " MPa)", dem: sTh, cap: 2 * M.Fy, unit: "MPa", ref: "ASME BPVC VIII-2 (2023) 5.5.6.1 (rango primario + secundario ≤ S_PS = máx(3S; 2Sy)); " + M.fuente });
    add({ sys: "est", name: pfx + "Disco: tensión térmica de membrana frente a Fy (conservador: sin plastificación)", formula: "σ = E·Δα·ΔT/(1 − ν) ≤ Fy", dem: sTh, cap: M.Fy, unit: "MPa", ref: "Termoelasticidad; criterio del revisor" });
    add({ sys: "est", name: pfx + "Disco: pandeo por la compresión térmica entre tornillos (panel s × s)", formula: "σ ≤ σ_cr = k·π²E/(12(1 − ν²))·(t_e/s)², k = 2 (compresión biaxial igual, bordes simplemente apoyados en los tornillos), s = " + g.sb + " mm", dem: sTh, cap: sCr, unit: "MPa", ref: "Timoshenko y Gere, Theory of Elastic Stability §9.5 (placa cuadrada en compresión biaxial)" });
    add({ sys: "est", kind: "info", name: pfx + "Disco: masa (dos semidiscos de " + nf(g.mSS / 2, 0) + " kg: manipulación con medios mecánicos, no manual)", formula: "m = ρ·π(R_o² − R_i²)·t", dem: g.mSS, cap: g.mSS / 2, unit: "kg / kg por semidisco", ref: "ISO 11228-1 (carga manual ≤ 25 kg: no aplica)" });
    /* --- Tornillos disco–mesa --- */
    const w = BF.worst;
    add({ sys: "est", name: pfx + "Tornillos del disco (" + BL.lista.length + " × M" + g.dT + " 10.9): corte de diseño por el par de giro (arrastre)", formula: "V_T = T_calado·r/Σr² ≤ Fnv·A_b/Ω; Fnv = 0,45·Fu (rosca en el plano), Ω = 2,00; T_calado = " + nf(C.Tcal, 1) + " kN·m (el par por la interfaz no supera el de calado)", dem: BF.V_prim / 1e3, cap: BF.capV / 1e3, unit: "kN", ref: "AISC 360-22 §J3.7, Tabla J3.2 (grupo 150 ≈ 10.9)" });
    add({ sys: "est", kind: "info", name: pfx + "Tornillos del disco: componente térmica secundaria (" + nf(BF.dTd, 0) + " K) por anillo según su rigidez y combinación informativa con el par", formula: "franja de ancho = paso del anillo exterior, nudos en los anillos (centro fijo, borde libre), resortes de Huth; V_th,anillos (kN) = " + BF.th_out.porAnillo.map((x) => nf(x / 1e3, 2)).join(" / ") + "; √(V_T² + V_th²) = " + nf(BF.V_comb / 1e3, 2) + " kN frente a " + nf(BF.capV / 1e3, 2) + " (no se suma como carga de resistencia: el disco acomoda con la holgura y el aplastamiento local del agujero)", dem: BF.Fth_out / 1e3, cap: BF.V_comb / 1e3, unit: "kN / kN", ref: "AISC 360-22 §J3.10 (deformación del agujero admitida); Huth (1986, ASTM STP 927)" });
    add({ sys: "est", name: pfx + "Tornillos del disco: aplastamiento y desgarro hacia el borde exterior en el disco (avellanado)", formula: "V_T ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 = " + nf(BF.te, 2) + " mm, l_c = (R_o − r) − d_h/2 = " + nf(BF.lcEdge, 1) + " mm", dem: BF.V_prim / 1e3, cap: BF.RnSS_edge / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a, J3-6c); EN 1993-1-8 Tabla 3.4 (avellanado)" });
    const tbW = w.anillo ? P.t_pr : P.t_bot, leW = Math.min(D.disco.tornillos.lista.reduce((m, b) => Math.min(m, isFinite(b.le) ? b.le : 0), Infinity), tbW);
    add({ sys: "est", name: pfx + "Tornillos del disco: aplastamiento en la pieza roscada de la mesa", formula: "V_T ≤ R_n/Ω, R_n = 2,4·d·l_e·Fu; l_e = mín. engrane = " + nf(leW, 1) + " mm", dem: BF.V_prim / 1e3, cap: 2.4 * g.dT * leW * Math.min(P.Fu, P.Fu_pr > 0 ? P.Fu_pr : P.Fu) / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Fu: la menor entre el anillo inferior y la plancha inferior)" });
    add({ sys: "est", kind: "geo", name: pfx + "Tornillos del disco: engrane en la plancha inferior (pasante) o en el anillo inferior (ciego, remanente 3 mm)", formula: "1,25·d ≤ l_e (mínimo de todas las posiciones)", dem: 1.25 * g.dT, cap: leW, unit: "mm", ref: "VDI 2230-1:2015 (orientativo, 10.9 en S355; criterio del registro AF2)" });
    add({ sys: "est", kind: "geo", name: pfx + "Tornillos del disco: separación entre centros", formula: "3·d ≤ s_mín", dem: 3 * g.dT, cap: BL.sMin, unit: "mm", ref: "AISC 360-22 §J3.4" });
    add({ sys: "est", kind: "geo", name: pfx + "Tornillos del disco: distancia al borde exterior e interior del disco", formula: "e_mín (Tabla J3.4M) ≤ mín(R_o − r_ext; r_int − R_i)", dem: J34M(g.dT), cap: Math.min(C.Ro - BL.radii[BL.radii.length - 1], BL.radii[0] - C.Ri), unit: "mm", ref: "AISC 360-22 §J3.5, Tabla J3.4M (M16 para menores, como el núcleo)" });
    add({ sys: "est", kind: "info", name: pfx + "Tornillos del disco: posiciones libres de la CJP, de almas, nervios y cubo (pie del filete) y de los agujeros de los pasadores", formula: "|y| ≥ c_CJP = " + P.bx_c_cjp + " mm; distancia al alma/nervio ≥ t/2 + w + d/2 + " + P.bx_c_alma + "; distancia al pasador ≥ d_pas/2 + d/2 + 3 + d", dem: BL.lista.length, cap: BL.radii.length, unit: "tornillos / anillos", ref: "Geometría; AISC 360-22 §J3.4" });
    add({ sys: "est", name: pfx + "Tornillos del disco: tracción al izar la mesa con el disco colgado (despegue)", formula: "T = φ_izaje·m_disco·g/n ≤ Fnt·A_b/Ω; Fnt = 0,75·Fu, Ω = 2,00", dem: BF.Tup / 1e3, cap: BF.capT / 1e3, unit: "kN", ref: "AISC 360-22 §J3.6, Tabla J3.2" });
    }
    /* --- Mesa de plancha entera por nivel (rev. 7c, decisión del mandante 19-11-2026) --- */
    if (meOn(P)) {
      const ts = [P.t_pr, P.t_top, P.t_bot], REFM = "Decisión del mandante 19-11-2026 (rev. 7c); docs/bx/README_BX.md §12";
      add({ sys: "est", kind: "geo", name: pfx + "Mesa de plancha entera: un solo espesor por nivel (t_pr = t_top = t_bot)", formula: "máx(t_pr, t_top, t_bot)/mín(t_pr, t_top, t_bot) ≤ 1; t_pr = " + P.t_pr + ", t_top = " + P.t_top + ", t_bot = " + P.t_bot + " mm (con espesores distintos use bx_mesa_entera = 0: disco + anillo)", dem: Math.max(...ts) / Math.min(...ts), cap: 1, unit: "–", ref: REFM });
      add({ sys: "est", kind: "info", name: pfx + "Mesa de plancha entera: uniones soldadas plancha–anillo (superior e inferior) y empalmes CJP de los 4 segmentos de 90° de cada anillo de pasadores — no aplica", formula: "planchas Ø" + P.D_top + " × " + P.t_top + " de una pieza con los " + Math.round(P.N_pin) + " agujeros Ø" + P.d_pin + " H7: sin anillo de pasadores (las filas «anillo» del núcleo se refieren a la zona de los pasadores de la plancha, del mismo espesor)", dem: null, unit: "–", ref: REFM });
      if (!(P.opt_wood > 0.5) && R.m && R.hubG) {
        const Rt = P.D_top / 2, aH = Math.round(P.N_pin) * Math.PI / 4 * P.d_pin ** 2, hg = R.hubG, hole = P.D_piv + 80;
        const mE = RHO * (P.t_top * (Math.PI * Rt * Rt - Math.PI / 4 * hole ** 2 - aH) + P.t_bot * (Math.PI * Rt * Rt - Math.PI / 4 * hg.d_bush ** 2 - aH) - Math.PI / 4 * (hg.Drb ** 2 - hg.d_bush ** 2) * hg.hPl);
        add({ sys: "est", kind: "info", name: pfx + "Mesa de plancha entera: masa de las planchas superior e inferior = disco completo Ø" + P.D_top + " (sin doble conteo en el traslape R" + nf(TT_.prIn(P), 0) + "…R" + nf(Rt, 0) + ")", formula: "núcleo (disco Ø 2·R_anillo,int + corona R_anillo,int…R) = ρ·[t_top·(πR² − π·Ø_agujero²/4 − N·π·d²/4) + t_bot·(πR² − π·Ø_buje²/4 − N·π·d²/4) − rebaje del collar]; " + nf(R.m.top + R.m.bot, 1) + " kg frente a " + nf(mE, 1) + " kg", dem: R.m.top + R.m.bot, cap: mE, unit: "kg / kg", ref: "Geometría; " + REFM });
      }
    }
    /* --- Generales --- */
    add({ sys: "est", kind: "info", name: pfx + "Altura que agrega la interfaz sobre la plancha base", formula: "Δ = t_portador + h_p + t_disco = " + g.tc + " + " + nf(g.hp, 1) + " + " + g.tss, dem: g.tc + g.hp + g.tss, unit: "mm", ref: "Geometría (el eje de los cilindros sube Δ)" });
    add({ sys: "est", kind: "info", name: pfx + "Masa agregada por la interfaz (disco + pastillas + portador)", formula: "m = m_disco + m_pastillas + m_portador", dem: g.mSS + S.bx.mUH + S.bx.mCar, cap: g.mSS, unit: "kg / kg disco", ref: "Geometría" });
    if (g.LAM) add({ sys: "est", kind: "pend", name: pfx + "Corrosión galvánica: lámina inoxidable soldada a la mesa de acero al carbono", formula: "Sin verificación numérica. La costura perimetral continua exterior e interior sella el intersticio lámina–plancha (sin electrolito entre ambas); la zona de dilución del E309L queda bajo la costura. Propuesta: imprimación epóxica en el canto de la plancha de la mesa junto a la costura y pasivado local del inox (ASTM A380/A967) después de esmerilar", dem: 0, unit: "–", ref: "ISO 9223; AWS D1.6/D1.6M:2017 (unión disímil); decisión del proyectista" });
    else add({ sys: "est", kind: "pend", name: pfx + "Corrosión galvánica: disco inoxidable contra la mesa de acero al carbono y tornillos en roscas de acero al carbono", formula: "Sin verificación numérica. Propuesta: tornillos de acero 10.9/8.8 con zinc laminar (no A4) en roscas de la mesa y de la base; imprimación epóxica en la cara de la mesa bajo el disco y sellante perimetral (el inox actúa de cátodo de gran área: el ataque va al acero de la mesa, que queda protegido por la imprimación)", dem: 0, unit: "–", ref: "ISO 9223; ISO 10683; decisión del proyectista" });
    add({ sys: "est", kind: "pend", name: pfx + "Arranque adherencia–deslizamiento de UHMW sobre inoxidable tras reposo bajo carga (μ estático de diseño de la opción B)", formula: "Sin verificación numérica; ensayo de arranque de una pastilla con p = " + nf(L.pMax, 2) + " MPa", dem: 0, unit: "–", ref: "Ensayo del proveedor (como la opción B del núcleo)" });
    return out;
  }
  // estado como el núcleo (verifs)
  function stOf(P, c) {
    if (c.kind === "info") c.st = "info";
    else if (c.kind === "pend") c.st = "pend";
    else if (!isFinite(c.fu)) c.st = "fail";
    else if (c.kind === "geo" || c.sys === "giro") c.st = c.fu <= 1 ? "ok" : "fail";
    else c.st = c.fu <= 0.9 ? "ok" : c.fu <= 1 ? "warn" : "fail";
    if (P.__th && P.__th.alc !== 2 && c.grp !== "Temperatura" && ACC_GRPS.includes(c.grp)) c.fuera = true;
    return c;
  }
  function verdictOf(checks, R, base) {
    const bad = (sys) => checks.filter((c) => c.sys === sys && c.st === "fail" && !c.fuera), warn = (sys) => checks.filter((c) => c.sys === sys && c.st === "warn" && !c.fuera);
    const pendCrit = checks.filter((c) => c.st === "pend" && c.kind !== "info" && c.fu != null && !(isFinite(c.fu) && c.fu <= 1))
      .map((c) => Object.assign({ grp: c.grp, nombre: c.name, fu: c.fu, sys: c.sys, ref: c.ref }, c.fuera ? { fuera_alcance_termico: true } : {})).sort((a, b) => (isFinite(b.fu) ? b.fu : 1e99) - (isFinite(a.fu) ? a.fu : 1e99));
    const v = { gira: R.K.ok && bad("giro").length === 0, estructura: bad("est").length === 0, warnGiro: warn("giro").length, warnEst: warn("est").length, pend: checks.filter((c) => c.st === "pend").length,
      fuMax: Math.max(0, ...checks.filter((c) => c.fu != null && isFinite(c.fu) && c.kind === "fu" && !c.fuera).map((c) => c.fu)), pendientes_criticos: pendCrit, fuMaxPend: pendCrit.length ? pendCrit[0].fu : 0,
      limitaciones_uso: (base.limitaciones_uso || []).concat(checks.filter((c) => c.limitacion).map((c) => ({ id: "BX-T-SELLO", caso: c.name.replace(/^BX · LIMITACIÓN DE USO: /, ""), condicion: c.formula, referencia: c.ref, informativa: true }))) };
    v.estado_global = !(v.gira && v.estructura) ? "NO CUMPLE" : pendCrit.length ? "NO CUMPLE / PENDIENTE DE DECISIÓN" : "CUMPLE";
    return v;
  }

  /* ---------------- Plancha base bajo el soporte del ojal E con t_base > 20: crédito del espesor (FEA de Mindlin) ---------------- */
  // El núcleo calibra S = σ/M del refuerzo con t_base = 20 y no acredita una base más gruesa (k_Tb = máx(1; (20/t_b)²)). Rev. 5: con A36 la base pasa a 25 mm;
  // la FEA de Mindlin de la base completa de tests/indep_plancha_base_E.py §4 (mesa cargada con contacto unilateral, losa unilateral, soportes rígidos,
  // malla 40 mm, σ_vM a > 100 mm de la huella) sobre el diseño BX (modo pivotado, h = 138 mm, refuerzo y atiesador del núcleo) da, respecto de t_base = 20:
  //   empuje (nom/dis/cal): FU_FEA 0,193/0,611/0,860 → 22 mm: 0,174/0,548/0,771 → 25 mm: 0,172/0,520/0,728 (el núcleo daba 0,823 a calado con 20: la FEA es
  //   4,5 % mayor, se aplica ese factor); atasco del retorno: 1,002 → 0,848 → 0,677 (núcleo 1,055). Factor sobre la fila del núcleo, interpolado en t_base
  //   (≥ 25: el de 25); mesa vacía sin crédito. Solo modo pivotado (la calibración no cubre el guiado).
  // Rev. 6 (base de 22 mm de A572 Gr. 50, refuerzo automático de 65 mm de A36, paredes E de 25): la misma FEA sobre el JSON de diseño rev. 6 da, con
  // Fy = 250 (la menor de las piezas): nom/dis/cal 0,174/0,548/0,771 frente al núcleo 0,195/0,575/0,799 (cociente máx. 0,965 > 0,937 de la rev. 5: se
  // adopta 0,965 para no quedar del lado inseguro) y atasco del retorno 0,848 frente a 1,052 (0,806 < 0,846: se conserva 0,846, conservador). El pico del
  // retorno cae en la base sola (t = 22, A572: con Fy 345 FU 0,614) y el del calado en la franja del atiesador (t_eq = 72, A36): las filas usan la menor Fy.
  // Rev. 7 (todo A572 Gr. 50, base 22, refuerzo automático de 45 mm, paredes E de 22 y atiesador 22 × 60): con la malla de 40 mm de la calibración el
  // sistema es singular (las paredes de 22 mm no toman una fila completa de nodos de la máscara rígida del soporte), y con 20/25/30/35 mm la FEA no converge
  // en malla: calado 0,865/0,900/0,962/0,816 y retorno 0,824/0,654/0,666/0,471 frente al núcleo 0,831 y 0,785 (Fy 345). La rev. 6 tampoco: con 20/30/35 mm
  // el calado daba 1,326/1,094/0,811 (con 40: 0,771). Criterio conservador: con t_base ≥ 22 se toma la ENVOLVENTE de las mallas de la rev. 7 como factor
  // sobre la fila del núcleo (empuje 0,962/0,831 = 1,158; retorno 0,824/0,785 = 1,050: penalización, no crédito); entre 20 y 22 se interpola; sin
  // crédito por encima de 22 (la calibración de 25 mm de la rev. 5 era solo con malla de 40). El factor vale para la geometría por defecto de la rev. 7.
  const BASE_FEA = { tb: [20, 22], emp: [1.045, 0.962 / 0.831], ret: [1.0, 0.824 / 0.785] };
  function baseCredit(P, checks) {
    const out = [], tb = P.t_base;
    if (!(tb > 20 + 1e-9) || TT_.driveMode(P) !== 2) return out;
    const T = BASE_FEA.tb, k = (arr) => { const x = Math.min(tb, T[T.length - 1]); let i = 1; while (i < T.length - 1 && T[i] < x) i++; return arr[i - 1] + (arr[i] - arr[i - 1]) * (x - T[i - 1]) / (T[i] - T[i - 1]); };
    const re = /^Plancha base bajo el soporte del ojal E: base de .* flexión de la base y del refuerzo con la (.*)$/;
    checks.forEach((c) => {
      const m = re.exec(c.name); if (!m || c.kind !== "fu" || c.bx) return;
      const id = /atasco del retorno/.test(m[1]) ? "ret" : /vac[ií]a/.test(m[1]) ? null : "emp"; if (!id) return;
      const f = k(BASE_FEA[id]); if (!(Math.abs(f - 1) > 1e-9)) return;
      out.push({ after: c, row: { kind: "fu", grp: c.grp, sys: c.sys, bx: true, k_tb: f, name: "BX · " + c.name + " — " + (f < 1 ? "crédito" : "ajuste") + " por la FEA de Mindlin de la base (t_base = " + tb + " mm)",
        formula: c.formula + "; × k = " + nf(f, 3) + " (FEA de Mindlin de la base completa con t_base = " + tb + ": " + (id === "ret" ? "atasco del retorno" : "empuje") + ", envolvente de las mallas de 20 a 35 mm sobre el diseño rev. 7 frente al núcleo); Fy = la menor entre la base y el refuerzo o el atiesador (" + nf(c.cap * P.Nd / 1.25, 0) + " MPa)",
        dem: c.dem * f, cap: c.cap, unit: c.unit, ref: (c.ref || "") + "; tests/indep_plancha_base_E.py §4 (FEA de Mindlin, misma formulación de la calibración del núcleo) sobre los diseños TT300-BX rev. 5 a 7; docs/bx/README_BX.md §9 a §11" } });
      c.kind = "info"; c.st = "info"; c.sustituida = true; c.name = c.name + " [sustituida en TT300-BX por la fila con el factor de la FEA de la base]";
    });
    return out;
  }

  /* ---------------- Anillos de pasadores de distinto espesor (rev. 6) ---------------- */
  // El núcleo verifica el pasador de empuje con un solo espesor de anillo t = máx(t_pr, t_top, t_bot) (anillos iguales). Con t_pr menor que la plancha
  // superior (rev. 6: t_pr = 22 < t_top = 25) el anillo superior queda de máx(t_pr, t_top) = 25 (una pieza con la plancha en la zona del anillo, como la
  // masa del núcleo) y el inferior de máx(t_pr, t_bot) = 22: la reacción V = F_r·(1/2 + e/L) puede caer en cualquiera de los dos (e accidental en ambos
  // sentidos), de modo que el aplastamiento y el bisel de la soldadura se verifican también con el anillo más delgado, y la flexión del pasador con la luz
  // entre los planos medios de los anillos L = h − (t_sup + t_inf)/2. Filas BX agregadas después de las del núcleo (que quedan).
  function ringRows(P, R, checks) {
    const out = [], tS = Math.max(P.t_pr, P.t_top), tI = Math.max(P.t_pr, P.t_bot), tN = Math.max(P.t_pr, P.t_top, P.t_bot), tMin = Math.min(tS, tI);
    if (!(tMin < tN - 1e-9) || !R.Fstall) return out;
    const Nd = P.Nd, Fpr = R.Fstall * Math.hypot(1, P.mu_s), FyR = P.Fy_pr > 0 ? P.Fy_pr : P.Fy;
    const L1 = P.h_disc - (tS + tI) / 2, Vp = Fpr * (0.5 + P.e_dog / L1), c = Math.min(P.dog_h, L1), M = Fpr / 4 * (L1 - c / 2) / 1e3, Sp = Math.PI * P.d_pin ** 3 / 32;
    const at = (re) => checks.find((q) => q.grp === "Pasadores de empuje" && re.test(q.name));
    const cB = at(/^Aplastamiento en el agujero del anillo$/), cF = at(/^Flexión \(biapoyado/), cW = at(/bisel dentro del anillo/), cS = at(/^Soldadura pasador–anillo \(PJP/);
    const lb = "anillo " + (tI < tS ? "inferior" : "superior") + " de " + tMin + " mm (sup. máx(t_pr, t_top) = " + tS + ", inf. máx(t_pr, t_bot) = " + tI + ")";
    const REGR = "Modelo del pasador biapoyado del núcleo con los dos espesores de anillo; docs/bx/README_BX.md §10";
    if (cB) out.push({ after: cB, row: { kind: "fu", grp: cB.grp, sys: "est", bx: true, name: "BX · Aplastamiento en el agujero del " + lb, formula: "σ = V/(d·t) ≤ 1,25·Fy_pr/Nd; V = F_r·(1/2 + e/L) = " + nf(Vp, 1) + " kN con L = h − (t_sup + t_inf)/2 = " + nf(L1, 1) + " mm, t = " + tMin + " mm, Fy_pr = " + FyR + " MPa",
      dem: Vp * 1e3 / (P.d_pin * tMin), cap: 1.25 * FyR / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento en pasadores); " + REGR } });
    if (cF) out.push({ after: cF, row: { kind: "fu", grp: cF.grp, sys: "est", bx: true, name: "BX · Pasador de empuje: flexión con la luz entre los planos medios de los anillos (" + tS + " / " + tI + " mm)", formula: "M = F_r·(L − c/2)/4, L = h − (t_sup + t_inf)/2 = " + nf(L1, 1) + " mm, c = h_uña; σ = M/S ≤ Fy_pin/Nd",
      dem: M * 1e6 / Sp, cap: P.Fy_pin / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3; " + REGR } });
    if (cW && cS) { const S = +(/S (\d+)/.exec(cS.name) || [0, 0])[1];
      out.push({ after: cW, row: { kind: "geo", grp: cW.grp, sys: "est", bx: true, name: "BX · Soldadura pasador–anillo: bisel dentro del " + lb + " (S ≤ t − 5)", formula: "S = " + S + " mm ≤ " + (tMin - 5) + " mm", dem: S, cap: tMin - 5, unit: "mm", ref: "Geometría; " + REGR } }); }
    return out;
  }

  /* ---------------- API (análoga a TT) ---------------- */
  function analyze(P, opts) {
    if (!active(P)) return Object.assign({}, TT_.analyze(P, opts), { bx: null });
    const Dg = design(P.__th ? Object.assign({}, P.__th.P0, { __th: undefined }) : P), Pc = Object.assign({}, full(P), { __bx: Dg.bx });
    const A = TT_.analyze(Pc, opts);
    const rows = bxRows(Pc, A.R, Dg).map((c) => stOf(Pc, c));
    const core = A.checks.map((c) => Object.assign({}, c)), cred = baseCredit(Pc, core).concat(ringRows(Pc, A.R, core));   // copias: el análisis del núcleo puede estar en memoria
    cred.forEach((o) => { const r = stOf(Pc, Object.assign({}, o.row, { fu: o.row.dem / o.row.cap })); core.splice(core.indexOf(o.after) + 1, 0, r); });
    if (cylOn(Pc)) core.forEach((c) => { if (c.grp === "Giro" && /^Vástago: flexocompresión/.test(c.name)) c.name = c.name.replace("DATO DEL PROVEEDOR", "dato confirmado por el mandante 19-11-2026"); });
    if (cylOn(Pc)) core.forEach((c) => { if (c.grp === "Giro" && /^Ojal comercial del vástago/.test(c.name)) { c.sustituida = true; c.name += " [sustituida en TT300-BX por las filas del grupo «Cilindro» (cilindro fabricado)]"; } });
    const cyl = cylRows(Pc, A.R).map((c) => stOf(Pc, c)), ig = core.reduce((k, c, i) => (c.grp === "Giro" ? i : k), -1);
    if (cyl.length) core.splice(ig + 1, 0, ...cyl);
    const idx = core.reduce((k, c, i) => (c.grp === "Interfaz" ? i : k), -1);
    const checks = core.slice(0, idx + 1).concat(rows, core.slice(idx + 1));
    const cyx = cylExport(Pc, A.R, checks);   // rev. 7d: cilindro fabricado (también en el bloque «bx» del JSON de diseño)
    return { P: full(P), Pc, R: A.R, fea: A.fea, checks, verdict: verdictOf(checks, A.R, A.verdict), bx: Object.assign(exportable(Dg), cyx ? { cilindro: cyx } : {}) };
  }
  const exportable = (Dg) => { const o = Object.assign({}, Dg); delete o._geo; delete o._e; delete o._ce; return o; };
  function compute(P) { return TT_.compute(coreP(P)); }
  function masses(P) { return compute(P).m; }
  function market(P) { return TT_.market(coreP(P)); }
  function capacityByCyl(P, ns) { return TT_.capacityByCyl(coreP(P), ns); }
  // Escenario térmico: TT.thermal sobre la alternativa B con la geometría BX congelada (gancho), más las filas BX evaluadas a cada T con las capacidades reducidas
  function thermal(P, opts) {
    if (!active(P)) return TT_.thermal(P, opts);
    opts = Object.assign({}, opts || {}, { alts: ["B"] });
    const Pf = full(P), Dg = design(Pf), xb = (b) => Object.assign({}, b, cylOn(Pf) && TT_.driveMode(Pf) === 2 ? { p_prueba_cil: Pf.bx_cyl_kt * Pf.p_relief } : {});   // rev. 7e: prueba del cilindro fabricado (fila térmica del aceite atrapado)
    const Pc = Object.assign({}, Pf, { __bx: xb(Dg.bx) }), r = TT_.thermal(Pc, opts);
    const Tref = Pf.T_ref, Tscn = r.T_scn, grad = r.gradiente_scn, gradAt = (T) => (Tscn > Tref ? grad * Math.max(0, T - Tref) / (Tscn - Tref) : 0);
    r.alternativas.forEach((alt) => {
      const Pa = Object.assign({}, Pc, { opt_ss: 0, opt_uhmw: 1, opt_bz: 0, bz_conf: 1, opt_wood: alt.madera ? 1 : 0 }); delete Pa.__th;
      const Da = alt.madera ? design(Object.assign({}, Pf, { opt_wood: 1 })) : Dg; Pa.__bx = xb(Da.bx);
      alt.nombre = "BX · " + (P.bx_disc_modo === 0 ? "Disco inoxidable atornillado" : "Lámina inoxidable soldada") + " + pastillas de UHMW en portador soldado" + (alt.madera ? " + cubierta de madera" : "");
      alt.byT.forEach((b) => {
        const Pt = TT_.thermalP(Pa, b.T, null, null, gradAt(b.T)), Rt = TT_.compute(Pt), rows = bxRows(Pt, Rt, Da).map((c) => stOf(Pt, c));
        const est = rows.filter((c) => c.kind === "fu" && c.sys === "est" && isFinite(c.fu)), gov = est.reduce((m, c) => (!m || c.fu > m.fu ? c : m), null);
        b.bx = { filas: rows.map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })), fuEst: gov ? gov.fu : 0, gobernante: gov ? { grp: gov.grp, nombre: gov.name, fu: gov.fu } : null,
          estructura: !rows.some((c) => c.st === "fail"), nFail: rows.filter((c) => c.st === "fail").length, nWarn: rows.filter((c) => c.st === "warn").length };
        b.estructura_bx = b.estructura && b.bx.estructura;
      });
    });
    r.modulo = "TT300-BX"; r.avisos = r.avisos.concat(["TT300-BX: filas propias en byT[].bx (presión, PV, ajuste y tornillos con capacidades reducidas a T); la geometría BX es la de 20 °C (congelada)"]);
    return r;
  }
  // Bloque «bx» del JSON de diseño (tools/export_design_bx.js)
  function exportBX(P, A) {
    const Dg = design(P); if (!Dg) return null;
    const o = exportable(Dg);
    o.verificaciones = (A ? A.checks.filter((c) => c.bx && c.grp !== CYL_GRP) : []).map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref }));
    if (meOn(full(P)) && !meOk(P)) throw new Error(meMsg(P));
    o.mesa = mesaOf(full(P), A && A.R);
    o.cilindro = cylExport(full(P), A && A.R, A && A.checks);   // rev. 7d: cilindro fabricado (null = comercial)
    o.capacidad_nominal_tf = P.W_tf; o.alivio_bar = P.p_relief; o.alarma_bar = P.p_alarm;   // rev. 7: 290 t, 680 / 600 bar (el nombre TT300-BX queda como designación del modelo)
    o.revision = "TT300-BX rev. 7 (18-11-2026): capacidad nominal " + P.W_tf + " t; todas las planchas en " + astm(P.Fy, P.Fu) + "; planchas de 22 mm (mesa, anillos, base, portador, cajón E, atiesador)" + (o.mesa.plancha_entera ? "; rev. 7c (19-11-2026): mesa con una plancha completa Ø" + P.D_top + " × " + P.t_top + " por nivel con los agujeros de los pasadores (sin anillos de pasadores)" : "");
    o.sistema = "planta x, y (mm) con O en el centro de la mesa; z desde la cara superior de la plancha base; CJP del disco sobre el eje x";
    o.z = { base_sup: 0, portador_sup: Dg.portador.t, pastilla_sup: Dg.portador.t + Dg.pastillas.h_p, disco_sup: Dg.portador.t + Dg.pastillas.h_p + Dg.disco.t, nota: "disco_sup = cara inferior de la mesa (δ sobre la base)" };
    return o;
  }

  return { _int: { layout, flow, sites, ctxOf, size, puckEval, cellOf, torsion, lamDesign, baseCredit, ringRows, BASE_FEA, mesaOf, meOn, meOk, cylGeo, cylRows, cylExport, cylOn }, PARAM_GROUPS, BX_GROUP, CYL_GROUP, CYL: { core: CYL_CORE, grupo: CYL_GRP }, A36, defaults, active, coreP, design, analyze, compute, masses, market, capacityByCyl, thermal, exportBX, cellPlate, huth, edgeForce, EcOf, matOf, fabricacion: (P) => (design(P) || {}).fabricacion, TT: TT_ };
})();
if (typeof module !== "undefined") module.exports = BX;
