import { useState } from "react"
import {
    ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from "recharts"
import KpiCard from "../KpiCard"
import type { BenchmarkResults, BenchmarkRow } from "../../types/api"
import {
    describeModel, formatKpi, KIND_COLOR, KIND_LABEL, KIND_ORDER, KPI_DEFS, ESSENTIAL_MODELS, score,
} from "../../lib/benchmarkModels"
import type { KpiDef } from "../../lib/benchmarkModels"
import { num } from "../../lib/format"
import { AXIS_TICK, CARD, MUTED_SERIES, stdHint, TOOLTIP_STYLE } from "./chartStyle"
import { KindBadge, KindLegend } from "./shared"

type View = "model" | "compare"
type Period = "mean" | number

// --- Vue « par modèle » --------------------------------------------------------

function ModelView({ results, ranking }: { results: BenchmarkResults; ranking: string[] }) {
    const [model, setModel] = useState(ranking.includes("lightgbm") ? "lightgbm" : ranking[0])
    const info = describeModel(model)
    const summary = results.summary.find(r => r.model === model)
    const folds = results.by_fold.filter(r => r.model === model).sort((a, b) => (a.test_year ?? 0) - (b.test_year ?? 0))
    const rank = ranking.indexOf(model) + 1

    if (!summary) return null

    const def = (key: string) => KPI_DEFS.find(d => d.key === key) as KpiDef
    const card = (key: string, tone?: "good" | "warn") => {
        const d = def(key)
        return { label: d.label, value: formatKpi(d, summary[d.key]), hint: stdHint(summary, d, d.hint), tone }
    }
    const bias = summary.bias ?? 0
    const biasCard = { ...card("bias"), tone: Math.abs(bias) > 1 ? ("warn" as const) : undefined }

    const chartData = folds.map(f => ({ year: String(f.test_year), mae: f.mae, mae_debiased: f.mae_debiased }))

    return (
        <div className="space-y-8">
            <div className={`${CARD} p-6`}>
                <label htmlFor="model-select" className="text-xs font-medium uppercase tracking-widest text-muted">
                    Modèle
                </label>
                <select
                    id="model-select"
                    value={model}
                    onChange={e => setModel(e.target.value)}
                    className="mt-2 w-full rounded-lg border border-line bg-raised px-3 py-2.5 text-sm text-ink focus:border-neon/60 focus:outline-none"
                >
                    {KIND_ORDER.map(kind => (
                        <optgroup key={kind} label={KIND_LABEL[kind]}>
                            {ranking.filter(m => describeModel(m).kind === kind).map(m => (
                                <option key={m} value={m}>
                                    {describeModel(m).label} ({m})
                                </option>
                            ))}
                        </optgroup>
                    ))}
                </select>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                    <h2 className="text-xl font-semibold text-ink">{info.label}</h2>
                    <KindBadge kind={info.kind} />
                    <span className="text-xs text-faint">
                        {rank}<sup>e</sup> sur {ranking.length} par MAE · {summary.runs} exécution{summary.runs > 1 ? "s" : ""}
                    </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted">{info.description}</p>
            </div>

            <section>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-neon-soft">
                    Moyenne sur {folds.length} année{folds.length > 1 ? "s" : ""} de test
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <KpiCard {...card("mae")} />
                    <KpiCard {...card("mae_debiased")} />
                    <KpiCard {...card("rmse")} />
                    <KpiCard {...card("mape")} />
                    <KpiCard {...biasCard} />
                    <KpiCard {...card("p95_ae")} />
                    <KpiCard {...card("r2")} />
                    <KpiCard {...card("mase")} />
                </div>
            </section>

            <div className={`${CARD} p-6`}>
                <h2 className="mb-1 text-lg font-semibold text-ink">Erreur selon l'année de test</h2>
                <p className="mb-6 text-sm text-faint">
                    La MAE centrée est l'erreur une fois le biais retiré. L'écart entre les deux barres est le décalage de niveau.
                </p>
                <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#172640" vertical={false} />
                        <XAxis dataKey="year" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} unit=" GW" />
                        <Tooltip
                            formatter={(value, name) => [
                                typeof value === "number" ? `${num(value, 2)} GW` : "—",
                                name === "mae" ? "MAE" : "MAE centrée",
                            ]}
                            contentStyle={TOOLTIP_STYLE}
                            labelStyle={{ color: "#8a9bb8" }}
                            cursor={{ fill: "#1ea0ff10" }}
                        />
                        <Legend
                            formatter={name => (name === "mae" ? "MAE" : "MAE centrée")}
                            wrapperStyle={{ fontSize: "13px", color: "#8a9bb8" }}
                        />
                        <Bar dataKey="mae" name="mae" fill={KIND_COLOR[info.kind]} radius={[4, 4, 0, 0]} maxBarSize={44} />
                        <Bar dataKey="mae_debiased" name="mae_debiased" fill={MUTED_SERIES} radius={[4, 4, 0, 0]} maxBarSize={44} />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            <div className={`${CARD} overflow-x-auto`}>
                <h2 className="px-6 pt-6 text-lg font-semibold text-ink">Détail par année de test</h2>
                <table className="mt-4 w-full text-sm">
                    <thead>
                        <tr className="border-b border-line text-left text-xs uppercase tracking-widest text-muted">
                            <th className="px-6 py-3 font-medium">Année</th>
                            {KPI_DEFS.map(d => <th key={d.key} className="whitespace-nowrap px-3 py-3 text-right font-medium">{d.label}</th>)}
                        </tr>
                    </thead>
                    <tbody className="tabular-nums">
                        {folds.map(f => (
                            <tr key={f.test_year} className="border-b border-line/60 last:border-0">
                                <td className="px-6 py-3 text-ink">{f.test_year}</td>
                                {KPI_DEFS.map(d => <td key={d.key} className="whitespace-nowrap px-3 py-3 text-right text-muted">{formatKpi(d, f[d.key])}</td>)}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// --- Vue « comparaison » -------------------------------------------------------

function CompareView({ results, ranking }: { results: BenchmarkResults; ranking: string[] }) {
    const [metric, setMetric] = useState<KpiDef>(KPI_DEFS[0])
    const [period, setPeriod] = useState<Period>("mean")
    const [selected, setSelected] = useState<Set<string>>(
        () => new Set(ESSENTIAL_MODELS.filter(m => ranking.includes(m))),
    )

    const years = results.protocol.test_years
    const rows: BenchmarkRow[] = period === "mean"
        ? results.summary
        : results.by_fold.filter(r => r.test_year === period)

    const chosen = rows.filter(r => selected.has(r.model))
    const sorted = [...chosen].sort((a, b) => score(metric, a[metric.key]) - score(metric, b[metric.key]))
    const chartData = sorted.map(r => ({
        name: describeModel(r.model).label,
        model: r.model,
        kind: describeModel(r.model).kind,
        value: r[metric.key],
    }))

    const toggle = (model: string) =>
        setSelected(prev => {
            const next = new Set(prev)
            if (next.has(model)) next.delete(model)
            else next.add(model)
            return next
        })

    const best = (def: KpiDef): number | null => {
        if (chosen.length === 0) return null
        return chosen.reduce((acc, r) => (score(def, r[def.key]) < score(def, acc) ? r[def.key] : acc), chosen[0][def.key])
    }

    const chip = (active: boolean) =>
        `rounded-full border px-3 py-1.5 text-xs transition-colors ${active
            ? "border-neon/60 bg-neon/10 text-neon-soft"
            : "border-line text-muted hover:border-neon/30 hover:text-ink"}`

    return (
        <div className="space-y-8">
            <div className={`${CARD} space-y-6 p-6`}>
                <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">Indicateur</p>
                    <div className="flex flex-wrap gap-2">
                        {KPI_DEFS.map(d => (
                            <button key={d.key} onClick={() => setMetric(d)} className={chip(d.key === metric.key)}>
                                {d.label}
                            </button>
                        ))}
                    </div>
                    <p className="mt-2 text-xs text-faint">{metric.hint}</p>
                </div>

                <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">Période</p>
                    <div className="flex flex-wrap gap-2">
                        <button onClick={() => setPeriod("mean")} className={chip(period === "mean")}>
                            Moyenne {years[0]}-{years[years.length - 1]}
                        </button>
                        {years.map(y => (
                            <button key={y} onClick={() => setPeriod(y)} className={chip(period === y)}>{y}</button>
                        ))}
                    </div>
                </div>

                <div>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-medium uppercase tracking-widest text-muted">
                            Modèles ({selected.size} sur {ranking.length})
                        </p>
                        <div className="flex gap-3 text-xs">
                            <button className="text-muted hover:text-ink" onClick={() => setSelected(new Set(ranking))}>Tout</button>
                            <button
                                className="text-muted hover:text-ink"
                                onClick={() => setSelected(new Set(ESSENTIAL_MODELS.filter(m => ranking.includes(m))))}
                            >
                                Essentiel
                            </button>
                            <button className="text-muted hover:text-ink" onClick={() => setSelected(new Set())}>Aucun</button>
                        </div>
                    </div>
                    {KIND_ORDER.map(kind => {
                        const models = ranking.filter(m => describeModel(m).kind === kind)
                        if (models.length === 0) return null
                        return (
                            <div key={kind} className="mt-3">
                                <p className="mb-1.5 text-xs text-faint">
                                    {KIND_LABEL[kind]}
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    {models.map(m => (
                                        <button
                                            key={m}
                                            onClick={() => toggle(m)}
                                            aria-pressed={selected.has(m)}
                                            title={m}
                                            className={chip(selected.has(m))}
                                        >
                                            {describeModel(m).label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {chosen.length === 0 ? (
                <div className={`${CARD} p-10 text-center text-sm text-muted`}>Sélectionne au moins un modèle.</div>
            ) : (
                <>
                    <div className={`${CARD} p-6`}>
                        <h2 className="mb-1 text-lg font-semibold text-ink">
                            {metric.label} par modèle
                            {period === "mean" ? "" : ` · test ${period}`}
                        </h2>
                        <p className="mb-4 text-sm text-faint">
                            {metric.better === "zero"
                                ? "Triés du plus proche de zéro au plus éloigné."
                                : metric.better === "higher" ? "Triés du plus haut au plus bas." : "Triés du plus bas au plus haut : le meilleur est en haut."}
                        </p>
                        <div className="mb-4"><KindLegend /></div>
                        <ResponsiveContainer width="100%" height={Math.max(160, chartData.length * 42 + 50)}>
                            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#172640" horizontal={false} />
                                <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} unit={metric.unit} />
                                <YAxis type="category" dataKey="name" width={190} tick={{ ...AXIS_TICK, fill: "#e8eef8" }} axisLine={false} tickLine={false} />
                                {metric.better === "zero" && <ReferenceLine x={0} stroke="#5b6c8a" />}
                                <Tooltip
                                    formatter={value => [typeof value === "number" ? formatKpi(metric, value) : "—", metric.label]}
                                    contentStyle={TOOLTIP_STYLE}
                                    labelStyle={{ color: "#8a9bb8" }}
                                    cursor={{ fill: "#1ea0ff10" }}
                                />
                                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
                                    {chartData.map(d => <Cell key={d.model} fill={KIND_COLOR[d.kind]} />)}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className={`${CARD} overflow-x-auto`}>
                        <h2 className="px-6 pt-6 text-lg font-semibold text-ink">Tous les indicateurs</h2>
                        <p className="px-6 pt-1 text-sm text-faint">
                            En gras : meilleure valeur parmi les modèles sélectionnés. Les références utilisent la consommation
                            passée ou les prévisions de RTE : elles ne sont pas comparables au sens strict aux modèles de la piste A.
                        </p>
                        <table className="mt-4 w-full text-sm">
                            <thead>
                                <tr className="border-b border-line text-left text-xs uppercase tracking-widest text-muted">
                                    <th className="px-6 py-3 font-medium">Modèle</th>
                                    {KPI_DEFS.map(d => <th key={d.key} className="whitespace-nowrap px-3 py-3 text-right font-medium">{d.label}</th>)}
                                </tr>
                            </thead>
                            <tbody className="tabular-nums">
                                {sorted.map(r => {
                                    const info = describeModel(r.model)
                                    return (
                                        <tr key={r.model} className="border-b border-line/60 last:border-0">
                                            <td className="whitespace-nowrap px-6 py-3 text-ink">
                                                {info.label}
                                            </td>
                                            {KPI_DEFS.map(d => {
                                                const isBest = best(d) === r[d.key] && r[d.key] != null && chosen.length > 1
                                                return (
                                                    <td key={d.key} className={`whitespace-nowrap px-3 py-3 text-right ${isBest ? "font-semibold text-neon-soft" : "text-muted"}`}>
                                                        {formatKpi(d, r[d.key])}
                                                    </td>
                                                )
                                            })}
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}

// --- Bloc « statistiques avancées » ---------------------------------------------

/** Tout le détail chiffré : un modèle à la fois, ou plusieurs modèles comparés indicateur par indicateur. */
export default function AdvancedStats({ results, ranking }: { results: BenchmarkResults; ranking: string[] }) {
    const [view, setView] = useState<View>("model")
    const tab = (active: boolean) =>
        `flex-1 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${active
            ? "bg-neon/15 text-neon-soft shadow-glow"
            : "text-muted hover:text-ink"}`
    return (
        <div className="space-y-6">
            <div className={`${CARD} flex gap-1 p-1`} role="tablist">
                <button role="tab" aria-selected={view === "model"} onClick={() => setView("model")} className={tab(view === "model")}>
                    KPI par modèle
                </button>
                <button role="tab" aria-selected={view === "compare"} onClick={() => setView("compare")} className={tab(view === "compare")}>
                    KPI comparés
                </button>
            </div>
            {view === "model"
                ? <ModelView results={results} ranking={ranking} />
                : <CompareView results={results} ranking={ranking} />}
        </div>
    )
}
