interface ResultBannerProps {
    power: number
    date: string
    hour: number
    rteConsumptionMW?: number | null
}

export default function ResultBanner({ power, date, hour, rteConsumptionMW }: ResultBannerProps) {
    const fmtGW = (v: number) => v.toFixed(2) + " GW"
    const hourStr = String(hour).padStart(2, "0")

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-blue-600 text-white shadow-2xl z-50">
            <div className="max-w-4xl mx-auto px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-3">
                            <span className="text-2xl">⚡</span>
                            <div>
                                <p className="text-xs text-blue-200 uppercase tracking-wide">Prédiction ML</p>
                                <p className="text-3xl font-bold leading-tight">{fmtGW(power)}</p>
                            </div>
                        </div>

                        {rteConsumptionMW != null && (
                            <>
                                <div className="w-px h-10 bg-blue-500" />
                                <div>
                                    <p className="text-xs text-blue-200 uppercase tracking-wide">Réel RTE</p>
                                    <p className="text-3xl font-bold leading-tight">{fmtGW(rteConsumptionMW / 1000)}</p>
                                </div>
                            </>
                        )}
                    </div>

                    <div className="text-right text-blue-200 text-sm">
                        <p>{date}</p>
                        <p>{hourStr}h00</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
