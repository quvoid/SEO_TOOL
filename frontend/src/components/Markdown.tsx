// Renders AI narrative Markdown (##, **bold**, lists, `code`) as real HTML.
// Fixes the "junk symbols" that appeared when narratives were shown as raw text.
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children?: string }) {
  if (!children) return null;
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
