import { Input } from "@/shared/components/ui/input";
import { isAddress } from "ethers";
import { cn } from "@/lib/utils";

interface AddressInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  showValidation?: boolean;
}

export function AddressInput({
  value,
  onChange,
  placeholder = "Enter contract address(0x...)",
  className = "",
  showValidation = true,
}: AddressInputProps) {
  console.log("value", value);
  console.log("onChange", onChange);

  const isValid = value === "" || isAddress(value);

  console.log("isValid", isValid);

  return (
    <div className="relative w-full text-xs">
      <Input
        type="text"
        value={value}
        onChange={(e) => {
          const val = e.target.value;
          onChange(val);
        }}
        placeholder={placeholder}
        className={cn(
          "!pr-8 !pl-4", // force padding-right for clear button clearance, force padding-left for placeholder text
          !isValid &&
            showValidation &&
            "border-destructive ring-destructive/20",
          className,
        )}
      />

      {/* Clear button */}
      {value && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onChange("");
          }}
          className="text-muted-foreground hover:text-foreground absolute top-1/2 right-2 z-10 flex h-4 w-4 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full transition-colors"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      )}
    </div>
  );
}
