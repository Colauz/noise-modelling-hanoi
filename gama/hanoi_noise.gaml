/**
 * ============================================================================
 *  HANOI URBAN NOISE - simulation agent-based
 *  Center for Environmental Intelligence, VinUniversity
 * ============================================================================
 *
 *  Ce que la simulation montre
 *  ---------------------------
 *  Une carte de bruit urbain qui varie selon l'HEURE de la journée et selon un
 *  scénario de VOLUME DE TRAFIC, avec des véhicules mobiles dont la composition
 *  (motos / voitures / poids lourds) est mesurée sur nos propres vidéos.
 *
 *  Statut scientifique de chaque couche  (important : tout n'a pas le même statut)
 *  --------------------------------------------------------------------------
 *  1. NIVEAU DE FOND (cellules colorées) - PRÉDIT
 *     Depuis la V2 (août 2026), le modèle livré est un NOYAU PHYSIQUE À TROIS PARAMÈTRES,
 *     et non plus un LightGBM. Chaque classe de voirie est traitée comme une source
 *     LINÉIQUE incohérente : l'intensité décroît en 1/d (et non en 1/d², qui vaudrait
 *     pour une source ponctuelle).
 *
 *         E(x) = A_hw / max(d_hw, D0)  +  A_res / max(d_res, D0)  +  B
 *         L(x) = 10 * log10( E(x) )
 *
 *     d_hw  = distance au grand axe le plus proche (motorway/trunk/primary/secondary)
 *     d_res = distance à la petite rue la plus proche (tertiary/residential/...)
 *     Coefficients ajustés sur nos 363 mesures, contraints positifs, lisibles dans
 *     outputs/gama_inputs/physical_params.csv. Une valeur par heure, 5h-21h.
 *
 *     PERFORMANCE RÉELLE (run du 5 août 2026, outputs/models/metrics.json, produit par
 *     scripts/evaluate_models.py : n = 363, 17 blocs, IC 95 % bootstrap) — R² :
 *
 *         modèle                          block-CV 600 m   BUFFERED LOO   leave-one-site-out
 *                                                          (référence)
 *         table site x heure                    -0.008        -0.419            -0.058
 *         régression sur log(dist_road)          0.221         0.200             0.189
 *         noyau physique (CE MODÈLE)             0.255         0.246             0.222
 *         LightGBM v1 (6 features)               0.304         0.137             0.029
 *         LightGBM v2 (8 features)               0.332         0.099            -0.035
 *         hybride physique + ML sur résidu       0.395         0.123             0.035
 *
 *     >>> LIRE CE TABLEAU AVANT D'INTERPRÉTER LA CARTE. Le classement s'INVERSE presque
 *     exactement entre la première colonne (protocole permissif) et les deux suivantes
 *     (protocoles qui testent la généralisation). Nous avons construit l'architecture
 *     hybride que nous recommandions nous-mêmes : elle domine sous block-CV et PERD sous
 *     les deux protocoles stricts (ΔR² -0.123 et -0.187 face au noyau physique seul).
 *     C'est pourquoi la carte affichée ici est produite par la PHYSIQUE SEULE : le
 *     LightGBM de résidu est entraîné et sauvegardé, mais NON appliqué. Le choix est fait
 *     par le code (evaluate_models.py, drapeau `apply_residual`), pas à la main.
 *
 *     Conséquence pratique : les contrastes spatiaux affichés sont pilotés par la distance
 *     aux deux classes de voirie, et rien d'autre. La morphologie agrégée à 300 m
 *     n'apportait aucun gain mesurable. Voir paper/sections/negative_results.md §5.z.
 *
 *     Le R² 0.45 affiché jusqu'en juillet 2026 venait d'une CV groupée sur des cellules de
 *     110 m, plus petites que le rayon de 300 m des features : il fuyait et surestimait la
 *     performance. Il ne doit plus être cité.
 *
 *     C'est un niveau de type L_eq : une moyenne, pas un instantané. Il est calibré en
 *     RELATIF (contrastes entre lieux et entre heures), pas en absolu : nos capteurs sont
 *     des smartphones non certifiés — voir paper/sections/metrology.md.
 *
 *  2. TRAFIC (véhicules) - MESURÉ
 *     147 vidéos horodatées, appariées à nos mesures de bruit (écart médian 15 s),
 *     agrégées par site et par heure. Les heures non filmées sont interpolées et
 *     signalées comme telles par l'indicateur "Trafic à cette heure".
 *
 *     DEUX GRANDEURS, À NE PAS CONFONDRE (v2, août 2026) :
 *       - DENSITÉ (véh/image) : ce que voyait la v1, obtenu par détection image par
 *         image. Pilote le NOMBRE d'agents Vehicle affichés.
 *       - DÉBIT (véh/min) : franchissements d'une ligne virtuelle au centre de
 *         l'image, obtenus par SUIVI d'objets (YOLOv8 + ByteTrack). C'est la
 *         grandeur qui gouverne physiquement l'émission sonore, et c'est celle
 *         qu'affichent les moniteurs "Débit mesuré" et "dont motos".
 *     Les deux divergent exactement là où ça compte : en congestion la densité est
 *     maximale et le débit s'effondre. C'est la raison pour laquelle la v1 ne
 *     trouvait aucun lien entre trafic et niveau sonore.
 *
 *  3. VÉHICULES - VISUELS, PAS SONORES  (résultat de calibration)
 *     Les véhicules affichés représentent le parc mesuré (nombre et composition),
 *     mais n'ajoutent PAS de bruit dans le calcul. Raison : nous avons tenté de
 *     calibrer une émission par catégorie sur nos propres données
 *     (scripts/calibrate_emissions.py, régression en énergie sous contrainte de
 *     non-négativité sur les 147 vidéos appariées). Les trois coefficients sont
 *     ressortis NULS : à site donné, le nombre de véhicules visibles n'explique pas
 *     le niveau mesuré (R² 0.008 à 0.044 selon le site ; corrélations de signe
 *     incohérent : Hoan Kiem -0.09, Ocean Park -0.19, Vinh Tuy +0.21, et -0.15 sur
 *     les 147 vidéos appariées). Causes probables : les véhicules garés sont comptés, la distance
 *     de chaque véhicule est ignorée, et la vitesse - qui domine le bruit de
 *     roulement - n'est pas observable sur un comptage. Plutôt que d'injecter des
 *     valeurs inventées, on s'abstient : le niveau reste piloté par le modèle validé
 *     et par la loi de volume de trafic.
 *
 *  3bis. CHANTIERS - CALIBRÉS SUR NOS MESURES
 *     Nos 32 points « chantier à proximité » (distance médiane mesurée : 56 m du
 *     chantier) sont +2,0 dB au-dessus des 152 autres points d'Ocean Park. Converti
 *     en énergie, cela correspond à une source équivalente de 64,7 dB à 56 m (médianes). La
 *     simulation ajoute cette énergie avec l'atténuation géométrique
 *     L(d) = 64,7 − 20·log10(d / 56), en somme ÉNERGÉTIQUE avec le fond.
 *
 *  4. SCÉNARIO DE TRAFIC (slider) - LOI PHYSIQUE, APPLIQUÉE À LA SEULE PART TRAFIC
 *     Multiplier le débit par k décale de 10·log10(k) la part d'énergie ATTRIBUABLE AU
 *     TRAFIC : doubler le trafic = +3 dB là où le trafic domine, quasiment rien dans une
 *     cour intérieure. Chaque cellule est décomposée en
 *           E_cellule = E_résiduel + E_trafic,
 *     E_résiduel étant estimé par le 5e percentile des niveaux prédits de la zone à cette
 *     heure (les cellules les plus calmes = celles où le trafic contribue le moins).
 *     Idem pour la mitigation : la « zone 30 » retire 3 dB à la SOURCE, et seulement dans
 *     un rayon de 150 m d'une route.
 *     CORRECTION D'AOÛT 2026 : auparavant, 10·log10(k) et le -3 dB étaient ajoutés
 *     UNIFORMÉMENT à toutes les cellules, ce qui est physiquement faux et surestimait
 *     l'effet des scénarios loin des voiries.
 *     Invariant : à k = 1 sans mitigation, la carte est identique à la carte prédite.
 *
 *  Seuils réglementaires affichés : QCVN 26:2010/BTNMT (Vietnam, zone ordinaire),
 *  70 dB de 6h à 21h · 55 dB de 21h à 6h. La recommandation OMS 53 dB a été retirée :
 *  c'est un L_den (moyenne annuelle, pénalités soir/nuit), non comparable à notre
 *  grandeur — voir paper/sections/metrology.md.
 *
 *  Entrées : générées par `python3 scripts/export_gama_zones.py`
 * ============================================================================
 */
