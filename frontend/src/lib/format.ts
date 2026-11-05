const nf = (digits: number) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits })

export const num = (v: number | null, digits = 2, unit = "") => (v == null ? "—" : `${nf(digits).format(v)}${unit}`)
export const pct = (v: number | null, digits = 1) => num(v, digits, " %")
export const signed = (v: number | null, digits = 2, unit = "") =>
    v == null ? "—" : `${v > 0 ? "+" : ""}${nf(digits).format(v)}${unit}`
