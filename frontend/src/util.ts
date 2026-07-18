// Strip the "Module N — " / "Module 6b: " prefix from AI-generated titles.
export function cleanTitle(t?: string, fallback = ""): string {
  if (!t) return fallback;
  return t.replace(/^\s*Module\s+\d+[a-z]?\s*[—:\-]\s*/i, "").trim() || fallback;
}