model hanoi_noise

global {
    // ---------------- zone d'étude ----------------
    // Les 3 sites sont distants de ~10 km : on cadre sur un site à la fois.
    // Changer la zone puis relancer l'expérimentation.
    string zone <- "oceanpark" among: ["oceanpark", "hoankiem", "vinhtuy"];

    file roads_file     <- file('../outputs/gama_inputs/' + zone + '_roads.shp');
    file buildings_file <- file('../outputs/gama_inputs/' + zone + '_buildings.shp');
    file noise_shp      <- file('../outputs/gama_inputs/' + zone + '_noise.shp');
    file fleet_csv      <- csv_file('../outputs/gama_inputs/fleet_by_hour.csv', true);
    string phys_path    <- '../outputs/gama_inputs/physical_params.csv';
    string constr_path  <- '../outputs/gama_inputs/' + zone + '_construction.shp';
    string meas_path    <- '../outputs/gama_inputs/' + zone + '_measurements.shp';

    // Enveloppe du monde. INDISPENSABLE : sans elle GAMA crée un monde 100x100 m,
    // les agents tombent hors de l'index spatial et closest_to / at_distance
    // renvoient nil (bug silencieux : les véhicules n'affectent plus rien).
    geometry shape <- envelope(noise_shp);

    // ---------------- paramètres de scénario ----------------
    int   hour_of_day        <- 17 min: 5 max: 21;
    float traffic_multiplier <- 1.0 min: 0.2 max: 3.0;
    // Scénarios de mitigation (Phase 4) :
    //   "zone 30"       -> vitesse réduite 50->30 km/h : -3 dB (fourchette littérature -2 a -4)
    //   "pietonnisation"-> trafic ramené a 20% : -7 dB via 10*log10(0.2)
    string mitigation        <- "aucune" among: ["aucune", "zone 30", "pietonnisation"];
    // Chantiers : horaires d'activité (scénario "horaires étendus" = allonger la plage)
    bool  construction_on    <- true;
    int   work_start         <- 7  min: 5 max: 12;
    int   work_end           <- 17 min: 13 max: 21;
    bool  show_vehicles      <- true;
    bool  show_measures      <- false;  // nos points de mesure terrain

    // ---------------- constantes ----------------
    int   HMIN <- 5;
    int   HMAX <- 21;
    // Seuils affichés. Les deux sont des seuils VIETNAMIENS, portant sur la même grandeur
    // que la nôtre (un niveau, pas un indicateur long terme). La référence OMS 53 dB a été
    // RETIRÉE : c'est un L_den, moyenne ANNUELLE avec pénalités soir/nuit, non comparable à
    // un niveau horaire prédit depuis des échantillons de 25 s (paper/sections/metrology.md).
    float qcvn_day   <- 70.0;  // QCVN 26:2010/BTNMT, zone ordinaire, 6h-21h
    float qcvn_night <- 55.0;  // QCVN 26:2010/BTNMT, zone ordinaire, 21h-6h
    int   veh_density_scale <- 22;   // véhicules affichés par unité de "véhicules/image"

    // Décomposition fond / trafic (voir la correction physique dans `reflex scenario`).
    float AMBIENT_PCT   <- 0.05;  // percentile bas pris comme ambiance résiduelle non routière
    float MITIG_RADIUS  <- 150.0; // portée d'une mesure de mitigation autour d'une route (m)
    float Z30_DB        <- -3.0;  // zone 30 : -3 dB à la SOURCE (littérature -2 à -4)

    // ---------------- noyau physique ajusté (v2, août 2026) ----------------
    // Coefficients lus dans outputs/gama_inputs/physical_params.csv, produits par
    // scripts/evaluate_models.py. Modèle de source LINÉIQUE : E = A/d (et non A/d²).
    //     E_trafic(cellule) = A_HW / max(d_hw, D0) + A_RES / max(d_res, D0)
    // On ne s'en sert PAS pour recalculer le niveau (la grille prédite le porte déjà),
    // mais pour savoir COMMENT l'énergie de trafic d'une cellule se répartit entre
    // grands axes et petites rues. C'est ce qui permet de cibler une mitigation :
    // une « zone 30 » agit sur les rues locales, pas sur la nationale voisine.
    float A_HW  <- 0.0;
    float A_RES <- 0.0;
    float B_BG  <- 0.0;
    float PHYS_D0 <- 5.0;
    bool  phys_ok <- false;

    // Chantiers : source équivalente calibrée sur NOS mesures.
    float L_CONSTR_REF <- 64.7;   // source équivalente à D_CONSTR_REF (calcul sur médianes)
    float D_CONSTR_REF <- 56.0;   // distance de référence, médiane observée (m)
    float D_MIN        <- 25.0;   // plancher = 1er quartile des distances observees (32 m)
    float CONSTR_RADIUS <- 250.0; // au-delà, contribution négligeable

    // ---------------- indicateurs ----------------
    float mean_dB     <- 0.0;
    float exceed_qcvn <- 0.0;
    float exceed_night <- 0.0;   // % de la zone au-dessus du seuil QCVN NUIT (55 dB)
    float ambient_dB   <- 0.0;   // ambiance résiduelle non routière de la zone, à cette heure
    float peak_dB     <- 0.0;
    int   n_vehicles  <- 0;
    float flow_now      <- 0.0;   // débit total à l'heure courante (véh/min), scénario inclus
    float flow_moto_now <- 0.0;   // dont motos
    string traffic_source <- "-";
    string zone_label <- "-";
    float  mitigation_dB <- 0.0;
    float  eff_traffic <- 1.0;
    bool   constr_active <- false;
    int    n_constr <- 0;
    float  constr_zone_dB <- 0.0;   // niveau moyen a moins de 200 m d'un chantier

    // profils de trafic par heure (lus depuis fleet_by_hour.csv)
    // DEUX grandeurs distinctes, à ne pas confondre :
    //   fleet_total     DENSITÉ  - véhicules visibles par image. Pilote le NOMBRE
    //                              d'agents Vehicle affichés (ce qu'on voit à l'écran).
    //   fleet_flow      DÉBIT    - franchissements de ligne par minute (suivi ByteTrack).
    //                              C'est la grandeur qui gouverne l'ÉMISSION acoustique.
    // En congestion les deux divergent : densité maximale, débit effondré.
    map<int, float> fleet_total  <- [];
    map<int, float> fleet_moto   <- [];
    map<int, float> fleet_car    <- [];
    map<int, int>   fleet_meas   <- [];
    map<int, float> fleet_flow      <- [];
    map<int, float> fleet_moto_flow <- [];

    init {
        zone_label <- (zone = "oceanpark") ? "Ocean Park (nouveau tissu urbain)"
            : ((zone = "hoankiem") ? "Hoan Kiem (vieux quartier)" : "Vinh Tuy (corridor de transport)");
        string site_key <- (zone = "oceanpark") ? "Ocean Park"
            : ((zone = "hoankiem") ? "Hoan Kiem lake" : "Vinh Tuy area");

        create Road from: roads_file;
        create Building from: buildings_file;
        create NoisePoint from: noise_shp with: [d_hw::float(read("d_hw")),
                                                 d_res::float(read("d_res"))] {
            loop h from: HMIN to: HMAX {
                db_by_hour << float(read("h" + string(h)));
            }
        }

        // coefficients du noyau physique (une seule ligne de données)
        if (file_exists(phys_path)) {
            matrix pm <- matrix(csv_file(phys_path, true));
            A_HW    <- float(pm[0, 0]);
            A_RES   <- float(pm[1, 0]);
            B_BG    <- float(pm[2, 0]);
            PHYS_D0 <- float(pm[3, 0]);
            phys_ok <- (A_HW + A_RES) > 0;
        }
        // Part d'énergie de trafic attribuable aux GRANDS AXES, cellule par cellule.
        // Si les coefficients manquent, on retombe sur 50/50 : la mitigation reste
        // applicable, simplement sans ciblage par classe de voirie.
        ask NoisePoint {
            if (phys_ok) {
                float e_hw  <- A_HW  / max([d_hw,  PHYS_D0]);
                float e_res <- A_RES / max([d_res, PHYS_D0]);
                share_hw <- (e_hw + e_res) > 0 ? e_hw / (e_hw + e_res) : 0.5;
            } else {
                share_hw <- 0.5;
            }
        }

        // profil de trafic horaire du site
        // colonnes : 0 site_name · 1 hour · 2 total · 3 measured · 4 n_videos
        //            5 moto_share · 6 car_share · 7 bus_share · 8 truck_share
        //            9 total_flow_per_min · 10 moto_flow_per_min · 11 car_flow_per_min
        //            12 bus_flow_per_min · 13 truck_flow_per_min      (v2, colonnes ajoutées
        //            EN FIN de fichier : les indices 0-8 ci-dessus restent valides)
        matrix fl <- matrix(fleet_csv);
        loop i from: 0 to: fl.rows - 1 {
            if (string(fl[0, i]) = site_key) {
                int h <- int(fl[1, i]);
                fleet_total[h] <- float(fl[2, i]);
                fleet_meas[h]  <- int(fl[3, i]);
                fleet_moto[h]  <- float(fl[5, i]);
                fleet_car[h]   <- float(fl[6, i]);
                if (fl.columns > 10) {
                    fleet_flow[h]      <- float(fl[9, i]);
                    fleet_moto_flow[h] <- float(fl[10, i]);
                }
            }
        }

        if (file_exists(constr_path)) {
            create ConstructionSite from: file(constr_path) with: [loud::int(read("loud"))];
        }
        n_constr <- length(ConstructionSite);
        if (file_exists(meas_path)) {
            create Measure from: file(meas_path) with: [dB::float(read("dB")), m_hour::int(read("hour"))];
        }

        // Distance de chaque cellule à la route la plus proche : figée ici une fois pour
        // toutes, elle sert à borner spatialement les scénarios de mitigation (une zone 30
        // n'a aucun effet sur une cour intérieure située à 300 m de toute rue).
        ask NoisePoint {
            Road r <- Road closest_to self;
            d_road <- (r = nil) ? 1e6 : (self distance_to r);
        }

        write "Zone " + zone_label + " : " + string(length(NoisePoint)) + " cellules, "
            + string(length(Road)) + " routes, " + string(length(Building)) + " batiments, "
            + string(n_constr) + " chantiers, " + string(length(Measure)) + " mesures terrain.";
        do sync_fleet;
    }

    // ---- ajuste le parc au (heure x facteur de trafic) courant ----
    action sync_fleet {
        float base  <- (fleet_total[hour_of_day] = nil) ? 0.0 : fleet_total[hour_of_day];
        int target  <- int(base * eff_traffic * veh_density_scale);
        float mshare <- (fleet_moto[hour_of_day] = nil) ? 0.5 : fleet_moto[hour_of_day];
        float cshare <- (fleet_car[hour_of_day] = nil) ? 0.4 : fleet_car[hour_of_day];

        int diff <- target - length(Vehicle);
        if (diff > 0) {
            create Vehicle number: diff {
                my_road <- one_of(Road);
                pts <- copy(my_road.shape.points);
                idx <- 0;
                location <- first(pts);
                float d <- rnd(1.0);
                // vitesses differenciees pour le rendu ; aucune emission sonore associee
                // (non identifiable sur nos donnees, cf. en-tete point 3)
                if (d < mshare)               { v_type <- "moto";  speed <- 9.0; }
                else if (d < mshare + cshare) { v_type <- "car";   speed <- 11.0; }
                else                          { v_type <- "heavy"; speed <- 8.0; }
            }
        } else if (diff < 0) {
            ask (-diff) among Vehicle { do die; }
        }
        n_vehicles <- length(Vehicle);
        traffic_source <- (fleet_meas[hour_of_day] = 1) ? "mesure (videos)" : "interpole";
        // débit mesuré à cette heure, mis à l'échelle du scénario : c'est la grandeur
        // à citer quand on parle d'intensité de trafic, pas le nombre d'agents affichés.
        flow_now      <- (fleet_flow[hour_of_day] = nil) ? 0.0
                            : fleet_flow[hour_of_day] * eff_traffic;
        flow_moto_now <- (fleet_moto_flow[hour_of_day] = nil) ? 0.0
                            : fleet_moto_flow[hour_of_day] * eff_traffic;
    }

    // ---- plancher ambiant NON ROUTIER de la zone à l'heure courante ----
    // Percentile bas des niveaux prédits : les cellules les plus calmes de la zone sont
    // celles où le trafic contribue le moins. On s'en sert comme estimation de l'ambiance
    // résiduelle (ventilation, activités, avifaune, bruit lointain), qu'un scénario de
    // trafic ne doit PAS faire bouger.
    action compute_ambient {
        list<float> lv <- (NoisePoint collect each.base_dB) sort_by each;
        int i <- max([0, min([length(lv) - 1, int(length(lv) * AMBIENT_PCT)])]);
        ambient_dB <- empty(lv) ? 0.0 : lv[i];
    }

    reflex scenario {
        eff_traffic   <- (mitigation = "pietonnisation")
                            ? traffic_multiplier * 0.2 : traffic_multiplier;
        constr_active <- construction_on and hour_of_day >= work_start and hour_of_day <= work_end;

        do sync_fleet;

        // Niveau de fond prédit pour l'heure, AVANT scénario.
        ask NoisePoint { base_dB <- db_by_hour[hour_of_day - HMIN]; }
        do compute_ambient;
        float e_amb_zone <- 10 ^ (ambient_dB / 10);

        // ------------------------------------------------------------------------------
        //  CORRECTION PHYSIQUE (août 2026) — décomposition énergétique fond / trafic
        // ------------------------------------------------------------------------------
        //  AVANT : background_dB <- base_dB + 10*log10(k) + mitigation_dB, appliqué
        //  UNIFORMÉMENT à toutes les cellules. Physiquement faux : 10*log10(k) ne vaut que
        //  pour la part d'énergie ATTRIBUABLE AU TRAFIC. Tripler le trafic ajoutait +4,8 dB
        //  jusque dans les cours intérieures, où le trafic ne contribue quasiment pas ; et
        //  la « zone 30 » retirait 3 dB à des cellules qu'aucune rue ne dessert.
        //
        //  MAINTENANT : chaque cellule est décomposée en
        //        E_cellule = E_résiduel + E_trafic
        //  avec E_résiduel = min(E_ambiant_zone, E_cellule)  (jamais plus que la cellule).
        //  Seul E_trafic subit le facteur de volume et la mitigation.
        //
        //  Invariant vérifiable : à k = 1 sans mitigation, background_dB == base_dB
        //  exactement pour toutes les cellules — la carte de référence est inchangée.
        //
        //  La mitigation « zone 30 » (-3 dB sur la source, fourchette littérature -2 à -4)
        //  est en outre bornée à MITIG_RADIUS autour d'une route : au-delà, une réduction
        //  de vitesse n'a pas de sens physique.
        // ------------------------------------------------------------------------------
        //  RAFFINEMENT v2 (août 2026) — LA MITIGATION CIBLE UNE CLASSE DE VOIRIE
        //  L'énergie de trafic d'une cellule est elle-même scindée en deux, selon le
        //  noyau physique ajusté (A_HW/d_hw contre A_RES/d_res) :
        //        E_trafic = E_grands_axes + E_petites_rues
        //  Une « zone 30 » est une mesure de police sur la voirie LOCALE : elle ne
        //  s'applique donc qu'à E_petites_rues. L'appliquer aussi aux grands axes,
        //  comme le faisait la v1, créditait le scénario d'une baisse sur des cellules
        //  dont le bruit vient d'une nationale que la mesure ne touche pas.
        //  Idem pour la piétonnisation : on ferme des rues, pas une voie rapide.
        //  Invariant conservé : à k = 1 sans mitigation, background_dB == base_dB.
        //  NB : on repart de `traffic_multiplier` et non de `eff_traffic`, qui porte déjà
        //  le facteur 0.2 de la piétonnisation — l'appliquer deux fois doublerait l'effet.
        //  `eff_traffic` reste utilisé par sync_fleet pour le NOMBRE de véhicules affichés.
        float f_z30 <- 10 ^ (Z30_DB / 10);             // -3 dB -> facteur d'énergie ~0.50

        ask NoisePoint {
            float e_tot     <- 10 ^ (base_dB / 10);
            float e_res     <- min([e_amb_zone, e_tot]);
            float e_traffic <- e_tot - e_res;
            float e_hw_part  <- e_traffic * share_hw;
            float e_res_part <- e_traffic * (1 - share_hw);
            float f_hw   <- traffic_multiplier;   // le volume s'applique aux deux classes
            float f_loc  <- traffic_multiplier;
            if (mitigation = "zone 30" and d_res <= MITIG_RADIUS) { f_loc <- f_loc * f_z30; }
            if (mitigation = "pietonnisation")                    { f_loc <- f_loc * 0.2; }
            background_dB <- 10 * log(e_res + f_hw * e_hw_part + f_loc * e_res_part) / log(10);
            constr_energy <- 0.0;
        }
        // Décalage EFFECTIF moyen sur la zone (remplace l'ancien -3 dB affiché en dur).
        // Il est désormais toujours plus faible en valeur absolue que le décalage "source",
        // puisque les cellules dominées par l'ambiance résiduelle bougent peu : c'est
        // exactement ce que l'ancienne formule uniforme surestimait.
        mitigation_dB <- mean(NoisePoint collect (each.background_dB - each.base_dB));
    }

    // chantiers actifs : énergie ajoutée, atténuation géométrique depuis la source
    reflex construction_noise when: constr_active {
        ask ConstructionSite {
            list<NoisePoint> around <- NoisePoint at_distance CONSTR_RADIUS;
            loop c over: around {
                float d <- max([D_MIN, location distance_to c.location]);
                float lvl <- L_CONSTR_REF - 20 * log(d / D_CONSTR_REF) / log(10);
                c.constr_energy <- c.constr_energy + (10 ^ (lvl / 10));
            }
        }
    }

    reflex indicators {
        // somme ÉNERGÉTIQUE : fond (contient déjà le trafic moyen) + chantiers
        ask NoisePoint {
            float e <- (10 ^ (background_dB / 10)) + constr_energy;
            effective_dB <- 10 * log(e) / log(10);
        }
        mean_dB     <- mean(NoisePoint collect each.effective_dB);
        peak_dB     <- max(NoisePoint collect each.effective_dB);
        exceed_qcvn <- (NoisePoint count (each.effective_dB > qcvn_day)) / length(NoisePoint) * 100;
        exceed_night <- (NoisePoint count (each.effective_dB > qcvn_night)) / length(NoisePoint) * 100;
        // effet local des chantiers : la moyenne de zone le masque (4 sites / plusieurs
        // milliers de cellules), on suit donc le voisinage immediat des chantiers.
        if (n_constr > 0) {
            list<NoisePoint> near_c <- NoisePoint where
                ((ConstructionSite closest_to each) != nil and
                 (each.location distance_to (ConstructionSite closest_to each).location) < 200.0);
            constr_zone_dB <- empty(near_c) ? 0.0 : mean(near_c collect each.effective_dB);
        }
    }
}

