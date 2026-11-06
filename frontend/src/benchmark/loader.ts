import { fetchBenchmark } from "../services/api"
import type { BenchmarkResults } from "../types/api"
import { parseBenchmark } from "./schema"

/** Charge les résultats du benchmark depuis l'API et les valide avant tout affichage. */
export async function loadBenchmark(token: string): Promise<BenchmarkResults> {
    return parseBenchmark(await fetchBenchmark(token))
}
