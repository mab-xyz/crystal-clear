interface HeaderProps {
  inputAddress: string;
  setInputAddress: (address: string) => void;
  fromBlock: string;
  setFromBlock: (block: string) => void;
  toBlock: string;
  setToBlock: (block: string) => void;
  handleSubmit: (event: React.FormEvent | any) => void;
}

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CustomButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {}