// ============================================================================
species Road {
    aspect default { draw shape color: rgb(155, 155, 155) width: 1; }
}

species Building {
    aspect default { draw shape color: rgb(232, 232, 232) border: rgb(205, 205, 205); }
}

species NoisePoint {
    list<float> db_by_hour;
    float base_dB       <- 55.0;  // niveau prédit pour l'heure courante, AVANT scénario
    float d_road        <- 0.0;   // distance à la route la plus proche (m), figée à l'init
    float d_hw          <- 2000.0; // distance au grand axe le plus proche (m), depuis le shp
    float d_res         <- 2000.0; // distance à la petite rue la plus proche (m)
    float share_hw      <- 0.5;   // part de l'énergie de trafic venant des grands axes
    float background_dB <- 55.0;
    float constr_energy <- 0.0;   // énergie apportée par les chantiers actifs
    float effective_dB <- 55.0;

    // Palette de carte de bruit : bandes de 5 dB, vert -> rouge sombre.
    // La bascule orange/rouge est calée sur le seuil QCVN jour (70 dB).
    aspect default {
        rgb col <- rgb(126, 20, 40);
        if (effective_dB < 50)      { col <- rgb(26, 152, 80); }
        else if (effective_dB < 55) { col <- rgb(102, 189, 99); }
        else if (effective_dB < 60) { col <- rgb(166, 217, 106); }
        else if (effective_dB < 65) { col <- rgb(254, 224, 82); }
        else if (effective_dB < 70) { col <- rgb(253, 174, 60); }
        else if (effective_dB < 75) { col <- rgb(230, 90, 45); }
        else if (effective_dB < 80) { col <- rgb(190, 35, 35); }
        draw square(40) color: col;
    }
}

