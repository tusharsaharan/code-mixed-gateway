import type { ReactNode } from "react";

export function GradientText({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`bg-gradient-to-r from-primary via-accent-foreground to-primary bg-[length:200%_100%] bg-clip-text text-transparent [animation:gradient-pan_7s_ease_infinite] ${
        className ?? ""
      }`}
    >
      {children}
    </span>
  );
}
