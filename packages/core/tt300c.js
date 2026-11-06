/* TT300-C · Núcleo de cálculo de tornamesa hidráulica (accionamiento por cilindro pivotado y uña).
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
      ["hc_min", "Fijación desmontable · tope: altura mínima de contacto entre la barra y el canto del sector (tolerancia de corte y rebabas del canto)", "mm", 3, 1, 20, 0.5],
      ["d_tor", "Fijación desmontable: tornillo avellanado de posición (ISO 10642)", "mm", 6, 4, 12, 1],
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
    { id: "cinematica", t: "Accionamiento guiado (patín y uña)", p: [
      ["x_g", "Eje del cilindro y de la guía: distancia al centro", "mm", 1140, 500, 2500, 5],
      ["l_p", "Pasador del vástago (en el patín) → centro del pasador tomado", "mm", 300, 100, 800, 5],
      ["s_free", "Recorrido libre antes de tomar el pasador", "mm", 10, 0, 100, 1],
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
      ["Fy_dog", "Fy uña (34CrNiMo6+QT, Re ≥ 900 certificado 3.1)", "MPa", 900, 235, 1200, 5],
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
    { id: "base", t: "Base", p: [
      ["B", "Lado de la base cuadrada", "mm", 2560, 1000, 4500, 10],
      ["t_base", "Espesor plancha base", "mm", 18, 6, 60, 1],
      ["t_base_min", "Espesor mínimo de base por planitud (criterio de fabricación)", "mm", 16, 6, 60, 1],
      ["rim_h", "Alto del marco perimetral", "mm", 45, 0, 200, 1],
      ["rim_t", "Espesor del marco perimetral", "mm", 10, 0, 40, 1],
      ["c_lug", "Puntos de izaje (lados y): distancia al borde", "mm", 150, 30, 600, 5],
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
    m.wood = P.opt_wood > 0.5 ? P.rho_wood * 1e-9 * Math.PI / 4 * (P.D_top ** 2 - hole_top ** 2) * P.t_wood : 0;   // cubierta de madera (kg/m³ → kg/mm³)
    m.disc = m.top + m.bot + m.webs + m.ribs + m.hub + m.pins + m.wood;
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
  // Geometría resuelta y dimensionamiento de cada tope soldado (fijación desmontable) con el par de calado de R; la usan la masa (m.stopBars) y las verificaciones
  function stopsOf(P, R) {
    const I = R.ifc, out = [];
    if (!(I.o > 0) || !(P.fix_mode < 1.5)) return out;
    const Nd = P.Nd, Fw = P.FEXX * 0.60 / (1.20 * Nd), aInf = stopAInf(P);
    const Ftot = R.Tmax / (R.r_u / 1000), kpk = R.q_max / R.q_avg, Lav = R.Ro - R.Ri - 100;   // kN en el radio de fricción (T_calado); sector más cargado; canto radial disponible (mm)
    const push = (o) => {
      const g = stopGeo(P, o.t), Tw = Math.max(P.b_tope, o.tResp), mB = g.hB > 0 && isFinite(o.L) ? RHO * o.L * P.b_tope * g.hB : 0;
      out.push(Object.assign(o, { pieza: o.nombre, a_sup: P.a_sup, a_inf: aInf, h_barra: g.hB, h_c: g.hC, h_c_min: P.hc_min, z: g.z, w_tope: P.w_tope, b_tope: P.b_tope, w_min: wMin(Tw), Tw, Lav, m_barra: mB, m_barras: o.capas * o.n * mB }));
    };
    const sized = (id, grp, nombre, n, t, FyP, tResp, allow, capas) => {
      const g = stopGeo(P, t), Fst = Ftot / n * kpk, adm = 1.25 * Math.min(FyP, P.Fy) / Nd;       // el menor Fy entre el canto del sector y la barra
      const LreqB = g.hC > 0 ? Fst * 1e3 / (adm * g.hC) : Infinity, LreqW = weldStop(P, Fst, 1, g.z) / Fw, Lreq = Math.max(LreqB, LreqW);
      const L = P.L_tope > 0 ? P.L_tope : (isFinite(Lreq) ? Math.ceil(Lreq / 0.9 / 5) * 5 : Lav);   // largo: el mayor entre aplastamiento y soldadura, con FU objetivo 0,90
      push({ id, grp, nombre, n, t, tResp, allow, capas: capas || 1, F: Fst, L, Lreq, adm, uh: false });
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
    const pick = (c) => P.t_ss > 0 ? [P.t_ss, P.t_ss] : [commercial(SS_COMM, Math.max(c.treq, tS)), commercial(SS_COMM, Math.max(c.treq2, tS))];   // [disco de la base (liso), disco de la mesa (ranurado)]
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
        tuhTope = P.a_sup + stopAInf(P) + Math.max(P.hc_min, Fs * 1e3 / (P.p_uhmw * Lav * 0.9));
      }
      tuh = P.t_uhmw > 0 ? P.t_uhmw : commercial(UH_COMM, Math.max(tuhReq, tuhTope));
      EcU = uc.Ec(tuh); SU = uc.S(tuh);
    }
    return { o, tss: t1, tss2: t2, tssReq: c.treq, tss2Req: c.treq2, tTope: tS, tuhTope, gr, tFlex: c.tFlex, q, qAvg: c.L.q_avg, a, sad, A_ss, tuh, tuhReq, tuhConf, EcU, SU,
      delta: t1 + t2 + tuh, mTop: RHO_SS * A_ss * t2, mUH: o === 2 ? RHO_UH * A_ss * tuh : 0, mSS: RHO_SS * A_ss * (t1 + t2), mBz: 0, tbz: 0 };
  }
  // Opción C: placa de bronce con tapones de grafito, fija a la base, contra un disco duro rotatorio (configuraciones 1 y 3, esta con pastillas
  // que cubren la fracción bz_cover) o contra una 2.ª placa de bronce de aleación distinta (configuración 2).
  //   Bronce: σ = 3·q_loc·a²/(4·t²)/η ≤ 0,6·Fy_bz, η = (p − d)/p (ligamento entre tapones)  →  t_req = t_flex/√η + sobreespesor, ≥ mínimo constructivo.
  function ifaceDesignBz(P) {
    const conf = Math.min(3, Math.max(1, Math.round(P.bz_conf))), a = P.ss_void / 2;
    const A_ss = Math.PI * ((P.D_top / 2) ** 2 - riOf(P) ** 2);
    const cov = conf === 3 ? Math.min(1, Math.max(0.05, P.bz_cover)) : 1;
    const eta = (P.bz_plug_p - P.bz_plug_d) / P.bz_plug_p, fg = Math.PI * P.bz_plug_d ** 2 / (2 * Math.sqrt(3) * P.bz_plug_p ** 2);
    const rBz = P.rho_bz * 1e-6;
    const mPlate = (t) => A_ss * cov * t * (rBz * (1 - PLUG_DEPTH * fg) + RHO_GR * PLUG_DEPTH * fg);   // placa con tapones (parte cubierta)
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
    const pickC = (c) => P.t_cara > 0 ? P.t_cara : commercial(conf === 2 ? BZ_COMM : SS_COMM, Math.max(c.treqC, tS));
    const pickB = (c) => P.t_bz > 0 ? P.t_bz : commercial(BZ_COMM, Math.max(c.treqB, tS));
    let c = calc(0, 0), tB = pickB(c), tC = pickC(c);
    for (let i = 0; i < 4; i++) { c = calc(rot(tC), tB + tC); const nb = pickB(c), nc = pickC(c); if (nb === tB && nc === tC) break; tB = nb; tC = nc; }
    return { o: 3, conf, cov, eta, fg, a, A_ss, tTope: tS, q: c.L.q_max, qAvg: c.L.q_avg, qLoc: c.qLoc, qC: c.qC, gr: P.h_gr, fgr: grooveFrac(P).f, qNet: c.qLoc / (1 - fg - grooveFrac(P).f), tss2: tC, tss2Req: c.treqC,
      tbz: tB, tbzReq: c.treqB, tFlexB: c.tfB, tss: tC, tssReq: c.treqC, tFlex: c.tfC, sad: 0.6 * P.Fy_bz, sadC: 0.6 * FyC, FyC,
      tuh: 0, tuhReq: 0, tuhConf: 0, delta: tB + tC, mTop: rot(tC), mUH: 0,
      mSS: conf === 2 ? 0 : RHO_SS * A_ss * tC, mBz: conf === 2 ? mPlate(tB) + mSolid(tC) : mPlate(tB) };
  }

  // Masas sin las barras de los topes (estas dependen del par de calado y se suman en compute(), que es la fuente de m.total)
  function massesBase(P) {
    const ifc = ifaceDesign(P), m = massesMesa(P, ifc.delta);
    m.ssTop = ifc.mTop; m.ss = ifc.mSS; m.uhmw = ifc.mUH; m.bz = ifc.mBz;   // pieza rotatoria, discos inoxidables o duros, lámina UHMW y bronce
    m.base = RHO * (P.B * P.B - Math.PI / 4 * P.D_piv ** 2) * P.t_base + (P.h_boss > 0 ? RHO * Math.PI / 4 * (P.D_boss ** 2 - P.D_piv ** 2) * P.h_boss : 0)   // + collar de asiento del pivote
      + 4 * RHO * (2 * P.R_ear * (P.h_ear - 0) + Math.PI * P.R_ear ** 2 / 2 - Math.PI / 4 * P.d_ear ** 2) * P.t_ear;   // + 4 orejas de izaje
    m.rim = RHO * (4 * P.B - 4 * P.rim_t) * P.rim_h * P.rim_t;
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
    m.pivot = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + ifc.delta + P.h_disc - P.t_top + 3);
    m.cyl = P.n_cyl * P.m_cyl;
    m.stopBars = 0;                                                      // barras de los topes soldados: las completa compute()
    m.total = m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.pivot + m.cyl;
    return m;
  }
  const masses = (P) => compute(P).m;                                   // con las barras de los topes dentro de m.total
  function bracketGeo(P) {
    const Win = P.D_body + 20;                                          // luz interior entre mejillas (cilindro coaxial con la guía)
    const H = hAxis(P) + P.b_eye / 2 + P.g_ch + P.t_ch;                 // alto hasta cara superior de la oreja superior
    const spacer = Math.max(0, hAxis(P) - P.b_eye / 2 - P.g_ch - P.t_ch); // suplemento bajo la oreja inferior
    // saliente trasera: desgarro por corte de la oreja superior (2 planos) con F/2 a calado, BTH-1 Fy/(Nd·√3)
    const Fs = Math.PI / 4 * P.D_bore ** 2 * P.p_relief / 10;           // N
    const aReq = (Fs / 2) / (2 * P.t_ch * P.Fy / (P.Nd * Math.sqrt(3)));
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
  function guideGeo(P) {
    const pitch = 2 * Math.PI / P.N_pin, R = P.R_pin, a_min = R * Math.cos(pitch / 2);
    const front = P.l_p + 20 + P.f_ext;                                  // pasador del vástago → cara delantera del patín (cubre la uña)
    const rear = 1.25 * P.d_pp;                                          // pasador del vástago → cara trasera del patín
    const L_s = front + rear, Lg = 2 / 3 * L_s;                          // brazo entre reacciones de guía (presión lineal)
    const chord = 2 * R * Math.sin(pitch / 2);
    const y_pin0 = -R * Math.sin(pitch / 2), y_rp0 = y_pin0 - P.l_p - P.s_free, y_rp1 = y_pin0 + chord - P.l_p;
    const y_eye = y_rp0 - P.L0;
    const Y_bed = Math.max(Math.abs(y_rp0 - rear), Math.abs(y_rp1 + front)) + 10;
    const zc0 = hAxis(P) + P.t_base;                                      // eje del cilindro (absoluto)
    // boca del alojamiento: se adelanta desde la cara del patín hasta 10 mm de los pasadores, entre los anillos de la mesa
    const mouthX = Math.min(P.x_g - P.w_s / 2, R + P.d_pin / 2 + 10), inset = P.x_g - P.w_s / 2 - mouthX;
    const lever = mouthX - a_min;                                        // voladizo de la uña: boca → centro del pasador
    // retorno: la uña se desliza radialmente hacia afuera (resorte) hasta despejar el pasador siguiente
    const tipX = a_min - P.c_tip, travel = R + P.d_pin / 2 + 5 - tipX;
    const pocketEnd = mouthX + P.L_in + travel + P.s_sp;                // fondo del alojamiento (uña retraída + resorte)
    const shoeTop = Math.max(zc0 + forkH(P) / 2, zc0 + P.dog_h / 2 + 1 + P.t_pk);   // cara superior del patín (horquilla o tapa del alojamiento)
    return { shoeTop, pitch, a_min, front, rear, L_s, Lg, chord, y_pin0, y_rp0, y_rp1, y_eye, L_bed: 2 * Y_bed, Y_bed, zc0, lever, mouthX, inset, tipX, travel, pocketEnd };
  }
  function kinematics(P) {
    const g = guideGeo(P), R = P.R_pin, n = 60;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const th = -g.pitch / 2 + g.pitch * i / n, arm = R * Math.cos(th);
      pts.push({ th, s: P.s_free + R * (Math.sin(th) - Math.sin(-g.pitch / 2)), arm, Delta: P.x_g - arm });
    }
    const s_req = P.s_free + g.chord;
    return Object.assign({ ok: true, pts, s_req, margin: P.stroke - s_req, armMin: g.a_min, armMax: R, gap: g.chord - P.d_pin,
      radial: R - g.a_min, DeltaMax: P.x_g - g.a_min }, g);
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
    const K = kinematics(P);
    const A = Math.PI / 4 * P.D_bore ** 2, Aann = A - Math.PI / 4 * P.d_rod ** 2;
    const Fstall = A * P.p_relief / 10 / 1e3, Falarm = A * P.p_alarm / 10 / 1e3, Fret = Aann * P.p_ret / 10 / 1e3;
    const torque = (mu, r) => mu * N * r / 1e3 + T_piv(mu);                                   // kN·m
    // Equilibrio del patín en planta (cara plana de la uña): en la posición θ el pasador recibe F_pas (normal a la cara, en y)
    // y la fricción H = s·μ_s·F_pas en x. El pasador gira con la mesa: el punto de contacto (a, y_p − r) se mueve en x con
    // velocidad ω·(r − y_p), de modo que s = signo(y_p − r) (la fricción cambia de sentido en y_p = r; ahí se evalúan ambos).
    // Mesa: x_c·F_pas − y_c·H = T/n.  Patín: R_f = [F_pas·Δ + H·(y_c − y_r)]/Lg; R_r = H − R_f;
    // cilindro: F_cil·η = F_pas + μg(|R_f| + |R_r|).  Se toma el máximo en la carrera (y ambos signos en θ = 0).
    const yMid = (K.front - K.rear) / 2;                 // centro del patín respecto del pasador del vástago
    function drive(th, s) {                               // por unidad de F_pas
      const xc = P.R_pin * Math.cos(th), yc = P.R_pin * Math.sin(th) - P.d_pin / 2;
      const yrp = P.R_pin * Math.sin(th) - P.l_p, yr = yrp + yMid - K.Lg / 2;
      const h = s * P.mu_s, rf = ((P.x_g - xc) + h * (yc - yr)) / K.Lg, rr = h - rf;
      return { th, s, xc, yc, h, rf, rr, den: xc - h * yc, fr: 1 + P.mu_g * (Math.abs(rf) + Math.abs(rr)) };
    }
    const dpts = [], thX = Math.asin(Math.min(1, P.d_pin / 2 / P.R_pin));
    K.pts.forEach((q) => dpts.push(drive(q.th, P.R_pin * Math.sin(q.th) >= P.d_pin / 2 ? 1 : -1)));
    if (thX < K.pitch / 2) { dpts.push(drive(thX, -1)); dpts.push(drive(thX, 1)); }
    dpts.sort((a, b) => a.th - b.th || a.s - b.s);
    const atPt = (d, T) => { const Fp = T * 1e3 / P.n_cyl / d.den; return { Fp, H: d.h * Fp, Rf: d.rf * Fp, Rr: d.rr * Fp, F: Fp * d.fr / P.eta_c }; };
    const Fcyl = (T, armmm) => {                          // kN; sin brazo: máximo en la carrera
      if (armmm) { const th = Math.acos(Math.min(1, armmm / P.R_pin)), sg = (t) => (P.R_pin * Math.sin(t) >= P.d_pin / 2 ? 1 : -1); return Math.max(atPt(drive(-th, sg(-th)), T).F, atPt(drive(th, sg(th)), T).F); }
      return Math.max(...dpts.map((d) => atPt(d, T).F));
    };
    const Kg = (arm) => Fcyl(1, arm) * P.n_cyl * (arm || K.armMin) / 1e3;   // factor equivalente F_cil·n·a/T
    // a calado (mesa detenida, la fricción de guía puede ser nula): F_pas = η·F_calado; reacciones de guía y fricción radial máximas
    const stall = dpts.map((d) => { const Fp = Fstall * P.eta_c; return { Fp, H: Math.abs(d.h) * Fp, R: Math.max(Math.abs(d.rf), Math.abs(d.rr)) * Fp, Rsum: (Math.abs(d.rf) + Math.abs(d.rr)) * Fp }; });
    const stallMax = { Fp: Math.max(...stall.map((x) => x.Fp)), H: Math.max(...stall.map((x) => x.H)), R: Math.max(...stall.map((x) => x.R)), Rsum: Math.max(...stall.map((x) => x.Rsum)) };
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
    const curve = K.ok ? K.pts.map((q) => ({ s: q.s, arm: q.arm, F: cd ? Fcyl(cd.T, q.arm) : 0 })) : [];
    const stroke = K.ok && cd ? dpts.map((d) => Object.assign({ th: d.th, s: P.s_free + P.R_pin * (Math.sin(d.th) + Math.sin(K.pitch / 2)) }, atPt(d, cd.T))) : [];
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
      Rguide: stallMax.R, ePiv: ePivEff(P) };
    // barras de los topes soldados: dependen del par de calado, así que se dimensionan aquí y suman a m.total (no están en ninguna otra pieza).
    // Las barras de la mesa giran y cargan la interfaz, pero no se realimentan a N (< 0,01 %; evita la dependencia circular con el par de calado).
    ifc.topes = stopsOf(P, res);
    m.stopBars = ifc.topes.reduce((s, t) => s + t.m_barras, 0);
    m.total += m.stopBars;
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
    const qOwn = (R.m.base + R.m.rim + R.m.brackets + R.m.shoes + R.m.beds) * G / (P.B * P.B);   // peso propio repartido sobre la base
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

  /* ---------------- Verificaciones ---------------- */
  // kind: "fu" (FU = dem/cap), "geo" (FU con criterio geométrico), "info" (no afecta el veredicto), "pend" (pendiente de dato)
  function verifs(P, R, fea) {
    const out = [];
    const add = (o) => out.push(Object.assign({ kind: "fu" }, o, { fu: o.kind === "info" || o.kind === "pend" ? null : (o.fu != null ? o.fu : ((o.cap > 0 && o.dem >= 0) ? o.dem / o.cap : Infinity)) }));   // capacidad ≤ 0 o demanda negativa: no cumple
    const K = R.K, Nd = P.Nd, Fy = P.Fy;
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
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Carrera requerida con margen", formula: "s_libre + ΔL(paso) + margen ≤ carrera", dem: K.ok ? K.s_req + P.s_margin : NaN, cap: P.stroke, unit: "mm", ref: "Cinemática (rev. C3)" });
    const bgv = bracketGeo(P), Bh = P.B / 2 - P.rim_t - 5, zBed = P.t_base + P.t_bed;
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
    // Verificaciones geométricas y de la barra comunes a todos los topes
    const stopCommon = (s) => {
      const { grp, pieza: nombre, t, allow, L, F } = s, g = stopGeo(P, t);
      add({ grp, sys: "est", kind: "geo", name: nombre + ": altura de contacto efectiva del tope sobre el canto del sector", formula: "h_c,mín ≤ h_c = t − a_sup − a_inf (t = " + t + "; barra h = t − a_sup; espesor mínimo del sector " + tStopMin(P) + " mm)", dem: P.hc_min, cap: g.hC, unit: "mm", ref: "Criterio del proyecto (geometría del tope; tolerancia de corte del canto)" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": barra del tope bajo la superficie de deslizamiento al final de la vida", formula: "a_sup ≥ 1 mm + sobreespesor de desgaste y relapeado (" + allow.toFixed(2).replace(".", ",") + " mm)", dem: 1 + allow, cap: P.a_sup, unit: "mm", ref: "Criterio del proyecto (la barra no debe rozar la pieza contraria)" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": alivio inferior del canto libra el filete del tope", formula: "a_inf ≥ w_tope + 1 mm (chaflán 45° en el canto del sector sobre el triángulo del filete)", dem: P.w_tope + 1, cap: aInf, unit: "mm", ref: "AWS D1.1/D1.1M:2020 (perfil del filete de cateto w); geometría" });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": filete del tope dentro de la altura de barra", formula: "w_tope + h_c,mín ≤ h_barra = t − a_sup (el cateto vertical del filete debe caber bajo el contacto)", dem: P.w_tope + P.hc_min, cap: g.hB, unit: "mm", ref: REFW });
      add({ grp, sys: "est", kind: "geo", name: nombre + ": filete mínimo del tope según la parte más gruesa", formula: "w_mín(T = máx(b_tope; t_respaldo) = " + s.Tw + ") ≤ w_tope", dem: s.w_min, cap: P.w_tope, unit: "mm", ref: REFW });
      add({ grp, sys: "est", name: nombre + ": flexión de la barra del tope en la raíz (voladizo de altura z)", formula: "σ = 6·F·z/(L·b²) ≤ Fy/Nd; z = a_inf + h_c/2", dem: 6 * F * 1e3 * g.z / (L * P.b_tope ** 2), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3 (flexión, Fy/Nd)" });
      add({ grp, sys: "est", kind: "info", name: nombre + ": masa de las barras del tope (incluida en la masa total, m.stopBars)", formula: "m = capas·n·ρ·L·b_tope·h_barra, una barra por sector y capa", dem: s.m_barras, cap: s.m_barra, unit: "kg / kg por barra", ref: "Geometría (suma a m.total desde la 2.ª pasada; antes no se contaban)" });
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
    const handRow = (grp, nombre, mass, n) => add({ grp, sys: "est", kind: "geo", name: nombre + ": masa del sector (manipulación manual al desmontar)", formula: "m_sector = m_pieza/n ≤ 25 kg", dem: mass / n, cap: 25, unit: "kg", ref: "ISO 11228-1 (carga manual)" });
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
        add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Sectores de disco: crecimiento por dilatación de la cuerda (dejar una junta en frío ≥ 1 mm, biselar bordes)", formula: "j = (α_inox − α_acero)·ΔT·cuerda del sector", dem: (AL_SS - AL_S) * P.dT * chord, unit: "mm", ref: "Termoelasticidad" });
        handRow("Interfaz inox", "Disco inoxidable", RHO_SS * I.A_ss * Math.max(I.tss, I.tss2), P.n_sec);
        add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Soldar los topes antes del alivio de tensiones y del rectificado de las caras; el sector entra por el borde de la mesa izada y se asegura con los tornillos de posición", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      } else {
        const Ttot = R.Tmax, TretF = P.mu_back * R.N * R.r_u / 1e3, TretA = P.tau_bond * R.Ac * R.r_u / 1e6, Tret = Math.max(TretF, TretA);
        add({ grp: "Interfaz inox", sys: "giro", name: "Retención de los discos sobre su plancha de respaldo (la mayor entre fricción y pegado; no se suman)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A·r_u). Un adhesivo rígido falla con deslizamientos de centésimas de mm: la fricción no se moviliza a tiempo", dem: Ttot, cap: Tret, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        if (P.tau_bond > 0) {
          const eps = (AL_SS - AL_S) * P.dT, tb2 = eps * Math.sqrt(P.G_ad * E_SS * Math.max(I.tss, I.tss2) / P.t_ad);
          add({ grp: "Interfaz inox", sys: "est", name: "Adhesivo: cortante térmico en el borde del disco (dilatación diferencial)", formula: "τ_borde = ε·√(G_ad·E_inox·t_disco/t_adhesivo), ε = (α_inox − α_acero)·ΔT ≤ τ_adm,cíclico", dem: tb2, cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
        }
        const sth = E_SS * (AL_SS - AL_S) * P.dT;
        add({ grp: "Interfaz inox", sys: "est", name: "Dilatación diferencial inox–acero: tensión si el disco quedara restringido", formula: "σ = E_inox·(α_inox − α_acero)·ΔT ≤ 0,6·Fy_inox", dem: sth, cap: I.sad, unit: "MPa", ref: "Termoelasticidad; α inox 17,3 y acero 11,7 (×10⁻⁶/K)" });
        add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Fijación permanente (pegado): los discos NO son desmontables sin destruir la unión; no admite limpieza ni cambio", formula: "Alternativa: fijación desmontable por sectores (fix_mode = 1)", dem: 0, unit: "–", ref: "Requisito de mantenimiento del mandante" });
      }
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Dilatación diferencial radial del disco respecto de su respaldo", formula: "Δr = (α_inox − α_acero)·ΔT·R", dem: (AL_SS - AL_S) * P.dT * R.Ro, unit: "mm", ref: "Termoelasticidad" });
      if (I.o === 1) groovesRows("Interfaz inox", "disco de la mesa");
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Altura que agrega la interfaz sobre la plancha base", formula: I.o === 2 ? "Δ = t_disco base + t_disco mesa + t_UHMW" : "Δ = t_disco base + t_disco mesa", dem: I.delta, unit: "mm", ref: "Geometría (eje de los cilindros sube Δ)" });
      if (I.o === 1) add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Opción A: par inox–inox con riesgo de gripado si la película de grasa se expulsa: exigir aleaciones o durezas distintas (≥ 50 HB de diferencia) o recubrimiento", formula: "Sin verificación numérica (ASTM G98)", dem: 0, unit: "–", ref: "ASTM G98; decisión del proyectista" });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Masa agregada por la interfaz (discos inoxidables + lámina UHMW)", formula: "m = ρ·A·t", dem: R.m.ss + R.m.uhmw, unit: "kg", ref: "Geometría" });
    }
    if (I.o === 2) {
      const REFU = "Proveedor de UHMW-PE (datos de catálogo, ASTM D4020); confirmar con ensayo";
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: presión de contacto máxima frente a la admisible sostenida", formula: "q_máx ≤ p_adm,UHMW", dem: I.q, cap: P.p_uhmw, unit: "MPa", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "Lámina UHMW: espesor adoptado frente al requerido", formula: "t ≥ máx(E_ap·δ_planitud/(p_adm − q_máx); t_mín constructivo)", dem: I.tuhReq, cap: I.tuh, unit: "mm", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: espesor por conformidad de planitud (con módulo confinado) / comercial adoptado", formula: "t_conf = E_c(S)·δ/(p_adm − q_máx); E_c = E[1 + (M/E − 1)S²/(1 + S²)], S = D/(4t), M = E(1−ν)/((1+ν)(1−2ν)), ν = 0,45", dem: I.tuhConf, cap: I.tuh, unit: "mm", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: factor de forma y módulo confinado en el espesor adoptado", formula: "S = D/(4t); E_c(S)", dem: I.SU, cap: I.EcU, unit: "– / MPa", ref: REFU });
      const Fdrag = Math.max(R.mu.d, R.mu.cont, R.mu.dry) * R.N;                     // kN, arrastre de la lámina con el μ máximo
      const dist = P.life * P.turns_yr * 2 * Math.PI * P.r_ef / 1000;              // m deslizados en la vida
      const wear = P.k_wear * 1e-7 * I.q * dist;                                   // mm de desgaste de la cara de la lámina en la vida
      if (removable) {
        const sU = topeOf("uhmw"), Fs = sU.F, gU = stopGeo(P, I.tuh), sigU = gU.hC > 0 ? Fs * 1e3 / (Lav * gU.hC) : Infinity;
        add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW (" + P.n_seg + " sectores): aplastamiento del canto contra el tope del rebaje", formula: "σ = F_sector/(L_canto·h_c) ≤ p_adm,UHMW; h_c = t − a_sup − a_inf; F_sector = μ_máx·N/n·(q_máx/q_med)", dem: sigU, cap: P.p_uhmw, unit: "MPa", ref: REFU });
        add({ grp: "Interfaz inox", sys: "est", name: "Tope del rebaje del sector UHMW: soldadura al disco de la base (2 filetes, corte + par de excentricidad)", formula: "f = √[(F/(2aL))² + (F·z/(b·a·L))²] ≤ 0,60FEXX/(1,20Nd); z = a_inf + h_c/2", dem: weldStop(P, Fs, Lav, gU.z), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4; AISC 360-22 J2.4 (resultante); hallazgo T2" });
        stopCommon(sU);                                                  // el tope del rebaje se suelda al disco de la base
        add({ grp: "Interfaz inox", sys: "est", kind: "geo", name: "Lámina UHMW: masa del sector (manipulación manual)", formula: "m_sector = m_UHMW/n ≤ 25 kg", dem: R.m.uhmw / P.n_seg, cap: 25, unit: "kg", ref: "ISO 11228-1 (carga manual)" });
      } else add({ grp: "Interfaz inox", sys: "est", kind: "pend", name: "Opción B: retención de los sectores de UHMW contra el arrastre por fricción (rebaje perimetral o cola de milano en el disco de la base)", formula: "arrastre ≈ μ_máx·N (los pernos no bastan: aplastamiento del UHMW)", dem: Fdrag, unit: "kN", ref: "Equilibrio con el μ máximo; decisión del proyectista" });
      const vcyl = P.Q_pump * 1e6 / 60 / (P.n_cyl * R.A);                          // mm/s, velocidad del vástago
      const vmax = R.Ro / R.K.armMin * vcyl / 1000;                                 // m/s en el borde de la mesa durante la carrera
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: valor PV en el borde de la mesa (durante la carrera)", formula: "PV = q_máx·v; v = R·v_cil/a_mín, v_cil = Q/(n·A)", dem: I.q * vmax, cap: P.PV_uh, unit: "MPa·m/s", ref: REFU });
      add({ grp: "Interfaz inox", sys: "est", name: "Lámina UHMW: desgaste en la vida de diseño frente al 20 % del espesor", formula: "h = k·q_máx·s ≤ 0,20·t; s = vida·vueltas/año·2π·r_ef", dem: wear, cap: 0.2 * I.tuh, unit: "mm", ref: REFU });
      const gap = (AL_UH - AL_S) * P.dT * 2 * R.Ro * Math.sin(Math.PI / P.n_seg);
      add({ grp: "Interfaz inox", sys: "est", kind: "info", name: "Lámina UHMW: crecimiento radial del sector (fijar al centro con agujeros ranurados)", formula: "Δr = (α_UHMW − α_acero)·ΔT·R", dem: (AL_UH - AL_S) * P.dT * R.Ro, unit: "mm", ref: REFU });
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
        add({ grp: G3, sys: "est", kind: "info", name: "Sectores de bronce: crecimiento por dilatación de la cuerda (dejar una junta en frío ≥ 1 mm, biselar bordes, sellar)", formula: "j = (α_bz − α_acero)·ΔT·cuerda del sector", dem: (AL_BZ - AL_S) * P.dT * chordB, unit: "mm", ref: "Termoelasticidad" });
        add({ grp: G3, sys: "est", kind: "info", name: (conf === 2 ? "Sectores de la 2.ª placa" : "Sectores del disco duro") + ": crecimiento por dilatación de la cuerda (junta en frío ≥ 1 mm)", formula: "j = (α − α_acero)·ΔT·cuerda del sector", dem: ((conf === 2 ? AL_BZ : AL_SS) - AL_S) * P.dT * chordC, unit: "mm", ref: "Termoelasticidad" });
        const mBzPlate = R.m.bz - (conf === 2 ? R.ifc.mTop : 0);
        handRow(G3, "Placa de bronce con grafito", mBzPlate, nB);
        handRow(G3, conf === 2 ? "2.ª placa de bronce" : "Disco duro", conf === 2 ? R.ifc.mTop : R.m.ss, P.n_sec);
        add({ grp: G3, sys: "est", kind: "pend", name: "Soldar los topes antes del alivio de tensiones y del rectificado; sectores atornillados con tornillos de posición, sacables con la mesa izada", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      } else {
        // retención: la placa de bronce fija a la base (la menor área pegada es la de las pastillas)
        const TretF = P.mu_back * R.N * R.r_u / 1e3, TretA = P.tau_bond * R.Ac * I.cov * R.r_u / 1e6, Tret = Math.max(TretF, TretA);
        add({ grp: G3, sys: "giro", name: "Retención de la placa de bronce sobre la base (la mayor entre fricción y pegado; no se suman)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A_pegada·r_u)", dem: R.Tmax, cap: Tret, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        if (P.tau_bond > 0) {
          const tb1 = (AL_BZ - AL_S) * P.dT * Math.sqrt(P.G_ad * E_BZ * I.tbz / P.t_ad);
          add({ grp: G3, sys: "est", name: "Adhesivo de la placa de bronce: cortante térmico en el borde", formula: "τ = ε·√(G_ad·E_bz·t/t_adhesivo), ε = (α_bz − α_acero)·ΔT ≤ τ_adm,cíclico", dem: tb1, cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
          const epsC = ((conf === 2 ? AL_BZ : AL_SS) - AL_S) * P.dT, EC = conf === 2 ? E_BZ : E_SS;
          add({ grp: G3, sys: "est", name: conf === 2 ? "Adhesivo de la 2.ª placa de bronce: cortante térmico en el borde" : "Adhesivo del disco duro: cortante térmico en el borde", formula: "τ = ε·√(G_ad·E·t/t_adhesivo) ≤ τ_adm,cíclico", dem: epsC * Math.sqrt(P.G_ad * EC * I.tss / P.t_ad), cap: P.tau_cyc, unit: "MPa", ref: "Línea de pegado elástica (corte); criterio del proyecto" });
        }
        add({ grp: G3, sys: "est", name: "Dilatación diferencial bronce–acero: tensión si la placa quedara restringida", formula: "σ = E_bz·(α_bz − α_acero)·ΔT ≤ 0,6·Fy_bz", dem: E_BZ * (AL_BZ - AL_S) * P.dT, cap: I.sad, unit: "MPa", ref: "Termoelasticidad; α bronce 18, acero 11,7 (×10⁻⁶/K)" });
        if (conf === 2) add({ grp: G3, sys: "est", name: "Dilatación diferencial bronce–acero de la 2.ª placa: tensión si quedara restringida", formula: "σ = E_bz·(α_bz − α_acero)·ΔT ≤ 0,6·Fy_bz2", dem: E_BZ * (AL_BZ - AL_S) * P.dT, cap: I.sadC, unit: "MPa", ref: "Termoelasticidad" });
        const TretR = Math.max(P.mu_back * R.N * R.r_u / 1e3, P.tau_bond * R.Ac * R.r_u / 1e6);
        add({ grp: G3, sys: "giro", name: conf === 2 ? "Retención de la 2.ª placa de bronce sobre la mesa (la mayor entre fricción y pegado)" : "Retención del disco duro sobre la mesa (la mayor entre fricción y pegado)", formula: "T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A·r_u)", dem: R.Tmax, cap: TretR, unit: "kN·m", ref: "Equilibrio; respaldo granallado sin pintura; adhesivo epóxico estructural" });
        add({ grp: G3, sys: "est", kind: "pend", name: "Fijación permanente (pegado): la placa y el disco NO son desmontables sin destruir la unión; no admite limpieza ni cambio", formula: "Alternativa: fijación desmontable por sectores (fix_mode = 1)", dem: 0, unit: "–", ref: "Requisito de mantenimiento del mandante" });
      }
      groovesRows(G3, "placa de bronce");
      add({ grp: G3, sys: "est", kind: "info", name: "Dilatación diferencial radial de la placa respecto de su respaldo (fijar al centro con agujeros ranurados)", formula: "Δr = (α_bz − α_acero)·ΔT·R", dem: (AL_BZ - AL_S) * P.dT * R.Ro, unit: "mm", ref: "Termoelasticidad" });
      if (conf === 3) add({ grp: G3, sys: "est", kind: "info", name: "Pastillas de bronce: crecimiento por dilatación de la cuerda de la pastilla (dejar una junta en frío ≥ 1 mm, biselar bordes, sellar)", formula: "j = (α_bz − α_acero)·ΔT·cuerda de la pastilla", dem: (AL_BZ - AL_S) * P.dT * 2 * R.Ro * Math.sin(Math.PI / P.bz_npad), unit: "mm", ref: "Termoelasticidad" });
      add({ grp: G3, sys: "est", kind: "info", name: "Altura que agrega la interfaz sobre la plancha base", formula: "Δ = t_bronce + t_disco (o 2.ª placa)", dem: I.delta, unit: "mm", ref: "Geometría (el eje de los cilindros sube Δ)" });
      add({ grp: G3, sys: "est", kind: "info", name: "Masa agregada por la interfaz (bronce con grafito + disco duro o 2.ª placa)", formula: "m = ρ·A·t (bronce descontando los tapones, más el grafito)", dem: R.m.ss + R.m.bz, unit: "kg", ref: "Geometría" });
      add({ grp: G3, sys: "est", kind: "pend", name: "Arranque con adherencia–deslizamiento (stick-slip) a 2,5 mm/s: diferencia entre μ estático y cinético", formula: "Sin verificación numérica; ensayo de arranque tras reposo bajo carga", dem: 0, unit: "–", ref: "Ensayo del proveedor" });
      add({ grp: G3, sys: "est", kind: "pend", name: "Par galvánico bronce–acero en contacto con grasa: sellado perimetral y protección del respaldo", formula: "Sin verificación numérica", dem: 0, unit: "–", ref: "Decisión del proyectista" });
      if (conf === 2) add({ grp: G3, sys: "est", kind: "pend", name: "Bronce contra bronce (aleaciones distintas): riesgo de gripado; el grafito va solo en una placa", formula: "Sin verificación numérica (ASTM G98)", dem: 0, unit: "–", ref: "ASTM G98; decisión del proyectista" });
      if (conf === 3 && !removable) add({ grp: G3, sys: "est", kind: "pend", name: "Retención de las pastillas de bronce: alojamientos soldados o pegado; la mesa apoya solo en las pastillas", formula: "Arrastre ≈ μ_máx·N", dem: Math.max(R.mu.d, R.mu.cont, R.mu.dry) * R.N, unit: "kN", ref: "Equilibrio; decisión del proyectista" });
    }

    /* --- Cubierta de madera dura y altura de skidding --- */
    const Htop = P.t_base + R.ifc.delta + P.h_disc + (P.opt_wood > 0.5 ? P.t_wood : 0);
    if (P.opt_wood > 0.5) {
      const RLw = P.D_load / 2, Aw = Math.PI * (RLw * RLw - ((P.D_piv + 80) / 2) ** 2), qTopW = P.phi_d * R.W * 1e3 / (P.f_apoyo * Aw) * (1 + 4 * P.e / RLw);
      add({ grp: "Cubierta", sys: "est", name: "Madera: aplastamiento perpendicular a la fibra bajo la carga (área de contacto efectiva)", formula: "q = φd·W/(f_apoyo·A_círculo)·(1 + 4e/R_carga) ≤ p_adm,madera (sin acreditar reparto sobre la plancha)", dem: qTopW, cap: P.p_wood, unit: "MPa", ref: "Madera dura (datos de proveedor); criterio conservador" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: la ley lineal de presiones no admite tracción (q mín ≥ 0)", formula: "4e/R_carga ≤ 1 (e ≤ D_carga/8)", dem: 4 * P.e / RLw, cap: 1, unit: "–", ref: "Estática del apoyo" });
      add({ grp: "Cubierta", sys: "est", kind: "geo", name: "Madera: espesor mínimo (desgaste y fijación)", formula: "t_madera ≥ 30 mm", dem: 30, cap: P.t_wood, unit: "mm", ref: "Práctica constructiva" });
      add({ grp: "Cubierta", sys: "est", kind: "info", name: "Masa de la cubierta de madera (gira con la mesa y carga la interfaz)", formula: "m = ρ·A·t", dem: R.m.wood, unit: "kg", ref: "Geometría" });
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
    add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo almas/nervios–planchas", formula: "w_mín(T = " + Tw + ") ≤ w ≤ t_alma", dem: wMin(Tw), cap: Math.min(P.w_web, Math.min(P.t_web, P.t_rib)), unit: "mm", ref: "AWS D1.1/D1.1M:2020, tamaño mínimo de filete" });
    add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo mejillas–base", formula: "w_mín(T = " + Tb + ") ≤ w ≤ t_mín", dem: wMin(Tb), cap: Math.min(P.w_br, Math.min(P.t_base, P.t_ch)), unit: "mm", ref: "AWS D1.1/D1.1M:2020, tamaño mínimo de filete" });

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
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento pasador–uña", formula: "σ = F/(d·h_uña) ≤ 1,25·Fy_mín/Nd", dem: Fs * 1e3 / (P.d_pin * P.dog_h), cap: 1.25 * Math.min(P.Fy_pin, P.Fy_dog) / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });

    /* --- Uña (cara de empuje plana, templada) --- */
    const Adog = P.dog_b * P.dog_h, Hs = P.mu_s * Fs;                  // fricción radial máxima en la cara (a calado)
    const lev = K.lever + P.e_dog, Sdog = P.dog_h * P.dog_b ** 2 / 6;
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
    const App = Math.PI * P.d_pp ** 2 / 4, Spp = Math.PI * P.d_pp ** 3 / 32;
    const Mpp = Fs / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) / 1e3;
    add({ grp: "Articulaciones", sys: "est", name: "Pasador: flexión (horquilla)", formula: "M = F/2·(t/2 + g + b/4); σ ≤ Fy/Nd", dem: Mpp * 1e6 / Spp, cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / 3-2.3" });
    add({ grp: "Articulaciones", sys: "est", name: "Pasador: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 * 1e3 / App, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: "Articulaciones", sys: "est", name: "Aplastamiento en mejillas", formula: "σ = (F/2)/(d·t) ≤ 1,25Fy/Nd", dem: Fs / 2 * 1e3 / (P.d_pp * P.t_ch), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    const bgx = bracketGeo(P), aSh = bgx.rear - P.d_pp / 2;
    add({ grp: "Articulaciones", sys: "est", name: "Oreja superior de la ménsula: desgarro por corte tras el agujero", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = saliente − d/2", dem: Fs / 2 * 1e3 / (2 * P.t_ch * aSh), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (simplificado, 2 planos de corte)" });
    add({ grp: "Articulaciones", sys: "est", kind: "info", name: "Ojal comercial del cilindro: admitir pasador y carga", formula: "Ø ojal ≥ d_pp; ancho = b_ojal (confirmar con ficha)", dem: P.d_pp, unit: "mm", ref: "Ficha del fabricante" });
    const hax = R.hax;
    const Mch = Fs / 2 * hax / 1e3;
    add({ grp: "Articulaciones", sys: "est", name: "Mejilla de la ménsula: flexión en la base", formula: "σ = (F/2)·h_eje/(t·L²/6) ≤ Fy/Nd", dem: Mch * 1e6 / (P.t_ch * P.L_ch ** 2 / 6), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    const aw = 0.707 * P.w_br;
    const fV = Fs * 1e3 / (4 * aw * P.L_ch), fM = Fs * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6);
    add({ grp: "Articulaciones", sys: "est", name: "Soldadura mejillas–base (4 filetes)", formula: "f = √(fV² + fM²) ≤ 0,60FEXX/(1,20Nd)", dem: Math.hypot(fV, fM), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4" });

    /* --- Pivote --- */
    const Hasym = R.Fstall * P.eta_c * Math.max(...[-1, 1].map((e) => Math.abs(1 / asymF(P, P.mu_g - 0.05, e) - 1 / asymF(P, P.mu_g + 0.05, e))));
    // Con un número impar de cilindros el empuje no es un par puro: la fuerza tangencial sobre el pasador (F_pas) no se equilibra y el pivote
    // reacciona con una fuerza igual. Diseño para la presión del buje y calado para la flexión del pivote (cadena BTH-1).
    const rs = Math.hypot(1, P.mu_s);                                                              // resultante de F_pas y la fricción H = μ_s·F_pas de la cara
    const odd = P.n_cyl % 2 === 1, HcilD = odd ? Math.max(...R.stroke.map((q) => q.Fp)) * rs : 0, HcilS = odd ? R.stallMax.Fp * rs : 0;
    const H = Math.max(R.H_ecc(R.mu.d), P.Ch * R.N) + Hasym + HcilD, Hf = Math.max(R.H_ecc(R.mu.d), P.Ch * R.N) + Hasym + HcilS;
    if (odd) add({ grp: "Pivote", sys: "est", kind: "info", name: "Reacción del pivote por empuje no equilibrado (n° impar de cilindros): F_pas de diseño / de calado", formula: "H_cil = F_pas·√(1 + μ_s²) (el par no es puro con 1 o 3 cilindros; el n° 3 se trata como un cilindro: geometría no definida)", dem: HcilD, cap: HcilS, unit: "kN", ref: "Equilibrio de la mesa" });
    add({ grp: "Pivote", sys: "est", kind: "info", name: "Empuje neto al pivote por fricción desigual de los patines (μg ± 0,05)", formula: "H_asim = F_calado·η·|1/f(μg−0,05) − 1/f(μg+0,05)|", dem: Hasym, unit: "kN", ref: "Equilibrio (revisión independiente H10)" });
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
      add({ grp: "Pivote", sys: "est", name: "Soldadura del collar a la base (filete perimetral): V_c y M_c del asiento rígido-lineal", formula: "f = √(f_b² + f_v²) ≤ 0,60FEXX/(1,2·Nd); f_b = M_c/(π·D²/4·a), f_v = V_c/(π·D·a), a = 0,707·w_collar; V_c = H/L·[h + k(h − h²/L)], M_c = H/L·[(1 + k)h²/2 − k·h³/(3L)], k = 6(e + L/2)/L (V_c ≈ 1,85·H)", dem: Math.hypot(fbC, fvC), cap: Fw, unit: "MPa", ref: "AWS D1.1 / AISC 360-22 J2.4 (grupo circular, método elástico; resultante vectorial de corte y flexión)" });
      add({ grp: "Pivote", sys: "est", kind: "info", name: "Carga del collar sobre su filete: V_c y M_c (respecto de la cara superior de la base)", formula: "V_c y M_c de la distribución rígido-lineal del asiento; la plancha base toma la reacción de signo contrario", dem: Vc / 1e3, cap: Mc / 1e6, unit: "kN / kN·m", ref: "Equilibrio del collar" });
      const wallE = Math.min(wallC, P.h_boss);
      add({ grp: "Pivote", sys: "est", kind: "geo", name: "Collar: filete mínimo según la parte más gruesa (pared del collar o plancha base)", formula: "w_mín(T = máx(pared del collar = " + wallC + "; t_base = " + P.t_base + ")) ≤ w_collar; no más que la parte más delgada", dem: Math.min(wMin(Math.max(wallC, P.t_base)), Math.min(wallC, P.t_base)), cap: P.w_collar, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 5.8; AISC 360-22 Tabla J2.4" });
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
      add({ grp: "Orejas de izaje", sys: "est", kind: "geo", name: "Oreja: filete mínimo según la parte más gruesa (oreja o plancha base)", formula: "w_mín(T = máx(t_oreja; t_base) = " + Math.max(P.t_ear, P.t_base) + ") ≤ w_oreja; no más que la parte más delgada", dem: Math.min(wMin(Math.max(P.t_ear, P.t_base)), Math.min(P.t_ear, P.t_base)), cap: P.w_ear, unit: "mm", ref: "AWS D1.1/D1.1M:2020 Tabla 5.8; AISC 360-22 Tabla J2.4" });
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
    fat("Uña (boca del patín)", Fd * 1e3 * lev / Sdog, "A", nCyc);
    fat("Pasadores de articulación", Fd / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) * 1e3 / Spp, "A", nCyc);
    fat("Pie de soldadura mejilla–base", Fd / 2 * 1e3 * hax / (P.t_ch * P.L_ch ** 2 / 6), "E", nCyc);
    fat("Garganta soldadura mejilla–base (corte)", Math.hypot(Fd * 1e3 / (4 * aw * P.L_ch), Fd * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6)), "F", nCyc);

    out.forEach((c) => {
      if (c.kind === "info") c.st = "info";
      else if (c.kind === "pend") c.st = "pend";
      else if (!isFinite(c.fu)) c.st = "fail";
      else if (c.kind === "geo" || c.sys === "giro") c.st = c.fu <= 1 ? "ok" : "fail";   // límites con margen propio
      else c.st = c.fu <= 0.9 ? "ok" : c.fu <= 1 ? "warn" : "fail";
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
      fea = { top: discCached(P, R, "top", opts), bot: discCached(P, R, "bot", opts), glob: globalBending(P, R), lift: runLift(P, R, opts.coarse) };
    }
    const checks = verifs(P, R, fea);
    const bad = (sys) => checks.filter((c) => c.sys === sys && c.st === "fail");
    const warn = (sys) => checks.filter((c) => c.sys === sys && c.st === "warn");
    const verdict = {
      gira: R.K.ok && bad("giro").length === 0,
      estructura: bad("est").length === 0,
      warnGiro: warn("giro").length, warnEst: warn("est").length,
      pend: checks.filter((c) => c.st === "pend").length,
      fuMax: Math.max(0, ...checks.filter((c) => c.fu != null && isFinite(c.fu) && c.kind === "fu").map((c) => c.fu)),
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

  return { riOf, hubGeo, capacityW, capacityByCyl, market, MARKET, prIn, pinClear, bracketGeo, guideGeo, forkH, PARAM_GROUPS, defaults, parseRings, masses, kinematics, compute, discModel, runDisc, globalBending, runLift, verifs, analyze, FSR, FAT_CAT, hAxis, G, PSI_CAT, chamferGeo };
})();
if (typeof module !== "undefined") module.exports = TT;
