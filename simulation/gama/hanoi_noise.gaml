/**
 * ============================================================================
 *  HANOI URBAN NOISE - agent-based simulation
 *  [AFFILIATION TO CONFIRM - CEI or COSMOS Lab], VinUniversity
 * ============================================================================
 *
 *  What the simulation shows
 *  -------------------------
 *  An urban noise map that varies with the HOUR of the day and with a TRAFFIC
 *  VOLUME scenario, together with moving vehicles whose composition
 *  (motorcycles / cars / heavy vehicles) is measured on our own videos.
 *
 *  Scientific status of each layer  (important: they do not all have the same status)
 *  --------------------------------------------------------------------------
 *  1. BACKGROUND LEVEL (coloured cells) - PREDICTED
 *     Since V2 (August 2026) the delivered model is a THREE-PARAMETER PHYSICAL
 *     KERNEL, no longer a LightGBM. Each road class is treated as an incoherent
 *     LINE source: intensity falls as 1/d (not as 1/d^2, which would hold for a
 *     point source).
 *
 *         E(x) = A_hw / max(d_hw, D0)  +  A_res / max(d_res, D0)  +  B
 *         L(x) = 10 * log10( E(x) )
 *
 *     d_hw  = distance to the nearest major road (motorway/trunk/primary/secondary)
 *     d_res = distance to the nearest minor street (tertiary/residential/...)
 *     Coefficients fitted on our 363 measurements, constrained non-negative, readable in
 *     inputs/physical_params.csv. One value per hour, 05:00-21:00.
 *
 *     ACTUAL PERFORMANCE (run of 5 August 2026, models/metrics.json, produced by
 *     scripts/04_evaluate_models.py: n = 363, 17 blocks, 95 % bootstrap CI) - R2:
 *
 *         model                           block-CV 600 m   BUFFERED LOO   leave-one-site-out
 *                                                          (reference)
 *         site x hour table                     -0.008        -0.419            -0.058
 *         regression on log(dist_road)           0.221         0.200             0.189
 *         physical kernel (THIS MODEL)           0.255         0.246             0.222
 *         LightGBM v1 (6 features)               0.304         0.137             0.029
 *         LightGBM v2 (8 features)               0.332         0.099            -0.035
 *         hybrid physics + ML on residual        0.395         0.123             0.035
 *
 *     >>> READ THIS TABLE BEFORE INTERPRETING THE MAP. The ranking INVERTS almost
 *     exactly between the first column (permissive protocol) and the next two
 *     (protocols that test generalisation). We built the hybrid architecture we
 *     recommended ourselves: it dominates under block-CV and LOSES under both strict
 *     protocols (dR2 -0.123 and -0.187 against the physical kernel alone).
 *     That is why the map shown here is produced by the PHYSICS ALONE: the residual
 *     LightGBM is trained and saved, but NOT applied. The choice is made by the code
 *     (04_evaluate_models.py, flag `apply_residual`), not by hand.
 *
 *     Practical consequence: the spatial contrasts displayed are driven by the distance
 *     to the two road classes, and by nothing else. Morphology aggregated over 300 m
 *     brought no measurable gain. See docs/negative-results.md section 5.z.
 *
 *     The R2 0.45 shown until July 2026 came from a CV grouped on 110 m cells, smaller
 *     than the 300 m feature radius: it leaked and overstated performance. It must no
 *     longer be cited.
 *
 *     This is an L_eq-type level: an average, not an instantaneous reading. It is
 *     calibrated in RELATIVE terms (contrasts between places and between hours), not in
 *     absolute terms: our sensors are uncertified smartphones - see docs/metrology.md.
 *
 *  2. TRAFFIC (vehicles) - MEASURED
 *     147 timestamped videos, matched to our noise measurements (median gap 15 s),
 *     aggregated by site and by hour. Unfilmed hours are interpolated and
 *     flagged as such by the "Traffic at this hour" indicator.
 *
 *     TWO QUANTITIES, NOT TO BE CONFUSED (v2, August 2026):
 *       - DENSITY (veh/frame): what v1 saw, obtained by frame-by-frame
 *         detection. Drives the NUMBER of Vehicle agents displayed.
 *       - FLOW (veh/min): crossings of a virtual line at the centre of
 *         the image, obtained by object TRACKING (YOLOv8 + ByteTrack). This is the
 *         quantity that physically governs acoustic emission, and it is the one
 *         shown by the "Measured flow" and "of which motorcycles" monitors.
 *     The two diverge exactly where it matters: in congestion density is
 *     maximal and flow collapses. That is why v1 found no
 *     link between traffic and sound level.
 *
 *  3. VEHICLES - VISUAL, NOT ACOUSTIC  (a calibration result)
 *     The vehicles displayed represent the measured fleet (number and composition),
 *     but they add NO noise to the computation. Reason: we attempted to
 *     calibrate a per-category emission on our own data
 *     (scripts/05_calibrate_emissions.py, energy regression under a non-negativity
 *     constraint over the 147 matched videos). All three coefficients came out
 *     NULL: at a given site, the number of visible vehicles does not explain
 *     the measured level (R2 0.008 to 0.044 depending on the site; correlations of
 *     inconsistent sign: Hoan Kiem -0.09, Ocean Park -0.19, Vinh Tuy +0.21, and -0.15 over
 *     the 147 matched videos). Probable causes: parked vehicles are counted, the distance
 *     of each vehicle is ignored, and speed - which dominates rolling
 *     noise - is not observable from a count. Rather than injecting invented
 *     values, we abstain: the level stays driven by the validated model
 *     and by the traffic volume law.
 *
 *  3bis. CONSTRUCTION SITES - CALIBRATED ON OUR MEASUREMENTS
 *     Our 32 "construction nearby" points (measured median distance: 56 m from the
 *     site) are +2.0 dB above the other 152 points at Ocean Park. Converted
 *     to energy, this corresponds to an equivalent source of 64.7 dB at 56 m (medians). The
 *     simulation adds that energy with geometric attenuation
 *     L(d) = 64.7 - 20*log10(d / 56), summed in ENERGY with the background.
 *
 *  4. TRAFFIC SCENARIO (slider) - A PHYSICAL LAW, APPLIED TO THE TRAFFIC SHARE ONLY
 *     Multiplying flow by k shifts by 10*log10(k) the share of energy ATTRIBUTABLE TO
 *     TRAFFIC: doubling traffic = +3 dB where traffic dominates, almost nothing in an
 *     inner courtyard. Each cell is decomposed as
 *           E_cell = E_residual + E_traffic,
 *     E_residual being estimated by the 5th percentile of the predicted levels of the zone at
 *     that hour (the quietest cells = those where traffic contributes least).
 *     Likewise for mitigation: a "zone 30" removes 3 dB at the SOURCE, and only within
 *     a radius of 150 m of a road.
 *     CORRECTION OF AUGUST 2026: previously, 10*log10(k) and the -3 dB were added
 *     UNIFORMLY to every cell, which is physically wrong and overstated
 *     the effect of the scenarios far from roads.
 *     Invariant: at k = 1 with no mitigation, the map is identical to the predicted map.
 *
 *  Regulatory thresholds displayed: QCVN 26:2010/BTNMT (Vietnam, ordinary zone),
 *  70 dB from 06:00 to 21:00 - 55 dB from 21:00 to 06:00. The WHO 53 dB recommendation was
 *  withdrawn: it is an L_den (annual average, evening/night penalties), not comparable to our
 *  quantity - see docs/metrology.md.
 *
 *  Inputs: generated by `python3 scripts/07_export_gama_inputs.py`
 * ============================================================================
 */
