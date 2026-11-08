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
      ["tor2_n", "AF2: N° de tornillos (0 = automático: el menor múltiplo del N° de ranuras radiales con FU ≤ 0,85 al par de diseño)", "–", 0, 0, 120, 1],
      ["tor2_r", "AF2: radio del círculo de tornillos (0 = automático: entre la ranura circunferencial exterior y el borde, libre de la ranura)", "mm", 0, 0, 1000, 1],
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
    { id: "cubierta", t: "Cubierta de madera dura y altura de skidding", p: [
      ["opt_wood", "Cubierta de madera dura sobre la plancha superior de la mesa", "–", 0, 0, 1, "chk"],
      ["t_wood", "Espesor de los tablones", "mm", 50, 20, 150, 5],
      ["rho_wood", "Densidad de la madera dura (seca al aire)", "kg/m³", 900, 500, 1300, 10],
      ["p_wood", "Presión admisible de aplastamiento perpendicular a la fibra (sostenida; confirmar con NCh1198 y el proveedor)", "MPa", 6, 1, 20, 0.5],
      ["f_apoyo", "Fracción del círculo de apoyo de la carga que toca realmente la madera (tablones contiguos dentro del anillo de acero: 0,90, definido por el mandante)", "–", 0.9, 0.05, 1, 0.05],
      ["h_skid", "Altura de los rieles de skidding o de la superficie de llegada (0 = no aplica)", "mm", 0, 0, 800, 5],
      ["tol_skid", "Tolerancia de enrase con los rieles", "mm", 10, 1, 50, 1],
      ["t_ring", "Anillo de acero de contención de la madera (pletina soldada a la plancha superior en el borde): ancho radial; el alto es t_madera y el acero va en el borde exterior, los tablones dentro (Ø D_mesa − 2·t_anillo)", "mm", 10, 4, 40, 1],
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
      ["cam_px", "Pórticos del riel: espesor en x de cada pata (una a cada lado del cuerpo del cilindro, que pasa bajo el pórtico trasero)", "mm", 30, 10, 80, 1],
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
      ["pv_bu", "Bloque-uña: ancho del cuerpo en planta", "mm", 70, 30, 150, 1],
      ["pv_ecr", "Bloque-uña: desplazamiento lateral del cuerpo hacia afuera (cuerpo acodado que libra el pasador siguiente; flexión F·e en el cuerpo)", "mm", 35, 0, 80, 1],
      ["pv_bf", "Bloque-uña: ancho de la cara de empuje (tramo de la cara centrado en la línea E–Q–P)", "mm", 80, 30, 160, 1],
      ["pv_lf", "Bloque-uña: largo del tramo de la cara", "mm", 60, 20, 200, 1],
      ["pv_hu", "Bloque-uña: alto (≤ luz libre entre anillos − 10)", "mm", 140, 40, 200, 1],
      ["pv_dq", "Pasador vertical Q (bloque-uña sobre el ojal del vástago; su extremo inferior es el seguidor de la placa-leva): Ø", "mm", 90, 30, 150, 1],
      ["pv_dE", "Pasador vertical del ojal trasero E: Ø", "mm", 70, 30, 150, 1],
      ["pv_tl", "Soporte del ojal E: espesor de las tapas superior e inferior del cajón (orejas del pasador E)", "mm", 28, 8, 80, 1],
      ["pv_box", "Soporte del ojal E: lado del cajón soldado a la base, centrado en E (paredes traseras en L hacia la esquina; ventana para el ojal hacia la mesa: sección en U)", "mm", 260, 100, 500, 5],
      ["pv_tbox", "Soporte del ojal E: espesor de las paredes del cajón", "mm", 25, 6, 50, 1],
      ["pv_wbox", "Soporte del ojal E: filete cajón–base (a ambos lados de las tres paredes; 22 → 21 mm el 08-11-2026 para dejar el filete máximo en FU ≤ 0,95)", "mm", 21, 4, 30, 1],
      ["pv_muE", "μ del pasador del ojal E (resistencia al giro del cilindro en la rampa de la leva)", "–", 0.20, 0.05, 0.6, 0.01],
      ["pv_c", "Placa-leva: holgura sobre la trayectoria de Q en el empuje", "mm", 3, 0.5, 20, 0.5],
      ["pv_msync", "Placa-leva: margen mínimo de sincronía (holgura bloque-uña–pasador siguiente con Q apoyado en la leva)", "mm", 5, 1, 30, 0.5],
      ["pv_alpha", "Placa-leva: ángulo de la rampa del extremo retraído respecto de la trayectoria de Q (mínimo por sincronía; el giro del cilindro en E casi no ofrece roce)", "°", 65, 20, 80, 1],
      ["pv_dwell", "Placa-leva: tramo a nivel de toma en el extremo retraído", "mm", 2, 0, 20, 0.5],
      ["pv_tcam", "Placa-leva: espesor (alto del contacto con el seguidor; el bloque-uña pasa sobre ella)", "mm", 30, 10, 60, 1],
      ["pv_wlip", "Placa-leva: ancho del labio detrás del recorte (lleva los pernos en su eje)", "mm", 80, 30, 200, 5],
      ["Fy_camP", "Placa-leva: Fy del acero (S355J2: 355; familia 1 con canto templado o inserto templado)", "MPa", 355, 235, 1000, 5],
      ["Fu_camP", "Placa-leva: Fu del acero (S355J2: 470)", "MPa", 470, 300, 1100, 10],
      ["pv_nb", "Placa-leva: N° de pernos por placa", "–", 6, 2, 16, 1],
      ["pv_db", "Placa-leva: Ø de los pernos", "mm", 20, 10, 36, 1],
      ["pv_tlin", "Placa-leva: espesor del revestimiento del canto (familias 2–4)", "mm", 8, 2, 30, 1],
      ["pv_lpad", "Seguidor: largo de la zapata en el sentido de la leva (0 = automático: Ø del pasador Q o el que piden p_adm y PV de la familia con FU 0,90)", "mm", 0, 0, 600, 5],
      ["pv_cQ", "Holgura del pasador Q al borde de la mesa (la placa-leva va sobre la base, fuera de la mesa)", "mm", 10, 2, 50, 1],
      ["pv_cB", "Holgura mínima bloque-uña–pasador siguiente durante el empuje", "mm", 10, 2, 50, 1],
      ["pv_cc", "Holgura mínima cuerpo del cilindro–borde de la mesa", "mm", 10, 2, 100, 1],
      ["pv_fugeo", "Sugerencia de E: FU objetivo de las holguras «cajón del ojal dentro de la base» y «Q fuera de la mesa» (1 = solo factibles; con B = 2.560 no hay solución por debajo de 0,97: el cajón pide R_E chico y Q fuera de la mesa lo pide grande; FU ≤ 0,95 en ambas exige B ≥ 2.760)", "–", 1, 0.5, 1, 0.01],
    ] },
    { id: "base", t: "Base", p: [
      ["B", "Lado de la base cuadrada", "mm", 2560, 1000, 4500, 10],
      ["t_base", "Espesor plancha base", "mm", 18, 6, 60, 1],
      ["t_base_min", "Espesor mínimo de base por planitud (criterio de fabricación)", "mm", 16, 6, 60, 1],
      ["rim_h", "Alto del marco perimetral", "mm", 45, 0, 200, 1],
      ["rim_t", "Espesor del marco perimetral", "mm", 10, 0, 40, 1],
      ["c_lug", "Puntos de izaje (lados y): distancia al borde (4.ª pasada: 150 → 200 mm; con hc_min = 6 la opción B pesa ≈ 4,1 t y con 150 mm la flecha de izaje pasaba del límite B/300; con 200 mm queda 15 % bajo el límite. 08-11-2026: 200 → 250 mm, la leva de reenganche suma ≈ 160 kg sobre la base y con 200 mm la variante B + madera quedaba a 8 % del límite, bajo el margen de 10 % del hallazgo C12; con 250 mm queda 23 % bajo el límite)", "mm", 250, 30, 600, 5],
      ["x_lug", "Puntos de izaje: distancia al eje y", "mm", 600, 0, 2000, 5],
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
    const d_bush = P.D_piv + 30, hw = P.h_disc - P.t_top - P.t_bot, collar = P.h_boss > 0;
    const hRaw = P.h_boss - (delta || 0) + P.c_boss_a, hRec = collar ? Math.max(0, hRaw) : 0;
    const Drb = collar ? Math.max(P.D_boss + 2 * P.c_boss_r, d_bush) : d_bush;
    return { d_bush, hw, delta: delta || 0, Drb, hRaw: collar ? hRaw : 0, hRec, hPl: hRec > 0 ? P.t_bot : 0, hHub: Math.min(Math.max(0, hRec - P.t_bot), hw), Ri: riOf(P),
      wall: (P.D_hub - Drb) / 2 };   // pared del cubo (y ligamento de la plancha) junto al rebaje
  }

  /* ---------------- Masas ---------------- */
  function massesMesa(P, delta) {
    const rings = parseRings(P.rings);
    const hw = P.h_disc - P.t_top - P.t_bot;
    const Rt = P.D_top / 2, r_hub = P.D_hub / 2, d_bush = P.D_piv + 2 * 15, hg = hubGeo(P, delta);
    // planchas: disco central + anillo de pasadores (agujeros de pasadores en todo el espesor del anillo)
    const rpr = prIn(P), aRing = Math.PI * (Rt * Rt - rpr * rpr) - P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const hole_top = P.D_piv + 80;                                       // alojamiento de la tapa retenedora
    const m = {};
    m.top = RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * hole_top ** 2) * P.t_top + aRing * Math.max(P.t_pr, P.t_top));
    m.bot = RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * d_bush ** 2) * P.t_bot + aRing * Math.max(P.t_pr, P.t_bot) - Math.PI / 4 * (hg.Drb ** 2 - d_bush ** 2) * hg.hPl);   // agujero del buje y rebaje del collar (Ø D_boss + 2·c_boss_r, profundidad hPl)
    m.webs = RHO * rings.reduce((s, r) => s + 2 * Math.PI * r * hw * P.t_web, 0);
    const ringsIn = rings.filter((r) => r > r_hub && r < P.R_rib).length;
    m.ribs = RHO * P.N_rib * Math.max(0, P.R_rib - r_hub - ringsIn * P.t_web) * hw * P.t_rib;
    m.hub = RHO * Math.PI / 4 * (Math.max(0, P.D_hub ** 2 - d_bush ** 2) * hw - Math.max(0, hg.Drb ** 2 - d_bush ** 2) * hg.hHub);   // rebaje del collar: solo la parte que pasa de la plancha inferior (h_collar − δ + c_boss_a − t_bot)
    m.pins = RHO * P.N_pin * Math.PI / 4 * P.d_pin ** 2 * P.h_disc;
    // cubierta de madera (kg/m³ → kg/mm³): los tablones van dentro del anillo de acero de contención (Ø D_mesa − 2·t_anillo, hasta la abertura de la tapa)
    // y el anillo es una pletina t_anillo × t_madera en el borde, soldada a la plancha superior (gira con la mesa y carga la interfaz)
    const wood_on = P.opt_wood > 0.5, Rw = Rt - P.t_ring;
    m.wood = wood_on ? P.rho_wood * 1e-9 * Math.PI / 4 * ((2 * Rw) ** 2 - hole_top ** 2) * P.t_wood : 0;
    m.ring = wood_on ? RHO * Math.PI * (Rt * Rt - Rw * Rw) * P.t_wood : 0;
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
    const mPiv = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + P.h_disc - P.t_top + 3);
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
  const wMin = (T) => T <= 6 ? 3 : T <= 12 ? 5 : T <= 20 ? 6 : 8;   // AWS D1.1/D1.1M:2020 Tabla 5.8: filete mínimo según la parte más gruesa (AISC Tabla J2.4 lo da por la más delgada: nunca mayor)
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
    const Ftot = R.Tmax / (R.r_u / 1000), kpk = R.q_max / R.q_avg, Lav = R.Ro - R.Ri - 100;   // kN en el radio de fricción (T_calado); sector más cargado; canto radial disponible (mm)
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
  // AF2 (opción A pegada, fix_mode = 2): tornillos avellanados ISO 10642 10.9 del disco de la mesa a la plancha inferior (roscados en ella). El par de diseño T se reparte
  // en n tornillos sobre el radio r: V = T/(n·r). Corte AISC J3.6 (Fnv = 0,45·Fu, rosca incluida); aplastamiento J3.10 en el disco (espesor t − k/2 por el avellanado,
  // EN 1993-1-8 Tabla 3.4) y en la plancha; separación J3.3 (3d), borde J3.4M; cabeza ≤ t − 0,5; roscado ≥ 1,25d en la plancha.
  function tornillosAF2(P, R) {
    const I = R.ifc;
    if (!(I && I.o === 1 && P.fix_mode > 1.5) || !R.cd) return null;
    const d = P.tor2_d, Ab = Math.PI / 4 * d * d, dh = d + 1, k = isoK(d), dk = isoDk(d), Ro = R.Ro, t = I.tss2, tb = P.t_bot, T = R.cd.T;
    const nr = P.h_gr > 0 ? Math.max(1, Math.round(P.n_gr_rad)) : 4, rOut = P.h_gr > 0 && P.n_gr_circ >= 1 ? Ro - 30 : Ro;
    const r = P.tor2_r > 0 ? P.tor2_r : (P.h_gr > 0 && P.n_gr_circ >= 1 ? rOut - P.w_gr / 2 - dk / 2 - 5 : Ro - Math.max(J34M(d), dk / 2 + 5));
    const Fnv = 0.45 * P.Fu_bolt, capV = Fnv / 2;
    const ev = (n) => {
      const V = T * 1e6 / (n * r), s = 2 * Math.PI * r / n, lc = s - dh, te = t - k / 2;
      const RnD = Math.min(1.2 * lc * te * P.Fu_ss, 2.4 * d * te * P.Fu_ss), RnM = Math.min(1.2 * lc * tb * P.Fu, 2.4 * d * tb * P.Fu);
      return { n, V, s, lc, te, RnD, RnM, fuV: V / Ab / capV, fuD: V / (RnD / 2), fuM: V / (RnM / 2) };
    };
    let e = null;
    if (P.tor2_n > 0) e = ev(Math.round(P.tor2_n));
    else for (let m = 1; m <= 60 && !e; m++) { const q = ev(nr * m); if (Math.max(q.fuV, q.fuD, q.fuM) <= 0.85) e = q; }
    if (!e) e = ev(nr * 60);
    const ang = Array.from({ length: e.n }, (_, i) => (i + 0.5) * 360 / e.n);
    const L = [16, 20, 25, 30, 35, 40, 45, 50].find((x) => x >= t + Math.min(tb, 1.25 * d + 2) - 1) || Math.ceil(t + tb);
    const latR = nr && P.h_gr > 0 ? r * Math.sin(Math.PI / e.n) : Infinity;   // distancia lateral del eje a la ranura radial más cercana (el tornillo va a mitad de camino)
    return Object.assign(e, { d, Ab, dh, k, dk, r, t, tb, T, Fnv, capV, ang, pos: ang.map((a) => [r * Math.cos(a * D2R), r * Math.sin(a * D2R)]), L, rOut, latR,
      avellanado: { d_cabeza: dk, prof: k, angulo_deg: 90, bajo_cara: t - k }, rosca: { d: d, paso: { 6: 1, 8: 1.25, 10: 1.5, 12: 1.75, 14: 2, 16: 2, 20: 2.5 }[Math.round(d)] || null, prof: tb, pasante: true, d_broca: d - ({ 6: 1, 8: 1.25, 10: 1.5, 12: 1.75, 14: 2, 16: 2, 20: 2.5 }[Math.round(d)] || 0.15 * d) },
      designacion: "ISO 10642 M" + d + " × " + L + " – 10.9" });
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

  // Soporte del ojal E (modo pivotado): cajón soldado a la base centrado en E; sus tapas superior e inferior llevan el pasador vertical E y el ojal del cilindro
  // entra por una ventana hacia la mesa (la sección resistente es una U: pared trasera perpendicular a la fuerza y dos paredes laterales)
  function pivSupGeo(P) {
    const zc0 = hAxis(P) + P.t_base, b = P.b_eye, g = P.g_ch, tl = P.pv_tl, B = P.pv_box, t = P.pv_tbox;
    const zU = zc0 + b / 2 + g + tl / 2, zL = zc0 - b / 2 - g - tl / 2, hBox = zc0 + b / 2 + g + tl - P.t_base;
    const yc = (B * t * t / 2 + 2 * t * B * B / 2) / (3 * B * t), I = B * t ** 3 / 12 + B * t * (yc - t / 2) ** 2 + 2 * (t * B ** 3 / 12 + t * B * (B / 2 - yc) ** 2), S = I / Math.max(yc, B - yc);
    const mBox = RHO * 3 * B * hBox * t, mLug = 2 * RHO * tl * (B * B - Math.PI / 4 * P.pv_dE ** 2), mPin = RHO * Math.PI / 4 * P.pv_dE ** 2 * (b + 2 * g + 2 * tl + 20);
    return { zc0, zU, zL, hU: zU - P.t_base, hL: zL - P.t_base, hBox, aTear: B / 2 - P.pv_dE / 2, S, yc, zLugBot: zc0 - b / 2 - g - tl, forkH: b + 2 * g + 2 * tl, mBox, mLug, mPin, m: mBox + mLug + mPin };
  }
  // Bloque-uña (modo pivotado): cuerpo acodado b_u × h_u desde el cubo de Q hasta el tramo de la cara (b_f × l_f), horquilla sobre el ojal del vástago y pasador Q
  function pivBlkGeo(P, K) {
    const zc0 = hAxis(P) + P.t_base, r = P.d_pin / 2, Lqp = K && K.ok ? K.Lqp : (P.pv_Lqp || 300), eb = P.pv_dq / 2 + 25, s2 = Lqp - r, s1 = s2 - P.pv_lf;
    const tq = (P.pv_hu - P.b_eye - 2 * P.g_ch) / 2, zLc = zc0 - P.b_eye / 2 - P.g_ch - tq / 2, zCam = P.t_base + P.pv_tcam / 2, lq = zLc - zCam;
    const mBlk = RHO * (P.pv_hu * ((s1 + eb) * P.pv_bu + P.pv_lf * P.pv_bf) - (P.b_eye + 2 * P.g_ch) * 2 * eb * eb), lPin = zc0 + P.pv_hu / 2 - (P.t_base + 2);
    const mPin = RHO * Math.PI / 4 * P.pv_dq ** 2 * lPin;
    return { zc0, eb, s1, s2, tq, zLc, zCam, lq, lPin, mBlk, mPin, m: Math.max(0, mBlk) + mPin, zBot: zc0 - P.pv_hu / 2 };
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
      const K = kinPiv(P), sg = pivSupGeo(P), bk = pivBlkGeo(P, K), CP = camPiv(P, K), fam = camFam(P);
      m.brackets = P.n_cyl * sg.m;
      m.dogs = P.n_cyl * bk.m;
      m.shoes = 0; m.beds = 0;
      m.cam = CP ? 2 * P.n_cyl * (RHO * P.pv_tcam * CP.area + (fam.f > 1 ? fam.rhoL * P.pv_tlin * P.pv_tcam * CP.Lb : 0)) : 0;
    }
    m.pivot = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + ifc.delta + P.h_disc - P.t_top + 3);
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
  // AISC 360-22 J3: pernos (Fnt = 0,75·Fu, Fnv = 0,45·Fu con rosca en el plano de corte, área nominal, Ω = 2,00; tracción + corte J3.7, Ec. J3-3a)
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
    const zc0 = g.zc0, zU = zc0 + P.dog_h / 2, zS = zU + 1 + P.t_pk / 2, zPb = g.shoeTop + 2, zF = zPb + P.cam_t / 2, zTop = zc0 + P.h_disc / 2;
    const xFp0 = P.x_g - P.w_s / 2 + 10 + P.cam_dp / 2, xE0 = xFp0 + P.cam_df / 2 + c, xPo = xE0 + P.cam_w, wNet = P.cam_w - uPk, lFp = zF - zU;
    const Lsp = g.L_bed + P.cam_ls, Lpl = g.L_bed + 2 * P.cam_ls, hPed = zPb - (P.t_base + P.t_bed), yOf = (e) => g.y_pin0 + e - P.dog_b / 2;
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
    const Sx = aw * (ls * px + px * px / 3), Sy = aw * (px * ls + ls * ls / 3), Lw = aw * 2 * (px + ls), Fwc = P.FEXX * 0.60 / (1.20 * P.Nd);
    const cases = [[NRx * kR, Fret], [NT * kR, 0]].map(([Rx, Ry]) => {
      const sPed = (Rx / 2) * hPed / (ls * px * px / 6) + (Ry / 2) * hPed / (px * ls * ls / 6);
      const fW = Math.hypot((Rx / 2) * hPed / Sx + (Ry / 2) * hPed / Sy, Math.hypot(Rx, Ry) / 2 / Lw);
      const V = Math.hypot(Rx, Ry) / P.cam_nb, b = boltJ3(P, P.cam_db, V, 0), Rn = 2.4 * P.cam_db * P.cam_t * P.Fu_cam;
      return { Rx, Ry, sPed, fW, V, b, Rn, fuV: b.frv / b.capV, fuB: V / (Rn / 2) };
    });
    const cg = cases.reduce((a, b) => (Math.max(b.fuV, b.fuB) > Math.max(a.fuV, a.fuB) ? b : a)), cp = cases.reduce((a, b) => (b.sPed > a.sPed ? b : a)), cw = cases.reduce((a, b) => (b.fW > a.fW ? b : a));
    let Apk = 0; for (let i = 1; i <= n; i++) Apk += 0.5 * ((uCam(etas[i]) - c) + (uCam(etas[i - 1]) - c)) * (etas[i] - etas[i - 1]);
    const flag = Math.max(0, xE0 - (xL - capW / 2)), wExt = (xR + px / 2) - (xL - px / 2);
    const mPlate = RHO * P.cam_t * Math.max(0, P.cam_w * Lpl - Apk + 2 * ls * flag), mPed = 4 * RHO * (px * ls * Math.max(0, hPed) + capW * ls * 15);
    const mExt = 2 * RHO * ls * (Math.max(wExt, P.w_bed) * P.t_bed - P.w_slot * P.h_slot - P.w_tee * P.h_tee);
    const mFol = RHO * (Math.PI / 4 * P.cam_df ** 2 * P.cam_bf + Math.PI / 4 * P.cam_dp ** 2 * (lFp + 30));
    return { clr, uNeed, uCam, fam, muC, muP, kt, kp, lockDem, lockCap, alpha: P.cam_alpha, c, m, travel: trav, uPk, eta0, eta1, etaEnd, etaR1, etaX1, etaE0, etaAp, hasPk, needMax, sync, syncIn, etaSync, cover, prof,
      perfil_y: prof.map(([e, u]) => ({ eta: e, y: yOf(e), u, x_canto: xE0 + (u - c) })), need: etas.map((e, i) => ({ eta: e, u_need: need[i], u_leva: uCam(e) })),
      zc0, zU, zS, zPb, zF, zTop, xFp0, xE0, xPo, wNet, lFp, Lsp, Lpl, hPed, Fret, NR, NRx, NT, Nd, sigPl, kM, kR, bolts: cg, ped: cp, weld: cw, Fwc, Apk, portico: { xL, xR, px, ls, capW, flag, wExt },
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
  // Placa-leva del modo pivotado. w = desplazamiento lateral de Q hacia afuera (−t) respecto de la recta E–P al inicio: Q(L, w) = E + L·û(ψ₀ − w/L).
  // Empuje: w_emp(L) (alineación E–Q–P); retorno (mesa detenida: B en θ_ini y el anterior a B): w_nec(L) = menor w con holgura ≥ margen
  // (bloque alineado con el vástago). Canto de la leva (centro del seguidor): w_leva = máx(w_emp + c; bolsillo) con rampa a α desde L0 + tramo.
  const camPivMemo = memoP((P) => camPivRaw(P, kinPiv(P)), true);
  function camPiv(P, K) { return K && K.ok ? (K === kinPiv(P) ? camPivMemo(P) : camPivRaw(P, K)) : null; }
  function camPivRaw(P, K) {
    if (!K || !K.ok) return null;
    const r = P.d_pin / 2, R = P.R_pin, E = K.E, Lqp = K.Lqp, psi0 = K.pts[0].psi, L0 = P.L0, Ls = K.Ls, Le = K.Lend, fam = camFam(P);
    const Qof = (L, w) => { const ps = psi0 - w / L, u = [Math.cos(ps), Math.sin(ps)]; return { Q: [E[0] + L * u[0], E[1] + L * u[1]], u }; };
    const pushW = K.pts.map((q) => [q.L, -q.L * (q.psi - psi0)]);
    const wPush = (L) => { if (L <= Ls) return 0; for (let i = 1; i < pushW.length; i++) if (L <= pushW[i][0]) { const [a0, b0] = pushW[i - 1], [a1, b1] = pushW[i]; return b0 + (b1 - b0) * (L - a0) / (a1 - a0); } return pushW[pushW.length - 1][1]; };
    const pins = [K.ths - K.pitch, K.ths].map((th) => [R * Math.cos(th), R * Math.sin(th)]);   // B y el anterior (A queda adelante de la cara: el retorno se aleja de él)
    const clrRet = (L, w) => { const { Q, u } = Qof(L, w); return Math.min(...pins.map((p) => unaDist(P, p[0], p[1], Q, u, Lqp))) - r; };
    const m = P.pv_msync, c = P.pv_c, al = P.pv_alpha * D2R, ta = Math.tan(al), n = 160;
    const wNeed = (L) => {
      if (clrRet(L, 0) >= m) return 0;
      let lo = 0, hi = NaN; for (let w = 5; w <= 400; w += 5) { if (clrRet(L, w) >= m) { hi = w; break; } lo = w; }
      if (!isFinite(hi)) return Infinity;
      for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (clrRet(L, mid) >= m) hi = mid; else lo = mid; }
      return hi;
    };
    const Lg = Array.from({ length: n + 1 }, (_, i) => L0 + (Le - L0) * i / n), need = Lg.map(wNeed), base = Lg.map((L) => wPush(L) + c);
    const wPk = Math.max(0, ...need.map((x) => (isFinite(x) ? x : 1e9)));
    let LX1 = -Infinity; Lg.forEach((L, i) => { if (need[i] > base[i]) LX1 = Math.max(LX1, L - (wPk - Math.min(need[i], wPk)) / ta); });
    const hasPk = isFinite(LX1), Lend = L0 + P.pv_dwell;
    if (hasPk) LX1 += 5;                                                // 5 mm de holgura de fabricación en la salida del bolsillo hacia la carrera de empuje
    const wCam = (L) => { const b = wPush(L) + c; return !hasPk || L <= Lend ? b : Math.max(b, Math.min(wPk, c + ta * (L - Lend), wPk - ta * (L - LX1))); };
    const Lr1 = Math.min(Lend + (wPk - c) / ta, (wPk - c + ta * (Lend + LX1)) / (2 * ta));   // fin de la rampa de reenganche (o vértice del bolsillo)
    let sync = Infinity, Lsync = L0, syncOut = Infinity; Lg.forEach((L) => { const s = clrRet(L, wCam(L)); if (L <= Lr1) { if (s < sync) { sync = s; Lsync = L; } } else syncOut = Math.min(syncOut, s); });
    { const dL = (Le - L0) / n, c0 = Lsync; for (let k = -40; k <= 40; k++) { const L = c0 + dL * k / 40; if (L < L0 || L > Lr1) continue; const s = clrRet(L, wCam(L)); if (s < sync) { sync = s; Lsync = L; } } }   // refinamiento local del mínimo
    let held = 0, tot = 0; Lg.forEach((L) => { if (L >= Ls) { tot++; if (Math.abs(wCam(L) - (wPush(L) + c)) < 1e-9) held++; } });
    // geometría en planta: trayectoria del centro del seguidor (Q a w_leva), canto (desplazado d_q/2 hacia −t), borde exterior y pernos sobre el eje del labio
    const rf = P.pv_dq / 2, wOut = Math.max(...Lg.map(wCam)) + rf + P.pv_wlip, eEnd = rf + 30;
    const Lp = [L0 - eEnd].concat(Lg, [Le + eEnd]);
    const path = Lp.map((L) => { const w = wCam(Math.min(Math.max(L, L0), Le)), { Q, u } = Qof(L, w); return { L, w, x: Q[0], y: Q[1], cx: Q[0] + rf * u[1], cy: Q[1] - rf * u[0], ox: 0, oy: 0 }; });
    path.forEach((p) => { const { Q, u } = Qof(p.L, wOut); p.ox = Q[0]; p.oy = Q[1]; const wl = wOut - P.pv_wlip / 2, q2 = Qof(p.L, wl); p.lx = q2.Q[0]; p.ly = q2.Q[1]; });
    let Lb = 0, area = 0; for (let i = 1; i < path.length; i++) { Lb += Math.hypot(path[i].cx - path[i - 1].cx, path[i].cy - path[i - 1].cy); area += 0.5 * ((wOut - path[i].w - rf) + (wOut - path[i - 1].w - rf)) * (path[i].L - path[i - 1].L); }
    const nb = Math.max(2, Math.round(P.pv_nb)), sb = Lb / (nb - 1), bolts = Array.from({ length: nb }, (_, k) => { const L = (L0 - eEnd) + (Le - L0 + 2 * eEnd) * k / (nb - 1), q = Qof(L, wOut - P.pv_wlip / 2).Q; return [q[0], q[1]]; });
    const Bh = P.B / 2 - P.rim_t - 5, ed = [E[0] / K.RE, E[1] / K.RE], pts = path.flatMap((p) => [[p.cx, p.cy], [p.ox, p.oy]]);
    const inBase = Math.max(...pts.map(([x, y]) => Math.max(Math.abs(x), Math.abs(y)))), side = pts.map(([x, y]) => x * ed[1] - y * ed[0]), sgn = Math.sign(side.reduce((a, b) => a + b, 0)) || 1;
    const diag = Math.min(...side.map((s) => s * sgn)), Rin = Math.min(...path.map((p) => Math.hypot(p.cx, p.cy)));
    return { fam, c, m, alpha: P.pv_alpha, Lend, LX1, Lr1, hasPk, wPk, sync, syncOut, Lsync, cover: tot ? held / tot : 1, need: Lg.map((L, i) => ({ L, w_nec: need[i], w_emp: wPush(L), w_leva: wCam(L) })), path, bolts, Lb, sb, area, wOut, rf, inBase, Bh, diag, Rin, wCam, wPush, Qof, clrRet, wNeed, psi0, pins };
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
    const mode = driveMode(P), fam = camFam(P);
    const K = mode === 2 ? kinPiv(P) : kinematics(P);
    const A = Math.PI / 4 * P.D_bore ** 2, Aann = A - Math.PI / 4 * P.d_rod ** 2;
    const Fstall = A * P.p_relief / 10 / 1e3, Falarm = A * P.p_alarm / 10 / 1e3, Fret = Aann * P.p_ret / 10 / 1e3;
    const torque = (mu, r) => mu * N * r / 1e3 + T_piv(mu);                                   // kN·m
    let dpts, atPt, Fcyl, Kg, stallMax;
    if (mode === 2) {
      // Pivotado: por unidad de par T (kN·m) en el pasador: F_n = (T/n)/a_ef (a_ef = a − μ_s·|v_s|, potencia virtual con el roce del contacto);
      // la leva toma la fuerza transversal T_leva = μ_s·F_n en Q y su roce μ_leva·T_leva se suma al cilindro: F_cil·η = F_n·(1 + μ_leva·μ_s).
      const kf = 1 + fam.mu * P.mu_s;
      dpts = K.ok ? K.pts : [];
      atPt = (d, T) => { const Fp = T * 1e3 / P.n_cyl / d.aEff; return { Fp, H: P.mu_s * Fp, Fcam: P.mu_s * Fp, Rf: 0, Rr: 0, F: Fp * kf / P.eta_c }; };
      Fcyl = (T) => Math.max(...dpts.map((d) => atPt(d, T).F));
      Kg = () => Fcyl(1) * P.n_cyl * K.armMin / 1e3;
      const Fp = Fstall * P.eta_c / kf;
      stallMax = { Fp, H: P.mu_s * Fp, Fcam: P.mu_s * Fp, R: 0, Rsum: 0 };
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
    const curve = !K.ok ? [] : mode === 2 ? K.pts.map((q) => ({ s: q.L - P.L0, arm: q.a, armEff: q.aEff, F: cd ? atPt(q, cd.T).F : 0 })) : K.pts.map((q) => ({ s: q.s, arm: q.arm, F: cd ? Fcyl(cd.T, q.arm) : 0 }));
    const stroke = !(K.ok && cd) ? [] : mode === 2 ? dpts.map((d) => Object.assign({ th: d.th, s: d.L - P.L0, L: d.L, arm: d.a, armEff: d.aEff, psi: d.psi, ft: d.ft, fr: d.fr }, atPt(d, cd.T)))
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
      res.sup = pivSupGeo(P); res.blk = pivBlkGeo(P, K); res.camP = Object.assign({}, camPiv(P, K));   // copia: la leva memorizada no lleva las fuerzas, que dependen de la carga
      const CP = res.camP, Fn = (T) => Math.max(...dpts.map((d) => atPt(d, T).Fp)), Tdis = cd ? P.mu_s * Fn(cd.T) * 1e3 : 0;   // N
      const NR = Fret * 1e3 / Math.sin(P.pv_alpha * D2R), Tst = stallMax.Fcam * 1e3, Ncam = Math.max(NR, Tst);
      const vQ = (P.Q_pump * 1e6 / 60 / (P.n_cyl * A)) / 1000 * Math.max(...K.pts.map((q, i) => (i ? Math.hypot(q.Q[0] - K.pts[i - 1].Q[0], q.Q[1] - K.pts[i - 1].Q[1]) / Math.max(1e-9, Math.abs(q.L - K.pts[i - 1].L)) : 0)));   // m/s del seguidor
      let lpad = P.pv_dq;
      if (fam.tipo === "pad") {   // p_adm y PV del material con la carga de diseño (como la interfaz de giro); a calado, aplastamiento BTH-1 (filas)
        const lp = Tdis / (0.9 * fam.pAdm * P.pv_tcam), lv = fam.PV ? Tdis * vQ / (0.9 * fam.PV * P.pv_tcam) : 0;
        lpad = P.pv_lpad > 0 ? P.pv_lpad : Math.max(P.pv_dq, Math.ceil(Math.max(lp, lv) / 5) * 5);
      }
      CP.lpad = lpad; CP.Ncam = Ncam; CP.NR = NR; CP.Tst = Tst; CP.Tdis = Tdis; CP.vQ = vQ;
      const mPad = fam.tipo === "pad" ? 2 * P.n_cyl * (RHO * lpad * P.pv_tcam * 25) : 0;   // zapata de acero de 25 mm de espesor con su revestimiento en la leva
      m.cam += mPad; m.total += mPad; m.camPad = mPad;
    }
    // barras de los topes soldados: dependen del par de calado, así que se dimensionan aquí y suman a m.total (no están en ninguna otra pieza).
    // Las barras de la mesa giran y cargan la interfaz, pero no se realimentan a N (< 0,01 %; evita la dependencia circular con el par de calado).
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
  function runDisc(P, R, which, coarse) {
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
    const hc = P.h_disc - (P.t_top + P.t_bot) / 2;
    const imb = Q[n - 1] * 2 * Math.PI * Rd / 1e3;
    return { Mmax, rM, sigTop: Mmax / (P.t_top * hc), sigBot: Mmax / (P.t_bot * hc), Vmax: Vmax / 1e3, rV, imbalance: imb };
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
      const g = th.grad, h = P.h_disc, kap = al.st * g / h, sag = kap * (P.D_top / 2) ** 2 / 2, sigTh = P.E * al.st * g / (2 * (1 - P.nu));
      const gapR = kap * (Ro * Ro - Ri * Ri) / 2, win = kap * (P.ss_void / 2) ** 2 / 2;
      const GREF = REG + "; EN 1991-1-5 §6.1.4.1 Tabla 6.1 (tableros de puentes: otra tipología); σ de la placa restringida según Timoshenko";
      tadd({ sub: "d", kind: "info", conf: "C", name: "Gradiente: curvatura térmica de la mesa", formula: "κ = α·ΔT_grad/h con h = h_mesa = " + P.h_disc + " mm", dem: kap * 1e3, unit: "1/m", ref: GREF });
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
      const q = K.at(th); q.aEff = q.a - P.mu_s * Math.abs(q.vs);
      const Fp = T * 1e3 / P.n_cyl / q.aEff;
      return { F: Fp * (1 + R.fam.mu * P.mu_s) / P.eta_c, Fp, H: P.mu_s * Fp, Rf: 0, Rr: 0, arm: q.a, armEff: q.aEff, ft: q.ft, fr: q.fr, caso: c.id };
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
  // 2. Geometría fija del modo pivotado: ojales, placas-leva (recorte y contorno por cilindro y sentido), bloque-uña (marco local), pasador Q, L0 y carrera
  function pivotGeo(P) {
    const R = simR(P), K = R.K, CP = R.camP;
    if (driveMode(P) !== 2 || !K.ok || !CP) return null;
    const placas = {};
    [1, 2].forEach((cil) => ["antihorario", "horario"].forEach((sen) => {
      const f = pivTr(P, sen, cil), rec = CP.path.map((p) => f([p.cx, p.cy])), ext = CP.path.map((p) => f([p.ox, p.oy]));
      placas[cil + "_" + sen] = { recorte: rec, contorno: rec.concat(ext.slice().reverse()), pernos: CP.bolts.map(f), centro_seguidor: CP.path.map((p) => f([p.x, p.y])) };
    }));
    const loc = unaPolys(P, [0, 0], [1, 0], K.Lqp);
    return { E: [K.E, [-K.E[0], -K.E[1]]], R_E: K.RE, phi_E: P.pv_phE, L_qp: K.Lqp, L0: P.L0, carrera: P.stroke, s_libre: P.s_free, s_req: K.s_req, th_ini: K.ths, th_fin: K.the, paso: K.pitch,
      placas, t_placa: P.pv_tcam, bloque: { local: loc, nota: "marco local: origen en Q, eje x hacia el pasador tomado (s), eje y = t (hacia el centro O)", d_Q: P.pv_dq, h: P.pv_hu, R_cubo: P.pv_dq / 2 + 25 },
      pasadorQ: { d: P.pv_dq, largo: R.blk.lPin }, ojalE: { d: P.pv_dE, lado_cajon: P.pv_box } };
  }
  // 3. Estado del modo pivotado en la posición s del vástago (s = L − L0, 0 … s_req). fase = «empuje» | «retorno»; sentido = «antihorario» | «horario» (cilindro 1).
  //    Empuje: s ≤ s_libre aproximación sin contacto (θ = θ_ini); luego |P(θ) − E| = L0 + s + L_qp. Retorno (mesa detenida en θ_fin): Q se desplaza w hacia afuera
  //    lo que exige el pasador siguiente (holgura 0) sin pasar del canto de la leva; la leva lo devuelve en la rampa. alertas.sincronia: con Q contra la leva la holgura
  //    es menor que el margen (misma definición que la verificación); alertas.choque: la leva obliga a una posición con interferencia.
  function pivotAt(P, s, fase, sentido) {
    const R = simR(P), K = R.K, CP = R.camP;
    if (driveMode(P) !== 2 || !K.ok || !CP) return null;
    const L = P.L0 + Math.max(0, Math.min(s, K.s_req)), f = pivTr(P, sentido, 1), cd = caseOf(R, "dis");
    let th, w, Fc = 0, dr = null, hol, holL;
    if (fase !== "retorno") {
      th = L <= K.Ls ? K.ths : K.ths + Math.acos(Math.max(-1, Math.min(1, (P.R_pin ** 2 + K.RE ** 2 - (L + K.Lqp) ** 2) / (2 * P.R_pin * K.RE)))) - Math.acos(Math.max(-1, Math.min(1, (P.R_pin ** 2 + K.RE ** 2 - (K.Ls + K.Lqp) ** 2) / (2 * P.R_pin * K.RE))));
      w = CP.wPush(L);
      if (L > K.Ls) { dr = driveAtSim(P, th, "dis"); Fc = P.mu_s * dr.Fp; }
      hol = Infinity; holL = Infinity;
    } else {
      th = K.the;
      const wA = CP.wPush(K.Lend), wc = CP.wCam(L);
      let wn = 0; if (CP.clrRet(L, 0) < 0) { let lo = 0, hi = 400; for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (CP.clrRet(L, mid) >= 0) hi = mid; else lo = mid; } wn = hi; }
      w = Math.max(Math.min(wA, wc), Math.min(wn, wc));
      hol = CP.clrRet(L, w); holL = CP.clrRet(L, wc);
    }
    const { Q, u } = CP.Qof(L, w), t = [-u[1], u[0]], rf = P.pv_dq / 2;
    const pol = unaPolys(P, Q, u, K.Lqp), tr = (pg) => pg.map(f);
    const enRampa = fase === "retorno" && L <= CP.Lr1 && L >= CP.Lend;
    return { th: sentido === "horario" ? 2 * P.pv_phE * D2R - th : th, th_cil1_antihorario: th, L, s: L - P.L0, phi: Math.atan2(u[1], u[0]), phi_f: Math.atan2(f([u[0], u[1]])[1], f([u[0], u[1]])[0]), w, Q: f(Q), E: f(K.E),
      una: { poligono: tr(pol.cuerpo).concat(tr(pol.cara)), cuerpo: tr(pol.cuerpo), cara: tr(pol.cara), cubo: tr(pol.cubo) },
      contactoLeva: { punto: f([Q[0] - rf * t[0], Q[1] - rf * t[1]]), F: Fc, enRampa },
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
    const legs = yS.flatMap((y0) => [por.xL, por.xR].map((xc) => ({ x: [xc - por.px / 2, xc + por.px / 2], y: [y0 - P.cam_ls / 2, y0 + P.cam_ls / 2], z: [P.t_base + P.t_bed, c.zPb - 15] })));
    const caps = yS.flatMap((y0) => [por.xL, por.xR].map((xc) => ({ x: [xc - por.capW / 2, xc + por.capW / 2], y: [y0 - P.cam_ls / 2, y0 + P.cam_ls / 2], z: [c.zPb - 15, c.zPb] })));
    const nb2 = Math.max(1, Math.round(P.cam_nb / 2)), bolts = yS.flatMap((y0) => [por.xL, por.xR].flatMap((xc) => Array.from({ length: nb2 }, (_, k) => [xc, y0 - P.cam_ls / 2 + J34M(P.cam_db) + (nb2 > 1 ? k * (P.cam_ls - 2 * J34M(P.cam_db)) / (nb2 - 1) : (P.cam_ls / 2 - J34M(P.cam_db)))])));
    const ext = [-1, 1].map((sg) => ({ x: [xFlag + (por.capW - por.px) / 2, por.xR + por.px / 2], y: sg > 0 ? [g.Y_bed, g.Y_bed + P.cam_ls] : [-g.Y_bed - P.cam_ls, -g.Y_bed], z: [P.t_base, P.t_base + P.t_bed] }));
    const yFol = P.l_p - P.d_pin / 2 - P.dog_b / 2;    // seguidor respecto del pasador del vástago (y)
    const fam = c.fam, mat = fam.f === 1 ? "42CrMo4+QT, canto templado por inducción ≥ 55 HRC (rodillo de leva templado)" : fam.nombre + " (zapata deslizante; no cumple en el modo guiado)";
    const T = (sx, dy) => (q) => [sx * q[0], dy * q[1]], conf = { "1_antihorario": [1, 1], "2_antihorario": [-1, -1], "1_horario": [1, -1], "2_horario": [-1, 1] };
    return {
      sistema: "planta x, y (mm) con O en el centro de la mesa; z desde la cara inferior de la base (piso); local = lado +x, empuje +y (cilindro 1, antihorario)",
      riel: { contorno_local: riel, t: P.cam_t, z: [c.zPb, c.zPb + P.cam_t], material: mat, Fy: P.Fy_cam, nota: "canto interior = leva (toma, bolsillo y rampa); aletas hacia adentro en la zona de los pórticos (el seguidor no llega); se voltea para el otro sentido de giro (simetría en y)" },
      porticos: { patas_local: legs, tapas_local: caps, pernos_local: bolts, d_perno: P.cam_db, agujero: P.cam_db + 2, filete_pata_asiento: P.cam_wf, material: "42CrMo4+QT (patas y tapas)" },
      prolongacion_bancada_local: ext,
      seguidor: { rodillo: { d: P.cam_df, b: P.cam_bf, z: [c.zF - P.cam_bf / 2, c.zF + P.cam_bf / 2] }, perno: { d: P.cam_dp, largo: c.lFp + 30, empotrado_en_una: 30, z_cara_sup_una: c.zU }, x_eje_toma: c.xFp0, y_respecto_pasador_vastago: yFol, recorrido_x: c.travel },
      ranura_tapa_patin: { ancho: P.cam_dp + 1, x: [c.xFp0 - (P.cam_dp + 1) / 2, c.xFp0 + c.travel + (P.cam_dp + 1) / 2], y_respecto_pasador_vastago: yFol, t_tapa: P.t_pk, nota: "ranura pasante en la tapa del alojamiento de la uña (guía del perno en y, ajuste H9/f8)" },
      instancias: Object.fromEntries(Object.entries(conf).map(([k, [sx, dy]]) => { const f = T(sx, dy); return [k, { lado: sx, sentido: dy, riel: riel.map(f), pernos: bolts.map(f), patas: legs.map((l) => ({ x: l.x.map((v) => sx * v).sort((a, b) => a - b), y: l.y.map((v) => dy * v).sort((a, b) => a - b), z: l.z })) }]; })),
    };
  }
  // Modo pivotado: cajón y tapas del ojal E, pasador E, bloque-uña acodado, pasador Q, 4 placas-leva (contorno con bolsillo y rampa, pernos, material)
  function pivotFab(P, R) {
    const K = R.K, sg = R.sup, bk = R.blk, CP = R.camP, G = pivotGeo(P), fam = CP.fam;
    const b = P.pv_box, E = K.E, sx = Math.sign(E[0]) || 1, sy = Math.sign(E[1]) || -1;
    const psis = K.pts.map((q) => q.psi), ph = P.pv_phE * D2R, refl = (a) => 2 * ph - a, deg = (a) => ((a / D2R) % 360 + 360) % 360;
    const sec = [Math.min(...psis), Math.max(...psis), Math.min(...psis.map(refl)), Math.max(...psis.map(refl))].map(deg);
    const box = (Ec, s1, s2) => ({ centro: Ec, esquinas: [[Ec[0] - b / 2, Ec[1] - b / 2], [Ec[0] + b / 2, Ec[1] - b / 2], [Ec[0] + b / 2, Ec[1] + b / 2], [Ec[0] - b / 2, Ec[1] + b / 2]],
      paredes_completas: [s1 > 0 ? "x+" : "x−", s2 > 0 ? "y+" : "y−"], paredes_con_ventana: [s1 > 0 ? "x−" : "x+", s2 > 0 ? "y−" : "y+"] });
    const pl = fam.f === 1 ? "S355J2 con canto templado (inserto o placa templable) ≥ 55 HRC" : "S355J2 (respaldo) con revestimiento de " + fam.corto + " de " + P.pv_tlin + " mm en el canto";
    return {
      sistema: "planta x, y (mm) con O en el centro de la mesa; z desde la cara inferior de la base (piso)",
      soporte_E: { cilindro1: box(E, sx, sy), cilindro2: box([-E[0], -E[1]], -sx, -sy), lado: b, t_pared: P.pv_tbox, alto_paredes: sg.hBox, z_paredes: [P.t_base, P.t_base + sg.hBox],
        tapas: { t: P.pv_tl, lado: b, z_inf: [sg.zL - P.pv_tl / 2, sg.zL + P.pv_tl / 2], z_sup: [sg.zU - P.pv_tl / 2, sg.zU + P.pv_tl / 2], agujero_E: P.pv_dE, ajuste: "H9/f8" },
        ventana: { sector_deg: [Math.min(sec[0], sec[2]) - 10, Math.max(sec[1], sec[3]) + 10], z: [sg.zL + P.pv_tl / 2, sg.zU - P.pv_tl / 2], nota: "abertura en las dos paredes que miran a la mesa para el giro del ojal en ambos sentidos (± 10° de holgura); la sección resistente es la U de las paredes completas" },
        soldadura: { filete: P.pv_wbox, paredes_base: "a ambos lados de las paredes, perimetral a la base", tapas_paredes: "filete a ambos lados del mismo tamaño" }, material: "S355J2 (Fy " + P.Fy + ")" },
      pasador_E: { d: P.pv_dE, largo: sg.forkH + 20, z: [sg.zL - P.pv_tl / 2 - 10, sg.zU + P.pv_tl / 2 + 10], material: "Fy " + P.Fy_pp + " MPa", ajuste: "H9/f8" },
      bloque_una: { contorno_local: G.bloque.local, h: P.pv_hu, z: [bk.zBot, bk.zBot + P.pv_hu], agujero_Q: P.pv_dq, horquilla: { ranura_ojal: P.b_eye + 2 * P.g_ch, t_mejilla: bk.tq, R_cubo: bk.eb }, cuerpo: { b: P.pv_bu, e_acodado: P.pv_ecr }, cara: { b: P.pv_bf, l: P.pv_lf, templada: "≥ 55 HRC (Fy_sup " + P.Fy_surf + ")" }, material: "34CrNiMo6+QT (Fy " + P.Fy_dog + ")",
        nota: "marco local: origen en Q, x hacia el pasador tomado, y = t (hacia O); el cuerpo se desplaza e_acodado hacia −y" },
      pasador_Q: { d: P.pv_dq, largo: bk.lPin, z: [P.t_base + 2, bk.zBot + P.pv_hu], extremo_inferior: "seguidor de la placa-leva (" + (fam.tipo === "hertz" ? "templado" : "con zapata de " + CP.lpad + " mm") + ")", voladizo_bajo_horquilla: bk.lq, material: "Fy " + P.Fy_pp + " MPa" },
      placas_leva: { instancias: G.placas, t: P.pv_tcam, z: [P.t_base, P.t_base + P.pv_tcam], material: pl, familia: fam.f, revestimiento: fam.f > 1 ? { material: fam.nombre, t: P.pv_tlin } : null, zapata: fam.tipo === "pad" ? { largo: CP.lpad, alto: P.pv_tcam } : null,
        pernos: { d: P.pv_db, n: Math.round(P.pv_nb), agujero: P.pv_db + 2, clase: "10.9 a la base (roscado o pasante con tuerca bajo la base)" }, ancho_labio: P.pv_wlip },
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
    fabricacion: camGuidedFab(P, R, c),
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
    E: f(K.E), Q: K.pts.map((q) => f(q.Q)), P: K.pts.map((q) => f(q.P)),
    leva_centro_seguidor: CP.path.map((p) => f([p.x, p.y])), leva_canto: CP.path.map((p) => f([p.cx, p.cy])), leva_borde_exterior: CP.path.map((p) => f([p.ox, p.oy])), leva_pernos: CP.bolts.map(f) });
  return {
    E: K.E, R_E: K.RE, phi_E: P.pv_phE, L_qp: K.Lqp, automatico: K.auto, sugerencia: K.sugerencia || suggestE(P), theta_ini_deg: K.ths / D2R, theta_fin_deg: K.the / D2R,
    brazo_min: K.aMin, brazo_max: K.aMax, brazo_ef_min: K.aEffMin, carrera_req: K.sReq, Q_min: K.QrMin, holgura_pasador_siguiente: K.clrB, holgura_cuerpo_mesa: K.body,
    cinematica: R.stroke.map((q) => ({ th: q.th / D2R, a: q.arm, a_ef: q.armEff, L: q.L, s: q.s, psi_deg: q.psi / D2R, f_tang: q.ft, f_rad: q.fr, F_cil: q.F, F_n: q.Fp, F_leva: q.Fcam, p: q.F * 1e3 / R.A * 10 })),
    bloque_una: { b_cuerpo: P.pv_bu, e_acodado: P.pv_ecr, b_cara: P.pv_bf, l_cara: P.pv_lf, h: P.pv_hu, d_Q: P.pv_dq, R_cubo: bk.eb, s_cara_ini: bk.s1, s_cara: bk.s2, t_horquilla: bk.tq, z_inf: bk.zBot, l_pasador_Q: bk.lPin, voladizo_leva: bk.lq, masa: bk.m },
    soporte_E: { lado_cajon: P.pv_box, t_pared: P.pv_tbox, filete: P.pv_wbox, t_tapas: P.pv_tl, d_E: P.pv_dE, alto: sg.hBox, z_tapa_sup: sg.zU, z_tapa_inf: sg.zL, S_U: sg.S, masa: sg.m, nota: "cajón centrado en E; paredes traseras en L hacia la esquina; ventana para el ojal hacia la mesa (sección resistente en U)" },
    placa_leva: { familia: CP.fam.f, familia_nombre: CP.fam.nombre, automatico: CP.fam.auto, mu: CP.fam.mu, t: P.pv_tcam, ancho_labio: P.pv_wlip, t_revestimiento: CP.fam.f > 1 ? P.pv_tlin : 0, l_zapata: CP.lpad, n_pernos: Math.round(P.pv_nb), d_perno: P.pv_db, Fy: P.Fy_camP,
      holgura: CP.c, margen_sincronia: CP.m, sincronia: CP.sync, alpha_deg: CP.alpha, bolsillo_w: CP.wPk, fraccion_empuje_retenida: CP.cover, L_fin_rampa: CP.Lend, L_tope_rampa: CP.Lr1, L_salida_bolsillo: CP.LX1, perfil: CP.need,
      fuerzas_N: { rampa_atasco: CP.NR, transversal_calado: CP.Tst, transversal_diseno: CP.Tdis, diseno: CP.Ncam }, v_seguidor_m_s: CP.vQ, area: CP.area, largo_canto: CP.Lb },
    posiciones: Object.fromEntries(Object.entries(tr).map(([k, f]) => [k, pts(f)])),
    fabricacion: pivotFab(P, R),
    nota: "coordenadas en planta (mm) con O en el centro; Q y P: 61 posiciones del empuje; leva_centro_seguidor: trayectoria del centro del extremo inferior de Q contra la leva (empuje + bolsillo + rampa); leva_canto: canto de contacto; leva_borde_exterior: borde de la placa; leva_pernos: ejes de los pernos" };
})();
  const masas_desc = MODE === 1 ? { brackets: "ménsulas del ojal trasero (n_br)", dogs: "uñas", shoes: "patines", beds: "bancadas", cam: "leva de reenganche: riel, soportes, prolongación de la bancada y seguidor (Tarea 1)" }
  : { brackets: "soportes del ojal E (cajón, tapas y pasador vertical; uno por cilindro)", dogs: "bloques-uña con pasador Q (uno por cilindro)", shoes: "— (no hay patín)", beds: "— (no hay bancada)", cam: "4 placas-leva con revestimiento y zapatas del seguidor" };
    const tw = R.ifc && R.ifc.tornillos, tornillos_interfaz = tw ? { aplica: "AF2: opción A pegada (fix_mode = 2), disco de la mesa → plancha inferior de la mesa", designacion: tw.designacion, n: tw.n, d: tw.d, r: tw.r, PCD: 2 * tw.r, angulos_deg: tw.ang, posiciones: tw.pos,
      avellanado: tw.avellanado, rosca_en_mesa: tw.rosca, t_disco: tw.t, t_plancha_mesa: tw.tb, V_por_tornillo_kN: tw.V / 1e3, nota: "ángulos medidos desde +x, a mitad de camino entre las ranuras radiales de engrase; avellanado 90° (ISO 10642) en la cara de deslizamiento del disco de la mesa" } : null;
    return { modo: MODE, modo_nombre: MODE === 1 ? "guiado (patín y uña sobre bancada)" : "pivotado con guía de leva (tipo KIET)", levaGuiada, pivotado, masas_desc, tornillos_interfaz };
  }

  /* ---------------- Verificaciones de la leva guiada (Tarea 1) y del modo pivotado (Tarea 2) ---------------- */
  const REG_CG = "docs/normas/registro.md, «Leva de reenganche positiva (modo guiado)»", REG_PV = "docs/normas/registro.md, «Accionamiento pivotado tipo KIET»";
  const nfx = (v, d) => (+v).toFixed(d == null ? 1 : d).replace(".", ",");
  function camGuidedRows(P, R, add) {
    const c = R.camG, G = "Leva de reenganche";
    if (!c) { add({ grp: G, sys: "giro", kind: "info", name: "Leva de reenganche positiva desactivada (opt_cam = 0): el reenganche depende solo del resorte", formula: "Sin verificación", dem: 0, unit: "–", ref: REG_CG }); return; }
    const Nd = P.Nd, Fy = P.Fy_cam, f = c.fam, Es = P.E / (2 * (1 - P.nu ** 2)), Bh = P.B / 2 - P.rim_t - 5;
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
    add({ grp: G, sys: "est", name: "Perno del seguidor: corte", formula: "τ = N/A ≤ Fy/(Nd·√3)", dem: c.Nd / Ap, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: G, sys: "est", name: "Ranura de la tapa del patín (guía del perno): aplastamiento por la fuerza en y", formula: "σ = F_ret/(d_perno·t_tapa) ≤ 1,25·Fy_patín/Nd", dem: c.Fret / (P.cam_dp * P.t_pk), cap: 1.25 * P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    add({ grp: G, sys: "est", name: "Riel-leva: flexión en planta + axial en el bolsillo (ancho reducido; biapoyado entre soportes)", formula: "σ = máx[N_toma·k_M; N_rampa,x·k_M + F_ret·w_n/… ]: N·k_M/(t·w_n²/6) + F_ret/(t·w_n); k_M = máx (L/2 + y)(L/2 − y)/L = " + nfx(c.kM) + " mm, w_n = " + nfx(c.wNet) + " mm", dem: c.sigPl, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3 y §3-2.1" });
    add({ grp: G, sys: "est", name: "Pórtico del riel: flexión de cada pata en su base (R_x/2 y R_y/2 a la altura del riel)", formula: "σ = (R_x/2)·h/(l·b²/6) + (R_y/2)·h/(b·l²/6) ≤ Fy/Nd, h = " + nfx(c.hPed) + " mm (voladizo, conservador frente al pórtico)", dem: c.ped.sPed, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    add({ grp: G, sys: "est", name: "Pórtico del riel: soldadura de cada pata a su asiento (filete perimetral)", formula: "f = √[(M_x/S_x + M_y/S_y)² + (V/(a·2(b + l)))²] ≤ 0,60FEXX/(1,20Nd); S_x = a(l·b + b²/3), S_y = a(b·l + l²/3)", dem: c.weld.fW, cap: c.Fwc, unit: "MPa", ref: "AISC 360-22 §J2.4 (grupo de soldadura, método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: G, sys: "est", name: "Pernos riel–pórtico: corte (M" + P.cam_db + ", " + P.cam_nb + " por pórtico)", formula: "f_rv = (R/n)/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu (rosca incluida), Ω = 2,00", dem: c.bolts.b.frv, cap: c.bolts.b.capV, unit: "MPa", ref: "AISC 360-22 §J3.6, Tabla J3.2" });
    add({ grp: G, sys: "est", name: "Pernos riel–pórtico: aplastamiento en el riel", formula: "R/n ≤ R_n/Ω, R_n = 2,4·d·t·Fu, Ω = 2,00", dem: c.bolts.V / 1e3, cap: c.bolts.Rn / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.10 (Ec. J3-6a)" });
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
  function pivFat(P, R, Fd) {
    const F = Fd * 1e3, sg = R.sup, Sbox = sg.S, Mb = F / 2 * (sg.hU + sg.hL), aw = 0.707 * P.pv_wbox;
    const m = pivPinM(P, R, F, P.mu_s * F);
    return { blk: F / (P.pv_bu * P.pv_hu) + 6 * F * (P.pv_ecr + P.e_dog) / (P.pv_hu * P.pv_bu ** 2), pin: Math.max(m.MQ / (Math.PI * P.pv_dq ** 3 / 32), m.ME / (Math.PI * P.pv_dE ** 3 / 32)),
      toe: Mb / Sbox, thr: Math.hypot(F / (4 * P.pv_box * aw), Mb / (aw * P.pv_box ** 2)) };
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
    if (R.sup) add({ grp: G, sys: "giro", kind: "geo", name: "Oreja inferior del ojal E sobre la base", formula: "t_base ≤ z_eje − b_ojal/2 − g − t_oreja", dem: P.t_base, cap: R.sup.zLugBot, unit: "mm", ref: "Geometría (alzado)" });
    if (CP) {
      add({ grp: G, sys: "giro", kind: "geo", name: "Sincronía del retorno: holgura bloque-uña–pasador siguiente con Q contra la rampa de la placa-leva", formula: "mín holgura(bloque alineado con el vástago, Q en w_leva(L)) ≥ margen en la rampa de reenganche (α = " + P.pv_alpha + "°, desde L0 + tramo)", dem: P.pv_msync, cap: CP.sync, unit: "mm", ref: REG_PV + "; geometría" });
      const al = P.pv_alpha * D2R, kE = P.pv_muE * P.pv_dE / (2 * P.L0);
      add({ grp: G, sys: "giro", name: "Rampa de la placa-leva sin autobloqueo (" + fam.corto + ", μ = " + nfx(fam.mu, 2) + ")", formula: "μ_E·d_E/(2·L0)·(sen α + μ·cos α) < cos α − μ·sen α (el par que hace girar el cilindro en E vence el roce del pasador E)", dem: kE * (Math.sin(al) + fam.mu * Math.cos(al)), cap: Math.cos(al) - fam.mu * Math.sin(al), unit: "–", ref: REG_PV + "; equilibrio con fricción" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-leva dentro de la base", formula: "máx(|x|; |y|) del contorno ≤ B/2 − t_marco − 5", dem: CP.inBase, cap: Bh, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "geo", name: "Placas-leva de ambos sentidos de giro a cada lado de la diagonal (no se solapan)", formula: "distancia mínima del contorno a la diagonal O–E ≥ 5 mm", dem: 5, cap: CP.diag, unit: "mm", ref: "Geometría (planta)" });
      add({ grp: G, sys: "giro", kind: "info", name: "Placa-leva: profundidad del bolsillo (salida lateral de Q para pasar sobre el pasador siguiente) y fracción del empuje con Q retenido por la leva", formula: "w_bolsillo = máx w_nec(L); fracción = parte de la carrera de empuje con w_leva = w_emp + c", dem: CP.wPk, cap: CP.cover, unit: "mm / –", ref: REG_PV });
    }
    add({ grp: G, sys: "giro", kind: "info", name: "Ojal comercial del vástago sobre el pasador Q y ojal trasero sobre el pasador E: admitir pasador y carga (pandeo del cilindro biarticulado: dato del proveedor)", formula: "Ø ojal ≥ d_Q, d_E; la fila de pandeo usa solo el vástago (L0 + carrera): confirmar con la ficha del cilindro", dem: P.pv_dq, cap: P.pv_dE, unit: "mm", ref: "Ficha del fabricante; ISO/TS 13725" });
  }
  function pivRows(P, R, add) {
    const K = R.K, CP = R.camP, bk = R.blk, sg = R.sup, fam = R.fam, Nd = P.Nd, Fy = P.Fy, Fs = R.Fstall * 1e3, Fw = P.FEXX * 0.60 / (1.20 * Nd);
    if (!K.ok || !CP || !bk || !sg) return;
    const UN = "Uña", AR = "Articulaciones", SO = "Soporte del ojal E", PL = "Placas-leva", Ncam = CP.Ncam;
    // bloque-uña
    const bu = P.pv_bu, hu = P.pv_hu, bf = P.pv_bf, ec = P.pv_ecr + P.e_dog;
    add({ grp: UN, sys: "est", name: "Bloque-uña: compresión + flexión en el cuerpo acodado (a calado)", formula: "σ = F/(b·h) + 6F·(e_cr + e)/(h·b²) ≤ Fy/Nd; F = F_calado (cota de F_n), b = " + bu + ", h = " + hu + " mm", dem: Fs / (bu * hu) + 6 * Fs * ec / (hu * bu * bu), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1 y §3-2.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: compresión + flexión en el tramo de la cara", formula: "σ = F/(b_f·h) + 6F·e/(h·b_f²) ≤ Fy/Nd", dem: Fs / (bf * hu) + 6 * Fs * P.e_dog / (hu * bf * bf), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1 y §3-2.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: corte por la fuerza transversal del roce en la cara", formula: "τ = 1,5·μ_s·F/(b·h) ≤ Fy/(Nd·√3)", dem: 1.5 * P.mu_s * Fs / (bu * hu), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    const Iu = hu * bu ** 3 / 12, Pcr = Math.PI ** 2 * P.E * Iu / (K.Lqp ** 2);
    add({ grp: UN, sys: "est", name: "Bloque-uña: pandeo en planta (biarticulado entre Q y el contacto)", formula: "F_calado ≤ Pcr/Nd; Pcr = π²·E·(h·b³/12)/L_qp²", dem: Fs / 1e3, cap: Pcr / Nd / 1e3, unit: "kN", ref: "Euler; factor Nd de ASME BTH-1 Cat. B" });
    const Es = P.E / (2 * (1 - P.nu ** 2)), qE = P.k_edge * Fs / hu, p0 = Math.sqrt(qE * Es / (Math.PI * P.d_pin / 2));
    add({ grp: UN, sys: "est", name: "Bloque-uña: contacto de Hertz cara–pasador (a calado; ambas caras templadas)", formula: "p₀ = √(q·E*/(π·r)), q = k_borde·F/h_bloque ≤ 1,67·Fy_sup", dem: p0, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: "Hertz, contacto lineal; inicio de fluencia por Tresca (p₀ = 1,67σy)" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: aplastamiento de la horquilla en el pasador Q", formula: "σ = (F/2)/(d_Q·t_h) ≤ 1,25·Fy/Nd; t_h = (h_bloque − b_ojal − 2g)/2 = " + nfx(bk.tq) + " mm", dem: Fs / 2 / (P.pv_dq * bk.tq), cap: 1.25 * P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    add({ grp: UN, sys: "est", name: "Bloque-uña: desgarro de la horquilla detrás del pasador Q", formula: "τ = (F/2)/(2·t_h·a), a = R_cubo − d_Q/2 ≤ Fy/(Nd·√3)", dem: Fs / 2 / (2 * bk.tq * (bk.eb - P.pv_dq / 2)), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (2 planos de corte)" });
    // pasadores Q y E, orejas del soporte
    const m = pivPinM(P, R, Fs, Ncam), AQ = Math.PI / 4 * P.pv_dq ** 2, AE = Math.PI / 4 * P.pv_dE ** 2;
    add({ grp: AR, sys: "est", name: "Pasador Q: flexión (horquilla del bloque) con la reacción de la leva en su extremo inferior", formula: "M = √[(F/2·(t_h/2 + g + b/4))² + (N_leva·l_Q)²], l_Q = " + nfx(bk.lq) + " mm; σ = M/(πd³/32) ≤ Fy/Nd", dem: m.MQ / (Math.PI * P.pv_dq ** 3 / 32), cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / §3-2.3" });
    add({ grp: AR, sys: "est", name: "Pasador Q: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 / AQ, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: AR, sys: "est", name: "Pasador vertical E: flexión (orejas del soporte)", formula: "M = F/2·(t_oreja/2 + g + b/4); σ ≤ Fy/Nd", dem: m.ME / (Math.PI * P.pv_dE ** 3 / 32), cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / §3-2.3" });
    add({ grp: AR, sys: "est", name: "Pasador vertical E: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 / AE, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: AR, sys: "est", name: "Tapas del cajón E (orejas del pasador): aplastamiento", formula: "σ = (F/2)/(d_E·t_tapa) ≤ 1,25Fy/Nd", dem: Fs / 2 / (P.pv_dE * P.pv_tl), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    add({ grp: AR, sys: "est", name: "Tapas del cajón E: desgarro por corte hacia la pared trasera", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = b_cajón/2 − d_E/2 = " + nfx(sg.aTear) + " mm", dem: Fs / 2 / (2 * P.pv_tl * sg.aTear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (2 planos de corte)" });
    // cajón del soporte (sección en U) y su soldadura
    const b = P.pv_box, t = P.pv_tbox, Mb = Fs / 2 * (sg.hU + sg.hL), aw = 0.707 * P.pv_wbox;
    add({ grp: SO, sys: "est", name: "Cajón del ojal E: flexión en la base (F/2 en cada tapa; sección en U con la ventana del ojal)", formula: "σ = F/2·(h_sup + h_inf)/S_U ≤ Fy/Nd; S_U = I/c de la U (pared trasera + 2 laterales) = " + nfx(sg.S / 1e3, 0) + "×10³ mm³", dem: Mb / sg.S, cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    add({ grp: SO, sys: "est", name: "Cajón del ojal E: corte (dos paredes laterales)", formula: "τ = F/(2·b·t) ≤ Fy/(Nd·√3)", dem: Fs / (2 * b * t), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: SO, sys: "est", name: "Soldadura cajón del ojal E–base (filetes a ambos lados de las tres paredes): corte y flexión", formula: "f = √[(F/(4·b·a))² + (M/(a·b²))²] ≤ 0,60FEXX/(1,20Nd); grupo en U de líneas: S = b²/2 por filete (dos filetes por pared), a = 0,707w", dem: Math.hypot(Fs / (4 * b * aw), Mb / (aw * b * b)), cap: Fw, unit: "MPa", ref: "AISC 360-22 §J2.4 (grupo de soldadura, método elástico); ASME BTH-1 §3-3.4" });
    add({ grp: SO, sys: "est", kind: "geo", name: "Filete cajón–base: mínimo según la parte más gruesa", formula: "w_mín(T = máx(t_cajón; t_base)) ≤ w; no más que la parte más delgada", dem: Math.min(wMin(Math.max(t, P.t_base)), Math.min(t, P.t_base)), cap: P.pv_wbox, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 5.8; AISC 360-22 §J2.2b" });
    add({ grp: SO, sys: "est", kind: "geo", name: "Filete cajón–base: máximo según el borde de la pared", formula: "w ≤ w_máx(t_cajón) (t < 6: t; t ≥ 6: t − 2 mm)", dem: P.pv_wbox, cap: wMax(t), unit: "mm", ref: "AISC 360-22 §J2.2b" });
    // placas-leva
    const tc = P.pv_tcam, lp = CP.lpad;
    add({ grp: PL, sys: "est", kind: "info", name: "Placa-leva (" + fam.nombre + (fam.auto ? ", automático" : "") + "): cargas del seguidor: atasco al retraer a p_ret / transversal a calado / transversal de diseño", formula: "N_rampa = F_ret/sen α; T = μ_s·F_n (roce del contacto uña–pasador); la placa se verifica con N = máx(N_rampa; T_calado)", dem: CP.NR / 1e3, cap: CP.Tst / 1e3, unit: "kN", ref: REG_PV });
    if (fam.tipo === "hertz") {
      const q = Ncam / tc, p0c = Math.sqrt(q * Es / (Math.PI * P.pv_dq / 2));
      add({ grp: PL, sys: "est", name: "Placa-leva: contacto de Hertz extremo del pasador Q–canto templado (a calado)", formula: "p₀ = √(q·E*/(π·r_Q)), q = N/t_leva ≤ 1,67·Fy_sup (canto plano, cota del recorte cóncavo)", dem: p0c, cap: 1.67 * P.Fy_surf, unit: "MPa", ref: fam.pRef });
    } else {
      const pS = Ncam / (lp * tc), pD = CP.Tdis / (lp * tc);
      add({ grp: PL, sys: "est", name: "Placa-leva (" + fam.corto + "): presión de la zapata del seguidor en el empuje de diseño", formula: "p = T_dis/(l_zapata·t_leva) ≤ p_adm (carga de diseño, como la interfaz de giro); T_dis = μ_s·F_n,dis; l_zapata = " + lp + " mm" + (P.pv_lpad > 0 ? "" : " (automático, FU 0,90 con p_adm y PV)"), dem: pD, cap: fam.pAdm, unit: "MPa", ref: fam.pRef });
      if (fam.PV) add({ grp: PL, sys: "est", name: "Placa-leva (" + fam.corto + "): valor PV de la zapata en el empuje de diseño", formula: "PV = (T_dis/(l·t))·v_Q ≤ PV_adm; v_Q = " + nfx(CP.vQ * 1000, 1) + " mm/s", dem: pD * CP.vQ, cap: fam.PV, unit: "MPa·m/s", ref: fam.pRef });
      if (fam.FyL) add({ grp: PL, sys: "est", name: "Placa-leva (" + fam.corto + "): aplastamiento del revestimiento a calado", formula: "p ≤ 1,25·Fy_rev/Nd", dem: pS, cap: 1.25 * fam.FyL / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
      if (fam.f === 2 || fam.f === 3) add({ grp: PL, sys: "est", name: "Placa-leva: respaldo de acero del revestimiento (aplastamiento a calado)", formula: "p ≤ 1,25·Fy_placa/Nd", dem: pS, cap: 1.25 * P.Fy_camP / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
      add({ grp: PL, sys: "est", kind: "geo", name: "Seguidor: largo de la zapata practicable", formula: "l_zapata ≤ 3·d_Q", dem: lp, cap: 3 * P.pv_dq, unit: "mm", ref: "Criterio del proyecto (zapata pivotante sobre el pasador Q)" });
    }
    add({ grp: PL, sys: "est", name: "Placa-leva: flexión del labio entre pernos", formula: "σ = 6·(N·s/4)/(t·w_labio²) ≤ Fy/Nd; s = " + nfx(CP.sb) + " mm entre pernos", dem: 6 * (Ncam * CP.sb / 4) / (tc * P.pv_wlip ** 2), cap: P.Fy_camP / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    const bj = boltJ3(P, P.pv_db, Ncam / 2, 0), lc = P.pv_wlip / 2 - (P.pv_db + 2) / 2, Rn = Math.min(1.2 * lc * tc * P.Fu_camP, 2.4 * P.pv_db * tc * P.Fu_camP);
    add({ grp: PL, sys: "est", name: "Pernos de la placa-leva: corte (M" + P.pv_db + ", " + Math.round(P.pv_nb) + " por placa; los dos más cercanos toman N)", formula: "f_rv = (N/2)/A_b ≤ Fnv/Ω, Fnv = 0,45·Fu, Ω = 2,00", dem: bj.frv, cap: bj.capV, unit: "MPa", ref: "AISC 360-22 §J3.6, Tabla J3.2" });
    add({ grp: PL, sys: "est", name: "Pernos de la placa-leva: aplastamiento en el agujero de la placa", formula: "N/2 ≤ R_n/Ω, R_n = mín(1,2·l_c·t·Fu; 2,4·d·t·Fu), l_c = w_labio/2 − d_h/2", dem: Ncam / 2 / 1e3, cap: Rn / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.10 (Ec. J3-6a)" });
    add({ grp: PL, sys: "est", kind: "geo", name: "Pernos de la placa-leva: distancia al borde del labio", formula: "e_mín (Tabla J3.4M) ≤ w_labio/2", dem: J34M(P.pv_db), cap: P.pv_wlip / 2, unit: "mm", ref: "AISC 360-22 §J3.4, Tabla J3.4M" });
    add({ grp: PL, sys: "est", kind: "info", name: "Masas del modo pivotado: soporte del ojal E / bloque-uña con pasador Q (por cilindro) y 4 placas-leva", formula: "m = ρ·V", dem: sg.m, cap: bk.m, unit: "kg", ref: "Geometría" });
  }

  /* ---------------- Verificaciones ---------------- */
  // kind: "fu" (FU = dem/cap), "geo" (FU con criterio geométrico), "info" (no afecta el veredicto), "pend" (pendiente de dato)
  function verifs(P, R, fea) {
    const out = [];
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
    else add({ grp: "Giro", sys: "giro", kind: "geo", name: "Carrera requerida con margen (pivotado)", formula: "L(θ_fin) − L0 + margen ≤ carrera; L(θ) = |P_i − E| − L_qp, L(θ_ini) = L0 + s_libre", dem: K.ok ? K.s_req + P.s_margin : NaN, cap: P.stroke, unit: "mm", ref: "Cinemática del cilindro pivotado (docs/normas/registro.md, «Accionamiento pivotado tipo KIET»)" });
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
    const REFW = "AWS D1.1/D1.1M:2020 Tabla 5.8 (filete mínimo por la parte más gruesa)";
    // K2: AWS (mínimo por la parte más gruesa, sin exceder la más delgada) y AISC Tabla J2.4 (por la más delgada) no coinciden; el proyecto aplica AWS
    const REFWMIN = "Se aplica la regla de AWS (parte más gruesa): AWS D1.1/D1.1M:2020 Tabla 5.8, sin exceder el espesor de la parte más delgada; AISC 360-22 Tabla J2.4 lo da por la parte más delgada (valor menor o igual) y no se usa";
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
      const REFD = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16 (placa circular empotrada, carga uniforme); 0,6Fy (AISC 360-22 F11, criterio del proyecto)";
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
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos avellanados disco–mesa: corte (" + tw.n + " × M" + tw.d + " 10.9 en R" + nfx(tw.r, 0) + ")", formula: "f_rv = V/A_b ≤ Fnv/Ω; V = T_dis/(n·r) = " + nfx(tw.V / 1e3, 2) + " kN, Fnv = 0,45·Fu (rosca incluida), Ω = 2,00", dem: tw.V / tw.Ab, cap: tw.capV, unit: "MPa", ref: "AISC 360-22 §J3.6, Tabla J3.2 (grupo 150 ≈ 10.9); " + RA });
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos: aplastamiento en el disco inoxidable de la mesa (avellanado)", formula: "V ≤ R_n/Ω, R_n = mín(1,2·l_c·t_e·Fu; 2,4·d·t_e·Fu), t_e = t − k/2 = " + nfx(tw.te, 2) + " mm, l_c = s − d_h", dem: tw.V / 1e3, cap: tw.RnD / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.10 (Ec. J3-6a); EN 1993-1-8 Tabla 3.4 (espesor con avellanado); " + RA });
          add({ grp: "Interfaz inox", sys: "est", name: "AF2 · Tornillos: aplastamiento en la plancha inferior de la mesa (agujero roscado)", formula: "V ≤ R_n/Ω, R_n = mín(1,2·l_c·t·Fu; 2,4·d·t·Fu), t = t_inf", dem: tw.V / 1e3, cap: tw.RnM / 2 / 1e3, unit: "kN", ref: "AISC 360-22 §J3.10 (Ec. J3-6a); " + RA });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: separación entre centros", formula: "3·d ≤ s = 2πr/n", dem: 3 * tw.d, cap: tw.s, unit: "mm", ref: "AISC 360-22 §J3.3" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: distancia al borde exterior del disco", formula: "e_mín (Tabla J3.4M) ≤ R_o − r", dem: J34M(tw.d), cap: R.Ro - tw.r, unit: "mm", ref: "AISC 360-22 §J3.4, Tabla J3.4M (desde M16; para menores se toma el valor de M16)" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: cabeza avellanada dentro del espesor del disco", formula: "k + 0,5 + sobreespesor de relapeado ≤ t; k = " + nfx(tw.k, 2) + " mm (ISO 10642); el disco de la mesa se dimensiona con este mínimo", dem: tw.k + 0.5 + P.ss_allow, cap: tw.t, unit: "mm", ref: "ISO 10642; criterio del mandante (cabeza ≤ espesor − 0,5 mm), también tras el relapeado" });
          add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: longitud roscada en la plancha inferior de la mesa", formula: "1,25·d ≤ t_inf (agujero roscado pasante)", dem: 1.25 * tw.d, cap: tw.tb, unit: "mm", ref: "VDI 2230 (orientativo, 10.9 en acero S355); " + RA });
          if (P.h_gr > 0) add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "AF2 · Tornillos: cabeza libre de la ranura circunferencial exterior", formula: "holgura (R_ranura − w/2) − (r + d_k/2) ≥ 3 mm", dem: 3, cap: tw.rOut - P.w_gr / 2 - tw.r - tw.dk / 2, unit: "mm", ref: "Geometría" });
          add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "AF2 · Tornillos: designación y geometría (avellanado 90°, roscado pasante en la plancha inferior)", formula: tw.designacion + "; n = " + tw.n + " a (k + ½)·360°/n, entre las ranuras radiales; Ø cabeza " + tw.dk + " mm, prof. " + nfx(tw.k, 2) + " mm", dem: tw.n, cap: tw.r, unit: "– / mm", ref: RA });
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
      const G3 = "Interfaz bronce", REFB = "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy (AISC 360-22 F11, criterio del proyecto); Fy de ASTM B584 / B148 (confirmar con el proveedor)";
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

    /* --- Cubierta de madera dura y altura de skidding --- */
    const Htop = P.t_base + R.ifc.delta + P.h_disc + (P.opt_wood > 0.5 ? P.t_wood : 0);
    if (P.opt_wood > 0.5) {
      const RLw = P.D_load / 2, Aw = Math.PI * (RLw * RLw - ((P.D_piv + 80) / 2) ** 2), qTopW = P.phi_d * R.W * 1e3 / (P.f_apoyo * Aw) * (1 + 4 * P.e / RLw);
      add({ grp: "Cubierta", sys: "est", name: "Madera: aplastamiento perpendicular a la fibra bajo la carga (área de contacto efectiva)", formula: "q = φd·W/(f_apoyo·A_círculo)·(1 + 4e/R_carga) ≤ p_adm,madera (sin acreditar reparto sobre la plancha)", dem: qTopW, cap: P.p_wood, unit: "MPa", ref: "Madera dura (datos de proveedor); criterio conservador" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: la ley lineal de presiones no admite tracción (q mín ≥ 0)", formula: "4e/R_carga ≤ 1 (e ≤ D_carga/8)", dem: 4 * P.e / RLw, cap: 1, unit: "–", ref: "Estática del apoyo" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: espesor mínimo (desgaste y fijación)", formula: "t_madera ≥ 30 mm", dem: 30, cap: P.t_wood, unit: "mm", ref: "Práctica constructiva" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Masa de la cubierta de madera (gira con la mesa y carga la interfaz)", formula: "m = ρ·A·t, A = π/4·((D − 2·t_anillo)² − Ø_abertura²): los tablones van dentro del anillo de acero; Ø_abertura = D_piv + 80 (el 3D usa una abertura mayor y N_pin bolsillos de perno y arandela que el núcleo no descuenta: conservador)", dem: R.m.wood, unit: "kg", ref: "Geometría" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Anillo de acero de contención de la madera (pletina t_anillo × t_madera en el borde, soldada a la plancha superior; incluida en la masa total y en m.disc)", formula: "m = ρ_acero·π·(R² − (R − t_anillo)²)·t_madera (alto del anillo = espesor de los tablones; ancho radial t_anillo = " + P.t_ring + " mm)", dem: R.m.ring, cap: R.m.wood, unit: "kg (anillo / madera)", ref: "Geometría; anillo adoptado por el mandante (pletina de 10 mm)" });
      add({ grp: "Cubierta", sys: "est", kind: "pend", name: "Fijación de los tablones (tornillos avellanados), acceso a la tapa de inspección, humedad y pudrición, acabado antideslizante", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
    }
    add({ grp: "Geometría", sys: "est", kind: "info", name: "Altura total sobre el piso (base + interfaz + mesa + cubierta)", formula: "H = t_base + Δ_interfaz + h_mesa + t_madera", dem: Htop, unit: "mm", ref: "Geometría" });
    if (P.h_skid > 0) add({ grp: "Geometría", sys: "est", kind: "geo", name: "Enrase de la superficie superior con los rieles de skidding", formula: "|H − h_riel| ≤ tolerancia", dem: Math.abs(Htop - P.h_skid), cap: P.tol_skid, unit: "mm", ref: "Compatibilidad con el sistema de skidding" });

    /* --- Mesa --- */
    const sAll = 0.6 * Fy;
    if (fea) {
      const k = P.kFEA;
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha superior: σvm local (carga con e)", formula: "MITC4 × k_malla", dem: fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy), criterio conservador" });
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha inferior: σvm local (contacto q_max)", formula: "MITC4 × k_malla", dem: fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy), criterio conservador" });
      const gb = fea.glob;
      add({ grp: "Mesa", sys: "est", name: "Plancha superior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local", dem: gb.sigTop + fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      add({ grp: "Mesa", sys: "est", name: "Plancha inferior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local", dem: gb.sigBot + fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      const hw = P.h_disc - P.t_top - P.t_bot;
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
    const Tw = Math.max(P.t_top, P.t_bot), Tb = Math.max(P.t_base, P.t_ch);
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
    add({ grp: "Pasadores de empuje", sys: "est", name: "Corte en el apoyo", formula: "τ = 4V/(3A), V = F_r·(1/2 + e/L) ≤ Fy/(Nd·√3)", dem: 4 * Vp * 1e3 / (3 * Ap), cap: P.Fy_pin / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento en el agujero del anillo", formula: "σ = V/(d·t) ≤ 1,25Fy/Nd", dem: sV, cap: sbA, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento en pasadores)" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento pasador–uña", formula: "σ = F/(d·h_uña) ≤ 1,25·Fy_mín/Nd (pivotado: h = alto del bloque-uña)", dem: Fs * 1e3 / (P.d_pin * (mode === 2 ? P.pv_hu : P.dog_h)), cap: 1.25 * Math.min(P.Fy_pin, P.Fy_dog) / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });

    let lev = 0, Sdog = 1, aw = 1, hax = R.hax, Spp = 1;   // usados por la fatiga del modo guiado
    if (mode === 1) {
      /* --- Uña (cara de empuje plana, templada) --- */
      const Adog = P.dog_b * P.dog_h, Hs = P.mu_s * Fs;                  // fricción radial máxima en la cara (a calado)
      lev = K.lever + P.e_dog; Sdog = P.dog_h * P.dog_b ** 2 / 6;
      add({ grp: "Uña", sys: "est", name: "Flexión en la boca del patín (voladizo) con fricción radial", formula: "σ = [F·(x_boca − a_mín + e) + μ_s·F·b/2]/(h·b²/6) + μ_s·F/(h·b) ≤ Fy/Nd", dem: (Fs * lev + Hs * P.dog_b / 2) * 1e3 / Sdog + Hs * 1e3 / Adog, cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      add({ grp: "Uña", sys: "est", name: "Corte en la boca del patín", formula: "τ = 1,5·F/(h·b) ≤ Fy/(Nd·√3)", dem: 1.5 * Fs * 1e3 / Adog, cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
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
      add({ grp: "Uña", sys: "est", name: "Corte en la sección del contacto (punta achaflanada)", formula: "τ = 1,5·F/(h·w_c), w_c = b − Δy(1 − c_punta/Δx) ≤ Fy/(Nd·√3)", dem: 1.5 * Fs * 1e3 / (P.dog_h * wC), cap: P.Fy_dog / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
      add({ grp: "Uña", sys: "est", name: "Flexión en la zona del chaflán", formula: "σ = máx 6F(x − a)/(h·w(x)²) ≤ Fy/Nd", dem: sChMax, cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      const bR = P.beta_ch * Math.PI / 180, mr = P.mu_ret, kR = 1 + 2 * Math.max(0, K.mouthX - (K.tipX + ch.dx / 2)) / P.L_in;
      add({ grp: "Giro", sys: "giro", name: "Retorno sin autobloqueo de la uña (chaflán contra el pasador siguiente)", formula: "μ·k·(sin β + μ cos β) < cos β − μ sin β, k = 1 + 2·l/L_in", dem: mr * kR * (Math.sin(bR) + mr * Math.cos(bR)), cap: Math.cos(bR) - mr * Math.sin(bR), unit: "–", ref: "Equilibrio con fricción del trinquete" });

      /* --- Patín: alojamiento de la uña --- */
      const lL = lev, cL = -lL + Math.sqrt(lL * lL + lL * P.L_in + P.L_in ** 2 / 2), sLip = Fs * 1e3 / (P.dog_h * (2 * cL - P.L_in));
      add({ grp: "Patín y guía", sys: "est", name: "Aplastamiento del alojamiento de la uña (bloque rígido-plástico)", formula: "c = −l + √(l² + l·L_in + L_in²/2); σ = F/(h·(2c − L_in)) ≤ 1,25Fy_patín/Nd", dem: sLip, cap: 1.25 * P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.5 (aplastamiento)" });
      if (K.inset > 0) {
        const Vw = Math.min(Fs, sLip * P.dog_h * Math.min(K.inset, cL) / 1e3), Hw = P.dog_h + 20;
        add({ grp: "Patín y guía", sys: "est", name: "Pared del marco de boca: flexión (voladizo del marco)", formula: "σ = 6V·(i/2)/((h+20)·t²), V = mín(F; σ_al·h·mín(i, c))", dem: 6 * Vw * 1e3 * K.inset / 2 / (Hw * P.t_fw ** 2), cap: P.Fy_shoe / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
        add({ grp: "Patín y guía", sys: "est", name: "Pared del marco de boca: corte", formula: "τ = 1,5V/((h+20)·t) ≤ Fy/(Nd·√3)", dem: 1.5 * Vw * 1e3 / (Hw * P.t_fw), cap: P.Fy_shoe / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
      }

      /* --- Patín y bancada (reacciones de guía con fricción radial, a calado) --- */
      const Rg = R.Rguide, qG = 4 * Rg * 1e3 / K.L_s;                   // presión lineal máxima (distribución triangular por mitad)
      add({ grp: "Patín y guía", sys: "est", name: "Aplastamiento de la lengüeta en la ranura (pico de la distribución lineal)", formula: "R = máx[F_pas·Δ + H·(y_c − y_r)]/Lg; σ = 4R/((h_ranura − 2)·L_patín) ≤ 1,25Fy/Nd", dem: qG / (P.h_slot - 2), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.5" });
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
        add({ grp: "Patín y guía", sys: "est", name: "Retención vertical del patín: aplastamiento en la cabeza T", formula: "V = M_vuelco/((w_b + w_T)/2) + M_cabeceo/L_patín; σ = V/(ala·L_patín) ≤ 1,25Fy/Nd", dem: Vup * 1e3 / (ov * K.L_s), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.5" });
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
      add({ grp: "Articulaciones", sys: "est", name: "Pasador: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 * 1e3 / App, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
      add({ grp: "Articulaciones", sys: "est", name: "Aplastamiento en mejillas", formula: "σ = (F/2)/(d·t) ≤ 1,25Fy/Nd", dem: Fs / 2 * 1e3 / (P.d_pp * P.t_ch), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
      const bgx = bracketGeo(P), aSh = bgx.rear - P.d_pp / 2;
      add({ grp: "Articulaciones", sys: "est", name: "Oreja superior de la ménsula: desgarro por corte tras el agujero", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = saliente − d/2", dem: Fs / 2 * 1e3 / (2 * P.t_ch * aSh), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (simplificado, 2 planos de corte)" });
      add({ grp: "Articulaciones", sys: "est", kind: "info", name: "Ojal comercial del cilindro: admitir pasador y carga", formula: "Ø ojal ≥ d_pp; ancho = b_ojal (confirmar con ficha)", dem: P.d_pp, unit: "mm", ref: "Ficha del fabricante" });
          const Mch = Fs / 2 * hax / 1e3;
      add({ grp: "Articulaciones", sys: "est", name: "Mejilla de la ménsula: flexión en la base", formula: "σ = (F/2)·h_eje/(t·L²/6) ≤ Fy/Nd", dem: Mch * 1e6 / (P.t_ch * P.L_ch ** 2 / 6), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
      aw = 0.707 * P.w_br;
      const fV = Fs * 1e3 / (4 * aw * P.L_ch), fM = Fs * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6);
      add({ grp: "Articulaciones", sys: "est", name: "Soldadura mejillas–base (4 filetes)", formula: "f = √(fV² + fM²) ≤ 0,60FEXX/(1,20Nd)", dem: Math.hypot(fV, fM), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4" });

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
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Buje sobre el collar: el buje cabe bajo la plancha superior", formula: "h_collar + g_buje + L_buje ≤ δ + h_disc − t_top", dem: P.h_boss + P.g_bush + P.L_bush, cap: R.ifc.delta + P.h_disc - P.t_top, unit: "mm", ref: "Geometría" });
      // Equilibrio del collar con el MISMO asiento rígido-lineal que da σ (no la simplificación V = H, M = H(e + L/2)): z desde la cara superior del collar,
      // w(z) = H/L·[1 + k(1 − 2z/L)], k = 6(e + L/2)/L, fuerza por unidad de profundidad (ΣF = H y ΣM_centro = H(e + L/2)). El collar (0 ≤ z ≤ h) recibe
      // V_c = ∫w dz y M_c = ∫w·(h − z) dz respecto del plano de la soldadura (cara superior de la base); la plancha base (h ≤ z ≤ L) toma la reacción de signo contrario.
      const Lc = Lseat, hc = P.h_boss, kc = 6 * (eP + Lc / 2) / Lc;
      const Vc = Math.abs(Hf * 1e3 / Lc * (hc + kc * (hc - hc * hc / Lc))), Mc = Math.abs(Hf * 1e3 / Lc * ((1 + kc) * hc * hc / 2 - kc * hc ** 3 / (3 * Lc)));   // N y N·mm
      const awc = 0.707 * P.w_collar, fbC = Mc / (Math.PI * P.D_boss ** 2 / 4 * awc), fvC = Vc / (Math.PI * P.D_boss * awc);
      add({ grp: "Pivote", sys: "est", name: "Soldadura del collar a la base (filete perimetral): V_c y M_c del asiento rígido-lineal", formula: "f = √(f_b² + f_v²) ≤ 0,60FEXX/(1,2·Nd); f_b = M_c/(π·D²/4·a), f_v = V_c/(π·D·a), a = 0,707·w_collar; V_c = H/L·[h + k(h − h²/L)], M_c = H/L·[(1 + k)h²/2 − k·h³/(3L)], k = 6(e + L/2)/L (V_c ≈ 1,875·H)", dem: Math.hypot(fbC, fvC), cap: Fw, unit: "MPa", ref: "AWS D1.1 / AISC 360-22 J2.4 (grupo circular, método elástico; resultante vectorial de corte y flexión)" });
      add({ grp: "Pivote", sys: "est", kind: "info", name: "Carga del collar sobre su filete: V_c y M_c (respecto de la cara superior de la base)", formula: "V_c y M_c de la distribución rígido-lineal del asiento; la plancha base toma la reacción de signo contrario", dem: Vc / 1e3, cap: Mc / 1e6, unit: "kN / kN·m", ref: "Equilibrio del collar" });
      const wallE = Math.min(wallC, P.h_boss);
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar: filete mínimo según la parte más gruesa (pared del collar o plancha base)", formula: "w_mín(T = máx(pared del collar = " + wallC + "; t_base = " + P.t_base + ")) ≤ w_collar; no más que la parte más delgada", dem: Math.min(wMin(Math.max(wallC, P.t_base)), Math.min(wallC, P.t_base)), cap: P.w_collar, unit: "mm", ref: REFWMIN });
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar: filete máximo según el borde del collar", formula: "w_collar ≤ w_máx(t) con t = mín(pared del collar; h_collar) = " + wallE + " (t < 6: t; t ≥ 6: t − 2 mm)", dem: P.w_collar, cap: wMax(wallE), unit: "mm", ref: "AISC 360-22 §J2.2b (tamaño máximo del filete a lo largo de bordes)" });
    }
    add({ grp: "Pivote", sys: "est", name: "Aplastamiento del buje en el cubo de la mesa (Ø exterior del buje = D_piv + 30)", formula: "σ = H/((D_piv + 30)·L_buje) ≤ 1,25·Fy/Nd", dem: Hf * 1e3 / ((P.D_piv + 30) * P.L_bush), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento)" });
    if (!(P.Ch > 0)) add({ grp: "Pivote", sys: "est", kind: "info", name: "Caso sísmico: no aplica", formula: "Sin requerimiento sísmico (decisión del mandante, 31-10-2026); si se instala en forma permanente, ingresar Ch", dem: 0, unit: "–", ref: "Decisión del mandante" });

    /* --- Base --- */
    if (fea && fea.lift) {
      add({ grp: "Base", sys: "est", name: "Izaje del conjunto: σvm en la plancha base", formula: "MITC4 × k_malla, φ_izaje; máximo a ≥ 2·pad del cáncamo (la esquina de la placa de apoyo es singular)", dem: fea.lift.vmMax * P.kFEA, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy)" });
      add({ grp: "Base", sys: "est", kind: "geo", name: "Izaje: flecha de la base", formula: "w ≤ B/300", dem: fea.lift.wMax, cap: P.B / 300, unit: "mm", ref: "Criterio del proyecto" });
    }
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje fuera de la mesa", formula: "D/2 + 10 + 35 ≤ √(x_izaje² + (B/2 − c)²) (huella Ø70)", dem: P.D_top / 2 + 45, cap: Math.hypot(P.x_lug, P.B / 2 - P.c_lug), unit: "mm", ref: "Geometría" });
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje dentro del marco", formula: "t_marco + 35 ≤ c", dem: P.rim_t + 35, cap: P.c_lug, unit: "mm", ref: "Geometría" });
    const mt = R.m.total;
    {   // orejas de izaje soldadas: 3 ramales efectivos a 60° respecto de la horizontal, carga en el plano de la oreja
      const T = mt * P.phi_lift * G / 1e3 / (3 * Math.sin(60 * D2R)), Tv = T * Math.sin(60 * D2R), Th = T * Math.cos(60 * D2R);   // kN
      const dp = P.d_ear - P.g_ear, Ln = 2 * P.R_ear, aw = 0.707 * P.w_ear, Sw = 2 * aw * Ln * Ln / 6;
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: aplastamiento del agujero (pasador del grillete d − g)", formula: "σ = T/(d_p·t) ≤ 1,25·Fy/Nd", dem: T * 1e3 / (dp * P.t_ear), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3; ASME B30.26 (grillete)" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: tracción en la sección neta del agujero", formula: "σ = T/(2(R − d/2)·t) ≤ Fy/Nd", dem: T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.1; AISC 360-22 D2" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: desgarro por corte detrás del agujero", formula: "τ = T/(2(R − d/2)·t) ≤ Fy/(Nd·√3)", dem: T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2; AISC 360-22 D5" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: soldadura a la base (filete a ambos lados, T vertical + T horizontal con brazo h)", formula: "f = √[(Tv/(2aL) + Th·h/S)² + (Th/(2aL))²] ≤ 0,60FEXX/(1,2Nd); L = 2R, a = 0,707w, S = 2aL²/6", dem: Math.hypot(Tv * 1e3 / (2 * aw * Ln) + Th * 1e3 * P.h_ear / Sw, Th * 1e3 / (2 * aw * Ln)), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4; AISC 360-22 J2.4" });
      // placa de la oreja en la base (sección 2R × t): flexión en su plano por Th·h y tracción por Tv; corte por Th
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: placa en la base: flexión Th·h + tracción Tv", formula: "σ = Th·h/(t·(2R)²/6) + Tv/(2R·t) ≤ Fy/Nd", dem: Th * 1e3 * P.h_ear / (P.t_ear * Ln * Ln / 6) + Tv * 1e3 / (Ln * P.t_ear), cap: Fy / Nd, unit: "MPa", ref: "AISC 360-22 D2; ASME BTH-1 §3-2.1 y §3-2.3" });
      add({ grp: "Orejas de izaje", sys: "est", name: "Oreja: placa en la base: corte Th", formula: "τ = Th/(2R·t) ≤ Fy/(Nd·√3)", dem: Th * 1e3 / (Ln * P.t_ear), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
      // AISC 360-22 D5.2 (miembros con pasador): b_e = mín(2t + 16 mm; (2R − d)/2) (D5.1); a = R − d/2 (extremo semicircular centrado en el agujero)
      const be = Math.min(2 * P.t_ear + 16, (Ln - P.d_ear) / 2);
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: extensión a tras el agujero ≥ 1,33·b_e (AISC D5.2(3))", formula: "a = R − d/2 ≥ 1,33·b_e; b_e = mín(2t + 16; (2R − d)/2) = " + be.toFixed(1).replace(".", ",") + " mm", dem: 1.33 * be, cap: P.R_ear - P.d_ear / 2, unit: "mm", ref: "AISC 360-22 §D5.2(3) (extensión mínima más allá del extremo de apoyo del agujero, paralela a la fuerza)" });
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: ancho de la placa en el agujero ≥ 2·b_e + d (AISC D5.2(3))", formula: "2R ≥ 2·b_e + d", dem: 2 * be + P.d_ear, cap: Ln, unit: "mm", ref: "AISC 360-22 §D5.2(3)" });
      add({ grp: "Orejas de izaje", sys: "est", kind: P.ear_gira > 0.5 ? "geo" : "info", name: "Oreja: holgura agujero–pasador ≤ 1 mm si el pasador gira bajo carga plena (AISC D5.2(2))", formula: P.ear_gira > 0.5 ? "g = d − d_pasador ≤ 1 mm" : "g = d − d_pasador = " + P.g_ear + " mm; no aplica el límite de 1 mm (izaje estático: el pasador no gira bajo la carga plena); con ear_gira = 1 exige ≤ 1 mm", dem: P.g_ear, cap: 1, unit: "mm", ref: "AISC 360-22 §D5.2(2)" });
      // filete: mínimo AWS D1.1 Tabla 5.8 por la parte más gruesa (AISC J2.4 lo da por la más delgada; el mínimo no excede la parte más delgada), máximo AISC J2.2b en el borde de la oreja
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: filete mínimo según la parte más gruesa (oreja o plancha base)", formula: "w_mín(T = máx(t_oreja; t_base) = " + Math.max(P.t_ear, P.t_base) + ") ≤ w_oreja; no más que la parte más delgada", dem: Math.min(wMin(Math.max(P.t_ear, P.t_base)), Math.min(P.t_ear, P.t_base)), cap: P.w_ear, unit: "mm", ref: REFWMIN });
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
      fat("Pie de soldadura cajón del ojal–base", f.toe, "E", nCyc);
      fat("Garganta soldadura cajón del ojal–base (corte)", f.thr, "F", nCyc);
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
    if (!opts.cache) return runDisc(P, R, which, opts.coarse);
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
    const verdict = {
      gira: R.K.ok && bad("giro").length === 0,
      estructura: bad("est").length === 0,
      warnGiro: warn("giro").length, warnEst: warn("est").length,
      pend: checks.filter((c) => c.st === "pend").length,
      fuMax: Math.max(0, ...checks.filter((c) => c.fu != null && isFinite(c.fu) && c.kind === "fu" && !c.fuera).map((c) => c.fu)),
    };
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
    const R = compute(P), mu = R.mu, kN = R.W, Htop = P.t_base + R.ifc.delta + P.h_disc + (P.opt_wood > 0.5 ? P.t_wood : 0);
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
    const fuEstOf = (A) => { let best = null; A.checks.forEach((c) => { if (!c.fuera && c.grp !== "Temperatura" && c.sys === "est" && c.kind === "fu" && isFinite(c.fu) && (!best || c.fu > best.fu)) best = c; }); return best; };
    const fuTermOf = (A) => { let best = null; A.checks.forEach((c) => { if (!c.fuera && c.grp === "Temperatura" && c.sys === "est" && c.kind === "fu" && isFinite(c.fu) && (!best || c.fu > best.fu)) best = c; }); return best; };
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

  return { driveAt: driveAtSim, pivotGeo, pivotAt, camGeo, camAt, guidedAt, designDrive, driveMode, camFam, camGuided, camPiv, kinPiv, pivKin, suggestE, pivSupGeo, pivBlkGeo, pivAsym, boltJ3, tapones, tapInfo, thermal, thermalP, thermalFactors, oilTrapped, oilViscosity, alphaSteelMean, TH_ALTS, riOf, hubGeo, capacityW, capacityByCyl, market, MARKET, prIn, pinClear, bracketGeo, guideGeo, forkH, PARAM_GROUPS, defaults, parseRings, masses, kinematics, compute, discModel, runDisc, globalBending, runLift, verifs, analyze, FSR, FAT_CAT, hAxis, G, PSI_CAT, chamferGeo };
})();
if (typeof module !== "undefined") module.exports = TT;
