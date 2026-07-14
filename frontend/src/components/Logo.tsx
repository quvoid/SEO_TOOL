// Schbang brand mark — a clean, flat, multi-colour hash + wordmark.
// (Simplified geometric take on the official logo; swap in the official SVG/PNG
//  at src/assets/ later if you want a pixel-perfect asset.)
export function SchbangMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-label="Schbang" role="img">
      <g transform="skewX(-11)" strokeLinecap="round" strokeWidth="12" fill="none">
        <line x1="42" y1="16" x2="36" y2="84" stroke="#2BB9EE" />
        <line x1="70" y1="16" x2="64" y2="84" stroke="#7CC243" />
        <line x1="18" y1="40" x2="84" y2="40" stroke="#F15A29" />
        <line x1="14" y1="66" x2="80" y2="66" stroke="#FFD21E" />
      </g>
      <circle cx="72" cy="74" r="8" fill="#EC6FA9" />
    </svg>
  );
}

export function SchbangLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo">
      <SchbangMark size={compact ? 26 : 30} />
      {!compact && (
        <span className="logo-word">
          Schbang<span className="logo-dot">.</span>
        </span>
      )}
    </div>
  );
}
