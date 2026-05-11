import type { ReactNode } from "react";

import { cardClass, subCardClass } from "@/lib/ui";

type CardProps = {
  children: ReactNode;
  className?: string;
  variant?: "default" | "elevated" | "sub";
  as?: "div" | "section" | "aside" | "article";
};

export default function Card({
  children,
  className,
  variant = "default",
  as: Element = "div",
}: CardProps) {
  const base =
    variant === "sub"
      ? subCardClass
      : variant === "elevated"
        ? `${cardClass} bg-panel-2`
        : cardClass;

  return (
    <Element className={[base, className].filter(Boolean).join(" ")}>
      {children}
    </Element>
  );
}
