import type { BenchmarkRow } from "../../types/api"
import { formatKpi } from "../../lib/benchmarkModels"
import type { KpiDef } from "../../lib/benchmarkModels"

export const AXIS_TICK = { fontSize: 12, fill: "#8a9bb8" }
export const TOOLTIP_STYLE = {
    background: "#0a1322",
    borderRadius: "10px",
    border: "1px solid #1ea0ff55",
    fontSize: "13px",
    color: "#e8eef8",
}
export const CARD = "rounded-xl border border-line bg-surface shadow-card"
export const MUTED_SERIES = "#8a9bb8"

export function stdHint(row: BenchmarkRow, def: KpiDef, base: string): string {
    const std = row[`${def.key}_std`]
    return std ? `${base} · ± ${formatKpi({ ...def, signed: false, unit: def.unit }, std)} entre années` : base
}
