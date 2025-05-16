import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CustomButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export function OrangeButton({ className, ...props }: CustomButtonProps) {
  return (
    <Button
      className={cn(
        "inline-flex items-center justify-center border rounded-sm",
        "whitespace-nowrap text-sm font-medium",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0",
        "disabled:pointer-events-none disabled:opacity-50",
        "bg-orange-300 text-orange-950 border-orange-950",
        "shadow-btn hover:shadow-btn-hover active:shadow-btn-active",
        "transition-all hover:bg-orange-400 active:bg-orange-400",
        "px-3 py-1.5 h-10",
        className,
      )}
      {...props}
    />
  );
}
