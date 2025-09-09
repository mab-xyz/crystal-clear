// Custom hook for graph analysis state management
// Reduces prop drilling and centralizes graph-related logic

import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalAlert } from "@/shared/components/ui";
import { fetchGraphData } from "@/utils/graphFetcher";
import { getApiAvailability } from "@/utils/queries";
import type { GraphData, Node } from "@/types/graph";
import { API } from "@/constants";

interface UseGraphAnalysisParams {
  inputAddress: string;
  fromBlock: string;
  toBlock: string;
  autoExecute?: boolean; // Add flag to control auto-execution
}

interface UseGraphAnalysisReturn {
  // Data
  jsonData: GraphData | null;
  apiAvailability: boolean | undefined;
  loading: boolean;
  error: Error | null;

  // Node selection state
  selectedNode: Node | null;
  setSelectedNode: (node: Node | null) => void;

  // Highlighting state
  highlightAddress: string | null;
  setHighlightAddress: (address: string | null) => void;

  // Actions
  refetchData: () => void;
  prefetchData: (address: string, from: string, to: string) => void;

  // Status
  hasData: boolean;
  hasError: boolean;
}

export function useGraphAnalysis({
  inputAddress,
  fromBlock,
  toBlock,
  autoExecute = true, // Default to true for backward compatibility
}: UseGraphAnalysisParams): UseGraphAnalysisReturn {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [highlightAddress, setHighlightAddress] = useState<string | null>(null);
  const { showLocalAlert } = useLocalAlert();
  const queryClient = useQueryClient();

  // Optimized query key for caching - only include valid complete parameters
  const queryKey = useMemo(() => {
    // Only create query key if we have a complete, valid address
    if (!inputAddress || inputAddress.length < 10) {
      return ["graphData", "invalid"];
    }
    return ["graphData", inputAddress, fromBlock, toBlock].filter(Boolean);
  }, [inputAddress, fromBlock, toBlock]);

  // API availability query
  const { data: apiAvailability } = useQuery({
    queryKey: ["apiAvailability"],
    queryFn: getApiAvailability,
    staleTime: API.PREFETCH_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });

  // Graph data query with optimized caching
  const {
    data: jsonData = null,
    isLoading: loading,
    error,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: async () => {
      if (!inputAddress) return null;
      return fetchGraphData(inputAddress, fromBlock, toBlock, (message) =>
        showLocalAlert(message, 5000),
      );
    },
    enabled:
      !!inputAddress &&
      inputAddress.length >= 10 &&
      !!apiAvailability &&
      autoExecute,
    staleTime: API.STALE_TIME_MS,
    refetchOnWindowFocus: false,
    retry: API.RETRY_ATTEMPTS,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Prefetch function for performance optimization
  const prefetchData = (address: string, from: string, to: string) => {
    if (!apiAvailability) return;

    queryClient.prefetchQuery({
      queryKey: ["graphData", address, from, to].filter(Boolean),
      queryFn: () => fetchGraphData(address, from, to, () => {}),
      staleTime: API.PREFETCH_STALE_TIME_MS,
    });
  };

  const refetchData = () => {
    refetch();
  };

  return {
    // Data
    jsonData,
    apiAvailability,
    loading,
    error,

    // Node selection state
    selectedNode,
    setSelectedNode,

    // Highlighting state
    highlightAddress,
    setHighlightAddress,

    // Actions
    refetchData,
    prefetchData,

    // Status
    hasData: !!jsonData,
    hasError: !!error,
  };
}
