// Lightweight custom dropdown — dark, flat menu (no OS white popup).
// Keyboard: Enter/ArrowDown opens, arrows move focus, Escape closes.
import { useEffect, useRef, useState } from "react";

export interface Option {
  value: string;
  label: string;
}

export function Select({
  value,
  options,
  onChange,
  placeholder = "Select…",
}: {
  value: string;
  options: Option[];
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const current = options.find((o) => o.value === value);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  // Focus the active (or first) item when the menu opens via keyboard/click.
  useEffect(() => {
    if (!open || !menuRef.current) return;
    const items = menuRef.current.querySelectorAll<HTMLButtonElement>(".select-item");
    const idx = Math.max(0, options.findIndex((o) => o.value === value));
    items[idx]?.focus();
  }, [open, options, value]);

  const close = (refocus = true) => {
    setOpen(false);
    if (refocus) btnRef.current?.focus();
  };

  const onMenuKey = (e: React.KeyboardEvent) => {
    const items = menuRef.current
      ? [...menuRef.current.querySelectorAll<HTMLButtonElement>(".select-item")]
      : [];
    const idx = items.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); items[Math.min(idx + 1, items.length - 1)]?.focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); items[Math.max(idx - 1, 0)]?.focus(); }
    else if (e.key === "Home") { e.preventDefault(); items[0]?.focus(); }
    else if (e.key === "End") { e.preventDefault(); items[items.length - 1]?.focus(); }
    else if (e.key === "Tab") { close(false); }
  };

  return (
    <div className="select" ref={ref}>
      <button
        type="button"
        className="select-btn"
        ref={btnRef}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); setOpen(true); }
          else if (open && e.key === "Escape") { e.preventDefault(); close(); }
        }}
      >
        <span className="select-val">{current?.label ?? placeholder}</span>
        <span className={`select-caret ${open ? "up" : ""}`} aria-hidden>
          ▾
        </span>
      </button>
      {open && (
        <div className="select-menu" role="listbox" ref={menuRef} onKeyDown={onMenuKey}>
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={o.value === value}
              className={`select-item ${o.value === value ? "active" : ""}`}
              onClick={() => {
                onChange(o.value);
                close();
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
