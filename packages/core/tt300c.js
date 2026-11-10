/* TT300-C · Núcleo de cálculo de tornamesa hidráulica (accionamiento guiado con patín y uña, o pivotado con guía de leva tipo KIET).
   Unidades: N, mm, MPa (internas); kN, kN·m, kg y bar en la salida.
   Requiere FEA (fea.js) en el ámbito global o vía require. */
const TT = (() => {
  const FEA_ = (typeof FEA !== "undefined") ? FEA : require("./fea.js");
  const G = 9.80665, RHO = 7.85e-6, D2R = Math.PI / 180;
  const RHO_SS = 7.93e-6, RHO_UH = 0.94e-6;                       // kg/mm³: inoxidable austenítico y UHMW-PE
  const AL_SS = 17.3e-6, AL_S = 11.7e-6, AL_UH = 180e-6, E_SS = 193000;   // 1/K y MPa
  const AL_BZ = 18e-6, E_BZ = 110000, RHO_GR = 1.8e-6, PLUG_DEPTH = 0.7;   // bronce: 1/K y MPa; grafito kg/mm³; profundidad del tapón (fracción del espesor)
  const BZ_COMM = [4, 5, 6, 8, 10, 12, 15, 20, 25, 30];            // espesores comerciales de plancha de bronce (mm)
  const SS_COMM = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25];           // espesores comerciales de plancha inoxidable (mm)
  const UH_COMM = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]; // espesores comerciales de plancha UHMW (mm)

  /* ---------------- Parámetros ---------------- */
  // [id, etiqueta, unidad, valor por defecto, mín, máx, paso, nota]
  const PARAM_GROUPS = [
    { id: "carga", t: "Carga", p: [
      ["W_tf", "Capacidad nominal (WLL)", "tf", 300, 50, 1000, 10],
      ["e", "Excentricidad máx. del CG", "mm", 150, 0, 400, 10],
      ["phi_d", "Factor de carga para resistencias φd", "–", 1.10, 1, 2, 0.05],
      ["D_load", "Diámetro de apoyo de la carga (parrilla)", "mm", 1600, 600, 2000, 50],
    ] },
    { id: "interfaz", t: "Interfaz de giro (acero-acero, grasa grafitada)", p: [
      ["mu_d", "μ estático de diseño", "–", 0.20, 0.05, 0.6, 0.01],
      ["r_ef", "Radio efectivo de fricción de diseño", "mm", 800, 300, 1000, 10],
      ["mu_nom", "μ nominal (grasa limpia)", "–", 0.15, 0.05, 0.6, 0.01],
      ["mu_cont", "μ contaminado", "–", 0.25, 0.05, 0.6, 0.01],
      ["mu_dry", "μ acero seco (referencial)", "–", 0.50, 0.1, 0.9, 0.01],
      ["q_adm", "Presión de contacto admisible", "MPa", 10, 1, 50, 0.5],
      ["FS_min", "FS mínimo del accionamiento (calado / diseño)", "–", 1.25, 1, 3, 0.05],
    ] },
    { id: "inox", t: "Interfaz alternativa: discos inoxidables (A), discos con lámina UHMW (B) o placa de bronce con grafito (C)", p: [
      ["opt_ss", "Opción A: dos discos de acero inoxidable con grasa entre sí", "–", 0, 0, 1, "chk"],
      ["opt_uhmw", "Opción B: dos discos de acero inoxidable con una lámina de UHMW entre ellos", "–", 0, 0, 1, "chk"],
      ["opt_bz", "Opción C: placa de bronce con tapones de grafito (fija a la base) y disco duro rotatorio", "–", 0, 0, 1, "chk"],
      ["bz_conf", "Opción C · configuración: 1 = placa de bronce + disco duro; 2 = dos placas de bronce de aleaciones distintas; 3 = como 1 con pastillas segmentadas", "–", 1, 1, 3, 1],
      ["t_ss", "Espesor de cada disco inoxidable (0 = automático, según cálculo)", "mm", 0, 0, 40, 1],
      ["t_uhmw", "Espesor de la lámina UHMW (0 = automático, según cálculo)", "mm", 0, 0, 60, 1],
      ["Fy_ss", "Fy del acero inoxidable (ASTM A240 304: 205; 316L: 170)", "MPa", 205, 100, 600, 5],
      ["ss_void", "Ø del vacío local bajo el disco (pérdida de contacto con el respaldo) y ventana de medición de la planitud", "mm", 100, 20, 400, 5],
      ["ss_allow", "Sobreespesor por disco: desgaste y relapeado", "mm", 0.5, 0, 5, 0.1],
      ["ss_tmin", "Espesor mínimo constructivo del disco (avellanado y rectificado)", "mm", 4, 2, 20, 0.5],
      ["mu_back", "μ disco–plancha de respaldo (acero–inox limpio y seco bajo la carga; clase A de AISC: 0,30)", "–", 0.30, 0.1, 0.8, 0.01],
      ["tau_bond", "Pegado estructural del disco a su respaldo: resistencia de diseño al corte (0 = sin adhesivo)", "MPa", 0.5, 0, 5, 0.1],
      ["G_ad", "Adhesivo: módulo de corte (epóxico tenaz ≈ 100; rígido ≈ 1.000)", "MPa", 100, 10, 2000, 10],
      ["t_ad", "Adhesivo: espesor de la línea de pegado", "mm", 1.0, 0.1, 5, 0.1],
      ["tau_cyc", "Adhesivo: cortante admisible sostenido o cíclico en el borde (criterio del proyecto; confirmar con el proveedor)", "MPa", 4, 0.5, 20, 0.5],
      ["dT", "Diferencia térmica de diseño entre disco o lámina y plancha de acero", "K", 40, 0, 100, 1],
      ["muA_nom", "Opción A · μ nominal (inox–inox con grasa limpia)", "–", 0.15, 0.03, 0.6, 0.01],
      ["muA_d", "Opción A · μ estático de diseño", "–", 0.20, 0.05, 0.6, 0.01],
      ["muA_cont", "Opción A · μ contaminado", "–", 0.25, 0.05, 0.8, 0.01],
      ["muA_dry", "Opción A · μ seco (referencial; riesgo de gripado)", "–", 0.60, 0.1, 1.0, 0.01],
      ["muB_nom", "Opción B · μ nominal (UHMW sobre inox con grasa limpia)", "–", 0.08, 0.02, 0.6, 0.01],
      ["muB_d", "Opción B · μ estático de diseño (arranque tras reposo bajo carga, sin película de grasa)", "–", 0.20, 0.03, 0.6, 0.01],
      ["muB_cont", "Opción B · μ contaminado", "–", 0.25, 0.05, 0.8, 0.01],
      ["muB_dry", "Opción B · μ seco (UHMW sin lubricación)", "–", 0.25, 0.05, 0.8, 0.01],
      ["p_uhmw", "UHMW: presión admisible sostenida (≈ ¼ del esfuerzo a 10 % de deformación)", "MPa", 5, 1, 20, 0.5],
      ["E_uhmw", "UHMW: módulo aparente con fluencia (1.000 h)", "MPa", 300, 100, 1000, 10],
      ["d_flat", "Variación máxima del hueco entre las dos caras de la lámina en una ventana de Ø = vacío local (suma de las planitudes de ambas caras y de la tolerancia de espesor de la lámina)", "mm", 0.05, 0.01, 1, 0.01],
      ["uh_tmin", "Espesor mínimo constructivo de la lámina UHMW (fijación avellanada)", "mm", 6, 2, 30, 1],
      ["k_wear", "UHMW sobre inox con grasa: tasa de desgaste específico (×10⁻⁷ mm³/N·m)", "–", 2, 0.1, 100, 0.1],
      ["PV_uh", "UHMW: valor PV admisible", "MPa·m/s", 0.05, 0.01, 0.5, 0.01],
      ["n_seg", "N° de sectores de la lámina UHMW (juntas de dilatación y rebajes de retención)", "–", 24, 4, 96, 1],
      ["fix_mode", "Fijación de discos, bronce y UHMW: 1 = sectores desmontables con topes soldados al respaldo; 2 = pegado permanente (no desmontable)", "–", 1, 1, 2, 1],
      ["n_sec", "Fijación desmontable: N° de sectores de cada disco o placa de bronce", "–", 24, 6, 96, 1],
      ["L_tope", "Fijación desmontable: largo de cada tope sobre el canto radial del sector (0 = automático)", "mm", 0, 0, 800, 5],
      ["w_tope", "Fijación desmontable: filete de soldadura del tope al respaldo", "mm", 6, 3, 16, 1],
      ["b_tope", "Fijación desmontable: espesor de la barra del tope (separa los dos filetes: brazo del par de excentricidad)", "mm", 20, 6, 40, 1],
      ["a_sup", "Fijación desmontable · tope: alivio de la cara superior de la barra bajo la superficie de deslizamiento (≥ 1 mm más el sobreespesor de desgaste y relapeado)", "mm", 2, 1, 8, 0.5],
      ["a_inf", "Fijación desmontable · tope: alivio inferior en el canto del sector (chaflán 45° que libra el filete delantero; 0 = automático, w_tope + 1 mm)", "mm", 0, 0, 24, 0.5],
      ["hc_min", "Fijación desmontable · tope: altura mínima de contacto entre la barra y el canto del sector (con h_c = 3 mm el aplastamiento pasaba de FU 0,90 a 1,31 por 1 mm de error de corte: 4.ª pasada, hallazgo T6; espesor mínimo del sector con tope = a_sup + a_inf + h_c,mín = 15 mm)", "mm", 6, 1, 20, 0.5],
      ["tol_hc", "Fijación desmontable · tope: tolerancia de la altura de contacto (corte y rebabas del canto): el largo del tope y el espesor de la lámina UHMW se dimensionan con h_c − tol_hc, de modo que 1 mm menos de contacto no pasa de FU 0,90", "mm", 1, 0, 3, 0.5],
      ["j_sec", "Fijación desmontable · junta en frío entre sectores contiguos de disco, placa o lámina (mínimo 1 mm; la junta efectiva es la mayor entre este valor y la dilatación calculada, redondeada a 0,1 mm; se descuenta de la masa)", "mm", 1, 1, 10, 0.5],
      ["d_tor", "Fijación desmontable: tornillo avellanado de posición (ISO 10642)", "mm", 6, 4, 12, 1],
      ["tor2_d", "Opción A pegada (AF2: fix_mode = 2): Ø de los tornillos avellanados ISO 10642 clase 10.9 que transmiten el par del disco de la mesa a la mesa (decisión del mandante 08-11-2026: M12)", "mm", 12, 6, 20, 1],
      ["tor2_n", "AF2: N° de tornillos (0 = automático: todas las bisectrices entre pasadores libres de las ranuras radiales; con un valor menor se toman equiespaciadas entre ellas; 10-11-2026)", "–", 0, 0, 120, 1],
      ["tor2_r", "AF2: radio del círculo de tornillos (0 = automático: R_pin, intercalados con los pasadores en la corona; 10-11-2026: el R949 anterior cortaba 8 de los 24 agujeros de los pasadores y la rosca caía en el anillo inferior, no en la plancha inferior)", "mm", 0, 0, 1000, 1],
      ["Fu_ss", "Fu del acero inoxidable (ASTM A240 304: 515)", "MPa", 515, 400, 900, 5],
      ["h_gr", "Engrase: profundidad de las ranuras en el disco de la mesa (A) o en el bronce (C); 0 = sin ranuras", "mm", 1.0, 0, 5, 0.5],
      ["w_gr", "Engrase: ancho de las ranuras", "mm", 8, 3, 25, 1],
      ["n_gr_rad", "Engrase: N° de ranuras radiales", "–", 12, 0, 48, 1],
      ["n_gr_circ", "Engrase: N° de ranuras circunferenciales", "–", 3, 0, 12, 1],
      ["n_greaser", "Engrase: N° de graseras M10×1 en el borde de la mesa", "–", 4, 1, 16, 1],
      ["t_bz", "Opción C · espesor de la placa de bronce con grafito (0 = automático)", "mm", 0, 0, 60, 1],
      ["t_cara", "Opción C · espesor del disco duro o de la 2.ª placa de bronce (0 = automático)", "mm", 0, 0, 60, 1],
      ["Fy_bz", "Opción C · Fy del bronce con grafito (C95400 aluminio-bronce ≈ 170; C93200 ≈ 97; C86300 ≈ 415)", "MPa", 170, 50, 600, 5],
      ["rho_bz", "Opción C · densidad del bronce", "g/cm³", 7.45, 7, 9, 0.05],
      ["Fy_bz2", "Opción C (2 placas) · Fy de la 2.ª placa de bronce, aleación distinta (C93200 ≈ 97)", "MPa", 97, 50, 600, 5],
      ["Fy_cara", "Opción C · Fy del disco duro (17-4PH o inoxidable nitrurado)", "MPa", 1000, 200, 1500, 10],
      ["HB_cara", "Opción C · dureza del disco duro", "HB", 330, 100, 700, 10],
      ["HB_bz", "Opción C · dureza del bronce", "HB", 100, 50, 300, 5],
      ["p_bz", "Opción C · presión admisible sostenida sobre el bronce neto (sin tapones)", "MPa", 20, 5, 60, 1],
      ["PV_bz", "Opción C · valor PV admisible del bronce con grafito", "MPa·m/s", 0.5, 0.05, 3, 0.05],
      ["k_bz", "Opción C · desgaste específico del bronce con grafito (×10⁻⁷ mm³/N·m)", "–", 10, 0.1, 500, 0.1],
      ["bz_plug_d", "Opción C · diámetro de los tapones de grafito", "mm", 12, 4, 40, 1],
      ["bz_plug_p", "Opción C · paso de los tapones (patrón escalonado)", "mm", 30, 10, 100, 1],
      ["bz_edge", "Opción C · franja de borde: distancia mínima del borde del tapón al borde del bronce, a las muescas de los topes, a los tornillos de posición y a las ranuras de engrase (cuenta de tapones reales)", "mm", 4, 0, 20, 0.5],
      ["bz_fg_modo", "Opción C · fracción de grafito que usa el cálculo (masa, q_neto, PV, desgaste, lubricación): 0 = ideal f_g = π·d²/(2√3·p²) sobre toda la corona; 1 = real (tapones que caben: N_real·π·d²/4/A_contacto)", "–", 1, 0, 1, 1],
      ["bz_fg_min", "Opción C · cobertura mínima de lubricante sólido (f_g del grafito sobre el área de contacto). (supuesto C: orden de magnitud de bronces autolubricados comerciales; confirmar con el catálogo del proveedor, el valor lo fija la ficha)", "–", 0.20, 0.02, 0.6, 0.01],
      ["bz_fg_estricto", "Opción C · si f_g < bz_fg_min: 0 = aviso (el criterio es un supuesto por confirmar); 1 = no cumple (el veredicto de estructura falla)", "–", 0, 0, 1, "chk"],
      ["bz_eta_min", "Opción C · ligamento mínimo entre tapones η = (p − d)/p (criterio de proyecto)", "–", 0.45, 0.2, 0.9, 0.01],
      ["bz_n_tor", "Opción C · tornillos de posición por sector o pastilla en la zona del bronce (0, 2 o 4; 2 = sobre la bisectriz, entre la muesca y cada borde)", "–", 2, 0, 4, 2],
      ["bz_allow", "Opción C · sobreespesor del bronce por desgaste y relapeado", "mm", 1.0, 0, 6, 0.1],
      ["bz_tmin", "Opción C · espesor mínimo constructivo del bronce", "mm", 6, 3, 30, 1],
      ["cara_tmin", "Opción C · espesor mínimo del disco duro (distorsión del temple y rectificado)", "mm", 6, 3, 30, 1],
      ["bz_cover", "Opción C (configuración 3) · fracción del área cubierta por las pastillas de bronce", "–", 0.9, 0.1, 1, 0.05],
      ["bz_npad", "Opción C (configuración 3) · N° de pastillas por vuelta (junta de dilatación)", "–", 24, 6, 96, 1],
      ["muC_nom", "Opción C · μ nominal (bronce con grafito y grasa sobre acero duro)", "–", 0.08, 0.02, 0.6, 0.01],
      ["muC_d", "Opción C · μ estático de diseño (arranque tras reposo bajo carga)", "–", 0.15, 0.03, 0.6, 0.01],
      ["muC_cont", "Opción C · μ contaminado", "–", 0.20, 0.05, 0.8, 0.01],
      ["muC_dry", "Opción C · μ seco (solo grafito; referencial)", "–", 0.25, 0.05, 0.8, 0.01],
    ] },
    { id: "cubierta", t: "Cubierta de madera dura (W: tablones enrasados en el rebaje de la mesa) y altura de skidding", p: [
      ["opt_wood", "Cubierta de madera dura W (decisión del mandante, 08-11-2026): la mesa conserva el anillo superior R_reb…R (plancha superior actual en esa zona, con los pasadores); dentro de R_reb una plancha rebajada continua bajada t_madera, una pared cilíndrica en R_reb y los tablones enrasados con el anillo (sin anillo de contención 10×50; la altura total no aumenta)", "–", 0, 0, 1, "chk"],
      ["t_wood", "Espesor de los tablones = profundidad del rebaje (supuesto del mandante 50; ajustado a 45 = 2\" cepillado: con 50 el buje no cabe bajo la plancha rebajada, 142 > 140 mm, y la plancha inferior pasa de FU 0,90 por la menor altura del cajón)", "mm", 45, 20, 150, 5],
      ["rho_wood", "Densidad de la madera dura (seca al aire)", "kg/m³", 900, 500, 1300, 10],
      ["p_wood", "Presión admisible de aplastamiento perpendicular a la fibra (sostenida; confirmar con NCh1198 y el proveedor)", "MPa", 6, 1, 20, 0.5],
      ["f_apoyo", "Fracción del círculo de apoyo de la carga que toca realmente la madera (tablones contiguos dentro del rebaje: 0,90, definido por el mandante)", "–", 0.9, 0.05, 1, 0.05],
      ["h_skid", "Altura de los rieles de skidding o de la superficie de llegada (0 = no aplica)", "mm", 0, 0, 800, 5],
      ["tol_skid", "Tolerancia de enrase con los rieles", "mm", 10, 1, 50, 1],
      ["R_reb", "W · radio del rebaje: cara interior de la pared cilíndrica y borde interior del anillo superior (supuesto del mandante: 840, sobre el alma de R840)", "mm", 840, 300, 1900, 5],
      ["t_reb", "W · espesor de la plancha rebajada (0 = igual a t_top, supuesto del mandante)", "mm", 0, 0, 60, 1],
      ["t_pared", "W · espesor de la pared cilíndrica en R_reb (0 = igual a t_top, supuesto del mandante)", "mm", 0, 0, 60, 1],
      ["w_pared", "W · filete pared–plancha rebajada (a ambos lados) y filete exterior de refuerzo anillo–pared (AWS D1.1 T5.8: el anillo de 27 mm pide 8)", "mm", 8, 3, 16, 1],
      ["c_mad", "W · holgura de los tablones contra la pared (libra el filete interior w_pared + 2) y contra la abertura de la tapa de inspección", "mm", 12, 2, 40, 1],
      ["b_tab", "W · ancho nominal de los tablones (200, fijado por el mandante)", "mm", 200, 80, 400, 5],
      ["j_tab", "W · junta entre tablones (hinchamiento por humedad)", "mm", 3, 0, 15, 1],
      ["d_tmad", "W · fijación de los tablones: Ø del tornillo ISO 4762 de cabeza cilíndrica (en cajeado con arandela ISO 7093) roscado en un taladro ciego de la plancha rebajada", "mm", 10, 6, 16, 1],
      ["s_tmad", "W · fijación: separación máxima entre filas de tornillos a lo largo del tablón", "mm", 600, 200, 1500, 50],
      ["k_hmad", "W · fuerza horizontal de la carga sobre la cubierta durante el skidding, como fracción de φd·W (supuesto C: empuje de los gatos de skidding; la toma el escalón de R_reb)", "–", 0.10, 0, 0.6, 0.01],
    ] },
    { id: "mesa", t: "Mesa giratoria (cajón)", p: [
      ["D_top", "Diámetro de la mesa", "mm", 2000, 1000, 4000, 10],
      ["t_top", "Espesor plancha superior", "mm", 20, 6, 60, 1],
      ["t_bot", "Espesor plancha inferior (contacto)", "mm", 16, 6, 60, 1],
      ["h_disc", "Altura total de la mesa", "mm", 210, 60, 400, 5],
      ["rings", "Radios de almas anulares", "mm", "300, 590, 840"],   // 3.ª pasada: 2.º anillo 580 → 590 (con R_i = 131 el momento global sube 8 % y con 580 la plancha superior quedaba en FU 0,906 > 0,90; con 590, 0,850; sin costo de masa)
      ["t_web", "Espesor almas anulares", "mm", 6, 6, 40, 1],
      ["N_rib", "N° de nervios radiales", "–", 14, 4, 56, 1],
      ["t_rib", "Espesor nervios radiales", "mm", 6, 6, 40, 1],
      ["R_rib", "Radio exterior de nervios", "mm", 840, 300, 1900, 5],
      ["D_hub", "Diámetro exterior del cubo (pared ≥ 25 mm junto al rebaje del collar: D_cubo ≥ D_collar + 2·c_boss_r + 50)", "mm", 310, 150, 600, 10],
      ["w_web", "Filete almas/nervios–planchas (cada lado)", "mm", 6, 3, 16, 1],
    ] },
    { id: "pasadores", t: "Pasadores de empuje (en la mesa)", p: [
      ["N_pin", "N° de pasadores", "–", 28, 8, 72, 1],
      ["d_pin", "Diámetro del pasador", "mm", 85, 30, 160, 5],
      ["R_pin", "Radio del círculo de pasadores", "mm", 930, 400, 1950, 5],
      ["Fy_pin", "Fy pasador (34CrNiMo6+QT)", "MPa", 800, 235, 1000, 5],
      ["t_pr", "Espesor del anillo perimetral de pasadores (sup. e inf.)", "mm", 27, 10, 80, 1],
    ] },
    { id: "cilindros", t: "Cilindros hidráulicos", p: [
      ["n_cyl", "N° de cilindros (en par)", "–", 2, 1, 4, 1],
      ["D_bore", "Diámetro del émbolo", "mm", 90, 40, 250, 1],
      ["d_rod", "Diámetro del vástago", "mm", 63, 20, 200, 1],
      ["D_body", "Diámetro exterior del cuerpo", "mm", 130, 50, 300, 1],
      ["p_rated", "Presión nominal del cilindro y la bomba (clase de catálogo: 10.000 o 5.000 psi)", "psi", 10000, 1000, 10000, 500],
      ["p_relief", "Presión de alivio (calado)", "bar", 700, 50, 800, 10],
      ["p_alarm", "Presión de alarma / detención", "bar", 600, 50, 800, 10],
      ["p_ret", "Presión de retorno (puerto B)", "bar", 200, 10, 700, 10],
      ["stroke", "Carrera", "mm", 235, 50, 600, 1],
      ["L0", "Longitud ojal-ojal retraído (confirmar con proveedor)", "mm", 520, 200, 2000, 1],
      ["e_body", "Distancia del eje del ojal trasero al inicio del cuerpo", "mm", 75, 30, 300, 1],
      ["c_rod", "Retraído: eje del ojal del vástago → cara frontal del cuerpo", "mm", 110, 30, 400, 1],
      ["eta_c", "Rendimiento del cilindro (sellos)", "–", 0.95, 0.8, 1, 0.01],
      ["m_cyl", "Masa por cilindro", "kg", 55, 5, 500, 1],
      ["Q_pump", "Caudal de la bomba en el avance (a la presión de trabajo)", "L/min", 10, 0.2, 50, 0.1],
      ["Q_ret", "Caudal de retorno, bomba de dos etapas o válvula de alto caudal (0 = igual al de avance)", "L/min", 20, 0, 100, 0.1],
      ["eta_pump", "Rendimiento global de la bomba y el motor", "–", 0.85, 0.5, 0.95, 0.01],
      ["t_vuelta_obj", "Tiempo por vuelta objetivo (0 = sin objetivo)", "min", 15, 0, 240, 1],
      ["v_ret_max", "Velocidad máxima de retorno del vástago (rebote de la uña sobre el pasador)", "m/s", 0.25, 0.02, 1, 0.01],
    ] },
    { id: "modo", t: "Modo de accionamiento y material de las levas", p: [
      ["drive_mode", "Modo de accionamiento: 1 = guiado (patín y uña sobre bancada, con leva de reenganche); 2 = pivotado con guía de leva tipo KIET (cilindro pivotado en una esquina, bloque-uña sobre pasador vertical Q, placa-leva por sentido de giro). Por defecto 2 (decisión del mandante, 08-11-2026)", "–", 2, 1, 2, 1],
      ["cam_mat", "Material del contacto seguidor–leva: 0 = automático (guiado: 1, el rodillo es el único que no se autobloquea con la rampa que exige la sincronía; pivotado: sigue la interfaz de giro: acero–acero → 1, A → 4, B → 4 (la zapata de UHMW no cumple PV en el empuje), C → 3); 1 = acero templado–acero con grasa grafitada; 2 = UHMW sobre respaldo de acero (μ, p_adm y PV de la opción B); 3 = bronce con tapones de grafito sobre respaldo de acero (opción C); 4 = inoxidable–inoxidable con grasa (opción A)", "–", 0, 0, 4, 1],
      ["Fu_bolt", "Pernos de las levas y sus soportes: Fu (ISO 898-1 clase 10.9 ≈ AISC 360-22 grupo 150: 1.040)", "MPa", 1040, 400, 1220, 10],
    ] },
    { id: "cinematica", t: "Accionamiento guiado (patín y uña)", p: [
      ["x_g", "Eje del cilindro y de la guía: distancia al centro", "mm", 1140, 500, 2500, 5],
      ["l_p", "Pasador del vástago (en el patín) → centro del pasador tomado", "mm", 300, 100, 800, 5],
      ["s_free", "Recorrido libre antes de tomar el pasador (sobrecarrera de retorno: con la leva de reenganche positiva la rampa necesita ≥ 20 mm detrás del pasador siguiente; 10 → 21 mm, 07-11-2026)", "mm", 21, 0, 100, 1],
      ["s_margin", "Margen mínimo de carrera exigido", "mm", 5, 0, 50, 1],
      ["mu_g", "μ patín–guía (grasa grafitada)", "–", 0.15, 0.05, 0.6, 0.01],
      ["w_s", "Ancho del patín (en x)", "mm", 245, 60, 400, 5],
      ["slot", "Holgura radial de la uña en el patín", "mm", 10, 2, 40, 1],
      ["c_tip", "Penetración de la uña más allá del centro del pasador", "mm", 15, 0, 60, 1],
      ["s_sp", "Largo del resorte de retorno comprimido + tope", "mm", 55, 10, 150, 1],
      ["f_ext", "Extensión delantera del patín (más largo de guía)", "mm", 165, 0, 400, 5],
      ["t_fw", "Marco de boca: espesor de las paredes laterales", "mm", 80, 10, 100, 1],
      ["Fy_shoe", "Fy del patín (alojamiento de la uña y marco de boca)", "MPa", 460, 235, 1000, 5],
      ["t_pk", "Patín: espesor mínimo de tapa y fondo del alojamiento de la uña", "mm", 8, 4, 40, 1],
    ] },
    { id: "una", t: "Uña de empuje (en el patín)", p: [
      ["dog_b", "Uña: ancho en el sentido del empuje", "mm", 88, 20, 200, 1],
      ["dog_h", "Uña: alto", "mm", 110, 20, 200, 1],
      ["L_in", "Uña: largo alojado en el patín", "mm", 125, 50, 500, 5],
      ["l_lip", "Labio de apoyo de la uña en el patín (largo en x)", "mm", 60, 20, 200, 5],
      ["e_dog", "Excentricidad accidental de la uña", "mm", 10, 0, 50, 1],
      ["Fy_dog", "Fy uña (34CrNiMo6+QT, EN 10083-3 Re ≥ 800 para 40 < t ≤ 100 mm, certificado 3.1)", "MPa", 800, 235, 1200, 5],
      ["mu_s", "μ cara de la uña–pasador (deslizamiento radial)", "–", 0.15, 0.05, 0.6, 0.01],
      ["Fy_surf", "Límite elástico superficial de las caras de contacto (temple por inducción ≥ 55 HRC)", "MPa", 1500, 235, 2000, 10],
      ["k_edge", "Concentración de la carga lineal en los bordes de la cara (flexión del pasador bajo uña rígida)", "–", 1.32, 1, 3, 0.01],
      ["beta_ch", "Chaflán de retorno: ángulo de la normal respecto del eje radial", "°", 54, 20, 80, 1],
      ["mu_ret", "μ de retorno (chaflán y alojamiento), verificación de autobloqueo", "–", 0.20, 0.05, 0.6, 0.01],
      ["b_tip", "Ancho mínimo de la punta de la uña tras el chaflán", "mm", 20, 5, 100, 1],
    ] },
    { id: "guia", t: "Bancada de guía", p: [
      ["t_bed", "Bancada: espesor", "mm", 40, 16, 100, 1],
      ["w_bed", "Bancada: ancho", "mm", 160, 60, 400, 5],
      ["w_slot", "Ranura de guía: ancho (H8)", "mm", 40, 10, 100, 1],
      ["h_slot", "Ranura de guía: profundidad del cuello", "mm", 18, 5, 60, 1],
      ["w_tee", "Ranura T: ancho de la cabeza (retención vertical del patín)", "mm", 64, 10, 150, 1],
      ["h_tee", "Ranura T: alto de la cabeza", "mm", 10, 0, 40, 1],
      ["w_bed_f", "Filete bancada–base", "mm", 10, 4, 20, 1],
    ] },
    { id: "leva_guiada", t: "Accionamiento guiado: leva de reenganche positiva (riel-leva sobre el patín, apoyado en soportes empernados a la bancada)", p: [
      ["opt_cam", "Leva de reenganche positiva: riel-leva fijo que limita la salida de la uña, con bolsillo para pasar sobre el pasador siguiente y rampa que la devuelve detrás de él (el resorte queda de apoyo)", "–", 1, 0, 1, "chk"],
      ["cam_alpha", "Rampa de reenganche: ángulo del canto respecto del eje de la bancada (mínimo por sincronía, máximo por autobloqueo)", "°", 62, 20, 80, 1],
      ["cam_c", "Holgura de la leva sobre la posición de toma de la uña", "mm", 3, 0.5, 20, 0.5],
      ["cam_msync", "Margen mínimo de sincronía: holgura uña–pasador siguiente con la uña apoyada en la leva", "mm", 5, 1, 30, 0.5],
      ["cam_dwell", "Tramo a nivel de toma al final de la rampa (extremo retraído)", "mm", 2, 0, 20, 0.5],
      ["cam_df", "Seguidor: Ø del rodillo (familia 1) o de la zapata (familias 2–4)", "mm", 70, 30, 160, 1],
      ["cam_bf", "Seguidor: ancho del rodillo o alto de la zapata (≤ espesor del riel − 5)", "mm", 30, 10, 80, 1],
      ["cam_dp", "Seguidor: Ø del perno vertical fijo en la uña (pasa por una ranura de la tapa del patín, que lo guía en y)", "mm", 50, 16, 100, 1],
      ["mu_roll", "Seguidor de rodillo (familia 1): μ equivalente de rodadura y cojinete (conservador)", "–", 0.05, 0.005, 0.3, 0.005],
      ["cam_t", "Riel-leva: espesor de la pletina (va entre la cara superior del patín + 2 mm y la cara superior de la mesa)", "mm", 38, 10, 60, 1],
      ["cam_w", "Riel-leva: ancho de la pletina medido desde el canto a nivel de toma (la sección neta descuenta el bolsillo)", "mm", 170, 60, 300, 5],
      ["Fy_cam", "Riel-leva y soportes: Fy (42CrMo4+QT, EN 10083-3, 16 < t ≤ 40 mm: Re ≥ 750; canto templado por inducción ≥ 55 HRC)", "MPa", 750, 235, 1000, 5],
      ["cam_ls", "Pórticos del riel: largo en y de cada pata (la bancada se prolonga esto en cada extremo, ensanchada para asentar las dos patas)", "mm", 160, 40, 300, 5],
      ["cam_px", "Pórticos del riel: espesor en x de cada pata (una a cada lado del cuerpo del cilindro, que pasa bajo el pórtico trasero; 30 → 40 el 10-11-2026: las patas pasan a S355J2 soldable y con la interfaz B la flexión daba FU 1,20)", "mm", 40, 10, 80, 1],
      ["cam_nb", "Pórticos del riel: N° de pernos riel–pórtico por pórtico (verticales, la mitad en cada pata)", "–", 4, 2, 12, 2],
      ["cam_db", "Pórticos del riel: Ø de los pernos riel–pórtico", "mm", 20, 10, 36, 1],
      ["cam_wf", "Pórticos del riel: filete de cada pata a su asiento (perimetral)", "mm", 20, 4, 30, 1],
      ["Fu_cam", "Riel-leva: Fu (42CrMo4+QT, 16 < t ≤ 40 mm: Rm ≥ 1.000; se toma 900)", "MPa", 900, 300, 1200, 10],
    ] },
    { id: "articulacion", t: "Articulaciones y ménsulas del cilindro", p: [
      ["d_pp", "Diámetro de pasadores de articulación", "mm", 70, 20, 150, 5],
      ["Fy_pp", "Fy pasadores de articulación", "MPa", 650, 235, 1000, 5],
      ["t_ch", "Espesor de mejillas (horquilla)", "mm", 25, 8, 80, 1],
      ["g_ch", "Holgura mejilla-ojal", "mm", 2, 0, 10, 0.5],
      ["b_eye", "Ancho del ojal del cilindro", "mm", 50, 20, 150, 1],
      ["L_ch", "Largo de mejilla de la ménsula (sobre la base)", "mm", 325, 80, 800, 5],
      ["w_br", "Filete mejilla–base", "mm", 20, 4, 25, 1],
      ["n_br", "N° de ménsulas (2 por sentido de giro)", "–", 4, 2, 8, 1],
    ] },
    { id: "pivotado", t: "Accionamiento pivotado con guía de leva (tipo KIET; drive_mode = 2)", p: [
      ["pv_RE", "Ojal trasero E (pasador vertical fijo a la base): radio desde el centro (0 = sugerencia automática que maximiza el brazo efectivo mínimo; valor por defecto = sugerencia con los demás valores por defecto)", "mm", 1604, 0, 2500, 1],
      ["pv_phE", "Ojal trasero E: ángulo en planta (diagonal de la base como KIET, 315°; el 2.° cilindro va a +180°; el otro sentido de giro es la imagen especular respecto de la diagonal)", "°", 315, 0, 360, 1],
      ["pv_Lqp", "Bloque-uña: pasador Q → centro del pasador tomado (0 = sugerencia automática; la sugerencia con los valores por defecto es 440 mm y se adopta 432 para dejar 2 mm sobre la holgura mínima con el pasador siguiente, por tolerancias y por la dilatación de la mesa a 80 °C)", "mm", 432, 0, 1000, 1],
      ["pv_bu", "Bloque-uña: ancho del cuerpo en planta (70 → 90 el 09-11-2026, ensanchado hacia afuera con e_cr: la resultante del contacto con roce pasa por Q y por el punto de contacto desplazado, y suma excentricidad al cuerpo)", "mm", 90, 30, 150, 1],
      ["pv_ecr", "Bloque-uña: desplazamiento lateral del cuerpo hacia afuera (cuerpo acodado que libra el pasador siguiente; flexión F·e en el cuerpo; 35 → 45 el 09-11-2026 para conservar el borde interior al ensanchar el cuerpo)", "mm", 45, 0, 80, 1],
      ["pv_bf", "Bloque-uña: ancho de la cara de empuje (tramo de la cara centrado en la línea E–Q–P)", "mm", 80, 30, 160, 1],
      ["pv_rface", "Bloque-uña: radio de la cara de empuje cilíndrica convexa en planta (0 = plana). Con cara plana y roce μ_s el contacto se va a μ_s·(L_qp − r) ≈ 58 mm del eje, fuera de la cara: la cara convexa lo mantiene a R·sen γ del eje (09-11-2026)", "mm", 120, 0, 400, 5],
      ["pv_lf", "Bloque-uña: largo del tramo de la cara", "mm", 60, 20, 200, 1],
      ["pv_hu", "Bloque-uña: alto (≤ luz libre entre anillos − 10)", "mm", 140, 40, 200, 1],
      ["pv_dq", "Pasador vertical Q (bloque-uña sobre el ojal del vástago; su extremo inferior es el seguidor de la placa-leva): Ø", "mm", 90, 30, 150, 1],
      ["pv_dE", "Pasador vertical del ojal trasero E: Ø", "mm", 70, 30, 150, 1],
      ["pv_tl", "Soporte del ojal E: espesor de las tapas superior e inferior del cajón (orejas del pasador E; 28 → 29 el 10-11-2026: el desgarro hacia las paredes se mide hasta su cara interior, a la que se suelda la tapa, y con 28 mm daba FU 0,909; con 30 mm la flexión del pasador E pasa de 0,90)", "mm", 29, 8, 80, 1],
      ["pv_box", "Soporte del ojal E: lado del cajón soldado a la base, centrado en E (paredes traseras en L hacia la esquina; ventana para el ojal hacia la mesa: sección en U)", "mm", 260, 100, 500, 5],
      ["pv_tbox", "Soporte del ojal E: espesor de las paredes del cajón (25 → 30 el 10-11-2026: el cajón queda abierto hacia la mesa en todo el barrido del cilindro y la flexión en la base la toman las paredes traseras en L y los muñones; con 25 mm FU 0,877)", "mm", 30, 6, 50, 1],
      ["pv_wbox", "Soporte del ojal E: filete de refuerzo de las CJP pared–base y pared–pared y de las PJP de las tapas (10-11-2026: las uniones resistentes son CJP y PJP; 21 → 8 = mínimo AWS D1.1 Tabla 7.7 para la parte más gruesa > 20 mm)", "mm", 8, 4, 30, 1],
      ["pv_ext", "Soporte del ojal E: prolongación de las paredes traseras hacia la mesa más allá del cajón (aletas a lo largo de los bordes de la base, fuera del barrido del cilindro; 10-11-2026: sin pared delantera la flexión en la base la toman las paredes traseras, y con la interfaz B el eje sube y con 0 mm daba FU 1,22; con 100 mm 0,75)", "mm", 100, 0, 400, 5],
      ["pv_cE", "Soporte del ojal E: holgura de diseño entre el cuerpo del cilindro y las piezas del soporte (recorte en nariz de las tapas y largo de los muñones; la verificación exige ≥ 5 mm en todos los estados del empuje y del retorno, en ambos sentidos)", "mm", 8, 6, 30, 0.5],
      ["pv_rebt", "Soporte del ojal E: rebaje de la cara superior de la tapa superior bajo el borde de las paredes (rincón para el filete de refuerzo de la PJP)", "mm", 10, 0, 30, 1],
      ["pv_muE", "μ del pasador del ojal E (resistencia al giro del cilindro en la rampa de la leva)", "–", 0.20, 0.05, 0.6, 0.01],
      ["pv_c", "Placa-guía: separación del canto sobre la trayectoria colineal de Q al final del empuje y nivel de toma en el retraído (en el empuje Q se apoya en el canto: la rodilla E–Q–P es inestable en compresión)", "mm", 3, 0.5, 20, 0.5],
      ["pv_msync", "Placa-leva: margen mínimo de sincronía (holgura bloque-uña–pasador siguiente con Q apoyado en la leva)", "mm", 5, 1, 30, 0.5],
      ["pv_alpha", "Placa-guía: ángulo máximo admisible del flanco de reenganche respecto de la recta radial E–Q (el flanco recto usa el mínimo que exige la sincronía; con un límite menor la sincronía no cumple)", "°", 65, 20, 80, 1],
      ["pv_dwell", "Placa-guía: el flanco de reenganche pasa por el nivel de toma c en L0 + tramo (0 = en el retraído; 2 → 0 el 09-11-2026: el flanco recto ya no necesita tramo a nivel)", "mm", 0, 0, 20, 0.5],
      ["pv_tcam", "Placa-guía: espesor (alto del contacto con el seguidor; el bloque-uña y el cuerpo del cilindro pasan sobre ella)", "mm", 30, 10, 60, 1],
      ["pv_wlip", "Placa-guía: ligamento entre el punto más profundo del canto y el borde exterior de la placa rectangular (lleva la fila exterior de pernos)", "mm", 80, 30, 200, 5],
      ["pv_rmin", "Placa-guía: radio mínimo del canto convexo (sin socavado: radio de la trayectoria del centro ≥ d_Q/2 + este valor)", "mm", 10, 2, 100, 1],
      ["pv_tolg", "Placa-guía: tolerancia de posición del canto (corte CNC ± 0,2 y pasadores de posición ± 0,2); se suma al margen de sincronía con el crecimiento del círculo de pasadores a 80 °C", "mm", 0.4, 0, 3, 0.05],
      ["Fy_camP", "Placa-guía: Fy del acero (42CrMo4+QT, EN 10083-3, 16 < t ≤ 40 mm: Re ≥ 750; templable por inducción en el canto; era S355J2, que no admite el temple del canto que pide el contacto de Hertz)", "MPa", 750, 235, 1000, 5],
      ["Fu_camP", "Placa-guía: Fu del acero (42CrMo4+QT, 16 < t ≤ 40 mm: Rm ≥ 1.000; se toma 900 como el riel-leva)", "MPa", 900, 300, 1100, 10],
      ["pv_nb", "Placa-guía: N° de tornillos por placa (4 en las esquinas y el resto en la fila exterior; 6 → 8 el 09-11-2026: con M16 8.8 el grupo excéntrico pide 8)", "–", 8, 2, 16, 1],
      ["pv_db", "Placa-guía: Ø de los tornillos avellanados ISO 10642 roscados en la base (20 → 16 el 09-11-2026: con t_base = 18 mm el enganche de rosca ≥ 1,0·d de un 8.8 pide d ≤ 18; los pasantes con tuerca no caben bajo la base apoyada en la losa)", "mm", 16, 10, 36, 1],
      ["pv_Fub", "Placa-guía: Fu de los tornillos (clase 8.8: 800)", "MPa", 800, 400, 1200, 10],
      ["pv_dd", "Placa-guía: Ø de los 2 pasadores de posición ISO 8734 (m6 en agujeros H7 escariados, ciegos, en placa y base; 16 → 8 el 10-11-2026: el enganche ≥ 1,5·d en la base de 18 mm con alojamiento ciego, remanente 3 mm y 2 mm al fondo admite d ≤ 8)", "mm", 8, 4, 30, 1],
      ["pv_Fyrod", "Vástago del cilindro: Fy (DATO DEL PROVEEDOR; hipótesis: acero templado y cromado ≥ 520 MPa)", "MPa", 520, 235, 1000, 5],
      ["pv_tlin", "Placa-leva: espesor del revestimiento del canto (familias 2–4)", "mm", 8, 2, 30, 1],
      ["pv_lpad", "Seguidor: largo de la zapata en el sentido de la leva (0 = automático: Ø del pasador Q o el que piden p_adm y PV de la familia con FU 0,90)", "mm", 0, 0, 600, 5],
      ["pv_cQ", "Holgura del pasador Q al borde de la mesa (la placa-leva va sobre la base, fuera de la mesa)", "mm", 10, 2, 50, 1],
      ["pv_cB", "Holgura mínima bloque-uña–pasador siguiente durante el empuje", "mm", 10, 2, 50, 1],
      ["pv_cc", "Holgura mínima cuerpo del cilindro–borde de la mesa", "mm", 10, 2, 100, 1],
      ["pv_fugeo", "Sugerencia de E: FU objetivo de las holguras «cajón del ojal dentro de la base» y «Q fuera de la mesa» (1 = solo factibles; con B = 2.560 no hay solución por debajo de 0,97: el cajón pide R_E chico y Q fuera de la mesa lo pide grande; FU ≤ 0,95 en ambas exige B ≥ 2.760)", "–", 1, 0.5, 1, 0.01],
    ] },
    { id: "base", t: "Base", p: [
      ["B", "Lado de la base cuadrada", "mm", 2560, 1000, 4500, 10],
      ["t_base", "Espesor plancha base (18 → 20 el 10-11-2026: decisión del mandante, base de 20 mm con inserto de esquina bajo los soportes)", "mm", 20, 6, 60, 1],
      ["ins_on", "Inserto de esquina bajo cada soporte del cilindro (1 = sí; 0 = sin inserto: modelo de la franja sin anclaje, pendiente)", "–", 1, 0, 1, 1],
      ["ins_fsv", "Inserto: margen sobre la fuerza para girar la mesa vacía (caso de servicio; 1,25 = FS de giro del proyecto)", "–", 1.25, 1, 3, 0.05],
      ["t_base_min", "Espesor mínimo de base por planitud (criterio de fabricación)", "mm", 16, 6, 60, 1],
      ["rim_h", "Alto del marco perimetral", "mm", 45, 0, 200, 1],
      ["rim_t", "Espesor del marco perimetral", "mm", 10, 0, 40, 1],
      ["c_lug", "Puntos de izaje (lados y): distancia al borde (4.ª pasada: 150 → 200 mm; con hc_min = 6 la opción B pesa ≈ 4,1 t y con 150 mm la flecha de izaje pasaba del límite B/300; con 200 mm queda 15 % bajo el límite. 08-11-2026: 200 → 250 mm, la leva de reenganche suma ≈ 160 kg sobre la base y con 200 mm la variante B + madera quedaba a 8 % del límite, bajo el margen de 10 % del hallazgo C12; con 250 mm queda 23 % bajo el límite)", "mm", 430, 30, 600, 5],
      ["x_lug", "Puntos de izaje: distancia al eje y (10-11-2026: 600 → 850 y c 250 → 430, orejas sobre las diagonales (±850; ±850): en (±600; ±1.030) las placas-guía del sentido horario y los bloques-uña del modo pivotado pasaban sobre las orejas; en la diagonal quedan entre los dos barridos del cilindro, a 110 mm de la mesa)", "mm", 850, 0, 2000, 5],
      ["t_ear", "Orejas de izaje (4, soldadas a la base): espesor de la placa", "mm", 18, 6, 50, 1],
      ["R_ear", "Orejas de izaje: radio exterior (ancho = 2R; AISC 360-22 D5.2(3): a = R − d/2 ≥ 1,33·b_e)", "mm", 92, 30, 150, 1],
      ["d_ear", "Orejas de izaje: diámetro del agujero (grillete: pasador = d − g_ear)", "mm", 45, 20, 100, 1],
      ["g_ear", "Orejas de izaje: holgura diametral agujero–pasador del grillete", "mm", 3, 0, 10, 0.5],
      ["ear_gira", "Orejas de izaje: el pasador gira bajo la carga plena (AISC D5.2(2) exige holgura ≤ 1 mm; 0 = izaje estático)", "–", 0, 0, 1, "chk"],
      ["h_ear", "Orejas de izaje: altura del centro del agujero sobre la base", "mm", 90, 40, 300, 5],
      ["w_ear", "Orejas de izaje: filete de soldadura a la base (ambos lados)", "mm", 8, 4, 16, 1],
      ["phi_lift", "Factor dinámico de izaje", "–", 1.30, 1, 2, 0.05],
      ["q_floor", "Presión admisible de la losa / mats (referencial)", "MPa", 2.0, 0.1, 20, 0.1],
    ] },
    { id: "pivote", t: "Pivote central", p: [
      ["D_piv", "Diámetro del pivote", "mm", 120, 40, 400, 5],
      ["L_bush", "Largo del buje", "mm", 80, 20, 300, 5],
      ["p_bush", "Presión admisible del buje", "MPa", 30, 5, 100, 1],
      ["mu_bush", "μ del buje", "–", 0.20, 0.02, 0.5, 0.01],
      ["e_piv", "Brazo de flexión del pivote desde la cara superior del asiento: mínimo de ingreso (0 = automático); el brazo efectivo es máx(e_piv; g_bush + L_buje/2)", "mm", 0, 0, 200, 1],
      ["g_bush", "Holgura axial del buje sobre el collar (el buje reacciona a media altura: e = g_bush + L_buje/2)", "mm", 2, 0, 20, 0.5],
      ["h_boss", "Collar de asiento del pivote soldado sobre la base: altura (0 = sin collar; asiento = t_base + h_collar)", "mm", 60, 0, 200, 5],
      ["D_boss", "Collar de asiento del pivote: diámetro exterior (entra en un rebaje del cubo)", "mm", 250, 160, 500, 10],
      ["w_collar", "Collar de asiento del pivote: filete perimetral a la base", "mm", 10, 4, 30, 1],
      ["c_boss_r", "Rebaje del cubo: holgura radial con el collar (el cubo gira, el collar es fijo)", "mm", 3, 0, 20, 0.5],
      ["c_boss_a", "Rebaje del cubo: holgura axial sobre el collar (profundidad del rebaje desde la cara inferior de la mesa = h_collar − δ + c_boss_a, δ = altura que suma la interfaz)", "mm", 2, 0, 20, 0.5],
      ["m_ri", "Interfaz de giro: margen de borde entre el rebaje del collar y el radio interior R_i del anillo de contacto (con collar: R_i = D_collar/2 + c_boss_r + m_ri; sin collar: D_piv/2 + 15)", "mm", 3, 0, 30, 1],
      ["Fy_piv", "Fy pivote", "MPa", 650, 235, 1000, 5],
      ["Ch", "Coeficiente sísmico horizontal (0 = no aplica, decisión del mandante)", "–", 0, 0, 1.5, 0.01],
    ] },
    { id: "material", t: "Materiales y normas", p: [
      ["Fy", "Fy acero estructural (ASTM A572 Gr.50)", "MPa", 345, 235, 690, 5],
      ["Fu", "Fu acero estructural (ASTM A572 Gr.50: 450)", "MPa", 450, 340, 800, 5],
      ["FEXX", "Resistencia del electrodo FEXX", "MPa", 490, 410, 830, 10],
      ["E", "Módulo de elasticidad", "MPa", 200000, 190000, 210000, 1000],
      ["nu", "Coeficiente de Poisson", "–", 0.30, 0.25, 0.35, 0.01],
      ["Nd", "ASME BTH-1 factor de diseño (Cat. B = 3,0)", "–", 3.0, 2.0, 4.0, 0.5],
      ["kFEA", "Factor de convergencia de malla FEA (error de malla de las planchas de la mesa: 1,20 a 1,21 por Richardson; ver tests/convergencia.js)", "–", 1.22, 1, 1.5, 0.01],
    ] },
    { id: "fatiga", t: "Ciclo de servicio (fatiga)", p: [
      ["turns_yr", "Vueltas completas por año", "–", 50, 0, 10000, 1],
      ["life", "Vida de diseño", "años", 25, 1, 100, 1],
    ] },
    // Escenario térmico (docs/normas/registro.md · «Temperatura (exposición solar, 80 °C)»): NO modifica el cálculo a 20 °C. TT.thermal evalúa la geometría
    // dimensionada a 20 °C con las capacidades reducidas a T_serv. Los factores se dan a 80 °C (columna «Factor 80/20» del registro) y se interpolan
    // linealmente desde 1,00 a T_ref; sobre 80 °C se extrapola con cautela. Nivel de confianza del dato entre paréntesis (A tabla contrastada, B ficha o dos fuentes, C supuesto).
    { id: "temperatura", t: "Temperatura de servicio (escenario solar; no cambia el cálculo a 20 °C)", p: [
      ["T_serv", "Temperatura del cuerpo en servicio (escenario térmico aparte; solar: 80)", "°C", 20, 20, 120, 5],
      ["T_ref", "Temperatura de referencia del diseño y del montaje", "°C", 20, 0, 40, 1],
      ["term_alcance", "Alcance de la verificación térmica: 1 = sistema de placas y disco (plancha base, mesa, interfaz con sus topes y juntas, madera, pivote y collar); 2 = además el accionamiento mecánico (uña–pasador, patín–guía, pasadores de empuje) y el circuito hidráulico (cilindros, aceite atrapado, alivio térmico, sellos, viscosidad y bomba)", "–", 1, 1, 2, 1],
      ["dT_grad", "Gradiente plancha superior–inferior a 80 °C (hipótesis EN 1991-1-5 T6.1 de otra tipología, confianza C; escenario solar 15–18; 0 = sin gradiente; a otra T se escala con ΔT/60)", "K", 0, 0, 40, 1],
      ["kT_Fy", "Acero estructural y aleado: Fy a 80 °C / Fy a 20 °C (AISC 360-22 App. 4 y EN 1993-1-2: 1,00, confianza B; sensibilidad ASME II-D Tabla Y-1: 0,92, confianza C)", "–", 1.00, 0.5, 1, 0.01],
      ["kT_E", "Acero: E a 80 °C / E a 20 °C (EN 1993-1-2 k_E,θ = 1,00 a 100 °C, confianza B)", "–", 1.00, 0.5, 1, 0.005],
      ["kT_Fy_ss", "Inoxidable 304/316: Fy a 80 °C / Fy a 20 °C (EN 10088-2 de memoria, 0,80–0,85, confianza C)", "–", 0.82, 0.5, 1, 0.01],
      ["kT_E_ss", "Inoxidable: E a 80 °C / E a 20 °C (EN 10088-1: 194 GPa a 100 °C, confianza B)", "–", 0.975, 0.8, 1, 0.005],
      ["kT_p_uh", "UHMW-PE: capacidad (p_adm y PV) a 80 °C / a 20 °C (supuesto 0,3–0,5 sin curva del proveedor, confianza C; 80 °C es su límite de servicio)", "–", 0.40, 0.1, 1, 0.05],
      ["kT_E_uh", "UHMW-PE: módulo aparente a 80 °C / a 20 °C (supuesto sin curva del proveedor, confianza C)", "–", 0.40, 0.1, 1, 0.05],
      ["kT_bz", "Bronce (Fy, p_adm, PV, presión del buje) a 80 °C / a 20 °C (criterio de ingeniería, confianza C; sensibilidad 0,90)", "–", 1.00, 0.5, 1, 0.01],
      ["kT_wood", "Madera dura: factor C_t de aplastamiento perpendicular a la fibra a 80 °C (NDS 2018 T2.3.3: 0,7 seca; tabla confianza A, extrapolación a 80 °C confianza C)", "–", 0.70, 0.3, 1, 0.05],
      ["kT_bolt", "Pernos ISO 898-1 clase 10.9: Rp0,2 a 80 °C / a 20 °C (de memoria 0,93–0,95, confianza C)", "–", 0.94, 0.5, 1, 0.01],
      ["kT_weld", "Soldadura E70XX: FEXX a 80 °C / a 20 °C (criterio del revisor, confianza C)", "–", 1.00, 0.5, 1, 0.01],
      ["kT_hertz", "Fy superficial de las caras templadas (Hertz) a 80 °C / a 20 °C (criterio, confianza C)", "–", 1.00, 0.5, 1, 0.01],
      ["k_mu_T", "μ a 80 °C / μ a 20 °C (la grasa fluye y se expulsa; dato de entrada sin fuente, confianza C; 1,0 = sin cambio)", "–", 1.0, 0.5, 3, 0.05],
      ["c_bush_d", "Holgura diametral en frío buje de bronce–pivote (supuesto de ajuste H7/e8 para Ø120, confianza C)", "mm", 0.10, 0.02, 0.5, 0.01],
      ["K_oil", "Módulo volumétrico del aceite, cota baja (1,4–1,9 GPa a 80 °C y 700 bar, confianza C)", "MPa", 1400, 800, 2500, 50],
      ["K_oil_hi", "Módulo volumétrico del aceite, cota alta (da la mayor sobrepresión: es la que gobierna la verificación)", "MPa", 1900, 800, 2500, 50],
      ["ba_cil", "Relación de diámetros exterior/interior de la pared del cilindro hidráulico b/a (Lamé; supuesto, confianza C)", "–", 1.4, 1.05, 3, 0.05],
      ["oil_cont", "Rigidez del contenedor del aceite atrapado: 1 = rígido; 2 = cilindro (Lamé); 3 = manguera (K combinado ≈ 327 MPa)", "–", 2, 1, 3, 1],
      ["p_max_cil", "Presión máxima de trabajo del cilindro (prueba = 1,5 × esta; ISO 10100 de memoria, confianza C)", "bar", 700, 100, 1000, 10],
      ["alivio_term", "Válvula de alivio térmico en el tramo aislado (cilindro + retenciones): presión de apertura (0 = no hay)", "bar", 0, 0, 1000, 10],
      ["nu_min", "Viscosidad mínima admisible de la bomba (supuesto del revisor, confianza C)", "mm²/s", 10, 3, 40, 1],
      ["T_seal", "Límite de servicio continuo de los sellos NBR (80–120 °C según fuente, confianza C; se toma el menor)", "°C", 80, 60, 120, 5],
      ["T_drop", "Punto de goteo de la grasa grafitada NLGI 2 (≥ 175 °C, confianza B)", "°C", 175, 100, 300, 5],
    ] },
  ];

  function defaults() {
    const P = {};
    PARAM_GROUPS.forEach((g) => g.p.forEach((q) => { P[q[0]] = q[3]; }));
    return P;
  }
  function parseRings(s) {
    return [...new Set(String(s).split(/[,; ]+/).map(Number).filter((v) => isFinite(v) && v > 0))].sort((a, b) => a - b);   // sin radios repetidos
  }

  /* ---------------- Geometría del collar, el rebaje de la mesa y el radio interior de la interfaz ---------------- */
  // Radio interior real del anillo de contacto: el collar (Ø D_boss), el rebaje del cubo y de la plancha inferior (Ø D_boss + 2·c_boss_r) y el agujero de los discos
  // ocupan hasta D_boss/2 + c_boss_r; más un margen de borde m_ri. Sin collar el borde es el del buje (D_piv/2 + 15).
  const riOf = (P) => P.h_boss > 0 ? P.D_boss / 2 + P.c_boss_r + P.m_ri : P.D_piv / 2 + 15;
  // Rebaje del collar en la mesa. delta = altura que la interfaz suma bajo la mesa (la cara inferior de la plancha inferior queda a t_base + δ sobre el piso).
  // El collar sube h_boss sobre la base, de modo que sobresale h_boss − δ de la cara inferior; con la holgura axial, el rebaje mide h_boss − δ + c_boss_a desde esa cara
  // (negativo: el collar queda bajo la mesa y no hay rebaje). La plancha inferior lleva un agujero pasante Ø D_boss + 2·c_boss_r (un bolsillo menos profundo que t_bot dejaría un labio de pocos mm);
  // si el rebaje es más profundo que t_bot, el resto se rebaja en el cubo.
  function hubGeo(P, delta) {
    const wg = woodGeo(P), d_bush = P.D_piv + 30, hw = wg ? wg.hw_reb : P.h_disc - P.t_top - P.t_bot, collar = P.h_boss > 0;   // W: el cubo llega a la plancha rebajada
    const hRaw = P.h_boss - (delta || 0) + P.c_boss_a, hRec = collar ? Math.max(0, hRaw) : 0;
    const Drb = collar ? Math.max(P.D_boss + 2 * P.c_boss_r, d_bush) : d_bush;
    return { d_bush, hw, delta: delta || 0, Drb, hRaw: collar ? hRaw : 0, hRec, hPl: hRec > 0 ? P.t_bot : 0, hHub: Math.min(Math.max(0, hRec - P.t_bot), hw), Ri: riOf(P),
      wall: (P.D_hub - Drb) / 2 };   // pared del cubo (y ligamento de la plancha) junto al rebaje
  }

  /* ---------------- Cubierta de madera W: mesa con rebaje (decisión del mandante, 08-11-2026) ----------------
     Anillo superior R_reb…R (la plancha superior actual en esa zona; se fabrica en una pieza de espesor máx(t_pr, t_top) desde R_reb, con los N_pin pasadores),
     pared cilíndrica R_reb…R_reb + t_pared entre la cara superior de la plancha rebajada y la cara inferior del anillo, plancha rebajada continua t_reb
     (Ø hole_top … R_reb + t_pared + w_pared + 5) con su cara superior t_madera bajo la cara superior de la mesa, y tablones enrasados con el anillo.
     Las almas y nervios dentro de R_reb + t_pared pierden d_rebaje = t_madera + t_reb − t_top de altura (llegan a la cara inferior de la plancha rebajada);
     los nervios terminan en el alma de R_reb (R_nervio = R_reb). Cotas z desde la cara inferior de la mesa. */
  const ISO4762_L = [16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100];
  const ISO7093 = { 6: [18, 1.6], 8: [24, 2], 10: [30, 2.5], 12: [37, 3], 14: [44, 3], 16: [50, 3] };   // arandela ancha: Ø exterior y espesor
  // Franjas de tablones paralelos a x (ancho b, junta j) dentro del círculo R_w, con la abertura R_ab de la tapa de inspección. Disposición simétrica
  // (tablón centrado o junta centrada: la que deje los tablones de borde más anchos). Área exacta con F(R, y) = y·√(R² − y²) + R²·asen(y/R) = 2∫₀^y √(R² − s²) ds.
  function plankLayout(Rw, Rab, b, j, d, sMax) {
    const F = (R, y) => { if (!(R > 0)) return 0; const yc = Math.max(-R, Math.min(R, y)); return yc * Math.sqrt(R * R - yc * yc) + R * R * Math.asin(yc / R); };
    const lay = (odd) => {
      const out = [], p = b + j, y00 = odd ? -b / 2 : j / 2;
      for (let k = -Math.ceil(Rw / p) - 2; k <= Math.ceil(Rw / p) + 2; k++) {
        const y0 = y00 + k * p, y1 = y0 + b, a0 = Math.max(y0, -Rw), a1 = Math.min(y1, Rw);
        if (a1 - a0 > 1e-9) out.push([a0, a1]);
      }
      return out;
    };
    const L1 = lay(true), L0 = lay(false), wOf = (L) => Math.min(L[0][1] - L[0][0], L[L.length - 1][1] - L[L.length - 1][0]);
    const sel = wOf(L1) >= wOf(L0) ? L1 : L0;
    const eEnd = 7 * d, eEdge = Math.max(4 * d, 40), pos = [];
    const lista = sel.map(([y0, y1], i) => {
      const yMin = y0 <= 0 && y1 >= 0 ? 0 : Math.min(Math.abs(y0), Math.abs(y1)), yMax = Math.max(Math.abs(y0), Math.abs(y1));
      const xe = Math.sqrt(Math.max(0, Rw * Rw - yMax * yMax));   // extremo exterior más corto (borde más alejado del centro)
      const corte = yMax <= Rab ? "abertura" : (yMin < Rab ? "muesca" : null);
      const xi = corte ? Math.sqrt(Math.max(0, Rab * Rab - yMin * yMin)) : 0;   // fondo de la abertura o de la muesca (sobre el borde más cercano al centro)
      const piezas = corte === "abertura" ? [{ x0: -Math.sqrt(Rw * Rw - yMin * yMin), x1: -Math.sqrt(Math.max(0, Rab * Rab - yMax * yMax)) }, { x0: Math.sqrt(Math.max(0, Rab * Rab - yMax * yMax)), x1: Math.sqrt(Rw * Rw - yMin * yMin) }]
        : [{ x0: -Math.sqrt(Rw * Rw - yMin * yMin), x1: Math.sqrt(Rw * Rw - yMin * yMin) }];
      const w = y1 - y0, ys = w >= 2 * eEdge + 4 * d ? [y0 + eEdge, y1 - eEdge] : [(y0 + y1) / 2];   // 2 tornillos por fila si caben (a4 ≥ 4d al borde, a2 ≥ 4d entre ellos)
      // filas de tornillos por pieza entre extremos a ≥ 7d del corte (sobre el borde más desfavorable: el más corto) y a ≤ s_máx
      const segs = corte === "abertura" ? [[-xe, -xi], [xi, xe]] : corte === "muesca" ? [[-xe, -xi], [xi, xe]] : [[-xe, xe]];
      let nT = 0;
      segs.forEach(([u0, u1]) => {
        const Lu = (u1 - u0) - 2 * eEnd;
        const nR = Lu <= 0 ? 1 : Math.max(2, Math.ceil(Lu / sMax) + 1), xs = nR === 1 ? [(u0 + u1) / 2] : Array.from({ length: nR }, (_, k) => u0 + eEnd + Lu * k / (nR - 1));
        xs.forEach((x) => ys.forEach((y) => { pos.push([x, y]); nT++; }));
      });
      const area = (F(Rw, y1) - F(Rw, y0)) - (F(Rab, y1) - F(Rab, y0));
      return { i: i + 1, y0, y1, ancho: w, largo: 2 * Math.sqrt(Rw * Rw - yMin * yMin), corte, piezas, area, n_tornillos: nT, extremos: "arco R_tablones (corte curvo)" };
    });
    return { b, j, n: lista.length, lista, n_piezas: lista.reduce((s2, t) => s2 + t.piezas.length, 0), area_neta: lista.reduce((s2, t) => s2 + t.area, 0), posiciones: pos, e_extremo: eEnd, e_borde: eEdge };
  }
  function woodGeo(P) {
    if (!(P.opt_wood > 0.5)) return null;
    const tW = P.t_wood, tReb = P.t_reb > 0 ? P.t_reb : P.t_top, tPar = P.t_pared > 0 ? P.t_pared : P.t_top, tAn = Math.max(P.t_pr, P.t_top);
    const Rt = P.D_top / 2, Rreb = P.R_reb, Rpar = Rreb + tPar, RrebExt = Rpar + P.w_pared + 5, hole = P.D_piv + 80, Dins = P.D_piv + 120;
    const hw = P.h_disc - P.t_top - P.t_bot, dRec = tW + tReb - P.t_top, hwReb = hw - dRec, hwAn = P.h_disc - tAn - P.t_bot;
    const Rw = Rreb - P.c_mad, Rab = Dins / 2 + P.c_mad;
    const tab = plankLayout(Rw, Rab, P.b_tab, P.j_tab, P.d_tmad, P.s_tmad);
    // fijación: ISO 4762 Md en cajeado (cabeza 3 mm bajo la superficie) con arandela ISO 7093; taladro ciego en la plancha rebajada (remanente 3 mm, la caja queda cerrada),
    // rosca útil = profundidad − 4 (punta de la broca y salida del macho, como cad/geom.py); engrane ≥ 1,0·d y punta ≥ 2 mm antes del fin de la rosca útil
    const d = P.d_tmad, aw = ISO7093[d] || [3 * d, 0.25 * d], hCaj = d + aw[1] + 3, tRest = tW - hCaj, pT = tReb - 3, lR = pT - 4;
    const Lok = ISO4762_L.filter((L) => L - tRest >= d - 1e-9 && L - tRest <= lR - 2 + 1e-9), Lsel = Lok.length ? Math.max(...Lok) : null;
    const fij = { tipo: "ISO 4762 M" + d + " clase 8.8 galvanizado en caliente (o A4-70) con arandela ancha ISO 7093 en cajeado; roscado en taladro ciego de la plancha rebajada", d, L: Lsel,
      d_arandela: aw[0], h_arandela: aw[1], D_cajeado: aw[0] + 4, h_cajeado: hCaj, t_bajo_arandela: tRest, prof_taladro: pT, rosca_util: lR, broca: d <= 6 ? 5 : d <= 8 ? 6.8 : d <= 10 ? 8.5 : d <= 12 ? 10.2 : d <= 14 ? 12 : 14,
      engrane: Lsel != null ? Lsel - tRest : NaN, n_total: tab.posiciones.length, posiciones: tab.posiciones, e_extremo: tab.e_extremo, e_borde: tab.e_borde, s_max: P.s_tmad,
      apriete_kN: 0.8 * P.p_wood * Math.PI / 4 * (aw[0] ** 2 - (d + 0.5) ** 2) / 1e3 };
    fij.par_Nm = 0.2 * fij.apriete_kN * 1e3 * d / 1e3;
    const almas = parseRings(P.rings).map((r) => { const inn = r <= Rpar + 0.5; return { r, h: inn ? hwReb : hwAn, recortada: inn, t: P.t_web }; });
    const aPins = P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const masas = { anillo: RHO * (Math.PI * (Rt * Rt - Rreb * Rreb) - aPins) * tAn, pared: RHO * Math.PI * (Rpar * Rpar - Rreb * Rreb) * Math.max(0, tW - tAn), plancha_rebajada: RHO * Math.PI * (RrebExt * RrebExt - (hole / 2) ** 2) * tReb,
      tablones: P.rho_wood * 1e-9 * tW * tab.area_neta };
    return { t_madera: tW, R_rebaje: Rreb, t_reb: tReb, t_pared: tPar, t_anillo: tAn, w_pared: P.w_pared, c_mad: P.c_mad, R_pared_ext: Rpar, R_reb_ext: RrebExt, R_anillo_int: Rreb, R_ext: Rt,
      h_pared: tW - tAn, h_c: tW + tReb / 2 - tAn / 2, d_rebaje: dRec, hw: hw, hw_reb: hwReb, hw_anillo: hwAn, R_tablones: Rw, R_abertura: Rab, D_tapa_insp: Dins, hole_top: hole,
      z: { sup: P.h_disc, reb_sup: P.h_disc - tW, reb_inf: P.h_disc - tW - tReb, anillo_inf: P.h_disc - tAn, almas_reb_sup: P.h_disc - tW - tReb, nota: "cotas desde la cara inferior de la mesa (sumar t_base + δ para el piso)" },
      almas, nervios: { R_ext: P.R_rib, h: hwReb, sin_cambio_altura: P.R_rib <= Rpar + 0.5, nota: "los nervios llegan al alma de R_reb bajo la plancha rebajada" },
      soldaduras: {
        J1: { union: "anillo–pared", tipo: "PJP en bisel simple 45° desde el lado del rebaje (S = t_pared/2, E = S − 3 mm, AISC 360-22 Tabla J2.1) + filete exterior de refuerzo bajo el anillo", S: Math.ceil(tPar / 2), E: Math.ceil(tPar / 2) - 3, w: P.w_pared, largo: 2 * Math.PI * Rreb },
        J2: { union: "pared–plancha rebajada", tipo: "filete a ambos lados (interior bajo la holgura de los tablones, exterior antes de cerrar la caja)", w: P.w_pared, largo: 2 * Math.PI * Rreb + 2 * Math.PI * Rpar },
        secuencia: "1) pared a la plancha rebajada (J2, ambos lados); 2) anillo sobre la pared (J1: PJP desde el rebaje y filete exterior, con la subpieza invertida y la zona R_pared…R abierta); 3) almas, nervios y cubo; 4) plancha inferior" },
      tapas: { D_tapa_insp: Dins, asiento: "rebaje de la tapa de inspección y alojamiento de la tapa retenedora en la plancha rebajada (misma pila que en la plancha superior: 3 + tapa retenedora + 1 + tapa de inspección ≤ t_reb)", abertura_tablones: 2 * Rab },
      tablones: tab, fijacion: fij, masas, drenaje: "PENDIENTE: el rebaje es una bandeja; definir tubos de drenaje desde el fondo del rebaje al canto exterior de la mesa (supuesto por confirmar)" };
  }
  // JSON de diseño (tools/export_design.js y packages/web/planos_export.js): geometría de fabricación de la cubierta W y resumen del FEA escalonado; null sin cubierta
  function designWood(P, A) {
    const g = woodGeo(P); if (!g) return null;
    const f = A && A.fea, e = f && f.top && f.top.escalon;
    return Object.assign({ modelo: "W: anillo superior + pared cilíndrica + plancha rebajada + tablones enrasados (decisión del mandante, 08-11-2026)", altura_total_sin_cambio: true }, g,
      { fea: e ? { variantes: e.variantes, s_pared: e.sPared, s_anillo: e.sAnillo, linea_reb: e.lineaReb, linea_pared_sup: e.lineaParedSup, gobierna: e.gobierna, vm_reb: f.top.vmMax, w_reb: f.top.wMax, hc_glob: f.glob.hcTop, Mr_glob_reb: f.glob.MrReb } : null });
  }
  const topUnder = (P) => { const g = woodGeo(P); return g ? P.h_disc - g.t_madera - g.t_reb : P.h_disc - P.t_top; };   // cara inferior de la plancha sobre el cubo (pivote, buje, tapas)

  /* ---------------- Masas ---------------- */
  function massesMesa(P, delta) {
    const rings = parseRings(P.rings);
    const hw = P.h_disc - P.t_top - P.t_bot;
    const Rt = P.D_top / 2, r_hub = P.D_hub / 2, d_bush = P.D_piv + 2 * 15, hg = hubGeo(P, delta), wg = woodGeo(P);
    // planchas: disco central + anillo de pasadores (agujeros de pasadores en todo el espesor del anillo)
    const rpr = prIn(P), aRing = Math.PI * (Rt * Rt - rpr * rpr) - P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const hole_top = P.D_piv + 80;                                       // alojamiento de la tapa retenedora
    const m = {};
    // W: piel superior escalonada = anillo superior (t = máx(t_pr, t_top) desde R_reb) + pared cilíndrica + plancha rebajada (en m.top: la lista de materiales la suma como «plancha superior»)
    m.top = wg ? wg.masas.anillo + wg.masas.pared + wg.masas.plancha_rebajada : RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * hole_top ** 2) * P.t_top + aRing * Math.max(P.t_pr, P.t_top));
    m.bot = RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * d_bush ** 2) * P.t_bot + aRing * Math.max(P.t_pr, P.t_bot) - Math.PI / 4 * (hg.Drb ** 2 - d_bush ** 2) * hg.hPl);   // agujero del buje y rebaje del collar (Ø D_boss + 2·c_boss_r, profundidad hPl)
    m.webs = RHO * (wg ? wg.almas.reduce((s, a) => s + 2 * Math.PI * a.r * a.h * P.t_web, 0) : rings.reduce((s, r) => s + 2 * Math.PI * r * hw * P.t_web, 0));
    if (wg) {   // nervios: tramo dentro de R_pared con la altura reducida y el resto (si R_nervio > R_pared) con la del anillo
      const Rp = wg.R_pared_ext, rIn = Math.min(P.R_rib, Rp), nIn = rings.filter((r) => r > r_hub && r < Math.min(P.R_rib, Rp)).length, nOut = rings.filter((r) => r >= Rp && r < P.R_rib).length;
      m.ribs = RHO * P.N_rib * (Math.max(0, rIn - r_hub - nIn * P.t_web) * wg.hw_reb + Math.max(0, P.R_rib - Rp - nOut * P.t_web) * wg.hw_anillo) * P.t_rib;
    } else {
      const ringsIn = rings.filter((r) => r > r_hub && r < P.R_rib).length;
      m.ribs = RHO * P.N_rib * Math.max(0, P.R_rib - r_hub - ringsIn * P.t_web) * hw * P.t_rib;
    }
    m.hub = RHO * Math.PI / 4 * (Math.max(0, P.D_hub ** 2 - d_bush ** 2) * hg.hw - Math.max(0, hg.Drb ** 2 - d_bush ** 2) * hg.hHub);   // rebaje del collar: solo la parte que pasa de la plancha inferior (h_collar − δ + c_boss_a − t_bot); W: cubo bajo la plancha rebajada
    m.pins = RHO * P.N_pin * Math.PI / 4 * P.d_pin ** 2 * P.h_disc;
    // W: tablones (área neta de las piezas, sin juntas ni la abertura de la tapa); el anillo de contención 10×50 de la versión anterior se eliminó (m.ring = 0, clave conservada)
    m.wood = wg ? wg.masas.tablones : 0;
    m.ring = 0;
    m.disc = m.top + m.bot + m.webs + m.ribs + m.hub + m.pins + m.wood + m.ring;
    return m;
  }

  /* ---------------- Interfaz de giro: acero–acero (por defecto), discos inoxidables (A) o discos + UHMW (B) ---------------- */
  function ifOpt(P) { return P.opt_bz > 0.5 ? 3 : (P.opt_uhmw > 0.5 ? 2 : (P.opt_ss > 0.5 ? 1 : 0)); }
  function muSet(P) {
    const o = ifOpt(P);
    if (o === 1) return { nom: P.muA_nom, d: P.muA_d, cont: P.muA_cont, dry: P.muA_dry };
    if (o === 2) return { nom: P.muB_nom, d: P.muB_d, cont: P.muB_cont, dry: P.muB_dry };
    if (o === 3) return { nom: P.muC_nom, d: P.muC_d, cont: P.muC_cont, dry: P.muC_dry };
    return { nom: P.mu_nom, d: P.mu_d, cont: P.mu_cont, dry: P.mu_dry };
  }
  // Ranuras de engrase: área perdida y volumen de grasa para llenarlas
  function grooveFrac(P) {
    if (!(P.h_gr > 0)) return { Ag: 0, f: 0, V: 0 };
    const Ro = P.D_top / 2, Ri = riOf(P), rm = (Ro + Ri) / 2, Ac = Math.PI * (Ro * Ro - Ri * Ri);
    const Ag = P.w_gr * (P.n_gr_rad * (Ro - Ri) + P.n_gr_circ * 2 * Math.PI * rm);
    return { Ag, f: Math.min(0.9, Ag / Ac), V: Ag * P.h_gr / 1000 };   // V en cm³
  }
  const commercial = (list, t) => list.find((v) => v >= t - 1e-9) || Math.ceil(t);
  // Presión máxima de contacto con la masa rotatoria adicional mTop (kg): misma distribución lineal que compute()
  function ifaceLoad(P, mTop, dl) {   // dl: δ estimada (discos ya elegidos) para la masa del rebaje de la mesa; la diferencia es < 0,2 % de la masa de la mesa
    const m = massesMesa(P, dl), Ro = P.D_top / 2, Ri = riOf(P);
    const mPiv = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + topUnder(P) + 3);
    const ND = P.phi_d * P.W_tf * G + (m.disc + mTop + mPiv * 0.5) * G / 1e3;
    const Ac = Math.PI * (Ro * Ro - Ri * Ri), kq = 4 * P.e * Ro / (Ro * Ro + Ri * Ri);
    return { Ac, Ro, Ri, ND, q_avg: ND * 1e3 / Ac, q_max: ND * 1e3 / Ac * (1 + kq) };
  }
  // Lámina delgada de UHMW: el módulo aparente sube con el factor de forma S = D/(4t) (D = ventana del defecto) y se acota por el módulo
  // confinado M = E(1−ν)/((1+ν)(1−2ν)), ν = 0,45:  E_c = E·[1 + (M/E − 1)·S²/(1+S²)].  Espesor mínimo: t = E_c(t)·δ/(p_adm − q), por bisección.
  function uhConf(P, q) {
    const nu = 0.45, Mf = (1 - nu) / ((1 + nu) * (1 - 2 * nu));
    const Ec = (t) => { const S = P.ss_void / (4 * t), f = S * S / (1 + S * S); return P.E_uhmw * (1 + (Mf - 1) * f); };
    if (!(P.p_uhmw > q)) return { t: Infinity, Ec, S: (t) => P.ss_void / (4 * t) };
    const k = P.d_flat / (P.p_uhmw - q);
    let lo = 0.5, hi = 1000;
    for (let i = 0; i < 90; i++) { const mid = (lo + hi) / 2; if (mid - Ec(mid) * k >= 0) hi = mid; else lo = mid; }
    return { t: hi, Ec, S: (t) => P.ss_void / (4 * t) };
  }
  // Geometría del tope soldado (fijación desmontable). La barra de altura h_barra = t − a_sup se alza desde el respaldo hasta a_sup bajo la superficie de
  // deslizamiento; el filete delantero (cara cargada) ocupa un triángulo w × w en la base, que el canto del sector libra con un chaflán de a_inf = w + 1 mm.
  // El contacto útil es h_c = t − a_sup − a_inf y la resultante del aplastamiento queda a z = a_inf + h_c/2 del respaldo.
  const stopAInf = (P) => P.a_inf > 0 ? P.a_inf : P.w_tope + 1;
  const tStopMin = (P) => P.a_sup + stopAInf(P) + P.hc_min;        // espesor mínimo del sector para que el tope sea realizable
  const wMin = (T) => T <= 6 ? 3 : T <= 12 ? 5 : T <= 20 ? 6 : 8;   // AWS D1.1/D1.1M:2020 Tabla 7.7: filete mínimo según la parte más gruesa (AISC Tabla J2.4 lo da por la más delgada: nunca mayor)
  const wMax = (t) => t < 6 ? t : t - 2;                            // AISC 360-22 J2.2b: filete máximo a lo largo del borde de una placa de espesor t (t < 6: t; t ≥ 6: t − 2 mm)
  const ePivEff = (P) => Math.max(P.e_piv, P.g_bush + P.L_bush / 2);  // brazo efectivo de flexión del pivote: holgura del buje sobre el collar + L_buje/2 (e_piv de ingreso es un mínimo)
  const stopGeo = (P, t) => { const hB = t - P.a_sup, hC = hB - stopAInf(P), hCe = Math.max(hC, 0); return { hB, hC, hCe, z: stopAInf(P) + hCe / 2 }; };
  // MPa: corte + tracción del filete cargado por el par F·z (z = a_inf + h_c/2: la resultante del aplastamiento está sobre la base del contacto, no a t/2)
  const weldStop = (P, F, L, z) => { const aw = 0.707 * P.w_tope; return Math.hypot(F * 1e3 / (2 * aw * L), F * 1e3 * z / (P.b_tope * aw * L)); };
  // Discos de la opción A/B: disco de la base (liso) y disco de la mesa (con ranuras de engrase en A); se funden en uno si son iguales y sin ranura
  function discList(P, I) {
    const d = [{ id: "disc0", n: "Disco de la base (liso)", t: I.tss, req: I.tssReq, g: 0, resp: P.t_base }, { id: "disc1", n: I.gr > 0 ? "Disco de la mesa (con ranuras de engrase)" : "Disco de la mesa", t: I.tss2, req: I.tss2Req, g: I.gr, resp: P.t_bot }];
    if (I.tss === I.tss2 && I.gr === 0) { d.pop(); d[0].resp = Math.max(P.t_base, P.t_bot); }   // plancha a la que se sueldan los topes: base, fondo de la mesa o la mayor si son iguales
    return d;
  }
  // Largo de un tope: el mayor entre aplastamiento (con h_c − tol_hc) y soldadura, con FU objetivo 0,90, a múltiplos de 5 mm (o congelado a 20 °C en el escenario térmico, o L_tope manual).
  // Lo comparten stopsOf() (dimensionamiento) e ifaceDesignBz() (largo de la muesca que excluye tapones): una sola fuente.
  function stopLenOf(P, id, t, FyP, Fst, Lav) {
    const Nd = P.Nd, Fw = P.FEXX * 0.60 / (1.20 * Nd), g = stopGeo(P, t), adm = 1.25 * Math.min(FyP, P.Fy) / Nd;   // el menor Fy entre el canto del sector y la barra
    const hCd = g.hC - P.tol_hc, LreqB = hCd > 0 ? Fst * 1e3 / (adm * hCd) : Infinity, LreqW = weldStop(P, Fst, 1, g.z) / Fw, Lreq = Math.max(LreqB, LreqW);
    const Lz = P.__th && P.__th.frozen && P.__th.frozen.L[id];                                   // largo congelado a 20 °C (escenario térmico)
    const L = Lz > 0 ? Lz : P.L_tope > 0 ? P.L_tope : (isFinite(Lreq) ? Math.ceil(Lreq / 0.9 / 5) * 5 : Lav);
    return { L, Lreq, adm };
  }
  // Geometría resuelta y dimensionamiento de cada tope soldado (fijación desmontable) con el par de calado de R; la usan la masa (m.stopBars) y las verificaciones
  function stopsOf(P, R) {
    const I = R.ifc, out = [];
    if (!(I.o > 0) || !(P.fix_mode < 1.5)) return out;
    const Nd = P.Nd, Fw = P.FEXX * 0.60 / (1.20 * Nd), aInf = stopAInf(P);
    const Ftot = (R.TmaxTopes || R.Tmax) / (R.r_u / 1000), kpk = R.q_max / R.q_avg, Lav = R.Ro - R.Ri - 100;   // kN en el radio de fricción (T_calado; en el pivotado, la cota colineal de tmaxOf, mayor que la del empuje guiado, como en ifaceDesign); sector más cargado; canto radial disponible (mm)
    const push = (o) => {
      const g = stopGeo(P, o.t), Tw = Math.max(P.b_tope, o.tResp), rho = o.uh ? RHO_SS : RHO, mB = g.hB > 0 && isFinite(o.L) ? rho * o.L * P.b_tope * g.hB : 0;   // las barras del rebaje de la lámina UHMW son de acero inoxidable (7,93)
      out.push(Object.assign(o, { pieza: o.nombre, a_sup: P.a_sup, a_inf: aInf, h_barra: g.hB, h_c: g.hC, h_c_min: P.hc_min, tol_hc: P.tol_hc, z: g.z, w_tope: P.w_tope, b_tope: P.b_tope, w_min: wMin(Tw), Tw, Lav, rho_barra: rho, m_barra: mB, m_barras: o.capas * o.n * mB }));
    };
    const sized = (id, grp, nombre, n, t, FyP, tResp, allow, capas) => {
      const Fst = Ftot / n * kpk, sl = stopLenOf(P, id, t, FyP, Fst, Lav);
      push({ id, grp, nombre, n, t, tResp, allow, capas: capas || 1, F: Fst, L: sl.L, Lreq: sl.Lreq, adm: sl.adm, uh: false });
    };
    if (I.o === 1 || I.o === 2) {
      const discs = discList(P, I);
      discs.forEach((d) => sized(d.id, "Interfaz inox", d.n + " (" + P.n_sec + " sectores)", P.n_sec, d.t, P.Fy_ss, d.resp, P.ss_allow, discs.length === 1 ? 2 : 1));
    }
    if (I.o === 2) {      // rebaje del sector UHMW: el tope se suelda al disco de la base; la fuerza es el arrastre con el μ máximo y el largo es el canto disponible
      const Fdrag = Math.max(R.mu.d, R.mu.cont, R.mu.dry) * R.N, dist = P.life * P.turns_yr * 2 * Math.PI * P.r_ef / 1000, wear = P.k_wear * 1e-7 * I.q * dist;
      push({ id: "uhmw", grp: "Interfaz inox", nombre: "Lámina UHMW (" + P.n_seg + " sectores)", n: P.n_seg, t: I.tuh, tResp: I.tss, allow: wear, capas: 1, F: Fdrag / P.n_seg * kpk, L: Lav, Lreq: Lav, adm: P.p_uhmw, uh: true });
    }
    if (I.o === 3) {
      const nB = I.conf === 3 ? P.bz_npad : P.n_sec, FyC2 = I.conf === 2 ? P.Fy_bz2 : P.Fy_cara;
      sized("bz0", "Interfaz bronce", (I.conf === 3 ? "Pastillas de bronce (" : "Placa de bronce (") + nB + (I.conf === 3 ? " pastillas)" : " sectores)"), nB, I.tbz, P.Fy_bz, P.t_base, P.bz_allow);   // placa de bronce soldada a la base
      sized("bz1", "Interfaz bronce", (I.conf === 2 ? "2.ª placa de bronce" : "Disco duro") + " (" + P.n_sec + " sectores)", P.n_sec, I.tss, FyC2, P.t_bot, I.conf === 2 ? P.bz_allow : P.ss_allow);   // disco duro o 2.ª placa soldados al fondo de la mesa
    }
    return out;
  }
  // Material que el 3D real quita a las coronas de la interfaz (4.ª pasada); R.m.ss, R.m.uhmw y R.m.bz son netos y R.ifc.mSS/mUH/mBz la corona bruta.
  // Por sector (mm³):  V_junta = j·(R_o − R_i)·t  (junta en frío con el sector vecino; en la lámina UHMW la franja libre entre sectores es (b_tope + j)·(R_o − R_i)·t porque la barra del rebaje va dentro);
  //                    V_muesca = (b_tope + 2)·L_tope·t  (muesca pasante de la barra, 1 mm de holgura por lado; no hay en la lámina UHMW: su rebaje es la franja; con pegado, fix_mode = 2, no hay barras ni muescas ni chaflanes);
  //                    V_chaflán = a_inf²·L_tope  (chaflán 45° de cateto a_inf: a_inf²/2 por canto, en los DOS cantos de la muesca, porque el par se invierte con el sentido de giro).
  // La junta es j = máx(j_sec; (α − α_acero)·ΔT·cuerda) redondeada hacia arriba a 0,1 mm. Las pastillas de bronce (conf. 3) ya llevan sus juntas en la fracción de cobertura.
  // No se descuentan los tornillos de posición, las ranuras y graseras ni la distribución de tapones de grafito (conservador, < 0,2 % de la masa total).
  function cortesOf(P, R) {
    const I = R.ifc, out = [];
    if (!(I.o > 0)) return out;
    const Ro = R.Ro, Ri = R.Ri, rem = P.fix_mode < 1.5, aInf = stopAInf(P), top = (id) => (I.topes || []).find((x) => x.id === id);
    const jOf = (al, n) => jointOf(P, al, n);
    const add = (o) => {
      const tp = top(o.id), L = rem && tp ? tp.L : 0, cov = o.cov || 1;
      const j = o.joint ? jOf(o.alpha, o.n) : 0;
      const Vj = o.joint ? (o.strip && rem ? P.b_tope + j : j) * (Ro - Ri) * o.t : 0, Vn = rem && !o.strip ? (P.b_tope + 2) * L * o.t : 0, Vc = rem ? aInf * aInf * L : 0;
      const mB = o.rho * o.capas * I.A_ss * cov * o.t, mD = o.rho * o.capas * o.n * (Vj + Vn + Vc);
      if (mD > 0) out.push({ id: o.id, pieza: o.pieza, tgt: o.tgt, rho: o.rho, n: o.n, capas: o.capas, t: o.t, L, j, strip: !!o.strip, V_junta: Vj, V_muesca: Vn, V_chaflan: Vc, V_sector: Vj + Vn + Vc, m_bruta: mB, m_desc: mD, m_neta: mB - mD });
    };
    if ((I.o === 1 || I.o === 2) && rem) {
      const discs = discList(P, I);
      discs.forEach((d) => add({ id: d.id, pieza: (top(d.id) || {}).pieza || d.n, tgt: "ss", rho: RHO_SS, n: P.n_sec, capas: discs.length === 1 ? 2 : 1, t: d.t, joint: true, alpha: AL_SS }));
    }
    if (I.o === 2) add({ id: "uhmw", pieza: (top("uhmw") || {}).pieza || "Lámina UHMW (" + P.n_seg + " sectores)", tgt: "uhmw", rho: RHO_UH, n: P.n_seg, capas: 1, t: I.tuh, joint: true, strip: true, alpha: AL_UH });
    if (I.o === 3 && rem) {
      const nB = I.conf === 3 ? P.bz_npad : P.n_sec;
      add({ id: "bz0", pieza: (top("bz0") || {}).pieza || "Placa de bronce", tgt: "bz", rho: I.rhoPl, n: nB, capas: 1, t: I.tbz, joint: I.conf !== 3, alpha: AL_BZ, cov: I.cov });
      add({ id: "bz1", pieza: (top("bz1") || {}).pieza || "Disco duro", tgt: I.conf === 2 ? "bz" : "ss", rho: I.conf === 2 ? I.rhoSolid : RHO_SS, n: P.n_sec, capas: 1, t: I.tss, joint: true, alpha: I.conf === 2 ? AL_BZ : AL_SS });
    }
    return out;
  }
  /* ---------------- Tapones de grafito: cuenta determinista de los tapones que caben (opción C) ---------------- */
  // Junta en frío entre sectores contiguos: la mayor entre j_sec y la dilatación diferencial a ΔT de diseño, redondeada hacia arriba a 0,1 mm
  const jointOf = (P, al, n) => Math.ceil(Math.max(P.j_sec, (al - AL_S) * P.dT * 2 * (P.D_top / 2) * Math.sin(Math.PI / n)) * 10 - 1e-9) / 10;
  const ISO10642_DK = { 4: 8, 5: 10, 6: 12, 8: 16, 10: 20, 12: 24 };            // Ø de la cabeza avellanada (mm), ISO 10642
  const dkOf = (P) => ISO10642_DK[Math.round(P.d_tor)] || 2 * P.d_tor;
  const ISO10642_K = { 3: 1.86, 4: 2.48, 5: 3.1, 6: 3.72, 8: 4.96, 10: 6.2, 12: 7.44, 14: 8.4, 16: 8.8, 20: 10.16 };   // altura máxima de la cabeza avellanada (mm), ISO 10642
  const isoK = (d) => ISO10642_K[Math.round(d)] || 0.62 * d;
  const isoDk = (d) => ISO10642_DK[Math.round(d)] || ({ 14: 27, 16: 30, 20: 36 })[Math.round(d)] || 2 * d;
  // AF2 (opción A pegada, fix_mode = 2): tornillos avellanados ISO 10642 10.9 del disco de la mesa a la mesa. El par de diseño T se reparte en n tornillos sobre el radio r:
  // V = T/(n·r). Rediseño 10-11-2026: el círculo de tornillos va en la corona de pasadores (r = R_pin por defecto) INTERCALADO con los N_pin pasadores (pasadores en
  // (k + ½)·360°/N, tornillos en k·360°/N, a mitad de camino entre dos pasadores) y se omiten las posiciones cuya cabeza tocaría una ranura radial de engrase.
  // La rosca cae en la pieza real: el anillo inferior de pasadores (MES-004, t_pr) si r − d/2 > R_anillo,int (taladro ciego con remanente 3 mm: la punta no asoma a la
  // luz entre anillos por donde pasa el bloque-uña), o la plancha inferior (pasante). Corte AISC J3.7; aplastamiento J3.11 en el disco (t − k/2) y en la pieza roscada
  // (largo enganchado); separación J3.4 (3d entre tornillos y ligamento equivalente al agujero del pasador); borde J3.4M (agujero del pasador tratado como borde,
  // borde exterior y borde interior del anillo); engrane ≥ 1,25d (VDI 2230, 10.9 en S355, criterio del registro).
  // Pasadores de posición de la placa-guía (ISO 8734, m6 en H7 escariado): alojamientos ciegos en la base (cara superior) y en la placa (cara inferior) con remanente
  // ≥ 3 mm y 2 mm de fondo libre bajo la punta; enganche ≥ 1,5·d en cada pieza (criterio de diseño de pasadores de posición, registro); largo = el menor de la serie
  // ISO 8734 que aprovecha todo el alojamiento posible en la base (l_b = t_base − 3 − 2) y deja ≥ 1,5·d en la placa.
  const ISO8734_L = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100];
  function dowelGeo(P) {
    const d = P.pv_dd, lmin = 1.5 * d, rem = 3, fondo = 2, lbMax = P.t_base - rem - fondo, lpMax = P.pv_tcam - rem - fondo;
    const lb = Math.max(0, Math.min(lbMax, lpMax)), L = ISO8734_L.find((x) => x - lb >= lmin) || ISO8734_L[ISO8734_L.length - 1], lp = Math.min(L - lb, lpMax);
    return { d, L, lmin, lb, lp, lbMax, lpMax, rem, fondo, hb: lb + fondo, hp: lp + fondo, remB: P.t_base - lb - fondo, remP: P.pv_tcam - lp - fondo, designacion: "ISO 8734 – " + d + " m6 × " + L };
  }
  const PITCH = { 6: 1, 8: 1.25, 10: 1.5, 12: 1.75, 14: 2, 16: 2, 20: 2.5, 24: 3 };
  // ISO 286-1:2010 Tabla 1 (IT8, IT9) y desviación fundamental «f» del eje (ISO 286-1 Tabla 2), en mm, por rango de medida nominal (> a … ≤ b)
  const ISO286_R = [3, 6, 10, 18, 30, 50, 80, 120, 180, 250, 315, 400, 500], ISO286_IT = { 8: [14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97], 9: [25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155] }, ISO286_F = [-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68];
  const iso286i = (d) => { const i = ISO286_R.findIndex((b) => d <= b); return i < 0 ? ISO286_R.length - 1 : i; };
  const isoIT = (d, g) => ISO286_IT[g][iso286i(d)] / 1000, isoF = (d) => ISO286_F[iso286i(d)] / 1000;
  function tornillosAF2(P, R) {
    const I = R.ifc;
    if (!(I && I.o === 1 && P.fix_mode > 1.5) || !R.cd) return null;
    const d = P.tor2_d, Ab = Math.PI / 4 * d * d, dh = d + 1, k = isoK(d), dk = isoDk(d), Ro = R.Ro, t = I.tss2, T = R.cd.T, pt = PITCH[Math.round(d)] || 0.15 * d;
    const nr = P.h_gr > 0 ? Math.max(0, Math.round(P.n_gr_rad)) : 0, rOut = P.h_gr > 0 && P.n_gr_circ >= 1 ? Ro - 30 : Ro;
    const r = P.tor2_r > 0 ? P.tor2_r : P.R_pin, N = Math.max(1, Math.round(P.N_pin)), rPin = prIn(P), dP = P.d_pin;
    // posiciones candidatas: bisectrices entre pasadores; la cabeza (Ø d_k) a ≥ 3 mm de las ranuras radiales (ancho w_gr, a q·360°/n_r)
    const latGr = (a) => { let m = Infinity; for (let q = 0; q < nr; q++) { const e = ((a - 360 * q / nr + 540) % 360) - 180; if (Math.abs(e) < 90) m = Math.min(m, r * Math.abs(Math.sin(e * D2R))); } return m; };
    const lim = P.w_gr / 2 + dk / 2 + 3, cand = Array.from({ length: N }, (_, i) => i * 360 / N).filter((a) => latGr(a) >= lim);
    const nAuto = cand.length, nSel = P.tor2_n > 0 ? Math.max(1, Math.min(Math.round(P.tor2_n), nAuto)) : nAuto;
    const ang = nSel === nAuto ? cand : Array.from({ length: nSel }, (_, i) => cand[Math.floor(i * nAuto / nSel)]);
    const pos = ang.map((a) => [r * Math.cos(a * D2R), r * Math.sin(a * D2R)]), n = ang.length;
    let dGap = 360; for (let i = 0; i < n; i++) { let g = ((ang[(i + 1) % n] - ang[i]) % 360 + 360) % 360; if (n === 1) g = 360; dGap = Math.min(dGap, g || 360); }
    const s = 2 * r * Math.sin(Math.min(180, dGap) / 2 * D2R);   // separación mínima entre centros (cuerda)
    // pieza roscada real y engrane
    const enAnillo = r - d / 2 > rPin + 1e-9, tr = enAnillo ? P.t_pr : P.t_bot, rec = 0.5 + P.ss_allow;   // la cabeza queda 0,5 + sobreespesor bajo la cara (verificación del avellanado)
    const hd = enAnillo ? tr - 3 : tr, hu = enAnillo ? hd - 2 * pt : tr;   // taladro ciego con remanente 3 mm; rosca útil = taladro − 2 pasos (filetes incompletos y cono, hipótesis)
    const Ls = [16, 20, 25, 30, 35, 40, 45, 50, 55, 60], le = (L) => L - (t - rec);
    const L = enAnillo ? (Ls.filter((x) => le(x) + 2 <= hu).pop() || Ls[0]) : (Ls.find((x) => x >= t + Math.min(tr, 1.25 * d + 2) - 1) || Math.ceil(t + tr));
    const lEng = enAnillo ? le(L) : tr;
    // pasadores de empuje (en (k + ½)·360°/N sobre R_pin): distancia de cada tornillo al centro del pasador más cercano
    const pins = Array.from({ length: N }, (_, i) => (i + 0.5) * 360 / N).map((a) => [P.R_pin * Math.cos(a * D2R), P.R_pin * Math.sin(a * D2R)]);
    const cbp = Math.min(...pos.map((p) => Math.min(...pins.map((q) => Math.hypot(p[0] - q[0], p[1] - q[1])))));
    const Fnv = 0.45 * P.Fu_bolt, capV = Fnv / 2, V = T * 1e6 / (n * r), te = t - k / 2, lcD = s - dh, lcM = Math.min(s - dh, cbp - dP / 2 - dh / 2);
    const RnD = Math.min(1.2 * lcD * te * P.Fu_ss, 2.4 * d * te * P.Fu_ss), RnM = Math.min(1.2 * lcM * lEng * P.Fu, 2.4 * d * lEng * P.Fu);
    const latR = nr ? Math.min(...ang.map(latGr)) : Infinity;
    return { n, nAuto, V, s, lc: lcD, lcM, te, RnD, RnM, fuV: V / Ab / capV, fuD: V / (RnD / 2), fuM: V / (RnM / 2), d, Ab, dh, k, dk, r, t, tb: tr, T, Fnv, capV, ang, pos, L, rOut, latR, latLim: lim,
      enAnillo, pieza: enAnillo ? "anillo inferior de pasadores (MES-004, e = " + tr + " mm)" : "plancha inferior de la mesa (e = " + tr + " mm)", lEng, hd, hu, rec, cbp, dP, rPin,
      ligPin: cbp - dP / 2 - dh / 2, ePin: cbp - dP / 2, eIn: r - rPin, eOut: Ro - r,
      avellanado: { d_cabeza: dk, prof: k, angulo_deg: 90, bajo_cara: t - k },
      rosca: { d, paso: pt, pieza: enAnillo ? "anillo inferior de pasadores (MES-004)" : "plancha inferior", prof: enAnillo ? hu : tr, pasante: !enAnillo, ciega: enAnillo, prof_taladro: hd, remanente: enAnillo ? tr - hd : 0, engrane: lEng, d_broca: d - pt },
      designacion: "ISO 10642 M" + d + " × " + L + " – 10.9" };
  }
  // Corona de contacto (misma geometría que compute): R_o, R_i, área, radio de fricción r_u y k_q = 4eR_o/(R_o² + R_i²)
  function contactGeo(P) {
    const Ro = P.D_top / 2, Ri = riOf(P);
    return { Ro, Ri, Ac: Math.PI * (Ro * Ro - Ri * Ri), r_u: 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2), kq: 4 * P.e * Ro / (Ro * Ro + Ri * Ri) };
  }
  // Área útil de colocación = corona R_i…R_o menos la franja de borde (bz_edge, medida desde el borde del tapón), las muescas de los topes ((b_tope + 2) × L_tope),
  // los tornillos de posición (cabeza ISO 10642 sobre la bisectriz de cada sector) y las ranuras de engrase (circunferenciales y radiales).
  // Cuenta = centros de la malla escalonada (paso p, fila alterna p·√3/2, anclada al centro de la mesa) que caen en esa área; el mismo patrón S09 del dibujante.
  //   g = { n, radial (pastillas de bordes radiales: C3), span (° de cada pastilla), gap (mm de junta entre sectores paralelos), L (muesca; 0 sin topes), d, p, edge, nTor }
  const plugCache = new Map();
  function plugLayout(P, g) {
    const geo = contactGeo(P), Ri = geo.Ri, Ro = geo.Ro, d = g.d, p = g.p, m = g.edge + d / 2, n = g.n, th = 360 / n, rd = Math.PI / 180;
    const dk = dkOf(P), ru = geo.r_u, hb = (P.b_tope + 2) / 2, L = g.L, nTor = g.nTor;
    const key = [Ri, Ro, d, p, m, n, g.radial ? g.span : 0, g.radial ? 0 : g.gap, L, ru, hb, dk, nTor, P.h_gr > 0 ? [P.w_gr, P.n_gr_rad, P.n_gr_circ, P.R_pin, P.d_pin].join(",") : 0].join("|");
    const hit = plugCache.get(key);
    if (hit) return hit;
    // ranuras circunferenciales: la exterior a R_o − 30 y el resto equiespaciadas hasta R_i + 30 (cad/modelo3d_tt300c.py, S05)
    const rCirc = [];
    if (P.h_gr > 0) {
      const nc = Math.round(P.n_gr_circ);
      if (nc >= 1) rCirc.push(Ro - 30);
      for (let k = 1; k < nc; k++) rCirc.push(Ro - 30 - k * (Ro - 30 - (Ri + 30)) / (nc - 1));
    }
    const wHalf = P.w_gr / 2 + m, nRad = P.h_gr > 0 ? Math.round(P.n_gr_rad) : 0;
    // radios de los dos tornillos de posición sobre la bisectriz: a mitad de camino entre la muesca y cada borde, desplazados si caen sobre una ranura circunferencial
    const radios = [];
    if (L > 0 && nTor > 0) {
      const a = ru - L / 2, b = ru + L / 2, rLim = P.R_pin - P.d_pin / 2 - dk / 2 - 4;
      let c1 = (Ri + a) / 2, c2 = (b + Ro) / 2;
      if (rLim > b + dk) c2 = Math.min(c2, rLim);
      for (const [c, step] of [[c1, -8], [c2, c2 >= rLim - 1e-9 ? -8 : 8]]) {
        let r = c;
        for (let i = 0; i < 60; i++) { if (!rCirc.length || rCirc.every((rg) => Math.abs(r - rg) > P.w_gr / 2 + dk / 2 + 3)) break; r += step; }
        radios.push(r);
      }
    }
    const fL = (g.radial ? g.span : th) / 4 * rd;               // posiciones locales de los tornillos (x, y): 2 sobre la bisectriz o, con 4, 2 radios × 2 lados a ±span/4
    const scr = nTor >= 4 ? radios.flatMap((r) => [[r * Math.cos(fL), r * Math.sin(fL)], [r * Math.cos(fL), -r * Math.sin(fL)]]) : radios.map((r) => [r, 0]);
    const hh = (g.radial ? g.span : th) / 2 * rd, ax = g.radial ? 0 : (g.gap / 2) / Math.sin(hh);
    const rows = Math.floor(Ro / (p * Math.sqrt(3) / 2)) + 2, por = new Array(n).fill(0), pd = { borde: 0, muesca: 0, tornillos: 0, ranCirc: 0, ranRad: 0 };
    let N = 0, nMalla = 0;
    for (let j = -rows; j <= rows; j++) for (let i = -rows; i <= rows; i++) {
      const x = i * p + (((j % 2) + 2) % 2) * p / 2, y = j * p * Math.sqrt(3) / 2, r = Math.hypot(x, y);
      if (r < Ri + m || r > Ro - m) continue;
      nMalla++;
      let ph = Math.atan2(y, x) / rd; if (ph < 0) ph += 360;
      const k = Math.min(n - 1, Math.floor(ph / th + 1e-12)), dd = ph - (k + 0.5) * th, rad = dd * rd, xl = r * Math.cos(rad), yl = r * Math.sin(rad);
      let d1, d2;
      if (g.radial) { d1 = r * Math.sin(hh - rad); d2 = r * Math.sin(hh + rad); }      // pastilla: bordes radiales a ±span/2
      else { d1 = (xl - ax) * Math.sin(hh) - yl * Math.cos(hh); d2 = (xl - ax) * Math.sin(hh) + yl * Math.cos(hh); }   // sector: bordes paralelos a las radiales de contorno, separados por la junta
      if (d1 < m || d2 < m) { pd.borde++; continue; }
      if (L > 0 && Math.abs(yl) < hb + m && xl > ru - L / 2 - m && xl < ru + L / 2 + m) { pd.muesca++; continue; }
      if (scr.some(([sx, sy]) => Math.hypot(xl - sx, yl - sy) < dk / 2 + m)) { pd.tornillos++; continue; }
      if (rCirc.some((rg) => Math.abs(r - rg) < wHalf)) { pd.ranCirc++; continue; }
      let gr = false;
      for (let q = 0; q < nRad && !gr; q++) { const e = (ph - 360 * q / nRad + 540) % 360 - 180; if (Math.abs(e) < 90 && r * Math.abs(Math.sin(e * rd)) < wHalf) gr = true; }   // distancia lateral a la semirrecta de la ranura
      if (gr) { pd.ranRad++; continue; }
      N++; por[k]++;
    }
    const out = { N, N_malla: nMalla, porSector: por, perdidas: pd, L, radios, r_circ: rCirc, dk, edge: g.edge, n, nTor, margen: m, d, p };
    if (plugCache.size > 400) plugCache.clear();
    plugCache.set(key, out);
    return out;
  }
  function ifaceDesign(P) {
    const o = ifOpt(P);
    if (o === 0) return { o, tss: 0, tuh: 0, delta: 0, mTop: 0, mUH: 0, mSS: 0, mBz: 0, tbz: 0 };
    if (o === 3) return ifaceDesignBz(P);
    const sad = 0.6 * P.Fy_ss, a = P.ss_void / 2, gr = o === 1 ? P.h_gr : 0;     // ranuras de engrase solo en el disco de la mesa de la opción A
    // Disco inoxidable: placa circular empotrada de radio a sobre un vacío local, carga uniforme q:
    //   σ_máx = 3·q·a²/(4·t²) ≤ 0,6·Fy  →  t_flex = a·√(0,75·q/σ_adm); espesor requerido = t_flex + sobreespesor (+ ranura en el disco ranurado), ≥ mínimo constructivo.
    const A_ss = Math.PI * ((P.D_top / 2) ** 2 - riOf(P) ** 2);
    const calc = (mTop, dl) => { const L = ifaceLoad(P, mTop, dl), tFlex = a * Math.sqrt(0.75 * L.q_max / sad); return { L, tFlex, treq: Math.max(tFlex + P.ss_allow, P.ss_tmin), treq2: Math.max(tFlex + P.ss_allow + gr, P.ss_tmin) }; };
    const tS = P.fix_mode < 1.5 ? tStopMin(P) : 0;                        // con topes soldados el sector no puede ser más fino que a_sup + a_inf + h_c,mín
    const fz = P.__th && P.__th.frozen;                                    // escenario térmico: geometría dimensionada a 20 °C y congelada
    const tAv = o === 1 && P.fix_mode > 1.5 ? isoK(P.tor2_d) + 0.5 + P.ss_allow : 0;     // AF2: la cabeza avellanada queda 0,5 mm bajo la cara aun después del relapeado (sobreespesor)
    const pick = (c) => fz ? [fz.tss, fz.tss2] : P.t_ss > 0 ? [P.t_ss, P.t_ss] : [commercial(SS_COMM, Math.max(c.treq, tS)), commercial(SS_COMM, Math.max(c.treq2, tS, tAv))];   // [disco de la base (liso), disco de la mesa (ranurado)]
    let c = calc(0, 0), [t1, t2] = pick(c);
    for (let i = 0; i < 4; i++) {                                       // el disco rotatorio también carga la interfaz
      c = calc(RHO_SS * A_ss * t2, t1 + t2);
      const [n1, n2] = pick(c);
      if (n1 === t1 && n2 === t2) break; t1 = n1; t2 = n2;
    }
    const q = c.L.q_max;
    // Lámina UHMW: la falta de planitud d_flat comprime localmente la lámina; la sobrepresión E·d/t se suma a q y no debe pasar de p_adm
    let tuhConf = 0, tuhReq = 0, tuh = 0, EcU = 0, SU = 0, tuhTope = 0;
    if (o === 2) {
      const uc = uhConf(P, q);
      tuhConf = uc.t;
      tuhReq = Math.max(tuhConf, P.uh_tmin);
      if (P.fix_mode < 1.5) {                                           // tope del rebaje: σ = F_sector/(L·h_c) ≤ p_adm (FU objetivo 0,90) con h_c = t − a_sup − a_inf
        const Lav = P.D_top / 2 - riOf(P) - 100, ms = muSet(P), Nn = c.L.ND - (P.phi_d - 1) * P.W_tf * G;
        const Fs = Math.max(ms.d, ms.cont, ms.dry) * Nn / P.n_seg * c.L.q_max / c.L.q_avg;
        tuhTope = P.a_sup + stopAInf(P) + Math.max(P.hc_min, Fs * 1e3 / (P.p_uhmw * Lav * 0.9) + P.tol_hc);   // h_c ≥ F_s/(0,9·L·p_adm) + tol_hc; el 0,9 es margen de proyecto (no lo exige la norma)
      }
      tuh = fz ? fz.tuh : P.t_uhmw > 0 ? P.t_uhmw : commercial(UH_COMM, Math.max(tuhReq, tuhTope));
      EcU = uc.Ec(tuh); SU = uc.S(tuh);
    }
    return { o, tss: t1, tss2: t2, tssReq: c.treq, tss2Req: c.treq2, tTope: tS, tuhTope, gr, tFlex: c.tFlex, q, qAvg: c.L.q_avg, a, sad, A_ss, tuh, tuhReq, tuhConf, EcU, SU,
      delta: t1 + t2 + tuh, mTop: RHO_SS * A_ss * t2, mUH: o === 2 ? RHO_UH * A_ss * tuh : 0, mSS: RHO_SS * A_ss * (t1 + t2), mBz: 0, tbz: 0 };
  }
  // Tapones de la placa o pastilla de bronce de espesor tB: cuenta real (plugLayout), fracciones real e ideal y cobertura de grafito.
  // La cuenta no depende de la masa ni de la presión: depende del espesor del bronce (largo del tope) y de la geometría; por eso se evalúa después de dimensionar tB.
  //   over: { d, p, edge, nTor } sobrescribe el patrón (barridos de TT.tapones)
  function tapInfo(P, conf, cov, tB, over) {
    over = over || {};
    const geo = contactGeo(P), n = conf === 3 ? Math.round(P.bz_npad) : Math.round(P.n_sec), removable = P.fix_mode < 1.5, d = over.d != null ? over.d : P.bz_plug_d, p = over.p != null ? over.p : P.bz_plug_p;
    let L = 0;
    if (removable) {
      const Fst = tmaxOf(P) / (geo.r_u / 1000) / n * (1 + geo.kq), Lav = geo.Ro - geo.Ri - 100;   // F_tope = (T_calado/r_u)/n·(q_máx/q_med): el mismo del dimensionamiento de stopsOf
      L = stopLenOf(P, "bz0", tB, P.Fy_bz, Fst, Lav).L;
    }
    const gap = Math.max(conf === 3 ? 0 : jointOf(P, AL_BZ, n), jointOf(P, conf === 2 ? AL_BZ : AL_SS, Math.round(P.n_sec)));   // junta en frío efectiva entre sectores (el dibujante usa la mayor)
    const lay = plugLayout(P, { n, radial: conf === 3, span: 360 / n * cov, gap, L, d, p, edge: over.edge != null ? over.edge : P.bz_edge, nTor: over.nTor != null ? over.nTor : Math.round(P.bz_n_tor) });
    const ap = Math.PI * d * d / 4, Acont = geo.Ac * cov, fgIdeal = Math.PI * d * d / (2 * Math.sqrt(3) * p * p);
    return Object.assign({}, lay, { Acont, ap, fgReal: lay.N * ap / Acont, fgIdeal, Nideal: fgIdeal * Acont / ap, junta: gap, removable, cov, conf });
  }
  // Opción C: placa de bronce con tapones de grafito, fija a la base, contra un disco duro rotatorio (configuraciones 1 y 3, esta con pastillas
  // que cubren la fracción bz_cover) o contra una 2.ª placa de bronce de aleación distinta (configuración 2).
  //   Bronce: σ = 3·q_loc·a²/(4·t²)/η ≤ 0,6·Fy_bz, η = (p − d)/p (ligamento entre tapones)  →  t_req = t_flex/√η + sobreespesor, ≥ mínimo constructivo.
  //   Fracción de grafito f_g: bz_fg_modo = 1 (default) usa la real (tapones que caben, ver plugLayout); 0 usa la ideal π·d²/(2√3·p²) sobre toda la corona.
  //   f_g solo afecta la masa del bronce (grafito 1,8 en vez de bronce en 0,7·t), q_neto (y con él PV y desgaste) y la cobertura de lubricación; no a q_máx, espesores ni η.
  function ifaceDesignBz(P) {
    const conf = Math.min(3, Math.max(1, Math.round(P.bz_conf))), a = P.ss_void / 2;
    const A_ss = Math.PI * ((P.D_top / 2) ** 2 - riOf(P) ** 2);
    const cov = conf === 3 ? Math.min(1, Math.max(0.05, P.bz_cover)) : 1;
    const eta = (P.bz_plug_p - P.bz_plug_d) / P.bz_plug_p, fg = Math.PI * P.bz_plug_d ** 2 / (2 * Math.sqrt(3) * P.bz_plug_p ** 2);
    const rBz = P.rho_bz * 1e-6;
    const mSolid = (t) => A_ss * t * rBz;                                                              // 2.ª placa de bronce maciza (configuración 2)
    const FyC = conf === 2 ? P.Fy_bz2 : P.Fy_cara;
    const calc = (mTop, dl) => {
      const L = ifaceLoad(P, mTop, dl), qLoc = L.q_max / cov, qC = conf === 3 ? qLoc : L.q_max;
      const tfB = a * Math.sqrt(0.75 * qLoc / (0.6 * P.Fy_bz)), treqB = Math.max(tfB / Math.sqrt(eta) + P.bz_allow + P.h_gr, P.bz_tmin);   // + ranuras de engrase
      const tfC = a * Math.sqrt(0.75 * qC / (0.6 * FyC)), treqC = Math.max(tfC + (conf === 2 ? P.bz_allow : P.ss_allow), conf === 2 ? P.bz_tmin : P.cara_tmin);
      return { L, qLoc, qC, tfB, treqB, tfC, treqC };
    };
    const rot = (tC) => conf === 2 ? mSolid(tC) : RHO_SS * A_ss * tC;                                  // masa rotatoria (fija a la mesa)
    const tS = P.fix_mode < 1.5 ? tStopMin(P) : 0;                        // espesor mínimo por tope soldado (a_sup + a_inf + h_c,mín)
    const fz = P.__th && P.__th.frozen;                                    // escenario térmico: geometría congelada a 20 °C
    const pickC = (c) => fz ? fz.tss : P.t_cara > 0 ? P.t_cara : commercial(conf === 2 ? BZ_COMM : SS_COMM, Math.max(c.treqC, tS));
    const pickB = (c) => fz ? fz.tbz : P.t_bz > 0 ? P.t_bz : commercial(BZ_COMM, Math.max(c.treqB, tS));
    let c = calc(0, 0), tB = pickB(c), tC = pickC(c);
    for (let i = 0; i < 4; i++) { c = calc(rot(tC), tB + tC); const nb = pickB(c), nc = pickC(c); if (nb === tB && nc === tC) break; tB = nb; tC = nc; }
    const tap = tapInfo(P, conf, cov, tB), fgUsed = P.bz_fg_modo > 0.5 ? tap.fgReal : fg, fgr = grooveFrac(P).f;
    const rhoPl = rBz * (1 - PLUG_DEPTH * fgUsed) + RHO_GR * PLUG_DEPTH * fgUsed;                     // densidad de la placa con tapones (mezcla sobre el área cubierta)
    const mPlate = (t) => A_ss * cov * t * rhoPl;
    return { o: 3, conf, cov, eta, fg, fgIdeal: fg, fgReal: tap.fgReal, fgUsed, Nreal: tap.N, Nideal: tap.Nideal, cobGrafito: tap.fgReal, cobGrafitoIdeal: fg, tap, a, A_ss, tTope: tS, q: c.L.q_max, qAvg: c.L.q_avg, qLoc: c.qLoc, qC: c.qC, gr: P.h_gr, fgr, qNet: c.qLoc / (1 - fgUsed - fgr), tss2: tC, tss2Req: c.treqC,
      tbz: tB, tbzReq: c.treqB, tFlexB: c.tfB, tss: tC, tssReq: c.treqC, tFlex: c.tfC, sad: 0.6 * P.Fy_bz, sadC: 0.6 * FyC, FyC,
      tuh: 0, tuhReq: 0, tuhConf: 0, delta: tB + tC, mTop: rot(tC), mUH: 0, rhoPl, rhoSolid: rBz,
      mSS: conf === 2 ? 0 : RHO_SS * A_ss * tC, mBz: conf === 2 ? mPlate(tB) + mSolid(tC) : mPlate(tB) };
  }

  // Herramientas de polígonos en planta (contornos simples en cualquier sentido; [x, y] en mm)
  const PG = {
    area(pl) { let A = 0; for (let i = 0; i < pl.length; i++) { const p = pl[i], q = pl[(i + 1) % pl.length]; A += p[0] * q[1] - q[0] * p[1]; } return A / 2; },
    rect(x0, x1, y0, y1) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; },
    inside(pl, p) { let c = false; for (let i = 0, j = pl.length - 1; i < pl.length; j = i++) { const a = pl[i], b = pl[j]; if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; },
    segDist(p, a, b) { const ex = b[0] - a[0], ey = b[1] - a[1], l2 = ex * ex + ey * ey, t = l2 > 0 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / l2)) : 0; return Math.hypot(p[0] - a[0] - t * ex, p[1] - a[1] - t * ey); },
    edgeDist(pl, p) { let d = Infinity; for (let i = 0; i < pl.length; i++) d = Math.min(d, PG.segDist(p, pl[i], pl[(i + 1) % pl.length])); return d; },
    cross(a, b, c, d) { const o = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); return o(a, b, c) * o(a, b, d) < 0 && o(c, d, a) * o(c, d, b) < 0; },
    // distancia mínima entre dos polígonos; negativa si se solapan (penetración aproximada por los vértices interiores)
    dist(A, B) {
      let d = Infinity, pen = 0, hit = false;
      A.forEach((p) => { const e = PG.edgeDist(B, p); if (PG.inside(B, p)) { hit = true; pen = Math.max(pen, e); } else d = Math.min(d, e); });
      B.forEach((p) => { const e = PG.edgeDist(A, p); if (PG.inside(A, p)) { hit = true; pen = Math.max(pen, e); } else d = Math.min(d, e); });
      if (!hit) for (let i = 0; i < A.length && !hit; i++) for (let j = 0; j < B.length && !hit; j++) if (PG.cross(A[i], A[(i + 1) % A.length], B[j], B[(j + 1) % B.length])) hit = true;
      return hit ? -Math.max(pen, 1e-3) : d;
    },
    // recorte de un polígono por un polígono convexo (Sutherland–Hodgman)
    clip(sub, clp) {
      const s = PG.area(clp) > 0 ? 1 : -1, inS = (p, a, b) => s * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) >= -1e-9;
      const X = (p, q, a, b) => { const d1 = [q[0] - p[0], q[1] - p[1]], d2 = [b[0] - a[0], b[1] - a[1]], den = d1[0] * d2[1] - d1[1] * d2[0], t = ((a[0] - p[0]) * d2[1] - (a[1] - p[1]) * d2[0]) / den; return [p[0] + t * d1[0], p[1] + t * d1[1]]; };
      let out = sub.slice();
      for (let i = 0; i < clp.length && out.length; i++) {
        const a = clp[i], b = clp[(i + 1) % clp.length], inp = out; out = [];
        for (let j = 0; j < inp.length; j++) { const p = inp[j], q = inp[(j + 1) % inp.length], pi = inS(p, a, b), qi = inS(q, a, b); if (pi) out.push(p); if (pi !== qi) out.push(X(p, q, a, b)); }
      }
      return out.filter((p, i) => i === 0 || Math.hypot(p[0] - out[i - 1][0], p[1] - out[i - 1][1]) > 1e-6);
    },
    // propiedades de una sección de rectángulos [x0, x1, y0, y1] y tensión normal máxima con el vector momento m (σ = −(m_x·I_xy + m_y·I_xx)/D·x + (m_x·I_yy + m_y·I_xy)/D·y)
    sec(R) {
      let A = 0, Sx = 0, Sy = 0; R.forEach(([x0, x1, y0, y1]) => { const a = (x1 - x0) * (y1 - y0); A += a; Sx += a * (x0 + x1) / 2; Sy += a * (y0 + y1) / 2; });
      const cx = Sx / A, cy = Sy / A; let Ixx = 0, Iyy = 0, Ixy = 0;
      R.forEach(([x0, x1, y0, y1]) => { const b = x1 - x0, h = y1 - y0, a = b * h, dx = (x0 + x1) / 2 - cx, dy = (y0 + y1) / 2 - cy; Ixx += b * h ** 3 / 12 + a * dy * dy; Iyy += h * b ** 3 / 12 + a * dx * dx; Ixy += a * dx * dy; });
      return { R, A, cx, cy, Ixx, Iyy, Ixy, D: Ixx * Iyy - Ixy * Ixy };
    },
    sigma(s, m, x, y) { const X = x - s.cx, Y = y - s.cy; return (-(m[0] * s.Ixy + m[1] * s.Ixx) * X + (m[0] * s.Iyy + m[1] * s.Ixy) * Y) / s.D; },
    sigMax(s, m) { let o = 0; s.R.forEach(([x0, x1, y0, y1]) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].forEach(([x, y]) => { o = Math.max(o, Math.abs(PG.sigma(s, m, x, y))); })); return o; },
    // flujo de corte en la junta que separa la parte «sub» (rectángulos) del resto, con la fuerza horizontal F·f (N) aplicada sobre la sección (dm/dz = F·(−f_y, f_x))
    flow(s, sub, f, F) {
      let Qx = 0, Qy = 0; sub.forEach(([x0, x1, y0, y1]) => { const a = (x1 - x0) * (y1 - y0); Qx += a * ((y0 + y1) / 2 - s.cy); Qy += a * ((x0 + x1) / 2 - s.cx); });
      const dm = [-f[1] * F, f[0] * F], al = -(dm[0] * s.Ixy + dm[1] * s.Ixx) / s.D, be = (dm[0] * s.Iyy + dm[1] * s.Ixy) / s.D;
      return Math.abs(al * Qy + be * Qx);
    },
  };
  // Barrido del eje del cilindro respecto de E (modo pivotado, cilindro 1 en giro antihorario; el horario es su reflejo respecto de la diagonal O–E):
  // ψ de los estados reales (empuje con Q en el canto, aproximación con Q en la toma, retorno) más la referencia colineal y la envolvente del canto W(L),
  // de modo que la abertura del soporte cubre cualquier posición de Q entre la toma y el canto. estados: ψ de cada estado (rad) y su fase.
  function pivSweep(P, K, CP) {
    const st = [];
    (K.pts || []).forEach((q) => st.push({ psi: q.psi, fase: "colineal" }));
    if (CP && CP.guia) {
      CP.push.filter((g) => g.ok).forEach((g) => st.push({ psi: g.psi, fase: "empuje" }));
      CP.guia.ret.forEach((q) => st.push({ psi: CP.psi0 - q.w / q.L, fase: "retorno" }));
      for (let i = 0; i <= 100; i++) { const L = P.L0 + (K.Lend - P.L0) * i / 100; st.push({ psi: CP.psi0 - CP.wCam(L) / L, fase: "canto" }, { psi: CP.psi0 - P.pv_c / L, fase: "toma" }); }
    }
    const ps = st.map((q) => q.psi), lo = Math.min(...ps), hi = Math.max(...ps), ph = P.pv_phE * D2R;
    return { lo, hi, loH: 2 * ph - hi, hiH: 2 * ph - lo, estados: st, horario: st.map((q) => ({ psi: 2 * ph - q.psi, fase: q.fase })) };
  }
  // Soporte del ojal E (modo pivotado; rediseño 10-11-2026, docs/normas/registro.md «Soporte del ojal E: cajón abierto»): cajón soldado a la base, centrado en E,
  // ABIERTO hacia la mesa en todo el barrido del cuerpo del cilindro. Marco local con origen en E (cilindro 1; el 2 por rotación de 180°), x e y paralelos a los
  // bordes de la base, la esquina de la base hacia (+x, −y) en el cilindro 1 (E en 315°). Piezas: pared trasera X (x ∈ [b_i, b], y ∈ [−b, b]) y pared trasera Y
  // (y ∈ [−b, −b_i], x ∈ [−b, b_i]) en L hacia la esquina; muñones Y+ y X− (lo que queda de las paredes delanteras fuera del barrido); tapa inferior y tapa superior
  // entre las paredes, recortadas en «nariz»: el cuerpo (Ø D desde e_cuerpo) ocupa toda la altura de las tapas, de modo que las piezas quedan a lateral ≥ D/2 + c
  // de los ejes extremos del barrido o a s ≤ e_cuerpo − c de E (c = pv_cE, holgura de diseño; la verificación exige ≥ 5 mm en todos los estados).
  function pivSupGeo(P, K, CP) {
    const zc0 = hAxis(P) + P.t_base, be = P.b_eye, g = P.g_ch, tl = P.pv_tl, B = P.pv_box, t = P.pv_tbox, b = B / 2, bi = b - t, dE = P.pv_dE, ext = P.pv_ext;
    const zU = zc0 + be / 2 + g + tl / 2, zL = zc0 - be / 2 - g - tl / 2, zW = zU + tl / 2 + P.pv_rebt, hW = zW - P.t_base, hBox = hW;
    const ph = P.pv_phE * D2R, uv = (a) => [Math.cos(a), Math.sin(a)];
    // marco canónico: la esquina de la base hacia (+x, −y) (E en 315°); real = E + (s_x·X, −s_y·Y) con s = signo de E (cilindro 1)
    const sx = K && K.ok ? Math.sign(K.E[0]) || 1 : 1, sy = K && K.ok ? Math.sign(K.E[1]) || -1 : -1, toC = (a) => Math.atan2(-sy * Math.sin(a), sx * Math.cos(a));
    const sw0 = K && K.ok ? pivSweep(P, K, CP) : null, unwrap = (a, ref) => { while (a - ref > Math.PI) a -= 2 * Math.PI; while (a - ref < -Math.PI) a += 2 * Math.PI; return a; };
    const band = (st) => { const ps = st.map((q) => unwrap(toC(q.psi), toC(st[0].psi))); return { lo: Math.min(...ps), hi: Math.max(...ps), st: st.map((q, i) => Object.assign({}, q, { psi: ps[i] })) }; };
    let bA = sw0 ? band(sw0.estados) : { lo: 1.70, hi: 1.80, st: [] }, bH = sw0 ? band(sw0.horario) : { lo: 2.91, hi: 3.01, st: [] };
    if (Math.abs(unwrap((bA.lo + bA.hi) / 2, Math.PI / 2) - Math.PI / 2) > Math.abs(unwrap((bH.lo + bH.hi) / 2, Math.PI / 2) - Math.PI / 2)) [bA, bH] = [bH, bA];   // A = banda hacia +Y (lado de la pared X)
    bA = Object.assign(bA, { lo: unwrap(bA.lo, Math.PI / 2), hi: unwrap(bA.lo, Math.PI / 2) + (bA.hi - bA.lo) }); bH = Object.assign(bH, { lo: unwrap(bH.lo, Math.PI), hi: unwrap(bH.lo, Math.PI) + (bH.hi - bH.lo) });
    const sw = { lo: bA.lo, hi: bA.hi, loH: bH.lo, hiH: bH.hi, estados: bA.st.map((q) => Object.assign({}, q, { psi: unwrap(q.psi, Math.PI / 2) })), horario: bH.st.map((q) => Object.assign({}, q, { psi: unwrap(q.psi, Math.PI) })), real: sw0 };
    const c = P.pv_cE, a0 = P.e_body - c, l0 = P.D_body / 2 + c;
    // ψ₁ = ψ_mín de la banda A (hacia +Y, del lado de la pared X), ψ₂ = ψ_máx; ψ₃, ψ₄ = extremos de la banda H (hacia −X, del lado de la pared Y)
    const u1 = uv(sw.lo), u2 = uv(sw.hi), u3 = uv(sw.loH), u4 = uv(sw.hiH), n1 = [u1[1], -u1[0]], m4 = [-u4[1], u4[0]];
    const arc = (pa, pb, n) => Array.from({ length: n - 1 }, (_, k) => { const a = pa + (pb - pa) * (k + 1) / n; return [a0 * Math.cos(a), a0 * Math.sin(a)]; });
    const det = u2[0] * u3[1] - u2[1] * u3[0], X = Math.abs(det) > 1e-9 ? [a0 * (u3[1] - u2[1]) / det, a0 * (u2[0] - u3[0]) / det] : [a0 * u2[0], a0 * u2[1]];
    const CA = [a0 * u1[0] + l0 * n1[0], a0 * u1[1] + l0 * n1[1]], CH = [a0 * u4[0] + l0 * m4[0], a0 * u4[1] + l0 * m4[1]], far = 4 * B;
    const allowed = [[CA[0] + far * u1[0], CA[1] + far * u1[1]], CA, [a0 * u1[0], a0 * u1[1]], ...arc(sw.lo, sw.hi, 8), [a0 * u2[0], a0 * u2[1]], X, [a0 * u3[0], a0 * u3[1]], ...arc(sw.loH, sw.hiH, 8), [a0 * u4[0], a0 * u4[1]], CH,
      [CH[0] + far * u4[0], CH[1] + far * u4[1]], [-far, -far], [far, -far], [far, far]];
    const tapa = PG.clip(allowed, PG.rect(-bi, bi, -bi, bi));
    // muñones: desde la pared trasera hasta la recta lateral del barrido (x_s y y_s donde la recta queda más adentro en el espesor del muñón)
    const xA = (y) => (l0 - y * n1[1]) / n1[0], yH = (x) => (l0 - x * m4[0]) / m4[1], xs = Math.max(xA(bi), xA(b)), ys = Math.min(yH(-bi), yH(-b));
    const piezas = [
      { id: "pared_X", nombre: "Pared trasera X (paralela al borde x de la base)", t, poly: PG.rect(bi, b, -b, b + ext), z: [P.t_base, zW], rect: [bi, b, -b, b + ext] },
      { id: "pared_Y", nombre: "Pared trasera Y (paralela al borde y de la base)", t, poly: PG.rect(-b - ext, bi, -b, -bi), z: [P.t_base, zW], rect: [-b - ext, bi, -b, -bi] },
    ];
    if (xs < bi - 1 && ys > -bi + 1) piezas.push({ id: "munon_Y", nombre: "Muñón delantero Y+ (resto de la pared delantera fuera del barrido)", t, poly: PG.rect(xs, bi, bi, b), z: [P.t_base, zW], rect: [xs, bi, bi, b] },
      { id: "munon_X", nombre: "Muñón delantero X− (resto de la pared delantera fuera del barrido)", t, poly: PG.rect(-b, -bi, -bi, ys), z: [P.t_base, zW], rect: [-b, -bi, -bi, ys] });
    const hole = Array.from({ length: 48 }, (_, k) => [dE / 2 * Math.cos(k * Math.PI / 24), dE / 2 * Math.sin(k * Math.PI / 24)]);
    piezas.push({ id: "tapa_inf", nombre: "Tapa inferior (oreja inferior del pasador E), recortada en nariz", t: tl, poly: tapa, z: [zL - tl / 2, zL + tl / 2], agujero: dE },
      { id: "tapa_sup", nombre: "Tapa superior (oreja superior del pasador E), recortada en nariz y rebajada " + nfx(P.pv_rebt, 0) + " mm bajo el borde de las paredes", t: tl, poly: tapa, z: [zU - tl / 2, zU + tl / 2], agujero: dE });
    const walls = piezas.filter((q) => q.rect), Aw = walls.reduce((a, q) => a + PG.area(q.poly), 0), Acap = Math.abs(PG.area(tapa)) - Math.PI / 4 * dE * dE;
    piezas.forEach((q) => { q.masa = RHO * (q.rect ? PG.area(q.poly) * hW : Acap * tl); });
    const mBox = RHO * Aw * hW, mLug = 2 * RHO * tl * Acap, mPin = RHO * Math.PI / 4 * dE ** 2 * (be + 2 * g + 2 * tl + 20);
    // holgura cuerpo del cilindro–piezas: huella del cuerpo (s ∈ [e_cuerpo, L0 − c_vástago], ancho D) frente a cada pieza que comparte cota z con el cuerpo
    const zb = [zc0 - P.D_body / 2, zc0 + P.D_body / 2], s0 = P.e_body, s1 = P.L0 - P.c_rod;
    const foot = (psi) => { const u = uv(psi), n = [-u[1], u[0]], h = P.D_body / 2; return [[s0, -h], [s1, -h], [s1, h], [s0, h]].map(([s, l]) => [s * u[0] + l * n[0], s * u[1] + l * n[1]]); };
    const clrOf = (psi) => Math.min(...piezas.map((q) => { const dz = Math.max(0, q.z[0] - zb[1], zb[0] - q.z[1]), dp = PG.dist(foot(psi), q.poly); return dz > 0 ? Math.hypot(Math.max(0, dp), dz) : dp; }));
    let clr = { d: Infinity }; sw.estados.map((q) => Object.assign({ sentido: "antihorario" }, q)).concat(sw.horario.map((q) => Object.assign({ sentido: "horario" }, q))).forEach((q) => { const d = clrOf(q.psi); if (d < clr.d) clr = { d, psi: q.psi, fase: q.fase, sentido: q.sentido }; });
    // distancia del agujero a la nariz en la dirección del eje (desgarro con la tracción del retorno) y a las paredes traseras en la dirección de la fuerza de empuje
    const rayTo = (pl, dir) => { let best = Infinity; for (let i = 0; i < pl.length; i++) { const a = pl[i], q = pl[(i + 1) % pl.length], e = [q[0] - a[0], q[1] - a[1]], den = dir[0] * e[1] - dir[1] * e[0]; if (Math.abs(den) < 1e-12) continue; const tt = (a[0] * e[1] - a[1] * e[0]) / den, uu = (a[0] * dir[1] - a[1] * dir[0]) / den; if (tt > 0 && uu >= -1e-9 && uu <= 1 + 1e-9) best = Math.min(best, tt); } return best; };
    const psiAll = sw.estados.map((q) => q.psi).concat(sw.horario.map((q) => q.psi));
    const aNose = Math.min(...psiAll.map((p) => rayTo(tapa, uv(p)))) - dE / 2, aRear = Math.min(...psiAll.map((p) => rayTo(tapa, uv(p + Math.PI)))) - dE / 2;
    // juntas soldadas: paredes y muñones a la base y entre sí con CJP (TC-U4b, AWS D1.1-2020 Figura 5.1) y filete de refuerzo interior; tapas a las paredes con PJP
    // en bisel simple 45° desde arriba (TC-P4) y filete de refuerzo superior, sin soldadura por debajo (cavidad sin acceso). Líneas de la tapa: cantos contra paredes y muñones.
    const S_pjp = Math.max(6, tl - 8), E_pjp = S_pjp - 3, wr = P.pv_wbox;
    const capLines = [];
    for (let i = 0; i < tapa.length; i++) { const p = tapa[i], q = tapa[(i + 1) % tapa.length], mid = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
      const onWall = walls.some((w) => PG.edgeDist(w.poly, mid) < 1e-6 && Math.hypot(q[0] - p[0], q[1] - p[1]) > 1e-6); if (onWall) capLines.push([p, q]); }
    const Lcap = capLines.reduce((a, [p, q]) => a + Math.hypot(q[0] - p[0], q[1] - p[1]), 0);
    const Cc = capLines.reduce((a, [p, q]) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]); return [a[0] + L * (p[0] + q[0]) / 2 / Lcap, a[1] + L * (p[1] + q[1]) / 2 / Lcap]; }, [0, 0]);
    const Jcap = capLines.reduce((a, [p, q]) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]), m = [(p[0] + q[0]) / 2 - Cc[0], (p[1] + q[1]) / 2 - Cc[1]]; return a + L ** 3 / 12 + L * (m[0] ** 2 + m[1] ** 2); }, 0);
    // q máx (N/mm) en la línea de la tapa con la fuerza F·f aplicada en E (método elástico, AISC Manual Parte 8)
    const capQ = (f, F) => { const M = (0 - Cc[0]) * f[1] * F - (0 - Cc[1]) * f[0] * F; let qm = 0; capLines.forEach(([p, q]) => [p, q].forEach((r) => { const v = [f[0] * F / Lcap - M * (r[1] - Cc[1]) / Jcap, f[1] * F / Lcap + M * (r[0] - Cc[0]) / Jcap]; qm = Math.max(qm, Math.hypot(v[0], v[1])); })); return qm; };
    const sec = PG.sec(walls.map((w) => w.rect));
    const juntas = [
      { id: "J-E1", piezas: ["pared_X", "base"], tipo: "CJP en bisel simple 45° (TC-U4b): bisel por el interior, resanado de raíz y soldadura de respaldo por el exterior; filete de refuerzo interior", tamano: { CJP: t, filete_refuerzo: wr }, largo: 2 * b + ext, acceso: "interior: antes de montar las tapas (desde arriba); exterior: por fuera del borde de la base, con el marco interrumpido" },
      { id: "J-E2", piezas: ["pared_Y", "base"], tipo: "CJP en bisel simple 45° (TC-U4b), como J-E1", tamano: { CJP: t, filete_refuerzo: wr }, largo: b + bi + ext, acceso: "como J-E1" },
      { id: "J-E3", piezas: ["pared_Y", "pared_X"], tipo: "CJP de esquina en bisel simple 45° (TC-U4b) desde el exterior sobre el extremo de la pared Y, resanado y respaldo por el interior; filete de refuerzo interior", tamano: { CJP: t, filete_refuerzo: wr }, largo: hW, acceso: "en banco (subconjunto de paredes), ambas caras libres" },
    ];
    if (piezas.some((q) => q.id === "munon_Y")) juntas.push(
      { id: "J-E4", piezas: ["munon_Y", "pared_X"], tipo: "CJP en T en bisel simple 45° (TC-U4b) y filete de refuerzo en el rincón interior", tamano: { CJP: t, filete_refuerzo: wr }, largo: hW, acceso: "en banco" },
      { id: "J-E5", piezas: ["munon_X", "pared_Y"], tipo: "CJP en T en bisel simple 45° (TC-U4b) y filete de refuerzo en el rincón interior", tamano: { CJP: t, filete_refuerzo: wr }, largo: hW, acceso: "en banco" },
      { id: "J-E6", piezas: ["munon_Y", "munon_X", "base"], tipo: "CJP en bisel simple 45° (TC-U4b), ambas caras accesibles (lado de la mesa abierto)", tamano: { CJP: t, filete_refuerzo: wr }, largo: (bi - xs) + (ys + bi), acceso: "ambas caras" });
    juntas.push(
      { id: "J-E7", piezas: ["tapa_inf", "paredes y muñones"], tipo: "PJP en bisel simple 45° (TC-P4) en el canto de la tapa, soldada desde arriba, con filete de refuerzo superior; sin soldadura por debajo", tamano: { S: S_pjp, E: E_pjp, filete_refuerzo: wr }, largo: Lcap, acceso: "desde arriba, antes de la tapa superior" },
      { id: "J-E8", piezas: ["tapa_sup", "paredes y muñones"], tipo: "PJP en bisel simple 45° (TC-P4) desde arriba con filete de refuerzo en el rincón que forma el rebaje", tamano: { S: S_pjp, E: E_pjp, filete_refuerzo: wr, rebaje: P.pv_rebt }, largo: Lcap, acceso: "desde arriba" });
    const secuencia = [
      "1. Base con el marco perimetral interrumpido frente al soporte (tramos del marco a ≥ 50 mm de las paredes traseras; el marco no cumple función resistente en el núcleo).",
      "2. En banco: armar las paredes traseras X e Y y los muñones; soldar J-E3, J-E4 y J-E5 (CJP, ambas caras accesibles); END de las CJP.",
      "3. Presentar el subconjunto sobre la base con plantilla al eje E (± 1 mm); soldar J-E1, J-E2 y J-E6: bisel y raíz por el interior (aún sin tapas), resanado y respaldo por el exterior (fuera del borde de la base); filete de refuerzo interior.",
      "4. Tapa inferior: apoyada en calzas de montaje a la cota z, soldada desde arriba (J-E7, PJP + filete de refuerzo); retirar las calzas por el frente abierto.",
      "5. Tapa superior: igual, " + nfx(P.pv_rebt, 0) + " mm bajo el borde de las paredes (J-E8).",
      "6. Mecanizar el agujero Ø" + nfx(dE, 0) + " H9 de ambas tapas en línea, después de soldar (alineación del pasador E).",
      "7. Inspección: VT 100 %; UT 100 % de las CJP; MT de las PJP y los filetes (AWS D1.1/D1.1M:2020, cláusula 8, estructura cargada estáticamente).",
    ];
    // interrupción del marco: a lo largo de las paredes traseras con 50 mm de acceso a cada lado (coordenadas locales, cilindro 1)
    const gapRim = 50;
    const toReal = (cil) => (p) => { const E = K && K.ok ? K.E : [0, 0], q = [E[0] + sx * p[0], E[1] - sy * p[1]]; return cil === 2 ? [-q[0], -q[1]] : q; };
    return { zc0, zU, zL, zW, hU: zU - P.t_base, hL: zL - P.t_base, hBox, hW, b, bi, xs, ys, aTear: aRear, aNose, zLugBot: zc0 - be / 2 - g - tl, forkH: be + 2 * g + 2 * tl, mBox, mLug, mPin, m: mBox + mLug + mPin,
      piezas, tapa, sweep: sw, c, a0, l0, clr, clrOf, foot, sec, walls, capLines, Lcap, capQ, S_pjp, E_pjp, juntas, secuencia, Acap, sx, sy, toC, toReal,
      ext, marco: { holgura: gapRim, alcance: b + ext + gapRim } };
  }
  // Bloque-uña (modo pivotado): cuerpo acodado b_u × h_u desde el cubo de Q hasta el tramo de la cara (b_f × l_f), horquilla sobre el ojal del vástago y pasador Q
  function pivBlkGeo(P, K) {
    const zc0 = hAxis(P) + P.t_base, r = P.d_pin / 2, Lqp = K && K.ok ? K.Lqp : (P.pv_Lqp || 300), eb = P.pv_dq / 2 + 25, s2 = Lqp - r, s1 = s2 - P.pv_lf;
    const tq = (P.pv_hu - P.b_eye - 2 * P.g_ch) / 2, zLc = zc0 - P.b_eye / 2 - P.g_ch - tq / 2, zCam = P.t_base + P.pv_tcam / 2, lq = zLc - zCam;
    // cara de empuje: cilíndrica convexa de radio R_f (vértice en s₂, centro de curvatura en s_f = s₂ − R_f) o plana (R_f = 0). El bloque es libre en Q: la resultante
    // del contacto (inclinada ρ = atan μ_s respecto de la normal) pasa a d_R = μ_Q·d_Q/2 de Q (roce del pasador Q); la normal pasa por el centro de curvatura y por P,
    // de modo que sen γ = (s₂·sen ρ + d_R)/s_f y el contacto queda a e_c = R_f·sen γ del eje del bloque (cara plana: e_c = s₂·tan ρ + d_R). Signo ± (calado estático).
    const Rf = P.pv_rface > 0 ? P.pv_rface : 0, rho = Math.atan(P.mu_s), dR = P.pv_muE * P.pv_dq / 2, half = P.pv_bf / 2;
    const sf = Rf > 0 ? s2 - Rf : s2, sgam = Rf > 0 ? Math.min(1, (s2 * Math.sin(rho) + dR) / Math.max(1, sf)) : Math.sin(rho), gam = Math.asin(sgam);
    const ec = Rf > 0 ? Rf * sgam : s2 * Math.tan(rho) + dR, dBlk = Math.asin(Math.min(1, (Rf > 0 ? (Rf + r) * sgam : ec) / Lqp));   // giro del bloque respecto de la recta Q–P
    const sag = Rf > half ? Rf - Math.sqrt(Rf * Rf - half * half) : 0, a2 = Rf > half ? 2 * Math.asin(half / Rf) : 0, cut = Rf > half ? P.pv_bf * sag - Rf * Rf / 2 * (a2 - Math.sin(a2)) : 0;
    const mBlk = RHO * (P.pv_hu * ((s1 + eb) * P.pv_bu + P.pv_lf * P.pv_bf - cut) - (P.b_eye + 2 * P.g_ch) * 2 * eb * eb), lPin = zc0 + P.pv_hu / 2 - (P.t_base + 2);
    const mPin = RHO * Math.PI / 4 * P.pv_dq ** 2 * lPin;
    return { zc0, eb, s1, s2, tq, zLc, zCam, lq, lPin, mBlk, mPin, m: Math.max(0, mBlk) + mPin, zBot: zc0 - P.pv_hu / 2, Rf, sf, gam, ec, dR, dBlk, sag, ecBody: P.pv_ecr + P.e_dog + ec * s1 / s2, ecFace: P.e_dog + ec };
  }
  // Masas sin las barras de los topes (estas dependen del par de calado y se suman en compute(), que es la fuente de m.total)
  function massesBase(P) {
    const ifc = ifaceDesign(P), m = massesMesa(P, ifc.delta);
    m.ssTop = ifc.mTop; m.ss = ifc.mSS; m.uhmw = ifc.mUH; m.bz = ifc.mBz;   // pieza rotatoria, discos inoxidables o duros, lámina UHMW y bronce
    m.base = RHO * (P.B * P.B - Math.PI / 4 * P.D_piv ** 2) * P.t_base + (P.h_boss > 0 ? RHO * Math.PI / 4 * (P.D_boss ** 2 - P.D_piv ** 2) * P.h_boss : 0)   // + collar de asiento del pivote
      + 4 * RHO * (2 * P.R_ear * (P.h_ear - 0) + Math.PI * P.R_ear ** 2 / 2 - Math.PI / 4 * P.d_ear ** 2) * P.t_ear;   // + 4 orejas de izaje
    m.rim = RHO * (4 * P.B - 4 * P.rim_t) * P.rim_h * P.rim_t;
    if (driveMode(P) === 1) {
      const bg = bracketGeo(P);
      const Llug = bg.Llug, tl = 2 * P.t_ch + bg.spacer;
      m.brackets = RHO * P.n_br * (2 * P.t_ch * P.L_ch * bg.H + (bg.Win * Llug - Math.PI / 4 * P.d_pp ** 2) * tl);
      const g = guideGeo(P);
      // uña: bloque desde 0,3·d antes del centro del pasador hasta el fondo del alojamiento, menos el asiento cilíndrico
      const xUn = g.lever + P.c_tip + P.L_in;
      m.dogs = Math.max(0, RHO * P.n_cyl * (xUn * P.dog_b - chamferCut(P)) * P.dog_h);
      // patín: caja sobre la bancada + lengüeta + marco de boca − hueco del ojal − pasador − paso del vástago − alojamiento de la uña
      const zb = P.t_base + P.t_bed, Hs = g.shoeTop - zb, gap = P.b_eye + 2 * P.g_ch, dr = P.d_rod + 10;
      const shoeV = g.L_s * P.w_s * Hs + g.L_s * (P.w_slot - 2) * (P.h_tee > 0 ? P.h_slot + 1 : P.h_slot - 2) + (P.h_tee > 0 ? g.L_s * (P.w_tee - 2) * (P.h_tee - 2) : 0) + g.inset * (P.dog_b + 2 * P.t_fw) * (P.dog_h + 20)
        - (g.rear + 57.5) * 115 * gap - Math.PI / 4 * P.d_pp ** 2 * (g.zc0 + forkH(P) / 2 - Math.max(zb, g.zc0 - forkH(P) / 2 - 10) - gap) - dr * (g.rear - 40) * (dr - gap)
        - (g.pocketEnd - g.mouthX + 1 - g.inset) * (P.dog_b + 2) * (P.dog_h + 2) - g.inset * (P.dog_b + 2) * (P.dog_h + 2);
      m.shoes = RHO * P.n_cyl * shoeV;
      // bancadas: una por lado de cilindro (sirve a ambos sentidos de giro)
      m.beds = RHO * P.n_cyl * (g.L_bed * P.w_bed * P.t_bed - g.L_bed * P.w_slot * P.h_slot - g.L_bed * P.w_tee * P.h_tee);
      // Tarea 1: riel-leva, soportes, prolongación de la bancada y seguidor (uno por cilindro: la pletina se voltea para el otro sentido de giro)
      const cg = camGuided(P);
      m.cam = cg ? cg.m.total : 0;
    } else {
      // Tarea 2: sin patín, bancada ni ménsulas del modo guiado; brackets = soporte del ojal E (uno por cilindro: sirve a ambos sentidos),
      // dogs = bloque-uña con su pasador Q, cam = 4 placas-leva (una por cilindro y sentido) con su revestimiento (la zapata la suma compute())
      const K = kinPiv(P), sg = pivSup(P), bk = pivBlkGeo(P, K), CP = camPiv(P, K), fam = camFam(P);
      m.brackets = P.n_cyl * sg.m;
      if (K.ok) { const h = sg.marco.alcance, Lx = Math.max(0, P.B / 2 - (Math.abs(K.E[1]) - h)), Ly = Math.max(0, P.B / 2 - (Math.abs(K.E[0]) - h));   // marco interrumpido frente a las paredes traseras de cada soporte
        m.rim = Math.max(0, m.rim - P.n_cyl * RHO * P.rim_t * P.rim_h * Math.max(0, Lx + Ly - P.rim_t)); }
      m.dogs = P.n_cyl * bk.m;
      m.shoes = 0; m.beds = 0;
      m.cam = CP ? 2 * P.n_cyl * (RHO * P.pv_tcam * CP.area + (fam.f > 1 ? fam.rhoL * P.pv_tlin * P.pv_tcam * CP.Lb : 0)) : 0;
    }
    m.pivot = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + ifc.delta + topUnder(P) + 3);   // hasta 3 mm sobre la cara inferior de la plancha del cubo (W: la plancha rebajada)
    m.cyl = P.n_cyl * P.m_cyl;
    m.stopBars = 0;                                                      // barras de los topes soldados: las completa compute()
    m.total = m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.cam + m.pivot + m.cyl;
    return m;
  }
  const masses = (P) => compute(P).m;                                   // con las barras de los topes dentro de m.total
  function bracketGeo(P) {
    const Win = P.D_body + 20;                                          // luz interior entre mejillas (cilindro coaxial con la guía)
    const H = hAxis(P) + P.b_eye / 2 + P.g_ch + P.t_ch;                 // alto hasta cara superior de la oreja superior
    const spacer = Math.max(0, hAxis(P) - P.b_eye / 2 - P.g_ch - P.t_ch); // suplemento bajo la oreja inferior
    // saliente trasera: desgarro por corte de la oreja superior (2 planos) con F/2 a calado, BTH-1 Fy/(Nd·√3)
    const Fs = Math.PI / 4 * P.D_bore ** 2 * P.p_relief / 10;           // N
    const aReq = (Fs / 2) / (2 * P.t_ch * (P.__th ? P.__th.Fy0 : P.Fy) / (P.Nd * Math.sqrt(3)));   // escenario térmico: la saliente se dimensionó con el Fy de 20 °C
    const rear = Math.ceil((P.d_pp / 2 + aReq / 0.85) / 5) * 5;
    const lugF = P.d_pp / 2 + 25;                                        // saliente delantera (sin carga), libre del cuerpo
    return { Win, H, spacer, rear, lugF, Llug: rear + lugF, aReq, Wout: Win + 2 * P.t_ch };
  }
  function chamferGeo(P) {   // chaflán de retorno en la arista punta–cara trasera de la uña (cara de empuje plana)
    const g = guideGeo(P), dx = g.travel, dy = dx / Math.tan(P.beta_ch * Math.PI / 180);
    return { dx, dy, area: dx * Math.min(dy, P.dog_b) / 2 };
  }
  function chamferCut(P) { return chamferGeo(P).area; }
  function asymF(P, mg, end) {   // factor F_cil·η/F_pas en un extremo de la carrera (end = −1 toma, +1 final) para un μg dado
    const g = guideGeo(P), th = (end || -1) * g.pitch / 2, xc = P.R_pin * Math.cos(th), yc = P.R_pin * Math.sin(th) - P.d_pin / 2;
    const yr = P.R_pin * Math.sin(th) - P.l_p + (g.front - g.rear) / 2 - g.Lg / 2, h = (P.R_pin * Math.sin(th) >= P.d_pin / 2 ? 1 : -1) * P.mu_s;
    const rf = ((P.x_g - xc) + h * (yc - yr)) / g.Lg, rr = h - rf;
    return 1 + Math.max(0, mg) * (Math.abs(rf) + Math.abs(rr));
  }
  function TT_lugF(P) { return P.d_pp / 2 + 25; }
  function forkH(P) { return P.b_eye + 2 * P.g_ch + 2 * P.t_ch; }       // alto de la horquilla de la uña
  function hAxis(P) { return P.h_disc / 2 + ifaceDesign(P).delta; }   // eje del cilindro sobre la base = mitad de la luz del pasador + discos de la interfaz
  function prIn(P) { return Math.max(P.D_hub / 2, P.R_pin - (P.D_top / 2 - P.R_pin)); }   // radio interior del anillo de pasadores
  function pinClear(P) { return P.h_disc - 2 * Math.max(P.t_pr, P.t_top, P.t_bot); }

  /* ---------------- Geometría del accionamiento guiado ---------------- */
  // Lado +x: guía y cilindro paralelos a y en x = x_g; la uña empuja el pasador en +y entre θ = −π/N y +π/N.
  function guideGeo(P, lite) {   // lite: sin las cotas verticales (zc0, shoeTop), que dependen del espesor de la interfaz (hAxis); tmaxOf las evita para no recursar
    const pitch = 2 * Math.PI / P.N_pin, R = P.R_pin, a_min = R * Math.cos(pitch / 2);
    const front = P.l_p + 20 + P.f_ext;                                  // pasador del vástago → cara delantera del patín (cubre la uña)
    const rear = 1.25 * P.d_pp;                                          // pasador del vástago → cara trasera del patín
    const L_s = front + rear, Lg = 2 / 3 * L_s;                          // brazo entre reacciones de guía (presión lineal)
    const chord = 2 * R * Math.sin(pitch / 2);
    const y_pin0 = -R * Math.sin(pitch / 2), y_rp0 = y_pin0 - P.l_p - P.s_free, y_rp1 = y_pin0 + chord - P.l_p;
    const y_eye = y_rp0 - P.L0;
    const Y_bed = Math.max(Math.abs(y_rp0 - rear), Math.abs(y_rp1 + front)) + 10;
    const zc0 = lite ? NaN : hAxis(P) + P.t_base;                          // eje del cilindro (absoluto)
    // boca del alojamiento: se adelanta desde la cara del patín hasta 10 mm de los pasadores, entre los anillos de la mesa
    const mouthX = Math.min(P.x_g - P.w_s / 2, R + P.d_pin / 2 + 10), inset = P.x_g - P.w_s / 2 - mouthX;
    const lever = mouthX - a_min;                                        // voladizo de la uña: boca → centro del pasador
    // retorno: la uña se desliza radialmente hacia afuera (resorte) hasta despejar el pasador siguiente
    const tipX = a_min - P.c_tip, travel = R + P.d_pin / 2 + 5 - tipX;
    const pocketEnd = mouthX + P.L_in + travel + P.s_sp;                // fondo del alojamiento (uña retraída + resorte)
    const shoeTop = lite ? NaN : Math.max(zc0 + forkH(P) / 2, zc0 + P.dog_h / 2 + 1 + P.t_pk);   // cara superior del patín (horquilla o tapa del alojamiento)
    return { shoeTop, pitch, a_min, front, rear, L_s, Lg, chord, y_pin0, y_rp0, y_rp1, y_eye, L_bed: 2 * Y_bed, Y_bed, zc0, lever, mouthX, inset, tipX, travel, pocketEnd };
  }
  function kinematics(P, lite) {
    const g = guideGeo(P, lite), R = P.R_pin, n = 60;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const th = -g.pitch / 2 + g.pitch * i / n, arm = R * Math.cos(th);
      pts.push({ th, s: P.s_free + R * (Math.sin(th) - Math.sin(-g.pitch / 2)), arm, Delta: P.x_g - arm });
    }
    const s_req = P.s_free + g.chord;
    return Object.assign({ ok: true, pts, s_req, margin: P.stroke - s_req, armMin: g.a_min, armMax: R, gap: g.chord - P.d_pin,
      radial: R - g.a_min, DeltaMax: P.x_g - g.a_min }, g);
  }

  /* ---------------- Cadena de empuje en planta: equilibrio del patín por unidad de F_pas (lo usan compute y tmaxOf) ---------------- */
  function driveAtG(P, K, th, s) {
    const yMid = (K.front - K.rear) / 2;                 // centro del patín respecto del pasador del vástago
    const xc = P.R_pin * Math.cos(th), yc = P.R_pin * Math.sin(th) - P.d_pin / 2;
    const yrp = P.R_pin * Math.sin(th) - P.l_p, yr = yrp + yMid - K.Lg / 2;
    const h = s * P.mu_s, rf = ((P.x_g - xc) + h * (yc - yr)) / K.Lg, rr = h - rf;
    return { th, s, xc, yc, h, rf, rr, den: xc - h * yc, fr: 1 + P.mu_g * (Math.abs(rf) + Math.abs(rr)) };
  }
  function drivePts(P, K) {
    const dpts = [], thX = Math.asin(Math.min(1, P.d_pin / 2 / P.R_pin));
    K.pts.forEach((q) => dpts.push(driveAtG(P, K, q.th, P.R_pin * Math.sin(q.th) >= P.d_pin / 2 ? 1 : -1)));
    if (thX < K.pitch / 2) { dpts.push(driveAtG(P, K, thX, -1)); dpts.push(driveAtG(P, K, thX, 1)); }
    dpts.sort((a, b) => a.th - b.th || a.s - b.s);
    return dpts;
  }
  // Par de calado vencible (kN·m): el mismo R.Tmax de compute(), disponible sin construir R (lo usa el conteo de tapones para el largo de la muesca del tope)
  function tmaxOf(P) {
    const A = Math.PI / 4 * P.D_bore ** 2, Fstall = A * P.p_relief / 10 / 1e3;
    if (driveMode(P) === 2) { const K = kinPiv(P, true); return K.ok ? Fstall / Math.max(...K.pts.map((q) => 1e3 / P.n_cyl / q.aEff * (1 + camFam(P).mu * P.mu_s) / P.eta_c)) : 0; }
    const K = kinematics(P, true);
    return Fstall / Math.max(...drivePts(P, K).map((d) => 1e3 / P.n_cyl / d.den * d.fr / P.eta_c));
  }

  /* ---------------- Modo de accionamiento y familias de material del contacto seguidor–leva ---------------- */
  const driveMode = (P) => (Math.round(P.drive_mode) === 2 ? 2 : 1);
  // Familias (pedido del mandante 07-11-2026): reutilizan los μ, presiones admisibles y PV de la interfaz de giro. cam_mat = 0 (automático):
  // modo guiado → 1 (la rampa que exige la sincronía, ~62°, solo cumple el autobloqueo con rodillo); modo pivotado → la familia de la interfaz activa (base → 1, A → 4, B → 4, C → 3).
  function camFam(P) {
    const mode = driveMode(P), cm = Math.round(P.cam_mat), auto = !(cm >= 1 && cm <= 4);
    const f = auto ? (mode === 1 ? 1 : [1, 4, 4, 3][ifOpt(P)]) : cm;   // B → 4: la zapata de UHMW no cumple PV con la carga transversal del empuje (largo > 3·d_Q); los discos de B son inoxidables
    const D = {
      1: { nombre: "acero templado–acero con grasa grafitada", corto: "acero–acero", mu: P.mu_d, muRef: "μ_d de la grasa grafitada (interfaz acero–acero)", tipo: "hertz", pAdm: null, PV: null, FyL: null, rhoL: RHO, pRef: "Hertz, contacto lineal; canto templado por inducción (Fy_sup); inicio de fluencia p₀ = 1,67σy (Tresca)" },
      2: { nombre: "UHMW sobre respaldo de acero", corto: "UHMW", mu: P.muB_d, muRef: "μ_B,d de la opción B", tipo: "pad", pAdm: P.p_uhmw, PV: P.PV_uh, FyL: null, rhoL: RHO_UH, pRef: "p_adm sostenida y PV del UHMW-PE de la opción B (catálogo del proveedor, ASTM D4020)" },
      3: { nombre: "bronce con tapones de grafito sobre respaldo de acero", corto: "bronce con grafito", mu: P.muC_d, muRef: "μ_C,d de la opción C", tipo: "pad", pAdm: P.p_bz, PV: P.PV_bz, FyL: P.Fy_bz, rhoL: P.rho_bz * 1e-6, pRef: "p_adm sobre el bronce y PV de la opción C (ASTM B584/B148; catálogo del proveedor)" },
      4: { nombre: "inoxidable–inoxidable con grasa", corto: "inox–inox", mu: P.muA_d, muRef: "μ_A,d de la opción A", tipo: "pad", pAdm: P.q_adm, PV: null, FyL: P.Fy_ss, rhoL: RHO_SS, pRef: "q_adm del contacto metálico lubricado (criterio del proyecto); Fy del inoxidable ASTM A240" },
    };
    return Object.assign({ f, auto, mode }, D[f]);
  }
  // Distancia de un punto a un polígono convexo (negativa dentro) y a un rectángulo orientado (origen o, eje u, s ∈ [s0, s1], ancho w centrado)
  function polyDist(poly, px, py) {
    let dmin = Infinity, inside = true, sgn = 0;
    for (let i = 0; i < poly.length; i++) {
      const [ax, ay] = poly[i], [bx, by] = poly[(i + 1) % poly.length], ex = bx - ax, ey = by - ay, l2 = ex * ex + ey * ey;
      const t = l2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * ex + (py - ay) * ey) / l2)) : 0;
      dmin = Math.min(dmin, Math.hypot(px - ax - t * ex, py - ay - t * ey));
      const cr = ex * (py - ay) - ey * (px - ax);
      if (cr !== 0) { if (sgn === 0) sgn = Math.sign(cr); else if (Math.sign(cr) !== sgn) inside = false; }
    }
    return inside ? -dmin : dmin;
  }
  function rectDist(px, py, ox, oy, ux, uy, s0, s1, w) {
    const dx = px - ox, dy = py - oy, s = dx * ux + dy * uy, t = -dx * uy + dy * ux;
    const ds = Math.max(0, s0 - s, s - s1), dt = Math.max(0, Math.abs(t) - w / 2);
    return ds > 0 || dt > 0 ? Math.hypot(ds, dt) : -Math.min(s - s0, s1 - s, w / 2 - Math.abs(t));
  }
  // AISC 360-22 J3: pernos (Fnt = 0,75·Fu, Fnv = 0,45·Fu con rosca en el plano de corte, área nominal, Ω = 2,00; tracción + corte J3.8, Ec. J3-3a)
  function boltJ3(P, d, V, T) {
    const Ab = Math.PI / 4 * d * d, Fnt = 0.75 * P.Fu_bolt, Fnv = 0.45 * P.Fu_bolt, frv = V / Ab, ft = T / Ab, Om = 2.0;
    const Fpnt = Math.max(0, Math.min(Fnt, 1.3 * Fnt - Om * Fnt / Fnv * frv));
    return { Ab, Fnt, Fnv, frv, ft, Fpnt, capV: Fnv / Om, capT: Fpnt / Om };
  }
  const J34M = (d) => (d <= 16 ? 22 : d <= 20 ? 26 : d <= 22 ? 28 : d <= 24 ? 30 : d <= 27 ? 34 : d <= 30 ? 38 : d <= 36 ? 46 : 1.25 * d);   // AISC 360-22 Tabla J3.4M: distancia mínima al borde (mm)

  /* ---------------- Tarea 1: leva de reenganche positiva del modo guiado ---------------- */
  // Coordenadas del pasador siguiente B (θ = −π/N, centro (a_mín, y_pin0)): X radial (+ hacia afuera), η = y_cara de empuje − y_B.
  // La uña a la salida u es el polígono convexo: punta X = −c_punta + u, cara de empuje en η, cara trasera en η − b_uña y chaflán de retorno
  // entre (X_t + Δx, η − b) y (X_t, η − b + Δy). Al retraer (η de η₁ a η₀) la leva limita u ≤ u_leva(η): nivel de toma c, bolsillo (recorrido Δx)
  // y rampa a α del eje de la bancada que termina en c a η_fin = η₀ + tramo; el margen de sincronía es la menor holgura uña–B con u = u_leva(η).
  // Memoria por contenido de P (sin la copia P0 del escenario térmico): massesBase y compute piden la misma leva; los resultados son de solo lectura
  // Las cargas (W, e, φ_d, D_carga y los casos de fricción del giro) no intervienen en la geometría de las levas: se excluyen de la clave y se agrega la
  // cota del eje (depende de la interfaz, que sí depende de la carga), de modo que los barridos de capacidad reutilizan la leva.
  const MEMO_SKIP = new Set(["P0", "W_tf", "e", "phi_d", "D_load", "r_ef", "mu_nom", "mu_cont", "mu_dry", "FS_min", "turns_yr", "life", "q_floor", "phi_lift"]);
  const memoP = (fn, useHax) => { const cache = new Map(); return (P, ...a) => { const k = JSON.stringify(P, (kk, v) => (MEMO_SKIP.has(kk) ? undefined : v)) + (useHax ? "|" + hAxis(P) : ""); if (cache.has(k)) return cache.get(k); const r = fn(P, ...a); if (cache.size > 64) cache.clear(); cache.set(k, r); return r; }; };
  const camGuided = memoP(camGuidedRaw, true);
  function camGuidedRaw(P) {
    if (!(P.opt_cam > 0.5) || driveMode(P) !== 1) return null;
    const g = guideGeo(P), ch = chamferGeo(P), r = P.d_pin / 2, fam = camFam(P);
    const al = P.cam_alpha * D2R, ta = Math.tan(al), c = P.cam_c, m = P.cam_msync, trav = g.travel, dyc = Math.min(ch.dy, P.dog_b);
    const clr = (eta, u) => { const Xt = -P.c_tip + u, Yb = eta - P.dog_b; return polyDist([[Xt, eta], [Xt, Yb + dyc], [Xt + ch.dx, Yb], [Xt + 3000, Yb], [Xt + 3000, eta]], 0, 0) - r; };
    const uNeed = (eta) => { if (clr(eta, 0) >= m) return 0; let lo = 0, hi = trav + 60; if (clr(eta, hi) < m) return Infinity; for (let i = 0; i < 26; i++) { const mid = (lo + hi) / 2; if (clr(eta, mid) >= m) hi = mid; else lo = mid; } return hi; };
    const eta0 = -r - P.s_free, eta1 = g.chord - r, etaEnd = eta0 + P.cam_dwell, uPk = trav, n = 300;
    const etas = Array.from({ length: n + 1 }, (_, i) => eta0 + (eta1 - eta0) * i / n), need = etas.map(uNeed);
    const needMax = Math.max(0, ...need.map((x) => (isFinite(x) ? x : 1e9)));
    let etaX1 = -Infinity; etas.forEach((e, i) => { if (need[i] > c) etaX1 = Math.max(etaX1, e - (uPk - Math.min(need[i], uPk)) / ta); });
    const hasPk = isFinite(etaX1);
    if (hasPk) etaX1 += 5;                                              // 5 mm de holgura de fabricación en la entrada del bolsillo (no trabaja: la uña está en la toma)
    const uCam = (e) => (!hasPk || e <= etaEnd ? c : Math.max(c, Math.min(uPk, c + ta * (e - etaEnd), uPk - ta * (e - etaX1))));
    const etaR1 = etaEnd + (uPk - c) / ta, etaE0 = hasPk ? etaX1 + (uPk - c) / ta : -Infinity, etaAp = (uPk - c + ta * (etaEnd + etaX1)) / (2 * ta);
    // sincronía: holgura con la uña contra la rampa de reenganche (lado retraído del bolsillo); la entrada se informa aparte
    let sync = Infinity, etaSync = eta0, syncIn = Infinity; etas.forEach((e) => { const s = clr(e, uCam(e)); if (e <= Math.min(etaR1, etaAp)) { if (s < sync) { sync = s; etaSync = e; } } else syncIn = Math.min(syncIn, s); });
    { const de = (eta1 - eta0) / n, e0 = etaSync; for (let k = -40; k <= 40; k++) { const e = e0 + de * k / 40; if (e < eta0 || e > Math.min(etaR1, etaAp)) continue; const s = clr(e, uCam(e)); if (s < sync) { sync = s; etaSync = e; } } }   // refinamiento local del mínimo
    const prof = !hasPk ? [[eta0 - 20, c], [eta1 + 20, c]] : etaAp < etaR1 ? [[eta0 - 20, c], [etaEnd, c], [etaAp, c + ta * (etaAp - etaEnd)], [etaE0, c], [Math.max(etaE0, eta1) + 20, c]]
      : [[eta0 - 20, c], [etaEnd, c], [etaR1, uPk], [etaX1, uPk], [etaE0, c], [Math.max(etaE0, eta1) + 20, c]];
    const cover = hasPk ? Math.max(0, Math.min(1, (eta1 - Math.max(-r, etaE0)) / g.chord)) : 1;
    // alzado: perno vertical fijo en la uña, guiado en y por la ranura de la tapa del alojamiento; pletina-leva sobre el patín
    const zc0 = g.zc0, zU = zc0 + P.dog_h / 2, zS = zU + 1 + P.t_pk / 2, zPb = g.shoeTop + 2, zTop = zc0 + P.h_disc / 2;
    // rodillo apoyado abajo (2 mm sobre la cara inferior del riel: chaflán del canto) y retenido arriba por una arandela de tope de 4 mm con tornillo axial en el extremo
    // del perno (10-11-2026: el perno anterior terminaba en el eje del rodillo); el conjunto queda bajo la cara superior del riel y de la mesa (la carga puede volar sobre el borde)
    const hRet = 4, zF = zPb + 2 + P.cam_bf / 2, zRetTop = zF + P.cam_bf / 2 + hRet, hAvail = Math.min(P.cam_t, zTop - zPb) - 1, lPerno = 30 + (zF + P.cam_bf / 2 - zU);
    const xFp0 = P.x_g - P.w_s / 2 + 10 + P.cam_dp / 2, xE0 = xFp0 + P.cam_df / 2 + c, xPo = xE0 + P.cam_w, wNet = P.cam_w - uPk, lFp = zF - zU;
    const Lsp = g.L_bed + P.cam_ls, Lpl = g.L_bed + 2 * P.cam_ls, hPed = zPb - (P.t_base + P.t_bed), yOf = (e) => g.y_pin0 + e - P.dog_b / 2;
    // tapa de cada pata: pernos riel–pórtico ISO 4762 roscados en taladro ciego (remanente 3 mm, rosca útil = taladro − 2·P) con engrane ≥ 1,25·d (VDI 2230, 10.9 en S355):
    // espesor de la tapa = el menor múltiplo de 5 mm que admite un largo comercial con 1,25·d ≤ l_e ≤ rosca útil − 2 (antes 15 mm: engrane < 1,25·d)
    const pB = PITCH[Math.round(P.cam_db)] || 0.15 * P.cam_db, L4762 = [30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120], capLe = (tc) => tc - 3 - 2 * pB - 2;
    let tCap = 15, Lb = null; for (; tCap <= 100; tCap += 5) { Lb = L4762.filter((x) => x - P.cam_t <= capLe(tCap) && x - P.cam_t >= 1.25 * P.cam_db).pop(); if (Lb) break; }
    if (!Lb) { tCap = 100; Lb = L4762.filter((x) => x - P.cam_t <= capLe(tCap)).pop() || L4762[0]; }
    const leCap = Lb - P.cam_t, huCap = tCap - 3 - 2 * pB;
    // fuerzas (N): cilindro tirando a p_ret con la uña trabada; cotas sin roce (máximas): rampa N = F_ret/sen α; nivel de toma (chaflán sobre B) N = F_ret/tan β
    const Aann = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2), Fret = Aann * P.p_ret / 10, bR = P.beta_ch * D2R;
    const NR = Fret / Math.sin(al), NRx = Fret / ta, NT = Fret / Math.tan(bR), Nd = Math.max(NR, NT);
    const muC = fam.f === 1 ? P.mu_roll : fam.mu, muP = P.mu_ret, kt = 1 + 2 * Math.max(0, zF - zS) / P.dog_h, kp = 1 - 2 * muP * (zF - zc0) / P.L_in;
    const lockDem = muP * kt * (Math.sin(al) + muC * Math.cos(al)), lockCap = (Math.cos(al) - muC * Math.sin(al)) * kp;
    const ys = etas.map(yOf), kM = Math.max(...ys.map((y) => Math.max(0, (Lsp / 2 + y) * (Lsp / 2 - y)) / Lsp)), kR = Math.max(...ys.map((y) => Math.max(Lsp / 2 + y, Lsp / 2 - y) / Lsp));
    const Sn = P.cam_t * Math.max(wNet, 1e-6) ** 2 / 6, An = P.cam_t * Math.max(wNet, 1e-6);
    const sigPl = Math.max(NT * kM / Sn, NRx * kM / Sn + Fret / An);
    // pórtico de cada apoyo: dos patas (x = x_g ∓ (D_cuerpo/2 + 5 + b/2)) soldadas a un asiento sobre la bancada prolongada y ensanchada, que dejan pasar el cuerpo
    // del cilindro bajo el pórtico trasero; el riel (con una aleta hacia adentro en la zona del apoyo, donde el seguidor no llega) se emperna a las tapas de las patas.
    const px = P.cam_px, ls = P.cam_ls, xL = P.x_g - P.D_body / 2 - 5 - px / 2, xR = P.x_g + P.D_body / 2 + 5 + px / 2, capW = Math.max(px, 2 * J34M(P.cam_db)), aw = 0.707 * P.cam_wf;
    const Sx = aw * (ls * px + px * px / 3), Sy = aw * (px * ls + ls * ls / 3), Lw = aw * 2 * (px + ls), Fwc = P.FEXX * 0.60 / (1.20 * P.Nd), wExt0 = (xR + px / 2) - (xL - px / 2);
    const cases = [[NRx * kR, Fret], [NT * kR, 0]].map(([Rx, Ry]) => {
      const sPed = (Rx / 2) * hPed / (ls * px * px / 6) + (Ry / 2) * hPed / (px * ls * ls / 6);
      const fW = Math.hypot((Rx / 2) * hPed / Sx + (Ry / 2) * hPed / Sy, Math.hypot(Rx, Ry) / 2 / Lw);
      const V = Math.hypot(Rx, Ry) / P.cam_nb, b = boltJ3(P, P.cam_db, V, 0), Rn = 2.4 * P.cam_db * P.cam_t * P.Fu_cam, RnC = 2.4 * P.cam_db * leCap * P.Fu;
      // pata–tapa (filetes a ambos lados a lo largo de l, w = mínimo AWS para la parte más gruesa) con R a la altura del riel (brazo = t_tapa); prolongación–base (perimetral w_bed_f) con R·(z_riel − t_base)
      const wPT = wMin(Math.max(px, tCap)), aPT = 0.707 * wPT, ePT = tCap, fPT = Math.hypot((Rx / 2) * ePT / (aPT * ls * px) + (Ry / 2) * ePT / (aPT * ls * ls / 3), Math.hypot(Rx, Ry) / 2 / (2 * aPT * ls));
      const aEx = 0.707 * P.w_bed_f, bEx = Math.max(wExt0, P.w_bed), hEx = zPb - P.t_base, SxE = aEx * (ls * bEx + bEx * bEx / 3), SyE = aEx * (bEx * ls + ls * ls / 3), LwE = aEx * 2 * (bEx + ls);
      const fEx = Math.hypot(Rx * hEx / SxE + Ry * hEx / SyE, Math.hypot(Rx, Ry) / LwE);
      return { Rx, Ry, sPed, fW, V, b, Rn, RnC, fuV: b.frv / b.capV, fuB: V / (Rn / 2), fuC: V / (RnC / 2), wPT, fPT, fEx };
    });
    const cg = cases.reduce((a, b) => (Math.max(b.fuV, b.fuB, b.fuC) > Math.max(a.fuV, a.fuB, a.fuC) ? b : a)), cp = cases.reduce((a, b) => (b.sPed > a.sPed ? b : a)), cw = cases.reduce((a, b) => (b.fW > a.fW ? b : a)), cpt = cases.reduce((a, b) => (b.fPT > a.fPT ? b : a)), cex = cases.reduce((a, b) => (b.fEx > a.fEx ? b : a));
    let Apk = 0; for (let i = 1; i <= n; i++) Apk += 0.5 * ((uCam(etas[i]) - c) + (uCam(etas[i - 1]) - c)) * (etas[i] - etas[i - 1]);
    const flag = Math.max(0, xE0 - (xL - capW / 2)), wExt = (xR + px / 2) - (xL - px / 2);
    const mPlate = RHO * P.cam_t * Math.max(0, P.cam_w * Lpl - Apk + 2 * ls * flag), mPed = 4 * RHO * (px * ls * Math.max(0, hPed - tCap) + capW * ls * tCap);
    const mExt = 2 * RHO * ls * (Math.max(wExt, P.w_bed) * P.t_bed - P.w_slot * P.h_slot - P.w_tee * P.h_tee);
    const mFol = RHO * (Math.PI / 4 * P.cam_df ** 2 * P.cam_bf + Math.PI / 4 * P.cam_dp ** 2 * lPerno);
    return { clr, uNeed, uCam, fam, muC, muP, kt, kp, lockDem, lockCap, alpha: P.cam_alpha, c, m, travel: trav, uPk, eta0, eta1, etaEnd, etaR1, etaX1, etaE0, etaAp, hasPk, needMax, sync, syncIn, etaSync, cover, prof,
      perfil_y: prof.map(([e, u]) => ({ eta: e, y: yOf(e), u, x_canto: xE0 + (u - c) })), need: etas.map((e, i) => ({ eta: e, u_need: need[i], u_leva: uCam(e) })),
      zc0, zU, zS, zPb, zF, zTop, xFp0, xE0, xPo, wNet, lFp, Lsp, Lpl, hPed, Fret, NR, NRx, NT, Nd, sigPl, kM, kR, bolts: cg, ped: cp, weld: cw, weldPT: cpt, weldEx: cex, Fwc, Apk, portico: { xL, xR, px, ls, capW, flag, wExt, tCap, Lb, leCap, huCap, pB },
      hRet, zRetTop, hAvail, lPerno,
      m: { plate: mPlate, ped: mPed, ext: mExt, fol: mFol, one: mPlate + mPed + mExt + mFol, total: P.n_cyl * (mPlate + mPed + mExt + mFol) } };
  }

  /* ---------------- Tarea 2: accionamiento pivotado con guía de leva (tipo KIET) ---------------- */
  // Planta: O = centro, giro antihorario (θ creciente); ojal E = R_E·(cos φ, sin φ); pasador tomado P(θ) = R·(cos θ, sin θ).
  // El bloque-uña gira libre en Q y la normal del contacto pasa por el centro del pasador: E, Q y P alineados, Q = P + L_qp·(E − P)/|E − P|.
  // u = (P − E)/|P − E| (empuje), t = k × u (hacia el lado de O), L = |P − E| − L_qp (ojal–ojal), brazo a = (P × u)_z.
  // Deslizamiento en el contacto: dψ/dθ = (P·u)/|P − E| y v_s = −r·(1 − dψ/dθ) (por unidad de ω). El bloque gira libre en Q, de modo que la resultante
  // del contacto (normal + roce) pasa por Q: el roce no agrega un momento propio sino que inclina la resultante; por potencia virtual
  // F_cil·η·dL/dθ = T/n + μ_s·F_n·|v_s| (+ roce de la leva) con dL/dθ = a, el brazo efectivo es a_ef = a − μ_s·|v_s|.
  function unaDist(P, x, y, Q, u, Lqp) {   // distancia de (x, y) al bloque-uña: cuerpo acodado (e_cr hacia −t), tramo de la cara centrado y cubo del pasador Q
    const r = P.d_pin / 2, s2 = Lqp - r, s1 = s2 - P.pv_lf, eb = P.pv_dq / 2 + 25, tx = -u[1], ty = u[0];
    return Math.min(rectDist(x, y, Q[0] - P.pv_ecr * tx, Q[1] - P.pv_ecr * ty, u[0], u[1], -eb, s1, P.pv_bu), rectDist(x, y, Q[0], Q[1], u[0], u[1], s1, s2, P.pv_bf), Math.hypot(x - Q[0], y - Q[1]) - eb);
  }
  function segDistO(ax, ay, bx, by) { const dx = bx - ax, dy = by - ay, t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(ax + t * dx, ay + t * dy); }
  function pivBaseLimit(P) { const ph = P.pv_phE * D2R, Bh = P.B / 2 - P.rim_t - 5; return (Bh - P.pv_box / 2) / Math.max(Math.abs(Math.cos(ph)), Math.abs(Math.sin(ph))); }
  function pivKin(P, RE, Lqp, n) {
    n = n || 60;
    const R = P.R_pin, r = P.d_pin / 2, pitch = 2 * Math.PI / P.N_pin, ph = P.pv_phE * D2R, E = [RE * Math.cos(ph), RE * Math.sin(ph)];
    const Ls = P.L0 + P.s_free, tgt = Ls + Lqp, ca = (R * R + RE * RE - tgt * tgt) / (2 * R * RE);
    if (!(RE > R + r) || !(Lqp > r) || !(Math.abs(ca) <= 1)) return { ok: false, msg: "Accionamiento pivotado: no hay posición de toma con R_E = " + Math.round(RE) + " mm y L_qp = " + Math.round(Lqp) + " mm (|P − E| = L0 + s_libre + L_qp no tiene solución)", E, RE, Lqp };
    const ths = ph + Math.acos(ca), the = ths + pitch;
    const at = (th) => {
      const Px = R * Math.cos(th), Py = R * Math.sin(th), dx = Px - E[0], dy = Py - E[1], d = Math.hypot(dx, dy), u = [dx / d, dy / d], t = [-u[1], u[0]];
      const Q = [Px - Lqp * u[0], Py - Lqp * u[1]], a = Px * u[1] - Py * u[0], Pu = Px * u[0] + Py * u[1], Cu = Pu - r, dpsi = Pu / d, vs = -r * (1 - dpsi);
      return { th, P: [Px, Py], d, u, t, Q, L: d - Lqp, psi: Math.atan2(u[1], u[0]), a, ft: a / R, fr: Pu / R, C: [Px - r * u[0], Py - r * u[1]], Cu, dpsi, vs, Qr: Math.hypot(Q[0], Q[1]) };
    };
    const pts = [];
    let aMin = Infinity, aMax = -Infinity, aEffMin = Infinity, QrMin = Infinity, clrB = Infinity, body = Infinity, Lend = -Infinity;
    for (let i = 0; i <= n; i++) {
      const q = at(ths + pitch * i / n), Bp = [R * Math.cos(q.th - pitch), R * Math.sin(q.th - pitch)], Cp = [R * Math.cos(q.th + pitch), R * Math.sin(q.th + pitch)];
      q.aEff = q.a - P.mu_s * Math.abs(q.vs);   // potencia virtual: F_cil·η·dL/dθ = T/n + μ_s·F_n·|v_s| (+ roce de la leva), dL/dθ = a
      q.clrB = Math.min(unaDist(P, Bp[0], Bp[1], q.Q, q.u, Lqp), unaDist(P, Cp[0], Cp[1], q.Q, q.u, Lqp)) - r;
      q.body = segDistO(E[0] + P.e_body * q.u[0], E[1] + P.e_body * q.u[1], E[0] + (P.L0 - P.c_rod) * q.u[0], E[1] + (P.L0 - P.c_rod) * q.u[1]) - P.D_body / 2 - P.D_top / 2;
      aMin = Math.min(aMin, q.a); aMax = Math.max(aMax, q.a); aEffMin = Math.min(aEffMin, q.aEff); QrMin = Math.min(QrMin, q.Qr); clrB = Math.min(clrB, q.clrB); body = Math.min(body, q.body); Lend = Math.max(Lend, q.L);
      pts.push(q);
    }
    const sReq = Lend - P.L0, Qclr = QrMin - P.pv_dq / 2 - P.D_top / 2, eBox = Math.max(Math.abs(E[0]), Math.abs(E[1])) + P.pv_box / 2;
    const fg = P.pv_fugeo > 0 ? P.pv_fugeo : 1, Bh = P.B / 2 - P.rim_t - 5;   // holguras geométricas con FU objetivo (cajón en la base, Q fuera de la mesa)
    const feas = (P.D_top / 2 + P.pv_dq / 2 + P.pv_cQ) <= fg * QrMin && clrB >= P.pv_cB && body >= P.pv_cc && sReq + P.s_margin <= P.stroke && eBox <= fg * Bh;
    return { ok: true, mode: 2, E, RE, Lqp, phE: P.pv_phE, ths, the, pitch, pts, at, aMin, aMax, aEffMin, QrMin, Qclr, clrB, body, Lend, Ls, sReq, eBox, feas };
  }
  // Sugerencia de E (radio R_E sobre el ángulo φ y largo L_qp): maximiza el brazo efectivo mínimo con roce (a + μ_s·b_r) respetando la base (cajón del ojal),
  // L0 y la carrera (s_req + margen ≤ carrera), el pasador Q fuera de la mesa, el cuerpo del cilindro fuera de la mesa y la holgura con el pasador siguiente.
  const suggestCache = new Map();
  function suggestE(P) {
    const key = ["pv_fugeo", "R_pin", "d_pin", "N_pin", "pv_phE", "L0", "s_free", "stroke", "s_margin", "B", "rim_t", "pv_box", "pv_dq", "D_top", "pv_cQ", "pv_cB", "pv_cc", "e_body", "c_rod", "D_body", "mu_s", "pv_bu", "pv_bf", "pv_lf", "pv_ecr"].map((k) => P[k]).join("|");
    if (suggestCache.has(key)) return suggestCache.get(key);
    const REmax = Math.floor(pivBaseLimit(P)), REmin = Math.ceil(P.R_pin + P.d_pin), score = (k) => (k.ok && k.feas ? k.aEffMin : -Infinity);
    let best = { s: -Infinity, RE: NaN, Lqp: NaN };
    for (let RE = REmin; RE <= REmax; RE += 10) for (let Lqp = 100; Lqp <= 1000; Lqp += 10) { const s = score(pivKin(P, RE, Lqp, 20)); if (s > best.s) best = { s, RE, Lqp }; }
    if (isFinite(best.s)) {
      const c0 = best;
      for (let RE = Math.max(REmin, c0.RE - 10); RE <= Math.min(REmax, c0.RE + 10); RE += 1) for (let Lqp = c0.Lqp - 10; Lqp <= c0.Lqp + 10; Lqp += 1) { const s = score(pivKin(P, RE, Lqp, 40)); if (s > best.s) best = { s, RE, Lqp }; }
    }
    const out = { ok: isFinite(best.s), RE: best.RE, Lqp: best.Lqp, aEffMin: best.s, REmax, REmin };
    if (suggestCache.size > 50) suggestCache.clear();
    suggestCache.set(key, out);
    return out;
  }
  const kinPivFull = memoP((P) => kinPivRaw(P, false), true), kinPivLite = memoP((P) => kinPivRaw(P, true), false);
  function kinPiv(P, lite) { return lite ? kinPivLite(P) : kinPivFull(P); }
  function kinPivRaw(P, lite) {   // lite: sin la cota z del eje (depende de la interfaz; tmaxOf la evita para no recursar)
    const sg = P.pv_RE > 0 && P.pv_Lqp > 0 ? null : suggestE(P);
    const RE = P.pv_RE > 0 ? P.pv_RE : sg.RE, Lqp = P.pv_Lqp > 0 ? P.pv_Lqp : sg.Lqp;
    const K = pivKin(P, RE, Lqp, 60);
    if (!K.ok) return Object.assign(K, { pts: [], armMin: 0, s_req: NaN, margin: NaN, auto: !!sg });
    const R = P.R_pin, chord = 2 * R * Math.sin(K.pitch / 2);
    return Object.assign(K, { auto: !!sg, sugerencia: sg, armMin: K.aMin, armMax: K.aMax, s_req: K.sReq, margin: P.stroke - K.sReq, chord, gap: chord - P.d_pin, radial: 0, zc0: lite ? NaN : hAxis(P) + P.t_base, pitch: K.pitch });
  }
  /* ---------------- Placa-guía curva del modo pivotado (rediseño 09-11-2026; docs/qa/guia_curva_KIET/cambios.md) ---------------- */
  // Geometría plana de tramos tangentes {tipo: "linea" | "arco", p0, p1, centro, radio, sentido: "antihorario" | "horario"} (sentido de recorrido de p0 a p1).
  const GV = (() => {
    const add = (a, b) => [a[0] + b[0], a[1] + b[1]], sub = (a, b) => [a[0] - b[0], a[1] - b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1], crs = (a, b) => a[0] * b[1] - a[1] * b[0], nrm = (a) => Math.hypot(a[0], a[1]), unit = (a) => mul(a, 1 / nrm(a));
    const left = (a) => [-a[1], a[0]], right = (a) => [a[1], -a[0]], rot = (a, t) => [a[0] * Math.cos(t) - a[1] * Math.sin(t), a[0] * Math.sin(t) + a[1] * Math.cos(t)];
    const sg = (s) => (s.sentido === "antihorario" ? 1 : -1);
    function arcFrom(p0, t0, p1) {   // arco (o recta) desde p0, tangente t0, hasta p1
      const n0 = left(t0), ch = sub(p1, p0), den = 2 * dot(n0, ch);
      if (Math.abs(den) < 1e-9 * nrm(ch)) return { tipo: "linea", p0, p1 };
      const k = dot(ch, ch) / den;
      return { tipo: "arco", p0, p1, centro: add(p0, mul(n0, k)), radio: Math.abs(k), sentido: k > 0 ? "antihorario" : "horario" };
    }
    function biarc(p0, t0, p1, t1) {   // biarco de brazos iguales: dos arcos tangentes entre sí y a (p0, t0) y (p1, t1)
      const v = sub(p1, p0), t = add(t0, t1), a = 2 * (1 - dot(t0, t1)), b = dot(v, t);
      const d = a < 1e-12 ? dot(v, v) / (4 * dot(v, t1)) : (-b + Math.sqrt(b * b + a * dot(v, v))) / a;
      const pm = mul(add(add(p0, mul(t0, d)), sub(p1, mul(t1, d))), 0.5), s1 = arcFrom(p0, t0, pm), r2 = arcFrom(p1, mul(t1, -1), pm);
      return [s1, r2.tipo === "linea" ? { tipo: "linea", p0: pm, p1 } : { tipo: "arco", p0: pm, p1, centro: r2.centro, radio: r2.radio, sentido: r2.sentido === "antihorario" ? "horario" : "antihorario" }];
    }
    function tan(s, p) { if (s.tipo === "linea") return unit(sub(s.p1, s.p0)); const v = sub(p, s.centro); return mul(left(v), sg(s) / nrm(v)); }
    function sweep(s) { const a0 = Math.atan2(s.p0[1] - s.centro[1], s.p0[0] - s.centro[0]), a1 = Math.atan2(s.p1[1] - s.centro[1], s.p1[0] - s.centro[0]); let d = sg(s) * (a1 - a0); while (d < 0) d += 2 * Math.PI; while (d >= 2 * Math.PI) d -= 2 * Math.PI; return { a0, d }; }
    const len = (s) => (s.tipo === "linea" ? nrm(sub(s.p1, s.p0)) : s.radio * sweep(s).d);
    function at(s, f) { if (s.tipo === "linea") return add(s.p0, mul(sub(s.p1, s.p0), f)); const { a0, d } = sweep(s), a = a0 + sg(s) * d * f; return add(s.centro, mul([Math.cos(a), Math.sin(a)], s.radio)); }
    function pts(s, tol, step) {   // polilínea con flecha ≤ tol (y paso ≤ step si se pide); incluye p0 y p1 exactos
      const L = len(s); let n = 1;
      if (s.tipo === "arco") n = Math.ceil(sweep(s).d / (2 * Math.acos(Math.max(-1, 1 - tol / s.radio))) - 1e-9);
      if (step) n = Math.max(n, Math.ceil(L / step));
      n = Math.max(1, n);
      return Array.from({ length: n + 1 }, (_, i) => (i === 0 ? s.p0 : i === n ? s.p1 : at(s, i / n)));
    }
    function chain(S, tol, step) { const o = []; S.forEach((s, i) => { const q = pts(s, tol, step); o.push(...(i ? q.slice(1) : q)); }); return o; }
    function offset(s, d) {   // desplazamiento d a la derecha del recorrido (arcos concéntricos: radio ± d)
      const q0 = add(s.p0, mul(right(tan(s, s.p0)), d)), q1 = add(s.p1, mul(right(tan(s, s.p1)), d));
      return s.tipo === "linea" ? { tipo: "linea", p0: q0, p1: q1 } : { tipo: "arco", p0: q0, p1: q1, centro: s.centro, radio: s.radio + sg(s) * d, sentido: s.sentido };
    }
    function dist(s, p) {
      if (s.tipo === "linea") { const e = sub(s.p1, s.p0), t = Math.max(0, Math.min(1, dot(sub(p, s.p0), e) / dot(e, e))); return nrm(sub(p, add(s.p0, mul(e, t)))); }
      const { a0, d } = sweep(s); let a = sg(s) * (Math.atan2(p[1] - s.centro[1], p[0] - s.centro[0]) - a0); while (a < 0) a += 2 * Math.PI; while (a >= 2 * Math.PI) a -= 2 * Math.PI;
      return a <= d + 1e-12 ? Math.abs(nrm(sub(p, s.centro)) - s.radio) : Math.min(nrm(sub(p, s.p0)), nrm(sub(p, s.p1)));
    }
    function tr(s, f, mir) { const o = Object.assign({}, s, { p0: f(s.p0), p1: f(s.p1) }); if (s.tipo === "arco") { o.centro = f(s.centro); if (mir) o.sentido = s.sentido === "antihorario" ? "horario" : "antihorario"; } return o; }
    function g1(S) { let gap = 0, ang = 0, dk = 0; const k = (s) => (s.tipo === "linea" ? 0 : sg(s) / s.radio); for (let i = 1; i < S.length; i++) { const a = S[i - 1], b = S[i], t0 = tan(a, a.p1), t1 = tan(b, b.p0); gap = Math.max(gap, nrm(sub(a.p1, b.p0))); ang = Math.max(ang, Math.abs(Math.atan2(crs(t0, t1), dot(t0, t1)))); dk = Math.max(dk, Math.abs(k(a) - k(b))); } return { gap, ang, dk }; }
    function lineCircle(p, t, c, R) {   // parámetros λ de p + λt sobre la circunferencia (c, R)
      const d = sub(p, c), b = dot(d, t), q = dot(d, d) - R * R, D = b * b - q; if (D < 0) return []; const s = Math.sqrt(D); return [-b - s, -b + s];
    }
    function circles(c0, r0, c1, r1) {   // intersecciones de dos circunferencias
      const d = nrm(sub(c1, c0)); if (d > r0 + r1 || d < Math.abs(r0 - r1) || d === 0) return [];
      const a = (r0 * r0 - r1 * r1 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, r0 * r0 - a * a)), e = unit(sub(c1, c0)), m = add(c0, mul(e, a));
      return [add(m, mul(left(e), h)), sub(m, mul(left(e), h))];
    }
    const area = (pl) => { let A = 0; for (let i = 0; i < pl.length; i++) { const p = pl[i], q = pl[(i + 1) % pl.length]; A += p[0] * q[1] - q[0] * p[1]; } return A / 2; };
    return { add, sub, mul, dot, crs, nrm, unit, left, right, rot, arcFrom, biarc, tan, len, at, pts, chain, offset, dist, tr, g1, lineCircle, circles, area, sweep };
  })();
  // Placa-guía del modo pivotado (cilindro 1, giro antihorario; el resto por rotación de 180° y reflexión respecto de la diagonal).
  // w = desplazamiento lateral de Q hacia afuera (−t) respecto de la recta E–P al inicio: Q(L, w) = E + L·û(ψ₀ − w/L).
  // Seguidor = extremo inferior del pasador Q (radio r_f = d_Q/2); su centro recorre la trayectoria W(L) y el canto es el desplazamiento exacto a r_f hacia la placa.
  // Requisitos de W: (1) retorno: W ≥ w_nec(L; m + δ) (sincronía con margen, tolerancia de posición del canto y crecimiento del círculo de pasadores a 80 °C);
  // (2) empuje: la rodilla E–Q–P es inestable en compresión (rigidez lateral −F·(1/L + 1/L_qp)) y el roce de la cara empuja el bloque hacia afuera:
  // Q se apoya en el canto, de modo que W ≥ w_emp + c; (3) el retorno libre (Q a ψ constante tras el último contacto con el pasador) no toca el canto antes del flanco.
  // Trayectoria: flanco recto por (L0 + tramo, c) tangente por encima a w_nec (ángulo mínimo, ≤ α_máx), luego dos biarcos (hombro–cresta y bajada tangente a la
  // trayectoria de empuje en L_fin) elegidos por búsqueda en malla, y salida tangente. G1 por construcción; los arcos del canto son concéntricos con los del centro.
  const camPivMemo = memoP((P) => camPivRaw(P, kinPiv(P)), true);
  const pivSup = memoP((P) => { const K = kinPiv(P); return pivSupGeo(P, K, K.ok ? camPiv(P, K) : null); }, true);   // soporte del ojal E (geometría pura: memorizada)
  function camPiv(P, K) { return K && K.ok ? (K === kinPiv(P) ? camPivMemo(P) : camPivRaw(P, K)) : null; }
  function camPivRaw(P, K) {
    if (!K || !K.ok) return null;
    const V = GV, r = P.d_pin / 2, R = P.R_pin, E = K.E, Lqp = K.Lqp, psi0 = K.pts[0].psi, L0 = P.L0, Ls = K.Ls, Le = K.Lend, fam = camFam(P), rf = P.pv_dq / 2;
    const Qof = (L, w) => { const ps = psi0 - w / L, u = [Math.cos(ps), Math.sin(ps)]; return { Q: [E[0] + L * u[0], E[1] + L * u[1]], u }; };
    const toLW = (p) => { const d = V.sub(p, E), L = V.nrm(d); let a = psi0 - Math.atan2(d[1], d[0]); while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return [L, a * L]; };
    const pushW = K.pts.map((q) => [q.L, -q.L * (q.psi - psi0)]);
    const wPush = (L) => { if (L <= Ls) return 0; for (let i = 1; i < pushW.length; i++) if (L <= pushW[i][0]) { const [a0, b0] = pushW[i - 1], [a1, b1] = pushW[i]; return b0 + (b1 - b0) * (L - a0) / (a1 - a0); } return pushW[pushW.length - 1][1]; };
    const pins = [K.ths - K.pitch, K.ths].map((th) => [R * Math.cos(th), R * Math.sin(th)]);   // B y el anterior (A queda adelante de la cara: el retorno se aleja de él)
    const clrRet = (L, w) => { const { Q, u } = Qof(L, w); return Math.min(...pins.map((p) => unaDist(P, p[0], p[1], Q, u, Lqp))) - r; };
    const m = P.pv_msync, c = P.pv_c, rmin = P.pv_rmin, tolF = 0.3, gF = 2;
    const dT = alphaSteelMean(80, P.T_ref) * Math.max(0, 80 - P.T_ref) * R, dTol = P.pv_tolg + dT, md = m + dTol;
    const wAt = (L, mm) => {
      if (clrRet(L, 0) >= mm) return 0;
      let lo = 0, hi = NaN; for (let w = 4; w <= 400; w += 4) { if (clrRet(L, w) >= mm) { hi = w; break; } lo = w; }
      if (!isFinite(hi)) return Infinity;
      for (let i = 0; i < 26; i++) { const mid = (lo + hi) / 2; if (clrRet(L, mid) >= mm) hi = mid; else lo = mid; }
      return hi;
    };
    // L_B: desde aquí la cara del bloque alcanza el pasador B con menos que el margen (escalón de w_nec)
    let LB = Le; { let lo = L0, hi = Le; if (clrRet(L0, 0) >= md) { for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (clrRet(mid, 0) >= md) lo = mid; else hi = mid; } LB = hi; } else LB = L0; }
    const ng = Math.max(80, Math.ceil(Le - L0)), Lg = Array.from({ length: ng + 1 }, (_, i) => L0 + (Le - L0) * i / ng);
    const extra = [0, 0.05, 0.15, 0.35, 0.7, 1.2].map((d) => LB + d).filter((L) => L < Le);
    const LL = Lg.concat(extra).sort((a, b) => a - b), need = LL.map((L) => (L < LB ? 0 : wAt(L, md))), need0 = LL.map((L) => wAt(L, 0)), needM = LL.map((L) => wAt(L, m));
    const itp = (arr, L) => { if (L <= LL[0]) return arr[0]; for (let i = 1; i < LL.length; i++) if (L <= LL[i]) { if (arr === need && LL[i - 1] < LB && L >= LB) return arr[i]; return arr[i - 1] + (arr[i] - arr[i - 1]) * (L - LL[i - 1]) / (LL[i] - LL[i - 1]); } return arr[arr.length - 1]; };
    // retorno libre: la mesa queda en θ_fin; Q parte del canto en L_fin (w_emp + c) y conserva ψ salvo cuando el pasador lo empuja hacia afuera (holgura 0)
    let iPk = 0; LL.forEach((L, i) => { if (L >= LB && need0[i] > need0[iPk]) iPk = i; }); const Lpk = LL[iPk];
    const wFree = new Array(LL.length); { let ps = psi0 - (wPush(Le) + c) / Le; for (let i = LL.length - 1; i >= 0; i--) { const w = Math.max((psi0 - ps) * LL[i], need0[i]); wFree[i] = w; ps = psi0 - w / LL[i]; } }
    // requisito de W en grilla uniforme de 0,25 mm (consulta O(1)); la celda del escalón L_B toma el máximo de sus extremos
    const hq = 0.25, nq = Math.max(4, Math.ceil((Le - L0) / hq)), Lq = (i) => Math.min(Le, L0 + i * hq), reqA = new Float64Array(nq + 1), wpA = new Float64Array(nq + 1);
    for (let i = 0; i <= nq; i++) { const L = Lq(i); wpA[i] = wPush(L); reqA[i] = Math.max(L >= LB ? itp(need, L) + tolF : -Infinity, L >= Ls ? wpA[i] + c : -Infinity, c - 1e-9); }
    const gq = (A, L, step) => { if (L <= L0) return A[0]; if (L >= Le) return A[nq]; const x = (L - L0) / hq, i = Math.min(nq - 1, Math.floor(x)), f = x - i; return step && Lq(i) < LB && Lq(i + 1) >= LB ? Math.max(A[i], A[i + 1]) : A[i] + (A[i + 1] - A[i]) * f; };
    const req = (L) => gq(reqA, L, true), wpq = (L) => gq(wpA, L, false);
    // flanco recto por A1 = Q(L0 + tramo, c), ángulo φ_f a la derecha de la radial (hacia la placa): el mínimo que deja W ≥ w_nec, limitado a α_máx
    const LA = L0 + P.pv_dwell, A1 = Qof(LA, c).Q, uA = Qof(LA, c).u;
    const angTo = (p) => { const d = V.unit(V.sub(p, A1)); return Math.atan2(-V.crs(uA, d), V.dot(uA, d)); };
    let phiReq = 0, LT = Math.max(LB, LA + 1);
    for (let L = Math.max(LB, LA + 0.5); L <= Math.min(Le, LB + 90); L += 0.1) { const a = angTo(Qof(L, itp(need, L) + tolF).Q); if (a > phiReq) { phiReq = a; LT = L; } }
    const phiF = Math.min(phiReq + 1e-4, P.pv_alpha * D2R), dF = V.rot(uA, -phiF), capped = phiReq > P.pv_alpha * D2R;
    const flankAt = (L) => { const ls = V.lineCircle(A1, dF, E, L).filter((x) => x >= -1e-9); return ls.length ? V.add(A1, V.mul(dF, Math.min(...ls))) : null; };
    const pushDir = (L) => V.unit(V.sub(Qof(L, wPush(L) + c).Q, Qof(L - 1, wPush(L - 1) + c).Q));
    const N6 = Qof(Le, wPush(Le) + c).Q, t6 = pushDir(Le);
    const dirAng = (L, w, g) => V.unit(V.sub(Qof(L + 1e-3 * Math.cos(g), w + 1e-3 * Math.sin(g)).Q, Qof(L, w).Q));
    const evalS = (S) => {   // holgura mínima sobre el requisito, exceso medio, separación máxima del empuje y radios
      let worst = Infinity, sum = 0, nS = 0, gap = 0, Lp = -Infinity, back = false, rc = Infinity, rv = Infinity;
      for (const s of S) {
        const arc = s.tipo === "arco", sw = arc ? V.sweep(s) : null, k = s.sentido === "antihorario" ? 1 : -1, n = Math.max(1, Math.ceil(V.len(s) / 5));
        if (arc) { if (k < 0) rv = Math.min(rv, s.radio); else rc = Math.min(rc, s.radio); }
        for (let i = 1; i <= n; i++) {
          let x, y; if (arc) { const a = sw.a0 + k * sw.d * i / n; x = s.centro[0] + s.radio * Math.cos(a); y = s.centro[1] + s.radio * Math.sin(a); } else { x = s.p0[0] + (s.p1[0] - s.p0[0]) * i / n; y = s.p0[1] + (s.p1[1] - s.p0[1]) * i / n; }
          const dx = x - E[0], dy = y - E[1], L = Math.hypot(dx, dy); let aa = psi0 - Math.atan2(dy, dx); if (aa > Math.PI) aa -= 2 * Math.PI; else if (aa < -Math.PI) aa += 2 * Math.PI; const w = aa * L;
          if (L < Lp - 1e-6) back = true; if (L > Lp) Lp = L; const q = w - req(L); if (q < worst) worst = q; sum += q; nS++; if (L >= Ls) { const gg = w - wpq(L); if (gg > gap) gap = gg; }
        }
      }
      const ok = !back && rv >= rf + rmin;
      return { worst: back ? -1e9 : worst, mean: sum / nS, gap, rc, rv, ok, score: -(sum / nS) - 0.25 * gap + 0.02 * Math.min(rv, 400) + 0.02 * Math.min(rc, 200) };
    };
    // cargas que eligen el tope del flanco: empuje a calado con Q apoyado en el canto (máx h·F_calado·η) y atasco del retorno con el giro en E trabado
    // en el primer contacto del retorno libre (F_ret/sen φ₁); se toma el tope del flanco que hace mínima la mayor de las dos
    const eps = Math.asin(r * Math.sin(Math.atan(P.mu_s)) / Lqp), muc = fam.mu;
    const FeSt = Math.PI / 4 * P.D_bore ** 2 * P.p_relief / 10 * P.eta_c, FretN = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10;
    const eqQ = (Pp, q, tp) => { const uc = V.unit(V.sub(q, E)), b = V.unit(V.sub(Pp, q)), bp = V.rot(b, eps), nin = V.left(tp), a2 = V.mul(V.sub(nin, V.mul(tp, muc)), -1), det = V.crs(bp, a2); return { uc, b, bp, nin, fn: V.crs(uc, a2) / det, h: V.crs(bp, uc) / det, arm: V.crs(q, bp) }; };
    const rootOn = (pl, Pp) => { const Lc = V.nrm(V.sub(Pp, E)) - Lqp; let bs = null; for (let i = 1; i < pl.length; i++) { const f0 = V.nrm(V.sub(Pp, pl[i - 1])) - Lqp, f1 = V.nrm(V.sub(Pp, pl[i])) - Lqp; if (f0 * f1 > 0 || f0 === f1) continue; const q = V.add(pl[i - 1], V.mul(V.sub(pl[i], pl[i - 1]), f0 / (f0 - f1))), L = V.nrm(V.sub(q, E)); if (L >= Lc - 1 && (!bs || L < bs.L)) bs = { q, L, tp: V.unit(V.sub(pl[i], pl[i - 1])), Lc }; } return bs; };
    const loadsOf = (S, N2) => {
      const pl = V.chain([{ tipo: "linea", p0: A1, p1: N2 }].concat(S, [{ tipo: "linea", p0: N6, p1: V.add(N6, V.mul(t6, 20)) }]), 0.05, 1);
      let hMax = 0; for (let k = 0; k < K.pts.length; k += 3) { const q = K.pts[k], g = rootOn(pl, q.P); if (!g) return { J: Infinity }; const e = eqQ(q.P, g.q, g.tp); if (!(e.h > 0)) return { J: Infinity }; hMax = Math.max(hMax, e.h); }
      const lw = pl.map(toLW); let phi1 = 90;
      for (let i = iPk; i >= 0; i--) { const L = LL[i]; if (L < LA) break; let j = 1; while (j < lw.length - 1 && lw[j][0] < L) j++; const W = lw[j - 1][1] + (lw[j][1] - lw[j - 1][1]) * (L - lw[j - 1][0]) / ((lw[j][0] - lw[j - 1][0]) || 1); if (wFree[i] >= W) { const t = V.unit(V.sub(pl[j], pl[j - 1])), u = V.unit(V.sub(pl[j], E)); phi1 = Math.acos(Math.min(1, Math.abs(V.dot(t, u)))) / D2R; break; } }
      return { J: Math.max(hMax * FeSt, FretN / Math.sin(Math.max(1, phi1) * D2R)), hMax, phi1 };
    };
    const searchCrest = (L2, N2, coarse, seed) => {
      let best = null; const build = (L3, d3, g3) => { const w3 = req(L3) + d3, N3 = Qof(L3, w3).Q, t3 = dirAng(L3, w3, g3); return V.biarc(N2, dF, N3, t3).concat(V.biarc(N3, t3, N6, t6)); };
      const tryC = (L3, d3, g3) => { if (L3 <= L2 + 5 || L3 >= Le - 5 || d3 < 0) return; const S = build(L3, d3, g3), e = evalS(S), feas = e.ok && e.worst >= -1e-6; const key = feas ? 1e6 + e.score : e.worst - (e.ok ? 0 : 1e3); if (!best || key > best.key) best = { key, L3, d3, g3, S, e, feas }; };
      if (!seed) for (let L3 = L2 + 15; L3 <= Le - 15; L3 += coarse ? 10 : 5) for (const d3 of (coarse ? [0, 1.5, 4] : [0, 1, 2, 4, 6])) for (let g = -25; g <= 15; g += coarse ? 5 : 2.5) tryC(L3, d3, g * D2R);
      else { const b0 = seed; for (let L3 = b0.L3 - 6; L3 <= b0.L3 + 6; L3 += 1.5) for (let d3 = b0.d3 - 1; d3 <= b0.d3 + 1; d3 += 0.5) for (let g = b0.g3 / D2R - 4; g <= b0.g3 / D2R + 4; g += 1) tryC(L3, d3, g * D2R); }
      return best;
    };
    let pick = null;
    for (let L2c = LT; L2c <= Math.min(Le - 40, LT + 14); L2c += 2) {
      const N2c = flankAt(L2c); if (!N2c) break;
      const b = searchCrest(L2c, N2c, true); if (!b) continue;
      const ld = b.feas ? loadsOf(b.S, N2c) : { J: Infinity };
      const key = b.feas ? -ld.J + 1e-3 * b.e.score : -1e12 + b.e.worst;
      if (!pick || key > pick.key) pick = { key, L2: L2c, N2: N2c, b, ld };
    }
    const L2 = pick.L2, N2 = pick.N2, best = searchCrest(L2, N2, false, pick.b) || pick.b;
    const loads0 = loadsOf(best.S, N2);
    const roles = ["hombro", "cresta", "bajada", "empalme de empuje"];
    // marco de la placa: x' a lo largo de la cuerda A1–N6, y' hacia afuera (lado de la placa); lado interior por fuera de la mesa
    const xh = V.unit(V.sub(N6, A1)), yh = V.right(xh), X = (p) => V.dot(V.sub(p, A1), xh), Y = (p) => V.dot(V.sub(p, A1), yh);
    const lamB = rf + 20, N7 = V.add(N6, V.mul(t6, lamB));
    const core = [{ tipo: "linea", p0: A1, p1: N2 }].concat(best.S, [{ tipo: "linea", p0: N6, p1: N7 }]);
    const cTrav = V.chain(core.slice(0, -1), 0.1, 2), Rin = P.D_top / 2 + P.pv_cQ, yIn = Math.max(Math.min(...cTrav.map(Y)) - rf - 5, Y([0, 0]) + Rin);
    const Fe0 = V.add(A1, V.mul(V.right(dF), rf)), lamA = Math.max(5, (Y(Fe0) - yIn) / V.dot(dF, yh));
    const A0 = V.sub(A1, V.mul(dF, lamA));
    const tramos = [{ tipo: "linea", p0: A0, p1: N2, rol: "flanco de reenganche (con entrada tangente)" }].concat(best.S.map((s, i) => Object.assign(s, { rol: roles[i] })), [{ tipo: "linea", p0: N6, p1: N7, rol: "salida tangente" }]);
    const curv = (s) => (s.tipo !== "arco" ? null : s.sentido === "horario" ? "convexa" : "cóncava");   // vista desde el seguidor
    const canto = tramos.map((s) => Object.assign(V.offset(s, rf), { rol: s.rol, curvatura: curv(s) }));
    // cierre del bolsillo hacia la mesa: arco de cola (cóncavo, R = r_f + 15) que gira hasta la normal al lado interior, y recta hasta el lado interior
    const E7 = canto[canto.length - 1].p1, rt = rf + 15, Ct = V.add(E7, V.mul(V.left(t6), rt)), Pt = V.add(Ct, V.mul(xh, rt));
    if (Y(Pt) > yIn + 1) {
      canto.push({ tipo: "arco", p0: E7, p1: Pt, centro: Ct, radio: rt, sentido: "antihorario", rol: "cierre del bolsillo (sin contacto)", curvatura: "cóncava" });
      canto.push({ tipo: "linea", p0: Pt, p1: V.sub(Pt, V.mul(yh, Y(Pt) - yIn)), rol: "cierre del bolsillo (sin contacto)", curvatura: null });
    } else {   // el lado interior corta el arco de cola antes de la normal: el arco termina sobre el lado interior
      const arc0 = { tipo: "arco", p0: E7, p1: Pt, centro: Ct, radio: rt, sentido: "antihorario" }; let lo = 0, hi = 1; for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (Y(V.at(arc0, mid)) > yIn) lo = mid; else hi = mid; }
      canto.push({ tipo: "arco", p0: E7, p1: V.at(arc0, hi), centro: Ct, radio: rt, sentido: "antihorario", rol: "cierre del bolsillo (sin contacto)", curvatura: "cóncava" });
    }
    const Bq = canto[canto.length - 1].p1;
    const Aq = canto[0].p0;   // pie del flanco sobre el lado interior (diente del gancho)
    // rectángulo: ligamento ≥ pv_wlip detrás del canto; extremos con lugar para los pernos fuera del recorte
    const cPts = V.chain(canto, 0.1), yOut = Math.max(...cPts.map(Y)) + P.pv_wlip, db = P.pv_db, eb = Math.max(J34M(db), 1.5 * db);
    let xMin = Math.min(...cPts.map(X)) - 2 * eb, xMax = Math.max(...cPts.map(X)) + 2 * eb;
    const P2 = (x, y) => V.add(A1, V.add(V.mul(xh, x), V.mul(yh, y)));
    const contourOf = (x0, x1) => canto.concat([{ tipo: "linea", p0: Bq, p1: P2(x1, yIn) }, { tipo: "linea", p0: P2(x1, yIn), p1: P2(x1, yOut) }, { tipo: "linea", p0: P2(x1, yOut), p1: P2(x0, yOut) }, { tipo: "linea", p0: P2(x0, yOut), p1: P2(x0, yIn) }, { tipo: "linea", p0: P2(x0, yIn), p1: Aq }]).map((s) => Object.assign({ rol: "contorno de la placa" }, s));
    const nb = Math.max(2, Math.round(P.pv_nb)), boltsOf = (x0, x1) => {
      const inner = nb >= 4 ? [P2(x0 + eb, yIn + eb), P2(x1 - eb, yIn + eb)] : [], no = nb - inner.length;
      const outer = Array.from({ length: no }, (_, k) => P2(x0 + eb + (x1 - x0 - 2 * eb) * (no > 1 ? k / (no - 1) : 0.5), yOut - eb));
      return { outer, inner, all: outer.concat(inner) };
    };
    let contorno, bl;
    for (let it = 0; it < 40; it++) {   // alarga los extremos hasta que los pernos interiores quedan a ≥ e_mín del recorte
      contorno = contourOf(xMin, xMax); bl = boltsOf(xMin, xMax);
      const dA = bl.inner.length ? Math.min(...contorno.map((s) => V.dist(s, bl.inner[0]))) : Infinity, dB = bl.inner.length ? Math.min(...contorno.map((s) => V.dist(s, bl.inner[1]))) : Infinity;
      if (dA >= eb - 1e-9 && dB >= eb - 1e-9) break;
      if (dA < eb) xMin -= 5; if (dB < eb) xMax += 5;
    }
    const yMid = (yIn + yOut) / 2, dowels = [P2(xMin + eb, yMid), P2(xMax - eb, yMid)];
    const polC = V.chain(contorno, 0.1), polCanto = V.chain(canto, 0.1), polCentro = V.chain(tramos, 0.1);
    const travel = V.chain(core.slice(0, -1), 0.1).filter((p) => toLW(p)[0] >= L0 - 1e-9);
    const g1t = V.g1(tramos), g1c = V.g1(canto);
    // W(L): centro del seguidor sobre la trayectoria (intersección exacta de la circunferencia |Q − E| = L con el tramo que la contiene)
    const segL = tramos.map((s) => [toLW(s.p0)[0], toLW(s.p1)[0]]);
    const onPath = (L) => {
      for (let i = 0; i < tramos.length; i++) { const s = tramos[i], [a, b] = segL[i]; if (L < Math.min(a, b) - 1e-9 || L > Math.max(a, b) + 1e-9) continue;
        let cand = s.tipo === "linea" ? V.lineCircle(s.p0, V.unit(V.sub(s.p1, s.p0)), E, L).filter((x) => x >= -1e-6 && x <= V.len(s) + 1e-6).map((x) => V.add(s.p0, V.mul(V.unit(V.sub(s.p1, s.p0)), x))) : V.circles(s.centro, s.radio, E, L).filter((p) => V.dist(s, p) < 1e-6);
        if (cand.length) { const p = cand[0]; return { p, s, i, t: V.tan(s, p) }; } }
      const s = L < segL[0][0] ? tramos[0] : tramos[tramos.length - 1], p = L < segL[0][0] ? s.p0 : s.p1; return { p, s, i: L < segL[0][0] ? 0 : tramos.length - 1, t: V.tan(s, p) };
    };
    const wCam = (L) => toLW(onPath(L).p)[1];
    const phiAt = (L) => { const o = onPath(L), u = V.unit(V.sub(o.p, E)); return Math.acos(Math.min(1, Math.abs(V.dot(o.t, u)))) / D2R; };
    const radAt = (o) => (o.s.tipo === "arco" ? (o.s.sentido === "horario" ? o.s.radio - rf : -(o.s.radio + rf)) : Infinity);   // radio del canto en el contacto (+ convexo, − cóncavo)
    // empuje guiado: Q en la trayectoria con |P − Q| = L_qp (el bloque libre en Q toca el pasador con la cara); fuerzas por unidad de fuerza F en Q
    const dense = V.chain(core, 0.02, 1), dBlkG = pivBlkGeo(P, K).dBlk;
    function guidedAt(th) {
      const Pp = [R * Math.cos(th), R * Math.sin(th)], Lc = V.nrm(V.sub(Pp, E)) - Lqp; let bst = null;
      for (let i = 1; i < dense.length; i++) { const f0 = V.nrm(V.sub(Pp, dense[i - 1])) - Lqp, f1 = V.nrm(V.sub(Pp, dense[i])) - Lqp; if (f0 * f1 > 0 || f0 === f1) continue;
        const q = V.add(dense[i - 1], V.mul(V.sub(dense[i], dense[i - 1]), f0 / (f0 - f1))), Lq = V.nrm(V.sub(q, E)); if (Lq >= Lc - 1 && (!bst || Lq < bst.L)) bst = { q, L: Lq }; }
      if (!bst) return { ok: false, th };
      const o = onPath(bst.L), q = o.p, tp = o.t, { uc, b, bp, nin, fn, h, arm } = eqQ(Pp, q, tp);
      const Bp = [R * Math.cos(th - K.pitch), R * Math.sin(th - K.pitch)], Cp = [R * Math.cos(th + K.pitch), R * Math.sin(th + K.pitch)];
      const dB = dBlkG, clrB = Math.min(...[0, -dB].map((d) => { const bb = V.rot(b, d); return Math.min(unaDist(P, Bp[0], Bp[1], q, bb, Lqp), unaDist(P, Cp[0], Cp[1], q, bb, Lqp)); })) - r;   // bloque alineado y girado hacia afuera el ángulo de equilibrio con el roce (el deslizamiento del pasador respecto del bloque es hacia afuera en todo el empuje: el giro hacia adentro pediría que la mesa retroceda)
      const body = segDistO(E[0] + P.e_body * uc[0], E[1] + P.e_body * uc[1], E[0] + (P.L0 - P.c_rod) * uc[0], E[1] + (P.L0 - P.c_rod) * uc[1]) - P.D_body / 2 - P.D_top / 2;
      const w = toLW(q)[1];
      return { ok: true, th, P: Pp, Q: q, L: bst.L, Lc, w, gap: w - wPush(Lc), uc, b, bp, tp, nin, fn, h, arm, ft: V.crs(Pp, bp) / R, fr: V.dot(Pp, bp) / R, phi: Math.acos(Math.min(1, Math.abs(V.dot(tp, uc)))) / D2R,
        contacto: V.sub(q, V.mul(nin, rf)), Rc: radAt(o), tramo: o.i, clrB, body, psi: Math.atan2(uc[1], uc[0]) };
    }
    const push = K.pts.map((q) => guidedAt(q.th)), pOk = push.filter((g) => g.ok);
    const sReqG = pOk.length ? Math.max(K.sReq, ...pOk.map((g) => g.L - L0)) : K.sReq;
    // retorno (mesa detenida en θ_fin): Q sale del canto en L_fin, conserva ψ salvo que el pasador lo empuje (holgura 0) y el canto lo devuelve a la toma
    const ret = []; { let ps = psi0 - wCam(Le) / Le; const nR = Math.max(200, Math.ceil(2 * (Le - L0)));
      for (let k = 0; k <= nR; k++) { const L = Le - (Le - L0) * k / nR, Wv = wCam(L), w0 = L >= LB ? wAt(L, 0) : 0; let w = Math.max((psi0 - ps) * L, w0); const guia = w >= Wv - 1e-9; w = Math.min(w, Wv); ps = psi0 - w / L;
        ret.push({ L, w, W: Wv, guia, hol: clrRet(L, w), holW: clrRet(L, Wv), phi: phiAt(L) }); } }
    let iF = ret.length - 1; while (iF > 0 && ret[iF - 1].guia) iF--;   // primer contacto de la conducción final (de L_fin hacia L0)
    const first = ret[iF], drive = ret.slice(iF);
    let sync = Infinity, Lsync = L0; drive.forEach((q) => { if (q.holW < sync) { sync = q.holW; Lsync = q.L; } });
    { const h = (Le - L0) / Math.max(200, Math.ceil(2 * (Le - L0))); for (let k = -50; k <= 50; k++) { const L = Lsync + h * k / 50; if (L < L0 || L > first.L) continue; const s = clrRet(L, wCam(L)); if (s < sync) { sync = s; Lsync = L; } } }
    const syncOut = Math.min(...ret.slice(0, iF).map((q) => q.hol).concat([Infinity]));
    // puntos de la holgura mínima de sincronía (L_sync, Q contra el canto, bloque alineado con E–Q): punto del bloque (o del cubo de Q) y punto del pasador
    // más cercano (B, el siguiente), en el marco global del cilindro 1 en giro antihorario; la mesa está detenida en θ_fin durante el retorno
    const syncPts = (() => {
      const { Q, u } = Qof(Lsync, wCam(Lsync)), pol = unaPolys(P, Q, u, Lqp), eb = P.pv_dq / 2 + 25;
      const nearOn = (pl, c0) => { let best = null; for (let i = 0; i < pl.length; i++) { const a = pl[i], b = pl[(i + 1) % pl.length], e = V.sub(b, a), t = Math.max(0, Math.min(1, V.dot(V.sub(c0, a), e) / V.dot(e, e))), p = V.add(a, V.mul(e, t)), d = V.nrm(V.sub(c0, p)); if (!best || d < best.d) best = { p, d }; } return best; };
      let best = null;
      pins.forEach((c0, ip) => {
        [pol.cuerpo, pol.cara].forEach((pl) => { const q = nearOn(pl, c0); if (!best || q.d < best.d) best = Object.assign(q, { c0, ip }); });
        const dq = V.nrm(V.sub(c0, Q)); if (dq - eb < (best ? best.d : Infinity)) best = { p: V.add(Q, V.mul(V.sub(c0, Q), eb / dq)), d: dq - eb, c0, ip };
      });
      const pB = V.add(best.c0, V.mul(V.unit(V.sub(best.p, best.c0)), r));
      return { L: Lsync, s: Lsync - L0, Q, punto_bloque: best.p, punto_pasador: pB, centro_pasador: best.c0, pasador: best.ip === 1 ? "B (siguiente)" : "anterior", holgura: best.d - r, th: K.the };
    })();
    const kE = P.pv_muE * P.pv_dE / (2 * L0), lockR = (ph) => { const a = ph * D2R; return { dem: kE * (Math.sin(a) + fam.mu * Math.cos(a)), cap: Math.cos(a) - fam.mu * Math.sin(a) }; };
    const lockW = drive.reduce((acc, q) => { const l = lockR(q.phi), x = l.cap > 0 ? l.dem / l.cap : Infinity; return x > acc.x ? { x, dem: l.dem, cap: l.cap, phi: q.phi, L: q.L } : acc; }, { x: -Infinity });
    // placa: holguras y posición
    const Bh = P.B / 2 - P.rim_t - 5, ed = [E[0] / K.RE, E[1] / K.RE];
    const inBase = Math.max(...polC.map(([x, y]) => Math.max(Math.abs(x), Math.abs(y)))), side = polC.map(([x, y]) => x * ed[1] - y * ed[0]), sgn = Math.sign(side.reduce((a, b) => a + b, 0)) || 1;
    const diag = Math.min(...side.map((s) => s * sgn)), RinC = Math.min(...polC.map((p) => V.nrm(p))), boxClr = Math.min(...polC.map(([x, y]) => Math.max(Math.abs(x - E[0]), Math.abs(y - E[1])))) - P.pv_box / 2;
    const folClr = Math.min(...travel.map((p) => Math.min(...contorno.map((s) => V.dist(s, p))))) - rf;
    const Lb = canto.slice(0, tramos.length).reduce((a, s) => a + V.len(s), 0), area = Math.abs(V.area(polC));
    const bo = bl.outer.map(X).sort((a, b) => a - b); let sb = 0; for (let i = 1; i < bo.length; i++) sb = Math.max(sb, bo[i] - bo[i - 1]); sb = Math.max(sb, yOut - yIn - 2 * eb);
    const arcs = tramos.filter((s) => s.tipo === "arco"), arcsE = canto.slice(0, tramos.length).filter((s) => s.tipo === "arco");
    const rCentroConv = Math.min(Infinity, ...arcs.filter((s) => s.sentido === "horario").map((s) => s.radio)), rCantoConv = Math.min(Infinity, ...arcsE.filter((s) => s.curvatura === "convexa").map((s) => s.radio)), rCantoConc = Math.min(Infinity, ...arcsE.filter((s) => s.curvatura === "cóncava").map((s) => s.radio));
    const lig = (pt, nIn) => {   // ligamento: distancia desde el punto del canto, hacia la placa (−n_in), hasta el borde opuesto del contorno
      const dir = V.mul(nIn, -1); let best = Infinity; polC.forEach((a, i) => { const b = polC[(i + 1) % polC.length], e = V.sub(b, a), den = V.crs(dir, e); if (Math.abs(den) < 1e-12) return; const w = V.sub(a, pt), t = V.crs(w, e) / den, u = V.crs(w, dir) / den; if (t > 1 && u >= 0 && u <= 1) best = Math.min(best, t); }); return best;
    };
    const ligPush = pOk.map((g) => lig(g.contacto, g.nin)), firstPt = onPath(first.L), ligJam = lig(V.sub(firstPt.p, V.mul(V.left(firstPt.t), rf)), V.left(firstPt.t));
    const need_ = LL.map((L, i) => ({ L, w_nec: need[i], w_nec0: need0[i], w_nec_m: needM[i], w_emp: wPush(L), w_leva: wCam(L), w_libre: wFree[i] }));
    const wPk = Math.max(...need_.map((q) => q.w_leva)), cover = pOk.length ? pOk.filter((g) => g.gap <= c + 0.5).length / pOk.length : 1;
    const guia = { tramos, canto, contorno, polilinea_centro: polCentro, polilinea_canto: polCanto, polilinea_contorno: polC, polilinea_recorrido: travel, tol: 0.1,
      flanco: { phi_deg: phiF / D2R, phi_req_deg: phiReq / D2R, limitado: capped, L_pie: LA, L_tope: L2, L_tangente: LT, A1, dir: dF }, nodos: { N2, N3: best.S[1].p1, N6, L3: best.L3, d3: best.d3, g3_deg: best.g3 / D2R, factible: best.feas, holgura_min_req: best.e.worst }, eleccion: Object.assign({ L2, FeSt, FretN }, loads0),
      rCentro: { convexo: rCentroConv }, rCanto: { convexo: rCantoConv, concavo: rCantoConc }, g1Max: Math.max(g1t.ang, g1c.ang), joinMax: Math.max(g1t.gap, g1c.gap), dKappa: g1c.dk,
      dTol, dT, md, LB, Lpk, ret, primer_contacto: { L: first.L, w: first.w, phi: first.phi }, syncWorst: sync - dTol, syncPts, lockR: lockW, phiRetMax: Math.max(...drive.map((q) => q.phi)),
      marco: { xh, yh, origen: A1, x: [xMin, xMax], y: [yIn, yOut], largo: xMax - xMin, ancho: yOut - yIn, Rin }, eb, folClr, boxClr, zCuerpo: hAxis(P) + P.t_base - P.D_body / 2, lig: { push: ligPush, jam: ligJam }, Aq, Bq };
    return { fam, c, m, md, alpha: phiF / D2R, Lend: LA, LX1: best.L3, Lr1: L2, hasPk: true, wPk, sync, syncOut, Lsync, cover, need: need_,
      path: travel.map((p) => { const [L, w] = toLW(p); return { L, w, x: p[0], y: p[1] }; }), bolts: bl.all, boltsOuter: bl.outer, dowels, Lb, sb, area, wOut: wPk + rf + P.pv_wlip, rf, inBase, Bh, diag, Rin: RinC, boxClr,
      wCam, wPush, Qof, toLW, clrRet, wNeed: (L) => (L < LB ? 0 : wAt(L, md)), psi0, pins, guia, push, guidedAt, onPath, sReqG, kE };
  }

  /* ---------------- Accionamiento ---------------- */
  const PSI_CAT = 0.07;   // bar por psi según la convención de catálogo (700 bar ≙ 10.000 psi); el factor exacto es 0,06895
  function compute(P) {
    const m = massesBase(P);
    const W = P.W_tf * G;                             // kN
    const Wd = (m.disc + m.ssTop + m.pivot * 0.5) * G / 1e3;     // kN (mesa + disco inoxidable rotatorio + medio pivote)
    const mu = muSet(P), ifc = ifaceDesign(P), oi = ifc.o;
    const N = W + Wd, ND = P.phi_d * W + Wd;
    const Ro = P.D_top / 2, Ri = riOf(P), hubG = hubGeo(P, ifc.delta);
    const Ac = Math.PI * (Ro * Ro - Ri * Ri);
    const r_u = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2);
    const kq = 4 * P.e * Ro / (Ro * Ro + Ri * Ri);
    const q_avg = ND * 1e3 / Ac, q_max = q_avg * (1 + kq), q_min = q_avg * (1 - kq);
    const H_ecc = (mu) => mu * N * P.e * (4 / 3) * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4);   // kN
    const T_piv = (mu) => P.mu_bush * H_ecc(mu) * (P.D_piv / 2) / 1e3;                        // kN·m
    const mode = driveMode(P), fam = camFam(P), kfCol = 1 + fam.mu * P.mu_s;
    const K = mode === 2 ? kinPiv(P) : kinematics(P);
    const A = Math.PI / 4 * P.D_bore ** 2, Aann = A - Math.PI / 4 * P.d_rod ** 2;
    const Fstall = A * P.p_relief / 10 / 1e3, Falarm = A * P.p_alarm / 10 / 1e3, Fret = Aann * P.p_ret / 10 / 1e3;
    const torque = (mu, r) => mu * N * r / 1e3 + T_piv(mu);                                   // kN·m
    let dpts, atPt, Fcyl, Kg, stallMax;
    if (mode === 2) {
      // Pivotado con Q apoyado en el canto de la placa-guía (la rodilla E–Q–P es inestable en compresión; docs/qa/guia_curva_KIET/cambios.md):
      // para cada θ, Q está en la trayectoria del canto con |P − Q| = L_qp; equilibrio del pasador Q: F·u_c + H·(n − μ_leva·t) = F_n·b' (b' = Q→P girada
      // el ángulo del círculo de rozamiento r·sen(atan μ_s)/L_qp), de donde F_n = f_n·F y H = h·F; el par es T/n = F_n·(Q × b'). Si no hay canto (sin
      // placa) se usa la cinemática colineal con potencia virtual: F_n = (T/n)/a_ef, F_cil·η = F_n·(1 + μ_leva·μ_s).
      const kf = 1 + fam.mu * P.mu_s, CPg = K.ok ? camPiv(P, K) : null;
      dpts = K.ok ? K.pts.map((q, i) => Object.assign({}, q, { g: CPg && CPg.push[i] && CPg.push[i].ok ? CPg.push[i] : null })) : [];
      atPt = (d, T) => {
        if (d.g) { const Fp = T * 1e3 / P.n_cyl / d.g.arm, Fe = Fp / d.g.fn; return { Fp, H: P.mu_s * Fp, Fcam: d.g.h * Fe, Rf: 0, Rr: 0, F: Fe / P.eta_c }; }
        const Fp = T * 1e3 / P.n_cyl / d.aEff; return { Fp, H: P.mu_s * Fp, Fcam: P.mu_s * Fp, Rf: 0, Rr: 0, F: Fp * kf / P.eta_c };
      };
      Fcyl = (T) => Math.max(...dpts.map((d) => atPt(d, T).F));
      Kg = () => Fcyl(1) * P.n_cyl * K.armMin / 1e3;
      const Fe = Fstall * P.eta_c, gs = dpts.filter((d) => d.g).map((d) => d.g);
      const Fp = gs.length ? Fe * Math.max(...gs.map((g) => g.fn)) : Fe / kf;
      stallMax = { Fp, H: P.mu_s * Fp, Fcam: gs.length ? Fe * Math.max(...gs.map((g) => g.h)) : P.mu_s * Fp, R: 0, Rsum: 0 };
    } else {
    // Equilibrio del patín en planta (cara plana de la uña): en la posición θ el pasador recibe F_pas (normal a la cara, en y)
    // y la fricción H = s·μ_s·F_pas en x. El pasador gira con la mesa: el punto de contacto (a, y_p − r) se mueve en x con
    // velocidad ω·(r − y_p), de modo que s = signo(y_p − r) (la fricción cambia de sentido en y_p = r; ahí se evalúan ambos).
    // Mesa: x_c·F_pas − y_c·H = T/n.  Patín: R_f = [F_pas·Δ + H·(y_c − y_r)]/Lg; R_r = H − R_f;
    // cilindro: F_cil·η = F_pas + μg(|R_f| + |R_r|).  Se toma el máximo en la carrera (y ambos signos en θ = 0).
      const drive = (th, s) => driveAtG(P, K, th, s);        // por unidad de F_pas
      dpts = drivePts(P, K);
      atPt = (d, T) => { const Fp = T * 1e3 / P.n_cyl / d.den; return { Fp, H: d.h * Fp, Rf: d.rf * Fp, Rr: d.rr * Fp, F: Fp * d.fr / P.eta_c }; };
      Fcyl = (T, armmm) => {                          // kN; sin brazo: máximo en la carrera
      if (armmm) { const th = Math.acos(Math.min(1, armmm / P.R_pin)), sg = (t) => (P.R_pin * Math.sin(t) >= P.d_pin / 2 ? 1 : -1); return Math.max(atPt(drive(-th, sg(-th)), T).F, atPt(drive(th, sg(th)), T).F); }
      return Math.max(...dpts.map((d) => atPt(d, T).F));
    };
      Kg = (arm) => Fcyl(1, arm) * P.n_cyl * (arm || K.armMin) / 1e3;   // factor equivalente F_cil·n·a/T
    // a calado (mesa detenida, la fricción de guía puede ser nula): F_pas = η·F_calado; reacciones de guía y fricción radial máximas
      const stall = dpts.map((d) => { const Fp = Fstall * P.eta_c; return { Fp, H: Math.abs(d.h) * Fp, R: Math.max(Math.abs(d.rf), Math.abs(d.rr)) * Fp, Rsum: (Math.abs(d.rf) + Math.abs(d.rr)) * Fp }; });
      stallMax = { Fp: Math.max(...stall.map((x) => x.Fp)), H: Math.max(...stall.map((x) => x.H)), R: Math.max(...stall.map((x) => x.R)), Rsum: Math.max(...stall.map((x) => x.Rsum)) };
    }
    const caseDef = [
      ["nom", ["Nominal: grasa grafitada limpia", "Nominal: inox–inox con grasa limpia", "Nominal: UHMW sobre inox con grasa limpia", "Nominal: bronce con grafito sobre acero con grasa limpia"][oi], mu.nom, r_u],
      ["dis", "Diseño: μ límite superior, r efectivo", mu.d, P.r_ef],
      ["borde", "Borde: μ de diseño con contacto en el borde (r = R)", mu.d, Ro],
      ["cont", "Contaminado: arena / película degradada", mu.cont, P.r_ef],
      ["seco", ["Acero seco, sin lubricación (referencial)", "Inox seco, sin lubricación (referencial; gripado)", "UHMW seco sobre inox (autolubricado)", "Bronce con grafito seco sobre acero (autolubricado)"][oi], mu.dry, r_u],
    ];
    const cases = K.ok ? caseDef.map(([id, name, mu, r]) => {
      const T = torque(mu, r), F = Fcyl(T);
      return { id, name, mu, r, T, F, p: F * 1e3 / A * 10, FS: Fstall / F, turns: F <= Fstall };
    }) : [];
    const cd = cases.find((c) => c.id === "dis");
    const Tmax = K.ok ? Fstall / Fcyl(1) : 0;           // par vencible a calado (F lineal en T)
    const muMax = (r) => K.ok ? Tmax / (N * r / 1e3 + T_piv(1)) : 0;   // T(μ) = μ·(N·r + T_piv(1)), T_piv lineal en μ
    const gArm = (d) => (d.g ? { L: d.g.L, arm: d.g.arm, armEff: d.g.arm * d.g.fn, psi: d.g.psi, ft: d.g.ft, fr: d.g.fr } : { L: d.L, arm: d.a, armEff: d.aEff, psi: d.psi, ft: d.ft, fr: d.fr });
    const curve = !K.ok ? [] : mode === 2 ? dpts.map((q) => { const a = gArm(q); return { s: a.L - P.L0, arm: a.arm, armEff: a.armEff, F: cd ? atPt(q, cd.T).F : 0 }; }) : K.pts.map((q) => ({ s: q.s, arm: q.arm, F: cd ? Fcyl(cd.T, q.arm) : 0 }));
    const stroke = !(K.ok && cd) ? [] : mode === 2 ? dpts.map((d) => { const a = gArm(d), f = atPt(d, cd.T); return Object.assign({ th: d.th, s: a.L - P.L0, L: a.L, arm: a.arm, armEff: a.armEff, psi: a.psi, ft: a.ft, fr: a.fr, H_guia: f.Fcam, phi_guia: d.g ? d.g.phi : NaN, w: d.g ? d.g.w : NaN, gap: d.g ? d.g.gap : NaN, Q: d.g ? d.g.Q : d.Q, a_colineal: d.a, a_ef_colineal: d.aEff, F_colineal: (cd.T * 1e3 / P.n_cyl / d.aEff) * kfCol / P.eta_c }, f); })
      : dpts.map((d) => Object.assign({ th: d.th, s: P.s_free + P.R_pin * (Math.sin(d.th) + Math.sin(K.pitch / 2)) }, atPt(d, cd.T)));
    const Vext = P.n_cyl * A * P.stroke, Vret = P.n_cyl * Aann * P.stroke;
    const Qr = P.Q_ret > 0 ? P.Q_ret : P.Q_pump;
    const tCycle = Vext / 1e6 / P.Q_pump + Vret / 1e6 / Qr;    // min (avance a Q_pump, retorno a Q_ret)
    // presión bajo las pastillas de bronce (configuración 3): el respaldo y la losa reciben q_máx/cobertura
    const qc = q_max / (ifc.o === 3 && ifc.cov ? ifc.cov : 1);
    // bomba y control: potencia hidráulica p·Q/600 (kW con bar y L/min), velocidad del vástago y caudal para el tiempo objetivo
    const pExt = cd ? cd.p : P.p_relief, pump = {
      Qr, tExt: Vext / 1e6 / P.Q_pump, tRet: Vret / 1e6 / Qr,
      PhExt: pExt * P.Q_pump / 600, PhRet: P.p_ret * Qr / 600, vExt: P.Q_pump * 1e6 / 60 / (P.n_cyl * A) / 1000, vRet: Qr * 1e6 / 60 / (P.n_cyl * Aann) / 1000,
      Qreq: P.t_vuelta_obj > 0 ? (Vext + Vret) / 1e6 / (P.t_vuelta_obj / P.N_pin) : 0 };
    pump.Pmotor = Math.max(pump.PhExt, pump.PhRet) / P.eta_pump;
    pump.PmotorAlarm = Math.max(P.p_alarm * P.Q_pump / 600, pump.PhRet) / P.eta_pump;               // a la presión de alarma
    const res = { pump, m, W, Wd, N, ND, Ro, Ri, hubG, Ac, r_u, q_avg, q_max, qc, q_min, H_ecc, T_piv, K, A, Aann, Fstall, Falarm, Fret,
      mu, ifc, Tmax, cases, cd, muMax, curve, stroke, stallMax, tCycle, tRev: tCycle * P.N_pin, Vext, hax: hAxis(P), torque, Fcyl, Kg, Kguide: Kg(),
      Rguide: stallMax.R, ePiv: ePivEff(P), mode, fam };
    if (mode === 1) res.camG = camGuided(P);
    else if (K.ok) {
      // pivotado: soporte del ojal, bloque-uña, placa-leva y zapata del seguidor (largo automático con p_adm y PV de la familia a FU 0,90)
      res.sup = pivSup(P); res.blk = pivBlkGeo(P, K); res.camP = Object.assign({}, camPiv(P, K));   // copia: la leva memorizada no lleva las fuerzas, que dependen de la carga
      // cargas de la placa-guía (N): empuje con Q apoyado en el canto (H = h·F en Q, a calado y en el diseño) y atasco del retorno con el giro en E trabado
      // en el primer contacto de la conducción final (N = F_ret/sen φ₁, sin el roce que ayudaría: cota)
      const CP = res.camP, g = CP.guia, Tdis = cd ? Math.max(...dpts.map((d) => atPt(d, cd.T).Fcam)) * 1e3 : 0;
      const phi1 = g.primer_contacto.phi, NR = Fret * 1e3 / Math.sin(Math.max(1, phi1) * D2R), Tst = stallMax.Fcam * 1e3, Ncam = Math.max(NR, Tst);
      const gp = CP.push.filter((q) => q.ok), Qs = gp.map((q) => q.Q);
      const vQ = (P.Q_pump * 1e6 / 60 / (P.n_cyl * A)) / 1000 * Math.max(0, ...gp.map((q, i) => (i ? Math.hypot(q.Q[0] - gp[i - 1].Q[0], q.Q[1] - gp[i - 1].Q[1]) / Math.max(1e-9, Math.abs(q.L - gp[i - 1].L)) : 0)));   // m/s del seguidor
      // Hertz con el radio real del canto en cada contacto (+ convexo, − cóncavo): 1/R_ef = 1/r_f + 1/R_c; longitud de contacto = t_placa − 2 (el pasador termina 2 mm sobre la base)
      const Es = P.E / (2 * (1 - P.nu ** 2)), lc = P.pv_tcam - 2, rfQ = P.pv_dq / 2, hz = (N, Rc) => { const Reff = 1 / (1 / rfQ + (isFinite(Rc) ? 1 / Rc : 0)), q = N / lc; return { N, Rc, Reff, q, p0: Math.sqrt(q * Es / (Math.PI * Reff)), b: Math.sqrt(4 * q * Reff / (Math.PI * Es)) }; };
      let hzP = null; gp.forEach((q) => { const z = hz(q.h * Fstall * P.eta_c * 1e3, q.Rc); z.th = q.th; z.contacto = q.contacto; if (!hzP || z.p0 > hzP.p0) hzP = z; });
      const fo = CP.onPath(g.primer_contacto.L), Rc1 = fo.s.tipo === "arco" ? (fo.s.sentido === "horario" ? fo.s.radio - rfQ : -(fo.s.radio + rfQ)) : Infinity, hzJ = hz(NR, Rc1);
      const iH = gp.reduce((k, q, i) => (q.h > gp[k].h ? i : k), 0);
      CP.hz = { push: hzP, jam: hzJ }; CP.Hpt = gp.length ? { th: gp[iH].th, contacto: gp[iH].contacto, nin: gp[iH].nin, lig: g.lig.push[iH], h: gp[iH].h } : null;
      CP.fe = Fstall * P.eta_c; CP.ratioMax = Math.max(...dpts.map((d) => (cd ? atPt(d, cd.T).F / ((cd.T * 1e3 / P.n_cyl / d.aEff) * kfCol / P.eta_c) : 1)));
      let lpad = P.pv_dq;
      if (fam.tipo === "pad") {   // p_adm y PV del material con la carga de diseño (como la interfaz de giro); a calado, aplastamiento BTH-1 (filas)
        const lp = Tdis / (0.9 * fam.pAdm * P.pv_tcam), lv = fam.PV ? Tdis * vQ / (0.9 * fam.PV * P.pv_tcam) : 0;
        lpad = P.pv_lpad > 0 ? P.pv_lpad : Math.max(P.pv_dq, Math.ceil(Math.max(lp, lv) / 5) * 5);
      }
      CP.lpad = lpad; CP.Ncam = Ncam; CP.NR = NR; CP.Tst = Tst; CP.Tdis = Tdis; CP.vQ = vQ;
      const mPad = fam.tipo === "pad" ? 2 * P.n_cyl * (RHO * lpad * P.pv_tcam * 25) : 0;   // zapata de acero de 25 mm de espesor con su revestimiento en la leva
      m.cam += mPad; m.total += mPad; m.camPad = mPad;
    }
    // inserto de esquina bajo los soportes (decisión del mandante 10-11-2026): masa añadida sobre la base de t_base; las paredes del soporte E (modo 2) o las
    // mejillas y el suplemento de la ménsula (modo 1) arrancan sobre el inserto (Δ más cortos); el marco perimetral se interrumpe a lo largo de los catetos (+50 mm)
    m.insertos = 0; m.insBrackets = 0; m.insRim = 0;
    const INS = cornerInsertOf(P, res);
    if (INS && INS.ok) {
      const Dz = INS.delta, rimL = (L) => RHO * P.rim_t * P.rim_h * L;
      m.insertos = INS.n * INS.mass;
      if (mode === 2) {
        m.insBrackets = P.n_cyl * RHO * res.sup.walls.reduce((a, q) => a + Math.abs(PG.area(q.poly)), 0) * Dz;
        const h = res.sup.marco.alcance, Lx = Math.max(0, P.B / 2 - (Math.abs(K.E[1]) - h)), Ly = Math.max(0, P.B / 2 - (Math.abs(K.E[0]) - h));
        m.insRim = P.n_cyl * rimL(Math.max(0, INS.legX + 50 - Lx) + Math.max(0, INS.legY + 50 - Ly));
      } else {
        const bg = bracketGeo(P);
        m.insBrackets = Math.round(P.n_br) * RHO * (2 * P.t_ch * P.L_ch + (bg.Win * bg.Llug - Math.PI / 4 * P.d_pp ** 2)) * Math.min(Dz, bg.spacer);
        m.insRim = INS.n * rimL(Math.min(P.B, INS.legX + 50) + Math.min(P.B, INS.legY + 50));
      }
      // la masa de los insertos va con el soporte del cilindro (m.brackets: soporte del ojal E o ménsula, uno por inserto), para que la lista de materiales
      // (packages/web/planos_export.js, que toma m.brackets) la cuente; m.insertos queda como dato informativo (ya incluido en m.brackets)
      m.brackets += m.insertos - m.insBrackets; m.rim -= m.insRim;
      m.total += m.insertos - m.insBrackets - m.insRim;
    }
    // barras de los topes soldados: dependen del par de calado, así que se dimensionan aquí y suman a m.total (no están en ninguna otra pieza).
    // Las barras de la mesa giran y cargan la interfaz, pero no se realimentan a N (< 0,01 %; evita la dependencia circular con el par de calado).
    res.TmaxTopes = mode === 2 ? Math.max(Tmax, tmaxOf(P)) : Tmax;          // topes: en el pivotado, la cota colineal de tmaxOf (mayor que la del empuje guiado), la misma de ifaceDesign (muescas y tapones)
    ifc.topes = stopsOf(P, res);
    ifc.tornillos = tornillosAF2(P, res);                                // AF2: tornillos avellanados disco de la mesa → mesa (null si no aplica)
    m.stopBars = ifc.topes.reduce((s, t) => s + t.m_barras, 0);
    // muescas, chaflanes y juntas entre sectores: las coronas brutas de massesBase pasan a netas (la masa rotatoria m.ssTop queda bruta: no se realimenta a N, conservador, < 0,01 %)
    ifc.cortes = cortesOf(P, res);
    const dsc = { ss: 0, uhmw: 0, bz: 0 };
    ifc.cortes.forEach((c) => { dsc[c.tgt] += c.m_desc; });
    m.ss -= dsc.ss; m.uhmw -= dsc.uhmw; m.bz -= dsc.bz;
    m.sectorCuts = dsc.ss + dsc.uhmw + dsc.bz;                           // kg descontados (informativo: ya no están en ss, uhmw ni bz)
    m.total += m.stopBars - m.sectorCuts;
    // tierra / losa (base delgada: sin reparto, se toma q_max de la interfaz como presión de apoyo)
    res.g_rigid = (ND + (m.total - m.disc) * G / 1e3) * 1e3 / (P.B * P.B) * (1 + 6 * P.e * Math.SQRT2 / P.B);
    return res;
  }

  /* ---------------- FEA de la mesa (sector entre nervios) ---------------- */
  function linspaceKeys(keys, h) {
    const out = [keys[0]];
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1], b = keys[i], n = Math.max(1, Math.ceil((b - a) / h));
      for (let k = 1; k <= n; k++) out.push(a + (b - a) * k / n);
    }
    return out;
  }
  function uniqSorted(arr, tol) {
    const s = arr.slice().sort((a, b) => a - b), o = [];
    for (const v of s) if (!o.length || v - o[o.length - 1] > tol) o.push(v);
    return o;
  }
  function discModel(P, R, which, coarse) {
    const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_top / 2;
    const hr = Math.max(coarse ? 30 : 18, (Rd - r0) / (coarse ? 28 : 48));
    const rings = parseRings(P.rings).filter((r) => r > r0 && r < Rd);
    const RL = Math.min(P.D_load / 2, Rd);
    const keyR = uniqSorted([r0, ...rings, Math.min(P.R_rib, Rd), P.R_pin - P.d_pin / 2, P.R_pin, P.R_pin + P.d_pin / 2, Rd, which === "top" ? RL : r0]
      .filter((r) => r >= r0 && r <= Rd), 2);
    const rs = linspaceKeys(keyR, hr);
    const pinAng = [];
    for (let k = 0; k < P.N_pin; k++) {
      const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin;
      if (a >= -1e-9 && a <= alpha + 1e-9) pinAng.push(a);
    }
    const db = (P.d_pin / 2) / P.R_pin;
    const keyT = uniqSorted([0, alpha, ...pinAng, ...pinAng.map((a) => a - db), ...pinAng.map((a) => a + db)].filter((a) => a >= 0 && a <= alpha), 1e-4);
    const ts = linspaceKeys(keyT, Math.max((coarse ? 2.5 : 1.25) * D2R, alpha / (coarse ? 16 : 30)));
    const nT = ts.length, nodes = [], elems = [], pol = [];
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) { nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]); pol.push([rs[i], ts[j]]); }
    const id = (i, j) => i * nT + j;
    const q = [], t = which === "top" ? P.t_top : P.t_bot;
    const q_top = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL);
    for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) {
      elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const rc = (rs[i] + rs[i + 1]) / 2;
      q.push(which === "top" ? (rc <= RL ? q_top : 0) : R.qc);
    }
    const wFix = new Set(), clamp = [], betaN = [], groups = { ring: rings.map(() => []), rib: [], pin: pinAng.map(() => []), hub: [] };
    const near = (a, b, tol) => Math.abs(a - b) < tol;
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
      const k = id(i, j), r = rs[i], th = ts[j];
      if (i === 0) { clamp.push(k); groups.hub.push(k); continue; }
      rings.forEach((rr, ri) => { if (near(r, rr, 0.5)) { wFix.add(k); groups.ring[ri].push(k); } });
      if ((j === 0 || j === nT - 1) && r <= P.R_rib + 0.5) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
      pinAng.forEach((ba, bi) => {
        const x = r * Math.cos(th) - P.R_pin * Math.cos(ba), y = r * Math.sin(th) - P.R_pin * Math.sin(ba);
        if (Math.hypot(x, y) <= P.d_pin / 2 + 0.5) { if (!wFix.has(k)) groups.pin[bi].push(k); wFix.add(k); }
      });
      if (j === 0) betaN.push([k, 0, 1]);
      if (j === nT - 1) betaN.push([k, -Math.sin(alpha), Math.cos(alpha)]);
    }
    return { nodes, pol, elems, q: Float64Array.from(q), t, E: P.E, nu: P.nu, wFix: [...wFix], clamp, betaN, groups, rings, pinAng, alpha, rs, ts, which, q_top };
  }
  const now = () => (typeof performance !== "undefined" ? performance.now() : Date.now());
  /* ---------------- FEA de la piel superior escalonada (cubierta W): modelo desarrollado ----------------
     La plancha rebajada, la pared cilíndrica y el anillo superior se modelan como UNA placa MITC4 desplegada en el plano: la pared es una corona de ancho L_dev
     (su flexión meridional; el giro es continuo en las dos uniones, que son rígidas) y el anillo sigue a continuación con los radios desplazados L_dev.
     Apoyos: w = 0 en R_reb (alma de R_reb y apoyo de la plancha) y en R_reb + L_dev (unión pared–anillo: el anillo es rígido en su plano, la pared no se desplaza
     lateralmente arriba); pasadores (w = 0) en R_pin + L_dev. La rigidez de la pared se conserva con L_dev = L·(t_reb/t_pared)³ (el modelo usa el espesor t_reb).
     Dos variantes y se toma la envolvente: «anillo» (L = distancia entre planos medios h_c y anillo con pasadores modelado con t_reb: la menor restricción del vano
     de la plancha rebajada) y «empotrada» (L = altura libre de la pared y empotramiento en el anillo: la mayor restricción, máximo momento en la pared).
     Se desprecia la rigidez circunferencial de la pared (anillo de t_pared × h_pared: < 1 % de la de flexión; acotado en tests/indep_madera.py).
     Validación: tests/test_tt300c.js «caso de referencia axisimétrico» (solución cerrada de Kirchhoff por tramos) y tests/indep_madera.py. */
  function stepPlate(s) {
    // s: { r0, Rd, alpha, t, E, nu, h, dth, keyR, keyT, lines, clampLines, ribs: [[ra, rb]], pins: [[R, ang, d]], hLoc: [[ra, rb, h]], load(rc), zone(rc), freeInner }
    const keyR = uniqSorted([s.r0, s.Rd, ...(s.keyR || [])].filter((r) => r >= s.r0 - 1e-9 && r <= s.Rd + 1e-9), 0.2);
    const hAt = (a, b) => { let h = s.h; (s.hLoc || []).forEach(([ra, rb, hh]) => { if (a >= ra - 1e-6 && b <= rb + 1e-6) h = Math.min(h, hh); }); return h; };
    const rs = [keyR[0]];
    for (let i = 1; i < keyR.length; i++) { const a = keyR[i - 1], b = keyR[i], n = Math.max(1, Math.ceil((b - a) / hAt(a, b) - 1e-9)); for (let k = 1; k <= n; k++) rs.push(a + (b - a) * k / n); }
    const ts = linspaceKeys(uniqSorted([0, s.alpha, ...(s.keyT || [])].filter((a) => a >= 0 && a <= s.alpha), 1e-4), s.dth);
    const nT = ts.length, nodes = [], pol = [], elems = [], q = [], zone = [], id = (i, j) => i * nT + j;
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) { nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]); pol.push([rs[i], ts[j]]); }
    for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) {
      elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const rc = (rs[i] + rs[i + 1]) / 2; q.push(s.load ? s.load(rc) : 0); zone.push(s.zone ? s.zone(rc) : "");
    }
    const lines = s.lines || [], cl = s.clampLines || [], ribs = s.ribs || [], pins = s.pins || [];
    const wFix = new Set(), clamp = [], betaN = [], groups = { line: lines.map(() => []), clampLine: cl.map(() => []), rib: [], pin: pins.map(() => []), hub: [] };
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
      const k = id(i, j), r = rs[i], th = ts[j];
      if (i === 0 && !s.freeInner) { clamp.push(k); groups.hub.push(k); continue; }
      lines.forEach((rl, li) => { if (Math.abs(r - rl) < 0.5) { wFix.add(k); groups.line[li].push(k); } });
      cl.forEach((rl, li) => { if (Math.abs(r - rl) < 0.5) { clamp.push(k); groups.clampLine[li].push(k); } });
      if ((j === 0 || j === nT - 1) && ribs.some(([ra, rb]) => r >= ra - 0.5 && r <= rb + 0.5)) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
      pins.forEach(([Rp, ba, d], bi) => { if (Math.hypot(r * Math.cos(th) - Rp * Math.cos(ba), r * Math.sin(th) - Rp * Math.sin(ba)) <= d / 2 + 0.5) { if (!wFix.has(k)) groups.pin[bi].push(k); wFix.add(k); } });
      if (j === 0) betaN.push([k, 0, 1]);
      if (j === nT - 1) betaN.push([k, -Math.sin(s.alpha), Math.cos(s.alpha)]);
    }
    return { nodes, pol, elems, q: Float64Array.from(q), zone, t: s.t, E: s.E, nu: s.nu, wFix: [...wFix], clamp, betaN, groups, rs, ts, alpha: s.alpha };
  }
  function discModelW(P, R, coarse, variant) {
    const g = woodGeo(P), alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rt = P.D_top / 2, Rreb = g.R_rebaje, ring = variant === "anillo";
    const Lw = Math.max(2, (ring ? g.h_c : g.h_pared) * (g.t_reb / g.t_pared) ** 3), Ra = Rreb + Lw, sh = Lw, Rd = ring ? Rt + sh : Ra;
    const hr = Math.max(coarse ? 30 : 18, (Rt - r0) / (coarse ? 28 : 48)), dth = Math.max((coarse ? 2.5 : 1.25) * D2R, alpha / (coarse ? 16 : 30));
    const rings = parseRings(P.rings), RL = Math.min(P.D_load / 2, Rt), Rpe = g.R_pared_ext;
    const inner = rings.filter((r) => r > r0 && r < Rreb - 0.5), outer = ring ? rings.filter((r) => r > Rpe + 0.5 && r < Rt) : [];
    const pinAng = []; if (ring) for (let k = 0; k < P.N_pin; k++) { const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin; if (a >= -1e-9 && a <= alpha + 1e-9) pinAng.push(a); }
    const Rp = P.R_pin + sh, db = (P.d_pin / 2) / Rp, q_top = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL);
    const ribs = [[r0, Math.min(P.R_rib, Rreb)]]; if (ring && P.R_rib > Rpe + 0.5) ribs.push([Rpe + sh, P.R_rib + sh]);
    const m = stepPlate({ r0, Rd, alpha, t: g.t_reb, E: P.E, nu: P.nu, h: hr, dth,
      keyR: [...inner, Rreb, Ra, Math.min(P.R_rib, Rreb), RL < Rreb ? RL : RL + sh, ...(ring ? [Rp - P.d_pin / 2, Rp, Rp + P.d_pin / 2, ...outer.map((r) => r + sh), ...(P.R_rib > Rpe + 0.5 ? [P.R_rib + sh] : [])] : [])],
      keyT: [...pinAng, ...pinAng.map((a) => a - db), ...pinAng.map((a) => a + db)],
      lines: [...inner, Rreb, ...(ring ? [Ra, ...outer.map((r) => r + sh)] : [])], clampLines: ring ? [] : [Ra], ribs, pins: pinAng.map((a) => [Rp, a, P.d_pin]),
      hLoc: [[Rreb, Ra, Math.min(hr, Lw / 4)]],
      load: (rc) => (rc < Rreb ? (rc <= RL ? q_top : 0) : (rc >= Ra && rc - sh <= RL ? q_top : 0)),
      zone: (rc) => (rc < Rreb ? "reb" : rc < Ra ? "pared" : "anillo") });
    return Object.assign(m, { which: "top", variant, q_top, Lw, Ra, sh, rings: inner, nIn: inner.length, pinAng });
  }
  function runDiscW(P, R, coarse) {
    const g = woodGeo(P), kP = (g.t_reb / g.t_pared) ** 2, t0 = now();
    const vs = ["anillo", "empotrada"].map((v) => {
      const m = discModelW(P, R, coarse, v), r = FEA_.plate(m), sumS = (arr) => Math.abs(arr.reduce((s2, k) => s2 + r.reac[k], 0));
      let vm = 0, imax = 0, sPar = 0, sAn = 0, wReb = 0, wAn = 0;
      r.el.forEach((e, i) => { const z = m.zone[i]; if (z === "reb") { if (e.vmGauss > vm) { vm = e.vmGauss; imax = i; } } else if (z === "pared") sPar = Math.max(sPar, e.vmGauss * kP); else sAn = Math.max(sAn, e.vmGauss); });
      m.pol.forEach((p, k) => { if (p[0] <= g.R_rebaje + 1e-6) wReb = Math.max(wReb, Math.abs(r.w[k])); else if (p[0] >= m.Ra + 1e-6) wAn = Math.max(wAn, Math.abs(r.w[k])); });
      const ringLine = m.rings.map((rr, i) => sumS(m.groups.line[i]) / (rr * m.alpha)).concat([sumS(m.groups.line[m.nIn]) / (g.R_rebaje * m.alpha)]);   // N/mm; la última es la línea de R_reb (alma + pie de la pared)
      const topLine = v === "anillo" ? sumS(m.groups.line[m.nIn + 1]) / (g.R_rebaje * m.alpha) : sumS(m.groups.clampLine[0]) / (g.R_rebaje * m.alpha);   // reacción horizontal en la unión pared–anillo
      const ribF = sumS(m.groups.rib), ribLine = ribF / (2 * Math.max(1, Math.min(P.R_rib, g.R_rebaje) - P.D_hub / 2));
      const ec = m.elems[imax].map((k) => m.nodes[k]), cx = ec.reduce((s2, p) => s2 + p[0], 0) / 4, cy = ec.reduce((s2, p) => s2 + p[1], 0) / 4;
      return { variante: v, model: m, res: r, vm, sPared: sPar, sAnillo: sAn, wReb, wAnillo: wAn, ringLine, topLine, ribLine, pinF: m.groups.pin.map((gr) => sumS(gr) / 1e3), L_dev: m.Lw, n: m.nodes.length,
        maxAt: [Math.hypot(cx, cy), Math.atan2(cy, cx) / D2R], Fapp: r.Fapplied / 1e3, Rsum: Math.abs(r.Rsum) / 1e3 };
    });
    const [A, B] = vs, gov = A.vm >= B.vm ? A : B, ringLine = A.ringLine.map((v, i) => Math.max(v, B.ringLine[i])), ribLine = Math.max(A.ribLine, B.ribLine);
    return { model: A.model, res: A.res, ms: now() - t0, vmMax: gov.vm, wMax: Math.max(A.wReb, B.wReb), ringLine, ribLine, pinF: A.pinF, lineMax: Math.max(0, ribLine, ...ringLine),
      Fapp: A.Fapp, Rsum: A.Rsum, maxAt: gov.maxAt, n: A.n + B.n,
      escalon: { variantes: vs.map((x) => ({ variante: x.variante, L_dev: x.L_dev, vm_reb: x.vm, s_pared: x.sPared, s_anillo: x.sAnillo, w_reb: x.wReb, w_anillo: x.wAnillo, linea_reb: x.ringLine[x.ringLine.length - 1], linea_pared_sup: x.topLine, n: x.n })),
        sPared: Math.max(A.sPared, B.sPared), sAnillo: A.sAnillo, lineaReb: Math.max(A.ringLine[A.ringLine.length - 1], B.ringLine[B.ringLine.length - 1]), lineaParedSup: Math.max(A.topLine, B.topLine), gobierna: gov.variante } };
  }
  function runDisc(P, R, which, coarse) {
    if (which === "top" && P.opt_wood > 0.5) return runDiscW(P, R, coarse);   // W: piel superior escalonada (modelo desarrollado)
    const m = discModel(P, R, which, coarse);
    const t0 = now();
    const r = FEA_.plate(m);
    const ms = now() - t0;
    let vmMax = 0, imax = 0;
    r.el.forEach((e, i) => { if (e.vmGauss > vmMax) { vmMax = e.vmGauss; imax = i; } });
    let wMax = 0; for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
    const sumS = (arr) => Math.abs(arr.reduce((s, k) => s + r.reac[k], 0));   // suma con signo (rev. m3)
    const ringLine = m.rings.map((rr, i) => sumS(m.groups.ring[i]) / (rr * m.alpha));   // N/mm
    const ribF = sumS(m.groups.rib), ribLine = ribF / (2 * Math.max(1, P.R_rib - P.D_hub / 2));   // N/mm, 2 bordes del sector = 1 nervio
    const pinF = m.groups.pin.map((g) => sumS(g) / 1e3);
    const ec = m.elems[imax].map((k) => m.nodes[k]);
    const cx = ec.reduce((s, p) => s + p[0], 0) / 4, cy = ec.reduce((s, p) => s + p[1], 0) / 4;
    return { model: m, res: r, ms, vmMax, wMax, ringLine, ribLine, pinF, lineMax: Math.max(0, ribLine, ...ringLine),
      Fapp: r.Fapplied / 1e3, Rsum: Math.abs(r.Rsum) / 1e3, maxAt: [Math.hypot(cx, cy), Math.atan2(cy, cx) / D2R], n: m.nodes.length };
  }

  /* ---------------- Flexión global axisimétrica del cajón (placa sándwich, borde libre) ---------------- */
  function globalBending(P, R) {
    const n = 4000, Rd = P.D_top / 2, RL = Math.min(P.D_load / 2, Rd), Ri = R.Ri;
    const qt = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL), qd = R.Wd * 1e3 / (Math.PI * Rd * Rd);
    const qb = R.ND * 1e3 / (Math.PI * (Rd * Rd - Ri * Ri));
    const r = new Float64Array(n), p = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      r[i] = 1e-6 + Rd * i / (n - 1);
      p[i] = (r[i] >= Ri ? qb : 0) - (r[i] <= RL ? qt : 0) - qd;
    }
    const cum = new Float64Array(n), Q = new Float64Array(n);
    for (let i = 1; i < n; i++) cum[i] = cum[i - 1] + 0.5 * (p[i] * r[i] + p[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
    for (let i = 0; i < n; i++) Q[i] = cum[i] / r[i];
    const Iq = new Float64Array(n), J = new Float64Array(n);
    for (let i = 1; i < n; i++) Iq[i] = Iq[i - 1] + 0.5 * (Q[i] + Q[i - 1]) * (r[i] - r[i - 1]);
    for (let i = 1; i < n; i++) J[i] = J[i - 1] + 0.5 * (Iq[i] * r[i] + Iq[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
    const psi = new Float64Array(n), dps = new Float64Array(n);
    for (let i = 0; i < n; i++) psi[i] = J[i] / r[i];
    for (let i = 1; i < n - 1; i++) dps[i] = (psi[i + 1] - psi[i - 1]) / (r[i + 1] - r[i - 1]);
    dps[0] = dps[1]; dps[n - 1] = dps[n - 2];
    const C = -(dps[n - 1] + P.nu * psi[n - 1] / Rd) / (1 + P.nu);
    let Mmax = 0, rM = 0, Vmax = 0, rV = 0;
    for (let i = 5; i < n - 5; i++) {
      const ps = psi[i] + C * r[i], dp = dps[i] + C;
      const Mr = dp + P.nu * ps / r[i], Mt = ps / r[i] + P.nu * dp;
      const M = Math.max(Math.abs(Mr), Math.abs(Mt));
      if (M > Mmax) { Mmax = M; rM = r[i]; }
      if (r[i] >= P.D_hub / 2 && r[i] <= P.R_rib) {
        const V = Math.abs(Q[i]) * 2 * Math.PI * r[i];
        if (V > Vmax) { Vmax = V; rV = r[i]; }
      }
    }
    // W: dentro de R_reb el ala superior es la plancha rebajada (t_reb), con su plano medio t_madera + t_reb/2 bajo la cara superior (h_c menor; sin aporte de la madera)
    const wg = woodGeo(P), tT = wg ? wg.t_reb : P.t_top, hc = wg ? P.h_disc - wg.t_madera - wg.t_reb / 2 - P.t_bot / 2 : P.h_disc - (P.t_top + P.t_bot) / 2;
    let MrReb = 0;
    if (wg) { const i = Math.max(5, Math.min(n - 6, Math.round(wg.R_rebaje / Rd * (n - 1)))), ps = psi[i] + C * r[i], dp = dps[i] + C; MrReb = Math.abs(dp + P.nu * ps / r[i]); }   // M_r global en R_reb (N·mm/mm): empuje del ala que cambia de nivel en el escalón
    const imb = Q[n - 1] * 2 * Math.PI * Rd / 1e3;
    return { Mmax, rM, sigTop: Mmax / (tT * hc), sigBot: Mmax / (P.t_bot * hc), Vmax: Vmax / 1e3, rV, imbalance: imb, hcTop: hc, MrReb };
  }

  /* ---------------- FEA de izaje de la base (cuarto de placa con simetría) ---------------- */
  function runLift(P, R, coarse) {
    const a = P.B / 2, n = coarse ? 14 : 24, h = a / n;
    const nodes = [], elems = [];
    for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * h, j * h]);
    const id = (i, j) => i * (n + 1) + j;
    const Rd = P.D_top / 2;
    const mOther = R.m.disc + R.m.pivot + R.m.dogs + R.m.cyl + R.m.ss + R.m.uhmw + R.m.bz;   // apoyado sobre la huella de la mesa (con las piezas de la interfaz)
    const qDisc = mOther * G / (Math.PI * Rd * Rd);
    const qOwn = (R.m.base + R.m.rim + R.m.brackets + R.m.shoes + R.m.beds + (R.m.cam || 0)) * G / (P.B * P.B);   // peso propio repartido sobre la base (con las levas, fijas a la base o a la bancada)
    const q = [];
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const xc = (i + 0.5) * h, yc = (j + 0.5) * h;
      q.push(P.phi_lift * (qOwn + (Math.hypot(xc, yc) <= Rd ? qDisc : 0)));
    }
    // puntos de izaje en los lados y: (±x_lug, ±(B/2 − c)); cuarto de placa con simetría en x = 0 e y = 0
    const xl = Math.min(P.x_lug, a - 1), yl = a - P.c_lug, pad = Math.max(75, 1.01 * h);   // placa de apoyo 150 × 150 (mín. un elemento)
    const wFix = [], betaN = [];
    for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
      const k = id(i, j), x = i * h, y = j * h;
      if (Math.abs(x - xl) <= pad + 1e-6 && Math.abs(y - yl) <= pad + 1e-6) wFix.push(k);
      if (i === 0) betaN.push([k, 1, 0]);
      if (j === 0) betaN.push([k, 0, 1]);
    }
    if (!wFix.length) { let best = 0, bd = 1e9; nodes.forEach((p, k) => { const d = Math.hypot(p[0] - xl, p[1] - yl); if (d < bd) { bd = d; best = k; } }); wFix.push(best); }
    const t0 = now();
    const r = FEA_.plate({ nodes, elems, t: P.t_base, E: P.E, nu: P.nu, q: Float64Array.from(q), wFix, betaN });
    // La tensión en la esquina de la placa rígida del cáncamo es singular (diverge con la malla): el máximo se toma a ≥ 2·pad del punto de izaje;
    // el cáncamo y sus soldaduras se verifican aparte (WLL del cáncamo y soldadura del fabricante).
    let vmMax = 0, wMax = 0, vmAll = 0;
    r.el.forEach((e, k) => {
      vmAll = Math.max(vmAll, e.vmGauss);
      const c = elems[k].reduce((s2, ni) => [s2[0] + nodes[ni][0] / 4, s2[1] + nodes[ni][1] / 4], [0, 0]);
      if (Math.max(Math.abs(c[0] - xl), Math.abs(c[1] - yl)) >= 2 * pad) vmMax = Math.max(vmMax, e.vmGauss);
    });
    for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
    return { nodes, elems, res: r, vmMax, vmAll, wMax, ms: now() - t0, Fapp: 4 * r.Fapplied / 1e3, Rsum: 4 * Math.abs(r.Rsum) / 1e3, n };
  }

  /* ---------------- Fatiga: AISC 360-22 Apéndice 3, Tabla A-3.1 (SI) ---------------- */
  // Cf en unidades US (ksi) según la tabla; F_SR[MPa] = 6,895·(Cf/n)^(1/k); F_TH en MPa
  const FAT_CAT = { A: [250e8, 165, 3], B: [120e8, 110, 3], C: [44e8, 69, 3], D: [22e8, 48, 3], E: [11e8, 31, 3], "E'": [3.9e8, 18, 3], F: [150e10, 55, 6] };
  function FSR(cat, nCyc) { const [Cf, Fth, k] = FAT_CAT[cat]; return Math.max(6.895 * Math.pow(Cf / Math.max(nCyc, 1), 1 / k), Fth); }

  /* ---------------- Temperatura de servicio (exposición solar) ---------------- */
  // Fuente de todos los datos: docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)» (niveles de confianza A/B/C allí definidos).
  // Escenario aparte: con T_serv = 20 °C el cálculo estándar no cambia. TT.thermal evalúa la geometría dimensionada a 20 °C (congelada) con las capacidades reducidas.
  const TH_AV = 7.5e-4;                    // 1/K, expansión volumétrica del aceite mineral (7,0–7,5×10⁻⁴; C)
  const TH_KHOSE = 327;                    // MPa, módulo combinado aceite + manguera (≈ 47 500 psi; C)
  const TH_NU_BZ = 0.33;                   // Poisson del bronce (buje)
  const TH_AL = { ss: 17e-6, uh: 190e-6, bz: 18e-6, woodT: 30e-6, woodL: 5e-6, st0: 12e-6 };   // inox (B), UHMW (B/C), bronce (C), madera (C); acero EN 1993-1-1 §3.2.6
  const epsSteel = (T) => 1.2e-5 * T + 0.4e-8 * T * T - 2.416e-4;        // EN 1993-1-2 §3.4.1.1, Δl/l con θ en °C (da 0 a 20 °C)
  function alphaSteelMean(T, Tref) {                                      // α medio entre T_ref y T: 12,4×10⁻⁶ para 20–80 °C
    Tref = Tref == null ? 20 : Tref;
    return T - Tref > 1e-9 ? (epsSteel(T) - epsSteel(Tref)) / (T - Tref) : TH_AL.st0;
  }
  const kAt = (k80, T, Tref) => (T - Tref <= 0 ? 1 : Math.max(0.05, 1 + (k80 - 1) * (T - Tref) / (80 - Tref)));   // lineal entre 1 (T_ref) y el valor a 80 °C; extrapola sobre 80 °C
  // Factores de reducción, dilataciones y notas a la temperatura T. ov: sobrescribe parámetros (sensibilidades)
  function thermalFactors(P, T, ov) {
    ov = ov || {};
    const g = (id) => (ov[id] != null ? ov[id] : P[id]), Tref = P.T_ref, ex = T > 80 + 1e-9, dT = Math.max(0, T - Tref);
    const f = (id) => kAt(g(id), T, Tref);
    const k = { Fy: f("kT_Fy"), E: f("kT_E"), Fy_ss: f("kT_Fy_ss"), E_ss: f("kT_E_ss"), p_uh: f("kT_p_uh"), E_uh: f("kT_E_uh"), bz: f("kT_bz"), wood: f("kT_wood"), bolt: f("kT_bolt"), weld: f("kT_weld"), hertz: f("kT_hertz"), mu: f("k_mu_T") };
    const notes = [];
    if (ex) notes.push("T > 80 °C: factores extrapolados linealmente desde el valor tabulado a 80 °C (sin dato publicado); tomar el resultado como orden de magnitud");
    if (T > 66) notes.push("80 °C excede el rango estándar de ASME BTH-1 (−4 a 66 °C): requiere decisión de persona calificada (registro, «Alcance térmico de BTH-1»; sección por confirmar)");
    if (T >= 80) notes.push("UHMW-PE: 80 °C es su límite de servicio continuo y coincide con el Vicat B50; sin curva del proveedor los factores k_p y k_E son supuestos (confianza C)");
    return { T, dT, extrap: ex, k, notes, alpha: { st: alphaSteelMean(T, Tref), ss: TH_AL.ss, uh: TH_AL.uh, bz: TH_AL.bz, woodT: TH_AL.woodT, woodL: TH_AL.woodL } };
  }
  // Presión por aceite atrapado entre una válvula de retención/bloqueo y un tope: Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c)  (MPa; ×10 = bar)
  function oilTrapped(P, T, ov) {
    ov = ov || {};
    const g = (id) => (ov[id] != null ? ov[id] : P[id]), dT = Math.max(0, T - P.T_ref), as = alphaSteelMean(T, P.T_ref), d = (TH_AV - 3 * as) * dT;
    const b2 = g("ba_cil") ** 2, Kc = P.E / (2 * ((b2 + 1) / (b2 - 1) + P.nu));      // Lamé: rigidez volumétrica de la sección del tubo (b/a)
    const mk = (K, Kcc) => { const Ke = Kcc ? 1 / (1 / K + 1 / Kcc) : K, dp = d * Ke; return { K, Ke, dp, bar: dp * 10 }; };
    const rigid = { lo: mk(g("K_oil")), hi: mk(g("K_oil_hi")) }, cyl = { lo: mk(g("K_oil"), Kc), hi: mk(g("K_oil_hi"), Kc) }, hose = { lo: mk(TH_KHOSE), hi: mk(TH_KHOSE) };
    return { T, dT, av: TH_AV, as3: 3 * as, Kc_lame: Kc, rigid, cyl, hose, sel: [rigid, cyl, hose][Math.min(3, Math.max(1, Math.round(g("oil_cont")))) - 1], expansion_free_pct: 100 * d,
      expansion_1m_mm: 1000 * d, ref: "docs/normas/registro.md, «Presión por aceite atrapado»; ISO 4413:2010 (cláusula por confirmar)" };
  }
  // Viscosidad cinemática del VG 46 a T (mm²/s), Walther (ASTM D341): lo = ν40 46 y ν100 6,8 (IV ≈ 100); hi = ν40 47,4 y ν100 9,5 (Eurol Hykrol EXL 46, IV 185)
  const walther = (n1, n2) => { const f = (n) => Math.log10(Math.log10(n + 0.7)), t = (c) => Math.log10(c + 273.15), B = (f(n1) - f(n2)) / (t(100) - t(40)), A = f(n1) + B * t(40); return (c) => Math.pow(10, Math.pow(10, A - B * t(c))) - 0.7; };
  const VISC_LO = walther(46, 6.8), VISC_HI = walther(47.4, 9.5);
  const oilViscosity = (T) => ({ lo: VISC_LO(T), hi: VISC_HI(T) });
  // Alcance de la verificación térmica (term_alcance): 1 (default) = sistema de placas y disco; 2 = además accionamiento mecánico y circuito hidráulico.
  // Fuera de alcance (con 1): las filas se calculan igual pero se marcan `fuera` y no entran al estado, al FU térmico, al veredicto ni a los cambios de estado (sección informativa).
  const alcanceOf = (P) => (Math.round(P.term_alcance) === 2 ? 2 : 1);
  const ACC_GRPS = ["Pasadores de empuje", "Uña", "Patín y guía", "Articulaciones", "Fatiga", "Leva de reenganche", "Soporte del ojal E", "Placas-leva"];   // grupos de verificación estándar del accionamiento mecánico (cadena de empuje, ménsula del cilindro y su fatiga)
  // Copia de P con las capacidades reducidas a T (geometría congelada: frozen). ov: sobrescribe parámetros kT_* (sensibilidades); grad: gradiente plancha superior–inferior a T (K)
  function thermalP(P, T, ov, frozen, grad) {
    const th = thermalFactors(P, T, ov), k = th.k, Q = Object.assign({}, P);
    ["Fy", "Fy_pin", "Fy_dog", "Fy_pp", "Fy_piv", "Fy_shoe", "Fy_cara", "Fy_cam", "Fy_camP"].forEach((id) => { Q[id] = P[id] * k.Fy; });
    Q.E = P.E * k.E; Q.Fy_ss = P.Fy_ss * k.Fy_ss;
    ["Fy_bz", "Fy_bz2", "p_bz", "PV_bz", "p_bush"].forEach((id) => { Q[id] = P[id] * k.bz; });
    Q.p_uhmw = P.p_uhmw * k.p_uh; Q.PV_uh = P.PV_uh * k.p_uh; Q.E_uhmw = P.E_uhmw * k.E_uh; Q.p_wood = P.p_wood * k.wood; Q.FEXX = P.FEXX * k.weld; Q.Fy_surf = P.Fy_surf * k.hertz; Q.Fu_bolt = P.Fu_bolt * k.bolt;
    if (Math.abs(k.mu - 1) > 1e-12) ["mu_d", "mu_nom", "mu_cont", "mu_dry", "muA_nom", "muA_d", "muA_cont", "muA_dry", "muB_nom", "muB_d", "muB_cont", "muB_dry", "muC_nom", "muC_d", "muC_cont", "muC_dry"].forEach((id) => { Q[id] = P[id] * k.mu; });
    Q.__th = { T, dT: th.dT, grad: grad || 0, k, alpha: th.alpha, notes: th.notes, extrap: th.extrap, Fy0: P.Fy, P0: P, frozen: frozen || null, alc: alcanceOf(P) };
    return Q;
  }

  // Filas del escenario térmico (grupo «Temperatura»). Se agregan SOLO cuando P.__th existe (TT.thermal); el análisis estándar no las incluye.
  // Todas las filas se emiten siempre (también con ΔT = 0) para que sean comparables fila a fila entre temperaturas. conf = nivel de confianza del dato (A/B/C) del registro.
  function thermalRows(P, R, fea, out, add) {
    const th = P.__th, I = R.ifc, K = R.K, T = th.T, dT = th.dT, al = th.alpha, k = th.k, Ro = R.Ro, Ri = R.Ri;
    const nf = (v, d) => (+v).toFixed(d == null ? 2 : d).replace(".", ",");
    const REG = "docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»";
    const tadd = (o) => add(Object.assign({ grp: "Temperatura", sys: "est" }, o, o.acc && th.alc !== 2 ? { fuera: true } : {}));   // acc: accionamiento o circuito hidráulico (fuera de alcance con term_alcance = 1)
    const eps = al.st * dT;                                                   // dilatación libre del acero (α medio 20–T)
    const pd = R.cd ? R.cd.p : P.p_relief;

    /* (a) Dilatación diferencial en juntas de los sectores: la junta en frío es la del diseño a 20 °C (congelada) */
    (I.cortes || []).forEach((c) => {
      const alp = c.tgt === "uhmw" ? al.uh : c.tgt === "bz" ? al.bz : al.ss, chord = 2 * Ro * Math.sin(Math.PI / c.n), alN = c.tgt === "uhmw" ? "UHMW" : c.tgt === "bz" ? "bronce" : "inox";
      const pad = c.id === "bz0" && I.conf === 3, jReq = Math.max(0, alp - al.st) * dT * chord, jDisp = pad ? (1 - I.cov) * chord : c.j;
      if (!(jDisp > 0) && !(jReq > 0)) return;
      tadd({ sub: "a", conf: "C", name: c.pieza + ": junta de dilatación requerida frente a la disponible en frío (no debe cerrarse)",
        formula: "j_req = (α_" + alN + " − α_acero)·ΔT·cuerda = (" + nf(alp * 1e6, 0) + " − " + nf(al.st * 1e6, 1) + ")×10⁻⁶·ΔT·" + nf(chord, 0) + " mm ≤ j_disp (" + (pad ? "(1 − cobertura)·cuerda de la pastilla" : "junta en frío del diseño a 20 °C = máx(j_sec; dilatación a ΔT = " + P.dT + " K), a 0,1 mm") + "); si la junta cierra, el sector se comprime y pandea",
        dem: jReq, cap: jDisp, unit: "mm", ref: REG + " (cálculos del revisor: ~10 mm/m de diferencia UHMW–acero); α de ficha de fabricante" });
      tadd({ sub: "a", kind: "info", conf: "C", name: c.pieza + ": crecimiento radial relativo al respaldo (fijar al centro con agujeros ranurados)", formula: "Δr = (α_" + alN + " − α_acero)·ΔT·R_o", dem: Math.max(0, alp - al.st) * dT * Ro, unit: "mm", ref: REG });
    });

    /* (b) Pivote: buje de bronce (Ø int. D_piv, Ø ext. D_piv + 30) en cubo de acero y pasador de acero */
    {
      const a = P.D_piv / 2, b = a + 15, dal = Math.max(0, al.bz - al.st) * dT, ratio = 2 * a * b / ((b * b + a * a) - TH_NU_BZ * (b * b - a * a));
      const boreR = a * al.bz * dT - ratio * dal * b, pinR = a * al.st * dT, dClose = Math.max(0, -2 * (boreR - pinR));   // cierre diametral con el Ø exterior del buje guiado por el cubo de acero (Lamé, anillo comprimido)
      const pc = E_BZ * dal / ((b * b + a * a) / (b * b - a * a) - TH_NU_BZ), sth = 2 * pc * b * b / (b * b - a * a);
      tadd({ sub: "b", conf: "C", name: "Buje de bronce–pivote: cierre de la holgura diametral con el buje retenido por el cubo de acero", formula: "cierre = 2·[(a·α_bz·ΔT − ρ·(α_bz − α_acero)·ΔT·b) − a·α_acero·ΔT]; ρ = 2ab/((b² + a²) − ν(b² − a²)) (Lamé); ≤ holgura diametral en frío c_bush_d = " + nf(P.c_bush_d, 2) + " mm (supuesto H7/e8; el núcleo no define el ajuste)",
        dem: dClose, cap: P.c_bush_d, unit: "mm", ref: REG + " (α bronce 18, acero 12,4×10⁻⁶); hipótesis del revisor" });
      tadd({ sub: "b", kind: "info", conf: "C", name: "Buje de bronce–pivote: holgura con el buje libre (afloja) / interferencia buje–cubo (aprieta)", formula: "Δc = (α_bz − α_acero)·ΔT·D_piv (aumento de holgura si el buje fuera libre); Δi = (α_bz − α_acero)·ΔT·(D_piv + 30) (aumento de interferencia en el cubo)", dem: dal * P.D_piv, cap: dal * (P.D_piv + 30), unit: "mm (holgura libre / interferencia)", ref: REG });
      tadd({ sub: "b", kind: "info", conf: "C", name: "Buje de bronce retenido: tensión circunferencial por dilatación impedida frente al Fy del bronce de menor resistencia (por confirmar)", formula: "σ_θ = 2·p·b²/(b² − a²), p = E_bz·(α_bz − α_acero)·ΔT/((b² + a²)/(b² − a²) − ν)", dem: sth, cap: P.Fy_bz2 * k.bz, unit: "MPa", ref: REG });
    }

    /* (c) Uña–pasador: la mesa a T y la base a la sombra (a T_ref) es el caso desfavorable; con ambas a T el efecto relativo es el de la escala uniforme */
    if (driveMode(P) === 1) {
      const dR = eps * P.R_pin;
      tadd({ acc: true, sub: "c", sys: "giro", kind: "geo", conf: "B", name: "Uña–pasador (mesa caliente, base a la sombra): holgura radial de la uña en el patín con el crecimiento del círculo de pasadores", formula: "R·(1 − cos π/N)·(1 + ε) + 2 + α·ΔT·R_pin ≤ holgura radial del patín; ε = α·ΔT; α·ΔT·R_pin = " + nf(dR, 2) + " mm", dem: K.radial * (1 + eps) + 2 + dR, cap: P.slot, unit: "mm", ref: REG + " (EN 1993-1-1 §3.2.6; EN 1993-1-2 §3.4.1.1)" });
      tadd({ acc: true, sub: "c", sys: "giro", kind: "geo", conf: "B", name: "Uña–pasador (mesa caliente): luz de la uña entre pasadores (la cuerda y el pasador crecen con la mesa)", formula: "(cuerda − d_pas)·(1 + ε) ≥ b_uña + 2·10", dem: P.dog_b + 20, cap: K.gap * (1 + eps), unit: "mm", ref: REG });
      tadd({ acc: true, sub: "c", sys: "giro", kind: "geo", conf: "B", name: "Uña–pasador (mesa caliente): carrera requerida con el crecimiento de la cuerda", formula: "s_libre + cuerda·(1 + ε) + margen ≤ carrera", dem: P.s_free + K.chord * (1 + eps) + P.s_margin, cap: P.stroke, unit: "mm", ref: REG });
      tadd({ acc: true, sub: "c", kind: "info", conf: "B", name: "Uña–pasador, caso uniforme (mesa y base calientes): desplazamiento relativo por escala uniforme", formula: "(x_g − a_mín)·α·ΔT; sin efecto relativo apreciable", dem: (P.x_g - K.armMin) * eps, unit: "mm", ref: REG });
        } else {
      const dR = eps * P.R_pin;
      tadd({ acc: true, sub: "c", sys: "giro", kind: "geo", conf: "B", name: "Pivotado (mesa caliente, base a la sombra): carrera requerida con el crecimiento del círculo de pasadores", formula: "s_req·(1 + ε) + α·ΔT·R_pin + margen ≤ carrera (cota: el pasador se aleja de E a lo sumo α·ΔT·R)", dem: K.s_req * (1 + eps) + dR + P.s_margin, cap: P.stroke, unit: "mm", ref: REG + " (EN 1993-1-1 §3.2.6; EN 1993-1-2 §3.4.1.1)" });
      tadd({ acc: true, sub: "c", sys: "giro", kind: "geo", conf: "B", name: "Pivotado (mesa caliente): bloque-uña libre del pasador siguiente con el crecimiento del paso", formula: "holgura mínima en el empuje − α·ΔT·cuerda ≥ holgura mínima", dem: P.pv_cB, cap: K.clrB - eps * K.chord, unit: "mm", ref: REG });
      tadd({ acc: true, sub: "c", kind: "info", conf: "B", name: "Pivotado, caso uniforme (mesa y base calientes): desplazamiento relativo por escala uniforme", formula: "|E|·α·ΔT; sin efecto relativo apreciable", dem: K.RE * eps, unit: "mm", ref: REG });
    }
    /* (d) Gradiente plancha superior (al sol) – inferior (a la sombra) */
    {
      const wgT = woodGeo(P), g = th.grad, h = wgT ? P.h_disc - wgT.d_rebaje : P.h_disc, kap = al.st * g / h, sag = kap * (P.D_top / 2) ** 2 / 2, sigTh = P.E * al.st * g / (2 * (1 - P.nu));   // W: el cajón es más bajo dentro de R_reb (κ mayor, conservador; la madera además aísla la plancha rebajada)
      const gapR = kap * (Ro * Ro - Ri * Ri) / 2, win = kap * (P.ss_void / 2) ** 2 / 2;
      const GREF = REG + "; EN 1991-1-5 §6.1.4.1 Tabla 6.1 (tableros de puentes: otra tipología); σ de la placa restringida según Timoshenko";
      tadd({ sub: "d", kind: "info", conf: "C", name: "Gradiente: curvatura térmica de la mesa", formula: "κ = α·ΔT_grad/h con " + (wgT ? "h = h_mesa − d_rebaje = " + h + " mm (cubierta W: altura del cajón dentro del rebaje)" : "h = h_mesa = " + P.h_disc + " mm"), dem: kap * 1e3, unit: "1/m", ref: GREF });
      tadd({ sub: "d", kind: "info", conf: "C", name: "Gradiente: flecha en el diámetro de la mesa (plancha libre)", formula: "s = κ·(D/2)²/2", dem: sag, unit: "mm", ref: GREF });
      tadd({ sub: "d", kind: "info", conf: "C", name: "Gradiente: tensión de flexión térmica si la mesa está restringida", formula: "σ = E·α·ΔT_grad/(2(1 − ν)); cota con la restricción total (la real depende de la caja)", dem: sigTh, cap: 0.6 * P.Fy, unit: "MPa", ref: GREF });
      const comb = (re, nombre) => { const c = out.find((x) => x.grp !== "Temperatura" && x.fu != null && re.test(x.name)); if (c) tadd({ sub: "d", conf: "C", name: nombre, formula: "FU actual (" + c.name + ") con σ_térmica sumada (suma conservadora): (dem + σ_th)/cap", dem: c.dem + sigTh, cap: c.cap, unit: c.unit, ref: GREF }); };
      comb(/^Plancha superior: global \+ local$/, "Gradiente: plancha superior (global + local) más σ térmica restringida");
      comb(/^Plancha inferior: global \+ local$/, "Gradiente: plancha inferior (global + local) más σ térmica restringida");
      comb(/pared del cubo junto al rebaje/, "Gradiente: pared del cubo junto al rebaje del collar más σ térmica restringida");
      tadd({ sub: "d", kind: "info", conf: "C", name: "Gradiente: desnivel de la cara de contacto entre R_i y R_o (la mesa se abomba: el contacto pasa al borde exterior)", formula: "Δz = κ·(R_o² − R_i²)/2; la carga aplana la mesa si σ_th cabe (fila de σ combinada): entonces el contacto se restablece", dem: gapR, cap: P.d_flat, unit: "mm (desnivel / planitud d_flat)", ref: GREF });
      tadd({ sub: "d", kind: "geo", conf: "C", name: "Gradiente: variación del hueco de contacto en la ventana de medición (Ø = vacío local) frente a la planitud admitida", formula: "κ·(Ø_vacío/2)²/2 ≤ d_flat", dem: win, cap: P.d_flat, unit: "mm", ref: GREF });
    }

    /* (e) Aceite atrapado: cilindro + retenciones. El cilindro empuja contra la fricción (no sostiene W): p_hold = F_dis/A (≡ W/A de la carga sostenida) y, en calado, p_alivio */
    {
      const o = oilTrapped(P, T), sel = o.sel, dp = sel.hi.bar, dpLo = sel.lo.bar, pMax = P.p_max_cil, pTest = 1.5 * pMax, rel = P.alivio_term, lim = (p) => (rel > 0 ? Math.min(p, rel) : p);
      const OREF = REG + ", «Presión por aceite atrapado»; ISO 4413:2010 (cláusula por confirmar); prueba 1,5 × (ISO 10100 de memoria)";
      const TRAMO = "tramo aislado = cilindro + válvulas de retención/bloqueo y tapones; un alivio de sistema aguas arriba de la retención NO lo protege";
      tadd({ acc: true, sub: "e", sys: "term", kind: "info", conf: "C", name: "Aceite atrapado: sobrepresión térmica Δp (cota alta K = 1,9 GPa / cota baja K = 1,4 GPa)", formula: "Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c); α_v = 7,5×10⁻⁴/K, 3α_s = " + nf(o.as3 * 1e5, 2) + "×10⁻⁵/K; contenedor: " + ["rígido", "cilindro b/a " + nf(P.ba_cil, 2) + " (Lamé, K_c = " + nf(o.Kc_lame / 1000, 1) + " GPa)", "manguera (K combinado 327 MPa)"][Math.min(3, Math.max(1, Math.round(P.oil_cont))) - 1] + "; aire libre no se cuenta", dem: dp, cap: dpLo, unit: "bar (K alta / K baja)", ref: OREF });
      tadd({ acc: true, sub: "e", sys: "term", conf: "C", name: "Aceite atrapado en la carrera de diseño: p_hold + Δp térmico frente a la presión máxima de trabajo del cilindro", formula: "p_hold = F_dis/A (presión de diseño, ≡ W/A del pistón que sostiene la carga) + Δp ≤ p_max_cil" + (rel > 0 ? " (limitada por la apertura del alivio térmico " + rel + " bar)" : " (sin alivio térmico)") + "; la sobrepresión aparece solo con movimiento restringido (tope, fin de carrera, calado); " + TRAMO, dem: lim(pd + dp), cap: pMax, unit: "bar", ref: OREF });
      tadd({ acc: true, sub: "e", sys: "term", conf: "C", name: "Aceite atrapado tras el calado: p_alivio + Δp térmico frente a la presión de prueba del cilindro (1,5 × p_max)", formula: "p_alivio (700 bar: el calado deja la presión atrapada en el alivio del sistema) + Δp ≤ 1,5·p_max_cil; " + TRAMO, dem: lim(P.p_relief + dp), cap: pTest, unit: "bar", ref: OREF });
      tadd({ acc: true, sub: "e", sys: "term", conf: "C", name: "Aceite atrapado en la cámara anular (lado vástago): p_retorno + Δp térmico frente a la presión máxima de trabajo", formula: "p_ret + Δp ≤ p_max_cil (la cámara anular también queda aislada entre retención y tope)", dem: lim(P.p_ret + dp), cap: pMax, unit: "bar", ref: OREF });
      if (rel > 0) {
        tadd({ acc: true, sub: "e", sys: "term", kind: "geo", conf: "C", name: "Válvula de alivio térmico: apertura bajo la presión máxima de trabajo del cilindro", formula: "p_apertura ≤ p_max_cil", dem: rel, cap: pMax, unit: "bar", ref: OREF });
        tadd({ acc: true, sub: "e", sys: "term", kind: "geo", conf: "C", name: "Válvula de alivio térmico: apertura sobre el alivio del sistema (no gotea en operación ni a calado)", formula: "p_alivio ≤ p_apertura; con p_alivio = p_max_cil la ventana de ajuste es nula: bajar el alivio del sistema o usar un cilindro de mayor presión", dem: P.p_relief, cap: rel, unit: "bar", ref: OREF });
      } else {
        const risk = pd + dp > pMax + 1e-9 || P.p_relief + dp > pTest + 1e-9 || P.p_ret + dp > pMax + 1e-9;
        tadd({ acc: true, sub: "e", sys: "term", conf: "C", stFix: risk ? "fail" : "ok", name: "Válvula de alivio térmico del tramo aislado (cilindro + retenciones): no hay" + (risk ? " y hay riesgo: instalar válvula de alivio térmico en el tramo aislado" : ""), formula: "alivio_term = 0 (no hay): " + (risk ? "instalar válvula de alivio térmico en el tramo aislado (cilindro + retenciones), con apertura entre el alivio del sistema y la presión máxima de trabajo; " : "") + TRAMO, dem: pd + dp, cap: pMax, unit: "bar", ref: OREF });
      }
      tadd({ acc: true, sub: "e", sys: "term", kind: "info", conf: "C", name: "Aceite: dilatación libre (si el pistón puede moverse bajo carga la presión se mantiene en p_hold y la expansión sale como carrera)", formula: "ΔV/V = (α_v − 3α_s)·ΔT; 1 m de columna de aceite se alarga ΔV/V·1 000 mm", dem: o.expansion_free_pct, cap: o.expansion_1m_mm, unit: "% / mm por m de columna", ref: OREF });
    }

    /* (f) Aceite, sellos y bomba */
    {
      const v = oilViscosity(T), SREF = REG + ", «Viscosidad a 80 °C» y sellos NBR (Ulman -30 a +80; Machine Design 90–100; Power & Motion -40 a 120)";
      tadd({ acc: true, sub: "f", sys: "term", conf: "C", name: "Aceite VG 46: viscosidad a T_serv frente al mínimo de la bomba", formula: "ν_mín,bomba = " + P.nu_min + " mm²/s (supuesto) ≤ ν(T) (Walther ASTM D341 con ν40 = 46 y ν100 = 6,8 → " + nf(v.lo, 1) + " mm²/s; con IV 185 → " + nf(v.hi, 1) + " mm²/s)", dem: P.nu_min, cap: v.lo, unit: "mm²/s", ref: SREF });
      tadd({ acc: true, sub: "f", sys: "term", conf: "C", stFix: T <= P.T_seal ? (T > 0.9 * P.T_seal ? "warn" : "ok") : (T <= 120 ? "warn" : "fail"), name: "Sellos NBR: temperatura de servicio frente al límite de las fuentes (80–120 °C)", formula: "T ≤ T_seal = " + P.T_seal + " °C (el menor de 80–120 °C); entre ese valor y 120 °C solo monitoreo; PU/FKM: FKM hasta 200 °C", dem: T, cap: P.T_seal, unit: "°C", ref: SREF });
      tadd({ acc: true, sub: "f", sys: "term", kind: "info", conf: "C", name: "Bomba con viscosidad baja: más fugas internas (menor caudal útil y rendimiento volumétrico); potencia del motor sin cambio apreciable", formula: "solo nota: Pmotor = p·Q/(600·η) con η a 20 °C; confirmar con la curva de la bomba a ν(T)", dem: R.pump.Pmotor, cap: v.lo, unit: "kW / mm²/s", ref: SREF });
    }

    /* (g) Lubricación */
    {
      const GREF = REG + ", «Grasa NLGI 2 con MoS₂/grafito» (ASTM D2265; fichas Mobil, SKF, Lubriplate)";
      tadd({ sub: "g", sys: "term", conf: "B", name: "Grasa grafitada: temperatura frente al punto de goteo (margen ≥ 95 K a 80 °C)", formula: "T ≤ T_goteo = " + P.T_drop + " °C; margen = T_goteo − T = " + nf(P.T_drop - T, 0) + " K", dem: T, cap: P.T_drop, unit: "°C", ref: GREF });
      const FSd = R.cd ? R.cd.FS : NaN;
      [0.8, 1, 1.2, 1.5].forEach((f) => tadd({ sub: "g", sys: "term", kind: "info", conf: "C", name: "Sensibilidad al μ de la grasa a T_serv (dato de entrada): FS del giro con μ × " + nf(f, 1), formula: "FS(μ·f) = FS_dis/f (F lineal en μ); FS_mín = " + P.FS_min + "; el μ real a T_serv no tiene fuente (la grasa fluida y la expulsión lo suben)", dem: FSd / f, cap: P.FS_min, unit: "– (FS / FS_mín)", ref: GREF }));
    }

    /* (h) UHMW-PE: capacidades ya reducidas en P (p_adm, PV, E) */
    if (I.o === 2) {
      const UREF = REG + ", «Interfaz UHMW-PE (opción B)» y filas UHMW-PE (fichas Quadrant/Mitsubishi, Ensinger, Röchling; sin curva a 80 °C)";
      tadd({ sub: "h", kind: "info", conf: "C", name: "Lámina UHMW: factores aplicados a la capacidad (k_p sobre p_adm y PV) y al módulo (k_E)", formula: "k_p = " + nf(k.p_uh, 3) + ", k_E = " + nf(k.E_uh, 3) + " (supuestos: sin curva del proveedor); la geometría de la lámina (espesor, tope) está congelada a 20 °C", dem: k.p_uh, cap: k.E_uh, unit: "– / –", ref: UREF });
      tadd({ sub: "h", kind: "info", conf: "C", name: "Lámina UHMW: acortamiento elástico bajo q_máx con el módulo reducido (flecha local en la ventana)", formula: "δ = q_máx·t/E_c(S); E_c = E_ap·k_E·[1 + (M/E − 1)S²/(1 + S²)]; E reducida aumenta la deformación bajo carga (y la fluencia, nota)", dem: I.q * I.tuh / I.EcU, cap: P.d_flat, unit: "mm (δ / planitud d_flat)", ref: UREF });
      const vcyl = P.Q_pump * 1e6 / 60 / (P.n_cyl * R.A), vmax = R.Ro / K.armMin * vcyl / 1000, PV20 = P.PV_uh / k.p_uh;
      tadd({ sub: "h", kind: "info", conf: "C", name: "Lámina UHMW: PV admisible por balance térmico, PV(T) = PV₂₀·(80 − T)/(80 − T_ref) (cota inferior: se anula a 80 °C)", formula: "criterio del revisor (confianza C): el calor friccional ya no se evacua cuando T_ambiente = T_límite; compárese con la fila de PV con k_p", dem: I.q * vmax, cap: PV20 * Math.max(0, (80 - T) / (80 - P.T_ref)), unit: "MPa·m/s", ref: UREF });
      tadd({ sub: "h", conf: "B", name: "Lámina UHMW: temperatura frente al límite de servicio continuo (80 °C; Vicat B50 = 80 °C)", formula: "T ≤ 80 °C", dem: T, cap: 80, unit: "°C", ref: UREF });
      tadd({ sub: "h", kind: "pend", conf: "C", name: "UHMW-PE a T_serv: exigir al proveedor la curva de módulo y de límite elástico entre 20 y 80 °C, creep (módulo de fluencia 550 → 300 MPa de 1 h a 1 000 h a 23 °C; +15 K ≈ tensión × 0,63) y desgaste a T", formula: "Sin verificación numérica: k_p y k_E son supuestos", dem: 0, unit: "–", ref: UREF });
    }
    if (I.o === 3) tadd({ sub: "h", kind: "pend", conf: "C", name: "Bronce con grafito a T_serv: la ficha de temperatura hallada es de C93200; confirmar C95400 (Fy, α) con el proveedor", formula: "Sin verificación numérica: k_bz = " + nf(k.bz, 2) + " es criterio de ingeniería", dem: 0, unit: "–", ref: REG + ", «Interfaz de bronce con grafito (opción C)»" });

    /* (i) Madera: C_t sobre p_wood (ya aplicado a P.p_wood) */
    if (P.opt_wood > 0.5) {
      const w = out.find((x) => x.grp === "Cubierta" && /Madera: aplastamiento/.test(x.name)), p0 = P.p_wood / k.wood;
      tadd({ sub: "i", kind: "info", conf: "C", name: "Madera: factor C_t aplicado al aplastamiento perpendicular a la fibra y sensibilidad con madera húmeda (C_t = 0,50 a 125–150 °F)", formula: "FU(C_t) = q/(p_wood·C_t); C_t seca = " + nf(k.wood, 2) + " (NDS 2018 T2.3.3, copia AWC: A en la tabla, 80 °C = 176 °F fuera de ella, extrapolación C)", dem: w ? w.dem / (p0 * 0.5) : NaN, cap: w ? w.dem / p0 : NaN, unit: "– (FU con C_t = 0,50 / FU con C_t = 1)", ref: REG + ", «Madera dura»; NDS 2018 Tabla 2.3.3" });
      const wgM = woodGeo(P);
      if (wgM) tadd({ sub: "i", kind: "geo", conf: "C", name: "Madera: holgura perimetral frente a la dilatación transversal a T (madera y acero a T)", formula: "(α_madera,⊥ − α_acero)·ΔT·2·R_tablones ≤ 2·c_mad + (n − 1)·j_tab; α⊥ = " + nf(al.woodT * 1e6, 0) + "×10⁻⁶ (C), α_acero = " + nf(al.st * 1e6, 1) + "×10⁻⁶, ΔT = " + nf(dT, 0) + " K (holguras del diseño a 20 °C)", dem: Math.max(0, al.woodT - al.st) * dT * 2 * wgM.R_tablones, cap: 2 * P.c_mad + (wgM.tablones.n - 1) * P.j_tab, unit: "mm", ref: REG + ", «Madera dura»; docs/normas/registro.md, «Cubierta de madera W (rebaje)»" });
      tadd({ sub: "i", kind: "pend", conf: "C", name: "Madera: el secado al sol baja la humedad de equilibrio (sube la resistencia, aparecen grietas y deformación de tablones); NCh1198 sin factor de temperatura confirmado", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: REG + ", «Madera dura»" });
    }

    /* (j) Acero estructural, soldaduras, pernos */
    tadd({ sub: "j", kind: "info", conf: "B", name: "Acero estructural y cadena de empuje: factor de Fy y de E aplicados (1,00 por AISC App. 4 / EN 1993-1-2; sensibilidad ASME II-D: 0,92, confianza C)", formula: "k_Fy = " + nf(k.Fy, 3) + ", k_E = " + nf(k.E, 3) + ", soldadura k = " + nf(k.weld, 2) + " (C); el App. 4 de AISC es de exposición al fuego: sirve de cota, no de norma de servicio sostenido", dem: k.Fy, cap: k.weld, unit: "– / –", ref: REG + ", «Acero estructural y cadena de empuje a 80 °C»" });
    tadd({ sub: "j", kind: "info", conf: "C", name: "Pernos 10.9: factor de Rp0,2 (0,94, de memoria de ISO 898-1); el modelo no tiene verificación de resistencia de pernos (los tornillos de posición ISO 10642 no transmiten carga)", formula: "k_perno = " + nf(k.bolt, 3) + " aplicable si se agregan uniones atornilladas", dem: k.bolt, unit: "–", ref: REG + ", «Pernos ISO 898-1 clase 10.9»" });
    tadd({ sub: "j", kind: "pend", conf: "C", stFix: T > 66 ? "pend" : "info", name: "ASME BTH-1: 80 °C (176 °F) excede el rango estándar (−4 a 66 °C): requiere decisión de persona calificada y registro de la hipótesis", formula: "Nd = 3,0 no incluye un margen térmico explícito; sección de BTH-1 sobre temperatura sin confirmar", dem: T, cap: 66, unit: "°C", ref: REG + ", «Alcance térmico de BTH-1»" });

    /* (k) Dilatación global */
    {
      const Dm = P.D_top * eps, Db = P.B * eps;
      tadd({ sub: "k", kind: "info", conf: "B", name: "Dilatación global: crecimiento del diámetro de la mesa (y de la base)", formula: "ΔD = α·ΔT·D (≈ 0,7 mm/m a ΔT = 60 K); la base: ΔB = α·ΔT·B", dem: Dm, cap: Db, unit: "mm (mesa / base)", ref: REG + ", «Dilatación libre»" });
      if (driveMode(P) === 1) {
        tadd({ acc: true, sub: "k", sys: "giro", kind: "geo", conf: "B", name: "Patín fuera de la mesa con la mesa caliente (base a la sombra)", formula: "(D/2)(1 + ε) + 15 ≤ x_g − w_s/2", dem: Ro * (1 + eps) + 15, cap: P.x_g - P.w_s / 2, unit: "mm", ref: REG });
        tadd({ acc: true, sub: "k", sys: "giro", kind: "geo", conf: "B", name: "Bancada de guía fuera de la mesa con la mesa caliente (base a la sombra)", formula: "(D/2)(1 + ε) + 10 ≤ x_g − w_bancada/2", dem: Ro * (1 + eps) + 10, cap: P.x_g - P.w_bed / 2, unit: "mm", ref: REG });
      } else if (K.ok) {
        tadd({ acc: true, sub: "k", sys: "giro", kind: "geo", conf: "B", name: "Pasador Q fuera de la mesa con la mesa caliente (base a la sombra)", formula: "(D/2)(1 + ε) + d_Q/2 + holgura ≤ mín |Q|", dem: Ro * (1 + eps) + P.pv_dq / 2 + P.pv_cQ, cap: K.QrMin, unit: "mm", ref: REG });
        tadd({ acc: true, sub: "k", sys: "giro", kind: "geo", conf: "B", name: "Cuerpo del cilindro fuera de la mesa con la mesa caliente (base a la sombra)", formula: "(D/2)(1 + ε) + D_cuerpo/2 + holgura ≤ mín dist(O, cuerpo)", dem: Ro * (1 + eps) + P.D_body / 2 + P.pv_cc, cap: K.body + P.D_body / 2 + P.D_top / 2, unit: "mm", ref: REG });
      }
    }
  }

  /* ---------------- API de simulación del movimiento (UI: packages/web/simulacion.js) ---------------- */
  // Funciones puras y deterministas: los resultados pesados (compute, levas) se memorizan por el contenido de P (caché acotada).
  const simCache = new Map();
  function simR(P) {
    const key = JSON.stringify(P);
    let R = simCache.get(key);
    if (!R) { R = compute(P); if (simCache.size > 8) simCache.clear(); simCache.set(key, R); }
    return R;
  }
  const caseOf = (R, caseId) => R.cases.find((c) => c.id === (caseId || "dis")) || R.cases.find((c) => c.id === "dis");
  // 1. Fuerzas en el ángulo θ del pasador tomado (rad) para un caso de fricción («nom», «dis», «borde», «cont», «seco»), en ambos modos.
  //    Guiado: θ ∈ [−π/N, π/N] (lado +x, empuje +y). Pivotado: θ absoluto del pasador que empuja el cilindro 1 (giro antihorario), θ ∈ [θ_ini, θ_fin].
  //    F = cilindro (kN), Fp = normal sobre el pasador (kN), H = roce de la cara (kN), Rf/Rr = reacciones de guía (kN; 0 en el pivotado),
  //    arm = brazo de la normal (mm), ft/fr = fracciones tangencial/radial de la normal sobre el pasador.
  function driveAtSim(P, th, caseId) {
    const R = simR(P), c = caseOf(R, caseId), T = c ? c.T : 0;
    if (driveMode(P) === 2) {
      const K = R.K; if (!K.ok) return null;
      const g = R.camP && R.camP.guidedAt ? R.camP.guidedAt(th) : null;   // Q apoyado en el canto de la placa-guía (mismo modelo que compute)
      if (g && g.ok) { const Fp = T * 1e3 / P.n_cyl / g.arm, Fe = Fp / g.fn; return { F: Fe / P.eta_c, Fp, H: P.mu_s * Fp, Fcam: g.h * Fe, Rf: 0, Rr: 0, arm: g.arm, armEff: g.arm * g.fn, ft: g.ft, fr: g.fr, caso: c.id }; }
      const q = K.at(th); q.aEff = q.a - P.mu_s * Math.abs(q.vs);
      const Fp = T * 1e3 / P.n_cyl / q.aEff;
      return { F: Fp * (1 + R.fam.mu * P.mu_s) / P.eta_c, Fp, H: P.mu_s * Fp, Fcam: P.mu_s * Fp, Rf: 0, Rr: 0, arm: q.a, armEff: q.aEff, ft: q.ft, fr: q.fr, caso: c.id };
    }
    const d = driveAtG(P, R.K, th, P.R_pin * Math.sin(th) >= P.d_pin / 2 ? 1 : -1), Fp = T * 1e3 / P.n_cyl / d.den;
    return { F: Fp * d.fr / P.eta_c, Fp, H: d.h * Fp, Rf: d.rf * Fp, Rr: d.rr * Fp, arm: P.R_pin * Math.cos(th), ft: Math.cos(th), fr: Math.sin(th), caso: c.id };
  }
  // Transformaciones de planta del modo pivotado: cilindro 1 en φ_E con giro antihorario; cilindro 2 = rotación 180°; horario = reflexión respecto de la diagonal O–E
  function pivTr(P, sentido, cil) {
    const ph = P.pv_phE * D2R, ed = [Math.cos(ph), Math.sin(ph)];
    const refl = (q) => { const d = q[0] * ed[0] + q[1] * ed[1]; return [2 * d * ed[0] - q[0], 2 * d * ed[1] - q[1]]; };
    const h = sentido === "horario", c2 = cil === 2;
    return (q) => { let o = h ? refl(q) : [q[0], q[1]]; if (c2) o = [-o[0], -o[1]]; return o; };
  }
  function unaPolys(P, Q, u, Lqp) {   // polígonos del bloque-uña en planta (cuerpo acodado, tramo de la cara, cubo de Q aproximado con 24 lados)
    const r = P.d_pin / 2, s2 = Lqp - r, s1 = s2 - P.pv_lf, eb = P.pv_dq / 2 + 25, t = [-u[1], u[0]];
    const rect = (o, a, b, w) => [[a, -1], [b, -1], [b, 1], [a, 1]].map(([s, k]) => [o[0] + s * u[0] + k * w / 2 * t[0], o[1] + s * u[1] + k * w / 2 * t[1]]);
    const Qs = [Q[0] - P.pv_ecr * t[0], Q[1] - P.pv_ecr * t[1]];
    return { cuerpo: rect(Qs, -eb, s1, P.pv_bu), cara: rect(Q, s1, s2, P.pv_bf), cubo: Array.from({ length: 24 }, (_, k) => [Q[0] + eb * Math.cos(k * Math.PI / 12), Q[1] + eb * Math.sin(k * Math.PI / 12)]) };
  }
  // Elementos sobre la base (planta + cota z) y sus holguras: orejas de izaje (huella radial 2R × (t + 2w) con los filetes), soportes del ojal E (piezas reales),
  // placas-guía, mesa con su interfaz y topes (R ≤ D/2), y en el modo pivotado las partes móviles (cuerpo y vástago del cilindro, bloque-uña con el cubo de Q) en los
  // estados del empuje y del retorno, ambos sentidos y ambos cilindros. En el modo guiado: bancadas, prolongaciones, pórticos, riel-leva, patines y cilindros.
  function earPolys(P) {
    const yl = P.B / 2 - P.c_lug, hw = P.t_ear / 2 + P.w_ear;
    return [[P.x_lug, yl], [-P.x_lug, yl], [P.x_lug, -yl], [-P.x_lug, -yl]].map((c) => { const r = Math.hypot(c[0], c[1]) || 1, u = [c[0] / r, c[1] / r], n = [-u[1], u[0]];
      return { centro: c, poly: [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, k]) => [c[0] + a * P.R_ear * u[0] + k * hw * n[0], c[1] + a * P.R_ear * u[1] + k * hw * n[1]]), z: [P.t_base, P.t_base + P.h_ear + P.R_ear] }; });
  }
  const circPoly = (R, n) => Array.from({ length: n }, (_, k) => [R * Math.cos(2 * Math.PI * k / n), R * Math.sin(2 * Math.PI * k / n)]);
  function pivMoving(P, R) {   // partes móviles del modo pivotado en planta (coordenadas reales), por estado
    const K = R.K, CP = R.camP, zc0 = hAxis(P) + P.t_base, bk = R.blk, st = [];
    CP.push.filter((g) => g.ok).forEach((g) => st.push({ Q: g.Q, b: g.b }));
    CP.guia.ret.forEach((q, i) => { if (i % 3 === 0) { const o = CP.Qof(q.L, q.w); st.push({ Q: o.Q, b: o.u }); } });
    for (let i = 0; i <= 10; i++) { const L = P.L0 + (K.Ls + 5 - P.L0) * i / 10, o = CP.Qof(L, P.pv_c); st.push({ Q: o.Q, b: o.u }); }   // aproximación con Q en la toma
    const out = [];
    [1, 2].forEach((cil) => ["antihorario", "horario"].forEach((sen) => { const f = pivTr(P, sen, cil), E = f(K.E);
      st.forEach((s) => { const Q = f(s.Q), d = Math.hypot(Q[0] - E[0], Q[1] - E[1]), u = [(Q[0] - E[0]) / d, (Q[1] - E[1]) / d], n = [-u[1], u[0]];
        const rr = (s0, s1, w) => [[s0, -w / 2], [s1, -w / 2], [s1, w / 2], [s0, w / 2]].map(([a, k]) => [E[0] + a * u[0] + k * n[0], E[1] + a * u[1] + k * n[1]]);
        const b2 = f([s.Q[0] + s.b[0], s.Q[1] + s.b[1]]), bb = [b2[0] - Q[0], b2[1] - Q[1]], pol = unaPolys(P, Q, bb, K.Lqp);
        out.push({ cil, sentido: sen, partes: [{ id: "cuerpo del cilindro", poly: rr(P.e_body, P.L0 - P.c_rod, P.D_body), z: [zc0 - P.D_body / 2, zc0 + P.D_body / 2] }, { id: "vástago", poly: rr(P.L0 - P.c_rod, d, P.d_rod), z: [zc0 - P.d_rod / 2, zc0 + P.d_rod / 2] },
          { id: "bloque-uña", poly: pol.cuerpo, z: [bk.zBot, bk.zBot + P.pv_hu] }, { id: "bloque-uña", poly: pol.cara, z: [bk.zBot, bk.zBot + P.pv_hu] }, { id: "cubo y pasador Q", poly: pol.cubo, z: [P.t_base + 2, bk.zBot + P.pv_hu] }] }); }); }));
    return out;
  }
  const bcCache = new WeakMap(), baseClearOf = (P, R) => { if (!bcCache.has(R)) bcCache.set(R, baseClear(P, R)); return bcCache.get(R); };
  function baseClear(P, R) {
    const ears = earPolys(P), mode = driveMode(P), zOv = (a, b) => a[0] < b[1] && b[0] < a[1], box = (pl) => { const xs = pl.map((p) => p[0]), ys = pl.map((p) => p[1]); return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]; };
    const near = (a, b, m) => a.bb[0] - m < b.bb[1] && b.bb[0] - m < a.bb[1] && a.bb[2] - m < b.bb[3] && b.bb[2] - m < a.bb[3];
    const W = (o) => Object.assign(o, { bb: box(o.poly) }), BIG = 500;
    const dmin = (As, Bs) => { let d = Infinity, who = null; As.forEach((a) => Bs.forEach((b) => { if (!zOv(a.z, b.z) || !near(a, b, BIG)) return; const x = PG.dist(a.poly, b.poly); if (x < d) { d = x; who = [a.id, b.id]; } })); return { d, who }; };
    ears.forEach((e, i) => W(Object.assign(e, { id: "oreja de izaje " + (i + 1) })));
    const mesa = W({ id: "mesa con la interfaz y sus topes (R = D/2)", poly: circPoly(P.D_top / 2, 144), z: [P.t_base, Infinity] }), out = { ears, mode };
    out.earMesa = dmin(ears, [mesa]);
    if (mode === 2 && R.K && R.K.ok && R.camP && R.camP.guia && R.sup) {
      const CP = R.camP, sg = R.sup, plates = [], sup = [];
      [1, 2].forEach((cil) => ["antihorario", "horario"].forEach((sen) => { const f = pivTr(P, sen, cil); plates.push(W({ id: "placa-guía " + cil + "_" + sen, poly: CP.guia.polilinea_contorno.map(f), z: [P.t_base, P.t_base + P.pv_tcam] })); }));
      [1, 2].forEach((cil) => sg.piezas.forEach((q) => sup.push(W({ id: "soporte E " + cil + " · " + q.id, poly: q.poly.map(sg.toReal(cil)), z: q.z }))));
      const mov = []; pivMoving(P, R).forEach((s) => s.partes.forEach((p) => mov.push(W(Object.assign({}, p, { id: p.id + " (cilindro " + s.cil + ", " + s.sentido + ")" })))));
      Object.assign(out, { plates, sup, plateEar: dmin(plates, ears), plateSup: dmin(plates, sup), plateMesa: dmin(plates, [mesa]), earSup: dmin(ears, sup), earPlate: dmin(ears, plates), earMov: dmin(ears, mov), nMov: mov.length });
    } else if (mode === 1) {
      const g = guideGeo(P), c = R.camG, fix = [];
      [1, -1].forEach((sx) => {   // banda ocupada por el accionamiento guiado de cada lado: bancada (± prolongación), patín, cilindro, riel-leva y pórticos
        const x0 = Math.min(P.x_g - P.w_s / 2, P.x_g - P.w_bed / 2, P.x_g - P.D_body / 2, c ? Math.min(c.xFp0 - P.cam_df / 2, c.portico.xL - c.portico.capW / 2) : Infinity) - 5;
        const x1 = Math.max(P.x_g + P.w_s / 2, P.x_g + P.w_bed / 2, P.x_g + P.D_body / 2, c ? Math.max(c.xPo, c.portico.xR + c.portico.capW / 2) : -Infinity) + 5, y1 = g.Y_bed + (c ? P.cam_ls : 0) + 5;
        fix.push(W({ id: "accionamiento guiado (lado " + (sx > 0 ? "+" : "−") + "x)", poly: PG.rect(sx > 0 ? x0 : -x1, sx > 0 ? x1 : -x0, -y1, y1), z: [P.t_base, Infinity] }));
      });
      Object.assign(out, { earDrive: dmin(ears, fix) });
    }
    return out;
  }
  // 2. Geometría fija del modo pivotado: ojales, placas-guía (canto curvo de tramos tangentes, contorno, tornillos y pasadores de posición por cilindro y sentido),
  //    bloque-uña (marco local), pasador Q, L0 y carrera. segmentos_*: {tipo: "linea" | "arco", p0, p1, centro, radio, sentido, rol, curvatura} en orden (G1 en el canto).
  function pivotGeo(P) {
    const R = simR(P), K = R.K, CP = R.camP;
    if (driveMode(P) !== 2 || !K.ok || !CP || !CP.guia) return null;
    const g = CP.guia, placas = {};
    [1, 2].forEach((cil) => ["antihorario", "horario"].forEach((sen) => {
      const f = pivTr(P, sen, cil), mir = sen === "horario", T = (S) => S.map((x) => GV.tr(x, f, mir));
      placas[cil + "_" + sen] = { recorte: g.polilinea_canto.map(f), contorno: g.polilinea_contorno.map(f), pernos: CP.bolts.map(f), pasadores_posicion: CP.dowels.map(f), centro_seguidor: g.polilinea_recorrido.map(f),
        segmentos_canto: T(g.canto), segmentos_centro: T(g.tramos), segmentos_contorno: T(g.contorno), tolerancia_polilinea: g.tol };
    }));
    const loc = unaPolys(P, [0, 0], [1, 0], K.Lqp);
    return { E: [K.E, [-K.E[0], -K.E[1]]], R_E: K.RE, phi_E: P.pv_phE, L_qp: K.Lqp, L0: P.L0, carrera: P.stroke, s_libre: P.s_free, s_req: CP.sReqG, th_ini: K.ths, th_fin: K.the, paso: K.pitch,
      placas, t_placa: P.pv_tcam, flanco_deg: CP.alpha, radio_min_canto_convexo: g.rCanto.convexo, radio_min_canto_concavo: g.rCanto.concavo,
      bloque: { local: loc, nota: "marco local: origen en Q, eje x hacia el pasador tomado (s), eje y = t (hacia el centro O); la cara es cilíndrica convexa de radio R_cara con vértice en x = L_qp − r (el rectángulo es su envolvente)", d_Q: P.pv_dq, h: P.pv_hu, R_cubo: P.pv_dq / 2 + 25, R_cara: R.blk.Rf, contacto_desde_eje: R.blk.ec, giro_equilibrio_deg: R.blk.dBlk / D2R },
      pasadorQ: { d: P.pv_dq, largo: R.blk.lPin }, ojalE: { d: P.pv_dE, lado_cajon: P.pv_box } };
  }
  // 2b. Cubierta de madera W para el dibujo de la simulación (planta): círculo de los tablones, abertura de la tapa, cara interior de la pared y anillo; null sin cubierta
  function cubiertaGeo(P) {
    const g = woodGeo(P); if (!g) return null;
    return { R_tablones: g.R_tablones, R_abertura: g.R_abertura, R_rebaje: g.R_rebaje, R_pared_ext: g.R_pared_ext, R_ext: g.R_ext, t_madera: g.t_madera, tablones: g.tablones.lista.map((t) => ({ y0: t.y0, y1: t.y1, corte: t.corte })), juntas: g.tablones.j };
  }
  // 3. Estado del modo pivotado en la posición s del vástago (s = L − L0, 0 … s_req). fase = «empuje» | «retorno»; sentido = «antihorario» | «horario» (cilindro 1).
  //    Empuje: aproximación con Q en el nivel de toma (w = c) hasta que la cara toca el pasador; la rodilla E–Q–P se abre hacia afuera (θ = θ_ini) hasta apoyar Q
  //    en el canto, y desde ahí Q recorre el canto con |P(θ) − Q| = L_qp (empuje guiado, fuerzas del caso de diseño). Retorno (mesa detenida en θ_fin): Q conserva ψ
  //    salvo que el pasador lo empuje hacia afuera (holgura 0) y el canto lo devuelve a la toma (conducción final, enRampa). alertas.sincronia: con Q contra el canto
  //    la holgura es menor que el margen; alertas.choque: posición con interferencia.
  function pivotAt(P, s, fase, sentido) {
    const R = simR(P), K = R.K, CP = R.camP;
    if (driveMode(P) !== 2 || !K.ok || !CP || !CP.guia) return null;
    const V = GV, g = CP.guia, L = P.L0 + Math.max(0, Math.min(s, CP.sReqG)), f = pivTr(P, sentido, 1), rf = P.pv_dq / 2, c = P.pv_c;
    const cantoAt = (LL) => { const o = CP.onPath(LL); return V.sub(o.p, V.mul(V.left(o.t), rf)); };
    let th, Q, u, b, Fc = 0, dr = null, hol = Infinity, holL = Infinity, enRampa = false, enCanto = false, contacto;
    if (fase !== "retorno") {
      th = K.ths; const Pi = [P.R_pin * Math.cos(th), P.R_pin * Math.sin(th)], g0 = CP.push[0];
      const dQP = (LL) => V.nrm(V.sub(CP.Qof(LL, c).Q, Pi)) - K.Lqp;
      let Lc = P.L0; if (dQP(P.L0) > 0) { let lo = P.L0, hi = K.Lend; for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (dQP(mid) > 0) lo = mid; else hi = mid; } Lc = lo; }
      if (L <= Lc || !g0.ok) { const o = CP.Qof(L, c); Q = o.Q; u = o.u; b = u; contacto = cantoAt(L); }
      else if (L < g0.L) {   // la rodilla se abre con la mesa quieta hasta que Q apoya en el canto
        const xs = V.circles(K.E, L, Pi, K.Lqp).sort((p, q) => CP.toLW(q)[1] - CP.toLW(p)[1]);
        Q = xs.length ? xs[0] : CP.Qof(L, c).Q; u = V.unit(V.sub(Q, K.E)); b = V.unit(V.sub(Pi, Q)); contacto = cantoAt(L);
      } else {
        const pu = CP.push; let i = 1; while (i < pu.length - 1 && !(pu[i].ok && pu[i].L >= L)) i++;
        let lo = pu[i - 1].th, hi = pu[i].th; for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2, gm = CP.guidedAt(mid); if (gm.ok && gm.L < L) lo = mid; else hi = mid; }
        th = (lo + hi) / 2; const gd = CP.guidedAt(th);
        Q = gd.Q; u = gd.uc; b = gd.b; contacto = gd.contacto; enCanto = true; dr = driveAtSim(P, th, "dis"); Fc = dr.Fcam;
      }
    } else {
      th = K.the; const rt = g.ret; let k = 1; while (k < rt.length - 1 && rt[k].L > L) k++;
      const a = rt[k - 1], bb = rt[k], t = (a.L - L) / ((a.L - bb.L) || 1), Wv = CP.wCam(L);
      let w = a.guia && bb.guia ? Wv : Math.min(Wv, a.w + (bb.w - a.w) * t);
      if (w < Wv && CP.clrRet(L, w) < 0) { let lo = w, hi = Wv; for (let i = 0; i < 50; i++) { const mid = (lo + hi) / 2; if (CP.clrRet(L, mid) >= 0) hi = mid; else lo = mid; } w = hi; }   // el pasador empuja el bloque (holgura 0)
      const o = CP.Qof(L, w); Q = o.Q; u = o.u; b = u; contacto = cantoAt(L);
      hol = CP.clrRet(L, w); holL = CP.clrRet(L, Wv); enRampa = L <= g.primer_contacto.L + 1e-9; enCanto = w >= Wv - 1e-9;
    }
    const w = CP.toLW(Q)[1], pol = unaPolys(P, Q, b, K.Lqp), tr = (pg) => pg.map(f);
    return { th: sentido === "horario" ? 2 * P.pv_phE * D2R - th : th, th_cil1_antihorario: th, L, s: L - P.L0, phi: Math.atan2(u[1], u[0]), phi_f: Math.atan2(f([u[0], u[1]])[1], f([u[0], u[1]])[0]), w, Q: f(Q), E: f(K.E),
      una: { poligono: tr(pol.cuerpo).concat(tr(pol.cara)), cuerpo: tr(pol.cuerpo), cara: tr(pol.cara), cubo: tr(pol.cubo) },
      contactoLeva: { punto: f(contacto), F: Fc, enRampa, enCanto },
      arm: dr ? dr.arm : null, armEff: dr ? dr.armEff : null, ft: dr ? dr.ft : null, fr: dr ? dr.fr : null, F: dr ? dr.F : 0,
      pasadores: { A: f([P.R_pin * Math.cos(th), P.R_pin * Math.sin(th)]), B: f([P.R_pin * Math.cos(th - K.pitch), P.R_pin * Math.sin(th - K.pitch)]) },
      holgura: hol, holgura_leva: holL, alertas: { sincronia: holL < P.pv_msync && enRampa, choque: hol < -1e-6 } };
  }

  // 4. Modo guiado con leva de reenganche: perfil del riel y estado en la posición s del vástago (s = 0 retraído … s_req).
  //    η = y_cara − y_B = s − r − s_libre; empuje: la uña en la toma (u = 0); retorno: u = salida que exige el pasador siguiente (chaflán), sin pasar de la leva.
  function camGeo(P) {
    if (driveMode(P) !== 1) return null;
    const c = simR(P).camG; if (!c) return null;
    return { perfil: c.prof.map(([eta, u]) => ({ eta, u })), perfil_y: c.perfil_y, holgura_toma: c.c, recorrido: c.travel, eta0: c.eta0, eta1: c.eta1, fin_rampa: c.etaEnd, tope_rampa: Math.min(c.etaR1, c.etaAp), salida_bolsillo: c.etaX1, entrada_toma: c.etaE0,
      alpha_deg: c.alpha, x_canto_toma: c.xE0, x_perno_toma: c.xFp0, riel: { t: P.cam_t, ancho: P.cam_w, largo: c.Lpl, y_soportes: [-c.Lsp / 2, c.Lsp / 2], z_inf: c.zPb }, sincronia: c.sync, margen: c.m };
  }
  function camAt(P, s, fase) {
    if (driveMode(P) !== 1) return null;
    const c = simR(P).camG; if (!c) return null;
    const g = guidedAt(P, s, fase), eta = g.eta, uc = c.uCam(eta);
    return Object.assign(g, { u_leva: uc, x_seguidor: c.xFp0 + g.u, holgura_leva: c.clr(eta, uc), enRampa: fase === "retorno" && eta >= c.etaEnd && eta <= Math.min(c.etaR1, c.etaAp),
      alertas: { sincronia: fase === "retorno" && eta <= Math.min(c.etaR1, c.etaAp) && c.clr(eta, uc) < c.m, choque: g.uNec > uc + 1e-9 } });
  }
  // 5. Modo guiado (con o sin leva): cara de empuje y_cara = y_rp0 + s + l_p − d/2, ángulo del pasador tomado, salida radial de la uña en el retorno (chaflán, holgura 0)
  //    y fuerzas del caso pedido (por defecto el nominal, «nom»).
  function guidedAt(P, s, fase, caseId) {
    if (driveMode(P) !== 1) return null;
    const R = simR(P), g = R.K, ch = chamferGeo(P), r = P.d_pin / 2, dyc = Math.min(ch.dy, P.dog_b), sc = Math.max(0, Math.min(s, g.s_req));
    const yFace = g.y_rp0 + sc + P.l_p - r, eta = yFace - g.y_pin0;
    const clr = (e, u) => { const Xt = -P.c_tip + u, Yb = e - P.dog_b; return polyDist([[Xt, e], [Xt, Yb + dyc], [Xt + ch.dx, Yb], [Xt + 3000, Yb], [Xt + 3000, e]], 0, 0) - r; };
    let th = -g.pitch / 2, uNec = 0, dr = null;
    if (fase !== "retorno") { if (sc > P.s_free) th = Math.asin(Math.max(-1, Math.min(1, (yFace + r) / P.R_pin))); if (sc >= P.s_free) dr = driveAtSim(P, th, caseId || "nom"); }
    else {
      th = g.pitch / 2;
      if (clr(eta, 0) < 0) { let lo = 0, hi = g.travel + 60; for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (clr(eta, mid) >= 0) hi = mid; else lo = mid; } uNec = hi; }
    }
    const cg = R.camG, u = fase === "retorno" ? (cg ? Math.min(uNec, cg.uCam(eta)) : Math.min(uNec, g.travel)) : 0;
    return { s: sc, y_rp: g.y_rp0 + sc, y_cara: yFace, y_seguidor: yFace - P.dog_b / 2, eta, th, u, uNec, x_punta: g.tipX + u, holgura: clr(eta, u),
      F: dr ? dr.F : 0, Fp: dr ? dr.Fp : 0, H: dr ? dr.H : 0, arm: dr ? dr.arm : null, caso: dr ? dr.caso : null };
  }

  /* ---------------- Geometría de fabricación del accionamiento (planos): sistema de la tornamesa, O en el centro, z desde el piso ---------------- */
  // Modo guiado: riel-leva, pórticos, prolongación de la bancada, seguidor y ranura de la tapa, para las 4 posiciones de cilindro
  // (lado sx = ±1 en x = sx·x_g, sentido de empuje dy = ±1; antihorario = (1, 1) y (−1, −1), horario = (1, −1) y (−1, 1)).
  function camGuidedFab(P, R, c) {
    const g = guideGeo(P), por = c.portico, yOf = (e) => g.y_pin0 + e - P.dog_b / 2, prof = c.prof.map(([e, u]) => [yOf(e), u]);
    const yS = [-c.Lsp / 2, c.Lsp / 2], half = c.Lpl / 2, xFlag = por.xL - por.capW / 2;
    const uAt = (y) => { for (let i = 1; i < prof.length; i++) if (y <= prof[i][0]) { const [y0, u0] = prof[i - 1], [y1, u1] = prof[i]; return y < y0 ? c.c : u0 + (u1 - u0) * (y - y0) / (y1 - y0); } return c.c; };
    const inFlag = (y) => yS.some((ys) => Math.abs(y - ys) <= P.cam_ls / 2 + 1e-9);
    const ys = [-half, half, ...prof.map((q) => q[0]), ...yS.flatMap((v) => [v - P.cam_ls / 2, v + P.cam_ls / 2])].filter((y) => y >= -half - 1e-9 && y <= half + 1e-9).sort((a, b) => a - b);
    const inner = []; ys.forEach((y) => { const x = inFlag(y) ? xFlag : c.xE0 + (uAt(y) - c.c); if (!inner.length || Math.abs(inner[inner.length - 1][0] - x) > 1e-9 || Math.abs(inner[inner.length - 1][1] - y) > 1e-9) inner.push([x, y]); });
    const riel = inner.concat([[c.xPo, half], [c.xPo, -half]]);
    const legs = yS.flatMap((y0) => [por.xL, por.xR].map((xc) => ({ x: [xc - por.px / 2, xc + por.px / 2], y: [y0 - P.cam_ls / 2, y0 + P.cam_ls / 2], z: [P.t_base + P.t_bed, c.zPb - por.tCap] })));
    const caps = yS.flatMap((y0) => [por.xL, por.xR].map((xc) => ({ x: [xc - por.capW / 2, xc + por.capW / 2], y: [y0 - P.cam_ls / 2, y0 + P.cam_ls / 2], z: [c.zPb - por.tCap, c.zPb] })));
    const nb2 = Math.max(1, Math.round(P.cam_nb / 2)), bolts = yS.flatMap((y0) => [por.xL, por.xR].flatMap((xc) => Array.from({ length: nb2 }, (_, k) => [xc, y0 - P.cam_ls / 2 + J34M(P.cam_db) + (nb2 > 1 ? k * (P.cam_ls - 2 * J34M(P.cam_db)) / (nb2 - 1) : (P.cam_ls / 2 - J34M(P.cam_db)))])));
    const ext = [-1, 1].map((sg) => ({ x: [xFlag + (por.capW - por.px) / 2, por.xR + por.px / 2], y: sg > 0 ? [g.Y_bed, g.Y_bed + P.cam_ls] : [-g.Y_bed - P.cam_ls, -g.Y_bed], z: [P.t_base, P.t_base + P.t_bed] }));
    const yFol = P.l_p - P.d_pin / 2 - P.dog_b / 2;    // seguidor respecto del pasador del vástago (y)
    const fam = c.fam, mat = fam.f === 1 ? "42CrMo4+QT (EN 10083-3), canto templado por inducción ≥ 55 HRC; pieza solo empernada (no se suelda)" : fam.nombre + " (zapata deslizante; no cumple en el modo guiado)";
    const fit = { ranura: P.cam_dp + " H9 (+0/+" + nfx(isoIT(P.cam_dp, 9), 3) + ")", perno: "Ø" + P.cam_dp + " f8 (−" + nfx(-isoF(P.cam_dp), 3) + "/−" + nfx(isoIT(P.cam_dp, 8) - isoF(P.cam_dp), 3) + ")", juego: [-isoF(P.cam_dp), isoIT(P.cam_dp, 9) - isoF(P.cam_dp) + isoIT(P.cam_dp, 8)] };
    const T = (sx, dy) => (q) => [sx * q[0], dy * q[1]], conf = { "1_antihorario": [1, 1], "2_antihorario": [-1, -1], "1_horario": [1, -1], "2_horario": [-1, 1] };
    return {
      sistema: "planta x, y (mm) con O en el centro de la mesa; z desde la cara inferior de la base (piso); local = lado +x, empuje +y (cilindro 1, antihorario)",
      riel: { contorno_local: riel, t: P.cam_t, z: [c.zPb, c.zPb + P.cam_t], material: mat, Fy: P.Fy_cam, nota: "canto interior = leva (toma, bolsillo y rampa); aletas hacia adentro en la zona de los pórticos (el seguidor no llega); se voltea para el otro sentido de giro (simetría en y)" },
      porticos: { patas_local: legs, tapas_local: caps, pernos_local: bolts, d_perno: P.cam_db, agujero: P.cam_db + 2, filete_pata_asiento: P.cam_wf, filete_pata_tapa: c.weldPT.wPT, t_tapa: por.tCap,
        pernos: { norma: "ISO 4762 M" + P.cam_db + " × " + por.Lb + " – 10.9", rosca: { pieza: "tapa de la pata", ciega: true, prof_taladro: por.tCap - 3, remanente: 3, rosca_util: por.huCap, engrane: por.leCap, paso: por.pB, d_broca: P.cam_db - por.pB } },
        material: "S355J2 (EN 10025-2), patas y tapas soldadas (metal base precalificado, AWS D1.1/D1.1M:2020 Tabla 5.3); el riel-leva de 42CrMo4+QT se emperna, no se suelda" },
      prolongacion_soldadura: { filete: P.w_bed_f, tipo: "filete perimetral a la base" },
      prolongacion_bancada_local: ext,
      seguidor: { rodillo: { d: P.cam_df, b: P.cam_bf, z: [c.zF - P.cam_bf / 2, c.zF + P.cam_bf / 2], material: "100Cr6 (ISO 683-17), templado total 58–64 HRC", cojinete: "dato del proveedor del seguidor (hipótesis: μ equivalente ≤ " + nfx(P.mu_roll, 3) + ")" },
        perno: { d: P.cam_dp, ajuste: fit.perno, largo: c.lPerno, empotrado_en_una: 30, z_cara_sup_una: c.zU, z: [c.zU - 30, c.zU - 30 + c.lPerno], fijacion_en_una: "sin soldadura (34CrNiMo6+QT); ajuste prensado en la uña (hipótesis)" },
        retencion: { tipo: "arandela de tope con tornillo axial en el extremo del perno", t_arandela: c.hRet, d_arandela: P.cam_df - 10, z: [c.zF + P.cam_bf / 2, c.zRetTop], tornillo: "ISO 10642 M8 (hipótesis)" },
        x_eje_toma: c.xFp0, y_respecto_pasador_vastago: yFol, recorrido_x: c.travel },
      ranura_tapa_patin: { ancho: P.cam_dp, ajuste: fit.ranura, juego: fit.juego, x: [c.xFp0 - P.cam_dp / 2, c.xFp0 + c.travel + P.cam_dp / 2], y_respecto_pasador_vastago: yFol, t_tapa: P.t_pk, nota: "ranura pasante en la tapa del alojamiento de la uña: guía del perno en y; ajuste deslizante " + fit.ranura + " / " + fit.perno + " (ISO 286-2)" },
      instancias: Object.fromEntries(Object.entries(conf).map(([k, [sx, dy]]) => { const f = T(sx, dy); return [k, { lado: sx, sentido: dy, riel: riel.map(f), pernos: bolts.map(f), patas: legs.map((l) => ({ x: l.x.map((v) => sx * v).sort((a, b) => a - b), y: l.y.map((v) => dy * v).sort((a, b) => a - b), z: l.z })) }]; })),
    };
  }
  // Modo pivotado: cajón y tapas del ojal E, pasador E, bloque-uña acodado, pasador Q, 4 placas-leva (contorno con bolsillo y rampa, pernos, material)
  function pivotFab(P, R) {
    const K = R.K, sg = R.sup, bk = R.blk, CP = R.camP, G = pivotGeo(P), fam = CP.fam;
    const b = P.pv_box, E = K.E, sx = sg.sx, sy = sg.sy, deg = (a) => ((a / D2R) % 360 + 360) % 360, f1 = sg.toReal(1), f2 = sg.toReal(2);
    const box = (Ec, s1, s2) => ({ centro: Ec, esquinas: [[Ec[0] - b / 2, Ec[1] - b / 2], [Ec[0] + b / 2, Ec[1] - b / 2], [Ec[0] + b / 2, Ec[1] + b / 2], [Ec[0] - b / 2, Ec[1] + b / 2]],
      paredes_completas: [s1 > 0 ? "x+" : "x−", s2 > 0 ? "y+" : "y−"], paredes_con_ventana: [s1 > 0 ? "x−" : "x+", s2 > 0 ? "y−" : "y+"] });
    const INS = cornerInsertOf(P, R), zSeat = INS && INS.ok ? INS.t : P.t_base, dzS = zSeat - P.t_base, zOf = (q) => (q.rect ? [zSeat, q.z[1]] : q.z), mOf = (q) => (q.rect ? q.masa * (q.z[1] - zSeat) / (q.z[1] - P.t_base) : q.masa);   // paredes y muñones soldados sobre el inserto
    const piezasOf = (f) => sg.piezas.map((q) => ({ id: q.id, nombre: q.nombre, t: q.t, z: zOf(q), poligono: q.poly.map(f), agujero_E: q.agujero || null, masa: mOf(q) }));
    // sector real del barrido (ambos sentidos) y verificación de cada junta (a calado, en todos los estados)
    const sw = sg.sweep.real, secR = sw ? [sw.lo, sw.hi, sw.loH, sw.hiH].map(deg) : [0, 0, 0, 0], SL = pivSupLoads(P, sg, R.Fstall * 1e3), Fw = P.FEXX * 0.60 / (1.20 * P.Nd), Fy = P.Fy, Nd = P.Nd;
    const fuJ = { "J-E1": Math.max(SL.sig / (Fy / Nd), SL.tau / (Fy / (Nd * Math.sqrt(3)))), "J-E2": Math.max(SL.sig / (Fy / Nd), SL.tau / (Fy / (Nd * Math.sqrt(3)))), "J-E6": Math.max(SL.sig / (Fy / Nd), SL.tau / (Fy / (Nd * Math.sqrt(3)))),
      "J-E3": SL.flow / (Fy / (Nd * Math.sqrt(3))), "J-E4": SL.flow / (Fy / (Nd * Math.sqrt(3))), "J-E5": SL.flow / (Fy / (Nd * Math.sqrt(3))), "J-E7": SL.pjp / Fw, "J-E8": SL.pjp / Fw };
    const juntas = sg.juntas.map((j) => Object.assign({}, j, { verificacion: { fu: fuJ[j.id], norma: /PJP/.test(j.tipo) ? "AISC 360-22 §J2.1a, §J2.4 (Tabla J2.5, PJP en corte 0,60FEXX/(1,20Nd)), Tabla J2.3; AWS D1.1/D1.1M:2020 Figura 5.2 (TC-P4), Tabla 7.7 (filete de refuerzo)" : "AISC 360-22 §J2.4, Tabla J2.5 (CJP = metal base); AWS D1.1/D1.1M:2020 Figura 5.1 (TC-U4b), Tabla 7.7 (filete de refuerzo); ASME BTH-1 §3-2" } }));
    // interrupción del marco perimetral frente a las paredes traseras (cilindro 1 y 2), sobre los bordes de la base
    const Bh = P.B / 2, rimCut = (cs) => { const Ec = cs === 1 ? E : [-E[0], -E[1]], ex = Math.sign(Ec[0]) || 1, ey = Math.sign(Ec[1]) || -1, h = sg.marco.alcance;
      const Lx = Math.max(Bh - (Math.abs(Ec[1]) - h), INS && INS.ok ? INS.legX + 50 : 0), Ly = Math.max(Bh - (Math.abs(Ec[0]) - h), INS && INS.ok ? INS.legY + 50 : 0);   // frente al soporte y a lo largo de los catetos del inserto
      return [{ borde: (ex > 0 ? "x = +" : "x = −") + nfx(Bh, 0), desde: [ex * Bh, ey * Bh], hasta: [ex * Bh, ey * (Bh - Lx)] }, { borde: (ey > 0 ? "y = +" : "y = −") + nfx(Bh, 0), desde: [ex * (Bh - Ly), ey * Bh], hasta: [ex * Bh, ey * Bh] }]; };
    const pl = fam.f === 1 ? "42CrMo4+QT (EN 10083-3), canto guía templado por inducción 52–56 HRC con capa efectiva ≥ 4 mm (EN 10328), revenido de alivio 180 °C" : "42CrMo4+QT (EN 10083-3) de respaldo con revestimiento de " + fam.corto + " de " + P.pv_tlin + " mm en el canto";
    return {
      sistema: "planta x, y (mm) con O en el centro de la mesa; z desde la cara inferior de la base (piso)",
      soporte_E: { cilindro1: Object.assign(box(E, sx, sy), { piezas: piezasOf(f1) }), cilindro2: Object.assign(box([-E[0], -E[1]], -sx, -sy), { piezas: piezasOf(f2) }), lado: b, t_pared: P.pv_tbox, alto_paredes: sg.zW - zSeat, z_paredes: [zSeat, sg.zW], asiento: INS && INS.ok ? "sobre el inserto de esquina (z = " + zSeat + ")" : "sobre la base",
        tipo: "cajón abierto hacia la mesa: paredes traseras en L (X e Y) y muñones delanteros; las paredes delanteras se eliminan en todo el barrido del cuerpo del cilindro (ambos sentidos); tapas inferior y superior entre las paredes, recortadas en nariz",
        marco_local: { origen: "E", ejes: "X, Y paralelos a los bordes de la base; esquina de la base hacia (+X, −Y)", real: "x = E_x + s_x·X, y = E_y − s_y·Y (cilindro 1); cilindro 2 = rotación de 180°", s_x: sx, s_y: sy, b: sg.b, b_i: sg.bi },
        piezas: sg.piezas.map((q) => ({ id: q.id, nombre: q.nombre, t: q.t, z: zOf(q), poligono_local: q.poly, agujero_E: q.agujero || null, masa: mOf(q), material: "S355J2 (EN 10025-2), Fy " + P.Fy + " MPa" })),
        tapas: { t: P.pv_tl, lado: 2 * sg.bi, poligono_local: sg.tapa, area_neta: sg.Acap, z_inf: [sg.zL - P.pv_tl / 2, sg.zL + P.pv_tl / 2], z_sup: [sg.zU - P.pv_tl / 2, sg.zU + P.pv_tl / 2], rebaje_sup: P.pv_rebt, agujero_E: P.pv_dE, ajuste: "H9/f8 (agujero mecanizado en línea en ambas tapas después de soldar)", nota: "las tapas van ENTRE las paredes (lado = 2·b_i); el polígono es la nariz recortada (holgura de diseño " + nfx(sg.c, 1) + " mm al cuerpo del cilindro)" },
        ventana: { tipo: "abierto (sin pared delantera en el barrido)", sector_deg: [secR[0], secR[1], secR[2], secR[3]], z: [P.t_base, sg.zW], nota: "sector del eje del cilindro respecto de E: antihorario [ψ_mín, ψ_máx] y horario (reflejo respecto de la diagonal); el cuerpo pasa sobre la base sin ninguna pieza del soporte delante" },
        barrido: { holgura_minima: sg.clr.d, estado: { sentido: sg.clr.sentido, fase: sg.clr.fase }, holgura_diseno: sg.c, holgura_exigida: 5, n_estados: sg.sweep.estados.length + sg.sweep.horario.length },
        juntas, secuencia: sg.secuencia,
        marco_interrupcion: { cilindro1: rimCut(1), cilindro2: rimCut(2), holgura_acceso: sg.marco.holgura, nota: "el marco perimetral se corta frente a las paredes traseras (acceso exterior al resanado y respaldo de las CJP) y a lo largo de los catetos del inserto de esquina hasta 50 mm más allá de su extremo; extremos del marco libres, con chaflán" },
        soldadura: { filete: P.pv_wbox, paredes_base: "CJP TC-U4b (bisel interior, resanado y respaldo exterior) + filete de refuerzo interior z" + P.pv_wbox, pared_pared: "CJP TC-U4b + filete de refuerzo interior z" + P.pv_wbox, tapas_paredes: "PJP TC-P4 S = " + sg.S_pjp + " (E = " + sg.E_pjp + ") desde arriba + filete de refuerzo z" + P.pv_wbox + "; sin soldadura por debajo" },
        material: "S355J2 (Fy " + P.Fy + ")", masa: sg.m - (INS && INS.ok ? RHO * sg.walls.reduce((a, q) => a + Math.abs(PG.area(q.poly)), 0) * dzS : 0),
        inserto: insertExport(P, R),
        plancha_base: (() => { const BP = pivBasePlate(P, R), Fa = INS_FB * P.Fy / P.Nd, cs = (nm, c, st) => ({ caso: nm, F_kN: c.F / 1e3, h: c.h, M_kNm: c.M / 1e6, a: c.a, w: c.w, b: c.b, s_H: c.sH, retencion_detras_del_talon: c.ret, M_corte_kNm: c.Mc / 1e6, sigma: c.sig, cap: Fa, fu: c.sig / Fa, tau: c.tau, fu_corte: c.tau / (Fa / Math.sqrt(3)), sentido: c.sentido, psi_deg: ((c.psi / D2R) % 360 + 360) % 360, norma: "ASME BTH-1-2020 §3-2.3.4 (flexión, F_b = 1,25·Fy/Nd), §3-2.3.6 (corte)", estado: st });
          return { t: P.t_base, material: "S355J2 (Fy " + P.Fy + " MPa)", anclaje: "no definido en el proyecto (base apoyada en losa o mats): contacto unilateral, sin retención propia", modelo: "soporte rígido; losa rígida solo a compresión; retención del talón solo por la mesa (R ≤ D/2) a través de la plancha; franja M_corte = M·(1 − a/s_H) (M si s_H ≤ a), b = w + a; coordenadas del marco local del soporte",
            casos: [cs("empuje a calado", BP.empuje, BP.empuje.sig > Fa ? "no cumple sin anclaje" : "cumple"), cs("retorno (atasco)", BP.retorno, BP.retorno.sig > Fa ? "no cumple sin anclaje" : "cumple")],
            mesa_vacia: { W_mesa_kN: BP.mesaVacia.W / 1e3, T_req_kN: BP.mesaVacia.Treq / 1e3, cumple: BP.mesaVacia.ok, nota: "calado con la mesa vacía (atasco): retención disponible = peso propio de la parte que gira (mesa + disco rotatorio + medio pivote + bloques-uña); pedida = n_cil·M/s_H con el brazo más largo" },
            revision_base_completa: (() => { const M = BP.empuje.M / 1e6, V = M / (P.B / 1e3), mxy = V / 2, tau = 6 * mxy * 1e3 / (P.t_base * P.t_base);
              return { estudio: "docs/qa/plancha_base_soporte_E.md",
                modelo: "base completa con los dos soportes: F₂ = −F₁ y M₂ = −M₁ (cilindros en ojales diagonalmente opuestos, en paralelo); la base no vuelca como cuerpo libre y no necesita retención global, pero el par de un soporte llega al otro (en diagonal, rodeando la mesa) solo por torsión de la base: fuerzas de esquina ≈ M/B (las esquinas libres suben) y momento torsor m_xy ≈ M/(2·B) en toda la plancha",
                M_kNm: M, V_esquina_kN: V, m_xy_kNm_m: mxy, tau_torsion_MPa: tau, fu_torsion_cota_inferior: tau / (P.Fy / (P.Nd * Math.sqrt(3))),
                nota_torsion: "τ = 6·m_xy/t² ≤ Fy/(Nd·√3) (ASME BTH-1 §3-2.3.6) para la placa libre en torsión pura: cota inferior; con el contacto unilateral y el peso propio la FEA de la base completa da más (la base flota sobre los pies)",
                mesa_vacia: "con la mesa vacía y los dos cilindros a calado la plancha de " + P.t_base + " mm no tiene rigidez a torsión: en la FEA de la base completa con contacto unilateral queda apoyada solo en los dos pies y el resto se levanta (del orden de 0,3 m en el cálculo lineal); el peso propio de la base y de la mesa equivale a pocos kN en las esquinas libres",
                un_cilindro: "posible: los cilindros se alimentan en paralelo con un alivio común y sin divisor de caudal; si uno no tiene reacción (bloque-uña sin tomar o émbolo a fin de carrera) el otro llega solo a la presión de alivio. Con la mesa cargada equivale al modelo de un soporte (retención en la huella de la mesa); con la mesa vacía no hay equilibrio sin anclaje",
                opciones: [
                  { id: "A", nombre: "anclaje a la losa", resultado: "cierra todos los casos con fuerzas por perno del estudio; pide datos de la losa que el proyecto no tiene" },
                  { id: "B", nombre: "base rígida (plancha gruesa o emparrillado)", resultado: "por defecto queda en el límite recién con ≈ 64 mm en toda la base (FU ≈ 1,0 junto al soporte con la mesa vacía, ≈ +2,4 t); con la interfaz B no alcanza" },
                  { id: "C", nombre: "marco perimetral continuo (tipo KIET)", resultado: "abierto: no da rigidez a torsión y no cumple con la mesa vacía en ningún tamaño probado; en cajón cerrado de 70 mm de ancho cumple por defecto con la mesa vacía desde ≈ 730 kg, pero no con la mesa cargada ni con la interfaz B" },
                  { id: "D", nombre: "nervios radiales o diagonales", resultado: "no dan rigidez a torsión: no cumplen con la mesa vacía; con la mesa cargada no alcanzan con secciones que quepan" },
                ],
                conclusion: "NO cumple sin anclaje ni base rígida; ninguna opción C o D cumple con < 600 kg sin interferencias: no se implementó ninguna (decisión del mandante: anclaje con datos de la losa, base rígida o restricción del calado con la mesa vacía)" }; })(),
            caso_termico: "no aplica (F de la presión de alivio y de retorno; la base queda a la sombra)", estado: "PENDIENTE: decisión de anclaje a la losa (o rediseño de la base) por el mandante; datos de la losa no definidos (f'c, espesor, armadura, bordes)", referencia: "docs/normas/registro.md, «Plancha base bajo el soporte del ojal E (10-11-2026)»" }; })() },
      pasador_E: { d: P.pv_dE, largo: sg.forkH + 20, z: [sg.zL - P.pv_tl / 2 - 10, sg.zU + P.pv_tl / 2 + 10], material: "Fy " + P.Fy_pp + " MPa", ajuste: "H9/f8" },
      bloque_una: { contorno_local: G.bloque.local, h: P.pv_hu, z: [bk.zBot, bk.zBot + P.pv_hu], agujero_Q: P.pv_dq, horquilla: { ranura_ojal: P.b_eye + 2 * P.g_ch, t_mejilla: bk.tq, R_cubo: bk.eb }, cuerpo: { b: P.pv_bu, e_acodado: P.pv_ecr }, cara: { b: P.pv_bf, l: P.pv_lf, radio_planta: bk.Rf || null, flecha_arista: bk.sag, contacto_desde_eje: bk.ec, nota: bk.Rf > 0 ? "cara cilíndrica convexa en planta (generatriz vertical), vértice en s = L_qp − r; aristas con chaflán 3 × 45°" : "cara plana", templada: "≥ 55 HRC (Fy_sup " + P.Fy_surf + ")" }, material: "34CrNiMo6+QT (Fy " + P.Fy_dog + ")",
        nota: "marco local: origen en Q, x hacia el pasador tomado, y = t (hacia O); el cuerpo se desplaza e_acodado hacia −y" },
      pasador_Q: { d: P.pv_dq, largo: bk.lPin, z: [P.t_base + 2, bk.zBot + P.pv_hu], extremo_inferior: "seguidor de la placa-leva (" + (fam.tipo === "hertz" ? "templado" : "con zapata de " + CP.lpad + " mm") + ")", voladizo_bajo_horquilla: bk.lq, material: "Fy " + P.Fy_pp + " MPa" },
      placas_leva: { instancias: G.placas, t: P.pv_tcam, z: [P.t_base, P.t_base + P.pv_tcam], material: pl, familia: fam.f, revestimiento: fam.f > 1 ? { material: fam.nombre, t: P.pv_tlin } : null, zapata: fam.tipo === "pad" ? { largo: CP.lpad, alto: P.pv_tcam } : null,
        tratamiento: fam.f === 1 ? { canto: "temple por inducción del canto guía (tramos de contacto: flanco, hombro, cresta, bajada y empalme) 52–56 HRC, capa efectiva ≥ 4 mm (EN 10328, 550 HV); resto del contorno sin temple", rugosidad_canto: "Ra ≤ 1,6 µm (rectificado o fresado de acabado después del temple)", bordes: "aristas superior e inferior del canto con chaflán 1 × 45°" } : { canto: "revestimiento pegado y atornillado", rugosidad_canto: "según proveedor" },
        corte: "contorno por corte láser o agua con sobreespesor de 1 mm en el canto y fresado CNC final siguiendo los arcos (tolerancia de perfil ± 0,2 mm, ISO 1101); polilínea de exportación con flecha ≤ " + CP.guia.tol + " mm",
        tolerancia_polilinea: CP.guia.tol, marco: { largo: CP.guia.marco.largo, ancho: CP.guia.marco.ancho, nota: "placa rectangular con recorte en media luna hacia la mesa (concepto KIET); x' a lo largo de la cuerda del canto, y' hacia afuera" },
        pernos: { d: P.pv_db, n: Math.round(P.pv_nb), clase: "8.8", norma: "ISO 10642 M" + P.pv_db + " × " + Math.round(P.pv_tcam + P.t_base - 2) + " (cabeza avellanada a ras; roscado en la base de " + P.t_base + " mm, enganche ≥ 1,0·d)", avellanado: "90° Ø" + nfx(2 * P.pv_db - 1.84, 1) + " (ISO 10642, k ≈ 0,56·d)", agujero: P.pv_db + 1, par_apriete: "según VDI 2230 con μ 0,14 (8.8)" },
        pasadores_posicion: (() => { const dw = dowelGeo(P); return { d: P.pv_dd, n: 2, norma: "ISO 8734 Ø" + P.pv_dd + " m6 (templado)", designacion: dw.designacion, largo: dw.L, ajuste: "H7 escariado en placa y base, montados después de alinear la placa con plantilla al círculo de pasadores",
          enganche_base: dw.lb, enganche_placa: dw.lp, enganche_min: dw.lmin, alojamiento_base: { tipo: "ciego desde la cara superior", prof: dw.hb, remanente: dw.remB, fondo_libre: dw.fondo }, alojamiento_placa: { tipo: "ciego desde la cara inferior", prof: dw.hp, remanente: dw.remP, fondo_libre: dw.fondo },
          nota: "enganche ≥ 1,5·d en cada pieza; agujeros ciegos con salida de aire (taladro de Ø3 al costado o pasador con plano, hipótesis) para el montaje; para desmontar se levanta la placa (el pasador queda en la base)" }; })(),
        holgura_sincronia: (() => { const sp = CP.guia.syncPts, mk = CP.guia.marco, loc = (p) => [GV.dot(GV.sub(p, mk.origen), mk.xh), GV.dot(GV.sub(p, mk.origen), mk.yh)], deg = (a) => ((a / D2R) % 360 + 360) % 360, inst = {};
          [1, 2].forEach((cil) => ["antihorario", "horario"].forEach((sen) => { const f = pivTr(P, sen, cil), th = (sen === "horario" ? 2 * P.pv_phE * D2R - sp.th : sp.th) + (cil === 2 ? Math.PI : 0);
            inst[cil + "_" + sen] = { punto_bloque: f(sp.punto_bloque), punto_pasador: f(sp.punto_pasador), centro_pasador: f(sp.centro_pasador), Q: f(sp.Q), theta_deg: deg(th) }; }));
          return { nominal: sp.holgura, peor_caso: sp.holgura - CP.guia.dTol, tolerancias: CP.guia.dTol, margen_exigido: P.pv_msync, L: sp.L, s: sp.s, fase: "retorno (mesa detenida en θ_fin, Q contra el canto, bloque alineado con E–Q)", pasador: sp.pasador,
            marco_placa: { punto_bloque: loc(sp.punto_bloque), punto_pasador: loc(sp.punto_pasador), nota: "x' a lo largo de la cuerda del canto, y' hacia afuera (mismas coordenadas en las 4 placas: rotación y reflexión llevan su marco)" }, instancias: inst }; })(),
        ancho_labio: P.pv_wlip },
    };
  }
  /* ---------------- Datos de dibujo del accionamiento (export_design.js y planos_export.js) ---------------- */
  function designDrive(P, R) {
    const MODE = driveMode(P), D2R = Math.PI / 180;
// Tarea 1 · leva de reenganche del modo guiado (lado +x, sentido +y; el resto por simetría: x → −x, y → −y, y la pletina se voltea para el otro sentido)
  const levaGuiada = (() => {
  const c = R.camG; if (!c) return null;
  return { activa: true, familia: c.fam.f, familia_nombre: c.fam.nombre, automatico: c.fam.auto, mu_seguidor: c.muC, alpha_deg: c.alpha, holgura_toma: c.c, margen_sincronia: c.m, sincronia: c.sync, sincronia_entrada: c.syncIn,
    recorrido_bolsillo: c.uPk, u_nec_max: c.needMax, fraccion_empuje_retenida: c.cover, eta: { eta0: c.eta0, eta1: c.eta1, fin_rampa: c.etaEnd, tope_rampa: Math.min(c.etaR1, c.etaAp), salida_bolsillo: c.etaX1, entrada_toma: c.etaE0 },
    perfil: c.perfil_y, // y: posición del centro del seguidor (lado +x, empuje +y); x_canto: canto del riel en ese punto (nivel de toma = x_canto mínimo)
    z: { eje: c.zc0, sup_una: c.zU, ranura_tapa: c.zS, inf_riel: c.zPb, seguidor: c.zF, sup_mesa: c.zTop, sup_riel: c.zPb + P.cam_t },
    x: { perno_seguidor_toma: c.xFp0, canto_toma: c.xE0, borde_exterior: c.xPo, soporte_interior: c.xPo - P.cam_px, ancho_neto_bolsillo: c.wNet },
    riel: { t: P.cam_t, ancho: P.cam_w, largo: c.Lpl, luz_soportes: c.Lsp, y_soportes: [-c.Lsp / 2, c.Lsp / 2], Fy: P.Fy_cam },
    soportes: { tipo: "pórtico de dos patas soldadas a un asiento; el cuerpo del cilindro pasa bajo el pórtico trasero", largo_y: P.cam_ls, espesor_pata_x: P.cam_px, alto: c.hPed, x_patas: [c.portico.xL, c.portico.xR], ancho_tapa: c.portico.capW, filete_pata: P.cam_wf, n_pernos: P.cam_nb, d_perno: P.cam_db, prolongacion_bancada_por_extremo: P.cam_ls, ancho_prolongacion: c.portico.wExt },
    fabricacion: Object.assign(camGuidedFab(P, R, c), { inserto: insertExport(P, R) }),
    seguidor: { d_rodillo: P.cam_df, b_rodillo: P.cam_bf, d_perno: P.cam_dp, voladizo_perno: c.lFp },
    fuerzas_N: { F_ret: c.Fret, rampa: c.NR, rampa_x: c.NRx, toma: c.NT, diseno: c.Nd }, autobloqueo: { dem: c.lockDem, cap: c.lockCap, k_t: c.kt, k_p: c.kp }, masas: c.m };
})();
// Tarea 2 · modo pivotado tipo KIET: 2 ojales en diagonal, 4 placas-leva (una por cilindro y sentido). Base: cilindro 1 en φ_E, giro antihorario;
// cilindro 2 = rotación 180°; giro horario = reflexión respecto de la diagonal O–E.
  const pivotado = (() => {
  const K = R.K; if (MODE !== 2 || !K.ok) return null;
  const CP = R.camP, sg = R.sup, bk = R.blk, ph = P.pv_phE * D2R, ed = [Math.cos(ph), Math.sin(ph)];
  const rot = (q) => [-q[0], -q[1]], refl = (q) => { const d = q[0] * ed[0] + q[1] * ed[1]; return [2 * d * ed[0] - q[0], 2 * d * ed[1] - q[1]]; };
  const tr = { "1_antihorario": (q) => q, "2_antihorario": rot, "1_horario": refl, "2_horario": (q) => rot(refl(q)) };
  const pts = (f) => ({
    E: f(K.E), Q: R.stroke.map((q) => f(q.Q)), Q_colineal: K.pts.map((q) => f(q.Q)), P: K.pts.map((q) => f(q.P)),
    leva_centro_seguidor: CP.guia.polilinea_recorrido.map(f), leva_canto: CP.guia.polilinea_canto.map(f), leva_borde_exterior: CP.guia.polilinea_contorno.map(f), leva_pernos: CP.bolts.map(f), leva_pasadores_posicion: CP.dowels.map(f) });
  return {
    E: K.E, R_E: K.RE, phi_E: P.pv_phE, L_qp: K.Lqp, automatico: K.auto, sugerencia: K.sugerencia || suggestE(P), theta_ini_deg: K.ths / D2R, theta_fin_deg: K.the / D2R,
    brazo_min: K.aMin, brazo_max: K.aMax, brazo_ef_min: K.aEffMin, carrera_req: CP.sReqG, carrera_req_colineal: K.sReq, Q_min: K.QrMin, holgura_pasador_siguiente: K.clrB, holgura_cuerpo_mesa: K.body,
    cinematica: R.stroke.map((q) => ({ th: q.th / D2R, a: q.arm, a_ef: q.armEff, L: q.L, s: q.s, psi_deg: q.psi / D2R, f_tang: q.ft, f_rad: q.fr, F_cil: q.F, F_n: q.Fp, F_leva: q.Fcam, p: q.F * 1e3 / R.A * 10,
      w: q.w, separacion_colineal: q.gap, phi_presion_deg: q.phi_guia, a_colineal: q.a_colineal, a_ef_colineal: q.a_ef_colineal, F_cil_colineal: q.F_colineal })),
    bloque_una: { b_cuerpo: P.pv_bu, e_acodado: P.pv_ecr, b_cara: P.pv_bf, l_cara: P.pv_lf, h: P.pv_hu, d_Q: P.pv_dq, R_cubo: bk.eb, s_cara_ini: bk.s1, s_cara: bk.s2, t_horquilla: bk.tq, z_inf: bk.zBot, l_pasador_Q: bk.lPin, voladizo_leva: bk.lq, masa: bk.m, R_cara: bk.Rf, contacto_cara: bk.ec, giro_equilibrio_deg: bk.dBlk / D2R },
    soporte_E: { lado_cajon: P.pv_box, t_pared: P.pv_tbox, filete: P.pv_wbox, t_tapas: P.pv_tl, d_E: P.pv_dE, alto: sg.hW - ((cornerInsertOf(P, R) || {}).ok ? cornerInsertOf(P, R).delta : 0), z_tapa_sup: sg.zU, z_tapa_inf: sg.zL, rebaje_tapa_sup: P.pv_rebt, holgura_cuerpo: sg.clr.d, masa: (() => { const I = cornerInsertOf(P, R); return sg.m - (I && I.ok ? RHO * sg.walls.reduce((q, w) => q + Math.abs(PG.area(w.poly)), 0) * I.delta : 0); })(), nota: "cajón centrado en E, abierto hacia la mesa en todo el barrido del cilindro: paredes traseras en L, muñones y tapas recortadas en nariz (geometría constructiva en fabricacion.soporte_E)" },
    placa_leva: { familia: CP.fam.f, familia_nombre: CP.fam.nombre, automatico: CP.fam.auto, mu: CP.fam.mu, t: P.pv_tcam, ancho_labio: P.pv_wlip, t_revestimiento: CP.fam.f > 1 ? P.pv_tlin : 0, l_zapata: CP.lpad, n_pernos: Math.round(P.pv_nb), d_perno: P.pv_db, Fy: P.Fy_camP,
      holgura: CP.c, margen_sincronia: CP.m, margen_diseno: CP.md, tolerancias_mm: CP.guia.dTol, sincronia: CP.sync, sincronia_peor: CP.guia.syncWorst, alpha_deg: CP.alpha, alpha_req_deg: CP.guia.flanco.phi_req_deg, bolsillo_w: CP.wPk, fraccion_empuje_retenida: CP.cover,
      L_pie_flanco: CP.Lend, L_tope_flanco: CP.Lr1, L_cresta: CP.LX1, L_tope_rampa: CP.guia.primer_contacto.L, primer_contacto: CP.guia.primer_contacto, perfil: CP.need,
      segmentos_centro: CP.guia.tramos, segmentos_canto: CP.guia.canto, segmentos_contorno: CP.guia.contorno, radio_min_canto: CP.guia.rCanto, radio_min_centro_convexo: CP.guia.rCentro.convexo, g1_max_rad: CP.guia.g1Max, salto_curvatura_max: CP.guia.dKappa, tolerancia_polilinea: CP.guia.tol,
      hertz: CP.hz, relacion_F_guiado_colineal_max: CP.ratioMax, eleccion_flanco: CP.guia.eleccion,
      retorno: CP.guia.ret.filter((q, i) => i % 4 === 0 || i === CP.guia.ret.length - 1).map((q) => ({ L: q.L, w: q.w, W: q.W, guia: q.guia, holgura: q.hol, holgura_canto: q.holW, phi_deg: q.phi, Q: CP.Qof(q.L, q.w).Q })),
      fuerzas_N: { rampa_atasco: CP.NR, transversal_calado: CP.Tst, transversal_diseno: CP.Tdis, diseno: CP.Ncam }, v_seguidor_m_s: CP.vQ, area: CP.area, largo_canto: CP.Lb },
    posiciones: Object.fromEntries(Object.entries(tr).map(([k, f]) => [k, pts(f)])),
    fabricacion: pivotFab(P, R),
    nota: "coordenadas en planta (mm) con O en el centro; Q: 61 posiciones del empuje con Q apoyado en el canto (Q_colineal: cinemática E–Q–P alineada de referencia); P: pasador tomado; leva_centro_seguidor: recorrido del centro del extremo inferior de Q (L0 … L_fin); leva_canto: canto guía (polilínea con flecha ≤ 0,1 mm de los segmentos de placa_leva.segmentos_canto); leva_borde_exterior: contorno cerrado de la placa; leva_pernos y leva_pasadores_posicion: ejes" };
})();
  const masas_desc = MODE === 1 ? { brackets: "ménsulas del ojal trasero (n_br), con su inserto de esquina en la base", dogs: "uñas", shoes: "patines", beds: "bancadas", cam: "leva de reenganche: riel, soportes, prolongación de la bancada y seguidor (Tarea 1)" }
  : { brackets: "soportes del ojal E (cajón, tapas y pasador vertical; uno por cilindro), con su inserto de esquina en la base", dogs: "bloques-uña con pasador Q (uno por cilindro)", shoes: "— (no hay patín)", beds: "— (no hay bancada)", cam: "4 placas-guía curvas (concepto KIET) con revestimiento y zapatas del seguidor" };
    const tw = R.ifc && R.ifc.tornillos, tornillos_interfaz = tw ? { aplica: "AF2: opción A pegada (fix_mode = 2), disco de la mesa → " + tw.pieza, designacion: tw.designacion, n: tw.n, d: tw.d, r: tw.r, PCD: 2 * tw.r, angulos_deg: tw.ang, posiciones: tw.pos,
      avellanado: tw.avellanado, rosca_en_mesa: tw.rosca, pieza_roscada: tw.pieza, t_disco: tw.t, t_plancha_mesa: tw.tb, t_pieza_roscada: tw.tb, V_por_tornillo_kN: tw.V / 1e3,
      pasadores: { n: P.N_pin, d: P.d_pin, R: P.R_pin, angulos_deg: Array.from({ length: P.N_pin }, (_, k) => (k + 0.5) * 360 / P.N_pin), distancia_min_tornillo: tw.cbp, ligamento_libre: tw.ligPin },
      nota: "ángulos medidos desde +x: tornillos en las bisectrices entre pasadores (k·360°/N_pin), salvo las que caen sobre una ranura radial de engrase; avellanado 90° (ISO 10642) en la cara de deslizamiento del disco de la mesa; rosca ciega en el anillo inferior de pasadores (remanente 3 mm), sin asomar a la luz entre anillos" } : null;
    // modo guiado: plancha base bajo la ménsula del ojal trasero (docs/qa/plancha_base_modo_guiado.md)
    const guiado = MODE === 1 && R.K.ok ? (() => { const BP = guidedBasePlate(P, R), Fa = INS_FB * P.Fy / P.Nd, tq = BP.torsion;
      const cs = (nm, c, st) => ({ caso: nm, F_kN: c.F / 1e3, h: c.h, M_kNm: c.M / 1e6, a: c.a, w: c.w, b: c.b, s_H: c.sH, retencion_detras_del_talon: c.ret, M_corte_kNm: c.Mc / 1e6, sigma: c.sig, cap: Fa, fu: c.sig / Fa, tau: c.tau, fu_corte: c.tau / (Fa / Math.sqrt(3)), norma: "ASME BTH-1-2020 §3-2.3.4 (flexión, F_b = 1,25·Fy/Nd), §3-2.3.6 (corte)", estado: st });
      return { plancha_base: { estudio: "docs/qa/plancha_base_modo_guiado.md", t: P.t_base, material: "S355J2 (Fy " + P.Fy + " MPa)", ojal: BP.ojal, h: BP.h, huella_mejillas_local: BP.walls,
        anclaje: "no definido en el proyecto (base apoyada en losa o mats): contacto unilateral, sin retención propia",
        modelo: "ménsula rígida (dos mejillas soldadas a la plancha) con el ojal en (x_g; y_ojal); F a la altura del eje h sobre la plancha, M = F·h alrededor de x. Con los dos cilindros (lados ±x, empujes ±y) M₂ = −M₁ entre (x_g; y_ojal) y (−x_g; −y_ojal): la base no vuelca como cuerpo libre, pero el par llega de una ménsula a la otra solo por torsión de la base (el tramo en x lleva el vector a lo largo de su eje), igual que en el modo pivotado; las bancadas corren en y y son secciones abiertas: no dan rigidez a torsión",
        cierre_empuje: "la ménsula recibe −F·ŷ a h; el patín pasa F_pas a la mesa por la uña (en línea con el eje) y la guía de la bancada solo toma las reacciones laterales y el roce; la mesa reacciona con el roce de la interfaz (a nivel de la plancha) y el otro cilindro: el par F·h de la ménsula no se cierra en la bancada",
        cierre_retorno_rampa: "uña trabada en la rampa del riel-leva: la ménsula recibe +F_ret·ŷ a h y el riel −F_ret·ŷ a la altura del seguidor en los pórticos, sobre la prolongación de la misma bancada; el resto lo toma el patín sobre la bancada: el par se cierra en la franja (bancada y plancha entre la ménsula y los pórticos), sin cruzar la base",
        cierre_retorno_toma: "chaflán de la uña sobre el pasador siguiente a nivel de toma: la mesa toma F_ret y el riel N_toma = F_ret/tan β a la altura del seguidor: el par h·√(F_ret² + N_toma²) cruza la base como el empuje (menor)",
        casos: [cs("empuje a calado", BP.empuje, BP.empuje.sig > Fa ? "no cumple sin anclaje" : "cumple"), cs("retorno (atasco)", BP.retorno, BP.retorno.sig > Fa ? "no cumple sin anclaje" : "cumple")],
        mesa_vacia: { W_mesa_kN: BP.mesaVacia.W / 1e3, T_req_kN: BP.mesaVacia.Treq / 1e3, cumple: BP.mesaVacia.ok, nota: "calado con la mesa vacía: retención disponible = peso propio de la parte que gira; pedida = n_cil·M/s_H (cota del modelo de un soporte)" },
        M_kNm: tq.M / 1e6, V_esquina_kN: tq.Vc / 1e3, m_xy_kNm_m: tq.mxy / 1e3, tau_torsion_MPa: tq.tau, fu_torsion_cota_inferior: tq.tau / tq.cap,
        nota_torsion: "τ = 6·m_xy/t² ≤ Fy/(Nd·√3) (ASME BTH-1 §3-2.3.6) para la placa libre en torsión pura: cota inferior; la FEA de la base completa (bancadas con su sección real, contacto unilateral, peso propio) da más",
        fea: "estudio (malla de 40 mm; por defecto / interfaz B): mesa vacía con los dos cilindros a calado, FU ≈ 2,0 / 3,5 en la plancha lejos de las ménsulas y ≈ 4,7 / 7,6 en la bancada, con las esquinas libres levantadas ≈ 0,13 / 0,23 m (cálculo lineal); junto a la esquina de las mejillas 8,5 / 13 (depende de la malla: 21 con 20 mm); mesa cargada ≈ 3,9 / 6,0 junto a las mejillas, 2,2 / 3,4 lejos y 1,8 / 2,8 en la bancada; un cilindro con la mesa vacía: sin equilibrio; retorno ≈ 1,3–1,7 / 2,0–2,6 en la franja de plancha entre las mejillas y la bancada (lejos ≤ 0,6 / 0,8). En el modo pivotado, con la misma malla: 21 / 33 junto al soporte y 7,4 / 11,5 lejos, con 0,28 / 0,46 m",
        conclusion: "NO cumple sin anclaje ni base rígida: el modo guiado tiene el mismo mecanismo (torsión de la base entre las dos ménsulas) con valores menores que el pivotado; cerrar la franja de plancha entre la ménsula y la bancada no alcanza (la bancada queda con FU ≈ 4 con la mesa vacía) y un perno en cada esquina libre pide ≈ 75 kN por defecto y la bancada sigue en ≈ 3,7: decisión del mandante (anclaje con datos de la losa, base rígida o restricción del calado con la mesa vacía)",
        caso_termico: "no aplica (F de la presión de alivio y de retorno; la base queda a la sombra)", estado: "PENDIENTE: decisión de anclaje a la losa (o rediseño de la base) por el mandante", referencia: REG_BPG } }; })() : null;
    return { modo: MODE, modo_nombre: MODE === 1 ? "guiado (patín y uña sobre bancada)" : "pivotado con guía de leva (tipo KIET)", levaGuiada, pivotado, guiado, masas_desc, tornillos_interfaz };
  }

  /* ---------------- Verificaciones de la leva guiada (Tarea 1) y del modo pivotado (Tarea 2) ---------------- */
  const REG_CG = "docs/normas/registro.md, «Leva de reenganche positiva (modo guiado)»", REG_PV = "docs/normas/registro.md, «Accionamiento pivotado tipo KIET»";
  const nfx = (v, d) => (+v).toFixed(d == null ? 1 : d).replace(".", ",");
  function camGuidedRows(P, R, add) {
    const c = R.camG, G = "Leva de reenganche";
    if (!c) { add({ grp: G, sys: "giro", kind: "info", name: "Leva de reenganche positiva desactivada (opt_cam = 0): el reenganche depende solo del resorte", formula: "Sin verificación", dem: 0, unit: "–", ref: REG_CG }); return; }
    const Nd = P.Nd, Fy = P.Fy_cam, FyP = P.Fy, f = c.fam, Es = P.E / (2 * (1 - P.nu ** 2)), Bh = P.B / 2 - P.rim_t - 5, po = c.portico;
    add({ grp: G, sys: "giro", kind: "geo", name: "Sincronía: holgura uña–pasador siguiente con la uña contra la rampa de reenganche", formula: "mín holgura(uña con u = u_leva(η), pasador B) ≥ margen en la rampa; rampa a α = " + P.cam_alpha + "° desde η₀ + tramo (η₀ = −r − s_libre); la punta despeja B antes de que la rampa la empuje hacia adentro", dem: P.cam_msync, cap: c.sync, unit: "mm", ref: REG_CG + "; geometría (polígono de la uña con su chaflán frente al círculo del pasador)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Bolsillo de la leva: salida necesaria de la uña para pasar sobre el pasador siguiente frente al recorrido de retorno", formula: "máx u_nec(η; margen) ≤ Δx = recorrido de retorno de la uña en el patín", dem: c.needMax, cap: c.travel, unit: "mm", ref: REG_CG });
    add({ grp: G, sys: "giro", name: "Rampa de reenganche sin autobloqueo (μ_ret en el alojamiento; μ del seguidor " + (f.f === 1 ? "de rodillo" : f.corto) + ")", formula: "μ_ret·k_t·(sen α + μ_seg·cos α) < (cos α − μ_seg·sen α)·(1 − 2·μ_ret·z_f/L_in); k_t = 1 + 2(z_f − z_ranura)/h_uña = " + nfx(c.kt, 3) + " (torsión de la uña por la fuerza alta del seguidor), μ_seg = " + nfx(c.muC, 3), dem: c.lockDem, cap: c.lockCap, unit: "–", ref: REG_CG + "; equilibrio de la cuña con fricción" });
    add({ grp: G, sys: "giro", kind: "info", name: "Fracción del empuje con la uña retenida por la leva a nivel de toma (el bolsillo coincide con la toma del pasador siguiente)", formula: "(η₁ − η_entrada)/cuerda; en el resto el bolsillo deja la uña con el resorte y el roce del alojamiento, como hoy", dem: c.cover, unit: "–", ref: REG_CG });
    add({ grp: G, sys: "giro", kind: "info", name: "Leva: fuerzas de atasco al retraer a p_ret (cotas sin roce): rampa N = F_ret/sen α / nivel de toma N = F_ret/tan β", formula: "F_ret = A_anular·p_ret = " + nfx(c.Fret / 1e3) + " kN", dem: c.NR / 1e3, cap: c.NT / 1e3, unit: "kN (rampa / toma)", ref: REG_CG });
    add({ grp: G, sys: "giro", kind: "geo", name: "Riel-leva bajo la cara superior de la mesa", formula: "z_sup_patín + 2 + t_leva ≤ z_eje + h_mesa/2", dem: c.zPb + P.cam_t, cap: c.zTop, unit: "mm", ref: "Geometría (alzado)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Riel-leva sobre el cuerpo del cilindro (soporte trasero)", formula: "z_eje + D_cuerpo/2 + 1 ≤ z_inf_leva", dem: c.zc0 + P.D_body / 2 + 1, cap: c.zPb, unit: "mm", ref: "Geometría (alzado)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Riel-leva dentro de la base (x)", formula: "x_canto + ancho ≤ B/2 − t_marco − 5", dem: c.xPo, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Pórtico del riel: pata exterior y su tapa bajo el riel (x)", formula: "x_pata,ext + máx(b; tapa)/2 ≤ x_borde del riel", dem: c.portico.xR + c.portico.capW / 2, cap: c.xPo, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Pórtico del riel: pata interior fuera de la mesa (x)", formula: "D/2 + 10 ≤ x_pata,int − máx(b; tapa)/2", dem: P.D_top / 2 + 10, cap: c.portico.xL - c.portico.capW / 2, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Ranura de la tapa del patín para el perno del seguidor dentro del patín", formula: "x_perno + Δx + d_perno/2 + 10 ≤ x_g + w_s/2", dem: c.xFp0 + c.travel + P.cam_dp / 2 + 10, cap: P.x_g + P.w_s / 2, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Seguidor dentro del espesor del riel", formula: "b_seguidor + 5 ≤ t_leva", dem: P.cam_bf + 5, cap: P.cam_t, unit: "mm", ref: "Geometría" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Seguidor: rodillo y su retención (arandela de tope " + c.hRet + " mm con tornillo axial) bajo la cara superior del riel y de la mesa", formula: "2 (chaflán inferior del canto) + b_rodillo + arandela + 1 ≤ mín(t_leva; z_sup_mesa − z_inf_riel); el perno llega a la cara superior del rodillo (largo " + nfx(c.lPerno, 0) + " mm con 30 empotrados)", dem: 2 + P.cam_bf + c.hRet + 1, cap: c.hAvail + 1, unit: "mm", ref: "Geometría (alzado); la carga puede volar sobre el borde de la mesa" });
    add({ grp: G, sys: "giro", kind: "info", name: "Ranura de la tapa del patín: ajuste con el perno del seguidor", formula: "ranura " + P.cam_dp + " H9 (+0/+" + nfx(isoIT(P.cam_dp, 9) * 1e3, 0) + " µm) y perno Ø" + P.cam_dp + " f8 (−" + nfx(-isoF(P.cam_dp) * 1e3, 0) + "/−" + nfx((isoIT(P.cam_dp, 8) - isoF(P.cam_dp)) * 1e3, 0) + " µm): juego " + nfx(-isoF(P.cam_dp), 3) + "…" + nfx(isoIT(P.cam_dp, 9) - isoF(P.cam_dp) + isoIT(P.cam_dp, 8), 3) + " mm (ajuste deslizante; antes ranura " + (P.cam_dp + 1) + " rotulada H9/f8)", dem: P.cam_dp, unit: "mm", ref: "ISO 286-1:2010 e ISO 286-2:2010 (H9, f8)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Seguidor libre del borde de la mesa", formula: "D/2 + 5 ≤ x_perno − Ø_seguidor/2", dem: P.D_top / 2 + 5, cap: c.xFp0 - P.cam_df / 2, unit: "mm", ref: "Geometría (planta)" });
    if (f.tipo === "hertz") {
      const q = c.Nd / P.cam_bf, p0 = Math.sqrt(q * Es / (Math.PI * P.cam_df / 2));
      add({ grp: G, sys: "est", name: "Seguidor: contacto de Hertz rodillo–canto templado del riel (atasco a p_ret)", formula: "p₀ = √(q·E*/(π·r)), q = N/b, E* = E/(2(1 − ν²)) ≤ 1,67·Fy_sup", dem: p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: f.pRef });
    } else {
      const p = c.Nd / (P.cam_df * P.cam_bf);
      add({ grp: G, sys: "est", name: "Seguidor de zapata (" + f.corto + "): presión de contacto con la carga de atasco a p_ret", formula: "p = N/(Ø·b) ≤ p_adm de la familia", dem: p, cap: f.pAdm, unit: "MPa", ref: f.pRef });
      if (f.FyL) add({ grp: G, sys: "est", name: "Seguidor de zapata (" + f.corto + "): aplastamiento del revestimiento", formula: "p ≤ 1,25·Fy/Nd", dem: p, cap: 1.25 * f.FyL / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    }
    const Ap = Math.PI / 4 * P.cam_dp ** 2;
    add({ grp: G, sys: "est", name: "Perno del seguidor: flexión (voladizo desde la cara superior de la uña)", formula: "σ = N·l/(πd³/32), l = z_rodillo − z_sup_uña = " + nfx(c.lFp) + " mm ≤ Fy/Nd", dem: c.Nd * c.lFp / (Math.PI * P.cam_dp ** 3 / 32), cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / §3-2.3" });
    add({ grp: G, sys: "est", name: "Perno del seguidor: corte", formula: "τ = N/A ≤ Fy/(Nd·√3)", dem: c.Nd / Ap, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    add({ grp: G, sys: "est", name: "Ranura de la tapa del patín (guía del perno): aplastamiento por la fuerza en y", formula: "σ = F_ret/(d_perno·t_tapa) ≤ 1,25·Fy_patín/Nd", dem: c.Fret / (P.cam_dp * P.t_pk), cap: 1.25 * P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    add({ grp: G, sys: "est", name: "Riel-leva: flexión en planta + axial en el bolsillo (ancho reducido; biapoyado entre soportes)", formula: "σ = máx[N_toma·k_M; N_rampa,x·k_M + F_ret·w_n/… ]: N·k_M/(t·w_n²/6) + F_ret/(t·w_n); k_M = máx (L/2 + y)(L/2 − y)/L = " + nfx(c.kM) + " mm, w_n = " + nfx(c.wNet) + " mm", dem: c.sigPl, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3 y §3-2.1" });
    add({ grp: G, sys: "est", name: "Pórtico del riel: flexión de cada pata en su base (R_x/2 y R_y/2 a la altura del riel; patas y tapas de S355J2, soldables)", formula: "σ = (R_x/2)·h/(l·b²/6) + (R_y/2)·h/(b·l²/6) ≤ Fy/Nd, Fy = " + FyP + " MPa (S355J2: el 42CrMo4+QT no es metal base precalificado de AWS D1.1), h = " + nfx(c.hPed) + " mm (voladizo, conservador frente al pórtico)", dem: c.ped.sPed, cap: FyP / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3; AWS D1.1/D1.1M:2020 Tabla 5.3 (metales base precalificados)" });
    add({ grp: G, sys: "est", name: "Pórtico del riel: soldadura de cada pata a su asiento (filete perimetral)", formula: "f = √[(M_x/S_x + M_y/S_y)² + (V/(a·2(b + l)))²] ≤ 0,60FEXX/(1,20Nd); S_x = a(l·b + b²/3), S_y = a(b·l + l²/3)", dem: c.weld.fW, cap: c.Fwc, unit: "MPa", ref: "AISC 360-22 §J2.4 (grupo de soldadura, método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: G, sys: "est", name: "Pernos riel–pórtico: corte (M" + P.cam_db + ", " + P.cam_nb + " por pórtico)", formula: "f_rv = (R/n)/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu (rosca incluida), Ω = 2,00", dem: c.bolts.b.frv, cap: c.bolts.b.capV, unit: "MPa", ref: "AISC 360-22 §J3.7, Tabla J3.2" });
    add({ grp: G, sys: "est", name: "Pernos riel–pórtico: aplastamiento en el riel", formula: "R/n ≤ R_n/Ω, R_n = 2,4·d·t·Fu, Ω = 2,00", dem: c.bolts.V / 1e3, cap: c.bolts.Rn / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a)" });
    add({ grp: G, sys: "est", name: "Pernos riel–pórtico: aplastamiento en la tapa de la pata (largo enganchado)", formula: "R/n ≤ R_n/Ω, R_n = 2,4·d·l_e·Fu (S355J2), l_e = " + nfx(po.leCap, 0) + " mm, Ω = 2,00", dem: c.bolts.V / 1e3, cap: c.bolts.RnC / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a)" });
    add({ grp: G, sys: "est", kind: "geo", name: "Pernos riel–pórtico: engrane de la rosca en la tapa de la pata (taladro ciego)", formula: "1,25·d ≤ l_e = L − t_riel (ISO 4762 M" + P.cam_db + " × " + po.Lb + " – 10.9; tapa de " + po.tCap + " mm, taladro " + (po.tCap - 3) + " mm con remanente 3 mm, rosca útil " + nfx(po.huCap, 1) + " mm)", dem: 1.25 * P.cam_db, cap: po.leCap, unit: "mm", ref: "VDI 2230-1:2015 (orientativo, 10.9 en acero S355); criterio del registro (AF2)" });
    add({ grp: G, sys: "est", kind: "geo", name: "Pernos riel–pórtico: punta del perno dentro de la rosca útil de la tapa", formula: "l_e + 2 ≤ rosca útil = (t_tapa − 3) − 2·P", dem: po.leCap + 2, cap: po.huCap, unit: "mm", ref: "Criterio del proyecto" });
    add({ grp: G, sys: "est", name: "Pórtico del riel: soldadura pata–tapa (filetes a ambos lados, z" + c.weldPT.wPT + ")", formula: "f = √[((R_x/2)·e/(a·l·b) + (R_y/2)·e/(a·l²/3))² + (R/2/(2·a·l))²] ≤ 0,60FEXX/(1,20Nd), e = t_tapa = " + po.tCap + " mm, a = 0,707w", dem: c.weldPT.fPT, cap: c.Fwc, unit: "MPa", ref: "AISC 360-22 §J2.4 (grupo de soldadura, método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: G, sys: "est", kind: "geo", name: "Pórtico del riel: filete pata–tapa mínimo según la parte más gruesa", formula: "w_mín(T = máx(b_pata; t_tapa) = " + Math.max(P.cam_px, po.tCap) + ") ≤ w", dem: wMin(Math.max(P.cam_px, po.tCap)), cap: c.weldPT.wPT, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7" });
    add({ grp: G, sys: "est", name: "Prolongación de la bancada: soldadura a la base (filete perimetral w_bed_f) con el vuelco del pórtico", formula: "f = √[(R_x·h/S_x + R_y·h/S_y)² + (R/(a·2(b + l)))²] ≤ 0,60FEXX/(1,20Nd); h = z_riel − t_base, b = " + nfx(Math.max(po.wExt, P.w_bed), 0) + ", l = " + P.cam_ls + " mm, S_x = a(l·b + b²/3), S_y = a(b·l + l²/3)", dem: c.weldEx.fEx, cap: c.Fwc, unit: "MPa", ref: "AISC 360-22 §J2.4 (grupo de soldadura, método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: G, sys: "est", kind: "geo", name: "Prolongación de la bancada: filete mínimo según la parte más gruesa", formula: "w_mín(T = máx(t_bancada; t_base) = " + Math.max(P.t_bed, P.t_base) + ") ≤ w_bed_f", dem: wMin(Math.max(P.t_bed, P.t_base)), cap: P.w_bed_f, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7" });
    add({ grp: G, sys: "est", kind: "info", name: "Seguidor: grado del rodillo y del canto", formula: "rodillo macizo de 100Cr6 (ISO 683-17), templado total 58–64 HRC, más duro que el canto del riel (42CrMo4+QT templado por inducción ≥ 55 HRC): el Hertz se verifica con Fy_sup del canto; cojinete del rodillo sobre el perno: dato del proveedor del seguidor (hipótesis: μ equivalente ≤ μ_rod = " + nfx(P.mu_roll, 3) + ")", dem: P.cam_df, cap: P.cam_bf, unit: "mm (Ø / ancho)", ref: "ISO 683-17:2014; " + REG_CG });
    add({ grp: G, sys: "est", kind: "info", name: "Masa de la leva por cilindro: riel, soportes, prolongación de la bancada y seguidor", formula: "m = ρ·V (el riel descuenta el bolsillo)", dem: c.m.one, unit: "kg", ref: "Geometría" });
  }
  function pivAsym(P, R) {
    const K = R.K, fam = R.fam || camFam(P), mu1 = P.mu_s + 0.05, mu2 = Math.max(0, P.mu_s - 0.05), F0 = R.Fstall * P.eta_c;
    let H = 0, FradD = 0, FradS = 0;
    (K.pts || []).forEach((q, i) => {
      const s = q.vs !== 0 ? -Math.sign(q.vs) : -Math.sign(q.Cu), F1 = F0 / (1 + fam.mu * mu1), F2 = F0 / (1 + fam.mu * mu2), rr = [q.P[0] / P.R_pin, q.P[1] / P.R_pin];
      const nx = F1 * (q.u[0] + s * mu1 * q.t[0]) - F2 * (q.u[0] + s * mu2 * q.t[0]), ny = F1 * (q.u[1] + s * mu1 * q.t[1]) - F2 * (q.u[1] + s * mu2 * q.t[1]);
      H = Math.max(H, Math.hypot(nx, ny));
      const fr = (q.u[0] + s * P.mu_s * q.t[0]) * rr[0] + (q.u[1] + s * P.mu_s * q.t[1]) * rr[1], Fd = R.stroke[i] ? R.stroke[i].Fp : 0;
      FradD = Math.max(FradD, Math.abs(Fd * fr)); FradS = Math.max(FradS, Math.abs(R.stallMax.Fp * fr));
    });
    return { H, FradD, FradS };
  }
  function pivPinM(P, R, F, Ncam) {   // momentos de los pasadores Q y E (N·mm) con la fuerza del cilindro F (N) y la de la leva Ncam (N)
    const bk = R.blk, g = P.g_ch, b = P.b_eye;
    return { MQ: Math.hypot(F / 2 * (bk.tq / 2 + g + b / 4), (Ncam || 0) * bk.lq), ME: F / 2 * (P.pv_tl / 2 + g + b / 4) };
  }
  // Soporte del ojal E con la fuerza F (N) del cilindro empujando el pasador E hacia atrás (−u), en todos los estados del barrido y en ambos sentidos (marco canónico):
  // flexión biaxial de las paredes en la base (M = F/2·(h_sup + h_inf)), corte, CJP pared–base (von Mises con el metal base), flujo de corte en las CJP pared–pared
  // y PJP de las tapas (grupo elástico de líneas en el plano de la tapa con F/2 en E). Devuelve los máximos y el estado que los produce.
  function pivSupLoads(P, sg, F) {
    const out = { sig: 0, tau: 0, vm: 0, flow: 0, pjp: 0, psi: {} }, hs = sg.hU + sg.hL, ws = sg.walls, byId = (id) => ws.filter((w) => w.id === id).map((w) => w.rect);
    const joints = [["J-E3", byId("pared_Y").concat(byId("munon_X"))], ["J-E4", byId("munon_Y")], ["J-E5", byId("munon_X")]].filter((j) => j[1].length);
    const upd = (k, v, psi) => { if (v > out[k]) { out[k] = v; out.psi[k] = psi; } };
    sg.sweep.estados.concat(sg.sweep.horario).forEach((q) => {
      const f = [-Math.cos(q.psi), -Math.sin(q.psi)], m = [-f[1] * F / 2 * hs, f[0] * F / 2 * hs];
      const sig = PG.sigMax(sg.sec, m), Av = ws.reduce((a, w) => { const [x0, x1, y0, y1] = w.rect, lx = x1 - x0, ly = y1 - y0, L = Math.max(lx, ly), t = Math.min(lx, ly), d = lx >= ly ? f[0] : f[1]; return a + t * L * d * d; }, 0);
      const tau = F / Av; upd("sig", sig, q.psi); upd("tau", tau, q.psi); upd("vm", Math.sqrt(sig * sig + 3 * tau * tau), q.psi);
      joints.forEach(([, sub]) => upd("flow", PG.flow(sg.sec, sub, f, F) / P.pv_tbox, q.psi));
      upd("pjp", sg.capQ(f, F / 2) / sg.E_pjp, q.psi);
    });
    return out;
  }
  // Plancha base bajo el soporte del ojal E (docs/normas/registro.md, «Plancha base bajo el soporte del ojal E (10-11-2026)»). El soporte es un cuerpo rígido
  // soldado a la plancha; la fuerza del cilindro F·f actúa en E a h = (h_sup + h_inf)/2 sobre la plancha (resultante de F/2 en cada tapa) y le aplica M = F·h
  // alrededor del eje horizontal ⟂ f. En el plano de la plancha F se cierra con el otro cilindro y el roce de la mesa (par horizontal): la losa no toma corte.
  // La losa es rígida y solo comprime (contacto unilateral); el proyecto no define anclaje (base apoyada en losa o mats) y el peso propio de la plancha es
  // despreciable (ρ·g·t ≈ 0,0014 MPa), de modo que la única retención del talón es la mesa (R ≤ D/2), a través de la plancha.
  // Franja (equilibrio del cuerpo libre soporte + plancha del lado del pie de la línea del talón, ∥ al vector momento): con la compresión de la losa en el pie
  // (brazo a = extensión de la huella de las paredes en f) y la retención en el borde MÁS LEJANO de la mesa (s_H = brazo desde el pie: el brazo más largo,
  // favorable para la retención T = M/s_H y conservador para M_corte, que crece con s_H),
  // M_corte = M·(1 − a/s_H) cruza la línea del talón; si s_H ≤ a (la mesa no queda detrás del talón: retorno) no hay retención y M_corte = M.
  // Ancho b = w + a (w = ancho de la huella ⟂ f; reparto a 45° desde el centro de la huella, a a/2 de la línea crítica; criterio de ingeniería). σ = 6·M_corte/(b·t²) ≤ Fy/Nd.
  // Corte de la franja con la cota superior V = M/a (retención en el talón): τ = 1,5·V/(b·t) ≤ Fy/(Nd·√3). Empuje con F_calado (−u); retorno con
  // F_ret = A_anular·p_ret (atasco del retorno, +u); todos los estados del barrido en ambos sentidos (marco canónico del cilindro 1; el 2 por rotación de 180°).
  function pivBasePlate(P, R) {
    const sg = R.sup, K = R.K, E = K.E, O = [-sg.sx * E[0], sg.sy * E[1]], h = (sg.hU + sg.hL) / 2, t = P.t_base, Rh = P.D_top / 2;
    const V = sg.walls.flatMap((w) => { const [x0, x1, y0, y1] = w.rect; return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; }), d = (p, v) => p[0] * v[0] + p[1] * v[1];
    const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10, out = {};
    [["empuje", R.Fstall * 1e3, -1], ["retorno", Fret, 1]].forEach(([k, F, s]) => {
      let best = null;
      sg.sweep.estados.map((q) => Object.assign({ sentido: "antihorario" }, q)).concat(sg.sweep.horario.map((q) => Object.assign({ sentido: "horario" }, q))).forEach((q) => {
        const f = [s * Math.cos(q.psi), s * Math.sin(q.psi)], g = [-f[1], f[0]], pf = V.map((p) => d(p, f)), pg = V.map((p) => d(p, g));
        const toe = Math.max(...pf), a = toe - Math.min(...pf), w = Math.max(...pg) - Math.min(...pg), sH = toe - d(O, f) + Rh, M = F * h;
        const ret = sH > a, Mc = ret ? M * (1 - a / sH) : M, b = w + a, sig = 6 * Mc / (b * t * t), Vs = M / a, tau = 1.5 * Vs / (b * t);
        if (!best || sig > best.sig) best = { F, M, h, a, w, b, sH, ret, Mc, sig, Vs, tau, T: ret ? M / sH : Infinity, psi: q.psi, sentido: q.sentido, fase: q.fase };
      });
      out[k] = best;
    });
    // Mesa vacía: el calado no depende de la carga (atasco con la mesa vacía). La retención disponible es el peso propio de la parte que gira (W_d = mesa +
    // disco rotatorio + medio pivote, más los bloques-uña: cota superior) y la piden los dos soportes a la vez con el brazo más largo: T_req = 2·M/s_H.
    const Wm = R.Wd * 1e3 + (R.m.dogs || 0) * G, Treq = P.n_cyl * out.empuje.T;
    out.mesaVacia = { W: Wm, Treq, ok: Treq <= Wm };
    return out;
  }
  // Plancha base bajo la ménsula del ojal trasero del modo guiado (docs/qa/plancha_base_modo_guiado.md). Cilindro 1: lado +x, empuje +y; la ménsula (dos mejillas
  // soldadas a la plancha, marco local con origen en el ojal E = (x_g; y_ojal)) recibe −F·ŷ en el empuje y +F_ret·ŷ en el retorno, a la altura del eje h = h_eje
  // sobre la plancha: M = F·h alrededor de x. En el empuje la reacción la da la mesa (roce de la interfaz y el otro cilindro, a 180°): con los dos cilindros
  // M₂ = −M₁ entre (x_g; y_ojal) y (−x_g; −y_ojal) y el par cruza la base como torsión (la bancada es una sección abierta y corre en y). En el retorno con la uña
  // trabada en la rampa del riel-leva la reacción está en los pórticos de la misma bancada (se cierra en la franja); a nivel de toma (chaflán sobre el pasador
  // siguiente) la toma la mesa y cruza la base como el empuje. Mismo modelo de franja que pivBasePlate (soporte rígido, losa solo a compresión, retención en el borde
  // más lejano de la mesa; no cuenta la bancada) y la cota inferior de la torsión de la placa libre, τ = 6·m_xy/t² con m_xy = M/(2·B).
  function guidedBasePlate(P, R) {
    const K = R.K, bg = bracketGeo(P), h = R.hax, t = P.t_base, Rh = P.D_top / 2, x0 = bg.Win / 2, x1 = x0 + P.t_ch, y0 = -bg.rear, y1 = P.L_ch - bg.rear;
    const walls = [[x0, x1, y0, y1], [-x1, -x0, y0, y1]], O = [-P.x_g, -K.y_eye];
    const V = walls.flatMap(([a0, a1, b0, b1]) => [[a0, b0], [a1, b0], [a1, b1], [a0, b1]]), d = (p, v) => p[0] * v[0] + p[1] * v[1];
    const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10, out = { h, walls, O, ojal: [P.x_g, K.y_eye] };
    [["empuje", R.Fstall * 1e3, -1], ["retorno", Fret, 1]].forEach(([k, F, s]) => {
      const f = [0, s], g = [-f[1], f[0]], pf = V.map((p) => d(p, f)), pg = V.map((p) => d(p, g));
      const toe = Math.max(...pf), a = toe - Math.min(...pf), w = Math.max(...pg) - Math.min(...pg), sH = toe - d(O, f) + Rh, M = F * h;
      const ret = sH > a, Mc = ret ? M * (1 - a / sH) : M, b = w + a, sig = 6 * Mc / (b * t * t), Vs = M / a, tau = 1.5 * Vs / (b * t);
      out[k] = { F, M, h, a, w, b, sH, ret, Mc, sig, Vs, tau, T: ret ? M / sH : Infinity };
    });
    // mesa vacía: la retención disponible es el peso propio de la parte que gira (W_d: las uñas van en los patines, sobre la bancada)
    const Wm = R.Wd * 1e3, Treq = P.n_cyl * out.empuje.T;
    out.mesaVacia = { W: Wm, Treq, ok: Treq <= Wm };
    // torsión de la base entre las dos ménsulas (cota inferior: placa libre en torsión pura, sin peso ni contacto)
    const Mt = out.empuje.M, mxy = Mt / (2 * P.B);
    out.torsion = { M: Mt, Vc: Mt / P.B, mxy, tau: 6 * mxy / (t * t), cap: P.Fy / (P.Nd * Math.sqrt(3)) };
    return out;
  }
  // ---------------- Inserto de esquina bajo el soporte del cilindro (decisión del mandante 10-11-2026) ----------------
  // docs/normas/registro.md, «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)»; docs/qa/plancha_base_inserto.md.
  // Base de t_base en toda la planta. Bajo cada soporte del cilindro (modo 2: soporte del ojal E en las dos esquinas diagonales; modo 1: las n_br ménsulas del
  // ojal trasero, una por esquina) va un inserto de plancha más gruesa, al ras por debajo con la base y con la cara superior más alta, unido a la base con una CJP
  // a tope con transición 1:2,5 en la cara superior (el inserto se bisela). Planta, en el marco canónico de la esquina (+B/2; −B/2): triángulo X − Y ≥ c con la
  // hipotenusa a D/2 + ins_gap del centro, menos dos muescas rectangulares que dejan libres (con ins_clr) las piezas apoyadas en la base: placas-guía y trayectoria
  // del cubo y pasador Q (modo 2) o la banda del accionamiento guiado (bancada, prolongación, pórticos, patín; modo 1). Muesca del lado X: {X ≥ a, Y ≥ b};
  // muesca del lado Y: {X ≤ a', Y ≤ b'}. Espesor: el menor comercial de INS_T con FU ≤ 1 en todos los casos y holgura vertical ≥ 5 mm a las partes móviles.
  // Tensión (modelo calibrado; el núcleo no resuelve contacto unilateral): σ = κ·M·S(t_base, t_ins), con S = σ/M (MPa por kN·m) tabulada desde la FEA de Mindlin
  // de la base completa del verificador (tests/indep_plancha_base_E.py: mesa cargada como cuerpo rígido con contacto unilateral, losa unilateral, dos soportes
  // rígidos con M₂ = −M₁, inserto con su transición, malla 40 mm), con σ_vM evaluada a más de 100 mm de la huella rígida del soporte (criterio de la verificación
  // independiente: fuera de la singularidad de la esquina rígida); κ = INS_KAPPA cubre la interpolación y la banda de ψ. Retorno (atasco con la mesa cargada) y
  // mesa vacía en servicio: factores de la misma FEA sobre S (INS_RET, INS_VAC). Criterio: F_b = 1,25·Fy/Nd (ASME BTH-1-2020 §3-2.3.4, flexión respecto del
  // eje menor de secciones rectangulares macizas), Nd del proyecto.
  const INS_T = [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120];   // espesores comerciales de plancha (mm)
  const INS_SLOPE = 2.5, INS_KAPPA = 1.03, INS_FB = 1.25, INS_FUOBJ = 0.90, INS_PHI = 0.5;   // FU objetivo interno del proyecto (sobre 0,90: advertencia)
  const hull2 = (pts) => {   // envolvente convexa (cadena monótona), antihoraria
    const q = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]), cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], up = [];
    q.forEach((p) => { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); });
    for (let i = q.length - 1; i >= 0; i--) { const p = q[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  };
  const INS_CAL = {"2": [{"gap": 30, "clr": 10, "tb": [16, 20, 25], "ti": [45, 50, 55, 60, 70, 80, 90, 100], "S": [[4.3991, 3.8708, 3.4726, 3.2003, 2.8747, 2.7089, 2.6074, 2.5495], [3.5072, 3.0711, 2.7532, 2.5562, 2.2866, 2.1245, 2.0234, 1.974], [2.7432, 2.3924, 2.1773, 2.008, 1.7743, 1.6225, 1.5358, 1.4814]], "retS": 13.6, "retTb": 20, "retRef": 55, "vac": 1.8}, {"gap": 10, "clr": 8, "tb": [16, 20, 25], "ti": [40, 45, 50, 55, 60, 70, 80, 90, 100, 110], "S": [[4.8058, 4.1952, 3.7372, 3.3754, 3.1236, 2.7533, 2.5554, 2.437, 2.401, 2.4089], [3.9912, 3.4502, 3.0764, 2.779, 2.5464, 2.2331, 2.043, 1.93, 1.9182, 1.9228], [3.1894, 2.7654, 2.4553, 2.2173, 2.0232, 1.7545, 1.5807, 1.4835, 1.4541, 1.4749]], "retS": 13.0, "retTb": 20, "retRef": 55, "vac": 1.8}], "1": [{"gap": 10, "clr": 8, "tb": [16, 20, 25], "ti": [35, 40, 45, 50, 55, 60, 70, 80, 90, 100], "S": [[4.3482, 3.7442, 3.2336, 2.827, 2.4945, 2.2839, 1.99, 1.7827, 1.6304, 1.5185], [3.5581, 3.0028, 2.7399, 2.4496, 2.1858, 1.9049, 1.5949, 1.4293, 1.2971, 1.2045], [2.8373, 2.3972, 2.1341, 2.0042, 1.8389, 1.6808, 1.3654, 1.2159, 1.1085, 1.0216]], "retS": 11.4, "retTb": 20, "retRef": 35, "vac": 1.8}]};
  const insS = (cal, tb, ti) => {   // σ/M (MPa por kN·m): interpolación en t_ins por fila y lineal entre filas de t_base; fuera de la tabla, del lado seguro
    const row = (r) => { const T = cal.ti, S = cal.S[r]; if (ti <= T[0]) return S[0] + (S[0] - S[1]) / (T[1] - T[0]) * (T[0] - ti); if (ti >= T[T.length - 1]) return S[S.length - 1];
      let k = 1; while (T[k] < ti) k++; return S[k - 1] + (S[k] - S[k - 1]) * (ti - T[k - 1]) / (T[k] - T[k - 1]); };
    const B = cal.tb; if (tb <= B[0]) return row(0) * (B[0] / tb) ** 2; if (tb >= B[B.length - 1]) return row(B.length - 1);
    let k = 1; while (B[k] < tb) k++; return row(k - 1) + (row(k) - row(k - 1)) * (tb - B[k - 1]) / (B[k] - B[k - 1]);
  };
  // polígono del inserto en el marco canónico (esquina (+Bh; −Bh)); nx = {a, b} muesca del lado X, ny = {a, b} muesca del lado Y (null si no hay)
  // Región {Y ≥ −Bh, X ≤ Bh, X − Y ≥ c} menos {X ≥ a, Y ≥ b} (nx) y {X ≤ a′, Y ≤ b′} (ny): para cada X es un solo intervalo de Y
  // [lo(X), up(X)] (lo = b′ si X ≤ a′, si no −Bh; up = mín(X − c; b si X ≥ a)); el contorno es la cadena superior de izquierda a derecha, el borde X = Bh y
  // la cadena inferior de vuelta. ok = el conjunto de X con intervalo no vacío es conexo (si no, las muescas parten el inserto).
  function insPoly(Bh, c, nx, ny) {
    const up = (x, s) => Math.min(x - c, nx && (s > 0 ? x >= nx.a : x > nx.a) ? nx.b : Infinity), lo = (x, s) => (ny && (s > 0 ? x < ny.a : x <= ny.a) ? Math.max(-Bh, ny.b) : -Bh);
    const brk = [nx && nx.a, ny && ny.a, nx && nx.b + c, ny && ny.b + c, -Bh + c, Bh].filter((x) => x != null && isFinite(x) && x >= -Bh + c - 1e-9 && x <= Bh + 1e-9);
    const xs = brk.slice().sort((p, q) => p - q).filter((x, i, A) => i === 0 || x - A[i - 1] > 1e-9);   // sin redondear: los saltos en a y a′ se evalúan con los valores exactos
    const valid = (x, s) => up(x, s) - lo(x, s) > 1e-6, segs = [];   // tramos [x_i, x_i+1] con región (muestra en el punto medio)
    for (let i = 0; i + 1 < xs.length; i++) { const m = (xs[i] + xs[i + 1]) / 2; if (valid(m, 0)) segs.push([xs[i], xs[i + 1]]); }
    if (!segs.length) return { V: [], ok: false };
    let ok = true; for (let i = 1; i < segs.length; i++) if (segs[i][0] - segs[i - 1][1] > 1e-6) ok = false;
    const run = []; segs.forEach((g) => { if (!run.length || g[0] - run[run.length - 1][1] > 1e-6) run.push([g[0], g[1]]); else run[run.length - 1][1] = g[1]; });
    const best = run.reduce((m, g) => (g[1] - g[0] > m[1] - m[0] ? g : m), run[0]), X = xs.filter((x) => x >= best[0] - 1e-9 && x <= best[1] + 1e-9);
    const U = [], L = [];
    X.forEach((x, i) => { const l = i > 0, r = i < X.length - 1;   // límites por izquierda y por derecha (saltos en a y a′)
      const uL = up(x, -1), uR = up(x, 1), lL = lo(x, -1), lR = lo(x, 1);
      if (l) U.push([x, uL]); if (r && (!l || Math.abs(uR - uL) > 1e-9)) U.push([x, uR]);
      if (l) L.push([x, lL]); if (r && (!l || Math.abs(lR - lL) > 1e-9)) L.push([x, lR]); });
    const V = U.concat(L.reverse()), W = [];
    V.forEach((p) => { if (!W.length || Math.hypot(p[0] - W[W.length - 1][0], p[1] - W[W.length - 1][1]) > 1e-6) W.push(p); });
    if (W.length > 1 && Math.hypot(W[0][0] - W[W.length - 1][0], W[0][1] - W[W.length - 1][1]) < 1e-6) W.pop();
    const C = W.filter((p, i) => { const a0 = W[(i + W.length - 1) % W.length], b0 = W[(i + 1) % W.length]; return Math.abs((p[0] - a0[0]) * (b0[1] - a0[1]) - (p[1] - a0[1]) * (b0[0] - a0[0])) > 1e-6; });   // sin vértices colineales
    // empieza en la esquina (Bh; −Bh) si está
    const k = C.findIndex((p) => Math.abs(p[0] - Bh) < 1e-6 && Math.abs(p[1] + Bh) < 1e-6);
    return { V: k > 0 ? C.slice(k).concat(C.slice(0, k)) : C, ok };
  }
  const insCache = new WeakMap(), cornerInsertOf = (P, R) => { if (!insCache.has(R)) insCache.set(R, cornerInsert(P, R)); return insCache.get(R); };
  function guidedBand(P, R, sx) {   // banda del accionamiento guiado del lado sx (sin la holgura): bancada (± prolongación), patín, cilindro, riel-leva y pórticos
    const g = guideGeo(P), c = R.camG;
    const x0 = Math.min(P.x_g - P.w_s / 2, P.x_g - P.w_bed / 2, P.x_g - P.D_body / 2, c ? Math.min(c.xFp0 - P.cam_df / 2, c.portico.xL - c.portico.capW / 2) : Infinity);
    const x1 = Math.max(P.x_g + P.w_s / 2, P.x_g + P.w_bed / 2, P.x_g + P.D_body / 2, c ? Math.max(c.xPo, c.portico.xR + c.portico.capW / 2) : -Infinity), y1 = g.Y_bed + (c ? P.cam_ls : 0);
    return sx > 0 ? [x0, x1, -y1, y1] : [-x1, -x0, -y1, y1];
  }
  function cornerInsert(P, R) {
    const mode = driveMode(P), K = R.K;
    if (!(P.ins_on > 0) || !K || !K.ok || (mode === 2 && !(R.camP && R.camP.guia && R.sup)) || (mode === 1 && !R.camG)) return null;
    const Bh = P.B / 2, tb = P.t_base;
    const E1 = mode === 2 ? K.E : [P.x_g, K.y_eye], s0 = Math.sign(E1[0]) || 1, s1 = Math.sign(E1[1]) || -1;
    const toC = (p) => [s0 * p[0], -s1 * p[1]], toR = (q) => [s0 * q[0], -s1 * q[1]];
    // obstáculos apoyados en la base (planta, coordenadas reales del cilindro 1) y partes que pasan por encima (z)
    const obst = [], over = [];
    if (mode === 2) {
      const CP = R.camP;
      ["antihorario", "horario"].forEach((sen) => { const f = pivTr(P, sen, 1); obst.push({ id: "placa-guía 1_" + sen, poly: CP.guia.polilinea_contorno.map(f), z: [tb, tb + P.pv_tcam] }); });
      pivMoving(P, R).filter((s) => s.cil === 1).forEach((s) => s.partes.forEach((q) => { const o = { id: q.id + " (" + s.sentido + ")", grupo: q.id + " (" + s.sentido + ")", poly: q.poly, z: q.z };
        if (q.id === "cubo y pasador Q") obst.push(o); else over.push(o); }));
      const sg = R.sup; sg.piezas.filter((q) => !q.rect).forEach((q) => over.push({ id: "soporte E · " + q.id, poly: q.poly.map(sg.toReal(1)), z: q.z, propio: true }));
    } else {
      const b = guidedBand(P, R, s0); obst.push({ id: "accionamiento guiado (bancada, prolongación, pórticos, patín)", poly: PG.rect(b[0], b[1], b[2], b[3]), z: [tb, Infinity] });
      const zc = R.hax + tb, yE = E1[1], yb = s1 * (guideGeo(P).Y_bed + (R.camG ? P.cam_ls : 0));   // cuerpo entre el ojal y la banda del accionamiento
      over.push({ id: "cuerpo del cilindro", poly: PG.rect(E1[0] - P.D_body / 2, E1[0] + P.D_body / 2, Math.min(yE, yb), Math.max(yE, yb)), z: [zc - P.D_body / 2, zc + P.D_body / 2] });
    }
    // cargas por cilindro (M = F·h, h = eje sobre la cara superior de la base: el roce de la mesa entra a z = t_base)
    const h = mode === 2 ? (R.sup.hU + R.sup.hL) / 2 : R.hax, Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10 / 1e3;
    const cs = (id) => R.cases.find((q) => q.id === id), Nv = R.Wd, Fvac0 = Math.max(...["dis", "borde", "cont"].map((id) => cs(id) ? cs(id).F : 0)) * Nv / R.N, Fvac = P.ins_fsv * Fvac0;
    const lugBot = mode === 2 ? R.sup.zLugBot : tb + bracketGeo(P).spacer, Fb = INS_FB * P.Fy / P.Nd, cand = INS_T.filter((t) => t >= tb + 5);
    // variantes de planta calibradas (hipotenusa a D/2 + gap, muescas con clr), en orden de preferencia (inserto menor primero): la primera variante con un
    // espesor que cumple la flexión y las holguras manda; dentro de la variante, el menor espesor comercial
    const variant = (cal) => {
      const gap = cal.gap, clr = cal.clr, c = (P.D_top / 2 + gap) * Math.SQRT2;
      // muescas: cada obstáculo que alcanza el triángulo (con la holgura) va a la muesca del lado más cercano
      let nx = null, ny = null;
      obst.forEach((o) => { const q = o.poly.map(toC), xs = q.map((p) => p[0]), ys = q.map((p) => p[1]), bx = [Math.min(...xs), Math.max(...xs)], by = [Math.min(...ys), Math.max(...ys)];
        if (bx[1] - by[0] < c - clr) return;   // no alcanza el triángulo
        const cx = (bx[0] + bx[1]) / 2, cy = (by[0] + by[1]) / 2;
        if (Bh - cx <= cy + Bh) nx = { a: Math.min(nx ? nx.a : Infinity, bx[0] - clr), b: Math.min(nx ? nx.b : Infinity, by[0] - clr) };
        else ny = { a: Math.max(ny ? ny.a : -Infinity, bx[1] + clr), b: Math.max(ny ? ny.b : -Infinity, by[1] + clr) }; });
      const out0 = insPoly(Bh, c, nx, ny), Vc = out0.V, outline = Vc.map(toR);
      if (!out0.ok || Math.abs(PG.area(Vc)) < 1) return { ok: false, msg: "las muescas parten el inserto (sin tramo de hipotenusa)", outline, nx, ny, c, gap, clr };
      const fullOf = (t) => { const s = INS_SLOPE * (t - tb); return insPoly(Bh, c + s * Math.SQRT2, nx && { a: nx.a - s, b: nx.b - s }, ny && { a: ny.a + s, b: ny.b + s }).V.map(toR); };
      // holguras: en planta a los obstáculos; en altura (con la transición) a lo que pasa por encima
      const dOut = (o) => PG.dist(o.poly, outline), dObst = obst.map((o) => ({ o, d: dOut(o) }));
      const plan = dObst.reduce((m, x) => (x.d < m.d ? x : m), { d: Infinity, o: null });
      const ovr = over.map((o) => ({ o, d: dOut(o) })).filter((x) => x.d < 5);   // solapan en planta (d < 0) o pasan a menos de 5 mm
      // holgura de cada pieza que pasa por encima; con rebaje local (pk = {tr, polys}) la cara bajo las piezas cubiertas por el rebaje queda a tr
      const vList = (t, pk) => { const full = fullOf(t);
        return ovr.map((x) => { let d, top = t;
          if (x.d < 0) { const df = x.o.z[0] - t >= 5 ? 0 : PG.dist(x.o.poly, full); top = df <= 0 ? t : Math.max(tb, t - df / INS_SLOPE);   // sobre la transición: cara a t − d/2,5 (si la pieza deja 5 mm sobre t, no hace falta)
            if (pk && pk.grupos.includes(x.o.grupo || x.o.id)) top = Math.min(top, pk.tr);   // el rebaje es la envolvente convexa del barrido de su grupo: lo cubre entero
            d = x.o.z[0] - top; }
          else d = Math.hypot(x.d, Math.max(0, x.o.z[0] - tb));   // fuera del contorno: en el borde interior la cara está a t_base (arranque de la transición)
          return { d, id: x.o.id, z: x.o.z[0], top, propio: !!x.o.propio, poly: x.o.poly, grupo: x.o.grupo || x.o.id }; }); };
      const vMin = (L) => L.reduce((m, x) => (x.d < m.d ? x : m), { d: Infinity, id: null, z: null, top: null });
      const casos = [
        { id: "nom", nombre: "mesa cargada, empuje nominal (μ " + nfx(cs("nom").mu, 2) + ")", F: cs("nom").F, k: 1 },
        { id: "dis", nombre: "mesa cargada, empuje de diseño (μ " + nfx(cs("dis").mu, 2) + ", " + nfx(cs("dis").p, 0) + " bar)", F: cs("dis").F, k: 1 },
        { id: "cal", nombre: "mesa cargada, empuje a calado (" + nfx(P.p_relief, 0) + " bar)", F: R.Fstall, k: 1 },
        { id: "ret", nombre: "mesa cargada, atasco del retorno (F_ret = A_anular·p_ret, " + nfx(P.p_ret, 0) + " bar)", F: Fret, k: 1 },
        { id: "vac", nombre: "mesa vacía en servicio (F para girar la mesa vacía × " + nfx(P.ins_fsv, 2) + ")", F: Fvac, k: cal.vac },
      ];
      // S con rebaje local a tr: S(t) + φ·(S(tr) − S(t)), φ = INS_PHI (FEA: 0,31–0,35 con el rebaje bajo el barrido del cuerpo); retorno: el talón queda en la
      // esquina libre (sin la mesa detrás): S_ret de la FEA, casi independiente de t_ins; crece como S del empuje bajo t_ref
      const Sx = (t, tr) => insS(cal, tb, t) + (tr != null ? INS_PHI * (insS(cal, tb, tr) - insS(cal, tb, t)) : 0);
      const Sof = (id, t, tr) => id === "ret" ? cal.retS * (cal.retTb / tb) ** 2 * Math.max(1, Sx(t, tr) / insS(cal, tb, cal.retRef)) : Sx(t, tr);
      const evalT = (t, tr) => casos.map((q) => { const M = q.F * h / 1e3, sig = INS_KAPPA * q.k * M * Sof(q.id, t, tr); return Object.assign({}, q, { M, sig, fu: sig / Fb }); });
      const rowOf = (t) => {
        let L = vList(t, null), vc = vMin(L), pk = null;
        const viol = L.filter((x) => x.d < 5);
        if (viol.length && viol.every((x) => !x.propio)) {   // rebaje local de la cara superior bajo las piezas móviles que no dejan 5 mm (envolvente convexa por grupo)
          const tr = Math.min(...viol.map((x) => x.z)) - 5, groups = {};
          viol.forEach((x) => { (groups[x.grupo] = groups[x.grupo] || []).push(...x.poly); });
          if (tr >= tb + 5 && tr < t) { pk = { tr, depth: t - tr, polys: Object.keys(groups).map((k) => hull2(groups[k])), grupos: Object.keys(groups) }; L = vList(t, pk); vc = vMin(L); }
        }
        const ev = evalT(t, pk ? pk.tr : null);
        return { t, ev, fu: Math.max(...ev.map((q) => q.fu)), vc, pk, geoOk: vc.d >= 5 && t <= lugBot };
      };
      const rows = []; for (const t of cand) { const r = rowOf(t); rows.push(r); if (r.geoOk && r.fu <= INS_FUOBJ) break; }   // perezoso: hasta el primer espesor que llega al objetivo
      return { ok: true, gap, clr, c, cal, nx, ny, Vc, outline, fullOf, plan, dObst, rows,
        pick: rows.find((r) => r.geoOk && r.fu <= INS_FUOBJ) || rows.find((r) => r.geoOk && r.fu <= 1) || null,
        best: rows.filter((r) => r.geoOk).reduce((m, r) => (!m || r.fu < m.fu ? r : m), null) };
    };
    const vars = []; for (const cal of INS_CAL[mode]) { const v = variant(cal); vars.push(v); if (v.ok && v.pick && v.pick.fu <= INS_FUOBJ) break; }   // la primera variante que llega al objetivo corta la búsqueda
    const okv = vars.filter((v) => v.ok);
    if (!okv.length) return Object.assign({ mode, ok: false }, vars[0]);
    const V = okv.find((v) => v.pick && v.pick.fu <= INS_FUOBJ) || okv.find((v) => v.pick) || okv.reduce((m, v) => (v.best && (!m.best || v.best.fu < m.best.fu) ? v : m), okv[0]);
    const sel = V.pick || V.best || V.rows[0], { gap, clr, c, cal, nx, ny, Vc, outline, plan, dObst } = V;
    const t = sel.t, D = t - tb, full = V.fullOf(t), Aout = Math.abs(PG.area(outline)), Afull = Math.abs(PG.area(full));
    const legX = Math.max(0, ...Vc.filter((p) => Math.abs(p[0] - Bh) < 1e-6).map((p) => p[1] + Bh)), legY = Math.max(0, ...Vc.filter((p) => Math.abs(p[1] + Bh) < 1e-6).map((p) => Bh - p[0]));   // catetos sobre los bordes X = B/2 e Y = −B/2 (marco canónico)
    const mass = RHO * (Afull * D + (Aout - Afull) * D / 2);   // kg por inserto, masa añadida sobre la base de t_base (la transición es una cuña)
    const nIns = mode === 2 ? P.n_cyl : Math.max(2, Math.round(P.n_br));
    const reflect = (pl) => pl.map((p) => [p[0], -p[1]]).reverse();   // esquina (+x; +y) del mismo lado (modo 1, ménsula del otro sentido)
    const corners = [outline, outline.map((p) => [-p[0], -p[1]])].concat(nIns > 2 ? [reflect(outline), reflect(outline).map((p) => [-p[0], -p[1]])] : []);
    const fullCorners = [full, full.map((p) => [-p[0], -p[1]])].concat(nIns > 2 ? [reflect(full), reflect(full).map((p) => [-p[0], -p[1]])] : []);
    // bordes interiores (CJP con la base) y bordes sobre el borde de la base (sin junta)
    const edges = []; for (let i = 0; i < outline.length; i++) { const p = outline[i], q = outline[(i + 1) % outline.length], onB = (Math.abs(p[0] - q[0]) < 1e-6 && Math.abs(Math.abs(p[0]) - Bh) < 1e-6) || (Math.abs(p[1] - q[1]) < 1e-6 && Math.abs(Math.abs(p[1]) - Bh) < 1e-6); edges.push({ p, q, L: Math.hypot(q[0] - p[0], q[1] - p[1]), borde_base: onB }); }
    const Lcjp = edges.filter((e) => !e.borde_base).reduce((s, e) => s + e.L, 0);
    const fuB = Math.max(...sel.ev.map((q) => q.fu));
    const pk = sel.pk ? Object.assign({}, sel.pk, { polys: sel.pk.polys, polysAll: [].concat(...sel.pk.polys.map((pl) => [pl, pl.map((p) => [-p[0], -p[1]])])) }) : null;
    const mPk = pk ? RHO * pk.polys.reduce((a, pl) => a + Math.abs(PG.area(PG.clip(outline, pl))), 0) * pk.depth : 0;   // material quitado por el rebaje dentro del contorno (sin descontar el solape de los dos sentidos ni la transición: cota)
    return { mode, ok: true, t, t_base: tb, delta: D, gap, clr, c, hip_dist: c / Math.SQRT2, nx, ny, outline, full, corners, fullCorners, n: nIns, Aout, Afull, mass: mass - mPk, legX, legY, rebaje: pk, mRebaje: mPk,
      casos: sel.ev, fu: fuB, cumple: fuB <= 1 && sel.geoOk, geoOk: sel.geoOk, vClr: sel.vc, plan, obst: dObst.map((x) => ({ id: x.o.id, d: x.d })), Fvac, Fvac0, h, Fb, edges, Lcjp,
      zTop: tb + D, lugBot, slope: INS_SLOPE, kappa: INS_KAPPA, cal, variantes: vars.map((v) => ({ gap: v.gap, clr: v.clr, ok: v.ok, t: v.pick ? v.pick.t : null })),
      candidatos: V.rows.map((r) => ({ t: r.t, fu: r.fu, holgura_vertical: r.vc.d, asiento: r.t <= lugBot, rebaje: r.pk ? { z: r.pk.tr, profundidad: r.pk.depth } : null })) };
  }
  const REG_INS = "docs/normas/registro.md, «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)»; docs/qa/plancha_base_inserto.md";
  const LIM_USO_VACIA = { id: "atasco_mesa_vacia", texto: "No operar el accionamiento a presión de alivio con la mesa sin carga; ante un atasco sin carga, detener y liberar.",
    motivo: "El atasco a presión de alivio con la mesa vacía está EXCLUIDO como caso de diseño de la plancha base (decisión del mandante 10-11-2026, igual que KIET): sin la mesa cargada no hay retención y el par del soporte cruza la base como torsión. La plancha se verifica con la mesa cargada (hasta el calado) y con la mesa vacía a la fuerza de servicio.",
    alcance: "memoria de cálculo, manual de operación y planos (nota general)", referencia: REG_INS };
  const REF_FB = "ASME BTH-1-2020 §3-2.3.4 (flexión respecto del eje menor de barras y secciones rectangulares macizas: F_b = 1,25·Fy/Nd; número de ecuación: verificar)";
  const REF_CJP = "AISC 360-22 §J2.4, Tabla J2.5 (CJP: resistencia del metal base); AWS D1.1/D1.1M:2020 Figura 5.1 (junta precalificada a tope en doble V, B-U3: verificar designación), cláusula 4 (transición de espesores 1:2,5 en juntas a tope de partes de distinto espesor: verificar número de cláusula y figura)";
  // Filas del inserto (modo 2: grupo «Soporte del ojal E»; modo 1: «Articulaciones»). BP = franja del soporte (pivBasePlate / guidedBasePlate) para el corte y la retención.
  function insertRows(P, R, add, G, N, BP) {
    const I = cornerInsertOf(P, R); if (!I) return false;
    if (!I.ok) { add({ grp: G, sys: "est", kind: "geo", name: N + "inserto: geometría de la planta", formula: I.msg, dem: 1, cap: 0, unit: "–", ref: REG_INS }); return true; }
    const tb = I.t_base, Fb = I.Fb, Fy = P.Fy, Nd = P.Nd, quien = I.mode === 2 ? "soporte del ojal E" : "ménsula del ojal trasero", quienA = I.mode === 2 ? "el soporte del ojal E" : "la ménsula del ojal trasero";
    const cal = I.cal, rng = "t_base " + cal.tb[0] + "–" + cal.tb[cal.tb.length - 1] + " mm, t_inserto " + cal.ti[0] + "–" + cal.ti[cal.ti.length - 1] + " mm";
    add({ grp: G, sys: "est", kind: "info", name: N + "inserto: modelo, casos y calibración", formula: "Base de " + tb + " mm en toda la planta; bajo cada " + quien + " un inserto de " + I.t + " mm (" + I.n + " en total), al ras por debajo, cara superior " + nfx(I.delta, 0) + " mm más alta, CJP a tope con la base y transición 1:" + nfx(INS_SLOPE, 1) + " en la cara superior. Planta: triángulo de la esquina con la hipotenusa a D/2 + " + nfx(I.gap, 0) + " = " + nfx(I.hip_dist, 0) + " mm del centro, menos las muescas que dejan libres (" + nfx(I.clr, 0) + " mm de diseño) " + (I.mode === 2 ? "las placas-guía y la trayectoria del cubo y pasador Q" : "la banda del accionamiento guiado (bancada, prolongación, pórticos y patín)") + ". M = F·h con h = " + nfx(I.h, 0) + " mm (eje sobre la cara superior de la base: el roce de la mesa entra a z = t_base). σ = κ·M·S(t_base; t_inserto): S = σ/M de la FEA de Mindlin de la base completa del verificador independiente (tests/indep_plancha_base_E.py: mesa cargada como cuerpo rígido con contacto unilateral, losa unilateral, dos soportes rígidos con M₂ = −M₁, inserto con su transición; malla 40 mm; σ_vM a más de 100 mm de la huella rígida del soporte, fuera de la singularidad de su esquina), κ = " + nfx(INS_KAPPA, 2) + "; rango calibrado " + rng + " (fuera del rango, del lado seguro). Retorno: S_ret de la misma FEA (talón en la esquina, sin la mesa detrás). Mesa vacía en servicio: F = " + nfx(P.ins_fsv, 2) + "·máx(F_dis; F_borde; F_cont)·W_d/N = " + nfx(I.Fvac, 2) + " kN (μ de diseño y contaminado, contacto en el borde; × " + nfx(P.ins_fsv, 2) + " = FS de giro del proyecto como margen de arranque), factor " + nfx(cal.vac, 2) + " sobre S (FEA con la mesa vacía hasta 30 kN). Atasco a presión de alivio con la mesa vacía: EXCLUIDO (limitación de uso). Caso térmico: no aplica (F de las presiones de alivio y de retorno; la base queda a la sombra)", dem: I.t, cap: I.delta, unit: "mm (t_inserto / Δ sobre la base)", ref: REF_FB + "; " + REG_INS });
    I.casos.forEach((q) => add({ grp: G, sys: "est", name: N + "inserto de " + I.t + " mm sobre la base de " + tb + " mm, flexión con la " + q.nombre, formula: "σ = κ·M·S ≤ 1,25·Fy/Nd; F = " + nfx(q.F, 2) + " kN, M = F·h = " + nfx(q.M, 2) + " kN·m" + (q.id === "ret" ? ", S_ret" : "") + (q.k !== 1 ? ", factor " + nfx(q.k, 2) : "") + "; σ fuera de la singularidad de la huella rígida (> 100 mm)", dem: q.sig, cap: Fb, unit: "MPa", ref: REF_FB + "; " + REG_INS }));
    const be = BP.empuje, Mc = R.Fstall * 1e3 * I.h, tau = 1.5 * (Mc / be.a) / (be.b * I.t);
    add({ grp: G, sys: "est", name: N + "inserto: corte bajo " + quienA + " (empuje a calado)", formula: "τ = 1,5·V/(b·t_inserto) ≤ Fy/(Nd·√3), V = M/a = " + nfx(Mc / be.a / 1e3) + " kN (cota superior), a = " + nfx(be.a, 0) + " mm, b = " + nfx(be.b, 0) + " mm", dem: tau, cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1-2020 §3-2.3.6; " + REG_INS });
    const fuJ = Math.max(...I.casos.map((q) => q.fu));
    add({ grp: G, sys: "est", name: N + "inserto: CJP inserto–base (J-I1, a tope, " + nfx(I.Lcjp, 0) + " mm por inserto) en la línea de la junta", formula: "La CJP desarrolla el metal base de la parte más delgada (t_base = " + tb + " mm): FU = σ/(1,25·Fy/Nd) con la tensión máxima de las filas de flexión (cota: la tensión en la junta no la supera)", dem: fuJ * Fb, cap: Fb, unit: "MPa", ref: REF_CJP });
    add({ grp: G, sys: "est", kind: "info", name: N + "inserto: transición de espesor en la cara superior", formula: "Bisel 1:" + nfx(INS_SLOPE, 1) + " en el inserto a lo largo de los bordes interiores (ancho " + nfx(INS_SLOPE * I.delta, 0) + " mm); la cara inferior queda al ras. La tensión de flexión en la junta supera 1/3 de la admisible: se aplica la transición (conservador; ver cita)", dem: INS_SLOPE * I.delta, unit: "mm (ancho de la transición)", ref: REF_CJP });
    add({ grp: G, sys: "est", kind: "geo", name: N + "inserto: holgura en planta a las piezas apoyadas en la base", formula: "mín dist(" + (I.plan.o ? I.plan.o.id : "—") + "; contorno del inserto) ≥ 5 mm (muesca con " + nfx(I.clr, 0) + " mm de diseño)", dem: 5, cap: I.plan.d, unit: "mm", ref: "Geometría; " + REG_INS });
    add({ grp: G, sys: "est", kind: "geo", name: N + "inserto: holgura vertical a las piezas que pasan por encima", formula: "z_inferior − z_cara del inserto ≥ 5 mm (sobre la transición la cara está a t − d/" + nfx(INS_SLOPE, 1) + "); mínimo: " + (I.vClr.id || "—") + " a z = " + nfx(I.vClr.z, 0) + " sobre la cara a " + nfx(I.vClr.top, 0), dem: 5, cap: I.vClr.d, unit: "mm", ref: "Geometría; " + REG_INS });
    add({ grp: G, sys: "est", kind: "geo", name: N + "inserto: holgura a la mesa (hipotenusa fuera de R = D/2)", formula: "dist(hipotenusa; O) − D/2 = ins_gap ≥ 5 mm", dem: 5, cap: I.hip_dist - P.D_top / 2, unit: "mm", ref: "Geometría; " + REG_INS });
    add({ grp: G, sys: "est", kind: "geo", name: N + "inserto: " + (I.mode === 2 ? "la tapa inferior del ojal E queda sobre el inserto" : "el suplemento bajo la oreja inferior de la ménsula alcanza para el inserto"), formula: (I.mode === 2 ? "t_inserto ≤ z inferior de la tapa inferior" : "t_inserto ≤ t_base + suplemento (el suplemento y las mejillas se acortan Δ)"), dem: I.t, cap: I.lugBot, unit: "mm", ref: "Geometría; " + REG_INS });
    const Fv = I.Fvac, Mv = Fv * 1e3 * I.h, Tv = P.n_cyl * (be.ret ? Mv / be.sH : Infinity), Wv = BP.mesaVacia.W;
    add({ grp: G, sys: "est", name: N + "retención con la mesa vacía en servicio (sin anclaje)", formula: "n_cil·M/s_H ≤ W_mesa (peso propio de la parte que gira); M = F_servicio·h = " + nfx(Mv / 1e6, 3) + " kN·m, s_H = " + nfx(be.sH, 0) + " mm", dem: Tv / 1e3, cap: Wv / 1e3, unit: "kN", ref: "Equilibrio; " + REG_INS });
    add({ grp: G, sys: "est", kind: "info", name: N + "limitación de uso: atasco a presión de alivio con la mesa vacía EXCLUIDO como caso de diseño", formula: LIM_USO_VACIA.texto + " " + LIM_USO_VACIA.motivo, dem: R.Fstall, cap: Fv, unit: "kN (calado excluido / servicio verificado)", ref: REG_INS });
    return true;
  }
  function insertExport(P, R) {
    const I = cornerInsertOf(P, R); if (!I) return null;
    if (!I.ok) return { estado: "NO CUMPLE: " + I.msg, referencia: REG_INS };
    const r2 = (pl) => pl.map((p) => [p[0], p[1]]), norma = REF_FB;
    const juntas = [{ id: "J-I1", piezas: ["inserto", "base"], tipo: "CJP a tope en doble V (soldada desde arriba; la base se voltea en taller: resanado de raíz y soldadura por la cara inferior, amolada al ras) con transición 1:2,5 en la cara superior del inserto",
      tamano: { CJP: I.t_base, transicion_ancho: INS_SLOPE * I.delta, transicion_pendiente: "1:2,5" }, largo: I.Lcjp, largo_total: I.n * I.Lcjp,
      verificacion: { fu: Math.max(...I.casos.map((q) => q.fu)), norma: REF_CJP + "; " + norma } }];
    const secuencia = [
      "1. Oxicorte de la base de " + I.t_base + " mm con las " + I.n + " ventanas del inserto (contorno «esquinas»; los bordes sobre el borde de la base no llevan junta).",
      "2. Oxicorte de los insertos de " + I.t + " mm; bisel de la transición 1:2,5 en la cara superior a lo largo de los bordes interiores (ancho " + nfx(INS_SLOPE * I.delta, 0) + " mm, hasta el contorno «espesor pleno») y biseles de la CJP en doble V.",
      "3. Presentar base e insertos sobre mesa plana, al ras por la cara inferior; punteo con separación de raíz según la junta precalificada.",
      "4. CJP J-I1 por la cara superior; voltear, resanar la raíz y soldar por la cara inferior; amolar al ras la cara inferior (apoyo en la losa).",
      "5. Inspección: VT 100 % y UT 100 % de J-I1 (AWS D1.1/D1.1M:2020, cláusula 8); control de planitud de la base.",
      ...(I.rebaje ? ["5b. Rebaje local de la cara superior a z = " + nfx(I.rebaje.tr, 0) + " (" + nfx(I.rebaje.depth, 0) + " mm) bajo el barrido de: " + I.rebaje.grupos.join(", ") + " (fresado o cepillado, borde a 1:2,5)."] : []),
      "6. Marco perimetral interrumpido a lo largo de los catetos del inserto (hasta 50 mm más allá de su extremo): el marco no cumple función resistente.",
      "7. " + (I.mode === 2 ? "Soporte del ojal E (paredes, muñones y tapas) y oreja de izaje de la diagonal soldados sobre el inserto (las paredes y la oreja arrancan en z = " + I.t + ")" : "Mejillas de la ménsula, suplemento y oreja de izaje de la diagonal soldados sobre el inserto (mejillas y suplemento " + nfx(I.delta, 0) + " mm más cortos)") + "; después, el resto del accionamiento.",
    ];
    const casos = I.casos.map((q) => ({ id: q.id, caso: q.nombre, F_kN: q.F, h: I.h, M_kNm: q.M, sigma: q.sig, cap: I.Fb, fu: q.fu, norma }));
    const out = { estado: I.cumple ? "cumple" : "NO CUMPLE", t: I.t, t_base: I.t_base, delta: I.delta, z: [0, I.t], material: "S355J2 (EN 10025-2), Fy " + P.Fy + " MPa", n: I.n,
      catetos: [I.legX, I.legY], hipotenusa_dist_centro: I.hip_dist, holgura_mesa: I.hip_dist - P.D_top / 2, holgura_diseno_muescas: I.clr,
      muescas: { lado_x: I.nx, lado_y: I.ny, marco: "canónico de la esquina (+B/2; −B/2); real = (s_x·X, −s_y·Y)" },
      esquinas: I.corners.map(r2), esquinas_espesor_pleno: I.fullCorners.map(r2), poligono: I.mode === 2 ? { cilindro1: r2(I.corners[0]), cilindro2: r2(I.corners[1]) } : { esquinas: I.corners.map(r2) },
      transicion: { cara: "superior", pendiente: "1:2,5", ancho: INS_SLOPE * I.delta, norma: REF_CJP },
      rebaje: I.rebaje ? { z_cara: I.rebaje.tr, profundidad: I.rebaje.depth, bajo: I.rebaje.grupos, poligonos: I.rebaje.polysAll.map(r2), borde: "pendiente 1:2,5 fuera del polígono", masa_quitada: I.mRebaje, nota: "rebaje local de la cara superior del inserto bajo el barrido de las piezas móviles que no dejan 5 mm sobre el espesor pleno (envolvente convexa del barrido de cada pieza y sentido, cilindro 1 y su rotación de 180°); se mecaniza después de soldar J-I1" } : null,
      casos, fu_max: Math.max(...I.casos.map((q) => q.fu)), Fb: I.Fb,
      holguras: { planta: I.plan.d, planta_a: I.plan.o ? I.plan.o.id : null, vertical: I.vClr.d, vertical_a: I.vClr.id, mesa: I.hip_dist - P.D_top / 2, asiento: { t: I.t, z_max: I.lugBot }, exigida: 5 },
      juntas, secuencia, masa: I.mass, masa_total: I.n * I.mass,
      marco_interrupcion: { largo_desde_la_esquina: [I.legX + 50, I.legY + 50], nota: "el marco perimetral se interrumpe a lo largo de los dos catetos de cada inserto hasta 50 mm más allá de su extremo" },
      candidatos: I.candidatos, modelo: { S_tabla: I.cal, kappa: INS_KAPPA, criterio: "σ_vM a más de 100 mm de la huella rígida del soporte (verificación independiente)", fea: "tests/indep_plancha_base_E.py" },
      limitaciones_uso: [LIM_USO_VACIA], referencia: REG_INS };
    return out;
  }
  const REG_BPG = "docs/normas/registro.md, «Plancha base bajo la ménsula del ojal trasero (modo guiado, 10-11-2026)»; docs/qa/plancha_base_modo_guiado.md";
  function guidedBasePlateRows(P, R, add) {
    const BP = guidedBasePlate(P, R), be = BP.empuje, br = BP.retorno, tq = BP.torsion, Fy = P.Fy, Nd = P.Nd, Fa = INS_FB * Fy / Nd, G = "Articulaciones", N = "Plancha base bajo la ménsula del ojal trasero: ";
    if (insertRows(P, R, add, G, N, BP)) {   // base con inserto bajo las ménsulas: torsión de la base entre las ménsulas con la mesa vacía en servicio (cota inferior)
      const I = cornerInsertOf(P, R), Mv = I.ok ? I.Fvac * 1e3 * I.h : 0, mv = Mv / (2 * P.B), tv = 6 * mv / (P.t_base * P.t_base);
      add({ grp: G, sys: "est", name: N + "torsión de la base entre las dos ménsulas con la mesa vacía en servicio (cota inferior, placa libre)", formula: "m_xy ≈ M/(2·B), M = F_servicio·h = " + nfx(Mv / 1e6, 3) + " kN·m; τ = 6·m_xy/t_base² ≤ Fy/(Nd·√3) (cota inferior; la FEA de calibración con la mesa vacía da el reparto real)", dem: tv, cap: tq.cap, unit: "MPa", ref: "ASME BTH-1-2020 §3-2.3.6; " + REG_INS });
      return;
    }
    add({ grp: G, sys: "est", kind: "info", name: N + "modelo de la transferencia de carga y casos", formula: "Ménsula (dos mejillas de " + P.t_ch + " × " + P.L_ch + " mm soldadas a la plancha de " + P.t_base + " mm) con el ojal en (x_g; y_ojal) = (" + nfx(BP.ojal[0], 0) + "; " + nfx(BP.ojal[1], 0) + "); F a la altura del eje h = " + nfx(be.h, 0) + " mm sobre la plancha, M = F·h alrededor de x. Empuje a calado (F = " + nfx(be.F / 1e3) + " kN, M = " + nfx(be.M / 1e6, 2) + " kN·m): la reacción la da la mesa (roce de la interfaz y el otro cilindro, a 180°), no la bancada; con los dos cilindros M₂ = −M₁ y el par cruza la base como torsión. Retorno (F_ret = A_anular·p_ret = " + nfx(br.F / 1e3) + " kN, M = " + nfx(br.M / 1e6, 2) + " kN·m): con la uña trabada en la rampa la reacción está en los pórticos del riel-leva, sobre la misma bancada (se cierra en la franja); a nivel de toma la toma la mesa. Losa rígida solo a compresión; anclaje no definido en el proyecto. Caso térmico: no aplica (F sale de las presiones de alivio y de retorno). La interfaz B (eje más alto) gobierna", dem: be.M / 1e6, cap: br.M / 1e6, unit: "kN·m (empuje / retorno)", ref: REG_BPG });
    add({ grp: G, sys: "est", stFix: "pend", name: N + "flexión sin anclaje, empuje a calado — NO CUMPLE sin anclaje a la losa (PENDIENTE: decisión del mandante)", formula: "σ = 6·M_corte/(b·t²) ≤ 1,25·Fy/Nd; M_corte = M·(1 − a/s_H) en la línea del talón (extremo delantero de las mejillas) con la retención en el borde más lejano de la mesa (s_H = " + nfx(be.sH, 0) + " mm), a = L_mejilla = " + nfx(be.a, 0) + " mm, b = w + a = " + nfx(be.b, 0) + " mm; M_corte = " + nfx(be.M / 1e6 * (1 - be.a / be.sH), 2) + " kN·m. Modelo de un soporte (no cuenta la bancada, que queda a " + nfx(Math.max(0, -R.K.Y_bed - P.cam_ls * (R.camG ? 1 : 0) - (BP.ojal[1] + BP.walls[0][3])), 0) + " mm de las mejillas); la FEA de la base completa da otro reparto (estudio)", dem: be.sig, cap: Fa, unit: "MPa", ref: REF_FB + "; " + REG_BPG });
    add({ grp: G, sys: "est", stFix: "pend", name: N + "flexión sin anclaje, retorno (atasco) — sin retención detrás del talón (PENDIENTE: anclaje)", formula: "σ = 6·M/(b·t²) ≤ 1,25·Fy/Nd: la mesa queda delante del pie (s_H = " + nfx(br.sH, 0) + " mm ≤ a = " + nfx(br.a, 0) + " mm) y toda la M cruza la línea del pie; b = " + nfx(br.b, 0) + " mm", dem: br.sig, cap: Fa, unit: "MPa", ref: REF_FB + "; " + REG_BPG });
    add({ grp: G, sys: "est", name: N + "corte de la franja (empuje a calado)", formula: "τ = 1,5·V/(b·t) ≤ Fy/(Nd·√3), V = M/a = " + nfx(be.Vs / 1e3) + " kN (cota superior)", dem: be.tau, cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6; " + REG_BPG });
    add({ grp: G, sys: "est", stFix: "pend", name: N + "torsión de la base entre las dos ménsulas (dos cilindros a calado, mesa vacía) — cota inferior, NO CUMPLE sin anclaje ni base rígida (PENDIENTE)", formula: "M₂ = −M₁ en (x_g; y_ojal) y (−x_g; −y_ojal): fuerza de esquina ≈ M/B = " + nfx(tq.Vc / 1e3) + " kN (las esquinas libres suben), m_xy ≈ M/(2·B) = " + nfx(tq.mxy / 1e3, 2) + " kN·m/m; τ = 6·m_xy/t² ≤ Fy/(Nd·√3) para la placa libre en torsión pura (cota inferior: la bancada es una sección abierta y no da rigidez a torsión; la FEA de la base completa con contacto unilateral da más)", dem: tq.tau, cap: tq.cap, unit: "MPa", ref: "ASME BTH-1 §3-2.3.6; " + REG_BPG });
    add({ grp: G, sys: "est", kind: "pend", name: N + "levantamiento — anclaje a la losa no definido en el proyecto (PENDIENTE: anclaje y datos de la losa: f'c, espesor, armadura, bordes)", formula: "Con los dos cilindros M₂ = −M₁: la base no vuelca como cuerpo libre, pero el par llega de una ménsula a la otra por torsión de la base, que la plancha de " + P.t_base + " mm y las bancadas (secciones abiertas) no tienen. Con la mesa vacía (el calado no depende de la carga) la retención disponible es su peso propio, " + nfx(BP.mesaVacia.W / 1e3) + " kN, " + (BP.mesaVacia.ok ? "≥" : "<") + " " + nfx(BP.mesaVacia.Treq / 1e3) + " kN que piden las " + P.n_cyl + " ménsulas (cota del modelo de un soporte): la base queda apoyada en pocos puntos y las esquinas libres suben (FEA del estudio). Momento a anclar por ménsula: empuje " + nfx(be.M / 1e6, 2) + " kN·m, retorno " + nfx(br.M / 1e6, 2) + " kN·m", dem: be.M / 1e6, unit: "kN·m", ref: REG_BPG });
  }
  function pivFat(P, R, Fd) {
    const F = Fd * 1e3, sg = R.sup, L = pivSupLoads(P, sg, F);
    const m = pivPinM(P, R, F, P.mu_s * F);
    return { blk: F / (P.pv_bu * P.pv_hu) + 6 * F * R.blk.ecBody / (P.pv_hu * P.pv_bu ** 2), pin: Math.max(m.MQ / (Math.PI * P.pv_dq ** 3 / 32), m.ME / (Math.PI * P.pv_dE ** 3 / 32)),
      toe: L.sig, thr: L.pjp };
  }
  function pivGiroRows(P, R, add) {
    const K = R.K, CP = R.camP, G = "Giro", Bh = P.B / 2 - P.rim_t - 5, fam = R.fam;
    if (!K.ok) { add({ grp: G, sys: "giro", kind: "geo", name: "Accionamiento pivotado: geometría sin posición de toma", formula: K.msg || "|P − E| = L0 + s_libre + L_qp sin solución", dem: 1, cap: 0, unit: "–", ref: REG_PV }); return; }
    add({ grp: G, sys: "giro", kind: "info", name: "Pivotado: brazo mínimo geométrico a = dist(O, E–P) y brazo efectivo con el roce del contacto a − μ_s·|v_s|", formula: "a(θ) = (P × u)_z = dL/dθ; a_ef = a − μ_s·|v_s|, v_s = −r(1 − dψ/dθ), dψ/dθ = (P·u)/|P − E| (potencia virtual); E = (" + nfx(K.E[0], 0) + "; " + nfx(K.E[1], 0) + "), L_qp = " + nfx(K.Lqp, 0) + " mm", dem: K.aMin, cap: K.aEffMin, unit: "mm (geométrico / efectivo)", ref: REG_PV });
    const sg = K.sugerencia || suggestE(P);
    add({ grp: G, sys: "giro", kind: "info", name: "Pivotado: sugerencia automática de E (máximo brazo efectivo mínimo respetando base, L0, carrera, mesa y pasador siguiente)", formula: "R_E = " + nfx(sg.RE, 0) + " mm, L_qp = " + nfx(sg.Lqp, 0) + " mm (dem = brazo efectivo sugerido; cap = brazo efectivo con los valores ingresados)", dem: sg.aEffMin, cap: K.aEffMin, unit: "mm", ref: REG_PV });
    add({ grp: G, sys: "giro", kind: "geo", name: "Pasador Q fuera de la mesa en toda la carrera (la placa-leva va sobre la base)", formula: "D/2 + d_Q/2 + holgura ≤ mín |Q(θ)|", dem: P.D_top / 2 + P.pv_dq / 2 + P.pv_cQ, cap: K.QrMin, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Holgura cilindro–mesa a lo largo de la carrera (cuerpo del cilindro fuera de la mesa)", formula: "D/2 + D_cuerpo/2 + holgura ≤ mín dist(O, eje del cuerpo entre E + e_cuerpo y E + L0 − c_vástago)", dem: P.D_top / 2 + P.D_body / 2 + P.pv_cc, cap: K.body + P.D_body / 2 + P.D_top / 2, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Bloque-uña libre del pasador siguiente durante el empuje", formula: "holgura mínima (cuerpo acodado, tramo de la cara y cubo de Q frente al pasador anterior y al siguiente) ≥ holgura mínima", dem: P.pv_cB, cap: K.clrB, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Soporte del ojal E dentro de la base", formula: "máx(|E_x|; |E_y|) + lado del cajón/2 ≤ B/2 − t_marco − 5", dem: K.eBox, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
    add({ grp: G, sys: "giro", kind: "geo", name: "Bloque-uña dentro de la luz libre entre anillos", formula: "h_bloque + 10 ≤ h − 2·t_anillo", dem: P.pv_hu + 10, cap: pinClear(P), unit: "mm", ref: "Geometría (alzado)" });
    if (R.blk) add({ grp: G, sys: "giro", kind: "geo", name: "Bloque-uña sobre la placa-leva", formula: "t_base + t_leva + 2 ≤ z_eje − h_bloque/2", dem: P.t_base + P.pv_tcam + 2, cap: R.blk.zBot, unit: "mm", ref: "Geometría (alzado)" });
    if (R.sup && R.sup.clr && isFinite(R.sup.clr.d)) { const cl = R.sup.clr; add({ grp: G, sys: "giro", kind: "geo", name: "Cuerpo del cilindro libre del soporte del ojal E (tapas recortadas en nariz, paredes traseras y muñones) en todo el empuje y el retorno, ambos sentidos", formula: "mín dist(huella del cuerpo Ø" + P.D_body + " desde E + e_cuerpo hasta E + L0 − c_vástago; piezas del soporte que comparten cota z con el cuerpo) ≥ 5 mm; " + (cl.sentido || "") + ", " + (cl.fase || "") + " (" + R.sup.sweep.estados.length + " estados por sentido; el cilindro 2 por rotación de 180°)", dem: 5, cap: cl.d, unit: "mm", ref: "Geometría (planta y alzado); docs/normas/registro.md, «Soporte del ojal E: cajón abierto (10-11-2026)»" }); }
    if (R.sup) add({ grp: G, sys: "giro", kind: "geo", name: "Oreja inferior del ojal E sobre la base", formula: "t_base ≤ z_eje − b_ojal/2 − g − t_oreja", dem: P.t_base, cap: R.sup.zLugBot, unit: "mm", ref: "Geometría (alzado)" });
    if (CP && CP.guia) {
      const g = CP.guia, rf = P.pv_dq / 2, lr = g.lockR, phiLim = 90 - Math.atan(fam.mu) / D2R, gp = CP.push.filter((q) => q.ok);
      add({ grp: G, sys: "giro", kind: "geo", name: "Sincronía del retorno: holgura bloque-uña–pasador siguiente con Q contra el canto de la placa-guía (nominal, en toda la conducción final)", formula: "mín holgura(bloque alineado con el vástago, Q en W(L)) ≥ m + δ, L0 ≤ L ≤ L₁ (primer contacto); δ = tolerancia de posición " + nfx(P.pv_tolg, 2) + " + α·ΔT·R_pin " + nfx(g.dT, 2) + " mm (mesa a 80 °C)", dem: P.pv_msync + g.dTol, cap: CP.sync, unit: "mm", ref: REG_PV + "; geometría (polígono del bloque frente al círculo del pasador)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Sincronía en el peor caso (canto en el extremo de su tolerancia y mesa a 80 °C)", formula: "holgura nominal − δ ≥ m", dem: P.pv_msync, cap: g.syncWorst, unit: "mm", ref: REG_PV });
      add({ grp: G, sys: "giro", kind: "geo", name: "Flanco de reenganche: ángulo de presión máximo en la conducción final ≤ α_máx" + (g.flanco.limitado ? " (el flanco quedó limitado: la sincronía no cumple)" : ""), formula: "φ = ángulo entre el canto y la recta radial E–Q; flanco recto por (L0 + tramo, c) tangente por arriba a w_nec(m + δ): φ_req = " + nfx(g.flanco.phi_req_deg, 1) + "°", dem: g.phiRetMax, cap: P.pv_alpha, unit: "°", ref: REG_PV });
      add({ grp: G, sys: "giro", name: "Placa-guía sin autobloqueo en toda la conducción del retorno (" + fam.corto + ", μ = " + nfx(fam.mu, 2) + "; peor punto L = " + nfx(lr.L, 1) + " mm, φ = " + nfx(lr.phi, 1) + "°)", formula: "μ_E·d_E/(2·L0)·(sen φ + μ·cos φ) < cos φ − μ·sen φ en cada punto del canto que conduce a Q (el par que hace girar el cilindro en E vence el roce del pasador E)", dem: lr.dem, cap: lr.cap, unit: "–", ref: REG_PV + "; equilibrio con fricción" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Empuje con Q apoyado en el canto: ángulo de presión máximo bajo el de autobloqueo", formula: "φ_empuje = ∠(canto, E–Q) ≤ 90° − atan μ_leva en las 61 posiciones (la rodilla E–Q–P se abre hacia afuera y Q recorre el canto)", dem: Math.max(...gp.map((q) => q.phi)), cap: phiLim, unit: "°", ref: REG_PV + "; equilibrio del pasador Q" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Empuje con Q apoyado en el canto: reacción de la guía positiva en todas las posiciones (Q no se despega hacia la mesa)", formula: "h = H/F ≥ 0,005 con F·u_c + H·(n − μ·t) = F_n·b' (b' girada r·sen(atan μ_s)/L_qp hacia la mesa)", dem: 0.005, cap: Math.min(...gp.map((q) => q.h)), unit: "–", ref: REG_PV });
      add({ grp: G, sys: "giro", kind: "info", name: "Empuje guiado: fuerza del cilindro frente a la cinemática colineal E–Q–P (máximo en la carrera)", formula: "F_guiado/F_colineal; la fuerza de diseño y el FS usan el empuje guiado", dem: CP.ratioMax, unit: "–", ref: REG_PV });
      add({ grp: G, sys: "giro", kind: "geo", name: "Canto de la placa-guía: continuidad G1 (máximo quiebre de tangente en los empalmes)", formula: "|∠(t_fin del tramo i; t_inicio del tramo i+1)| ≤ 0,01°; arcos del canto concéntricos con los de la trayectoria del centro (radio ± d_Q/2)", dem: g.g1Max / D2R, cap: 0.01, unit: "°", ref: REG_PV + "; geometría" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Canto de la placa-guía: radio convexo mínimo sin socavado", formula: "R_canto = R_centro − d_Q/2 ≥ R_mín (R_centro ≥ d_Q/2 + R_mín); cóncavo mínimo " + nfx(g.rCanto.concavo, 1) + " mm; salto máximo de curvatura " + nfx(g.dKappa * 1e3, 2) + "×10⁻³ 1/mm", dem: P.pv_rmin, cap: g.rCanto.convexo, unit: "mm", ref: REG_PV + "; geometría" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placa-guía libre del seguidor en todo el recorrido (sin invasión del círculo d_Q/2)", formula: "mín dist(centro del seguidor, contorno de la placa) − d_Q/2 ≥ −0,001 (= 0 en el contacto)", dem: 0.001, cap: g.folClr + 0.002, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Bloque-uña libre de los pasadores en el empuje guiado (Q en el canto, bloque alineado con Q–P y girado hacia afuera el ángulo de equilibrio con roce)", formula: "holgura mínima (cuerpo acodado, cara y cubo de Q frente al pasador anterior y al siguiente) ≥ holgura mínima; giro de equilibrio δ = asin((R_cara + r)·sen γ/L_qp)", dem: P.pv_cB, cap: Math.min(...gp.map((q) => q.clrB)), unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Cuerpo del cilindro fuera de la mesa en el empuje guiado", formula: "D/2 + D_cuerpo/2 + holgura ≤ mín dist(O, eje del cuerpo)", dem: P.D_top / 2 + P.D_body / 2 + P.pv_cc, cap: Math.min(...gp.map((q) => q.body)) + P.D_body / 2 + P.D_top / 2, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía dentro de la base", formula: "máx(|x|; |y|) del contorno ≤ B/2 − t_marco − 5", dem: CP.inBase, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía fuera de la mesa (la mesa apoya en la base hasta R = D/2)", formula: "D/2 + holgura ≤ mín |contorno|", dem: P.D_top / 2 + P.pv_cQ, cap: CP.Rin, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía libres del cajón del ojal E", formula: "mín distancia de Chebyshev del contorno a E − lado/2 ≥ 5 mm", dem: 5, cap: CP.boxClr, unit: "mm", ref: "Geometría (planta)" });
      const BC = baseClearOf(P, R), wTxt = (o) => (o && o.who ? " (mínimo: " + o.who.join(" – ") + ")" : "");
      if (BC.plateEar) add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía libres de las orejas de izaje (4 placas con sus reflexiones y rotaciones frente a las 4 orejas con sus filetes)", formula: "mín dist(contorno de la placa; huella de la oreja 2R × (t + 2w), radial) ≥ 5 mm" + wTxt(BC.plateEar), dem: 5, cap: BC.plateEar.d, unit: "mm", ref: "Geometría (planta)" });
      if (BC.plateSup) add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía libres de los demás elementos fijos sobre la base (piezas reales de los soportes del ojal E, mesa con la interfaz y sus topes)", formula: "mín dist(contorno de la placa; paredes, muñones y tapas de los soportes E; círculo R = D/2 de la mesa y la interfaz) ≥ 5 mm" + wTxt(BC.plateSup.d < BC.plateMesa.d ? BC.plateSup : BC.plateMesa), dem: 5, cap: Math.min(BC.plateSup.d, BC.plateMesa.d), unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-guía de ambos sentidos de giro a cada lado de la diagonal (no se solapan)", formula: "distancia mínima del contorno a la diagonal O–E ≥ 5 mm", dem: 5, cap: CP.diag, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Cuerpo del cilindro sobre la placa-guía (alzado)", formula: "t_base + t_placa + 5 ≤ z_eje − D_cuerpo/2", dem: P.t_base + P.pv_tcam + 5, cap: g.zCuerpo, unit: "mm", ref: "Geometría (alzado)" });
      add({ grp: G, sys: "giro", kind: "info", name: "Placa-guía: profundidad del bolsillo (máx W) y fracción del empuje con Q a ≤ c + 0,5 mm de la recta colineal", formula: "W(L) = trayectoria del centro del seguidor; la rodilla apoya Q en el canto en todo el empuje", dem: CP.wPk, cap: CP.cover, unit: "mm / –", ref: REG_PV });
    }
    add({ grp: G, sys: "giro", kind: "info", name: "Ojal comercial del vástago sobre el pasador Q y ojal trasero sobre el pasador E: admitir pasador y carga (pandeo del cilindro biarticulado: dato del proveedor)", formula: "Ø ojal ≥ d_Q, d_E; la fila de pandeo usa solo el vástago (L0 + carrera): confirmar con la ficha del cilindro", dem: P.pv_dq, cap: P.pv_dE, unit: "mm", ref: "Ficha del fabricante; ISO/TS 13725" });
  }
  function pivRows(P, R, add) {
    const K = R.K, CP = R.camP, bk = R.blk, sg = R.sup, fam = R.fam, Nd = P.Nd, Fy = P.Fy, Fs = R.Fstall * 1e3, Fw = P.FEXX * 0.60 / (1.20 * Nd);
    if (!K.ok || !CP || !bk || !sg) return;
    const UN = "Uña", AR = "Articulaciones", SO = "Soporte del ojal E", PL = "Placas-leva", Ncam = CP.Ncam;
    // bloque-uña
    const bu = P.pv_bu, hu = P.pv_hu, bf = P.pv_bf, ec = bk.ecBody;
    add({ grp: UN, sys: "est", name: "Bloque-uña: compresión + flexión en el cuerpo acodado (a calado)", formula: "σ = F/(b·h) + 6F·(e_cr + e + e_c·s₁/s₂)/(h·b²) ≤ Fy/Nd; e_c = " + nfx(bk.ec) + " mm (contacto desplazado por el roce: la resultante pasa por Q y por el contacto); F = F_calado, b = " + bu + ", h = " + hu + " mm", dem: Fs / (bu * hu) + 6 * Fs * ec / (hu * bu * bu), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1 y §3-2.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: compresión + flexión en el tramo de la cara", formula: "σ = F/(b_f·h) + 6F·(e + e_c)/(h·b_f²) ≤ Fy/Nd", dem: Fs / (bf * hu) + 6 * Fs * bk.ecFace / (hu * bf * bf), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1 y §3-2.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: corte por la fuerza transversal del roce en la cara", formula: "τ = 1,5·μ_s·F/(b·h) ≤ Fy/(Nd·√3)", dem: 1.5 * P.mu_s * Fs / (bu * hu), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    const Iu = hu * bu ** 3 / 12, Pcr = Math.PI ** 2 * P.E * Iu / (K.Lqp ** 2);
    add({ grp: UN, sys: "est", name: "Bloque-uña: pandeo en planta (biarticulado entre Q y el contacto)", formula: "F_calado ≤ Pcr/Nd; Pcr = π²·E·(h·b³/12)/L_qp²", dem: Fs / 1e3, cap: Pcr / Nd / 1e3, unit: "kN", ref: "Euler; factor Nd de ASME BTH-1 Cat. B" });
    const Es = P.E / (2 * (1 - P.nu ** 2)), qE = P.k_edge * Fs / hu, Ref = 1 / (2 / P.d_pin + (bk.Rf > 0 ? 1 / bk.Rf : 0)), p0 = Math.sqrt(qE * Es / (Math.PI * Ref)), bH = Math.sqrt(4 * qE * Ref / (Math.PI * Es));
    add({ grp: UN, sys: "est", name: "Bloque-uña: contacto de Hertz cara–pasador (a calado; ambas caras templadas" + (bk.Rf > 0 ? "; cara convexa R " + nfx(bk.Rf, 0) + " mm" : "") + ")", formula: "p₀ = √(q·E*/(π·R_ef)), 1/R_ef = 1/r + 1/R_cara, q = k_borde·F/h_bloque ≤ 1,67·Fy_sup", dem: p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: "Hertz, contacto lineal; inicio de fluencia por Tresca (p₀ = 1,67σy)" });
    add({ grp: UN, sys: "est", kind: "geo", name: "Bloque-uña: contacto dentro de la cara (con el roce de la cara μ_s y el del pasador Q, ambos sentidos)", formula: (bk.Rf > 0 ? "cara convexa: e_c = R·sen γ, sen γ = (s₂·sen ρ + μ_Q·d_Q/2)/(s₂ − R)" : "cara plana: e_c = s₂·tan ρ + μ_Q·d_Q/2") + ", ρ = atan μ_s; e_c + b_Hertz ≤ b_f/2 − 3 (chaflán de la arista); γ = " + nfx(bk.gam / D2R, 1) + "°, giro del bloque " + nfx(bk.dBlk / D2R, 1) + "°", dem: bk.ec + bH, cap: P.pv_bf / 2 - 3, unit: "mm", ref: "Equilibrio del bloque libre en Q (miembro de dos fuerzas con roce); Hertz (semiancho b)" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: aplastamiento de la horquilla en el pasador Q", formula: "σ = (F/2)/(d_Q·t_h) ≤ 1,25·Fy/Nd; t_h = (h_bloque − b_ojal − 2g)/2 = " + nfx(bk.tq) + " mm", dem: Fs / 2 / (P.pv_dq * bk.tq), cap: 1.25 * P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: desgarro de la horquilla detrás del pasador Q", formula: "τ = (F/2)/(2·t_h·a), a = R_cubo − d_Q/2 ≤ Fy/(Nd·√3)", dem: Fs / 2 / (2 * bk.tq * (bk.eb - P.pv_dq / 2)), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (2 planos de corte)" });
    // pasadores Q y E, orejas del soporte
    const m = pivPinM(P, R, Fs, Ncam), AQ = Math.PI / 4 * P.pv_dq ** 2, AE = Math.PI / 4 * P.pv_dE ** 2;
    add({ grp: AR, sys: "est", name: "Pasador Q: flexión (horquilla del bloque) con la reacción de la leva en su extremo inferior", formula: "M = √[(F/2·(t_h/2 + g + b/4))² + (N_leva·l_Q)²], l_Q = " + nfx(bk.lq) + " mm; σ = M/(πd³/32) ≤ Fy/Nd", dem: m.MQ / (Math.PI * P.pv_dq ** 3 / 32), cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / §3-2.3" });
    add({ grp: AR, sys: "est", name: "Pasador Q: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 / AQ, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    add({ grp: AR, sys: "est", name: "Pasador vertical E: flexión (orejas del soporte)", formula: "M = F/2·(t_oreja/2 + g + b/4); σ ≤ Fy/Nd", dem: m.ME / (Math.PI * P.pv_dE ** 3 / 32), cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / §3-2.3" });
    add({ grp: AR, sys: "est", name: "Pasador vertical E: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 / AE, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    add({ grp: AR, sys: "est", name: "Tapas del cajón E (orejas del pasador): aplastamiento", formula: "σ = (F/2)/(d_E·t_tapa) ≤ 1,25Fy/Nd", dem: Fs / 2 / (P.pv_dE * P.pv_tl), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    add({ grp: AR, sys: "est", name: "Tapas del cajón E: desgarro por corte hacia las paredes traseras (empuje a calado)", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = mín sobre el barrido de la distancia del agujero a la pared en la dirección −u menos d_E/2 = " + nfx(sg.aTear) + " mm", dem: Fs / 2 / (2 * P.pv_tl * sg.aTear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (2 planos de corte)" });
    const Fret = Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10;
    add({ grp: AR, sys: "est", name: "Tapas del cajón E: desgarro hacia la nariz recortada con la tracción del retorno", formula: "τ = (F_ret/2)/(2·t·a_n) ≤ Fy/(Nd·√3), F_ret = A_anular·p_ret = " + nfx(Fret / 1e3) + " kN, a_n = mín sobre el barrido de la distancia del agujero a la nariz en la dirección +u menos d_E/2 = " + nfx(sg.aNose) + " mm", dem: Fret / 2 / (2 * P.pv_tl * sg.aNose), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (2 planos de corte)" });
    // soporte del ojal E (cajón abierto hacia la mesa): paredes en L + muñones, CJP pared–base y pared–pared, PJP de las tapas, mínimos y acceso
    const SL = pivSupLoads(P, sg, Fs), REG_SE = "docs/normas/registro.md, «Soporte del ojal E: cajón abierto (10-11-2026)»", tW = P.pv_tbox, wr = P.pv_wbox;
    const psiTxt = (k) => (SL.psi[k] != null ? " (peor estado: eje a " + nfx(((SL.psi[k] / D2R) % 360 + 360) % 360, 1) + "° en el marco del soporte)" : "");
    add({ grp: SO, sys: "est", name: "Soporte del ojal E: flexión de las paredes en la base (paredes traseras en L prolongadas + muñones; abierto hacia la mesa)", formula: "σ = máx |σ(M)| en las esquinas de la sección, flexión biaxial (I_xx, I_yy, I_xy), M = F/2·(h_sup + h_inf) perpendicular a −u en todos los estados del empuje y del retorno, en ambos sentidos ≤ Fy/Nd" + psiTxt("sig"), dem: SL.sig, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3; " + REG_SE });
    add({ grp: SO, sys: "est", name: "Soporte del ojal E: corte en las paredes", formula: "τ = F/A_v ≤ Fy/(Nd·√3), A_v = Σ t·L·cos²(pared; −u)", dem: SL.tau, cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    add({ grp: SO, sys: "est", name: "Soporte del ojal E: CJP paredes–base (J-E1, J-E2, J-E6; TC-U4b): metal base en la línea de la soldadura (tensión normal y corte)", formula: "FU = máx(σ/(Fy/Nd); τ/(Fy/(Nd·√3))) con σ y τ de las dos filas anteriores (la CJP desarrolla el metal base: AISC 360-22 Tabla J2.5; σ máx en las esquinas y τ en las almas no coinciden)", dem: Math.max(SL.sig / (Fy / Nd), SL.tau / (Fy / (Nd * Math.sqrt(3)))), cap: 1, unit: "–", ref: "AISC 360-22 §J2.4, Tabla J2.5 (CJP); AWS D1.1/D1.1M:2020 Figura 5.1 (TC-U4b); ASME BTH-1 §3-2" });
    add({ grp: SO, sys: "est", name: "Soporte del ojal E: CJP pared–pared (J-E3 a J-E5): corte longitudinal en la junta", formula: "τ = q/t, q = V·Q/I con flexión biaxial (flujo de corte de la parte unida por la junta) ≤ Fy/(Nd·√3)", dem: SL.flow, cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "AISC 360-22 Tabla J2.5 (CJP: metal base); ASME BTH-1 §3-2.3.6" });
    add({ grp: SO, sys: "est", name: "Soporte del ojal E: PJP tapas–paredes (J-E7, J-E8; TC-P4) soldadas solo desde arriba: grupo elástico en el plano de la tapa", formula: "f = q_máx/E ≤ 0,60FEXX/(1,20Nd); q = F/2/ΣL + M·r/J (F/2 en E, líneas = cantos de la tapa contra paredes y muñones, ΣL = " + nfx(sg.Lcap, 0) + " mm); E = S − 3 = " + nfx(sg.E_pjp, 0) + " mm (bisel 45°, S = " + nfx(sg.S_pjp, 0) + " mm; el filete de refuerzo no se cuenta)", dem: SL.pjp, cap: Fw, unit: "MPa", ref: "AISC 360-22 §J2.1a (Tabla J2.1), §J2.4 (Tabla J2.5, PJP en corte: 0,60FEXX); AISC Steel Construction Manual, Parte 8 (método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: SO, sys: "est", kind: "geo", name: "Soporte del ojal E: garganta efectiva mínima de las PJP de las tapas", formula: "E_mín(t más delgada = " + Math.min(P.pv_tl, tW) + " mm) ≤ E = S − 3", dem: Math.min(P.pv_tl, tW) <= 6 ? 3 : Math.min(P.pv_tl, tW) <= 13 ? 5 : Math.min(P.pv_tl, tW) <= 19 ? 6 : Math.min(P.pv_tl, tW) <= 38 ? 8 : Math.min(P.pv_tl, tW) <= 57 ? 10 : 13, cap: sg.E_pjp, unit: "mm", ref: "AISC 360-22 §J2.1b, Tabla J2.3 (garganta efectiva mínima de PJP)" });
    const INSe = cornerInsertOf(P, R), tSeatE = INSe && INSe.ok ? INSe.t : P.t_base;   // las paredes del soporte se sueldan sobre el inserto
    add({ grp: SO, sys: "est", kind: "geo", name: "Soporte del ojal E: filete de refuerzo mínimo (CJP pared–base, pared–pared y PJP de las tapas) según la parte más gruesa", formula: "w_mín(T = máx(t_pared; t_asiento; t_tapa) = " + Math.max(tW, tSeatE, P.pv_tl) + ") ≤ w_refuerzo (asiento: " + (tSeatE > P.t_base ? "inserto de esquina" : "base") + ")", dem: wMin(Math.max(tW, tSeatE, P.pv_tl)), cap: wr, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 7.7" });
    const gapEdge = P.B / 2 - (Math.max(Math.abs(K.E[0]), Math.abs(K.E[1])) + sg.b);
    add({ grp: SO, sys: "est", kind: "geo", name: "Soporte del ojal E: acceso exterior a las CJP de las paredes traseras (marco interrumpido frente al soporte)", formula: "w_refuerzo + 5 ≤ distancia de la cara exterior de la pared al borde de la base (resanado y soldadura de respaldo desde fuera de la base; el marco se interrumpe hasta " + nfx(sg.marco.alcance, 0) + " mm del eje E a lo largo de los dos bordes)", dem: wr + 5, cap: gapEdge, unit: "mm", ref: "AWS D1.1/D1.1M:2020 §7 (acceso para resanado y respaldo); " + REG_SE });
    add({ grp: SO, sys: "est", kind: "geo", name: "Soporte del ojal E: rincón para el filete de refuerzo de la tapa superior (rebaje bajo el borde de las paredes)", formula: "w_refuerzo ≤ rebaje", dem: wr, cap: P.pv_rebt, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Figura 5.2 (verificar: en la edición 2020 la Figura 5.2 es la de PJP; filete en T: el cateto vertical necesita la pared sobre la tapa)" });
    add({ grp: SO, sys: "est", kind: "info", name: "Soporte del ojal E: secuencia de armado y soldadura (todas las uniones accesibles; la cara inferior de las tapas no se suelda)", formula: sg.secuencia.join(" "), dem: sg.m, unit: "kg (por soporte)", ref: REG_SE });
    // plancha base bajo el soporte: contacto unilateral sin anclaje (no definido en el proyecto); filas con FU y estado «pend» (decisión de anclaje del mandante)
    const BP = pivBasePlate(P, R), REG_BP = "docs/normas/registro.md, «Plancha base bajo el soporte del ojal E (10-11-2026)»", be = BP.empuje, br = BP.retorno, Fa = INS_FB * Fy / Nd;
    if (!insertRows(P, R, add, SO, "Plancha base bajo el soporte del ojal E: ", BP)) {   // sin inserto (ins_on = 0): modelo de la franja sin anclaje, pendiente
    const stTxt = (c) => " (peor estado: " + c.sentido + ", " + (c.fase || "") + ", eje a " + nfx(((c.psi / D2R) % 360 + 360) % 360, 1) + "° en el marco del soporte)";
    add({ grp: SO, sys: "est", kind: "info", name: "Plancha base bajo el soporte del ojal E: modelo de la transferencia de carga y casos", formula: "Soporte rígido soldado a la plancha de " + P.t_base + " mm; F en E a h = (h_sup + h_inf)/2 = " + nfx(be.h, 1) + " mm sobre la plancha, M = F·h ⟂ f. En planta F se cierra con el otro cilindro y el roce de la mesa (la losa no toma corte). Losa rígida con contacto unilateral (solo compresión); anclaje a la losa: NO definido en el proyecto (base apoyada en losa o mats); peso propio despreciable: la única retención del talón es la mesa (R ≤ D/2) a través de la plancha. Casos: empuje a calado (F = " + nfx(be.F / 1e3) + " kN, M = " + nfx(be.M / 1e6, 2) + " kN·m) y atasco del retorno (F_ret = A_anular·p_ret = " + nfx(br.F / 1e3) + " kN, M = " + nfx(br.M / 1e6, 2) + " kN·m), todos los estados del barrido en ambos sentidos; caso térmico: no aplica (F sale de la presión de alivio y de retorno, y la base queda a la sombra: h no cambia). La interfaz B (eje más alto) gobierna", dem: be.M / 1e6, cap: br.M / 1e6, unit: "kN·m (empuje / retorno)", ref: REG_BP });
    add({ grp: SO, sys: "est", stFix: "pend", name: "Plancha base bajo el soporte del ojal E: flexión sin anclaje, empuje a calado — NO CUMPLE sin anclaje a la losa (PENDIENTE: decisión del mandante)", formula: "σ = 6·M_corte/(b·t²) ≤ 1,25·Fy/Nd; M_corte = M·(1 − a/s_H) en la línea del talón con la retención en el borde más lejano de la mesa (s_H = " + nfx(be.sH, 0) + " mm: el brazo más largo, conservador para M_corte), a = " + nfx(be.a, 0) + " mm, b = w + a = " + nfx(be.b, 0) + " mm (reparto a 45° desde el centro de la huella); M_corte = " + nfx(be.Mc / 1e6, 2) + " kN·m" + stTxt(be) + ". La FEA con contacto unilateral del verificador independiente da tensiones mayores", dem: be.sig, cap: Fa, unit: "MPa", ref: REF_FB + "; " + REG_BP });
    add({ grp: SO, sys: "est", stFix: "pend", name: "Plancha base bajo el soporte del ojal E: flexión sin anclaje, retorno (atasco) — sin retención detrás del talón (PENDIENTE: anclaje)", formula: "σ = 6·M/(b·t²) ≤ 1,25·Fy/Nd: la mesa queda delante del pie (s_H = " + nfx(br.sH, 0) + " mm ≤ a = " + nfx(br.a, 0) + " mm) y toda la M cruza la línea del pie; b = w + a = " + nfx(br.b, 0) + " mm" + stTxt(br), dem: br.sig, cap: Fa, unit: "MPa", ref: REF_FB + "; " + REG_BP });
    add({ grp: SO, sys: "est", name: "Plancha base bajo el soporte del ojal E: corte de la franja (empuje a calado)", formula: "τ = 1,5·V/(b·t) ≤ Fy/(Nd·√3), V = M/a = " + nfx(be.Vs / 1e3) + " kN (cota superior: retención en el talón)", dem: be.tau, cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6; " + REG_BP });
    add({ grp: SO, sys: "est", kind: "pend", name: "Plancha base bajo el soporte del ojal E: levantamiento del talón — anclaje a la losa no definido en el proyecto (PENDIENTE: anclaje y datos de la losa: f'c, espesor, armadura, bordes)", formula: "Sin anclaje la plancha despega del lado traccionado y la retención llega solo desde la mesa (filas de flexión). Momento a anclar por soporte: empuje " + nfx(be.M / 1e6, 2) + " kN·m, retorno " + nfx(br.M / 1e6, 2) + " kN·m; con la retención en el borde más lejano de la mesa T = M/s_H = " + nfx(be.T / 1e3) + " kN por soporte (empuje). Con la mesa vacía (el calado no depende de la carga) la retención disponible es su peso propio, " + nfx(BP.mesaVacia.W / 1e3) + " kN, " + (BP.mesaVacia.ok ? "≥" : "<") + " " + nfx(BP.mesaVacia.Treq / 1e3) + " kN que piden los " + P.n_cyl + " soportes (cota del modelo de un soporte). Revisión con la base completa (docs/qa/plancha_base_soporte_E.md): con los dos cilindros M₂ = −M₁ y la base no vuelca como cuerpo libre, pero el par llega de un soporte al otro solo por torsión de la base (fuerza de esquina ≈ M/B = " + nfx(be.M / 1e3 / P.B) + " kN en las esquinas libres), que la plancha de " + P.t_base + " mm no tiene: con la mesa vacía queda apoyada solo en los dos pies", dem: be.M / 1e6, unit: "kN·m", ref: REG_BP + "; docs/qa/plancha_base_soporte_E.md" });
    }
    // placas-guía curvas: cargas (empuje guiado a calado y atasco del retorno), contacto con el radio real, ligamento, tornillos, pasadores de posición y base
    const tc = P.pv_tcam, lp = CP.lpad, g = CP.guia, V = GV, hz = CP.hz;
    add({ grp: PL, sys: "est", kind: "info", name: "Placa-guía (" + fam.nombre + (fam.auto ? ", automático" : "") + "): cargas del seguidor: atasco del retorno con el giro en E trabado / empuje a calado con Q apoyado en el canto", formula: "N_atasco = F_ret/sen φ₁ (φ₁ = " + nfx(g.primer_contacto.phi, 1) + "° en el primer contacto del retorno, L = " + nfx(g.primer_contacto.L, 1) + " mm, sin el roce que ayuda); H = máx h·F_calado·η (empuje guiado); la placa se verifica con N = máx de ambas", dem: CP.NR / 1e3, cap: CP.Tst / 1e3, unit: "kN", ref: REG_PV });
    if (fam.tipo === "hertz") {
      add({ grp: PL, sys: "est", name: "Placa-guía: contacto de Hertz extremo del pasador Q–canto templado, empuje a calado con el radio real del canto (R_c = " + (isFinite(hz.push.Rc) ? nfx(hz.push.Rc, 1) : "∞") + " mm)", formula: "p₀ = √(q·E*/(π·R_ef)), 1/R_ef = 1/r_Q + 1/R_c (R_c > 0 convexo, < 0 cóncavo), q = H/(t − 2) ≤ 1,67·Fy_sup; peor punto de las 61 posiciones", dem: hz.push.p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: fam.pRef });
      add({ grp: PL, sys: "est", name: "Placa-guía: contacto de Hertz en el atasco del retorno (R_c = " + (isFinite(hz.jam.Rc) ? nfx(hz.jam.Rc, 1) : "∞, flanco recto") + " mm)", formula: "p₀ = √(q·E*/(π·R_ef)), q = N_atasco/(t − 2) ≤ 1,67·Fy_sup", dem: hz.jam.p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: fam.pRef });
      const bz = Math.max(hz.push.b, hz.jam.b);
      add({ grp: PL, sys: "est", kind: "geo", name: "Placa-guía: espesor de la capa templada frente a la profundidad del corte máximo de Hertz", formula: "2·0,786·b ≤ capa efectiva 4 mm, b = √(4·q·R_ef/(π·E*))", dem: 2 * 0.786 * bz, cap: 4, unit: "mm", ref: "Hertz, contacto lineal (τ_máx a z = 0,786·b); EN 10328 (profundidad de temple)" });
    } else {
      const pS = CP.Ncam / (lp * tc), pD = CP.Tdis / (lp * tc);
      add({ grp: PL, sys: "est", name: "Placa-guía (" + fam.corto + "): presión de la zapata del seguidor en el empuje de diseño", formula: "p = H_dis/(l_zapata·t_placa) ≤ p_adm (carga de diseño, como la interfaz de giro); l_zapata = " + lp + " mm" + (P.pv_lpad > 0 ? "" : " (automático, FU 0,90 con p_adm y PV)"), dem: pD, cap: fam.pAdm, unit: "MPa", ref: fam.pRef });
      if (fam.PV) add({ grp: PL, sys: "est", name: "Placa-guía (" + fam.corto + "): valor PV de la zapata en el empuje de diseño", formula: "PV = (H_dis/(l·t))·v_Q ≤ PV_adm; v_Q = " + nfx(CP.vQ * 1000, 1) + " mm/s", dem: pD * CP.vQ, cap: fam.PV, unit: "MPa·m/s", ref: fam.pRef });
      if (fam.FyL) add({ grp: PL, sys: "est", name: "Placa-guía (" + fam.corto + "): aplastamiento del revestimiento a calado", formula: "p ≤ 1,25·Fy_rev/Nd", dem: pS, cap: 1.25 * fam.FyL / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
      if (fam.f === 2 || fam.f === 3) add({ grp: PL, sys: "est", name: "Placa-guía: respaldo de acero del revestimiento (aplastamiento a calado)", formula: "p ≤ 1,25·Fy_placa/Nd", dem: pS, cap: 1.25 * P.Fy_camP / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
      add({ grp: PL, sys: "est", kind: "geo", name: "Seguidor: largo de la zapata practicable", formula: "l_zapata ≤ 3·d_Q", dem: lp, cap: 3 * P.pv_dq, unit: "mm", ref: "Criterio del proyecto (zapata pivotante sobre el pasador Q)" });
      const Rm = Math.min(g.rCanto.convexo, g.rCanto.concavo);
      add({ grp: PL, sys: "est", kind: "pend", name: "Zapata plana sobre el canto curvo: flecha l²/(8·R_mín) = " + nfx(lp * lp / (8 * Rm), 1) + " mm con R_mín = " + nfx(Rm, 1) + " mm (PENDIENTE: definir la cara de la zapata o un buje cilíndrico; la presión p = H/(l·t) supone apoyo completo)", formula: "flecha ≤ 0,5 mm para usar p = H/(l·t)", dem: lp * lp / (8 * Rm), unit: "mm", ref: REG_PV });
    }
    // ligamento de la placa entre el canto y el borde opuesto (viga entre tornillos, carga en el punto de contacto) y tornillos (grupo elástico)
    const Np = CP.Tst, Nj = CP.NR, Hp = CP.Hpt, fo = CP.onPath(g.primer_contacto.L), ninJ = V.left(fo.t), cJ = V.sub(fo.p, V.mul(ninJ, P.pv_dq / 2));
    const loads = [{ id: "empuje a calado", N: Np, p: Hp ? Hp.contacto : cJ, nin: Hp ? Hp.nin : ninJ, b: Hp ? Hp.lig : g.lig.jam, mu: fam.mu, tp: Hp ? V.right(Hp.nin) : V.right(ninJ) }, { id: "atasco del retorno", N: Nj, p: cJ, nin: ninJ, b: g.lig.jam, mu: 0, tp: V.right(ninJ) }];
    const sb = CP.sb, sig = (L) => 6 * (L.N * sb / 4) / (tc * L.b * L.b), tau = (L) => 1.5 * (L.N / 2) / (tc * L.b), Lw = loads.reduce((a, L) => (sig(L) > sig(a) ? L : a));
    add({ grp: PL, sys: "est", name: "Placa-guía: flexión del ligamento entre tornillos (" + Lw.id + ", ligamento " + nfx(Lw.b, 0) + " mm)", formula: "σ = 6·(N·s/4)/(t·b²) ≤ Fy/Nd; s = " + nfx(sb) + " mm entre tornillos, b = ligamento desde el contacto hasta el borde opuesto", dem: sig(Lw), cap: P.Fy_camP / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    add({ grp: PL, sys: "est", name: "Placa-guía: corte del ligamento", formula: "τ = 1,5·(N/2)/(t·b) ≤ Fy/(Nd·√3)", dem: Math.max(...loads.map(tau)), cap: P.Fy_camP / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    const aN = Math.max(1, CP.wPk - P.pv_c), rN = Math.max(1, g.rCanto.concavo), Kt = 1 + 2 * Math.sqrt(aN / rN);
    add({ grp: PL, sys: "est", name: "Placa-guía: concentración de tensiones en el radio cóncavo del recorte (sin fluencia local a calado)", formula: "K_t·σ_nom ≤ Fy; K_t = 1 + 2√(a/ρ) = " + nfx(Kt, 2) + " (entalla elíptica, cota superior), a = profundidad del bolsillo, ρ = radio cóncavo mínimo del canto (" + nfx(rN, 0) + " mm)", dem: Kt * sig(Lw), cap: P.Fy_camP, unit: "MPa", ref: "Pilkey, Peterson's Stress Concentration Factors (3.ª ed.), Ec. 4.3 (Inglis); ASME BTH-1 §3-2 no exige K_t en la verificación estática (material dúctil); la fatiga usa la categoría del detalle" });
    const Ib = tc * Lw.b ** 3 / 12, dfl = Lw.N * sb ** 3 / (48 * P.E * Ib) + Lw.N * sb / (4 * (P.E / 2.6) * (5 / 6) * tc * Lw.b);
    add({ grp: PL, sys: "est", kind: "geo", name: "Placa-guía: deformación del ligamento bajo la carga máxima (no altera la sincronía)", formula: "δ = N·s³/(48·E·I) + N·s/(4·κ·G·A) ≤ 0,1 mm (≈ 10 % del presupuesto de tolerancias δ = " + nfx(g.dTol, 2) + " mm)", dem: dfl, cap: 0.1, unit: "mm", ref: "Resistencia de materiales (viga de Timoshenko)" });
    // tornillos ISO 10642 roscados en la base: grupo elástico (AISC Manual, Parte 7) con la carga en el contacto (normal + roce sobre la placa)
    const B = CP.bolts, nB = B.length, Gc = B.reduce((a, b) => [a[0] + b[0] / nB, a[1] + b[1] / nB], [0, 0]), J = B.reduce((a, b) => a + (b[0] - Gc[0]) ** 2 + (b[1] - Gc[1]) ** 2, 0);
    const Vmax = (L) => { const Fv = V.add(V.mul(L.nin, -L.N), V.mul(L.tp, L.mu * L.N)), M = V.crs(V.sub(L.p, Gc), Fv); return Math.max(...B.map((b) => { const r = V.sub(b, Gc), m = V.mul(V.left(r), M / J); return V.nrm(V.add(V.mul(Fv, 1 / nB), m)); })); };
    const Vb = Math.max(...loads.map(Vmax)), Ab = Math.PI / 4 * P.pv_db ** 2, Fnv = 0.45 * P.pv_Fub, Fnt = 0.75 * P.pv_Fub, kH = 0.56 * P.pv_db, te = tc - kH / 2, dh = P.pv_db + 1, eb = g.eb;
    add({ grp: PL, sys: "est", name: "Tornillos de la placa-guía: corte (ISO 10642 M" + P.pv_db + " 8.8, " + nB + " por placa; grupo elástico con la carga en el contacto)", formula: "V_i = F/n + M·r_i/Σr², M = (p − G) × F; f_rv = máx V_i/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu (rosca incluida), Ω = 2,00", dem: Vb / Ab, cap: Fnv / 2, unit: "MPa", ref: "AISC 360-22 §J3.7, Tabla J3.2; AISC Steel Construction Manual, Parte 7 (método elástico)" });
    const RnP = Math.min(1.2 * (eb - dh / 2) * te * P.Fu_camP, 2.4 * P.pv_db * te * P.Fu_camP), RnB = 2.4 * P.pv_db * P.t_base * P.Fu;
    add({ grp: PL, sys: "est", name: "Tornillos de la placa-guía: aplastamiento en la placa (espesor útil con el avellanado)", formula: "V ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 (k ≈ 0,56·d, ISO 10642), l_c = e − d_h/2", dem: Vb / 1e3, cap: RnP / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a); EN 1993-1-8 Tabla 3.4 (avellanado)" });
    add({ grp: PL, sys: "est", name: "Tornillos de la placa-guía: aplastamiento en la plancha base (agujero roscado)", formula: "V ≤ 2,4·d·t_base·Fu/Ω, Ω = 2,00 (transferencia de la carga a la base)", dem: Vb / 1e3, cap: RnB / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a)" });
    const zc = (tc + 2) / 2, Tb = Math.max(...loads.map((L) => L.N * zc / Math.max(1, L.b - eb) / 2)), frv = Vb / Ab, Fpnt = Math.min(Fnt, 1.3 * Fnt - (2 * Fnt / Fnv) * frv);
    add({ grp: PL, sys: "est", name: "Tornillos de la placa-guía: tracción por el vuelco de la placa con corte combinado", formula: "T = N·z_c/(b − e)/2 (dos tornillos de la fila opuesta), z_c = (t + 2)/2; f_t = T/A_b ≤ F'nt/Ω, F'nt = 1,3·Fnt − (Ω·Fnt/Fnv)·f_rv ≤ Fnt, Fnt = 0,75·Fu, Ω = 2,00", dem: Tb / Ab, cap: Math.max(0, Fpnt) / 2, unit: "MPa", ref: "AISC 360-22 §J3.8 (Ec. J3-3b)" });
    add({ grp: PL, sys: "est", kind: "geo", name: "Tornillos de la placa-guía: enganche de la rosca en la base", formula: "1,0·d ≤ t_base (8.8 en acero S355; 10.9 pediría 1,25·d)", dem: P.pv_db, cap: P.t_base, unit: "mm", ref: "VDI 2230-1:2015 (orientativo)" });
    const dMin = Math.min(...B.concat(CP.dowels).map((b) => Math.min(...g.contorno.map((s) => V.dist(s, b))))), sMin = Math.min(...B.flatMap((a, i) => B.slice(i + 1).map((b) => V.nrm(V.sub(a, b)))));
    add({ grp: PL, sys: "est", kind: "geo", name: "Tornillos y pasadores de posición de la placa-guía: distancia al borde (incluido el recorte)", formula: "e_mín (Tabla J3.4M) ≤ mín dist(eje, contorno)", dem: J34M(P.pv_db), cap: dMin, unit: "mm", ref: "AISC 360-22 §J3.5, Tabla J3.4M" });
    add({ grp: PL, sys: "est", kind: "geo", name: "Tornillos de la placa-guía: separación mínima", formula: "3·d ≤ s_mín", dem: 3 * P.pv_db, cap: sMin, unit: "mm", ref: "AISC 360-22 §J3.4" });
    add({ grp: PL, sys: "est", kind: "info", name: "Pasadores de posición ISO 8734 (2 por placa, m6/H7): fijan la posición del canto (tolerancia ± " + nfx(P.pv_tolg / 2, 2) + " mm); no se cuentan en la resistencia", formula: "el corte lo toman los tornillos (holgura del agujero 1 mm)", dem: P.pv_dd, unit: "mm", ref: REG_PV });
    { const dw = dowelGeo(P), REGD = "docs/normas/registro.md, «Placa-guía: holgura mínima de sincronía y pasadores de posición (10-11-2026)»";
      add({ grp: PL, sys: "est", kind: "geo", name: "Pasadores de posición (" + dw.designacion + "): enganche en la base (alojamiento ciego)", formula: "1,5·d ≤ l_b = " + nfx(dw.lb, 0) + " mm; alojamiento Ø" + dw.d + " H7 de " + nfx(dw.hb, 0) + " mm (punta a " + dw.fondo + " mm del fondo) con remanente " + nfx(dw.remB, 0) + " mm en la base de " + P.t_base + " mm", dem: dw.lmin, cap: dw.lb, unit: "mm", ref: REGD });
      add({ grp: PL, sys: "est", kind: "geo", name: "Pasadores de posición (" + dw.designacion + "): enganche en la placa (alojamiento ciego por la cara inferior)", formula: "1,5·d ≤ l_p = L − l_b = " + nfx(dw.lp, 0) + " mm; alojamiento de " + nfx(dw.hp, 0) + " mm con remanente " + nfx(dw.remP, 0) + " mm en la placa de " + P.pv_tcam + " mm", dem: dw.lmin, cap: dw.lp, unit: "mm", ref: REGD });
      add({ grp: PL, sys: "est", kind: "geo", name: "Pasadores de posición: remanente bajo los alojamientos ciegos (base y placa)", formula: "3 mm ≤ mín(t_base − l_b − 2; t_placa − l_p − 2)", dem: 3, cap: Math.min(dw.remB, dw.remP), unit: "mm", ref: REGD }); }
    add({ grp: PL, sys: "est", kind: "info", name: "Masas del modo pivotado: soporte del ojal E / bloque-uña con pasador Q (por cilindro) y 4 placas-guía", formula: "m = ρ·V", dem: sg.m, cap: bk.m, unit: "kg", ref: "Geometría" });
  }

  /* ---------------- Verificaciones ---------------- */
  // kind: "fu" (FU = dem/cap), "geo" (FU con criterio geométrico), "info" (no afecta el veredicto), "pend" (pendiente de dato)
  function verifs(P, R, fea) {
    const out = [], sAllW = (fy) => 0.6 * fy;
    const add = (o) => out.push(Object.assign({ kind: "fu" }, o, { fu: o.kind === "info" || o.kind === "pend" ? null : (o.fu != null ? o.fu : ((o.cap > 0 && o.dem >= 0) ? o.dem / o.cap : Infinity)) }));   // capacidad ≤ 0 o demanda negativa: no cumple
    const K = R.K, Nd = P.Nd, Fy = P.Fy;
    const dTe = P.__th ? Math.max(P.dT, P.__th.dT) : P.dT;          // ΔT de las filas térmicas heredadas: la de diseño (40 K) o la del escenario si es mayor
    const EssT = E_SS * (P.__th ? P.__th.k.E_ss : 1);               // módulo del inoxidable a la temperatura del escenario
    const Fs = R.Fstall;                                   // fuerza de calado por cilindro, kN
    const cd = R.cd || { F: NaN, p: NaN, FS: NaN };
    const cs = (id) => R.cases.find((c) => c.id === id) || { F: NaN, FS: NaN, p: NaN };
    const Fw = (P.FEXX * 0.60) / (1.20 * Nd);              // BTH-1 soldaduras
    const FwA = 0.60 * P.FEXX / 2.0;                       // AISC J2.4 ASD (Ω 2,00), sin aumento direccional

    /* --- Giro --- */
    add({ grp: "Giro", sys: "giro", name: "FS del accionamiento en el caso de diseño", formula: "FS = F_calado / F_dis ≥ FS_min", dem: P.FS_min, cap: cd.FS, unit: "–", ref: "Criterio del proyecto (μ_d, r_ef)" });
    add({ grp: "Giro", sys: "giro", name: "Presión de diseño frente a la alarma", formula: "p_dis = F_dis / A ≤ p_alarma", dem: cd.p, cap: P.p_alarm, unit: "bar", ref: "Criterio de operación" });
    const pRatedBar = P.p_rated * PSI_CAT;
    add({ grp: "Giro", sys: "giro", name: "Alivio dentro de la presión nominal del cilindro y la bomba", formula: "p_alivio ≤ p_nominal (10.000 psi ≙ 700 bar; 5.000 psi ≙ 350 bar)", dem: P.p_relief, cap: pRatedBar, unit: "bar", ref: "ISO 4413:2010, protección contra sobrepresión; catálogo del fabricante" });
    add({ grp: "Giro", sys: "giro", name: "Alarma bajo el alivio (detiene antes de calar)", formula: "p_alarma ≤ 0,90 · p_alivio", dem: P.p_alarm, cap: 0.9 * P.p_relief, unit: "bar", ref: "Criterio de operación" });
    add({ grp: "Giro", sys: "giro", name: "Retorno dentro de la presión nominal", formula: "p_retorno ≤ p_nominal", dem: P.p_ret, cap: pRatedBar, unit: "bar", ref: "Catálogo del fabricante" });
    const Dreq = (pr, pa) => Math.sqrt(4 / Math.PI * Math.max(P.FS_min * cd.F * 1e3 / (pr / 10), cd.F * 1e3 / (pa / 10)));
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Émbolo mínimo con las presiones elegidas", formula: "A ≥ máx(FS_min·F_dis/p_alivio; F_dis/p_alarma)", dem: Dreq(P.p_relief, P.p_alarm), cap: P.D_bore, unit: "mm", ref: "Hidráulica" });
    add({ grp: "Giro", sys: "giro", name: "Gira con grasa contaminada", formula: "F_cont ≤ F_calado", dem: cs("cont").F, cap: Fs, unit: "kN", ref: "Criterio del proyecto" });
    add({ grp: "Giro", sys: "giro", name: "Gira con contacto en el borde (r = R)", formula: "F(μ_d, R) ≤ F_calado", dem: cs("borde").F, cap: Fs, unit: "kN", ref: "Revisión independiente M1" });
    const mode = driveMode(P);
    if (mode === 1) add({ grp: "Giro", sys: "giro", kind: "geo", name: "Carrera requerida con margen", formula: "s_libre + ΔL(paso) + margen ≤ carrera", dem: K.ok ? K.s_req + P.s_margin : NaN, cap: P.stroke, unit: "mm", ref: "Cinemática (rev. C3)" });
    else add({ grp: "Giro", sys: "giro", kind: "geo", name: "Carrera requerida con margen (pivotado)", formula: "máx L(θ) − L0 + margen ≤ carrera; L(θ) = |Q(θ) − E| con Q apoyado en el canto y |P(θ) − Q| = L_qp (colineal: L = |P − E| − L_qp), L(θ_ini) ≥ L0 + s_libre", dem: K.ok ? (R.camP ? R.camP.sReqG : K.s_req) + P.s_margin : NaN, cap: P.stroke, unit: "mm", ref: "Cinemática del cilindro pivotado (docs/normas/registro.md, «Accionamiento pivotado tipo KIET»)" });
    const bgv = mode === 1 ? bracketGeo(P) : null, Bh = P.B / 2 - P.rim_t - 5, zBed = P.t_base + P.t_bed;
    if (mode === 1) {
          add({ grp: "Giro", sys: "giro", kind: "geo", name: "Uña entre pasadores (ancho en el sentido del empuje)", formula: "cuerda − d_pas ≥ b_uña + 2·10", dem: P.dog_b + 20, cap: K.gap, unit: "mm", ref: "Cinemática" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Uña dentro de la luz libre entre anillos", formula: "h_uña + 10 ≤ h − 2·t_anillo", dem: P.dog_h + 10, cap: pinClear(P), unit: "mm", ref: "Geometría" });
      if (K.inset > 0) add({ grp: "Giro", sys: "giro", kind: "geo", name: "Boca del alojamiento entre los anillos de la mesa", formula: "h_uña + 2·10 (marco) + 10 ≤ h − 2·t_anillo", dem: P.dog_h + 30, cap: pinClear(P), unit: "mm", ref: "Geometría (alzado)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Alojamiento de la uña (retorno + resorte) dentro del patín", formula: "boca + L_in + recorrido de retorno + resorte + 10 ≤ x_g + w_s/2", dem: K.pocketEnd + 10, cap: P.x_g + P.w_s / 2, unit: "mm", ref: "Geometría (retorno del trinquete)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Holgura radial de la uña en el patín", formula: "R·(1 − cos π/N) + 2 ≤ holgura", dem: K.radial + 2, cap: P.slot, unit: "mm", ref: "Cinemática (rev. C2)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Patín fuera de la mesa", formula: "D/2 + 15 ≤ x_g − w_s/2", dem: P.D_top / 2 + 15, cap: P.x_g - P.w_s / 2, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Bancada de guía fuera de la mesa", formula: "D/2 + 10 ≤ x_g − w_bancada/2", dem: P.D_top / 2 + 10, cap: P.x_g - P.w_bed / 2, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cilindro, ménsula y bancada dentro de la base (x)", formula: "x_g + máx(D_cuerpo, W_ménsula, w_bancada, w_patín)/2 ≤ B/2 − t_marco − 5", dem: P.x_g + Math.max(P.D_body, bgv.Wout, P.w_bed, P.w_s) / 2, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Ménsula del ojal dentro de la base (y)", formula: "|y_ojal| + saliente trasera ≤ B/2 − t_marco − 5", dem: Math.abs(K.y_eye) + bgv.rear, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cuerpo del cilindro detrás del patín", formula: "saliente trasera del patín + 10 ≤ c_vástago", dem: K.rear + 10, cap: P.c_rod, unit: "mm", ref: "Geometría (cilindro retraído)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Fondo del alojamiento de la uña sobre la bancada", formula: "z_eje − h_uña/2 − 1 − z_bancada ≥ t_alojamiento", dem: P.t_pk, cap: K.zc0 - P.dog_h / 2 - 1 - zBed, unit: "mm", ref: "Geometría (alzado)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Patín bajo la cara superior de la mesa", formula: "z_sup_patín ≤ z_eje + h_mesa/2", dem: K.shoeTop, cap: K.zc0 + P.h_disc / 2, unit: "mm", ref: "Geometría (alzado)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Horquilla del patín sobre la bancada", formula: "z_bancada + 5 ≤ z_eje − h_horquilla/2", dem: zBed + 5, cap: K.zc0 - forkH(P) / 2, unit: "mm", ref: "Geometría (alzado)" });
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Orejas de la ménsula libres del cuerpo del cilindro", formula: "d_pp/2 + 25 + 10 ≤ e_cuerpo", dem: TT_lugF(P) + 10, cap: P.e_body, unit: "mm", ref: "Geometría" });
    } else pivGiroRows(P, R, add);
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cuerpo del cilindro libre sobre la base", formula: "D_cuerpo/2 + 5 ≤ h_eje", dem: P.D_body / 2 + 5, cap: R.hax, unit: "mm", ref: "Geometría" });
    const Ir = Math.PI * P.d_rod ** 4 / 64, Lext = P.L0 + P.stroke;
    const Pcr = Math.PI ** 2 * P.E * Ir / (Lext * Lext) / 1e3;
    add({ grp: "Giro", sys: "giro", name: "Pandeo del vástago (biarticulado, longitud extendida)", formula: "F_calado ≤ Pcr / 3; Pcr = π²EI/L²", dem: Fs, cap: Pcr / 3, unit: "kN", ref: "Euler, FS 3 (conservador frente a ISO/TS 13725)" });
    if (mode === 2 && K.ok) {
      // vástago del cilindro biarticulado (pasadores verticales E y Q): en planta solo recibe la fuerza axial, el momento de roce de los pasadores
      // (μ·F·d/2 en cada ojal, corte V = (M_E + M_Q)/L) y, en alzado, su peso; la reacción de la placa-guía entra al pasador Q y al bloque, no al vástago
      const Lc = P.L0 + P.stroke, d = P.d_rod, Ar = Math.PI / 4 * d * d, Ir = Math.PI * d ** 4 / 64, rg = d / 4, FyR = P.pv_Fyrod, Pr = Fs * 1e3;
      const Fe_ = Math.PI ** 2 * P.E / (Lc / rg) ** 2, Fcr = FyR / Fe_ <= 2.25 ? Math.pow(0.658, FyR / Fe_) * FyR : 0.877 * Fe_, Pc = Fcr * Ar / 1.67, Mc = FyR * d ** 3 / 6 / 1.67;
      const MQ = P.pv_muE * Pr * P.pv_dq / 2, ME = P.pv_muE * Pr * P.pv_dE / 2, Mw = P.m_cyl * G * Lc / 8, Pe1 = Math.PI ** 2 * P.E * Ir / Lc ** 2, B1 = 1 / Math.max(1e-6, 1 - 1.6 * Pr / Pe1);
      const Mr = B1 * Math.hypot(MQ, Mw), ratio = Pr / Pc >= 0.2 ? Pr / Pc + 8 / 9 * Mr / Mc : Pr / (2 * Pc) + Mr / Mc;
      add({ grp: "Giro", sys: "giro", kind: "info", name: "Vástago: carga transversal (roce de los pasadores E y Q a calado / peso del cilindro)", formula: "V = μ·F·(d_E + d_Q)/(2·L); la reacción de la placa-guía no llega al vástago (miembro biarticulado de dos fuerzas)", dem: P.pv_muE * Fs * (P.pv_dE + P.pv_dq) / 2 / Lc, cap: P.m_cyl * G / 2 / 1e3, unit: "kN", ref: REG_PV });
      add({ grp: "Giro", sys: "giro", name: "Vástago: flexocompresión a calado con el roce del ojal Q (μ = " + nfx(P.pv_muE, 2) + ") y el peso (Fy = " + P.pv_Fyrod + " MPa: DATO DEL PROVEEDOR)", formula: "P_r/P_c + 8/9·B₁·M_r/M_c ≤ 1; P_c = F_cr·A/1,67 (E3, KL = L0 + carrera), M_c = Fy·d³/6/1,67, M_r = √((μ·F·d_Q/2)² + (m·g·L/8)²), B₁ = 1/(1 − 1,6·P_r/P_e1)", dem: ratio, cap: 1, unit: "–", ref: "AISC 360-22 §H1.1 (Ec. H1-1a), §E3, Apéndice 8 (B₁, ASD α = 1,6)" });
    }
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Retorno: fuerza disponible en el puerto B", formula: "F_ret = A_anular · p_ret", dem: R.Fret, unit: "kN", ref: "Hidráulica" });
    add({ grp: "Giro", sys: "giro", name: "Velocidad de retorno del vástago frente al máximo (rebote de la uña sobre el pasador)", formula: "v_ret = Q_ret/(n·A_anular) ≤ v_ret,máx", dem: R.pump.vRet, cap: P.v_ret_max, unit: "m/s", ref: "Criterio del proyecto" });
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Potencia del motor de la bomba (el mayor entre avance y retorno, ÷ η)", formula: "P = p·Q/(600·η) a la presión de diseño (dem) y a la de alarma (cap)", dem: R.pump.Pmotor, cap: R.pump.PmotorAlarm, unit: "kW", ref: "Hidráulica" });
    if (P.t_vuelta_obj > 0) {
      add({ grp: "Giro", sys: "giro", kind: "geo", name: "Tiempo por vuelta frente al objetivo", formula: "t_vuelta ≤ t_objetivo", dem: R.tRev, cap: P.t_vuelta_obj, unit: "min", ref: "Criterio de operación" });
      add({ grp: "Giro", sys: "giro", kind: "info", name: "Caudal de bomba requerido para el tiempo objetivo (avance y retorno al mismo caudal)", formula: "Q = (V_avance + V_retorno)·N_pas/t_objetivo", dem: R.pump.Qreq, unit: "L/min", ref: "Hidráulica" });
    }
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Tiempo por vuelta", formula: "N_pas · (V_ext + V_ret) / Q", dem: R.tRev, unit: "min", ref: "Hidráulica" });

    /* --- Interfaz y apoyo --- */
    add({ grp: "Interfaz", sys: "est", name: "Presión de contacto máxima", formula: "q = N_D/A · (1 + 4eR/(R²+r²))", dem: R.q_max, cap: P.q_adm, unit: "MPa", ref: "Criterio acero/acero lubricado" });
    add({ grp: "Interfaz", sys: "est", kind: "geo", name: "Sin despegue de la mesa (q_mín ≥ 0)", formula: "1 − 4eR/(R²+r²) ≥ 0", dem: 4 * P.e * R.Ro / (R.Ro ** 2 + R.Ri ** 2), cap: 1, unit: "–", ref: "Núcleo central" });
    add({ grp: "Interfaz", sys: "est", kind: "info", name: "Presión sobre losa / mats bajo la mesa (base delgada, sin reparto)", formula: "σ ≈ q_máx (÷ cobertura con pastillas) ≤ q_losa (verificar por terceros)", dem: R.qc, cap: P.q_floor, unit: "MPa", ref: "Referencial (rev. M7)" });

    /* --- Fijación desmontable por sectores con topes y engrase (A, B y C) --- */
    const I = R.ifc;
    const Lav = R.Ro - R.Ri - 100;                           // canto radial disponible (mm)
    const removable = P.fix_mode < 1.5;
    // Tope soldado al respaldo que toma el par por aplastamiento sobre el canto del sector (el tornillo avellanado solo da posición).
    // Geometría (ver stopAInf): barra h_barra = t − a_sup; alivio inferior a_inf = w + 1 que libra el filete delantero; contacto h_c = t − a_sup − a_inf.
    // El dimensionamiento y la geometría resuelta (R.ifc.topes: la consume el dibujo vía apoyo.interfaz.topes e interfazGeom.topes) salen de stopsOf(), la misma fuente de m.stopBars.
    const aInf = stopAInf(P), topeOf = (id) => R.ifc.topes.find((x) => x.id === id);
    const REFW = "AWS D1.1/D1.1M:2020 Tabla 7.7 (filete mínimo por la parte más gruesa)";
    // K2: AWS (mínimo por la parte más gruesa, sin exceder la más delgada) y AISC Tabla J2.4 (por la más delgada) no coinciden; el proyecto aplica AWS
    const REFWMIN = "Se aplica la regla de AWS (parte más gruesa): AWS D1.1/D1.1M:2020 Tabla 7.7, sin exceder el espesor de la parte más delgada; AISC 360-22 Tabla J2.4 lo da por la parte más delgada (valor menor o igual) y no se usa";
    // Verificaciones geométricas y de la barra comunes a todos los topes
    const stopCommon = (s) => {
      const { grp, pieza: nombre, t, allow, L, F } = s, g = stopGeo(P, t);
      add({ grp, sys: "est", kind: "geo", name: nombre + ": altura de contacto efectiva del tope sobre el canto del sector", formula: "h_c,mín ≤ h_c = t − a_sup − a_inf (t = " + t + "; barra h = t − a_sup; espesor mínimo del sector " + tStopMin(P) + " mm)", dem: P.hc_min, cap: g.hC, unit: "mm", ref: "Criterio del proyecto (geometría del tope; tolerancia de corte del canto)" });
      const hcd = g.hC - P.tol_hc;
      add({ grp, sys: "giro", name: nombre + ": aplastamiento del tope con la altura de contacto reducida por la tolerancia (h_c − tol_hc)", formula: "σ = F_tope/(L_tope·(h_c − tol_hc)) ≤ adm; tol_hc = " + P.tol_hc + " mm (corte y rebabas del canto): el largo del tope (y el espesor de la lámina UHMW) se dimensionan con h_c − tol_hc y FU objetivo 0,90, de modo que 1 mm menos de contacto no pasa de FU 0,90", dem: hcd > 0 ? F * 1e3 / (L * hcd) : Infinity, cap: s.adm, unit: "MPa", ref: "Criterio del proyecto (hallazgo T6: el aplastamiento no debe depender de 1 mm de corte del canto); ASME BTH-1 §3-3.3" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": barra del tope bajo la superficie de deslizamiento al final de la vida", formula: "a_sup ≥ 1 mm + sobreespesor de desgaste y relapeado (" + allow.toFixed(2).replace(".", ",") + " mm)", dem: 1 + allow, cap: P.a_sup, unit: "mm", ref: "Criterio del proyecto (la barra no debe rozar la pieza contraria)" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": alivio inferior del canto libra el filete del tope", formula: "a_inf ≥ w_tope + 1 mm (chaflán 45° en el canto del sector sobre el triángulo del filete)", dem: P.w_tope + 1, cap: aInf, unit: "mm", ref: "AWS D1.1/D1.1M:2020 (perfil del filete de cateto w); geometría" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": filete del tope dentro de la altura de barra", formula: "w_tope + h_c,mín ≤ h_barra = t − a_sup (el cateto vertical del filete debe caber bajo el contacto)", dem: P.w_tope + P.hc_min, cap: g.hB, unit: "mm", ref: REFW });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": filete mínimo del tope según la parte más gruesa", formula: "w_mín(T = máx(b_tope; t_respaldo) = " + s.Tw + ") ≤ w_tope", dem: s.w_min, cap: P.w_tope, unit: "mm", ref: REFW });
      add({ grp, sys: "est", name: nombre + ": flexión de la barra del tope en la raíz (voladizo de altura z)", formula: "σ = 6·F·z/(L·b²) ≤ Fy/Nd; z = a_inf + h_c/2", dem: 6 * F * 1e3 * g.z / (L * P.b_tope ** 2), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3 (flexión, Fy/Nd)" });
      add({ grp, sys: "est", kind: "info", name: nombre + ": masa de las barras del tope (incluida en la masa total, m.stopBars)", formula: "m = capas·n·ρ·L·b_tope·h_barra, una barra por sector y capa; ρ = " + (s.rho_barra * 1e6).toFixed(2).replace(".", ",") + " g/cm³ (" + (s.uh ? "acero inoxidable: barras del rebaje de la lámina UHMW" : "acero estructural") + ")", dem: s.m_barras, cap: s.m_barra, unit: "kg / kg por barra", ref: "Geometría (suma a m.total desde la 2.ª pasada; antes no se contaban)" });
    };
    const stopRows = (s) => {
      const { grp, pieza: nombre, F: Fst, L: Lt, adm } = s, g = stopGeo(P, s.t);
      add({ grp, sys: "giro", name: nombre + ": aplastamiento del tope sobre el canto del sector", formula: "σ = F_tope/(L_tope·h_c) ≤ 1,25·mín(Fy_sector; Fy_barra)/Nd; h_c = t − a_sup − a_inf; F_tope = (T_calado/r_u)/n·(q_máx/q_med)", dem: g.hC > 0 ? Fst * 1e3 / (Lt * g.hC) : Infinity, cap: adm, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento); Nd del proyecto" });
      add({ grp, sys: "giro", kind: "geo", name: nombre + ": largo del tope frente al canto radial disponible", formula: "L_tope ≤ R_o − R_i − 100", dem: Lt, cap: Lav, unit: "mm", ref: "Geometría" });
      add({ grp, sys: "est", name: nombre + ": soldadura del tope al respaldo (2 filetes): corte + par de excentricidad", formula: "f = √[(F/(2·a·L))² + (F·z/(b·a·L))²] ≤ 0,60FEXX/(1,20Nd); a = 0,707w; z = a_inf + h_c/2 (resultante sobre el respaldo); el filete cargado toma el par con el brazo b_tope", dem: weldStop(P, Fst, Lt, g.z), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4; AISC 360-22 J2.4 (resultante); hallazgo T2 de la revisión independiente" });
      stopCommon(s);
    };
    // Tornillo avellanado de posición: la cabeza (k = 0,55·d, ISO 10642) debe dejar ≥ 2 mm de material bajo ella
    const screwRow = (grp, nombre, tEf) => add({ grp, sys: "est", kind: "geo", name: nombre + ": cabeza del tornillo avellanado dentro del espesor útil", formula: "0,55·d_tornillo + 2 ≤ t − sobreespesor", dem: 0.55 * P.d_tor + 2, cap: tEf, unit: "mm", ref: "ISO 10642 (altura de la cabeza k = 0,55·d); criterio del proyecto" });
    // Manipulación manual de cada sector (ISO 11228-1: 25 kg en condiciones ideales)
    const handRow = (grp, nombre, mass, n) => add({ grp, sys: "est", kind: "geo", name: nombre + ": masa del sector (manipulación manual al desmontar)", formula: "m_sector = m_neta_pieza/n ≤ 25 kg (neta: sin muescas, chaflanes ni juntas)", dem: mass / n, cap: 25, unit: "kg", ref: "ISO 11228-1 (carga manual)" });
    const cutOf = (id) => (R.ifc.cortes || []).find((c) => c.id === id), perSec = (id, fb) => { const c = cutOf(id); return c ? c.m_neta / (c.capas * c.n) : fb; };   // masa neta de un sector (kg)
    const gf = grooveFrac(P);
    const groovesRows = (grp, donde) => {
      if (!(P.h_gr > 0)) return;
      add({ grp, sys: "est", kind: "geo", name: "Engrase: área de las ranuras frente al área de contacto (" + donde + ")", formula: "f_ranuras = A_ranuras/A_contacto ≤ 0,25", dem: gf.f, cap: 0.25, unit: "–", ref: "Criterio del proyecto (la presión neta sube 1/(1 − f))" });
      add({ grp, sys: "est", kind: "info", name: "Engrase: volumen de grasa para llenar las ranuras y N° de graseras", formula: "V = A_ranuras·h; graseras M10×1 en el borde de la plancha inferior de la mesa, taladro Ø6 hasta la ranura exterior, purga por el perímetro bajo el faldón desmontable", dem: gf.V, cap: P.n_greaser, unit: "cm³ / graseras", ref: "Diseño de engrase" });
    };

    /* --- Interfaz con discos de acero inoxidable (A) o discos + lámina UHMW (B) --- */
    if (I.o === 1 || I.o === 2) {
      const REFD = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16 (placa circular empotrada, carga uniforme); 0,6Fy (criterio del proyecto, más conservador que AISC 360-22 F11-1)";
      // disco de la base (liso) y disco de la mesa (con ranuras de engrase en la opción A)
      const discs = discList(P, I);                                      // plancha a la que se sueldan los topes: base (disco de la base) o fondo de la mesa
      discs.forEach((d) => {
        const tEnd = d.t - P.ss_allow - d.g;                                  // espesor útil al final de la vida, sin sobreespesor ni ranura
        add({ grp: "Interfaz inox", sys: "est", name: d.n + ": flexión sobre un vacío local (placa empotrada, carga uniforme)", formula: "σ = 3·q·a²/(4·t²) ≤ 0,6·Fy_inox; a = Ø_vacío/2; t = t_disco − sobreespesor − ranura", dem: 0.75 * I.q * (I.a / tEnd) ** 2, cap: I.sad, unit: "MPa", ref: REFD });
        add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: d.n + ": espesor adoptado frente al requerido", formula: "t_disco ≥ máx(t_flex + sobreespesor + ranura; t_mínimo constructivo)", dem: d.req, cap: d.t, unit: "mm", ref: "Cálculo de espesor (flexión sobre vacío local, desgaste y relapeado, ranuras, fabricación)" });
      });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Disco inoxidable: espesor mínimo por flexión sobre el vacío local", formula: "t_flex = a·√(0,75·q_máx/(0,6·Fy_inox))", dem: I.tFlex, unit: "mm", ref: REFD });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Disco inoxidable: espesor requerido / comercial adoptado (disco de la base)", formula: "t_req = máx(t_flex + sobreespesor; t_mín); espesores comerciales de plancha ASTM A240", dem: I.tssReq, cap: I.tss, unit: "mm", ref: "ASTM A240 (plancha inoxidable)" });
      if (removable) {
        // sectores desmontables: topes soldados al respaldo toman el par; cada sector es libre de dilatarse
        discs.forEach((d) => { stopRows(topeOf(d.id)); screwRow("Interfaz inox", d.n, d.t - P.ss_allow); });
        const chord = 2 * R.Ro * Math.sin(Math.PI / P.n_sec);
        add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Sectores de disco: crecimiento por dilatación de la cuerda (dejar una junta en frío ≥ 1 mm, biselar bordes)", formula: "j = (α_inox − α_acero)·ΔT·cuerda del sector", dem: (AL_SS - AL_S) * dTe * chord, unit: "mm", ref: "Termoelasticidad" });
        handRow("Interfaz inox", "Disco inoxidable", Math.max(...discs.map((d) => perSec(d.id, RHO_SS * I.A_ss * d.t / P.n_sec))) * P.n_sec, P.n_sec);
        add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Soldar los topes antes del alivio de tensiones y del rectificado de las caras; el sector entra por el borde de la mesa izada y se asegura con los tornillos de posición", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      } else {
        const Ttot = R.Tmax, TretF = P.mu_back * R.N * R.r_u / 1e3, TretA = P.tau_bond * R.Ac * R.r_u / 1e6, Tret = Math.max(TretF, TretA);
        add({ grp: "Interfaz inox", sys: "giro", name: "Retención de los discos sobre su plancha de respaldo (la mayor entre fricción y pegado; no se suman)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A·r_u). Un adhesivo rígido falla con deslizamientos de centésimas de mm: la fricción no se moviliza a tiempo", dem: Ttot, cap: Tret, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        const tw = I.tornillos;
        if (tw) {
          const RA = "docs/normas/registro.md, «Tornillos avellanados del disco de la mesa (AF2)»";
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos avellanados disco–mesa: corte (" + tw.n + " × M" + tw.d + " 10.9 en R" + nfx(tw.r, 0) + ", intercalados con los " + P.N_pin + " pasadores)", formula: "f_rv = V/A_b ≤ Fnv/Ω; V = T_dis/(n·r) = " + nfx(tw.V / 1e3, 2) + " kN, Fnv = 0,45·Fu (rosca incluida), Ω = 2,00", dem: tw.V / tw.Ab, cap: tw.capV, unit: "MPa", ref: "AISC 360-22 §J3.7, Tabla J3.2 (grupo 150 ≈ 10.9); " + RA });
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos: aplastamiento en el disco inoxidable de la mesa (avellanado)", formula: "V ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 = " + nfx(tw.te, 2) + " mm, l_c = s − d_h", dem: tw.V / 1e3, cap: tw.RnD / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a); EN 1993-1-8 Tabla 3.4 (espesor con avellanado); " + RA });
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos: aplastamiento en la pieza roscada (" + tw.pieza + ", largo enganchado " + nfx(tw.lEng, 1) + " mm)", formula: "V ≤ R_n/Ω, R_n = mín(1,2·l_c·l_e·Fu; 2,4·d·l_e·Fu), l_c = mín(s − d_h; ligamento al agujero del pasador = " + nfx(tw.lcM, 1) + " mm) en la dirección tangencial de la fuerza", dem: tw.V / 1e3, cap: tw.RnM / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.11 (Ec. J3-6a); " + RA });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: separación entre centros", formula: "3·d ≤ s = cuerda mínima entre tornillos contiguos", dem: 3 * tw.d, cap: tw.s, unit: "mm", ref: "AISC 360-22 §J3.4" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: sin interferencia con los agujeros de los pasadores de empuje", formula: "d_pas/2 + d_h/2 ≤ mín distancia tornillo–pasador = " + nfx(tw.cbp, 1) + " mm (pasadores Ø" + P.d_pin + " en (k + ½)·360°/" + P.N_pin + " sobre R" + P.R_pin + ")", dem: tw.dP / 2 + tw.dh / 2, cap: tw.cbp, unit: "mm", ref: "Geometría; " + RA });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: ligamento libre al agujero del pasador (equivalente a la separación 3d)", formula: "3·d − d_h ≤ c − d_pas/2 − d_h/2 (el ligamento libre entre agujeros que deja una separación de 3d)", dem: 3 * tw.d - tw.dh, cap: tw.ligPin, unit: "mm", ref: "AISC 360-22 §J3.4" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: distancia al borde del agujero del pasador (tratado como borde)", formula: "e_mín (Tabla J3.4M) ≤ c − d_pas/2", dem: J34M(tw.d), cap: tw.ePin, unit: "mm", ref: "AISC 360-22 §J3.5, Tabla J3.4M (desde M16; para menores se toma el valor de M16)" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: distancia al borde exterior del disco y de la mesa", formula: "e_mín (Tabla J3.4M) ≤ R_o − r", dem: J34M(tw.d), cap: tw.eOut, unit: "mm", ref: "AISC 360-22 §J3.5, Tabla J3.4M (desde M16; para menores se toma el valor de M16)" });
          if (tw.enAnillo) add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: distancia al borde interior del anillo inferior (unión con la plancha inferior)", formula: "e_mín (Tabla J3.4M) ≤ r − R_anillo,int, R_anillo,int = " + nfx(tw.rPin, 0) + " mm", dem: J34M(tw.d), cap: tw.eIn, unit: "mm", ref: "AISC 360-22 §J3.5, Tabla J3.4M" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: cabeza avellanada dentro del espesor del disco", formula: "k + 0,5 + sobreespesor de relapeado ≤ t; k = " + nfx(tw.k, 2) + " mm (ISO 10642); el disco de la mesa se dimensiona con este mínimo", dem: tw.k + 0.5 + P.ss_allow, cap: tw.t, unit: "mm", ref: "ISO 10642; criterio del mandante (cabeza ≤ espesor − 0,5 mm), también tras el relapeado" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: engrane de la rosca en la pieza real (" + tw.pieza + ")", formula: "1,25·d ≤ l_e = L − (t − 0,5 − sobreespesor) = " + nfx(tw.lEng, 1) + " mm (" + tw.designacion + (tw.enAnillo ? "; taladro ciego " + nfx(tw.hd, 0) + " mm con remanente " + nfx(tw.tb - tw.hd, 0) + " mm, rosca útil " + nfx(tw.hu, 1) + " mm)" : "; rosca pasante)"), dem: 1.25 * tw.d, cap: tw.lEng, unit: "mm", ref: "VDI 2230-1:2015 (orientativo, 10.9 en acero S355); " + RA });
          if (tw.enAnillo) add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: punta del tornillo dentro de la rosca útil del taladro ciego (no asoma a la luz entre anillos)", formula: "l_e + 2 ≤ rosca útil = taladro − 2·P; taladro = t_anillo − 3 (remanente 3 mm)", dem: tw.lEng + 2, cap: tw.hu, unit: "mm", ref: "Criterio del proyecto (como la fijación de la cubierta W); " + RA });
          if (P.h_gr > 0) add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: cabeza libre de la ranura circunferencial exterior", formula: "holgura (R_ranura − w/2) − (r + d_k/2) ≥ 3 mm", dem: 3, cap: tw.rOut - P.w_gr / 2 - tw.r - tw.dk / 2, unit: "mm", ref: "Geometría" });
          if (P.h_gr > 0 && P.n_gr_rad > 0) add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: cabeza libre de las ranuras radiales (se omiten las bisectrices sobre una ranura: " + (tw.nAuto < P.N_pin ? P.N_pin - tw.nAuto + " de " + P.N_pin : "ninguna") + ")", formula: "w/2 + d_k/2 + 3 ≤ mín distancia lateral del eje a una ranura radial", dem: tw.latLim, cap: tw.latR, unit: "mm", ref: "Geometría" });
          add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "AF2 · Tornillos: designación y geometría (avellanado 90°, intercalados con los pasadores, rosca en la pieza real)", formula: tw.designacion + "; n = " + tw.n + " en las bisectrices entre pasadores (k·360°/" + P.N_pin + ") libres de las ranuras radiales, R" + nfx(tw.r, 0) + "; rosca en " + tw.pieza + "; Ø cabeza " + tw.dk + " mm, prof. " + nfx(tw.k, 2) + " mm", dem: tw.n, cap: tw.r, unit: "– / mm", ref: RA });
        }
        if (P.tau_bond > 0) {
          const eps = (AL_SS - AL_S) * dTe, tb2 = eps * Math.sqrt(P.G_ad * EssT * Math.max(I.tss, I.tss2) / P.t_ad);
          add({ grp: "Interfaz inox", sys: "est", name: "Adhesivo: cortante térmico en el borde del disco (dilatación diferencial)", formula: "τ_borde = ε·√(G_ad·E_inox·t_disco/t_adhesivo), ε = (α_inox − α_acero)·ΔT ≤ τ_adm,cíclico", dem: tb2, cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
        }
        const sth = EssT * (AL_SS - AL_S) * dTe;
        add({ grp: "Interfaz inox", sys: "est", name: "Dilatación diferencial inox–acero: tensión si el disco quedara restringido", formula: "σ = E_inox·(α_inox − α_acero)·ΔT ≤ 0,6·Fy_inox", dem: sth, cap: I.sad, unit: "MPa", ref: "Termoelasticidad; α inox 17,3 y acero 11,7 (×10⁻⁶/K)" });
        add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Fijación permanente (pegado): los discos NO son desmontables sin destruir la unión; no admite limpieza ni cambio", formula: "Alternativa: fijación desmontable por sectores (fix_mode = 1)", dem: 0, unit: "–", ref: "Requisito de mantenimiento del mandante" });
      }
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Dilatación diferencial radial del disco respecto de su respaldo", formula: "Δr = (α_inox − α_acero)·ΔT·R", dem: (AL_SS - AL_S) * dTe * R.Ro, unit: "mm", ref: "Termoelasticidad" });
      if (I.o === 1) groovesRows("Interfaz inox", "disco de la mesa");
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Altura que agrega la interfaz sobre la plancha base", formula: I.o === 2 ? "Δ = t_disco base + t_disco mesa + t_UHMW" : "Δ = t_disco base + t_disco mesa", dem: I.delta, unit: "mm", ref: "Geometría (eje de los cilindros sube Δ)" });
      if (I.o === 1) add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Opción A: par inox–inox con riesgo de gripado si la película de grasa se expulsa: exigir aleaciones o durezas distintas (≥ 50 HB de diferencia) o recubrimiento", formula: "Sin verificación numérica (ASTM G98)", dem: 0, unit: "–", ref: "ASTM G98; decisión del proyectista" });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Masa agregada por la interfaz (discos inoxidables + lámina UHMW)", formula: "m = ρ·A·t", dem: R.m.ss + R.m.uhmw, unit: "kg", ref: "Geometría" });
    }
    if (I.o === 2) {
      const REFU = "Proveedor de UHMW-PE (datos de catálogo, ASTM D4020); confirmar con ensayo";
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: presión de contacto máxima frente a la admisible sostenida", formula: "q_máx ≤ p_adm,UHMW", dem: I.q, cap: P.p_uhmw, unit: "MPa", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "Lámina UHMW: espesor adoptado frente al requerido", formula: "t ≥ máx(E_ap·δ_planitud/(p_adm − q_máx); t_mín constructivo)", dem: I.tuhReq, cap: I.tuh, unit: "mm", ref: REFU });
      if (removable) add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: espesor mínimo por el tope del rebaje / comercial adoptado", formula: "t ≥ a_sup + a_inf + máx(h_c,mín; F_s/(0,9·L·p_adm) + tol_hc); el 0,9 es un margen de proyecto sobre la presión admisible (no lo exige la norma) y tol_hc = " + P.tol_hc + " mm la tolerancia de la altura de contacto", dem: I.tuhTope, cap: I.tuh, unit: "mm", ref: REFU + "; criterio del proyecto (margen 0,9 y tolerancia)" });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: espesor por conformidad de planitud (con módulo confinado) / comercial adoptado", formula: "t_conf = E_c(S)·δ/(p_adm − q_máx); E_c = E[1 + (M/E − 1)S²/(1 + S²)], S = D/(4t), M = E(1−ν)/((1+ν)(1−2ν)), ν = 0,45", dem: I.tuhConf, cap: I.tuh, unit: "mm", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: factor de forma y módulo confinado en el espesor adoptado", formula: "S = D/(4t); E_c(S)", dem: I.SU, cap: I.EcU, unit: "– / MPa", ref: REFU });
      const Fdrag = Math.max(R.mu.d, R.mu.cont, R.mu.dry) * R.N;                     // kN, arrastre de la lámina con el μ máximo
      const dist = P.life * P.turns_yr * 2 * Math.PI * P.r_ef / 1000;              // m deslizados en la vida
      const wear = P.k_wear * 1e-7 * I.q * dist;                                   // mm de desgaste de la cara de la lámina en la vida
      if (removable) {
        const sU = topeOf("uhmw"), Fs = sU.F, gU = stopGeo(P, I.tuh), sigU = gU.hC > 0 ? Fs * 1e3 / (Lav * gU.hC) : Infinity;
        add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW (" + P.n_seg + " sectores): aplastamiento del canto contra el tope del rebaje", formula: "σ = F_sector/(L_canto·h_c) ≤ p_adm,UHMW; h_c = t − a_sup − a_inf; F_sector = μ_máx·N/n·(q_máx/q_med); el espesor se dimensiona con h_c ≥ F_s/(0,9·L·p_adm) + tol_hc (0,9: margen de proyecto, no lo exige la norma)", dem: sigU, cap: P.p_uhmw, unit: "MPa", ref: REFU });
        add({ grp: "Interfaz inox", sys: "est", name: "Tope del rebaje del sector UHMW: soldadura al disco de la base (2 filetes, corte + par de excentricidad)", formula: "f = √[(F/(2aL))² + (F·z/(b·a·L))²] ≤ 0,60FEXX/(1,20Nd); z = a_inf + h_c/2", dem: weldStop(P, Fs, Lav, gU.z), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4; AISC 360-22 J2.4 (resultante); hallazgo T2" });
        stopCommon(sU);                                                  // el tope del rebaje se suelda al disco de la base
        add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "Lámina UHMW: masa del sector (manipulación manual)", formula: "m_sector = m_UHMW_neta/n ≤ 25 kg", dem: R.m.uhmw / P.n_seg, cap: 25, unit: "kg", ref: "ISO 11228-1 (carga manual)" });
      } else add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Opción B: retención de los sectores de UHMW contra el arrastre por fricción (rebaje perimetral o cola de milano en el disco de la base)", formula: "arrastre ≈ μ_máx·N (los pernos no bastan: aplastamiento del UHMW)", dem: Fdrag, unit: "kN", ref: "Equilibrio con el μ máximo; decisión del proyectista" });
      const vcyl = P.Q_pump * 1e6 / 60 / (P.n_cyl * R.A);                          // mm/s, velocidad del vástago
      const vmax = R.Ro / R.K.armMin * vcyl / 1000;                                 // m/s en el borde de la mesa durante la carrera
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: valor PV en el borde de la mesa (durante la carrera)", formula: "PV = q_máx·v; v = R·v_cil/a_mín, v_cil = Q/(n·A)", dem: I.q * vmax, cap: P.PV_uh, unit: "MPa·m/s", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: desgaste en la vida de diseño frente al 20 % del espesor", formula: "h = k·q_máx·s ≤ 0,20·t; s = vida·vueltas/año·2π·r_ef", dem: wear, cap: 0.2 * I.tuh, unit: "mm", ref: REFU });
      const gap = (AL_UH - AL_S) * dTe * 2 * R.Ro * Math.sin(Math.PI / P.n_seg);
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: crecimiento radial del sector (fijar al centro con agujeros ranurados)", formula: "Δr = (α_UHMW − α_acero)·ΔT·R", dem: (AL_UH - AL_S) * dTe * R.Ro, unit: "mm", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: junta de dilatación entre sectores (ancho a dejar en frío)", formula: "j = (α_UHMW − α_acero)·ΔT·cuerda del sector; α_UHMW = 180×10⁻⁶/K", dem: gap, unit: "mm", ref: REFU });
    }

    /* --- Opción C: placa de bronce con tapones de grafito --- */
    if (I.o === 3) {
      const G3 = "Interfaz bronce", REFB = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy (criterio del proyecto, más conservador que AISC 360-22 F11-1); Fy de ASTM B584 / B148 (confirmar con el proveedor)";
      const REFC = "Proveedor de bronce con grafito (datos de catálogo); confirmar con ensayo", conf = I.conf;
      const tEffB = I.tbz - P.bz_allow - P.h_gr;
      add({ grp: G3, sys: "est", name: "Placa de bronce: flexión sobre un vacío local (empotrada, carga uniforme, ligamento entre tapones)", formula: "σ = 3·q_loc·a²/(4·t²·η) ≤ 0,6·Fy_bz; η = (p − d)/p; t = t_placa − sobreespesor; q_loc = q/cobertura", dem: 0.75 * I.qLoc * (I.a / tEffB) ** 2 / I.eta, cap: I.sad, unit: "MPa", ref: REFB });
      add({ grp: G3, sys: "est", kind: "geo", name: "Placa de bronce: espesor adoptado frente al requerido", formula: "t_placa ≥ máx(t_flex/√η + sobreespesor; t_mínimo constructivo)", dem: I.tbzReq, cap: I.tbz, unit: "mm", ref: "Cálculo de espesor (flexión, ligamento de los tapones, desgaste y fabricación)" });
      add({ grp: G3, sys: "est", kind: "info", name: "Placa de bronce: espesor por flexión / requerido / comercial adoptado", formula: "t_flex = a·√(0,75·q_loc/(0,6·Fy_bz)); t_req = t_flex/√η + sobreespesor", dem: I.tFlexB, cap: I.tbz, unit: "mm", ref: REFB });
      add({ grp: G3, sys: "est", kind: "info", name: "Tapones de grafito: fracción de área y eficiencia de ligamento", formula: "f_g = π·d²/(2√3·p²); η = (p − d)/p", dem: I.fg, cap: I.eta, unit: "– / –", ref: "Geometría del patrón escalonado" });
      {   // tapones reales: cuenta por la geometría (franja de borde, muescas, tornillos, ranuras), cobertura de grafito y criterios de lubricación y ligamento
        const T = I.tap, nfT = (v, d) => (+v).toFixed(d).replace(".", ",");
        add({ grp: G3, sys: "est", kind: "info", name: "Tapones de grafito: cantidad real colocable N_real frente a la ideal (malla escalonada que cae en el área útil)", formula: "N_real = centros de la malla (paso " + P.bz_plug_p + " mm, fila alterna p·√3/2) con el borde del tapón a ≥ bz_edge = " + P.bz_edge + " mm del borde del bronce" + (T.n ? " (" + T.n + (conf === 3 ? " pastillas" : " sectores") + ", junta " + nfT(T.junta, 1) + " mm)" : "") + (T.removable ? ", de la muesca del tope ((b_tope + 2) × " + T.L + " mm), de los " + (T.radios.length ? (T.nTor >= 4 ? 4 : 2) : 0) + " tornillos de posición por sector (cabeza ISO 10642 Ø" + T.dk + ")" : "") + " y de las ranuras de engrase; pérdidas por causa (tapones): borde " + T.perdidas.borde + ", muesca " + T.perdidas.muesca + ", tornillos " + T.perdidas.tornillos + ", ranura circ. " + T.perdidas.ranCirc + ", ranura rad. " + T.perdidas.ranRad + "; N_ideal = f_g,ideal·A/(π d²/4)", dem: T.N, cap: I.Nideal, unit: "tapones (real / ideal)", ref: "Geometría; conciliado con el patrón S09 del modelo 3D (cad/modelo3d_tt300c.py)" });
        add({ grp: G3, sys: "est", kind: "info", name: "Tapones de grafito: fracción de área usada en el cálculo (bz_fg_modo) frente a la ideal; real = N_real·π·d²/4/A_contacto", formula: "f_g,real = " + nfT(I.fgReal, 4) + " (cobertura de grafito = π·d²/4·N/A, A = " + (conf === 3 ? "cobertura·" : "") + "A_contacto); f_g,ideal = π·d²/(2√3·p²) = " + nfT(I.fgIdeal, 4) + "; el cálculo usa " + (P.bz_fg_modo > 0.5 ? "la real (bz_fg_modo = 1)" : "la ideal (bz_fg_modo = 0)") + " en masa del bronce, q_neto, PV, desgaste y lubricación; η no cambia", dem: I.fgUsed, cap: I.fgIdeal, unit: "– (usada / ideal)", ref: "Geometría del patrón escalonado" });
        const REFL = "Bronces autolubricados con grafito (catálogos de proveedor): supuesto C, orden de magnitud; confirmar con el catálogo del proveedor (el valor lo fija la ficha)";
        add({ grp: G3, sys: "est", kind: "geo", advisory: !(P.bz_fg_estricto > 0.5), stFix: I.fgUsed >= P.bz_fg_min - 1e-12 ? "ok" : (P.bz_fg_estricto > 0.5 ? "fail" : "warn"),
          name: "Bronce con grafito: cobertura mínima de lubricante sólido (f_g del grafito sobre el área de contacto)", formula: "f_g ≥ bz_fg_min = " + nfT(P.bz_fg_min, 2) + " (supuesto C); " + (P.bz_fg_estricto > 0.5 ? "criterio estricto (bz_fg_estricto = 1): no cumple" : "aviso: el valor es un supuesto y no cambia el veredicto (bz_fg_estricto = 0)"), dem: P.bz_fg_min, cap: I.fgUsed, unit: "–", ref: REFL });
        add({ grp: G3, sys: "est", kind: "geo", name: "Tapones de grafito: ligamento mínimo entre tapones η = (p − d)/p", formula: "η ≥ bz_eta_min = " + nfT(P.bz_eta_min, 2) + " (criterio de proyecto)", dem: P.bz_eta_min, cap: I.eta, unit: "–", ref: "Criterio del proyecto" });
      }
      if (conf === 2) {
        add({ grp: G3, sys: "est", name: "2.ª placa de bronce (maciza, aleación distinta): flexión sobre un vacío local", formula: "σ = 3·q·a²/(4·t²) ≤ 0,6·Fy_bz2; t = t_placa − sobreespesor", dem: 0.75 * I.qC * (I.a / (I.tss - P.bz_allow)) ** 2, cap: I.sadC, unit: "MPa", ref: REFB });
      } else {
        add({ grp: G3, sys: "est", name: "Disco duro: flexión sobre un vacío local (empotrado, carga uniforme)", formula: "σ = 3·q·a²/(4·t²) ≤ 0,6·Fy_cara; t = t_disco − sobreespesor", dem: 0.75 * I.qC * (I.a / (I.tss - P.ss_allow)) ** 2, cap: I.sadC, unit: "MPa", ref: REFB });
      }
      add({ grp: G3, sys: "est", kind: "geo", name: conf === 2 ? "2.ª placa de bronce: espesor adoptado frente al requerido" : "Disco duro: espesor adoptado frente al requerido", formula: "t ≥ máx(t_flex + sobreespesor; t_mínimo constructivo)", dem: I.tssReq, cap: I.tss, unit: "mm", ref: "Cálculo de espesor" });
      add({ grp: G3, sys: "est", name: "Presión de contacto sobre el bronce neto (sin tapones de grafito)", formula: "q_neto = q_máx/(cobertura·(1 − f_g)) ≤ p_adm,bronce", dem: I.qNet, cap: P.p_bz, unit: "MPa", ref: REFC });
      const vcyl = P.Q_pump * 1e6 / 60 / (P.n_cyl * R.A), vmax = R.Ro / R.K.armMin * vcyl / 1000;     // m/s en el borde durante la carrera
      add({ grp: G3, sys: "est", name: "Bronce con grafito: valor PV en el borde de la mesa (durante la carrera)", formula: "PV = q_neto·v; v = R·v_cil/a_mín, v_cil = Q/(n·A)", dem: I.qNet * vmax, cap: P.PV_bz, unit: "MPa·m/s", ref: REFC });
      const dist = P.life * P.turns_yr * 2 * Math.PI * P.r_ef / 1000, wear = P.k_bz * 1e-7 * I.qNet * dist;   // mm
      const tSpare = Math.max(0, I.tbz - I.tbzReq + P.bz_allow);
      add({ grp: G3, sys: "est", name: "Bronce con grafito: desgaste en la vida de diseño frente al espesor de reserva", formula: "h = k·q_neto·s ≤ t_placa − t_flex/√η (reserva); s = vida·vueltas/año·2π·r_ef", dem: wear, cap: Math.max(0, I.tbz - I.tFlexB / Math.sqrt(I.eta)), unit: "mm", ref: REFC });
      add({ grp: G3, sys: "est", kind: "geo", name: "Tapones de grafito: profundidad restante tras el desgaste (≥ 2 mm)", formula: "h + 2 ≤ 0,70·t_placa", dem: wear + 2, cap: PLUG_DEPTH * I.tbz, unit: "mm", ref: "Criterio de proyecto (el grafito debe seguir lubricando)" });
      if (conf !== 2) add({ grp: G3, sys: "est", kind: "geo", name: "Pareja bronce–disco duro: diferencia de dureza", formula: "HB_disco − HB_bronce ≥ 100 (acabado Ra ≤ 0,4 µm)", dem: 100, cap: P.HB_cara - P.HB_bz, unit: "HB", ref: "Práctica de pares deslizantes con bronce" });
      const nB = conf === 3 ? P.bz_npad : P.n_sec;                                  // sectores de bronce: pastillas o sectores de la placa
      const FyC2 = conf === 2 ? P.Fy_bz2 : P.Fy_cara;
      if (removable) {
        stopRows(topeOf("bz0"));                                         // placa de bronce soldada a la base
        stopRows(topeOf("bz1"));                                         // disco duro o 2.ª placa soldados al fondo de la mesa
        screwRow(G3, "Placa de bronce", I.tbz - P.bz_allow - P.h_gr);
        screwRow(G3, conf === 2 ? "2.ª placa de bronce" : "Disco duro", I.tss - (conf === 2 ? P.bz_allow : P.ss_allow));
        const chordB = 2 * R.Ro * Math.sin(Math.PI / nB), chordC = 2 * R.Ro * Math.sin(Math.PI / P.n_sec);
        add({ grp: G3, sys: "est", kind: "info", name: "Sectores de bronce: crecimiento por dilatación de la cuerda (dejar una junta en frío ≥ 1 mm, biselar bordes, sellar)", formula: "j = (α_bz − α_acero)·ΔT·cuerda del sector", dem: (AL_BZ - AL_S) * dTe * chordB, unit: "mm", ref: "Termoelasticidad" });
        add({ grp: G3, sys: "est", kind: "info", name: (conf === 2 ? "Sectores de la 2.ª placa" : "Sectores del disco duro") + ": crecimiento por dilatación de la cuerda (junta en frío ≥ 1 mm)", formula: "j = (α − α_acero)·ΔT·cuerda del sector", dem: ((conf === 2 ? AL_BZ : AL_SS) - AL_S) * dTe * chordC, unit: "mm", ref: "Termoelasticidad" });
        handRow(G3, "Placa de bronce con grafito", perSec("bz0", R.m.bz) * nB, nB);
        handRow(G3, conf === 2 ? "2.ª placa de bronce" : "Disco duro", perSec("bz1", R.m.ss) * P.n_sec, P.n_sec);
        add({ grp: G3, sys: "est", kind: "pend", name: "Soldar los topes antes del alivio de tensiones y del rectificado; sectores atornillados con tornillos de posición, sacables con la mesa izada", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      } else {
        // retención: la placa de bronce fija a la base (la menor área pegada es la de las pastillas)
        const TretF = P.mu_back * R.N * R.r_u / 1e3, TretA = P.tau_bond * R.Ac * I.cov * R.r_u / 1e6, Tret = Math.max(TretF, TretA);
        add({ grp: G3, sys: "giro", name: "Retención de la placa de bronce sobre la base (la mayor entre fricción y pegado; no se suman)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A_pegada·r_u)", dem: R.Tmax, cap: Tret, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        if (P.tau_bond > 0) {
          const tb1 = (AL_BZ - AL_S) * dTe * Math.sqrt(P.G_ad * E_BZ * I.tbz / P.t_ad);
          add({ grp: G3, sys: "est", name: "Adhesivo de la placa de bronce: cortante térmico en el borde", formula: "τ = ε·√(G_ad·E_bz·t/t_adhesivo), ε = (α_bz − α_acero)·ΔT ≤ τ_adm,cíclico", dem: tb1, cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
          const epsC = ((conf === 2 ? AL_BZ : AL_SS) - AL_S) * dTe, EC = conf === 2 ? E_BZ : E_SS;
          add({ grp: G3, sys: "est", name: conf === 2 ? "Adhesivo de la 2.ª placa de bronce: cortante térmico en el borde" : "Adhesivo del disco duro: cortante térmico en el borde", formula: "τ = ε·√(G_ad·E·t/t_adhesivo) ≤ τ_adm,cíclico", dem: epsC * Math.sqrt(P.G_ad * EC * I.tss / P.t_ad), cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
        }
        add({ grp: G3, sys: "est", name: "Dilatación diferencial bronce–acero: tensión si la placa quedara restringida", formula: "σ = E_bz·(α_bz − α_acero)·ΔT ≤ 0,6·Fy_bz", dem: E_BZ * (AL_BZ - AL_S) * dTe, cap: I.sad, unit: "MPa", ref: "Termoelasticidad; α bronce 18, acero 11,7 (×10⁻⁶/K)" });
        if (conf === 2) add({ grp: G3, sys: "est", name: "Dilatación diferencial bronce–acero de la 2.ª placa: tensión si quedara restringida", formula: "σ = E_bz·(α_bz − α_acero)·ΔT ≤ 0,6·Fy_bz2", dem: E_BZ * (AL_BZ - AL_S) * dTe, cap: I.sadC, unit: "MPa", ref: "Termoelasticidad" });
        const TretR = Math.max(P.mu_back * R.N * R.r_u / 1e3, P.tau_bond * R.Ac * R.r_u / 1e6);
        add({ grp: G3, sys: "giro", name: conf === 2 ? "Retención de la 2.ª placa de bronce sobre la mesa (la mayor entre fricción y pegado)" : "Retención del disco duro sobre la mesa (la mayor entre fricción y pegado)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A·r_u)", dem: R.Tmax, cap: TretR, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        add({ grp: G3, sys: "est", kind: "pend", name: "Fijación permanente (pegado): la placa y el disco NO son desmontables sin destruir la unión; no admite limpieza ni cambio", formula: "Alternativa: fijación desmontable por sectores (fix_mode = 1)", dem: 0, unit: "–", ref: "Requisito de mantenimiento del mandante" });
      }
      groovesRows(G3, "placa de bronce");
      add({ grp: G3, sys: "est", kind: "info", name: "Dilatación diferencial radial de la placa respecto de su respaldo (fijar al centro con agujeros ranurados)", formula: "Δr = (α_bz − α_acero)·ΔT·R", dem: (AL_BZ - AL_S) * dTe * R.Ro, unit: "mm", ref: "Termoelasticidad" });
      if (conf === 3) add({ grp: G3, sys: "est", kind: "info", name: "Pastillas de bronce: crecimiento por dilatación de la cuerda de la pastilla (dejar una junta en frío ≥ 1 mm, biselar bordes, sellar)", formula: "j = (α_bz − α_acero)·ΔT·cuerda de la pastilla", dem: (AL_BZ - AL_S) * dTe * 2 * R.Ro * Math.sin(Math.PI / P.bz_npad), unit: "mm", ref: "Termoelasticidad" });
      add({ grp: G3, sys: "est", kind: "info", name: "Altura que agrega la interfaz sobre la plancha base", formula: "Δ = t_bronce + t_disco (o 2.ª placa)", dem: I.delta, unit: "mm", ref: "Geometría (el eje de los cilindros sube Δ)" });
      add({ grp: G3, sys: "est", kind: "info", name: "Masa agregada por la interfaz (bronce con grafito + disco duro o 2.ª placa)", formula: "m = ρ·A·t (bronce descontando los tapones, más el grafito)", dem: R.m.ss + R.m.bz, unit: "kg", ref: "Geometría" });
      add({ grp: G3, sys: "est", kind: "pend", name: "Arranque con adherencia–deslizamiento (stick-slip) a 2,5 mm/s: diferencia entre μ estático y cinético", formula: "Sin verificación numérica; ensayo de arranque tras reposo bajo carga", dem: 0, unit: "–", ref: "Ensayo del proveedor" });
      add({ grp: G3, sys: "est", kind: "pend", name: "Par galvánico bronce–acero en contacto con grasa: sellado perimetral y protección del respaldo", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      if (conf === 2) add({ grp: G3, sys: "est", kind: "pend", name: "Bronce contra bronce (aleaciones distintas): riesgo de gripado; el grafito va solo en una placa", formula: "Sin verificación numérica (ASTM G98)", dem: 0, unit: "–", ref: "ASTM G98; decisión del proyectista" });
      if (conf === 3 && !removable) add({ grp: G3, sys: "est", kind: "pend", name: "Retención de las pastillas de bronce: alojamientos soldados o pegado; la mesa apoya solo en las pastillas", formula: "Arrastre ≈ μ_máx·N", dem: Math.max(R.mu.d, R.mu.cont, R.mu.dry) * R.N, unit: "kN", ref: "Equilibrio; decisión del proyectista" });
    }

    /* --- Masa descontada de las coronas por muescas, chaflanes y juntas entre sectores (4.ª pasada) --- */
    (R.ifc.cortes || []).forEach((c) => {
      const f2 = (v) => v.toFixed(1).replace(".", ",");
      add({ grp: I.o === 3 ? "Interfaz bronce" : "Interfaz inox", sys: "est", kind: "info", name: c.pieza + ": descuento de masa por muescas, chaflanes y juntas entre sectores (incluido en la masa neta m.ss / m.uhmw / m.bz)",
        formula: "m_desc = capas·n·ρ·[V_junta + V_muesca + V_chaflán] = " + c.capas + "·" + c.n + "·" + (c.rho * 1e6).toFixed(3).replace(".", ",") + " g/cm³·[" + f2(c.V_junta) + " + " + f2(c.V_muesca) + " + " + f2(c.V_chaflan) + "] mm³; V_junta = " + (c.strip ? "(b_tope + j)" : "j") + "·(R_o − R_i)·t, j = máx(j_sec; dilatación) = " + c.j.toFixed(1).replace(".", ",") + " mm" + (c.strip ? " (franja libre entre sectores, con la barra del rebaje dentro)" : "") + "; V_muesca = " + (c.strip ? "0 (sin muesca)" : "(b_tope + 2)·L_tope·t, L_tope = " + c.L) + "; V_chaflán = a_inf²·L_tope = 2 cantos × a_inf²/2·L (chaflán 45° en ambos cantos: el par se invierte con el sentido de giro); sin descontar tornillos de posición, ranuras, graseras ni tapones (conservador)",
        dem: c.m_desc, cap: c.m_neta, unit: "kg (descuento / neta)", ref: "Geometría (muesca de la barra b_tope + 2 por L, chaflán a_inf, juntas ≥ 1 mm); conciliación con el modelo 3D" });
    });

    /* --- Cubierta de madera dura W (rebaje) y altura de skidding --- */
    const wg = woodGeo(P), Htop = P.t_base + R.ifc.delta + P.h_disc;   // W: los tablones quedan enrasados con el anillo: la altura no aumenta
    if (wg) {
      const nfw = (v, d) => (+v).toFixed(d == null ? 1 : d).replace(".", ",");
      const RLw = P.D_load / 2, Rab = wg.R_abertura, Rw = wg.R_tablones, Aw = Math.PI * (Math.min(RLw, Rw) ** 2 - Rab * Rab), qTopW = P.phi_d * R.W * 1e3 / (P.f_apoyo * Aw) * (1 + 4 * P.e / RLw);
      const REGW = "docs/normas/registro.md, «Cubierta de madera W (rebaje)»";
      add({ grp: "Cubierta", sys: "est", name: "Madera: aplastamiento perpendicular a la fibra bajo la carga (área de contacto efectiva)", formula: "q = φd·W/(f_apoyo·A)·(1 + 4e/R_carga) ≤ p_adm,madera; A = π·(mín(R_carga; R_tablones)² − R_abertura²), R_abertura = " + nfw(Rab) + " mm (tapa de inspección Ø" + wg.D_tapa_insp + " + holgura); sin acreditar reparto (los tablones apoyan de forma continua en la plancha rebajada: la misma presión en su cara inferior)", dem: qTopW, cap: P.p_wood, unit: "MPa", ref: "Madera dura (datos de proveedor); criterio conservador; " + REGW });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: la ley lineal de presiones no admite tracción (q mín ≥ 0)", formula: "4e/R_carga ≤ 1 (e ≤ D_carga/8)", dem: 4 * P.e / RLw, cap: 1, unit: "–", ref: "Estática del apoyo" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: espesor mínimo (desgaste y fijación)", formula: "t_madera ≥ 30 mm", dem: 30, cap: P.t_wood, unit: "mm", ref: "Práctica constructiva" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: huella de la carga dentro de los tablones", formula: "R_carga = D_carga/2 ≤ R_tablones = R_reb − c_mad = " + nfw(Rw) + " mm (fuera de los tablones la carga caería sobre la holgura y el anillo de acero)", dem: RLw, cap: Rw, unit: "mm", ref: "Geometría; " + REGW });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Masa de la cubierta de madera (gira con la mesa y carga la interfaz)", formula: "m = ρ·t·Σ A_pieza: " + wg.tablones.n + " tablones de " + P.b_tab + " mm (junta " + P.j_tab + " mm) dentro de R_tablones = " + nfw(Rw) + " mm, menos la abertura R = " + nfw(Rab) + " mm sobre la tapa de inspección; " + wg.tablones.n_piezas + " piezas; sin bolsillos (los pasadores quedan en el anillo, fuera del rebaje)", dem: R.m.wood, unit: "kg", ref: "Geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Rebaje de la mesa: masas del anillo superior, la pared y la plancha rebajada (en m.top) y altura de almas y nervios bajo el rebaje", formula: "anillo R" + P.R_reb + "…R" + P.D_top / 2 + " t = " + wg.t_anillo + " (máx(t_pr, t_top), una pieza, " + P.N_pin + " agujeros de pasador): " + nfw(wg.masas.anillo) + " kg; pared R" + P.R_reb + "…R" + wg.R_pared_ext + " × " + nfw(wg.h_pared) + " mm: " + nfw(wg.masas.pared) + " kg; plancha rebajada t = " + wg.t_reb + ", Ø" + wg.hole_top + "…R" + wg.R_reb_ext + ": " + nfw(wg.masas.plancha_rebajada) + " kg; almas y nervios h = " + nfw(wg.hw_reb) + " mm (antes " + nfw(wg.hw) + "); sin el anillo de contención 10×50", dem: R.m.top, cap: wg.hw_reb, unit: "kg (m.top) / mm (h almas)", ref: "Geometría; decisión del mandante (08-11-2026)" });
      // pared en R_reb: momento del modelo FEA escalonado (envolvente de las dos variantes, × k_malla) + desvío del empuje global del ala (N_r·h_c) + apoyo lateral de los tablones (viga empotrada-apoyada)
      const fe = fea && fea.top && fea.top.escalon, gb = fea && fea.glob, Nr = gb ? gb.MrReb / gb.hcTop : 0, Hh = P.k_hmad * P.phi_d * R.W * 1e3, Lc = 2 * Math.min(RLw, Rw), wl = Hh / Lc;
      const Mlat = 3 * wl * wg.h_c / 16, Mjog = Nr * wg.h_c, tp = wg.t_pared, V = Nr + 11 / 16 * wl;
      add({ grp: "Cubierta", sys: "est", name: "Madera: apoyo lateral de los tablones contra la pared (contención del escalón; empuje del skidding)", formula: "σ = H/(L_c·t_madera) ≤ p_adm,madera (perpendicular a la fibra, conservador: los extremos de testa resisten más); H = k_hmad·φd·W = " + nfw(Hh / 1e3, 0) + " kN, L_c = 2·mín(R_carga; R_tablones) = " + nfw(Lc, 0) + " mm", dem: Hh / (Lc * P.t_wood), cap: P.p_wood, unit: "MPa", ref: "Equilibrio; k_hmad supuesto (C); " + REGW });
      if (fe) {
        const sP = P.kFEA * fe.sPared + 6 * (Mjog + Mlat) / (tp * tp), Mb = sP * tp * tp / 6;
        add({ grp: "Cubierta", sys: "est", name: "Pared del rebaje: flexión (FEA escalonada + desvío del ala + empuje lateral de los tablones)", formula: "σ = k_malla·σ_FEA,pared + 6·(N_r·h_c + M_lat)/t_pared²; σ_FEA = " + nfw(fe.sPared) + " MPa (envolvente: anillo con pasadores y pared empotrada), N_r = M_r,glob(R_reb)/h_c,glob = " + nfw(Nr) + " N/mm, h_c = " + nfw(wg.h_c) + " mm, M_lat = 3·(H/L_c)·h_c/16 = " + nfw(Mlat, 0) + " N·mm/mm; ≤ 0,6·Fy como las planchas de la caja (con ASME BTH-1 Fy/Nd = " + nfw(Fy / Nd, 0) + " MPa el FU sería " + nfw(sP / (Fy / Nd), 2) + ": la mesa no es un dispositivo bajo el gancho, ver registro)", dem: sP, cap: sAllW(Fy), unit: "MPa", ref: "criterio del proyecto 0,6Fy (más conservador que AISC 360-22 F11-1), criterio conservador de la mesa; " + REGW });
        add({ grp: "Cubierta", sys: "est", name: "Pared del rebaje: corte (empuje del ala + reacción lateral de los tablones)", formula: "τ = 1,5·V/t_pared, V = N_r + 11/16·H/L_c = " + nfw(V) + " N/mm ≤ 0,6Fy/1,50", dem: 1.5 * V / tp, cap: 0.6 * Fy / 1.5, unit: "MPa", ref: "AISC 360-22 G2.1(a)" });
        const aw = 0.707 * P.w_pared, S1 = wg.soldaduras.J1.S, E1 = Math.max(0, wg.soldaduras.J1.E);
        add({ grp: "Cubierta", sys: "est", name: "Soldadura pared–plancha rebajada (2 filetes): momento de la pared + corte", formula: "f = √[(M/(t_pared·a))² + (V/(2a))²] ≤ 0,6FEXX/2,0; M = σ_pared·t²/6 = " + nfw(Mb, 0) + " N·mm/mm, a = 0,707·w_pared (brazo t_pared, conservador); con ASME BTH-1 §3-3.4 (0,6FEXX/(1,2Nd) = " + nfw(P.FEXX * 0.6 / (1.2 * Nd), 1) + " MPa) el FU sería " + nfw(Math.hypot(Mb / (tp * aw), V / (2 * aw)) / (P.FEXX * 0.6 / (1.2 * Nd)), 2), dem: Math.hypot(Mb / (tp * aw), V / (2 * aw)), cap: FwA, unit: "MPa", ref: "AISC 360-22 J2.4, Ec. J2-4 (como las soldaduras de la mesa); " + REGW });
        add({ grp: "Cubierta", sys: "est", name: "Soldadura anillo–pared (PJP en bisel desde el rebaje + filete exterior): momento de la pared + corte", formula: "f = √[(M/(t_pared·mín(a; E)))² + (V/(a + E))²] ≤ 0,6FEXX/2,0; PJP S = " + S1 + " mm, E = S − 3 = " + E1 + " mm (AISC 360-22 Tabla J2.1, 45°, SMAW/FCAW); filete exterior a = 0,707·" + P.w_pared, dem: Math.hypot(Mb / (tp * Math.max(1e-9, Math.min(aw, E1))), V / (aw + E1)), cap: FwA, unit: "MPa", ref: "AISC 360-22 J2.1, J2.4 y Tabla J2.5 (PJP con tracción normal al eje: 0,6FEXX); " + REGW });
        add({ grp: "Mesa (FEA)", sys: "est", kind: "info", name: "Piel escalonada (W): variante que gobierna, σ del anillo y flecha de la plancha rebajada", formula: "modelo desarrollado (plancha rebajada + pared de ancho L_dev + anillo): variantes «anillo» (L_dev = " + nfw(fe.variantes[0].L_dev) + ") y «empotrada» (L_dev = " + nfw(fe.variantes[1].L_dev) + "); gobierna «" + fe.gobierna + "»; σ_anillo = " + nfw(fe.sAnillo) + " MPa (modelado con t_reb)", dem: fea.top.wMax, cap: fe.sAnillo, unit: "mm / MPa", ref: "Modelo escalonado validado (tests/test_tt300c.js, tests/indep_madera.py); " + REGW });
        const nW = 2 * P.turns_yr * P.life;
        if (nW <= 20000) add({ grp: "Cubierta", sys: "est", kind: "info", name: "Fatiga: pared del rebaje y sus soldaduras (N = " + Math.round(nW) + " ≤ 20 000)", formula: "N = 2 ciclos de carga por vuelta (carga y descarga) × vueltas/año × vida; clase de servicio 0: no requiere verificación", dem: nW, unit: "ciclos", ref: "AISC 360-22 Apéndice 3, A-3.1 (N ≤ 20 000); ASME BTH-1 §3-4" });
        else add({ grp: "Cubierta", sys: "est", name: "Fatiga: pared del rebaje (pie del filete pared–plancha rebajada, cat. E, N = " + Math.round(nW) + ")", formula: "Δσ = σ_pared ≤ F_SR = (Cf/N)^0,333 ≥ F_TH", dem: sP, cap: FSR("E", nW), unit: "MPa", ref: "AISC 360-22 Apéndice 3, Tabla A-3.1" });
      }
      const T2 = Math.max(tp, wg.t_reb), T1 = Math.max(tp, wg.t_anillo), wReq = Math.max(Math.min(wMin(T2), Math.min(tp, wg.t_reb)), Math.min(wMin(T1), Math.min(tp, wg.t_anillo)));
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: filete mínimo pared–plancha rebajada y de refuerzo anillo–pared", formula: "w_mín(T = máx(t_pared; t_reb) = " + T2 + ") y w_mín(T = máx(t_pared; t_anillo) = " + T1 + ") ≤ w_pared; no más que la parte más delgada", dem: wReq, cap: P.w_pared, unit: "mm", ref: REFWMIN });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: filete máximo según el canto de la pared", formula: "w_pared ≤ w_máx(t_pared = " + tp + ")", dem: P.w_pared, cap: wMax(tp), unit: "mm", ref: "AISC 360-22 §J2.2b" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: penetración parcial anillo–pared cabe en la altura libre de la pared", formula: "S = t_pared/2 = " + wg.soldaduras.J1.S + " ≤ h_pared = t_madera − t_anillo (bisel 45°)", dem: wg.soldaduras.J1.S, cap: wg.h_pared, unit: "mm", ref: "AWS D1.1/D1.1M:2020 (precalificadas PJP, bisel simple); geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: tablones libres del filete interior de la pared", formula: "w_pared + 2 ≤ c_mad", dem: P.w_pared + 2, cap: P.c_mad, unit: "mm", ref: "Geometría" });
      const dist = Math.min(...parseRings(P.rings).map((r) => r < P.R_reb ? P.R_reb - r : r > wg.R_pared_ext ? r - wg.R_pared_ext : 0));
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: alma bajo la pared (apoyo de la plancha rebajada en R_reb y de la pared)", formula: "distancia del alma anular más cercana a la franja de la pared [R_reb; R_reb + t_pared] ≤ t_alma/2 (el modelo escalonado supone w = 0 en R_reb)", dem: dist, cap: P.t_web / 2, unit: "mm", ref: "Geometría; hipótesis del FEA escalonado" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: nervios dentro de la zona rebajada (sin cambio de altura)", formula: "R_nervio ≤ R_reb + t_pared: los nervios terminan en el alma de R_reb con la altura h_reb = " + nfw(wg.hw_reb) + " mm; ninguna alma cambia de altura (las de r ≤ R_pared bajan d_rebaje = " + nfw(wg.d_rebaje) + " mm)", dem: P.R_rib, cap: wg.R_pared_ext, unit: "mm", ref: "Geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: plancha rebajada libre de los pasadores", formula: "R_reb_ext = R_reb + t_pared + w_pared + 5 ≤ R_pin − d_pin/2 − 5", dem: wg.R_reb_ext, cap: P.R_pin - P.d_pin / 2 - 5, unit: "mm", ref: "Geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: arandelas de los pasadores sobre el anillo, fuera del rebaje (sin bolsillos en los tablones)", formula: "R_reb + t_pared ≤ R_pin − (d_pin + 30)/2 (arandela Ø d_pin + 30, cad/geom.py)", dem: wg.R_pared_ext, cap: P.R_pin - (P.d_pin + 30) / 2, unit: "mm", ref: "Geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Rebaje: tapa retenedora y tapa de inspección en la plancha rebajada (accesibles por la abertura de los tablones)", formula: "3 (pivote sobre la cara inferior) + 6 (tapa retenedora mínima) + 1 + 8 (tapa de inspección en su rebaje) ≤ t_reb; abertura de los tablones Ø" + nfw(2 * Rab, 0) + " ≥ tapa Ø" + wg.D_tapa_insp + " + 2·c_mad", dem: 18, cap: wg.t_reb, unit: "mm", ref: "Geometría (cad/geom.py: cb_t = 8, cap_t = t − 12)" });
      // fijación de los tablones
      const fx = wg.fijacion;
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Fijación de los tablones: largo comercial del tornillo ISO 4762 con engrane ≥ 1,0·d sin tocar el fondo del taladro ciego", formula: "M" + fx.d + "×" + (fx.L || "—") + ": engrane = L − (t_madera − h_cajeado) = " + nfw(fx.engrane) + " mm ≥ d; punta ≥ 2 mm antes del fin de la rosca útil (" + nfw(fx.rosca_util) + " mm = taladro " + nfw(fx.prof_taladro) + " − 4); cajeado Ø" + fx.D_cajeado + " × " + nfw(fx.h_cajeado) + " (cabeza 3 mm bajo la superficie, arandela ISO 7093 Ø" + fx.d_arandela + ")", dem: fx.d, cap: fx.L ? fx.engrane : 0, unit: "mm", ref: "ISO 4762; ISO 7093-1; VDI 2230 (engrane en acero ≥ 1,0·d para 8.8); hallazgo de los planos (Ø8×80 no cabía)" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Fijación de los tablones: espesor mínimo de la plancha rebajada para el roscado ciego", formula: "1,0·d (engrane) + 2 (punta) + 4 (salida del macho y punta de broca) + 3 (remanente: la caja queda cerrada) ≤ t_reb", dem: fx.d + 9, cap: wg.t_reb, unit: "mm", ref: "Criterio de fabricación (como la tapa de inspección, cad/geom.py)" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Fijación de los tablones: el tornillo de 80 mm de la versión anterior no cabía en 50 + 20 mm (madera + plancha)", formula: "L = 80 > t_madera + t_plancha = 70: pasaba 10 mm a la caja; ahora M" + fx.d + "×" + fx.L + " en cajeado y taladro ciego", dem: 80, cap: 70, unit: "mm", ref: "Revisión de planos (MAD-001)" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Fijación de los tablones: cantidad, separaciones y par de apriete", formula: fx.n_total + " tornillos; ≥ 2 filas por pieza a ≥ 7d = " + fx.e_extremo + " mm de los extremos y ≤ " + P.s_tmad + " mm entre filas; 2 por fila a " + fx.e_borde + " mm de los cantos si el tablón tiene ≥ " + (2 * fx.e_borde + 4 * fx.d) + " mm (EN 1995-1-1 §8.5, de memoria); apriete hasta F = 0,8·p_madera·A_arandela = " + nfw(fx.apriete_kN, 2) + " kN (T ≈ 0,2·F·d)", dem: fx.n_total, cap: fx.par_Nm, unit: "– / N·m", ref: "Propuesta (confirmar con el mandante)" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: holgura perimetral frente a la dilatación transversal de la cubierta (ΔT de diseño)", formula: "(α_madera,⊥ − α_acero)·ΔT·2·R_tablones ≤ 2·c_mad + (n − 1)·j_tab; α⊥ = 30×10⁻⁶ (C), ΔT = " + P.dT + " K; la humedad (hinchamiento ≈ 0,2 %/% de humedad) se deja como pendiente", dem: Math.max(0, TH_AL.woodT - AL_S) * P.dT * 2 * Rw, cap: 2 * P.c_mad + (wg.tablones.n - 1) * P.j_tab, unit: "mm", ref: "Termoelasticidad; " + REGW });
      add({ grp: "Cubierta", sys: "est", kind: "pend", name: "Rebaje: drenaje del agua que entra entre los tablones (la plancha rebajada es una bandeja), humedad, pudrición y acabado antideslizante", formula: "Sin verificación numérica: proponer tubos de drenaje desde el fondo del rebaje al canto exterior de la mesa", dem: 0, unit: "–", ref: "Decisión del mandante" });
    }
    add({ grp: "Geometría", sys: "est", kind: "info", name: "Altura total sobre el piso (base + interfaz + mesa + cubierta)", formula: "H = t_base + Δ_interfaz + h_mesa (cubierta W: los tablones van enrasados en el rebaje y no suman altura)", dem: Htop, unit: "mm", ref: "Geometría" });
    if (P.h_skid > 0) add({ grp: "Geometría", sys: "est", kind: "geo", name: "Enrase de la superficie superior con los rieles de skidding", formula: "|H − h_riel| ≤ tolerancia", dem: Math.abs(Htop - P.h_skid), cap: P.tol_skid, unit: "mm", ref: "Compatibilidad con el sistema de skidding" });

    /* --- Mesa --- */
    const sAll = 0.6 * Fy;
    if (fea) {
      const k = P.kFEA;
      const fW = wg ? " (W: plancha rebajada t_reb = " + wg.t_reb + " mm bajo los tablones, modelo escalonado desarrollado con la pared y el anillo)" : "";
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha superior: σvm local (carga con e)", formula: "MITC4 × k_malla" + fW, dem: fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "criterio del proyecto 0,6Fy (más conservador que AISC 360-22 F11-1), criterio conservador" });
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha inferior: σvm local (contacto q_max)", formula: "MITC4 × k_malla", dem: fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "criterio del proyecto 0,6Fy (más conservador que AISC 360-22 F11-1), criterio conservador" });
      const gb = fea.glob;
      add({ grp: "Mesa", sys: "est", name: "Plancha superior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local" + (wg ? "; W: t = t_reb, h_c = h_mesa − t_madera − (t_reb + t_bot)/2 = " + gb.hcTop + " mm (el cajón es más bajo dentro de R_reb; sin aporte de la madera)" : ""), dem: gb.sigTop + fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      add({ grp: "Mesa", sys: "est", name: "Plancha inferior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local" + (wg ? "; W: h_c = " + gb.hcTop + " mm dentro de R_reb" : ""), dem: gb.sigBot + fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      const hw = wg ? wg.hw_reb : P.h_disc - P.t_top - P.t_bot;   // W: nervios bajo la plancha rebajada
      const tau = gb.Vmax * 1e3 / (P.N_rib * P.t_rib * hw);
      const lam = hw / P.t_rib, lamLim = 2.24 * Math.sqrt(P.E / Fy);
      add({ grp: "Mesa", sys: "est", name: "Corte en nervios radiales", formula: "τ = V/(N·t·h_w) ≤ 0,6Fy/1,50 (h/t ≤ 2,24√(E/Fy))", dem: tau, cap: 0.6 * Fy / (lam <= lamLim ? 1.50 : 1.67), unit: "MPa", ref: "AISC 360-22 G2.1(a), Ec. G2-1" });
      const qv = Math.max(fea.top.lineMax, fea.bot.lineMax);
      const qh = gb.Vmax * 1e3 / (P.N_rib * hw);
      const fw = Math.hypot(qh, qv) / (2 * 0.707 * P.w_web);
      add({ grp: "Mesa", sys: "est", name: "Soldadura alma/nervio–plancha (2 filetes)", formula: "f = √(q_h² + q_v²)/(2·0,707·w) ≤ 0,6FEXX/2,0", dem: fw, cap: FwA, unit: "MPa", ref: "AISC 360-22 J2.4, Ec. J2-4" });
      add({ grp: "Mesa", sys: "est", name: "Fluencia local de almas por carga de línea", formula: "σ = q_v / t ≤ Fy/1,50", dem: qv / Math.min(P.t_web, P.t_rib), cap: Fy / 1.5, unit: "MPa", ref: "AISC 360-22 J10.2" });
      add({ grp: "Mesa (FEA)", sys: "est", kind: "geo", name: "Equilibrio FEA (ΣF = ΣR)", formula: "|ΣF − ΣR| / ΣF ≤ 0,5 %", dem: Math.abs(fea.bot.Fapp - fea.bot.Rsum) / fea.bot.Fapp * 100 + 0.0001, cap: 0.5, unit: "%", ref: "Control numérico" });
    }

    /* --- Tamaño mínimo de filete según espesor de la parte más gruesa (wMin definido arriba, junto a los topes) --- */
    add({ grp: "Base", sys: "est", kind: "geo", name: "Espesor de la plancha base frente al mínimo por planitud", formula: "t_base_mín ≤ t_base", dem: P.t_base_min, cap: P.t_base, unit: "mm", ref: "Criterio de fabricación (planitud 0,20 de la cara de giro)" });
    const Tw = Math.max(wg ? wg.t_reb : P.t_top, P.t_bot), Tb = Math.max(P.t_base, P.t_ch);   // W: almas soldadas a la plancha rebajada
    add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo almas/nervios–planchas", formula: "w_mín(T = " + Tw + ") ≤ w ≤ t_alma", dem: wMin(Tw), cap: Math.min(P.w_web, Math.min(P.t_web, P.t_rib)), unit: "mm", ref: REFWMIN });
    if (mode === 1) add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo mejillas–base", formula: "w_mín(T = máx(t_base; t_mejilla) = " + Tb + ") ≤ w_br; el mínimo no excede la parte más delgada (" + Math.min(P.t_base, P.t_ch) + " mm)", dem: Math.min(wMin(Tb), Math.min(P.t_base, P.t_ch)), cap: P.w_br, unit: "mm", ref: REFWMIN });
    if (mode === 1) add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete máximo mejillas–base según el borde de la mejilla", formula: "w_br ≤ w_máx(t_mejilla = " + P.t_ch + ") (t < 6: t; t ≥ 6: t − 2 mm): la mejilla es la parte que termina en el borde; la plancha base (" + P.t_base + " mm) se suelda por su cara, donde J2.2b no limita el cateto", dem: P.w_br, cap: wMax(P.t_ch), unit: "mm", ref: "AISC 360-22 §J2.2b (tamaño máximo del filete a lo largo de bordes)" });

    /* --- Pasadores de empuje (cadena de empuje a fuerza de calado) --- */
    const tpr = Math.max(P.t_pr, P.t_top, P.t_bot), Ls = P.h_disc - tpr;
    const Fpr = Fs * Math.hypot(1, P.mu_s);                             // resultante con la fricción radial de la cara de la uña
    // Carga repartida en la altura de la uña (c = h_uña), centrada en la luz con excentricidad accidental e.
    // Pasador biapoyado en los anillos: el empotramiento que puede dar el agujero del anillo (aplastamiento sobre el espesor t,
    // descontado el corte) es una fracción menor del perfecto y no se cuenta; se informa como referencia.
    const c = Math.min(P.dog_h, Ls), Vp = Fpr * (0.5 + P.e_dog / Ls);                       // kN
    const Mss = Fpr / 4 * (Ls - c / 2) / 1e3, Mfix = Fpr * (3 * Ls * Ls - c * c) / (24 * Ls) / 1e3;   // kN·m
    const sbA = 1.25 * Fy / Nd, sV = Vp * 1e3 / (P.d_pin * tpr);
    const Me = Math.max(0, Math.min(Mfix, (sbA - sV) * P.d_pin * tpr * tpr / 6 / 1e6));
    const Mp = Mss;
    const Sp = Math.PI * P.d_pin ** 3 / 32, Ap = Math.PI * P.d_pin ** 2 / 4;
    add({ grp: "Pasadores de empuje", sys: "est", name: "Flexión (biapoyado entre anillos, carga repartida en la altura de la uña)", formula: "M = F_r·(L − c/2)/4, c = h_uña, F_r = F·√(1 + μ_s²); σ = M/S ≤ Fy/Nd", dem: Mp * 1e6 / Sp, cap: P.Fy_pin / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    add({ grp: "Pasadores de empuje", sys: "est", kind: "info", name: "Empotramiento disponible en el anillo / empotramiento perfecto (no se considera)", formula: "M_e = (σ_adm − V/(d·t))·d·t²/6; M_emp = F_r(3L² − c²)/(24L)", dem: Me / Mfix, unit: "–", ref: "Modelo del pasador" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Corte en el apoyo", formula: "τ = 4V/(3A), V = F_r·(1/2 + e/L) ≤ Fy/(Nd·√3)", dem: 4 * Vp * 1e3 / (3 * Ap), cap: P.Fy_pin / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento en el agujero del anillo", formula: "σ = V/(d·t) ≤ 1,25Fy/Nd", dem: sV, cap: sbA, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento en pasadores)" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento pasador–uña", formula: "σ = F/(d·h_uña) ≤ 1,25·Fy_mín/Nd (pivotado: h = alto del bloque-uña)", dem: Fs * 1e3 / (P.d_pin * (mode === 2 ? P.pv_hu : P.dog_h)), cap: 1.25 * Math.min(P.Fy_pin, P.Fy_dog) / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });

    let lev = 0, Sdog = 1, aw = 1, hax = R.hax, Spp = 1;   // usados por la fatiga del modo guiado
    if (mode === 1) {
      /* --- Uña (cara de empuje plana, templada) --- */
      const Adog = P.dog_b * P.dog_h, Hs = P.mu_s * Fs;                  // fricción radial máxima en la cara (a calado)
      lev = K.lever + P.e_dog; Sdog = P.dog_h * P.dog_b ** 2 / 6;
      add({ grp: "Uña", sys: "est", name: "Flexión en la boca del patín (voladizo) con fricción radial", formula: "σ = [F·(x_boca − a_mín + e) + μ_s·F·b/2]/(h·b²/6) + μ_s·F/(h·b) ≤ Fy/Nd", dem: (Fs * lev + Hs * P.dog_b / 2) * 1e3 / Sdog + Hs * 1e3 / Adog, cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      add({ grp: "Uña", sys: "est", name: "Corte en la boca del patín", formula: "τ = 1,5·F/(h·b) ≤ Fy/(Nd·√3)", dem: 1.5 * Fs * 1e3 / Adog, cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
      const Es = P.E / (2 * (1 - P.nu ** 2)), rp = P.d_pin / 2;
      const qE = P.k_edge * Fs * 1e3 / P.dog_h;                          // carga lineal máxima (borde de la cara)
      const p0 = Math.sqrt(qE * Es / (Math.PI * rp)), bH = Math.sqrt(4 * qE * rp / (Math.PI * Es));
      add({ grp: "Uña", sys: "est", name: "Contacto de Hertz cara plana–pasador (a calado; ambas caras templadas)", formula: "p₀ = √(q·E*/(π·r)), q = k_borde·F/h, E* = E/(2(1−ν²)) ≤ 1,67·Fy_sup (cara con alivio de borde)", dem: p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: "Hertz, contacto lineal; inicio de fluencia por Tresca (p₀ = 1,67σy)" });
      add({ grp: "Uña", sys: "est", kind: "info", name: "Profundidad mínima de temple (3 × profundidad del corte máximo)", formula: "z = 3·0,78·b, b = √(4q·r/(π·E*))", dem: 3 * 0.78 * bH, unit: "mm", ref: "Hertz, contacto lineal" });
      const ch = chamferGeo(P);
      add({ grp: "Uña", sys: "est", kind: "geo", name: "Chaflán de retorno: cabe en la uña dejando la punta", formula: "Δy = recorrido/tan β; Δy + b_punta ≤ b_uña", dem: ch.dy + P.b_tip, cap: P.dog_b, unit: "mm", ref: "Geometría (retorno del trinquete)" });
      // flexión y corte en la zona del chaflán: ancho w(u) = b − Δy·(1 − u/Δx), u medido desde la punta; carga en u = c_punta
      let sChMax = 0;
      for (let i = 1; i <= 40; i++) { const u = P.c_tip + (ch.dx - P.c_tip) * i / 40, w = P.dog_b - ch.dy * Math.max(0, 1 - u / ch.dx); sChMax = Math.max(sChMax, 6 * Fs * 1e3 * (u - P.c_tip) / (P.dog_h * w * w)); }
      const wC = P.dog_b - ch.dy * Math.max(0, 1 - P.c_tip / ch.dx);
      add({ grp: "Uña", sys: "est", name: "Corte en la sección del contacto (punta achaflanada)", formula: "τ = 1,5·F/(h·w_c), w_c = b − Δy(1 − c_punta/Δx) ≤ Fy/(Nd·√3)", dem: 1.5 * Fs * 1e3 / (P.dog_h * wC), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
      add({ grp: "Uña", sys: "est", name: "Flexión en la zona del chaflán", formula: "σ = máx 6F(x − a)/(h·w(x)²) ≤ Fy/Nd", dem: sChMax, cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      const bR = P.beta_ch * Math.PI / 180, mr = P.mu_ret, kR = 1 + 2 * Math.max(0, K.mouthX - (K.tipX + ch.dx / 2)) / P.L_in;
      add({ grp: "Giro", sys: "giro", name: "Retorno sin autobloqueo de la uña (chaflán contra el pasador siguiente)", formula: "μ·k·(sin β + μ cos β) < cos β − μ sin β, k = 1 + 2·l/L_in", dem: mr * kR * (Math.sin(bR) + mr * Math.cos(bR)), cap: Math.cos(bR) - mr * Math.sin(bR), unit: "–", ref: "Equilibrio con fricción del trinquete" });

      /* --- Patín: alojamiento de la uña --- */
      const lL = lev, cL = -lL + Math.sqrt(lL * lL + lL * P.L_in + P.L_in ** 2 / 2), sLip = Fs * 1e3 / (P.dog_h * (2 * cL - P.L_in));
      add({ grp: "Patín y guía", sys: "est", name: "Aplastamiento del alojamiento de la uña (bloque rígido-plástico)", formula: "c = −l + √(l² + l·L_in + L_in²/2); σ = F/(h·(2c − L_in)) ≤ 1,25Fy_patín/Nd", dem: sLip, cap: 1.25 * P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento; verificar)" });
      if (K.inset > 0) {
        const Vw = Math.min(Fs, sLip * P.dog_h * Math.min(K.inset, cL) / 1e3), Hw = P.dog_h + 20;
        add({ grp: "Patín y guía", sys: "est", name: "Pared del marco de boca: flexión (voladizo del marco)", formula: "σ = 6V·(i/2)/((h+20)·t²), V = mín(F; σ_al·h·mín(i, c))", dem: 6 * Vw * 1e3 * K.inset / 2 / (Hw * P.t_fw ** 2), cap: P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
        add({ grp: "Patín y guía", sys: "est", name: "Pared del marco de boca: corte", formula: "τ = 1,5V/((h+20)·t) ≤ Fy/(Nd·√3)", dem: 1.5 * Vw * 1e3 / (Hw * P.t_fw), cap: P.Fy_shoe / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
      }

      /* --- Patín y bancada (reacciones de guía con fricción radial, a calado) --- */
      const Rg = R.Rguide, qG = 4 * Rg * 1e3 / K.L_s;                   // presión lineal máxima (distribución triangular por mitad)
      add({ grp: "Patín y guía", sys: "est", name: "Aplastamiento de la lengüeta en la ranura (pico de la distribución lineal)", formula: "R = máx[F_pas·Δ + H·(y_c − y_r)]/Lg; σ = 4R/((h_ranura − 2)·L_patín) ≤ 1,25Fy/Nd", dem: qG / (P.h_slot - 2), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento; verificar)" });
      const tRoot = (P.w_bed - Math.max(P.w_slot, P.h_tee > 0 ? P.w_tee : 0)) / 2;
      const armW = P.h_tee + P.h_slot / 2 + 1;                           // del centroide del contacto en el cuello a la raíz (fondo de la cabeza T)
      add({ grp: "Patín y guía", sys: "est", name: "Pared de la ranura: flexión en la raíz", formula: "σ = 6·(4R/L_patín)·(h_T + h_ranura/2 + 1)/t_raíz², t_raíz = (w_b − w_T)/2 ≤ Fy/Nd", dem: 6 * qG * armW / tRoot ** 2, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      add({ grp: "Patín y guía", sys: "est", kind: "geo", name: "Fondo de la ranura de la bancada", formula: "t_bancada − h_ranura − h_T ≥ 12", dem: 12, cap: P.t_bed - P.h_slot - P.h_tee, unit: "mm", ref: "Criterio de fabricación (la bancada trabaja como una pieza)" });
      const Leff = Math.min(K.L_bed, K.L_s + 2 * P.w_bed), awb = 0.707 * P.w_bed_f;
      add({ grp: "Patín y guía", sys: "est", name: "Soldadura bancada–base (2 filetes longitudinales)", formula: "f = R/(2·0,707·w·L_ef), L_ef = L_patín + 2·w_bancada", dem: Rg * 1e3 / (2 * awb * Leff), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4" });
      // retención vertical: vuelco por la fricción radial H (eje x) y cabeceo por la fricción de guía (eje y), brazo z_eje − z_lengüeta
      const zT = P.t_base + P.t_bed - P.h_slot / 2, dz = K.zc0 - zT, SM = R.stallMax;
      const Mroll = SM.H * dz / 1e3, Mpitch = P.mu_g * SM.Rsum * dz / 1e3;          // kN·m
      const Vup = Mroll * 1e3 / ((P.w_bed + P.w_tee) / 2) + Mpitch * 1e3 / K.L_s;      // kN
      if (P.h_tee > 0) {
        const ov = (P.w_tee - P.w_slot) / 2;
        add({ grp: "Patín y guía", sys: "est", kind: "geo", name: "Ranura T: cabeza más ancha que el cuello", formula: "w_T ≥ w_ranura + 2·8", dem: P.w_slot + 16, cap: P.w_tee, unit: "mm", ref: "Geometría" });
        add({ grp: "Patín y guía", sys: "est", name: "Retención vertical del patín: aplastamiento en la cabeza T", formula: "V = M_vuelco/((w_b + w_T)/2) + M_cabeceo/L_patín; σ = V/(ala·L_patín) ≤ 1,25Fy/Nd", dem: Vup * 1e3 / (ov * K.L_s), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento; verificar)" });
        add({ grp: "Patín y guía", sys: "est", name: "Retención vertical: flexión del ala de la cabeza T", formula: "σ = 6V·(ala/2)/(L_patín·h_T²) ≤ Fy/Nd", dem: 6 * Vup * 1e3 * ov / 2 / (K.L_s * P.h_tee ** 2), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
        add({ grp: "Patín y guía", sys: "est", name: "Retención vertical: flexión del labio de la bancada sobre la cabeza T", formula: "σ = 6V·(ala/2)/(L_patín·h_ranura²) ≤ Fy/Nd", dem: 6 * Vup * 1e3 * ov / 2 / (K.L_s * P.h_slot ** 2), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      } else {
        const Wsh = R.m.shoes / P.n_cyl * G / 1e3;
        add({ grp: "Patín y guía", sys: "est", name: "Patín sin retención vertical: vuelco frente al peso propio", formula: "M_vuelco = H·Δz ≤ W_patín·w_bancada/2 (requiere ranura T)", dem: Mroll, cap: Wsh * P.w_bed / 2 / 1e3, unit: "kN·m", ref: "Equilibrio (revisión independiente H2)" });
      }
      add({ grp: "Patín y guía", sys: "est", kind: "info", name: "Factor de guía equivalente K = F_cil·n·a_mín/T (máximo en la carrera)", formula: "incluye μg en la guía y μ_s en la cara de la uña", dem: R.Kguide, unit: "–", ref: "Equilibrio del patín" });

      /* --- Articulaciones (ojal en la base y pasador del vástago) --- */
      const App = Math.PI * P.d_pp ** 2 / 4; Spp = Math.PI * P.d_pp ** 3 / 32;
      const Mpp = Fs / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) / 1e3;
      add({ grp: "Articulaciones", sys: "est", name: "Pasador: flexión (horquilla)", formula: "M = F/2·(t/2 + g + b/4); σ ≤ Fy/Nd", dem: Mpp * 1e6 / Spp, cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / 3-2.3" });
      add({ grp: "Articulaciones", sys: "est", name: "Pasador: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 * 1e3 / App, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
      add({ grp: "Articulaciones", sys: "est", name: "Aplastamiento en mejillas", formula: "σ = (F/2)/(d·t) ≤ 1,25Fy/Nd", dem: Fs / 2 * 1e3 / (P.d_pp * P.t_ch), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
      const bgx = bracketGeo(P), aSh = bgx.rear - P.d_pp / 2;
      add({ grp: "Articulaciones", sys: "est", name: "Oreja superior de la ménsula: desgarro por corte tras el agujero", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = saliente − d/2", dem: Fs / 2 * 1e3 / (2 * P.t_ch * aSh), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (simplificado, 2 planos de corte)" });
      add({ grp: "Articulaciones", sys: "est", kind: "info", name: "Ojal comercial del cilindro: admitir pasador y carga", formula: "Ø ojal ≥ d_pp; ancho = b_ojal (confirmar con ficha)", dem: P.d_pp, unit: "mm", ref: "Ficha del fabricante" });
          const Mch = Fs / 2 * hax / 1e3;
      add({ grp: "Articulaciones", sys: "est", name: "Mejilla de la ménsula: flexión en la base", formula: "σ = (F/2)·h_eje/(t·L²/6) ≤ Fy/Nd", dem: Mch * 1e6 / (P.t_ch * P.L_ch ** 2 / 6), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      aw = 0.707 * P.w_br;
      const fV = Fs * 1e3 / (4 * aw * P.L_ch), fM = Fs * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6);
      add({ grp: "Articulaciones", sys: "est", name: "Soldadura mejillas–base (4 filetes)", formula: "f = √(fV² + fM²) ≤ 0,60FEXX/(1,20Nd)", dem: Math.hypot(fV, fM), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4" });
      guidedBasePlateRows(P, R, add);

      camGuidedRows(P, R, add);
    } else pivRows(P, R, add);

    /* --- Pivote --- */
    // asimetría: modo guiado = roce desigual de los patines (μg ± 0,05); pivotado = roce desigual en el contacto uña–pasador (μ_s ± 0,05) del par de cilindros
    const Hasym = mode === 1 ? R.Fstall * P.eta_c * Math.max(...[-1, 1].map((e) => Math.abs(1 / asymF(P, P.mu_g - 0.05, e) - 1 / asymF(P, P.mu_g + 0.05, e)))) : pivAsym(P, R).H;
    // Con un número impar de cilindros el empuje no es un par puro: la fuerza tangencial sobre el pasador (F_pas) no se equilibra y el pivote
    // reacciona con una fuerza igual. Diseño para la presión del buje y calado para la flexión del pivote (cadena BTH-1).
    const rs = Math.hypot(1, P.mu_s);                                                              // resultante de F_pas y la fricción H = μ_s·F_pas de la cara
    const odd = P.n_cyl % 2 === 1, HcilD = odd ? Math.max(...R.stroke.map((q) => q.Fp)) * rs : 0, HcilS = odd ? R.stallMax.Fp * rs : 0;
    const H = Math.max(R.H_ecc(R.mu.d), P.Ch * R.N) + Hasym + HcilD, Hf = Math.max(R.H_ecc(R.mu.d), P.Ch * R.N) + Hasym + HcilS;
    if (odd) add({ grp: "Pivote", sys: "est", kind: "info", name: "Reacción del pivote por empuje no equilibrado (n° impar de cilindros): F_pas de diseño / de calado", formula: "H_cil = F_pas·√(1 + μ_s²) (el par no es puro con 1 o 3 cilindros; el n° 3 se trata como un cilindro: geometría no definida)", dem: HcilD, cap: HcilS, unit: "kN", ref: "Equilibrio de la mesa" });
    if (mode === 2) { const pa = pivAsym(P, R); add({ grp: "Pivote", sys: "est", kind: "info", name: "Pivotado: componente radial de la fuerza en el pasador tomado (por cilindro, diseño y calado) y neta del par al pivote", formula: "F_rad = F_n·(P·u)/R + roce μ_s·F_n·(t·r̂); con el par de cilindros en la diagonal las componentes radiales se anulan y al pivote solo llega la asimetría H_asim (fila siguiente)", dem: pa.FradD, cap: pa.FradS, unit: "kN (diseño / calado)", ref: "Equilibrio de la mesa; docs/normas/registro.md «Accionamiento pivotado tipo KIET»" }); }
    if (mode === 2) add({ grp: "Pivote", sys: "est", kind: "info", name: "Empuje neto al pivote por roce desigual en el contacto uña–pasador del par (μ_s ± 0,05), a calado", formula: "H_asim = máx_θ |F₁(μ_s + 0,05) + F₂(μ_s − 0,05)|, F_i = F_n,i·(u_i + s·μ_i·t_i) con F_n,i = F_calado·η/(1 + μ_leva·μ_i); los cilindros están a 180°", dem: Hasym, unit: "kN", ref: "Equilibrio de la mesa (análogo a la revisión independiente H10)" });
    else add({ grp: "Pivote", sys: "est", kind: "info", name: "Empuje neto al pivote por fricción desigual de los patines (μg ± 0,05)", formula: "H_asim = F_calado·η·|1/f(μg−0,05) − 1/f(μg+0,05)|", dem: Hasym, unit: "kN", ref: "Equilibrio (revisión independiente H10)" });
    add({ grp: "Pivote", sys: "est", name: "Presión en el buje", formula: "p = H/(D·L), H = máx(fricción excéntrica; Ch·N) + H_asim + H_cil", dem: H * 1e3 / (P.D_piv * P.L_bush), cap: P.p_bush, unit: "MPa", ref: "Fabricante del buje" });
    const eP = R.ePiv;                                                         // brazo efectivo: holgura del buje sobre el collar + L_buje/2 (e_piv de ingreso es un mínimo)
    add({ grp: "Pivote", sys: "est", kind: "info", name: "Brazo efectivo del pivote e (desde la cara superior del asiento hasta la reacción del buje)", formula: "e = máx(e_piv; g_buje + L_buje/2); el buje apoya a media altura con holgura axial g_buje sobre el collar", dem: eP, cap: P.g_bush + P.L_bush / 2, unit: "mm (efectivo / geométrico)", ref: "Estática del pivote; ASME BTH-1 §3-2.3" });
    add({ grp: "Pivote", sys: "est", name: "Flexión del pivote", formula: "σ = H·e/(πD³/32) ≤ Fy/Nd, e = brazo efectivo (H con la F_pas de calado si el n° de cilindros es impar)", dem: Hf * 1e3 * eP / (Math.PI * P.D_piv ** 3 / 32), cap: P.Fy_piv / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    // camino de fuerza del pivote: la misma reacción atraviesa el cubo (buje), el vástago y el agujero de la plancha base (calado, BTH-1)
    const Lseat = P.t_base + P.h_boss;                                        // profundidad del asiento: plancha base + collar soldado
    add({ grp: "Pivote", sys: "est", name: "Aplastamiento del pivote en el asiento (plancha base + collar, ajuste H7/p6)", formula: "σ = H/(D_piv·L_asiento) ≤ 1,25·Fy/Nd; H con la F_pas de calado si el n° de cilindros es impar", dem: Hf * 1e3 / (P.D_piv * Lseat), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    {   // momento H·(e + L/2) sobre el asiento (modelo lineal rígido): σ = H/(D·L)·(1 + 6(e + L/2)/L); L mínimo por bisección
      const sM = (L) => Hf * 1e3 / (P.D_piv * L) * (1 + 6 * (eP + L / 2) / L), cap = 1.25 * Fy / Nd;
      let lo = P.t_base, hi = 2000; for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (sM(m) > cap) lo = m; else hi = m; }
      add({ grp: "Pivote", sys: "est", name: "Asiento del pivote con momento H·e (plancha base + collar; profundidad mínima " + (sM(Lseat) <= cap ? Math.min(Lseat, Math.ceil(hi)) : Math.ceil(hi)) + " mm)", formula: "σ = H/(D·L)·(1 + 6(e + L/2)/L) ≤ 1,25·Fy/Nd, e = brazo efectivo, H = H de calado (aprox. de asiento rígido-lineal, sin pretensión del calado ni filetes)", dem: sM(Lseat), cap, unit: "MPa", ref: "ASME BTH-1 §3-3.3; hallazgo P6 de la revisión independiente" });
    }
    if (P.h_boss > 0) {
      const hg = R.hubG, Drb = hg.Drb, wallC = (P.D_boss - P.D_piv) / 2;
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar del pivote: pared del collar ≥ 30 mm (D_collar ≥ D_piv + 60)", formula: "D_piv + 60 ≤ D_collar", dem: P.D_piv + 60, cap: P.D_boss, unit: "mm", ref: "Criterio de fabricación" });
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar del pivote: pared del rebaje del cubo ≥ 25 mm (D_collar + 2·c_r + 50 ≤ D_cubo)", formula: "D_rebaje = D_collar + 2·c_boss_r (el cubo gira, el collar es fijo; mismo Ø en el agujero de la plancha inferior); D_rebaje + 50 ≤ D_cubo: pared del cubo y ligamento de la plancha ≥ 25 mm", dem: Drb + 50, cap: P.D_hub, unit: "mm", ref: "Criterio de fabricación (holgura de giro cubo–collar)" });
      add({ grp: "Pivote", sys: "est", kind: "info", name: "Rebaje del cubo para el collar: Ø D_collar + 2·c_boss_r × (h_collar − δ + c_boss_a) desde la cara inferior de la mesa", formula: "Ø rebaje = D_collar + 2·c_boss_r (agujero de la plancha inferior); profundidad = h_collar − δ + c_boss_a = " + hg.hRaw.toFixed(1).replace(".", ",") + " mm, δ = " + hg.delta + " mm que suma la interfaz (la plancha inferior, t_bot = " + P.t_bot + " mm, lleva un agujero pasante de ese Ø y el resto, si lo hay, se rebaja en el cubo; negativo: el collar queda bajo la mesa y no hay rebaje)", dem: Drb, cap: hg.hRaw, unit: "mm (Ø / profundidad)", ref: "Geometría (holgura de giro cubo–collar; la interfaz sube la cara inferior de la mesa δ)" });
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Interfaz: R_i libre del rebaje del collar y del agujero de la plancha (R_i ≥ D_collar/2 + c_boss_r + m_ri)", formula: "R_i = D_collar/2 + c_boss_r + m_ri; el anillo de contacto, los discos y la plancha de bronce arrancan fuera del rebaje con un margen de borde m_ri = " + P.m_ri + " mm", dem: Drb / 2 + P.m_ri, cap: R.Ri, unit: "mm", ref: "Geometría (la interfaz no puede ocupar el espacio del collar)" });
      {   // el anillo de contacto R_i … r_cubo apoya directamente bajo la pared del cubo (plancha inferior de t_bot sobre el pie del cubo): compresión de la pared entre el rebaje y D_cubo
        const rh = P.D_hub / 2, Awall = rh * rh - (Drb / 2) ** 2, Aring = Math.max(0, rh * rh - R.Ri * R.Ri);
        add({ grp: "Pivote", sys: "est", name: "Plancha inferior y pared del cubo junto al rebaje: aplastamiento de la pared del cubo bajo la presión de contacto del anillo interior", formula: "σ = q_máx·(r_cubo² − R_i²)/(r_cubo² − r_rebaje²) ≤ Fy/Nd (la presión sobre R_i … r_cubo entra por el pie del cubo; ligamento = (D_cubo − Ø rebaje)/2 = " + hg.wall + " mm)", dem: R.q_max * Aring / Awall, cap: P.Fy / P.Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento); estática del pie del cubo" });
      }
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Buje sobre el collar: el buje cabe bajo la plancha " + (P.opt_wood > 0.5 ? "rebajada (cubierta W)" : "superior"), formula: P.opt_wood > 0.5 ? "h_collar + g_buje + L_buje ≤ δ + h_disc − t_madera − t_reb (el cubo y el pivote llegan a la plancha rebajada)" : "h_collar + g_buje + L_buje ≤ δ + h_disc − t_top", dem: P.h_boss + P.g_bush + P.L_bush, cap: R.ifc.delta + topUnder(P), unit: "mm", ref: "Geometría" });
      // Equilibrio del collar con el MISMO asiento rígido-lineal que da σ (no la simplificación V = H, M = H(e + L/2)): z desde la cara superior del collar,
      // w(z) = H/L·[1 + k(1 − 2z/L)], k = 6(e + L/2)/L, fuerza por unidad de profundidad (ΣF = H y ΣM_centro = H(e + L/2)). El collar (0 ≤ z ≤ h) recibe
      // V_c = ∫w dz y M_c = ∫w·(h − z) dz respecto del plano de la soldadura (cara superior de la base); la plancha base (h ≤ z ≤ L) toma la reacción de signo contrario.
      const Lc = Lseat, hc = P.h_boss, kc = 6 * (eP + Lc / 2) / Lc;
      const Vc = Math.abs(Hf * 1e3 / Lc * (hc + kc * (hc - hc * hc / Lc))), Mc = Math.abs(Hf * 1e3 / Lc * ((1 + kc) * hc * hc / 2 - kc * hc ** 3 / (3 * Lc)));   // N y N·mm
      const awc = 0.707 * P.w_collar, fbC = Mc / (Math.PI * P.D_boss ** 2 / 4 * awc), fvC = Vc / (Math.PI * P.D_boss * awc);
      add({ grp: "Pivote", sys: "est", name: "Soldadura del collar a la base (filete perimetral): V_c y M_c del asiento rígido-lineal", formula: "f = √(f_b² + f_v²) ≤ 0,60FEXX/(1,2·Nd); f_b = M_c/(π·D²/4·a), f_v = V_c/(π·D·a), a = 0,707·w_collar; V_c = H/L·[h + k(h − h²/L)], M_c = H/L·[(1 + k)h²/2 − k·h³/(3L)], k = 6(e + L/2)/L (V_c ≈ " + nfx(Vc / (Hf * 1e3), 3) + "·H con L = t_base + h_collar = " + nfx(Lc, 0) + " mm)", dem: Math.hypot(fbC, fvC), cap: Fw, unit: "MPa", ref: "AWS D1.1 / AISC 360-22 J2.4 (grupo circular, método elástico; resultante vectorial de corte y flexión)" });
      add({ grp: "Pivote", sys: "est", kind: "info", name: "Carga del collar sobre su filete: V_c y M_c (respecto de la cara superior de la base)", formula: "V_c y M_c de la distribución rígido-lineal del asiento; la plancha base toma la reacción de signo contrario", dem: Vc / 1e3, cap: Mc / 1e6, unit: "kN / kN·m", ref: "Equilibrio del collar" });
      const wallE = Math.min(wallC, P.h_boss);
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar: filete mínimo según la parte más gruesa (pared del collar o plancha base)", formula: "w_mín(T = máx(pared del collar = " + wallC + "; t_base = " + P.t_base + ")) ≤ w_collar; no más que la parte más delgada", dem: Math.min(wMin(Math.max(wallC, P.t_base)), Math.min(wallC, P.t_base)), cap: P.w_collar, unit: "mm", ref: REFWMIN });
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar: filete máximo según el borde del collar", formula: "w_collar ≤ w_máx(t) con t = mín(pared del collar; h_collar) = " + wallE + " (t < 6: t; t ≥ 6: t − 2 mm)", dem: P.w_collar, cap: wMax(wallE), unit: "mm", ref: "AISC 360-22 §J2.2b (tamaño máximo del filete a lo largo de bordes)" });
    }
    add({ grp: "Pivote", sys: "est", name: "Aplastamiento del buje en el cubo de la mesa (Ø exterior del buje = D_piv + 30)", formula: "σ = H/((D_piv + 30)·L_buje) ≤ 1,25·Fy/Nd", dem: Hf * 1e3 / ((P.D_piv + 30) * P.L_bush), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    if (!(P.Ch > 0)) add({ grp: "Pivote", sys: "est", kind: "info", name: "Caso sísmico: no aplica", formula: "Sin requerimiento sísmico (decisión del mandante, 31-10-2026); si se instala en forma permanente, ingresar Ch", dem: 0, unit: "–", ref: "Decisión del mandante" });

    /* --- Base --- */
    if (fea && fea.lift) {
      add({ grp: "Base", sys: "est", name: "Izaje del conjunto: σvm en la plancha base", formula: "MITC4 × k_malla, φ_izaje; máximo a ≥ 2·pad del cáncamo (la esquina de la placa de apoyo es singular)", dem: fea.lift.vmMax * P.kFEA, cap: sAll, unit: "MPa", ref: "criterio del proyecto 0,6Fy (más conservador que AISC 360-22 F11-1)" });
      add({ grp: "Base", sys: "est", kind: "geo", name: "Izaje: flecha de la base", formula: "w ≤ B/300", dem: fea.lift.wMax, cap: P.B / 300, unit: "mm", ref: "Criterio del proyecto" });
    }
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje fuera de la mesa", formula: "D/2 + 10 + 35 ≤ √(x_izaje² + (B/2 − c)²) (huella Ø70)", dem: P.D_top / 2 + 45, cap: Math.hypot(P.x_lug, P.B / 2 - P.c_lug), unit: "mm", ref: "Geometría" });
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje dentro del marco", formula: "t_marco + 35 ≤ c", dem: P.rim_t + 35, cap: P.c_lug, unit: "mm", ref: "Geometría" });
    const mt = R.m.total;
    {   // orejas de izaje soldadas: 3 ramales efectivos a 60° respecto de la horizontal, carga en el plano de la oreja
      const T = mt * P.phi_lift * G / 1e3 / (3 * Math.sin(60 * D2R)), Tv = T * Math.sin(60 * D2R), Th = T * Math.cos(60 * D2R);   // kN
      const dp = P.d_ear - P.g_ear, Ln = 2 * P.R_ear, aw = 0.707 * P.w_ear, Sw = 2 * aw * Ln * Ln / 6;
      { const BC = baseClearOf(P, R), wTxt = (o) => (o && o.who ? " (mínimo: " + o.who.join(" – ") + ")" : ""), REGI = "Geometría (planta); docs/normas/registro.md, «Elementos sobre la base: holguras (10-11-2026)»";
        if (BC.earMov) add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Orejas de izaje libres de las partes móviles del accionamiento (cuerpo y vástago del cilindro, bloque-uña y cubo de Q) en todo el empuje y el retorno, ambos sentidos y cilindros", formula: "mín dist(huella de la oreja; huellas móviles en " + BC.nMov / 5 + " estados) ≥ 5 mm (la oreja llega a h + R = " + (P.h_ear + P.R_ear) + " mm: comparte cota con todas las partes)" + wTxt(BC.earMov), dem: 5, cap: BC.earMov.d, unit: "mm", ref: REGI });
        if (BC.earPlate) add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Orejas de izaje libres de las placas-guía, los soportes del ojal E y la mesa", formula: "mín dist(huella de la oreja; placas-guía, piezas de los soportes E, círculo R = D/2) ≥ 5 mm" + wTxt([BC.earPlate, BC.earSup, BC.earMesa].reduce((a, b) => (b.d < a.d ? b : a))), dem: 5, cap: Math.min(BC.earPlate.d, BC.earSup.d, BC.earMesa.d), unit: "mm", ref: REGI });
        if (BC.earDrive) add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Orejas de izaje libres del accionamiento guiado (bancadas y prolongaciones, patines, cilindros, riel-leva y pórticos) y de la mesa", formula: "mín dist(huella de la oreja; banda del accionamiento de cada lado y círculo R = D/2) ≥ 5 mm" + wTxt(BC.earDrive.d < BC.earMesa.d ? BC.earDrive : BC.earMesa), dem: 5, cap: Math.min(BC.earDrive.d, BC.earMesa.d), unit: "mm", ref: REGI });
      }
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: aplastamiento del agujero (pasador del grillete d − g)", formula: "σ = T/(d_p·t) ≤ 1,25·Fy/Nd", dem: T * 1e3 / (dp * P.t_ear), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3; ASME B30.26 (grillete)" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: tracción en la sección neta del agujero", formula: "σ = T/(2(R − d/2)·t) ≤ Fy/Nd", dem: T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1; AISC 360-22 D2" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: desgarro por corte detrás del agujero", formula: "τ = T/(2(R − d/2)·t) ≤ Fy/(Nd·√3)", dem: T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6; AISC 360-22 D5" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: soldadura a la base (filete a ambos lados, T vertical + T horizontal con brazo h)", formula: "f = √[(Tv/(2aL) + Th·h/S)² + (Th/(2aL))²] ≤ 0,60FEXX/(1,2Nd); L = 2R, a = 0,707w, S = 2aL²/6", dem: Math.hypot(Tv * 1e3 / (2 * aw * Ln) + Th * 1e3 * P.h_ear / Sw, Th * 1e3 / (2 * aw * Ln)), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4; AISC 360-22 J2.4" });
      // placa de la oreja en la base (sección 2R × t): flexión en su plano por Th·h y tracción por Tv; corte por Th
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: placa en la base: flexión Th·h + tracción Tv", formula: "σ = Th·h/(t·(2R)²/6) + Tv/(2R·t) ≤ Fy/Nd", dem: Th * 1e3 * P.h_ear / (P.t_ear * Ln * Ln / 6) + Tv * 1e3 / (Ln * P.t_ear), cap: Fy / Nd, unit: "MPa", ref: "AISC 360-22 D2; ASME BTH-1 §3-2.1 y §3-2.3" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: placa en la base: corte Th", formula: "τ = Th/(2R·t) ≤ Fy/(Nd·√3)", dem: Th * 1e3 / (Ln * P.t_ear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.3.6" });
      // AISC 360-22 D5.2 (miembros con pasador): b_e = mín(2t + 16 mm; (2R − d)/2) (D5.1); a = R − d/2 (extremo semicircular centrado en el agujero)
      const be = Math.min(2 * P.t_ear + 16, (Ln - P.d_ear) / 2);
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: extensión a tras el agujero ≥ 1,33·b_e (AISC D5.2(3))", formula: "a = R − d/2 ≥ 1,33·b_e; b_e = mín(2t + 16; (2R − d)/2) = " + be.toFixed(1).replace(".", ",") + " mm", dem: 1.33 * be, cap: P.R_ear - P.d_ear / 2, unit: "mm", ref: "AISC 360-22 §D5.2(3) (extensión mínima más allá del extremo de apoyo del agujero, paralela a la fuerza)" });
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: ancho de la placa en el agujero ≥ 2·b_e + d (AISC D5.2(3))", formula: "2R ≥ 2·b_e + d", dem: 2 * be + P.d_ear, cap: Ln, unit: "mm", ref: "AISC 360-22 §D5.2(3)" });
      add({ grp: "Orejas de izaje", sys: "est", kind: P.ear_gira > 0.5 ? "geo" : "info", name: "Oreja: holgura agujero–pasador ≤ 1 mm si el pasador gira bajo carga plena (AISC D5.2(2))", formula: P.ear_gira > 0.5 ? "g = d − d_pasador ≤ 1 mm" : "g = d − d_pasador = " + P.g_ear + " mm; no aplica el límite de 1 mm (izaje estático: el pasador no gira bajo la carga plena); con ear_gira = 1 exige ≤ 1 mm", dem: P.g_ear, cap: 1, unit: "mm", ref: "AISC 360-22 §D5.2(2)" });
      // filete: mínimo AWS D1.1 Tabla 7.7 por la parte más gruesa (AISC J2.4 lo da por la más delgada; el mínimo no excede la parte más delgada), máximo AISC J2.2b en el borde de la oreja
      { const INSo = R.K.ok ? cornerInsertOf(P, R) : null, onIns = INSo && INSo.ok && earPolys(P).some((e) => INSo.corners.some((pl) => PG.inside(pl, e.centro))), tS = onIns ? Math.max(P.t_base, INSo.t) : P.t_base;   // orejas de las diagonales del soporte: soldadas sobre el inserto
        add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: filete mínimo según la parte más gruesa (oreja o plancha base" + (onIns ? " o inserto de esquina" : "") + ")", formula: "w_mín(T = máx(t_oreja; t_asiento) = " + Math.max(P.t_ear, tS) + ") ≤ w_oreja; no más que la parte más delgada" + (onIns ? " (las orejas de las diagonales del soporte van sobre el inserto de " + INSo.t + " mm)" : ""), dem: Math.min(wMin(Math.max(P.t_ear, tS)), Math.min(P.t_ear, tS)), cap: P.w_ear, unit: "mm", ref: REFWMIN }); }
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: filete máximo según el borde de la placa", formula: "w_oreja ≤ w_máx(t_oreja) (t < 6: t; t ≥ 6: t − 2 mm)", dem: P.w_ear, cap: wMax(P.t_ear), unit: "mm", ref: "AISC 360-22 §J2.2b (tamaño máximo del filete a lo largo de bordes)" });
      add({ grp: "Orejas de izaje", sys: "est", kind: "info", name: "Tensión por oreja (3 ramales efectivos a 60°) y WLL mínimo del grillete", formula: "T = m·φ·g/(3·sen 60°)", dem: T, unit: "kN", ref: "ASME B30.9; B30.26" });
      const dLug = Math.hypot(P.x_lug, P.B / 2 - P.c_lug);
      add({ grp: "Orejas de izaje", sys: "est", kind: "info", name: "Ramales: longitud mínima para un ángulo ≥ 60° sobre la horizontal (el 60° es una cota mínima)", formula: "ángulo ≥ 60° (cota mínima) ⇒ L ≥ d/cos 60° = 2·d (d = distancia oreja–eje = " + dLug.toFixed(0) + " mm; altura del vértice ≥ d·tan 60°): ramales más cortos bajan el ángulo y suben T = W/(n·sen θ) y Th; en las cifras de arriba el ángulo es 60°", dem: dLug / Math.cos(60 * D2R), cap: dLug * Math.tan(60 * D2R), unit: "mm (longitud mínima / altura del vértice)", ref: "ASME B30.9 (factor de ángulo 1/sen θ); B30.26" });
    }
    add({ grp: "Base", sys: "est", kind: "info", name: "WLL requerido por cáncamo (eslinga 4 ramales, 3 efectivas, 60°)", formula: "m·φ / (3·sin 60°)", dem: mt * P.phi_lift / (3 * Math.sin(60 * D2R)) / 1000, unit: "t", ref: "ASME B30.9 (3 ramales efectivos)" });

    /* --- Fatiga --- */
    const nCyc = P.N_pin * P.turns_yr * P.life, nPin = 2 * P.turns_yr * P.life;
    const Fd = cd.F;                                                  // fuerza de operación (rango de tensiones)
    const fat = (name, sig, cat, N) => {
      if (N <= 20000) add({ grp: "Fatiga", sys: "est", kind: "info", name: name + " (N = " + Math.round(N) + " ≤ 20 000)", formula: "Clase de servicio 0: no requiere verificación", dem: N, unit: "ciclos", ref: "ASME BTH-1 §3-4 / AISC 360-22 A-3.1" });
      else add({ grp: "Fatiga", sys: "est", name: name + " (cat. " + cat + ", N = " + Math.round(N) + ")", formula: (cat === "F" ? "Δτ ≤ F_SR = (Cf/N)^0,167 ≥ F_TH" : "Δσ ≤ F_SR = (Cf/N)^0,333 ≥ F_TH"), dem: sig, cap: FSR(cat, N), unit: "MPa", ref: "AISC 360-22 Apéndice 3, Ec. A-3-1, Tabla A-3.1" });
    };
    fat("Pasadores de empuje", Fd * Ls / 4 * 1e3 / Sp, "A", nPin);
    if (mode === 1) {
      fat("Uña (boca del patín)", Fd * 1e3 * lev / Sdog, "A", nCyc);
      fat("Pasadores de articulación", Fd / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) * 1e3 / Spp, "A", nCyc);
      fat("Pie de soldadura mejilla–base", Fd / 2 * 1e3 * hax / (P.t_ch * P.L_ch ** 2 / 6), "E", nCyc);
      fat("Garganta soldadura mejilla–base (corte)", Math.hypot(Fd * 1e3 / (4 * aw * P.L_ch), Fd * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6)), "F", nCyc);
    } else if (K.ok && R.sup && R.blk) {
      const f = pivFat(P, R, Fd);
      fat("Bloque-uña (cuerpo acodado)", f.blk, "A", nCyc);
      fat("Pasadores de articulación E y Q", f.pin, "A", nCyc);
      fat("Pie de la CJP pared–base del soporte del ojal E (cat. E, conservador)", f.toe, "E", nCyc);
      fat("Garganta de la PJP tapa–paredes del soporte del ojal E (corte)", f.thr, "F", nCyc);
      const CP = R.camP;
      if (CP && CP.guia && CP.Hpt) {   // placa-guía: rango de tensión del ligamento con la carga de diseño del empuje (cada carrera carga y descarga la placa)
        const sb = CP.sb, b = CP.Hpt.lig, tc = P.pv_tcam, sOp = 6 * (CP.Tdis * sb / 4) / (tc * b * b), Ab = Math.PI / 4 * P.pv_db ** 2, eb = CP.guia.eb, dh = P.pv_db + 1;
        fat("Placa-guía: recorte con radio ≥ 25 mm (borde cortado térmicamente y fresado)", sOp, "C", nCyc);
        fat("Placa-guía: sección neta en los agujeros de los tornillos", CP.Tdis / Math.max(1, (CP.bolts.length)) / ((2 * eb - dh) * (tc - 0.28 * P.pv_db)), "D", nCyc);
      }
    }

    if (P.__th) thermalRows(P, R, fea, out, add);                      // escenario térmico (TT.thermal): filas del grupo «Temperatura»
    out.forEach((c) => {
      if (c.kind === "info") c.st = "info";
      else if (c.kind === "pend") c.st = "pend";
      else if (!isFinite(c.fu)) c.st = "fail";
      else if (c.kind === "geo" || c.sys === "giro") c.st = c.fu <= 1 ? "ok" : "fail";   // límites con margen propio
      else c.st = c.fu <= 0.9 ? "ok" : c.fu <= 1 ? "warn" : "fail";
      if (c.stFix) c.st = c.stFix;                                   // filas térmicas con criterio de estado propio (monitoreo, aviso de falta de alivio)
      if (P.__th && P.__th.alc !== 2 && c.grp !== "Temperatura" && ACC_GRPS.includes(c.grp)) c.fuera = true;   // accionamiento mecánico: fuera del alcance térmico (se calcula, no entra al veredicto)
    });
    return out;
  }

  /* FEA de la mesa con caché: con apoyos rígidos la solución es lineal en q y, en flexión, σ ∝ q/t².
     Se usa solo en la búsqueda del optimizador; la confirmación final corre una FEA nueva. */
  function discCached(P, R, which, opts) {
    if (!opts.cache || (which === "top" && P.opt_wood > 0.5)) return runDisc(P, R, which, opts.coarse);   // W: la escala σ ∝ q/t² no vale para el modelo escalonado
    const RL = Math.min(P.D_load / 2, P.D_top / 2);
    const q = which === "top" ? P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL) : R.qc;
    const t = which === "top" ? P.t_top : P.t_bot;
    const key = which + JSON.stringify([P.N_rib, P.D_hub, P.D_top, P.rings, P.R_rib, P.R_pin, P.d_pin, P.N_pin, P.D_load, P.E, P.nu, !!opts.coarse]);
    let c = opts.cache.get(key);
    if (!c) { c = { q, t, res: runDisc(P, R, which, opts.coarse) }; opts.cache.set(key, c); }
    const kq = q / c.q, ks = kq * (c.t / t) ** 2;
    return Object.assign({}, c.res, { vmMax: c.res.vmMax * ks, lineMax: c.res.lineMax * kq, ringLine: c.res.ringLine.map((v) => v * kq),
      ribLine: c.res.ribLine * kq, Fapp: c.res.Fapp * kq, Rsum: c.res.Rsum * kq, scaled: c.t !== t || c.q !== q });
  }

  /* ---------------- Análisis completo ---------------- */
  function analyze(P, opts) {
    opts = opts || {};
    if ((P.opt_ss > 0.5) + (P.opt_uhmw > 0.5) + (P.opt_bz > 0.5) > 1) throw new Error("Las opciones de interfaz A (opt_ss), B (opt_uhmw) y C (opt_bz) son excluyentes");
    const R = compute(P);
    let fea = null;
    if (R.K.ok && !opts.noFEA) {
      fea = opts.fea || { top: discCached(P, R, "top", opts), bot: discCached(P, R, "bot", opts), glob: globalBending(P, R), lift: runLift(P, R, opts.coarse) };   // opts.fea: FEA ya resuelto (escenario térmico: la tensión FEA no depende de Fy)
    }
    const checks = verifs(P, R, fea);
    const bad = (sys) => checks.filter((c) => c.sys === sys && c.st === "fail" && !c.fuera);   // fuera: filas del accionamiento y del circuito hidráulico con term_alcance = 1
    const warn = (sys) => checks.filter((c) => c.sys === sys && c.st === "warn" && !c.fuera);
    // Pendientes críticos (docs/qa/plancha_base_soporte_E.md §4): filas con estado «pend» y FU > 1 (p. ej. la plancha base bajo el soporte E sin anclaje,
    // a la espera de la decisión del mandante). No entran a `estructura` (resume las verificaciones resueltas; el generador de planos la usa) ni al FU
    // gobernante de TT.thermal, pero el estado global no dice «cumple»: queda «NO CUMPLE / PENDIENTE DE DECISIÓN» con la lista de las filas. Una decisión
    // pendiente del diseño lo es en cualquier escenario: las filas fuera del alcance térmico (accionamiento con term_alcance = 1) también se listan, marcadas.
    const pendCrit = checks.filter((c) => c.st === "pend" && c.kind !== "info" && c.fu != null && !(isFinite(c.fu) && c.fu <= 1))
      .map((c) => Object.assign({ grp: c.grp, nombre: c.name, fu: c.fu, sys: c.sys, ref: c.ref }, c.fuera ? { fuera_alcance_termico: true } : {})).sort((a, b) => (isFinite(b.fu) ? b.fu : 1e99) - (isFinite(a.fu) ? a.fu : 1e99));
    const verdict = {
      gira: R.K.ok && bad("giro").length === 0,
      estructura: bad("est").length === 0,
      warnGiro: warn("giro").length, warnEst: warn("est").length,
      pend: checks.filter((c) => c.st === "pend").length,
      fuMax: Math.max(0, ...checks.filter((c) => c.fu != null && isFinite(c.fu) && c.kind === "fu" && !c.fuera).map((c) => c.fu)),
      pendientes_criticos: pendCrit, fuMaxPend: pendCrit.length ? pendCrit[0].fu : 0,
      limitaciones_uso: (() => { const I = R.K.ok ? cornerInsertOf(P, R) : null; return I && I.ok ? [Object.assign({}, LIM_USO_VACIA)] : []; })(),   // casos excluidos del diseño que la memoria y los planos tienen que citar
    };
    verdict.estado_global = !(verdict.gira && verdict.estructura) ? "NO CUMPLE" : pendCrit.length ? "NO CUMPLE / PENDIENTE DE DECISIÓN" : "CUMPLE";
    return { P, R, fea, checks, verdict };
  }

  /* ---------------- Mercado y capacidad ---------------- */
  // W máxima (tf) que gira con el μ y el radio dados y el FS indicado (bisección sobre compute: FS = F_calado/F(T(μ, r)))
  function capacityW(P, mu, r, FS) {
    const f = (W) => { const R = compute(Object.assign({}, P, { W_tf: W })); return R.K.ok ? R.Fstall / R.Fcyl(R.torque(mu, r)) - FS : NaN; };
    let lo = 20, hi = 1500;
    if (!(f(lo) >= 0)) return 0;
    if (f(hi) >= 0) return hi;
    for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (f(mid) >= 0) lo = mid; else hi = mid; }
    return lo;
  }
  // Capacidad con n cilindros: la menor entre el giro (μ de diseño, FS_mín) y el pivote (reacción del empuje no equilibrado con n impar)
  function capacityByCyl(P, ns) {
    return ns.map((n) => {
      const Q = Object.assign({}, P, { n_cyl: n }), mu = muSet(Q), R0 = compute(Q);
      const wGiro = capacityW(Q, mu.d, P.r_ef, P.FS_min), wNom = capacityW(Q, mu.nom, R0.r_u, 1);
      const ok = (W) => { const A2 = analyze(Object.assign({}, Q, { W_tf: W }), { noFEA: true }); return !A2.checks.some((c) => c.grp === "Pivote" && c.st === "fail"); };   // solo las verificaciones del pivote
      let wPiv = 0, lo = 20, hi = 1500;
      if (ok(lo)) { if (ok(hi)) wPiv = hi; else { for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; } wPiv = lo; } }
      let wWood = Infinity;                                                                       // aplastamiento de la madera (si la cubierta está activa): q ∝ W
      if (P.opt_wood > 0.5) { const A2 = analyze(Object.assign({}, Q, { W_tf: 100 }), { noFEA: true }), rw = A2.checks.find((c) => /Madera: aplastamiento/.test(c.name)); if (rw && rw.dem > 0) wWood = 100 * rw.cap / rw.dem; }
      return { n, wGiro, wNom, wPiv, wWood: isFinite(wWood) ? wWood : null, wCap: Math.min(wGiro, wPiv, wWood) };
    });
  }
  // Equipos comerciales de referencia (datos públicos; brazo y radio de fricción estimados para μ implícito = n·F·a/(N·r_u))
  const MARKET = [
    { id: "ett200", name: "Enerpac ETT200", mass: 1700, capKN: 2000, h: 150, D: 1790, nCyl: 1, Fcyl: 222, p: 700, rot: 12.5, arm: 0.895, ru: 0.596, src: "Enerpac, ficha ETT-Series (EN-GB)" },
    { id: "ett400", name: "Enerpac ETT400", mass: 1725, capKN: 4000, h: 150, D: 1790, nCyl: 2, Fcyl: 222, p: 700, rot: 12.5, arm: 0.895, ru: 0.596, src: "Enerpac, ficha ETT-Series (EN-GB)" },
    { id: "kiet", name: "KIET 400T (equipo del cliente)", mass: 2158, capKN: 3924, h: 200, D: 2000, nCyl: 2, Fcyl: 397, p: 700, rot: 12.857, arm: 0.869, ru: 0.670, src: "Plano y manual KIET (análisis del 30-10-2026); capacidad declarada 400 t (el manual dice 500 t)" },
    { id: "hydra", name: "Hydra-Slide 8′×8′×6″ (250/500 t)", mass: null, capKN: null, h: 152, D: null, nCyl: null, Fcyl: null, p: null, rot: null, arm: null, ru: null, src: "Texto en el video del fabricante; sin ficha de masa ni de cilindros" },
  ];
  function market(P) {
    const R = compute(P), mu = R.mu, kN = R.W, Htop = P.t_base + R.ifc.delta + P.h_disc;   // cubierta W enrasada: no suma altura
    const ours = { name: "TT300-C (este diseño)", mass: R.m.total, capKN: kN, h: Htop, D: P.D_top, nCyl: P.n_cyl, Fcyl: R.Fstall, p: P.p_relief, rot: 360 / P.N_pin, arm: R.K.armMin / 1000, ru: R.r_u / 1000 };
    const impl = (r) => r.Fcyl && r.arm ? r.nCyl * r.Fcyl * r.arm / (r.capKN * r.ru) : null;
    const withK = (r) => Object.assign({}, r, { massPerKN: r.mass && r.capKN ? r.mass / r.capKN : null, muImpl: impl(r), FcylPerTon: r.Fcyl && r.capKN ? r.nCyl * r.Fcyl / (r.capKN / G) : null });
    return {
      ours: withK(ours), refs: MARKET.map(withK),
      capacity: { design: capacityW(P, mu.d, P.r_ef, P.FS_min), designFS1: capacityW(P, mu.d, P.r_ef, 1), nominal: capacityW(P, mu.nom, R.r_u, 1), nominalFS: capacityW(P, mu.nom, R.r_u, P.FS_min) },
    };
  }

  /* ---------------- Escenario térmico: API pura reutilizable (UI y export_design) ---------------- */
  const TH_ALTS = [["base", "Base: acero sobre acero con grasa grafitada", {}], ["A", "A · Dos discos de acero inoxidable con grasa", { opt_ss: 1 }], ["B", "B · Discos inox con lámina de UHMW", { opt_uhmw: 1 }],
    ["C1", "C1 · Placa de bronce con grafito + disco duro", { opt_bz: 1, bz_conf: 1 }], ["C2", "C2 · Dos placas de bronce de aleaciones distintas", { opt_bz: 1, bz_conf: 2 }], ["C3", "C3 · Bronce en pastillas + disco duro", { opt_bz: 1, bz_conf: 3 }]];
  const ST_RANK = { ok: 0, warn: 1, fail: 2 };
  // Nivel de confianza del dato (A/B/C del registro) de una verificación estándar cuya capacidad se redujo
  function confOf(c) {
    if (c.conf) return c.conf;
    if (c.grp === "Interfaz inox" || c.grp === "Interfaz bronce") return "C";
    if (c.grp === "Cubierta") return "A/C";
    if (/oldadura|Hertz|Filete|filete/.test(c.name)) return "C";
    return "B";
  }
  // Evalúa una alternativa a la temperatura T con la geometría congelada. ref: análisis a T_ref (para comparar fila a fila)
  function thermalRun(Pa, T, ov, frozen, grad, A0, cache) {
    const Pt = thermalP(Pa, T, ov, frozen, grad), reuse = Math.abs(Pt.E - Pa.E) < 1e-9 && A0 && A0.fea;
    const A = analyze(Pt, { cache, fea: reuse ? A0.fea : undefined });
    return { Pt, A };
  }
  function thermal(P, opts) {
    opts = opts || {};
    const Ts = (opts.T || [20, 40, 60, 80, 100]).slice(), Tref = P.T_ref, scn = P.T_serv > Tref;
    const Tscn = opts.Tscn != null ? opts.Tscn : (scn ? P.T_serv : 80);
    const grad = opts.gradient != null ? opts.gradient : (P.dT_grad > 0 ? P.dT_grad : (scn ? 0 : 15));   // K a Tscn; a otras T se escala con ΔT/ΔT_scn
    if (!Ts.some((t) => Math.abs(t - Tscn) < 1e-9)) { Ts.push(Tscn); Ts.sort((x, y) => x - y); }   // la tabla siempre incluye la temperatura del escenario
    const gradAt = (T) => (Tscn > Tref ? grad * Math.max(0, T - Tref) / (Tscn - Tref) : 0);
    const woodMode = opts.wood == null ? "form" : opts.wood;
    const ids = opts.alts || TH_ALTS.map((a) => a[0]);
    const cache = new Map(), alts = [];
    // FU gobernante del escenario: filas que entran al veredicto (las «pend» con FU, p. ej. la plancha base sin anclaje, quedan fuera de la comparación;
    // se informan aparte en byT[].pendientes_criticos y byT[].estado_global, desde verdict.pendientes_criticos de analyze())
    const fuEstOf = (A) => { let best = null; A.checks.forEach((c) => { if (!c.fuera && c.grp !== "Temperatura" && c.sys === "est" && c.kind === "fu" && c.st !== "pend" && isFinite(c.fu) && (!best || c.fu > best.fu)) best = c; }); return best; };
    const fuTermOf = (A) => { let best = null; A.checks.forEach((c) => { if (!c.fuera && c.grp === "Temperatura" && c.sys === "est" && c.kind === "fu" && c.st !== "pend" && isFinite(c.fu) && (!best || c.fu > best.fu)) best = c; }); return best; };
    const brief = (c) => (c ? { grp: c.grp, nombre: c.name, fu: c.fu } : null);
    const woods = woodMode === "both" ? [0, 1] : [woodMode === true || woodMode === 1 ? 1 : woodMode === false || woodMode === 0 ? 0 : (P.opt_wood > 0.5 ? 1 : 0)];
    TH_ALTS.filter((a) => ids.includes(a[0])).forEach(([id, nombre, flags]) => woods.forEach((w) => {
      const Pa = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 0, bz_conf: 1 }, flags, { opt_wood: w }); delete Pa.__th;
      const A20 = analyze(Pa, { cache }), I = A20.R.ifc;                                              // geometría de diseño a 20 °C (sin factores)
      const frozen = { tss: I.tss, tss2: I.tss2, tuh: I.tuh, tbz: I.tbz, L: Object.fromEntries((I.topes || []).map((s) => [s.id, s.L])) };
      const ref = thermalRun(Pa, Tref, null, frozen, 0, A20, cache);
      const byT = Ts.map((T) => {
        const run = T === Tref ? ref : thermalRun(Pa, T, null, frozen, gradAt(T), A20, cache), A = run.A, R = A.R, cur = A.checks;
        const eu = fuEstOf(A), tt = fuTermOf(A), rows = [], chg = [], fuera = [];
        cur.forEach((c, i) => {
          const r0 = ref.A.checks[i]; if (!r0) return;
          if (c.fuera) {   // accionamiento y circuito hidráulico (term_alcance = 1): se informan aparte, sin estado que afecte el veredicto
            if (c.kind !== "pend") fuera.push({ grp: c.grp === "Temperatura" ? "Temperatura · " + ({ c: "uña–pasador", e: "aceite atrapado", f: "aceite, sellos y bomba", k: "patín y guía" }[c.sub] || "") : c.grp, sub: c.sub || null, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, fu20: r0.fu, estado_informativo: c.st, estado20: r0.st, ref: c.ref });
            return;
          }
          if (r0.st !== c.st && ST_RANK[r0.st] != null && ST_RANK[c.st] != null) chg.push({ grp: c.grp, nombre: c.name, de: r0.st, a: c.st, fu20: r0.fu, fuT: c.fu, empeora: ST_RANK[c.st] > ST_RANK[r0.st], conf: confOf(c) });
          if (c.fu != null && r0.fu != null && c.kind !== "info") {
            const f0 = isFinite(r0.fu) ? r0.fu : 99, f1 = isFinite(c.fu) ? c.fu : 99;
            rows.push({ grp: c.grp, nombre: c.name, fu20: f0, fuT: f1, delta: f1 - f0, var_pct: f0 > 1e-9 ? (f1 / f0 - 1) * 100 : null, st20: r0.st, stT: c.st, conf: confOf(c), sys: c.sys });
          }
        });
        rows.sort((a, b) => b.delta - a.delta);
        const th = cur.filter((c) => c.grp === "Temperatura" && !c.fuera).map((c) => ({ sub: c.sub, sys: c.sys, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, conf: c.conf, ref: c.ref }));
        return { T, dT: Math.max(0, T - Tref), gradiente: gradAt(T), k: run.Pt.__th.k, notas: run.Pt.__th.notes, extrapolado: run.Pt.__th.extrap,
          FS: R.cd ? R.cd.FS : null, FS_min: P.FS_min, gira: A.verdict.gira, estructura: A.verdict.estructura, termico: !cur.some((c) => c.grp === "Temperatura" && !c.fuera && c.st === "fail"),
          fuEst: eu ? eu.fu : 0, gobernante: brief(eu), fuTerm: tt ? tt.fu : 0, gobernanteTerm: brief(tt), masa: R.m.total,
          pendientes_criticos: A.verdict.pendientes_criticos, estado_global: A.verdict.estado_global,   // filas «pend» con FU > 1: fuera del FU gobernante pero visibles
          nFail: cur.filter((c) => !c.fuera && c.st === "fail").length, nWarn: cur.filter((c) => !c.fuera && c.st === "warn").length,
          fuera_alcance: fuera, fuera_resumen: { n: fuera.length, fail: fuera.filter((x) => x.estado_informativo === "fail").length, warn: fuera.filter((x) => x.estado_informativo === "warn").length },
          sensibles: rows.filter((r) => r.delta > 1e-9).slice(0, 10), sensibles_est: rows.filter((r) => r.delta > 1e-9 && r.sys !== "term").slice(0, 10), cambian: chg, filas: th };
      });
      // sensibilidades a T_scn: Fy del acero 0,92 (ASME II-D), bronce 0,90, μ, UHMW y madera
      const sc = Tscn, g0 = gradAt(sc), base = thermalRun(Pa, sc, null, frozen, g0, A20, cache), eb = fuEstOf(base.A);
      const sumSens = (run) => { const e = fuEstOf(run.A); const wr = [];
        run.A.checks.forEach((c, i) => { const r0 = base.A.checks[i]; if (r0 && !c.fuera && r0.st !== c.st && ST_RANK[c.st] > ST_RANK[r0.st]) wr.push({ grp: c.grp, nombre: c.name, de: r0.st, a: c.st, fu: c.fu }); });
        const tm = fuTermOf(run.A); return { fuEst: e ? e.fu : 0, gobernante: brief(e), fuTerm: tm ? tm.fu : 0, gobernanteTerm: brief(tm), gira: run.A.verdict.gira, estructura: run.A.verdict.estructura, empeoran: wr, dFu: (e ? e.fu : 0) - (eb ? eb.fu : 0) }; };
      const sens = { T: sc, kFy092: Object.assign(sumSens(thermalRun(Pa, sc, { kT_Fy: 0.92 }, frozen, g0, A20, cache)), { k: 0.92, ref: "ASME II-D Tabla Y-1 (de memoria; confianza C)" }) };
      if (I.o === 3) sens.bz090 = Object.assign(sumSens(thermalRun(Pa, sc, { kT_bz: 0.90 }, frozen, g0, A20, cache)), { k: 0.90 });
      const FS0 = base.A.R.cd ? base.A.R.cd.FS : NaN;
      sens.mu = [0.8, 1, 1.2, 1.5].map((f) => ({ f, FS: FS0 / f, gira: FS0 / f >= P.FS_min - 1e-12 })); sens.mu_crit = FS0 / P.FS_min;   // μ máximo (múltiplo del de diseño) con FS ≥ FS_mín
      if (I.o === 2) {
        const uh = (ov) => { const run = thermalRun(Pa, sc, ov, frozen, g0, A20, cache); const rr = run.A.checks.filter((c) => c.grp === "Interfaz inox" && /UHMW/.test(c.name) && c.fu != null && c.kind !== "info"); const m = rr.reduce((b, c) => (!b || (isFinite(c.fu) ? c.fu : 99) > b.fu ? { fu: isFinite(c.fu) ? c.fu : 99, nombre: c.name } : b), null); return { fuUHMW: m ? m.fu : 0, gobernante: m ? m.nombre : null, cumple: !rr.some((c) => c.st === "fail") }; };
        const ks = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0];
        sens.uhmw = { kp: ks.map((k) => Object.assign({ k_p: k, k_E: P.kT_E_uh }, uh({ kT_p_uh: k }))), kE: ks.map((k) => Object.assign({ k_p: P.kT_p_uh, k_E: k }, uh({ kT_E_uh: k }))) };
        let lo = 0.05, hi = 1; if (uh({ kT_p_uh: hi }).cumple) { for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; if (uh({ kT_p_uh: m }).cumple) hi = m; else lo = m; } sens.uhmw.kp_crit = hi; } else sens.uhmw.kp_crit = null;   // k_p mínimo con el que la lámina cumple a T_scn
      }
      if (w) sens.madera = [0.7, 0.5].map((ct) => { const run = thermalRun(Pa, sc, { kT_wood: ct * 1 }, frozen, g0, A20, cache), c = run.A.checks.find((x) => x.grp === "Cubierta" && /Madera: aplastamiento/.test(x.name)); return { Ct: ct, fu: c ? c.fu : null, estado: c ? c.st : null }; });
      const jun = base.A.checks.filter((c) => c.grp === "Temperatura" && c.sub === "a" && /junta de dilatación requerida/.test(c.name)).map((c) => ({ pieza: c.name.split(":")[0], j_req: c.dem, j_disp: c.cap, fu: c.fu, estado: c.st }));
      alts.push({ id: id + (w ? "+madera" : ""), alt: id, madera: !!w, nombre: nombre + (w ? " + cubierta de madera" : ""), geometria: { o: I.o, conf: I.conf || null, tss: I.tss, tss2: I.tss2, tuh: I.tuh, tbz: I.tbz, masa20: A20.R.m.total, L: frozen.L },
        FS20: A20.R.cd ? A20.R.cd.FS : null, byT, sens, juntas: jun });
    }));
    const oil = Ts.map((T) => { const o = oilTrapped(P, T); return { T, dT: o.dT, rigido: { bajo: o.rigid.lo.bar, alto: o.rigid.hi.bar }, cilindro: { bajo: o.cyl.lo.bar, alto: o.cyl.hi.bar }, manguera: o.hose.hi.bar, Kc_lame_MPa: o.Kc_lame, seleccion_bar: o.sel.hi.bar }; });
    const alc = alcanceOf(P);
    return {
      version: 1, T: Ts, T_ref: Tref, T_scn: Tscn, gradiente_scn: grad, fuente: "docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»",
      aceite_fuera_de_alcance: alc !== 2, alternativas: alts, aceite: oil, viscosidad: Ts.map((T) => Object.assign({ T }, oilViscosity(T))), factores: Ts.map((T) => { const f = thermalFactors(P, T); return { T, k: f.k, alpha: f.alpha, extrapolado: f.extrap }; }),
      alcance: alc, alcance_texto: alc === 2 ? "Alcance 2: sistema de placas y disco más accionamiento mecánico (uña–pasador, patín–guía, pasadores de empuje) y circuito hidráulico (cilindros, aceite atrapado, alivio térmico, sellos, viscosidad y bomba)."
        : "Alcance 1 (por defecto): sistema de placas y disco: plancha base, mesa (planchas, almas, nervios, cubo), interfaz (discos inox, lámina UHMW, bronce, disco duro, pastillas, grasa y ranuras), topes y sus soldaduras, madera, pivote, buje y collar, gradiente, juntas y holguras. Los cilindros, el aceite, las válvulas, los sellos, la viscosidad, la bomba y el accionamiento mecánico están fuera de alcance (term_alcance = 2 los reactiva).",
      avisos: [
        "Los datos de UHMW-PE, acero inoxidable y bronce son de ficha de fabricante o supuestos (confianza C): confirmar con el proveedor; el UHMW-PE no tiene curva publicada a 80 °C y 80 °C es su límite de servicio continuo",
        "ASME BTH-1: 80 °C (176 °F) excede el rango estándar (−4 a 66 °C); la sección de BTH-1 sobre temperatura no está confirmada y exige decisión de persona calificada",
        alc === 2 ? "Aceite atrapado: un tramo aislado (cilindro + retenciones) exige válvula de alivio térmico; un alivio de sistema aguas arriba no lo protege"
          : "Nota informativa (fuera de alcance): un tramo aislado de aceite (cilindro + retenciones) con válvulas de retención o bloqueo exige válvula de alivio térmico; el circuito hidráulico y el accionamiento mecánico no entran en este escenario (term_alcance = 2 los reactiva)",
        "Geometría congelada: el escenario evalúa la geometría dimensionada a 20 °C con las capacidades reducidas; no re-dimensiona",
      ],
      supuestos_C: ["UHMW-PE: k_p y k_E (0,40)", "Inoxidable: Fy a 80 °C (0,82)", "Bronce: sin reducción (1,00) y α", "Madera: C_t 0,70 extrapolado a 80 °C (fuera de la tabla NDS)", "Pernos 10.9: 0,94", "Soldadura: sin reducción", "Gradiente plancha superior–inferior 15–18 K (EN 1991-1-5, otra tipología)",
        "μ a T_serv (dato de entrada)", "Holgura buje–pivote en frío"].concat(alc === 2 ? ["Módulo volumétrico del aceite 1,4–1,9 GPa y rigidez del contenedor (b/a = 1,4 por Lamé)", "Viscosidad mínima de la bomba 10 mm²/s", "Límite del sello NBR 80–120 °C"] : []),
      supuestos_fuera_alcance: alc === 2 ? [] : ["Módulo volumétrico del aceite 1,4–1,9 GPa y rigidez del contenedor (b/a = 1,4 por Lamé)", "Viscosidad mínima de la bomba 10 mm²/s", "Límite del sello NBR 80–120 °C"],
    };
  }


  /* ---------------- Tapones de grafito (opción C): ideal frente a real, barridos y patrón ---------------- */
  // API pura (UI y exportadores): para C1, C2 y C3 compara el cálculo con la fracción ideal (bz_fg_modo = 0) y la real (1), barre f_g,real, el patrón (d, p),
  // la franja de borde y los tornillos, y concluye el patrón recomendado. Todo sale del mismo núcleo (analyze / ifaceDesign): la memoria y la UI solo redactan.
  const TAP_ALTS = [["C1", 1, "C1 · Placa de bronce con grafito + disco duro"], ["C2", 2, "C2 · Dos placas de bronce de aleaciones distintas"], ["C3", 3, "C3 · Bronce en pastillas + disco duro"]];
  const TAP_D = [10, 12, 14, 16, 18, 20], TAP_P = Array.from({ length: 19 }, (_, i) => 22 + i), TAP_FG = Array.from({ length: 11 }, (_, i) => Math.round((0.05 + 0.025 * i) * 1e6) / 1e6);
  const TAP_LIG_MIN = 8, TAP_PROF_D = 3;          // fabricación (broca/mandrinadora, sin torno vertical): ligamento ≥ 8 mm y profundidad ≤ 3·d (criterio de taller, por confirmar)
  function tapones(P, opts) {
    opts = opts || {};
    const base = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 1 }); delete base.__th;
    const cache = new Map(), nf = (v, d) => (+v).toFixed(d == null ? 3 : d).replace(".", ",");
    const run = (conf, over) => analyze(Object.assign({}, base, { bz_conf: conf }, over || {}), { noFEA: true, cache });
    const pick = (A, re) => A.checks.find((c) => re.test(c.name));
    const RPV = /Bronce con grafito: valor PV/, RWE = /Bronce con grafito: desgaste/, RQN = /Presión de contacto sobre el bronce neto/, RLUB = /cobertura mínima de lubricante sólido/;
    const grpFails = (A) => A.checks.filter((c) => c.grp === "Interfaz bronce" && c.st === "fail" && !RLUB.test(c.name));
    const met = (A, modo) => {
      const R = A.R, I = R.ifc, pv = pick(A, RPV), we = pick(A, RWE), qn = pick(A, RQN);
      return { N: modo === 0 ? I.Nideal : I.Nreal, fg: modo === 0 ? I.fgIdeal : I.fgReal, cobertura: modo === 0 ? I.fgIdeal : I.fgReal, masa_bz: R.m.bz, masa_total: R.m.total, qNet: I.qNet, fuQ: I.qNet / A.P.p_bz,
        tbz: I.tbz, tbzReq: I.tbzReq, PV: pv.dem, fuPV: pv.fu, desgaste: we.dem, fuDesgaste: we.fu, FS: R.cd.FS, mu: R.mu.d, gira: A.verdict.gira, estructura: A.verdict.estructura, cumple_lub: (modo === 0 ? I.fgIdeal : I.fgReal) >= A.P.bz_fg_min - 1e-12 };
    };
    const dpct = (a, b) => { const o = {}; Object.keys(a).forEach((k) => { if (typeof a[k] === "number" && typeof b[k] === "number") o[k] = Math.abs(a[k]) > 1e-12 ? (b[k] / a[k] - 1) * 100 : null; }); return o; };
    // estado de un patrón (d, p): fabricación, η, y todas las verificaciones del bronce (sin la de lubricación, que se informa aparte)
    const patron = (conf, d, p, over) => {
      const A = run(conf, Object.assign({ bz_plug_d: d, bz_plug_p: p }, over || {})), I = A.R.ifc, m = met(A, 1), fails = grpFails(A);
      const lig = p - d, prof = PLUG_DEPTH * I.tbz, fab = lig >= TAP_LIG_MIN - 1e-9 && prof / d <= TAP_PROF_D + 1e-9, motivos = fails.map((c) => c.name);
      if (!fab) motivos.push("no fabricable (ligamento p − d ≥ " + TAP_LIG_MIN + " mm; profundidad ≤ " + TAP_PROF_D + "·d)");
      const estado = motivos.length ? "no cumple" : (m.cumple_lub ? "cumple" : "cumple sin lubricación");
      return Object.assign({ d, p, eta: I.eta, N: I.Nreal, n_agujeros: I.Nreal, fg_ideal: I.fgIdeal, fab, estado, motivos }, m, { fg: I.fgReal, A });
    };
    const strip = (o) => { const q = Object.assign({}, o); delete q.A; return q; };
    const alternativas = TAP_ALTS.map(([id, conf, nombre]) => {
      const A1 = run(conf, { bz_fg_modo: 1 }), A0 = run(conf, { bz_fg_modo: 0 }), I = A1.R.ifc, T = I.tap;
      const ideal = met(A0, 0), real = met(A1, 1);
      const geom = { N_real: T.N, N_ideal: I.Nideal, N_malla: T.N_malla, fg_real: I.fgReal, fg_ideal: I.fgIdeal, cobertura: I.cobGrafito, cobertura_total: I.fgReal * I.cov, area_contacto: T.Acont, cov: I.cov, n_sectores: T.n, junta: T.junta, L_muesca: T.L, radios_tornillos: T.radios,
        n_tornillos_sector: T.radios.length ? (T.nTor >= 4 ? 4 : 2) : 0, d_cabeza: T.dk, bz_edge: T.edge, perdidas: T.perdidas, por_sector_min: Math.min(...T.porSector), por_sector_max: Math.max(...T.porSector), d: T.d, p: T.p, eta: I.eta };
      // (b) barrido de f_g,real objetivo: con Ø fijo (el actual) se elige el mayor paso cuyo f_g,real alcanza el objetivo (monótono por construcción)
      const dB = base.bz_plug_d, scan = [];
      for (let p = Math.max(Math.ceil(dB + 1), 14); p <= 60; p++) { const q = run(conf, { bz_plug_p: p }).R.ifc; scan.push({ p, fg: q.fgReal }); }
      const fgmaxScan = scan.reduce((b, x) => (x.fg > b.fg ? x : b), scan[0]);
      const barrido_fg = TAP_FG.map((T0) => {
        let c = null; scan.forEach((x) => { if (x.fg >= T0 - 1e-12 && (!c || x.p > c.p)) c = x; });
        const alc = !!c, pp = alc ? c.p : fgmaxScan.p, r = patron(conf, dB, pp);
        return Object.assign(strip(r), { fg_obj: T0, estado: alc ? r.estado : "inalcanzable", alcanzable: alc });
      });
      // (c) barrido (d, p)
      const barrido_dp = []; TAP_D.forEach((d) => TAP_P.forEach((p) => { if (p > d) barrido_dp.push(strip(patron(conf, d, p))); }));
      // (d) sensibilidad a bz_edge y a los tornillos de posición
      const sen = (over) => { const A = run(conf, over), q = A.R.ifc, m = met(A, 1); return Object.assign({ N: q.Nreal, fg: q.fgReal, masa_bz: m.masa_bz, qNet: m.qNet, fuQ: m.fuQ, cumple_lub: m.cumple_lub, estructura: m.estructura, gira: m.gira, n_fallan: grpFails(A).length, n_tor: over.bz_n_tor }, over); };
      const sens_borde = [2, 4, 6, 8].map((e) => sen({ bz_edge: e }));
      const sens_tornillos = [[6, 0], [6, 2], [6, 4], [8, 2], [10, 2]].map(([dt, nt]) => sen({ d_tor: dt, bz_n_tor: nt }));
      // (e) conclusión automática
      const cand = barrido_dp.filter((x) => x.eta >= P.bz_eta_min - 1e-12 && x.fab && x.estado !== "no cumple");
      const fgMaxAlc = cand.reduce((b, x) => Math.max(b, x.fg), 0), ok = cand.filter((x) => x.fg >= P.bz_fg_min - 1e-12);
      const byMass = (x, y) => x.masa_bz - y.masa_bz || x.N - y.N || x.d - y.d;
      const rec = ok.length ? strip(ok.slice().sort(byMass)[0]) : null;
      const mejor = cand.length ? strip(cand.reduce((b, x) => (x.fg > b.fg + 1e-12 || (Math.abs(x.fg - b.fg) <= 1e-12 && x.masa_bz < b.masa_bz) ? x : b), cand[0])) : null;
      const act = barrido_dp.find((x) => x.d === base.bz_plug_d && x.p === base.bz_plug_p);
      // límites de f_g: la lubricación pone el mínimo; q_neto, PV y desgaste ponen el máximo (q_neto = q_loc/(1 − f_g − f_ranuras))
      const pvR = pick(A1, RPV), weR = pick(A1, RWE), qnR = pick(A1, RQN), qlim = (row) => I.qNet * row.cap / row.dem, fgOf = (qn) => 1 - I.fgr - I.qLoc / qn;
      const lim = { q_neto: fgOf(qlim(qnR)), PV: fgOf(qlim(pvR)), desgaste: fgOf(qlim(weR)) };
      const fgMaxFis = Math.min(lim.q_neto, lim.PV, lim.desgaste);
      const dM = real.masa_bz - ideal.masa_bz, texto = [];
      texto.push(id + ": con el patrón Ø" + base.bz_plug_d + " · paso " + base.bz_plug_p + " caben " + T.N + " tapones (ideal " + Math.round(I.Nideal) + "): f_g,real = " + nf(I.fgReal) + " frente a " + nf(I.fgIdeal) + " ideal; el bronce pesa " + nf(dM, 1) + " kg más (" + nf((real.masa_bz / ideal.masa_bz - 1) * 100, 1) + " %) y q_neto baja de " + nf(ideal.qNet, 2) + " a " + nf(real.qNet, 2) + " MPa (FU " + nf(real.fuQ, 2) + ").");
      texto.push("f_g mínimo para cumplir: " + nf(P.bz_fg_min, 2) + " (lubricación, supuesto C por confirmar con el catálogo); el máximo admisible por q_neto, PV y desgaste es " + nf(fgMaxFis, 2) + ". El espesor del bronce lo fija el tope (" + I.tTope + " mm) y no la flexión (requerido " + nf(I.tbzReq, 1) + " mm), así que f_g no cambia el espesor mientras η ≥ " + nf(P.bz_eta_min, 2) + ".");
      if (rec) texto.push("Patrón recomendado: Ø" + rec.d + " · paso " + rec.p + " (η " + nf(rec.eta, 2) + ", " + rec.N + " tapones, f_g " + nf(rec.fg) + ", bronce " + nf(rec.masa_bz, 1) + " kg, " + (act ? nf(rec.masa_bz - act.masa_bz, 1) + " kg frente al actual" : "") + ").");
      else texto.push("Ningún patrón del barrido (Ø10–20, paso 22–40) cumple f_g,real ≥ " + nf(P.bz_fg_min, 2) + " con η ≥ " + nf(P.bz_eta_min, 2) + " y fabricable: el máximo alcanzable es " + nf(fgMaxAlc) + (mejor ? " (Ø" + mejor.d + " · paso " + mejor.p + ", " + mejor.N + " tapones, η " + nf(mejor.eta, 3) + ")" : "") + ". El criterio queda como aviso hasta que la ficha del proveedor fije el valor; se conserva el patrón actual.");
      return { id, conf, nombre, geom, comparacion: { ideal, real, delta_pct: dpct(ideal, real), delta_abs: { masa_bz: dM, masa_total: real.masa_total - ideal.masa_total, qNet: real.qNet - ideal.qNet } },
        barrido_fg, barrido_dp, sens_borde, sens_tornillos, limites_fg: Object.assign({ fg_min_lubricacion: P.bz_fg_min, fg_max: fgMaxFis }, lim),
        conclusion: { fg_min_criterio: P.bz_fg_min, fg_max_fisico: fgMaxFis, fg_max_alcanzable: fgMaxAlc, cumple_criterio: !!rec, patron_recomendado: rec, mejor_alcanzable: mejor, patron_actual: act ? strip(act) : null,
          costo_masa: rec && act ? { delta_kg: rec.masa_bz - act.masa_bz, delta_pct: (rec.masa_bz / act.masa_bz - 1) * 100, delta_espesor: rec.tbz - act.tbz, delta_agujeros: rec.N - act.N } : null, texto } };
    });
    return { version: 1, parametros: { bz_plug_d: base.bz_plug_d, bz_plug_p: base.bz_plug_p, bz_edge: base.bz_edge, bz_fg_modo: base.bz_fg_modo, bz_fg_min: base.bz_fg_min, bz_eta_min: base.bz_eta_min, bz_n_tor: base.bz_n_tor, d_tor: base.d_tor, bz_fg_estricto: base.bz_fg_estricto, p_bz: base.p_bz, PV_bz: base.PV_bz, k_bz: base.k_bz, bz_cover: base.bz_cover, n_sec: base.n_sec, bz_npad: base.bz_npad },
      alternativas,
      barridos: { d: TAP_D, p: TAP_P, fg: TAP_FG, ligamento_min_fab: TAP_LIG_MIN, prof_max_d: TAP_PROF_D },
      notas: [
        "Cantidad real: conteo determinista de los centros de la malla escalonada (paso p, fila alterna p·√3/2, anclada al centro de la mesa) cuyo borde queda a ≥ bz_edge del borde del bronce, de la muesca del tope ((b_tope + 2) × L_tope), de los tornillos de posición (cabeza ISO 10642) y de las ranuras de engrase; es el mismo patrón S09 que coloca el dibujante (cad/modelo3d_tt300c.py) y reproduce su conteo (C1/C2 2 640; C3 2 364).",
        "bz_fg_min = " + nf(P.bz_fg_min, 2) + " es un supuesto de confianza C (orden de magnitud de bronces autolubricados comerciales): confirmar con el catálogo del proveedor; el valor lo fija la ficha. Por defecto el criterio avisa y no cambia el veredicto (bz_fg_estricto = 0).",
        "η ≥ " + nf(P.bz_eta_min, 2) + " es criterio de proyecto; la fabricabilidad (ligamento ≥ " + TAP_LIG_MIN + " mm, profundidad ≤ " + TAP_PROF_D + "·d, taladro con broca o mandrinadora, sin torno vertical) es un criterio de taller por confirmar.",
        "p_bz, PV_bz y k_bz son datos de catálogo del bronce con grafito (confianza C): q_neto, PV y desgaste dependen de ellos y de f_g,usada; el μ es un dato de entrada y no se modifica con f_g (con menos grafito el μ real podría subir: no modelado).",
        "La masa del bronce se calcula como mezcla ρ_bz(1 − 0,7 f_g) + ρ_grafito·0,7 f_g sobre el área cubierta (el tapón ocupa el 70 % del espesor): con menos tapones hay más bronce y más masa. El conteo no depende de la masa; sí del largo de la muesca (tope) y por eso del espesor del bronce.",
        "Los tornillos de posición están en la bisectriz de cada sector o pastilla, a mitad de camino entre la muesca y cada borde (2 por sector; 4 = dos radios × dos lados, hipótesis de sensibilidad); el parámetro d_tor fija el Ø de su cabeza.",
      ],
      supuestos: ["bz_fg_min " + nf(P.bz_fg_min, 2) + " (confianza C, catálogo del proveedor)", "bz_eta_min " + nf(P.bz_eta_min, 2) + " (criterio de proyecto)", "ligamento mínimo de fabricación " + TAP_LIG_MIN + " mm y profundidad ≤ " + TAP_PROF_D + "·d (criterio de taller por confirmar)", "bz_edge " + P.bz_edge + " mm (franja de borde del dibujante, S09)", "p_bz, PV_bz, k_bz del bronce con grafito (catálogo, confianza C)", "tornillos de posición: " + P.bz_n_tor + " por sector con cabeza ISO 10642 de M" + P.d_tor],
    };
  }

  return { woodGeo, designWood, plankLayout, stepPlate, discModelW, runDiscW, topUnder, cubiertaGeo, driveAt: driveAtSim, pivotGeo, pivotAt, camGeo, camAt, guidedAt, designDrive, driveMode, camFam, camGuided, camPiv, kinPiv, pivKin, suggestE, pivSupGeo, pivSup, pivSweep, baseClear, earPolys, pivBlkGeo, pivAsym, boltJ3, tapones, tapInfo, thermal, thermalP, thermalFactors, oilTrapped, oilViscosity, alphaSteelMean, TH_ALTS, riOf, hubGeo, capacityW, capacityByCyl, market, MARKET, prIn, pinClear, bracketGeo, guideGeo, forkH, PARAM_GROUPS, defaults, parseRings, masses, kinematics, compute, discModel, runDisc, globalBending, runLift, verifs, analyze, FSR, FAT_CAT, hAxis, G, PSI_CAT, chamferGeo };
})();
if (typeof module !== "undefined") module.exports = TT;
