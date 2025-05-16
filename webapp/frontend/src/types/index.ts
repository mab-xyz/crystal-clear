export interface Node {
  id: string;
  group: string;
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

export interface JsonData {
  address: string;
  from_block?: number;
  to_block?: number;
  n_nodes?: number;
  nodes?: Record<string, string>; // Map of address to name
  edges: Edge[];
}
