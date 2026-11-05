export interface RegionWeather {
    temperature: number
    wind_speed: number
    humidity: number
}

export const REGION_COORDS: Record<string, { lat: number; lon: number }> = {
    "Île-de-France":              { lat: 48.8566,  lon: 2.3522  },
    "Auvergne-Rhône-Alpes":       { lat: 45.7640,  lon: 4.8357  },
    "Bourgogne-Franche-Comté":    { lat: 47.3220,  lon: 5.0415  },
    "Bretagne":                   { lat: 48.1173,  lon: -1.6778 },
    "Centre-Val de Loire":        { lat: 47.9029,  lon: 1.9039  },
    "Corse":                      { lat: 41.9192,  lon: 8.7386  },
    "Grand Est":                  { lat: 48.5734,  lon: 7.7521  },
    "Hauts-de-France":            { lat: 50.6292,  lon: 3.0573  },
    "Normandie":                  { lat: 49.4432,  lon: 1.0993  },
    "Nouvelle-Aquitaine":         { lat: 44.8378,  lon: -0.5792 },
    "Occitanie":                  { lat: 43.6047,  lon: 1.4442  },
    "Pays de la Loire":           { lat: 47.2184,  lon: -1.5536 },
    "Provence-Alpes-Côte d'Azur": { lat: 43.2965,  lon: 5.3698  },
}

export interface LoginRequest{
    mail:string,
    plain_password:string
}

export interface TokenResponse{
    token:string
}

export interface PredictionRequest{
    date:string,
    hour:number,
    temperatures:Record<string,number>,
    wind_speeds:Record<string,number>,
    humidities:Record<string,number>
}

export interface PredictionResponse{
    date:string
    hour:number
    power:number
}


export interface SegmentKpi {
    key: string | number
    n: number
    mae: number
    mape: number | null
    bias: number
}

export interface KpiPoint {
    datetime: string
    predicted: number // GW
    actual: number    // GW
}

export interface KpiReport {
    n: number
    mean_actual: number
    mean_predicted: number
    mae: number
    rmse: number
    mape: number | null
    wape: number | null
    smape: number | null
    nrmse: number | null
    bias: number
    median_ae: number
    p95_ae: number
    max_ae: number
    r2: number | null
    mase: number | null
    within_5_pct: number | null
    within_10_pct: number | null
    peak_days: number
    peak_mae: number | null
    peak_bias: number | null
    peak_hour_mae: number | null
    by_hour: SegmentKpi[]
    by_day: SegmentKpi[]
    weekday: SegmentKpi | null
    weekend: SegmentKpi | null
}

export const REGIONS: string[]=["Île-de-France",
                    "Auvergne-Rhône-Alpes",
                    "Bourgogne-Franche-Comté",
                    "Bretagne",
                    "Centre-Val de Loire",
                    "Corse",
                    "Grand Est",
                    "Hauts-de-France",
                    "Normandie",
                    "Nouvelle-Aquitaine",
                    "Occitanie",
                    "Pays de la Loire",
                    "Provence-Alpes-Côte d'Azur"]

// --- Benchmark des modèles ---------------------------------------------------

export type BenchmarkKpiKey = "mae" | "mae_debiased" | "rmse" | "mape" | "wape" | "bias" | "p95_ae" | "r2" | "mase"

export type BenchmarkRow = {
    model: string
    runs: number
    val_mae: number
    fit_seconds: number
    predict_seconds: number
    /** Présent dans le classement global : nombre d'années de test */
    folds?: number
    /** Présent dans le détail par année */
    test_year?: number
} & Record<BenchmarkKpiKey, number | null> & Record<`${BenchmarkKpiKey}_std`, number | null>

export interface BenchmarkResults {
    generated_at: string
    protocol: {
        scheme: string
        test_years: number[]
        seeds: number[]
        refit_on_train_and_val: boolean
        recency_half_life_years: number
        bias_correction?: { window_days: number; delay_days: number; min_days: number }
    }
    summary: BenchmarkRow[]
    by_fold: BenchmarkRow[]
}
