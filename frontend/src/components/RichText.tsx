import type { ReactNode } from "react";

export function RichText({ text, className = "" }: { text: string; className?: string }) {
  const parts = (text ?? "").split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  const nodes: ReactNode[] = parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return <span key={index}>{part}</span>;
  });
  return <span className={className}>{nodes}</span>;
}

