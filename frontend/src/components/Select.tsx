// Lightweight custom dropdown — dark, flat menu (no OS white popup).
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
  const current = options.find((o) => o.value === value);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="select" ref={ref}>
      <button type="button" className="select-btn" onClick={() => setOpen((o) => !o)}>
        <span className="select-val">{current?.label ?? placeholder}</span>
        <span className={`select-caret ${open ? "up" : ""}`} aria-hidden>
          ▾
        </span>
      </button>
      {open && (
        <div className="select-menu" role="listbox">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={o.value === value}
              className={`select-item ${o.value === value ? "active" : ""}`}
              onClick={() => {
                onChange(o.value);
                setOpen(false);
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