species ConstructionSite {
    int loud <- 0;
    aspect default {
        rgb col <- (loud = 1) ? rgb(150, 30, 30) : rgb(190, 120, 40);
        // losange = chantier ; plein quand actif a cette heure
        draw square(70) rotate: 45 color: constr_active ? col : rgb(215, 215, 215)
             border: rgb(60, 60, 60);
    }
}

species Measure {
    float dB <- 60.0;
    int m_hour <- 12;
    aspect default {
        if (show_measures) {
            rgb col <- rgb(40, 40, 40);
            if (dB >= 75)      { col <- rgb(150, 20, 30); }
            else if (dB >= 70) { col <- rgb(220, 70, 40); }
            else if (dB >= 65) { col <- rgb(245, 160, 50); }
            else if (dB >= 60) { col <- rgb(250, 215, 70); }
            else               { col <- rgb(60, 170, 90); }
            draw circle(22) color: col border: rgb(20, 20, 20);
        }
    }
}

species Vehicle skills: [moving] {
    string v_type <- "moto";
    Road my_road;
    list<point> pts;
    int idx <- 0;

    // Déplacement le long des sommets de la polyligne de la route puis passage à une
    // route voisine. On n'utilise pas `goto ... on: graph` : le réseau OSM exporté est
    // fragmenté (peu de nœuds partagés), le pathfinding échoue et les agents restent figés.
    action pick_road {
        list<Road> nearby <- Road at_distance 30.0;
        my_road <- empty(nearby) ? one_of(Road) : one_of(nearby);
        if (my_road != nil) {
            pts <- copy(my_road.shape.points);
            if (length(pts) > 1 and (location distance_to last(pts)) < (location distance_to first(pts))) {
                pts <- reverse(pts);
            }
            idx <- 0;
        }
    }

    reflex drive {
        if (my_road = nil or idx >= length(pts)) { do pick_road; }
        else {
            do goto target: pts[idx] speed: speed;
            if (location distance_to pts[idx] < 4.0) { idx <- idx + 1; }
        }
    }

    aspect default {
        if (show_vehicles) {
            if (v_type = "moto")     { draw circle(16) color: rgb(255, 140, 0) border: #black; }
            else if (v_type = "car") { draw circle(20) color: rgb(20, 90, 190) border: #black; }
            else                     { draw circle(27) color: rgb(95, 35, 130) border: #black; }
        }
    }
}

// ============================================================================
experiment hanoi_noise_sim type: gui {
    parameter "Zone d'étude (relancer après changement)" var: zone category: "1 · Zone";
    parameter "Heure de la journée" var: hour_of_day category: "2 · Scénario";
    parameter "Facteur de trafic (1.0 = observé)" var: traffic_multiplier category: "2 · Scénario";
    parameter "Mitigation" var: mitigation category: "2 · Scénario";
    parameter "Chantiers actifs" var: construction_on category: "2 · Scénario";
    parameter "Chantier : début" var: work_start category: "2 · Scénario";
    parameter "Chantier : fin (horaires étendus)" var: work_end category: "2 · Scénario";
    parameter "Afficher les véhicules" var: show_vehicles category: "3 · Affichage";
    parameter "Afficher nos points de mesure" var: show_measures category: "3 · Affichage";

    output {
        display "Carte de bruit" type: opengl background: rgb(250, 250, 248) {
            species NoisePoint aspect: default;
            species Building aspect: default;
            species Road aspect: default;
            species ConstructionSite aspect: default;
            species Vehicle aspect: default;
            species Measure aspect: default;

            overlay position: {10 #px, 10 #px} size: {275 #px, 300 #px}
                    background: rgb(255, 255, 255) transparency: 0.12 {
                draw "HANOI URBAN NOISE" at: {14 #px, 24 #px} color: rgb(20, 20, 20)
                     font: font("Helvetica", 13, #bold);
                draw zone_label at: {14 #px, 42 #px} color: rgb(80, 80, 80)
                     font: font("Helvetica", 10, #plain);
                draw string(hour_of_day) + "h00   ·   trafic x" + string(traffic_multiplier with_precision 1)
                     at: {14 #px, 62 #px} color: rgb(20, 20, 20) font: font("Helvetica", 12, #bold);

                draw "NIVEAU PREDIT  L (dB)" at: {14 #px, 88 #px} color: rgb(20, 20, 20)
                     font: font("Helvetica", 9, #bold);
                draw "= < 50" at: {14 #px, 106 #px} color: rgb(26, 152, 80) font: font("Helvetica", 10, #bold);
                draw "= 50 - 55    (< QCVN nuit)" at: {14 #px, 122 #px} color: rgb(102, 189, 99) font: font("Helvetica", 10, #bold);
                draw "= 55 - 60" at: {14 #px, 138 #px} color: rgb(150, 200, 80) font: font("Helvetica", 10, #bold);
                draw "= 60 - 65" at: {14 #px, 154 #px} color: rgb(225, 195, 60) font: font("Helvetica", 10, #bold);
                draw "= 65 - 70" at: {14 #px, 170 #px} color: rgb(253, 174, 60) font: font("Helvetica", 10, #bold);
                draw "= 70 - 75    (> QCVN jour)" at: {14 #px, 186 #px} color: rgb(230, 90, 45) font: font("Helvetica", 10, #bold);
                draw "= 75 - 80" at: {14 #px, 202 #px} color: rgb(190, 35, 35) font: font("Helvetica", 10, #bold);
                draw "= > 80" at: {14 #px, 218 #px} color: rgb(126, 20, 40) font: font("Helvetica", 10, #bold);

                draw "VEHICULES  (mix mesure par video)" at: {14 #px, 244 #px} color: rgb(20, 20, 20)
                     font: font("Helvetica", 9, #bold);
                draw "o moto" at: {14 #px, 262 #px} color: rgb(255, 140, 0) font: font("Helvetica", 10, #bold);
                draw "o voiture" at: {90 #px, 262 #px} color: rgb(20, 90, 190) font: font("Helvetica", 10, #bold);
                draw "o bus/camion" at: {175 #px, 262 #px} color: rgb(95, 35, 130) font: font("Helvetica", 10, #bold);

                draw "Chantiers: " + string(n_constr) + (constr_active ? " actifs" : " arretes")
                     + "   Mitigation: " + mitigation
                     at: {14 #px, 274 #px} color: rgb(60, 60, 60) font: font("Helvetica", 9, #plain);
                draw "Fond : modele ML (cf. metrics.json) · trafic : 147 videos"
                     at: {14 #px, 286 #px} color: rgb(130, 130, 130) font: font("Helvetica", 8, #plain);
            }
        }

        display "Indicateurs" type: java2D background: #white {
            chart "Exposition (% de la zone)" type: series size: {1.0, 0.5} position: {0.0, 0.0}
                  y_range: [0, 100] {
                data "> QCVN jour 70 dB" value: exceed_qcvn color: rgb(200, 40, 40) marker: false thickness: 2.5;
                data "> QCVN nuit 55 dB" value: exceed_night color: rgb(80, 80, 80) marker: false thickness: 2.0;
            }
            chart "Niveau moyen de la zone (dB)" type: series size: {1.0, 0.5} position: {0.0, 0.5} {
                data "L moyen" value: mean_dB color: rgb(30, 110, 180) marker: false thickness: 2.5;
                data "seuil QCVN" value: qcvn_day color: rgb(200, 40, 40) marker: false thickness: 1.0;
            }
        }

        monitor "Zone" value: zone_label;
        monitor "Heure" value: string(hour_of_day) + "h00";
        monitor "Trafic à cette heure" value: traffic_source;
        monitor "Facteur de trafic" value: traffic_multiplier;
        monitor "Mitigation" value: mitigation;
        monitor "Chantiers (actifs ?)" value: string(n_constr) + (constr_active ? " · actifs" : " · arretes");
        monitor "L moyen < 200 m d'un chantier" value: constr_zone_dB with_precision 1;
        monitor "Véhicules simulés (densité)" value: n_vehicles;
        monitor "Débit mesuré (véh/min)" value: flow_now with_precision 1;
        monitor "dont motos (véh/min)" value: flow_moto_now with_precision 1;
        monitor "L moyen (dB)" value: mean_dB with_precision 1;
        monitor "L max (dB)" value: peak_dB with_precision 1;
        monitor "% zone > QCVN jour (70 dB)" value: exceed_qcvn with_precision 1;
        monitor "% zone > QCVN nuit (55 dB)" value: exceed_night with_precision 1;
        monitor "Ambiance residuelle (dB)" value: ambient_dB with_precision 1;
    }
}

// Expérimentation de contrôle : sans rendu graphique, pour valider la logique
// (heure, facteur de trafic, indicateurs) rapidement en ligne de commande.
experiment check type: gui {
    parameter "zone" var: zone;
    parameter "hour_of_day" var: hour_of_day;
    parameter "traffic_multiplier" var: traffic_multiplier;
    parameter "mitigation" var: mitigation;
    parameter "construction_on" var: construction_on;
    parameter "work_end" var: work_end;
    output {
        monitor "vehicules" value: n_vehicles;
        monitor "flow_veh_min" value: flow_now with_precision 2;
        monitor "flow_moto_min" value: flow_moto_now with_precision 2;
        monitor "share_hw_moy" value: mean(NoisePoint collect each.share_hw) with_precision 3;
        monitor "chantiers" value: n_constr;
        monitor "constr_actifs" value: constr_active;
        monitor "L_constr_200m" value: constr_zone_dB with_precision 2;
        monitor "L_moyen" value: mean_dB with_precision 2;
        monitor "L_max" value: peak_dB with_precision 2;
        monitor "pct_qcvn" value: exceed_qcvn with_precision 2;
        monitor "pct_qcvn_night" value: exceed_night with_precision 2;
        monitor "source" value: traffic_source;
    }
}
