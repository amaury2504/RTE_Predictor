import type { PredictionRequest, PredictionResponse, RegionWeather, KpiPoint, KpiReport, BenchmarkResults } from "../types/api"
import { REGIONS, REGION_COORDS } from "../types/api"

// Adresse de l'API : VITE_API_URL à la construction (ex. "/api" derrière le reverse proxy), localhost en développement
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export const register = async (mail: string, password: string): Promise<void> => {
    const response = await fetch(`${BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mail, plain_password: password })
    })
    if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail)
    }
}

export const login = async (mail: string, password: string): Promise<string> => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mail, plain_password: password })
    })
    if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail)
    }
    const data = await response.json()
    return data.token
}

// Mode démo : obtient un token de profil invité, sans identifiant ni mot de passe
export const loginAsGuest = async (): Promise<string> => {
    const response = await fetch(`${BASE_URL}/auth/guest`, { method: "POST" })
    if (!response.ok) {
        throw new Error("Impossible de continuer en profil invité")
    }
    const data = await response.json()
    return data.token
}

const DEFAULT_WEATHER: RegionWeather = { temperature: 10, wind_speed: 20, humidity: 70 }

export const fetchCurrentWeather = async (): Promise<Record<string, RegionWeather>> => {
    const settled = await Promise.allSettled(
        REGIONS.map(async region => {
            const { lat, lon } = REGION_COORDS[region]
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,wind_speed_10m,relative_humidity_2m&wind_speed_unit=kmh`
            const res = await fetch(url)
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const data = await res.json()
            return {
                region,
                weather: {
                    temperature: Math.round(data.current.temperature_2m),
                    wind_speed: Math.round(data.current.wind_speed_10m),
                    humidity: Math.round(data.current.relative_humidity_2m),
                } satisfies RegionWeather,
            }
        })
    )
    return Object.fromEntries(
        settled.map((result, i) => [
            REGIONS[i],
            result.status === "fulfilled" ? result.value.weather : DEFAULT_WEATHER,
        ])
    )
}

// Returns { region: { "2026-05-27T14:00": {temperature, wind_speed, humidity} } }
export const fetchWeekWeather = async (): Promise<Record<string, Record<string, RegionWeather>>> => {
    const settled = await Promise.allSettled(
        REGIONS.map(async region => {
            const { lat, lon } = REGION_COORDS[region]
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,wind_speed_10m,relative_humidity_2m&past_days=8&forecast_days=0&wind_speed_unit=kmh&timezone=Europe%2FParis`
            const res = await fetch(url)
            if (!res.ok) throw new Error()
            const data = await res.json()
            const times: string[] = data.hourly.time
            const temps: number[] = data.hourly.temperature_2m
            const winds: number[] = data.hourly.wind_speed_10m
            const humids: number[] = data.hourly.relative_humidity_2m
            const map: Record<string, RegionWeather> = {}
            times.forEach((t, i) => {
                map[t] = {
                    temperature: Math.round(temps[i] ?? 10),
                    wind_speed: Math.round(winds[i] ?? 20),
                    humidity: Math.round(humids[i] ?? 70),
                }
            })
            return { region, map }
        })
    )
    return Object.fromEntries(
        settled.map((result, i) => [
            REGIONS[i],
            result.status === "fulfilled" ? result.value.map : {},
        ])
    )
}

export const fetchRTENow = async (date: string, hour: number, token: string): Promise<number> => {
    const res = await fetch(`${BASE_URL}/prediction/rte-now?date=${encodeURIComponent(date)}&hour=${hour}`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail ?? "RTE indisponible")
    }
    const data = await res.json()
    return data.consumption_mw
}

export const predict = async (data: PredictionRequest, token: string): Promise<PredictionResponse> => {
    const response = await fetch(`${BASE_URL}/prediction/predict`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(data)
    })
    if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail)
    }
    return await response.json()
}

export interface BatchItem {
    date: string
    hour: number
    temperatures: Record<string, number>
    wind_speeds: Record<string, number>
    humidities: Record<string, number>
}

export const batchPredict = async (items: BatchItem[], token: string): Promise<PredictionResponse[]> => {
    const res = await fetch(`${BASE_URL}/prediction/batch-predict`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ items }),
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail ?? "Erreur batch predict")
    }
    const data = await res.json()
    return data.items
}

export const fetchKpis = async (points: KpiPoint[], token: string): Promise<KpiReport> => {
    const res = await fetch(`${BASE_URL}/prediction/kpis`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ points }),
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(typeof err.detail === "string" ? err.detail : "Erreur de calcul des KPI")
    }
    return await res.json()
}

export const fetchRTEWeek =async (token: string): Promise<Record<string, number>> => {
    const res = await fetch(`${BASE_URL}/prediction/rte-week`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail ?? "Données RTE semaine indisponibles")
    }
    const data = await res.json()
    return Object.fromEntries(
        (data.data as Array<{ datetime: string; consumption: number }>).map(r => [r.datetime, r.consumption])
    )
}

export const fetchBenchmark = async (token: string): Promise<BenchmarkResults> => {
    const res = await fetch(`${BASE_URL}/prediction/benchmark`, {
        headers: { "Authorization": `Bearer ${token}` },
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(typeof err.detail === "string" ? err.detail : `Résultats indisponibles (HTTP ${res.status})`)
    }
    return await res.json()
}
