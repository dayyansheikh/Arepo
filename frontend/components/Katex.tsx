import katex from "katex";
import "katex/dist/katex.min.css";

/**
 * Server-rendered KaTeX. Renders to an HTML string at build/request time so no
 * KaTeX runtime is shipped to the client. Use `display` for block equations
 * (centred, own line) and inline for terms sitting in prose.
 */
export function Katex({
  tex,
  display = false,
  ariaLabel,
}: {
  tex: string;
  display?: boolean;
  ariaLabel?: string;
}) {
  const html = katex.renderToString(tex, {
    displayMode: display,
    throwOnError: false,
    strict: "ignore",
    output: "htmlAndMathml",
  });

  if (display) {
    return (
      <div
        className="katex-block"
        role="math"
        aria-label={ariaLabel ?? tex}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  return (
    <span
      role="math"
      aria-label={ariaLabel ?? tex}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
