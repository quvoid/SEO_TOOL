// Schbang brand mark. Prefers /schbang-logo.png (drop the official PNG into
// frontend/public/schbang-logo.png). Falls back to a geometric SVG hash if the
// image isn't present.
import { useState } from "react";

function SchbangMark({ size = 34 }: { size?: number }) {
  const [imgOk, setImgOk] = useState(true);
  if (imgOk) {
    return (
      <img
        src="/schbang-logo.png"
        alt="Schbang"
        width={size}
        height={size}
        style={{ display: "block", objectFit: "contain", borderRadius: 6 }}
        onError={() => setImgOk(false)}
      />
    );
  }
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

export function SchbangLogo({ size = 34, showWord = true }: { size?: number; showWord?: boolean }) {
  return (
    <div className="logo">
      <SchbangMark size={size} />
      {showWord && (
        <span className="logo-word">
          Schbang<span className="logo-dot">.</span>
        </span>
      )}
    </div>
  );
}