model hanoi_noise

global {
    // ---------------- study area ----------------
    // The 3 sites are ~10 km apart: we frame one site at a time.
    //
    // WHY YOU MUST PRESS RELOAD (reload) AND NOT ONLY PLAY
    // The `file` declarations below are GLOBAL variables: GAMA evaluates them ONCE only,
    // when the simulation is created. Changing the zone in the parameter panel does not
    // recompute them - the experiment has to be reloaded.
    // This is not a model defect: verified headless, `zone=hoankiem` does load
    // Hoan Kiem (1763 cells, 673 roads, 10241 buildings, 99 field measurements). It is the
    // life cycle of GAMA globals, not a frozen file path.
    string target_zone <- "Ocean Park" among: ["Ocean Park", "Hoan Kiem", "Vinh Tuy"];

    // Matching file slug: the shapefiles are named in lower case, without spaces.
    // We keep `zone` as a derived variable so as not to rewrite every path.
    string zone <- (target_zone = "Ocean Park") ? "oceanpark"
                    : ((target_zone = "Hoan Kiem") ? "hoankiem" : "vinhtuy");

    file roads_file     <- file('inputs/' + zone + '_roads.shp');
    file buildings_file <- file('inputs/' + zone + '_buildings.shp');
    file noise_shp      <- file('inputs/' + zone + '_noise.shp');
    file fleet_csv      <- csv_file('inputs/fleet_by_hour.csv', true);
    string phys_path    <- 'inputs/physical_params.csv';
    string constr_path  <- 'inputs/' + zone + '_construction.shp';
    string meas_path    <- 'inputs/' + zone + '_measurements.shp';

    // World envelope. ESSENTIAL: without it GAMA creates a 100x100 m world,
    // agents fall outside the spatial index and closest_to / at_distance
    // return nil (silent bug: vehicles stop affecting anything).
    geometry shape <- envelope(noise_shp);

    // ---------------- scenario parameters ----------------
    int   hour_of_day        <- 17 min: 5 max: 21;
    float traffic_multiplier <- 1.0 min: 0.2 max: 3.0;
    // Mitigation scenarios (Phase 4):
    //   "zone 30"       -> speed reduced 50->30 km/h: -3 dB (literature range -2 to -4)
    //   "pietonnisation"-> traffic reduced to 20%: -7 dB via 10*log10(0.2)
    string mitigation        <- "aucune" among: ["aucune", "zone 30", "pietonnisation"];
    // Construction sites: activity hours (scenario "extended hours" = widen the range)
    bool  construction_on    <- true;
    int   work_start         <- 7  min: 5 max: 12;
    int   work_end           <- 17 min: 13 max: 21;
    bool  show_vehicles      <- true;
    bool  show_measures      <- false;  // our field measurement points

    // ---------------- constants ----------------
    int   HMIN <- 5;
    int   HMAX <- 21;
    // Displayed thresholds. Both are VIETNAMESE thresholds, bearing on the same quantity
    // as ours (a level, not a long-term indicator). The WHO 53 dB reference has been
    // WITHDRAWN: it is an L_den, an ANNUAL average with evening/night penalties, not comparable to
    // an hourly level predicted from 25 s samples (docs/metrology.md).
    float qcvn_day   <- 70.0;  // QCVN 26:2010/BTNMT, ordinary zone, 06:00-21:00
    float qcvn_night <- 55.0;  // QCVN 26:2010/BTNMT, ordinary zone, 21:00-06:00
    // ---------------- data-driven traffic (v2.1, August 2026) ----------------
    // BEFORE: the number of vehicles displayed was `density x 22`, a FIXED population
    // of immortal agents wandering at random. The factor 22 came from nowhere, and
    // no vehicle entered or left: that is what made the traffic look artificial.
    //
    // NOW: vehicles are created at a RATE equal to the FLOW MEASURED by ByteTrack
    // video tracking for (zone, hour), they cross the network, then DISAPPEAR.
    // The displayed population is no longer imposed: it EMERGES from flow and crossing
    // time, which is exactly Little's law (N = flow x residence time).
    //
    // FLOW_LINES_EQUIV: flow is measured on ONE counting section (a line in
    // one video), whereas the simulated zone holds hundreds of streets. This factor states
    // how many equivalent sections the zone is taken to represent. 1.0 = the conservative
    // reading "the whole zone carries the flow measured at one point". It is an ASSUMED
    // scaling choice, not a measurement: raising it densifies the display without changing
    // the sound level, which does not depend on the agents (see header, point 3).
    float FLOW_LINES_EQUIV <- 1.0 min: 0.2 max: 20.0;
    int   VEH_MAX_HOPS     <- 3;     // segments travelled before leaving the network

    // WHERE DOES THE MEASURED FLOW APPLY? (correction of 6 August 2026)
    // Observed bug: at Hoan Kiem, almost no vehicle visible around the lake although
    // ALL the videos were filmed there. Cause: vehicles were created on
    // `one_of(Road)`, hence UNIFORMLY over the 673 streets of the exported zone - which
    // extends 400 m beyond the survey envelope. With ~51 live vehicles, that is 0.076
    // vehicles per street: any street, including the lake loop, is empty 92 % of the
    // time. Flow measured at ONE point was diluted over a whole district.
    // Correction: flow applies only to the CORRIDOR ACTUALLY OBSERVED, that is,
    // to streets within FLOW_RADIUS of one of our measurement points. It is also
    // more honest: we measured nothing 400 m from the lake, so we inject nothing there.
    float FLOW_RADIUS <- 150.0 min: 50.0 max: 600.0;
    list<Road> spawn_roads <- [];   // streets carrying the measured flow (computed at init)

    // Background / traffic decomposition (see the physics correction in `reflex scenario`).
    float AMBIENT_PCT   <- 0.05;  // low percentile taken as non-road residual ambience
    float MITIG_RADIUS  <- 150.0; // reach of a mitigation measure around a road (m)
    float Z30_DB        <- -3.0;  // zone 30: -3 dB at the SOURCE (literature -2 to -4)

    // ---------------- fitted physical kernel (v2, August 2026) ----------------
    // Coefficients read from inputs/physical_params.csv, produced by
    // scripts/04_evaluate_models.py. LINE source model: E = A/d (not A/d^2).
    //     E_trafic(cellule) = A_HW / max(d_hw, D0) + A_RES / max(d_res, D0)
    // We do NOT use them to recompute the level (the predicted grid already carries it),
    // but to know HOW a cell's traffic energy splits between
    // major roads and minor streets. That is what allows mitigation to be targeted:
    // a "zone 30" acts on local streets, not on the trunk road next to them.
    float A_HW  <- 0.0;
    float A_RES <- 0.0;
    float B_BG  <- 0.0;
    float PHYS_D0 <- 5.0;
    bool  phys_ok <- false;

    // Construction sites: equivalent source calibrated on OUR measurements.
    float L_CONSTR_REF <- 64.7;   // equivalent source at D_CONSTR_REF (computed on medians)
    float D_CONSTR_REF <- 56.0;   // reference distance, observed median (m)
    float D_MIN        <- 25.0;   // floor = 1st quartile of observed distances (32 m)
    float CONSTR_RADIUS <- 250.0; // beyond this, the contribution is negligible

    // ---------------- indicators ----------------
    float mean_dB     <- 0.0;
    float exceed_qcvn <- 0.0;
    float exceed_night <- 0.0;   // % of the zone above the QCVN NIGHT threshold (55 dB)
    float ambient_dB   <- 0.0;   // non-road residual ambience of the zone, at this hour
    float peak_dB     <- 0.0;
    int   n_vehicles  <- 0;
    float flow_now      <- 0.0;   // total flow at the current hour (veh/min), scenario included
    float flow_moto_now <- 0.0;   // of which motorcycles
    string traffic_source <- "-";
    string zone_label <- "-";
    float  mitigation_dB <- 0.0;
    float  eff_traffic <- 1.0;
    bool   constr_active <- false;
    int    n_constr <- 0;
    float  constr_zone_dB <- 0.0;   // mean level within 200 m of a construction site

    // hourly traffic profiles (read from fleet_by_hour.csv)
    // TWO distinct quantities, not to be confused:
    //   fleet_total     DENSITY  - vehicles visible per frame. Drives the NUMBER
    //                              of Vehicle agents displayed (what is seen on screen).
    //   fleet_flow      FLOW     - line crossings per minute (ByteTrack tracking).
    //                              This is the quantity governing acoustic EMISSION.
    // In congestion the two diverge: density maximal, flow collapsed.
    map<int, float> fleet_total  <- [];
    map<int, float> fleet_moto   <- [];
    map<int, float> fleet_car    <- [];
    map<int, int>   fleet_meas   <- [];
    map<int, float> fleet_flow      <- [];
    map<int, float> fleet_moto_flow <- [];
    map<int, float> fleet_car_flow  <- [];

    // composition of the FLOW at the current hour (shares computed on flows, not on
    // density: we create vehicles at a rate, so the mix must be that of the flow)
    float moto_share_now <- 0.5;
    float car_share_now  <- 0.35;
    float spawn_debt     <- 0.0;   // fractional vehicle carried from one step to the next
    int   spawned_total  <- 0;

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

        // physical kernel coefficients (a single data row)
        if (file_exists(phys_path)) {
            matrix pm <- matrix(csv_file(phys_path, true));
            A_HW    <- float(pm[0, 0]);
            A_RES   <- float(pm[1, 0]);
            B_BG    <- float(pm[2, 0]);
            PHYS_D0 <- float(pm[3, 0]);
            phys_ok <- (A_HW + A_RES) > 0;
        }
        // Share of traffic energy attributable to MAJOR ROADS, cell by cell.
        // If the coefficients are missing, we fall back to 50/50: mitigation remains
        // applicable, simply without targeting by road class.
        ask NoisePoint {
            if (phys_ok) {
                float e_hw  <- A_HW  / max([d_hw,  PHYS_D0]);
                float e_res <- A_RES / max([d_res, PHYS_D0]);
                share_hw <- (e_hw + e_res) > 0 ? e_hw / (e_hw + e_res) : 0.5;
            } else {
                share_hw <- 0.5;
            }
        }

        // hourly traffic profile of the site
        // columns: 0 site_name - 1 hour - 2 total - 3 measured - 4 n_videos
        //            5 moto_share - 6 car_share - 7 bus_share - 8 truck_share
        //            9 total_flow_per_min - 10 moto_flow_per_min - 11 car_flow_per_min
        //            12 bus_flow_per_min - 13 truck_flow_per_min      (v2, columns appended
        //            AT THE END of the file: indices 0-8 above remain valid)
        matrix fl <- matrix(fleet_csv);
        loop i from: 0 to: fl.rows - 1 {
            if (string(fl[0, i]) = site_key) {
                int h <- int(fl[1, i]);
                fleet_total[h] <- float(fl[2, i]);
                fleet_meas[h]  <- int(fl[3, i]);
                fleet_moto[h]  <- float(fl[5, i]);
                fleet_car[h]   <- float(fl[6, i]);
                if (fl.columns > 11) {
                    fleet_flow[h]      <- float(fl[9, i]);
                    fleet_moto_flow[h] <- float(fl[10, i]);
                    fleet_car_flow[h]  <- float(fl[11, i]);
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

        // Distance from each cell to the nearest road: fixed here once and for
        // all, used to bound mitigation scenarios spatially (a zone 30
        // has no effect on an inner courtyard 300 m from any street).
        ask NoisePoint {
            Road r <- Road closest_to self;
            d_road <- (r = nil) ? 1e6 : (self distance_to r);
        }

        write "Zone " + zone_label + " : " + string(length(NoisePoint)) + " cellules, "
            + string(length(Road)) + " routes, " + string(length(Building)) + " batiments, "
            + string(n_constr) + " chantiers, " + string(length(Measure)) + " mesures terrain.";
        // Corridor into which measured flow is injected: the streets near our measurement
        // points, that is, where the videos were actually filmed.
        if (!empty(Measure)) {
            spawn_roads <- Road where ((each distance_to (Measure closest_to each)) <= FLOW_RADIUS);
        }
        // Fallback: if no measurement is available for the zone, we fall back to the whole
        // network rather than letting nothing circulate at all.
        if (empty(spawn_roads)) { spawn_roads <- copy(Road); }

        // Startup trace: says immediately whether the physical kernel and the flows were
        // loaded correctly. Without it, a missing CSV produced a silent
        // fallback (50/50 share, zero flow) indistinguishable from a real result.
        write "  physique : " + (phys_ok
                ? "A_hw=" + string(A_HW with_precision 0) + " A_res=" + string(A_RES with_precision 0)
                  + " B=" + string(B_BG) + " -> part grands axes moyenne "
                  + string((mean(NoisePoint collect each.share_hw)) with_precision 3)
                : "NON CHARGEE (repli 50/50) - lancer scripts/export_gama_zones.py");
        do sync_fleet;
        write "  trafic   : debit mesure " + string(flow_now with_precision 1) + " veh/min a "
            + string(hour_of_day) + "h (dont motos " + string(flow_moto_now with_precision 1)
            + ", part " + string(moto_share_now with_precision 2) + ") - source "
            + traffic_source;
        write "  corridor : " + string(length(spawn_roads)) + " rues sur " + string(length(Road))
            + " portent ce debit (a moins de " + string(int(FLOW_RADIUS)) + " m d'une mesure)";
    }

    // ---- reads the measured FLOW for (zone, hour) and derives the flow composition ----
    // No longer adjusts any population: the number of agents is now a CONSEQUENCE
    // of the flow (see `reflex spawn_traffic`), not an imposed target.
    action sync_fleet {
        traffic_source <- (fleet_meas[hour_of_day] = 1) ? "mesure (videos)" : "interpole";
        // flow measured at this hour, scaled by the scenario: this is THE quantity
        // driving the simulation, and the one to quote when speaking of traffic intensity.
        flow_now      <- (fleet_flow[hour_of_day] = nil) ? 0.0
                            : fleet_flow[hour_of_day] * eff_traffic;
        flow_moto_now <- (fleet_moto_flow[hour_of_day] = nil) ? 0.0
                            : fleet_moto_flow[hour_of_day] * eff_traffic;
        float f_car   <- (fleet_car_flow[hour_of_day] = nil) ? 0.0
                            : fleet_car_flow[hour_of_day] * eff_traffic;
        // shares of the FLOW (not of density); fall back to neutral values if the CSV
        // is a v1 version without flow columns.
        moto_share_now <- (flow_now > 0) ? min([1.0, flow_moto_now / flow_now]) : 0.5;
        car_share_now  <- (flow_now > 0) ? min([1.0 - moto_share_now, f_car / flow_now]) : 0.35;
        n_vehicles <- length(Vehicle);
    }

    // ---- VEHICLE CREATION AT THE MEASURED FLOW ----
    // Core of the data-driven design: over a step of `step` seconds, we must create
    //     flow(veh/min) / 60 * step * FLOW_LINES_EQUIV
    // vehicles. That number is almost always fractional; we carry the fraction in
    // `spawn_debt` from one step to the next, which reproduces the flow EXACTLY on average
    // instead of rounding (rounding to 0 would kill all traffic below 60/step veh/min).
    reflex spawn_traffic {
        spawn_debt <- spawn_debt + (flow_now / 60.0) * step * FLOW_LINES_EQUIV;
        int n <- int(spawn_debt);
        if (n > 0) {
            spawn_debt <- spawn_debt - n;
            spawned_total <- spawned_total + n;
            create Vehicle number: n {
                do enter_network;
                float d <- rnd(1.0);
                // Differentiated speeds for RENDERING only. No acoustic emission
                // is associated with the vehicles: it is not identifiable from our
                // data, neither as density nor as flow (header, point 3).
                if (d < moto_share_now)                       { v_type <- "moto";  speed <- 9.0; }
                else if (d < moto_share_now + car_share_now)  { v_type <- "car";   speed <- 11.0; }
                else                                          { v_type <- "heavy"; speed <- 8.0; }
            }
        }
        n_vehicles <- length(Vehicle);
    }

    // ---- NON-ROAD ambient floor of the zone at the current hour ----
    // Low percentile of the predicted levels: the quietest cells of the zone are
    // those where traffic contributes least. We use it as an estimate of the residual
    // ambience (ventilation, activity, birdsong, distant noise), which a traffic
    // scenario must NOT move.
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

        // Background level predicted for the hour, BEFORE the scenario.
        ask NoisePoint { base_dB <- db_by_hour[hour_of_day - HMIN]; }
        do compute_ambient;
        float e_amb_zone <- 10 ^ (ambient_dB / 10);

        // ------------------------------------------------------------------------------
        //  PHYSICS CORRECTION (August 2026) - background / traffic energy decomposition
        // ------------------------------------------------------------------------------
        //  BEFORE: background_dB <- base_dB + 10*log10(k) + mitigation_dB, applied
        //  UNIFORMLY to every cell. Physically wrong: 10*log10(k) holds only
        //  for the share of energy ATTRIBUTABLE TO TRAFFIC. Tripling traffic added +4.8 dB
        //  even inside courtyards, where traffic contributes almost nothing; and
        //  the "zone 30" removed 3 dB from cells that no street serves.
        //
        //  NOW: each cell is decomposed as
        //        E_cell = E_residual + E_traffic
        //  with E_residual = min(E_ambient_zone, E_cell)  (never more than the cell).
        //  Only E_traffic is subject to the volume factor and to mitigation.
        //
        //  Checkable invariant: at k = 1 with no mitigation, background_dB == base_dB
        //  exactly for every cell - the reference map is unchanged.
        //
        //  The "zone 30" mitigation (-3 dB at the source, literature range -2 to -4)
        //  is moreover bounded to MITIG_RADIUS around a road: beyond that, a speed
        //  reduction has no physical meaning.
        // ------------------------------------------------------------------------------
        //  v2 REFINEMENT (August 2026) - MITIGATION TARGETS ONE ROAD CLASS
        //  A cell's traffic energy is itself split in two, according to the
        //  fitted physical kernel (A_HW/d_hw against A_RES/d_res):
        //        E_traffic = E_major_roads + E_minor_streets
        //  A "zone 30" is a traffic order on LOCAL streets: it therefore
        //  applies only to E_minor_streets. Applying it to major roads as well,
        //  as v1 did, credited the scenario with a reduction on cells
        //  whose noise comes from a trunk road the measure does not touch.
        //  Likewise for pedestrianisation: streets are closed, not an expressway.
        //  Invariant preserved: at k = 1 with no mitigation, background_dB == base_dB.
        //  NB: we start from `traffic_multiplier` and not from `eff_traffic`, which already
        //  carries the 0.2 pedestrianisation factor - applying it twice would double the effect.
        //  `eff_traffic` is still used by sync_fleet for the NUMBER of vehicles displayed.
        float f_z30 <- 10 ^ (Z30_DB / 10);             // -3 dB -> energy factor ~0.50

        ask NoisePoint {
            float e_tot     <- 10 ^ (base_dB / 10);
            float e_res     <- min([e_amb_zone, e_tot]);
            float e_traffic <- e_tot - e_res;
            float e_hw_part  <- e_traffic * share_hw;
            float e_res_part <- e_traffic * (1 - share_hw);
            float f_hw   <- traffic_multiplier;   // volume applies to both classes
            float f_loc  <- traffic_multiplier;
            if (mitigation = "zone 30" and d_res <= MITIG_RADIUS) { f_loc <- f_loc * f_z30; }
            if (mitigation = "pietonnisation")                    { f_loc <- f_loc * 0.2; }
            background_dB <- 10 * log(e_res + f_hw * e_hw_part + f_loc * e_res_part) / log(10);
            constr_energy <- 0.0;
        }
        // Mean EFFECTIVE shift over the zone (replaces the old hardcoded -3 dB display).
        // It is now always smaller in absolute value than the "source" shift,
        // since cells dominated by residual ambience move little: that is
        // exactly what the old uniform formula overestimated.
        mitigation_dB <- mean(NoisePoint collect (each.background_dB - each.base_dB));
    }

    // active construction sites: energy added, geometric attenuation from the source
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
        // ENERGY sum: background (already contains mean traffic) + construction sites
        ask NoisePoint {
            float e <- (10 ^ (background_dB / 10)) + constr_energy;
            effective_dB <- 10 * log(e) / log(10);
        }
        mean_dB     <- mean(NoisePoint collect each.effective_dB);
        peak_dB     <- max(NoisePoint collect each.effective_dB);
        exceed_qcvn <- (NoisePoint count (each.effective_dB > qcvn_day)) / length(NoisePoint) * 100;
        exceed_night <- (NoisePoint count (each.effective_dB > qcvn_night)) / length(NoisePoint) * 100;
        // local effect of construction: the zone mean hides it (4 sites / several
        // thousand cells), so we track the immediate neighbourhood of the sites.
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
    float base_dB       <- 55.0;  // level predicted for the current hour, BEFORE scenario
    float d_road        <- 0.0;   // distance to the nearest road (m), fixed at init
    float d_hw          <- 2000.0; // distance to the nearest major road (m), from the shp
    float d_res         <- 2000.0; // distance to the nearest minor street (m)
    float share_hw      <- 0.5;   // share of traffic energy coming from major roads
    float background_dB <- 55.0;
    float constr_energy <- 0.0;   // energy contributed by active construction sites
    float effective_dB <- 55.0;

    // Noise map palette: 5 dB bands, green -> dark red.
    // The orange/red switch is set on the QCVN daytime threshold (70 dB).
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
        // diamond = construction site; filled when active at this hour
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
    int idx  <- 0;
    int hops <- 0;              // segments already travelled: bounds the lifetime

    // ENTERING THE NETWORK. The vehicle appears at one END of a randomly drawn
    // road, in one direction or the other (flip), no longer always at the first vertex:
    // otherwise all traffic ran in the same direction on every street.
    action enter_network {
        // drawn from the MEASURED CORRIDOR, not from the whole network: see FLOW_RADIUS
        my_road <- empty(spawn_roads) ? one_of(Road) : one_of(spawn_roads);
        hops <- 0;
        idx <- 0;
        if (my_road != nil) {
            pts <- copy(my_road.shape.points);
            if (flip(0.5)) { pts <- reverse(pts); }   // both directions of travel
            if (!empty(pts)) { location <- first(pts); }
        }
    }

    // Movement along the vertices of the road polyline, then transition to a
    // neighbouring road. We do not use `goto ... on: graph`: the exported OSM network is
    // fragmented (few shared nodes), pathfinding fails and the agents stay frozen.
    //
    // LEAVING THE NETWORK after VEH_MAX_HOPS segments. This is what makes the population
    // EMERGENT: vehicles enter at the measured flow and leave after a finite
    // crossing time, so N settles around flow x residence time (Little's
    // law) instead of being set by hand. Without this exit, agents accumulated
    // indefinitely and wandered at random.
    action pick_road {
        hops <- hops + 1;
        if (hops > VEH_MAX_HOPS) {
            do die;
        } else {
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
    parameter "Site (APPUYER SUR ⟳ RELANCER après changement)" var: target_zone
              category: "1 · Zone";
    parameter "Heure de la journée" var: hour_of_day category: "2 · Scénario";
    parameter "Facteur de trafic (1.0 = observé)" var: traffic_multiplier category: "2 · Scénario";
    parameter "Mitigation" var: mitigation category: "2 · Scénario";
    parameter "Chantiers actifs" var: construction_on category: "2 · Scénario";
    parameter "Chantier : début" var: work_start category: "2 · Scénario";
    parameter "Chantier : fin (horaires étendus)" var: work_end category: "2 · Scénario";
    parameter "Densité d'affichage du trafic (sections équivalentes)" var: FLOW_LINES_EQUIV
              category: "2 · Scénario";
    parameter "Rayon du corridor mesuré (m) — relancer" var: FLOW_RADIUS
              category: "2 · Scénario";
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
        monitor "Débit MESURÉ (véh/min)" value: flow_now with_precision 1;
        monitor "dont motos (véh/min)" value: flow_moto_now with_precision 1;
        monitor "Part motos dans le FLUX" value: moto_share_now with_precision 2;
        // An instructive contrast: the motorcycle share in DENSITY (what is seen on one
        // frame) differs from their share in the FLOW (what actually passes). At Hoan
        // Kiem: 0.64 in density against 0.82 in flow - motorcycles move, cars
        // are parked or move more slowly. This is the heart of the v2 distinction.
        monitor "  (rappel) part motos en DENSITÉ" value: (fleet_moto[hour_of_day] = nil)
                ? 0.0 : fleet_moto[hour_of_day] with_precision 2;
        monitor "Rues portant le débit (corridor mesuré)" value: length(spawn_roads);
        monitor "Véhicules présents (émergent)" value: n_vehicles;
        monitor "Véhicules créés (cumul)" value: spawned_total;
        monitor "L moyen (dB)" value: mean_dB with_precision 1;
        monitor "L max (dB)" value: peak_dB with_precision 1;
        monitor "% zone > QCVN jour (70 dB)" value: exceed_qcvn with_precision 1;
        monitor "% zone > QCVN nuit (55 dB)" value: exceed_night with_precision 1;
        monitor "Ambiance residuelle (dB)" value: ambient_dB with_precision 1;
    }
}

// Control experiment: without graphical rendering, to validate the logic
// (hour, traffic factor, indicators) quickly from the command line.
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
