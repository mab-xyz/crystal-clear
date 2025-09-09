// Graph visualization types

export interface Node {
  id: string;
  group: "main" | "other";
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface Edge {
  source: string;
  target: string;
  types: Record<string, number>;
}

export interface Link {
  source: string | Node;
  target: string | Node;
  type: string;
  count: number;
}

export interface GraphData {
  address: string;
  edges: Edge[];
  nodes?: Record<string, string>; // Map of address to name
  from_block?: number;
  to_block?: number;
  n_nodes?: number;
}

export interface GraphDimensions {
  width: number;
  height: number;
}

export interface NodeHoverInfo {
  balance?: string | null;
  company?: string | null;
  error?: boolean;
}
