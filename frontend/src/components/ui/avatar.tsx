interface AvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeStyles = {
  sm: "w-6 h-6 text-[10px]",
  md: "w-8 h-8 text-xs",
  lg: "w-10 h-10 text-sm",
};

export function Avatar({ name, size = "md", className = "" }: AvatarProps) {
  const initial = name.charAt(0).toUpperCase();

  return (
    <div
      className={`inline-flex items-center justify-center rounded-full bg-blue-600 text-white font-medium ${sizeStyles[size]} ${className}`}
    >
      {initial}
    </div>
  );
}
