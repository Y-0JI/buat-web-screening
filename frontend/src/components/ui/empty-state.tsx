import { type ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}
    >
      <div className="text-zinc-600 mb-4">{icon}</div>
      <h3 className="text-zinc-300 font-medium mb-1">{title}</h3>
      {description && (
        <p className="text-zinc-500 text-sm max-w-sm">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
