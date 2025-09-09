// Custom hook for URL state management
// Maintains analysis parameters in URL for better UX and shareable links

import { useState, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router";
import {
  validateEthereumAddress,
  validateBlockNumber,
} from "@/shared/utils/validation";

interface UrlStateParams {
  address?: string;
  fromBlock?: string;
  toBlock?: string;
  tab?: string;
}

interface UseUrlStateReturn {
  // Current state
  urlParams: UrlStateParams;

  // Actions
  updateUrl: (params: Partial<UrlStateParams>) => void;
  setAddress: (address: string) => void;
  setBlockRange: (from: string, to: string) => void;
  setTab: (tab: string) => void;

  // Utilities
  isValidState: boolean;
  getShareableUrl: () => string;
  resetUrl: () => void;
}

export function useUrlState(): UseUrlStateReturn {
  const navigate = useNavigate();
  const location = useLocation();

  // Parse current URL parameters
  const parseUrlParams = useCallback((): UrlStateParams => {
    const searchParams = new URLSearchParams(location.search);

    const params: UrlStateParams = {};

    const address = searchParams.get("address");
    if (address) params.address = address;

    const fromBlock = searchParams.get("from_block");
    if (fromBlock) params.fromBlock = fromBlock;

    const toBlock = searchParams.get("to_block");
    if (toBlock) params.toBlock = toBlock;

    const tab = searchParams.get("tab");
    if (tab) params.tab = tab;

    return params;
  }, [location.search]);

  const [urlParams, setUrlParams] = useState<UrlStateParams>(parseUrlParams);

  // Update local state when URL changes (browser back/forward)
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);

    const newParams: UrlStateParams = {};

    const address = searchParams.get("address");
    if (address) newParams.address = address;

    const fromBlock = searchParams.get("from_block");
    if (fromBlock) newParams.fromBlock = fromBlock;

    const toBlock = searchParams.get("to_block");
    if (toBlock) newParams.toBlock = toBlock;

    const tab = searchParams.get("tab");
    if (tab) newParams.tab = tab;

    setUrlParams(newParams);
  }, [location.search]);

  // Validate current state
  const isValidState = useCallback(() => {
    if (!urlParams.address) return false;

    const addressValidation = validateEthereumAddress(urlParams.address);
    if (!addressValidation.isValid) return false;

    if (urlParams.fromBlock) {
      const fromValidation = validateBlockNumber(urlParams.fromBlock);
      if (!fromValidation.isValid) return false;
    }

    if (urlParams.toBlock) {
      const toValidation = validateBlockNumber(urlParams.toBlock);
      if (!toValidation.isValid) return false;
    }

    return true;
  }, [urlParams]);

  // Update URL with new parameters
  const updateUrl = useCallback(
    (newParams: Partial<UrlStateParams>) => {
      const searchParams = new URLSearchParams(location.search);

      // Update or remove parameters
      Object.entries(newParams).forEach(([key, value]) => {
        if (value && value.trim()) {
          searchParams.set(key, value);
        } else {
          searchParams.delete(key);
        }
      });

      // Special handling for block parameters - if one is provided, ensure both are present
      if (newParams.fromBlock || newParams.toBlock) {
        const from = newParams.fromBlock || urlParams.fromBlock;
        const to = newParams.toBlock || urlParams.toBlock;

        if (from && to) {
          searchParams.set("from_block", from);
          searchParams.set("to_block", to);
        }
      }

      const newSearch = searchParams.toString();
      const newUrl = `${location.pathname}${newSearch ? `?${newSearch}` : ""}`;

      // Update URL without page reload
      navigate(newUrl, { replace: true });
    },
    [location, navigate, urlParams],
  );

  // Convenience methods
  const setAddress = useCallback(
    (address: string) => {
      updateUrl({ address });
    },
    [updateUrl],
  );

  const setBlockRange = useCallback(
    (fromBlock: string, toBlock: string) => {
      updateUrl({ fromBlock, toBlock });
    },
    [updateUrl],
  );

  const setTab = useCallback(
    (tab: string) => {
      updateUrl({ tab });
    },
    [updateUrl],
  );

  // Get shareable URL for current analysis
  const getShareableUrl = useCallback(() => {
    const baseUrl = window.location.origin;
    const searchParams = new URLSearchParams();

    if (urlParams.address) searchParams.set("address", urlParams.address);
    if (urlParams.fromBlock)
      searchParams.set("from_block", urlParams.fromBlock);
    if (urlParams.toBlock) searchParams.set("to_block", urlParams.toBlock);
    if (urlParams.tab) searchParams.set("tab", urlParams.tab);

    return `${baseUrl}/graph?${searchParams.toString()}`;
  }, [urlParams]);

  // Reset URL to clean state
  const resetUrl = useCallback(() => {
    navigate(location.pathname, { replace: true });
  }, [navigate, location.pathname]);

  return {
    urlParams,
    updateUrl,
    setAddress,
    setBlockRange,
    setTab,
    isValidState: isValidState(),
    getShareableUrl,
    resetUrl,
  };
}
