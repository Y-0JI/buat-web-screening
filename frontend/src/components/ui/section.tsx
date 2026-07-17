"use client";

import { useState, useId, type ReactNode } from "react";

interface SectionProps {
  title: string;
  defaultOpen?: boolean;
  badge?: ReactNode;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Section({
  title,
  defaultOpen = true,
  badge,
  action,
  className = "",
  children,
}: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div className={`border border-zinc-800 rounded-xl overflow-hidden ${className}`}>
      <div className="flex items-stretch w-full">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-controls={contentId}
          className="flex-1 min-w-0 flex items-center justify-between px-4 py-3 bg-zinc-900 hover:bg-zinc-800/60 transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-sm font-semibold text-zinc-200 truncate">
              {title}
            </h3>
            {badge}
          </div>
          <svg
            className={`w-4 h-4 text-zinc-500 transition-transform duration-200 ${
              isOpen ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        {action && (
          <div className="flex items-center shrink-0 bg-zinc-900 border-l border-zinc-800 px-3">
            {action}
          </div>
        )}
      </div>
      {isOpen && (
        <div id={contentId} className="px-4 py-3">
          {children}
        </div>
      )}
    </div>
  );
}
