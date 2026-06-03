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