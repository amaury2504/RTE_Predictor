export default function LogoMark({ size = 28 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <rect x="1" y="1" width="26" height="26" rx="7" fill="#0e1a2e" stroke="#1ea0ff" strokeOpacity="0.6" />
            <path
                d="M5 18 L10 12 L14 15 L18 8 L23 13"
                stroke="#5cc0ff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}
