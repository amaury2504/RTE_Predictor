import { KIND_COLOR, KIND_LABEL, KIND_ORDER } from "../../lib/benchmarkModels"
import type { ModelKind } from "../../lib/benchmarkModels"

export function KindBadge({ kind }: { kind: ModelKind }) {
    return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-0.5 text-xs text-muted">
            {KIND_LABEL[kind]}
        </span>
    )
}

export function KindLegend() {
    return (
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
            {KIND_ORDER.map(kind => (
                <span key={kind} className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: KIND_COLOR[kind] }} />
                    {KIND_LABEL[kind]}
                </span>
            ))}
        </div>
    )
}
