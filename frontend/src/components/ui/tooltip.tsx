"use client";

import { useState, useRef, type ReactNode } from "react";

interface TooltipProps {
  content: string;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
}

export function Tooltip({
  content,
  children,
  side = "top",
  className = "",
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const show = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(true);
  };

  const hide = () => {
    timeoutRef.current = setTimeout(() => setIsVisible(false), 100);
  };

  const positionStyles: Record<string, string> = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div
      className={`relative inline-flex ${className}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {isVisible && (
        <div
          className={`absolute z-50 px-2 py-1 text-xs text-zinc-100 bg-zinc-800 border border-zinc-700 rounded-md whitespace-nowrap pointer-events-none shadow-md ${positionStyles[side]}`}
          role="tooltip"
        >
          {content}
        </div>
      )}
    </div>
  );
}
