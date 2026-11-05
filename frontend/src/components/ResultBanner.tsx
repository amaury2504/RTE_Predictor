interface ResultBannerProps {
    power: number
    date: string
    hour: number
    rteConsumptionMW?: number | null
}

export default function ResultBanner({ power, date, hour, rteConsumptionMW }: ResultBannerProps) {
    const fmtGW = (v: number) => v.toFixed(2)
    const hourStr = String(hour).padStart(2, "0")

    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-neon/40 bg-surface/90 shadow-[0_-8px_40px_rgba(30,160,255,0.12)] backdrop-blur">
            <div className="mx-auto max-w-4xl px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-8">
                        <div>
                            <p className="text-xs font-medium uppercase tracking-widest text-muted">Prédiction ML</p>
                            <p className="text-3xl font-semibold leading-tight text-neon-soft tabular-nums">
                                {fmtGW(power)} <span className="text-base font-medium text-muted">GW</span>
                            </p>
                        </div>

                        {rteConsumptionMW != null && (
                            <>
                                <div className="h-10 w-px bg-line" />
                                <div>
                                    <p className="text-xs font-medium uppercase tracking-widest text-muted">Réel RTE</p>
                                    <p className="text-3xl font-semibold leading-tight text-signal tabular-nums">
                                        {fmtGW(rteConsumptionMW / 1000)} <span className="text-base font-medium text-muted">GW</span>
                                    </p>
                                </div>
                            </>
                        )}
                    </div>

                    <div className="text-right text-sm text-muted tabular-nums">
                        <p>{date}</p>
                        <p>{hourStr}h00</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
