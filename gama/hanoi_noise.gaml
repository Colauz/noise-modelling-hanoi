/**
 * Hanoi Noise Simulation
 * Import road network + buildings from OSMnx exports
 * Load predicted noise levels from Python surrogate model
 */
model hanoi_noise

global {
    file roads_file     <- file('../outputs/maps/gama_inputs/roads.shp');
    file buildings_file <- file('../outputs/maps/gama_inputs/buildings.shp');
    file noise_csv      <- csv_file('../outputs/maps/gama_inputs/noise_map.csv', true);

    // Scénarios : modifie ces paramètres pour tester
    float traffic_multiplier <- 1.0;  // 1.5 = +50% de trafic
    bool construction_active <- true;

    geometry shape <- envelope(roads_file);

    init {
        create Road from: roads_file;
        create Building from: buildings_file;
        // TODO: charger les points de bruit depuis noise_csv
        // TODO: créer des agents Vehicle qui se déplacent sur les routes
    }
}

species Road {
    aspect default { draw shape color: #gray; }
}

species Building {
    aspect default { draw shape color: #lightblue border: #black; }
}

// TODO: species Vehicle { ... }
// TODO: species NoiseSource { float level_dB; ... }

experiment hanoi_noise_sim type: gui {
    output {
        display map type: opengl {
            species Road aspect: default;
            species Building aspect: default;
        }
    }
}
