export type Tone = "default" | "good" | "warn"

export interface KpiItem {
    label: string
    value: string
    hint: string
    tone?: Tone
}

const TONE_CLASS: Record<Tone, string> = {
    default: "text-ink",
    good: "text-emerald-400",
    warn: "text-amber-400",
}

export default function KpiCard({ label, value, hint, tone = "default" }: KpiItem) {
    return (
        <div className="rounded-xl border border-line bg-surface p-5 shadow-card">
            <p className="text-xs font-medium uppercase tracking-widest text-muted">{label}</p>
            <p className={`mt-1.5 text-2xl font-semibold tabular-nums ${TONE_CLASS[tone]}`}>{value}</p>
            <p className="mt-1.5 text-xs leading-snug text-faint">{hint}</p>
        </div>
    )
}
