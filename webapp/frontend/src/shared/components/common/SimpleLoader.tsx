import { memo } from "react";

interface SimpleLoaderProps {
  size?: "sm" | "md" | "lg";
  message?: string;
  color?: string;
}

const SimpleLoader = memo(function SimpleLoader({
  size = "md",
  message,
  color = "#2b2b2b",
}: SimpleLoaderProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  const containerPadding = {
    sm: "p-2",
    md: "p-3",
    lg: "p-4",
  };

  return (
    <div
      className={`flex flex-col items-center justify-center ${containerPadding[size]}`}
    >
      {/* Simple spinning circle */}
      <div
        className={`${sizeClasses[size]} animate-spin rounded-full border-2 border-solid border-current border-r-transparent`}
        style={{ color }}
      >
        <span className="sr-only">Loading...</span>
      </div>

      {message && (
        <div className="mt-2 text-center text-sm text-gray-600">{message}</div>
      )}
    </div>
  );
});

export default SimpleLoader;
