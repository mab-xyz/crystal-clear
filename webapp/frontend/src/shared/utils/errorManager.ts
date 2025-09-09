import { useState } from "react";
import { useLocalAlert } from "@/shared/components/ui";

export type ErrorType = "form" | "api" | "network" | "runtime";

interface ErrorMap {
  [key: string]: string[]; // key is ErrorType
}

interface ErrorManager {
  errors: ErrorMap;
  setError: (type: ErrorType, message: string, showNow?: boolean) => void;
  clearError: (type: ErrorType) => void;
}

export const errorManager = (): ErrorManager => {
  const [errors, setErrors] = useState<ErrorMap>({});
  const { showLocalAlert } = useLocalAlert();

  const setError = (
    type: ErrorType,
    message: string,
    showNow: boolean = true,
  ) => {
    setErrors((prev) => {
      const updated = { ...prev };
      if (!updated[type]) updated[type] = [];
      updated[type].push(message);
      return updated;
    });
    if (showNow) showLocalAlert(message);
  };

  const clearError = (type: ErrorType) => {
    if (type) {
      setErrors((prev) => {
        const updated = { ...prev };
        delete updated[type];
        return updated;
      });
    } else {
      setErrors({});
    }
  };

  return {
    errors,
    setError,
    clearError,
  };
};
