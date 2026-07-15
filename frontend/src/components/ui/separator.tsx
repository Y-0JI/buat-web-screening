interface SeparatorProps {
  className?: string;
}

export function Separator({ className = "" }: SeparatorProps) {
  return (
    <hr className={`border-zinc-800 ${className}`} />
  );
}
