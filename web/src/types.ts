export type RunState =
  | 'draft'
  | 'queued'
  | 'running'
  | 'pause_requested'
  | 'paused'
  | 'stop_requested'
  | 'stopped'
  | 'completed'
  | 'failed'
  | 'interrupted'
  | 'budget_exhausted';
export interface RunConfig {
  name: string;
  mode: 'fixture' | 'live';
  rounds: number;
  batch_size: number;
  seed: number;
  fsa_enabled: boolean;
  max_candidates: number;
  max_seconds: number;
  dataset_id?: string | null;
}
export interface Run {
  id: string;
  config: RunConfig;
  config_hash: string;
  state: RunState;
  cursor: number;
  round: number;
  target: number;
  counts: {
    generated: number;
    validated: number;
    rejected: number;
    backtested: number;
    accepted: number;
    model_calls: number;
    tokens: number;
  };
  created_at: string;
  updated_at: string;
  started_at: string | null;
  error: string | null;
  checkpoint: Record<string, unknown>;
  is_experiment: false;
  notice: string;
}
export interface Gate {
  id: string;
  name: string;
  key: string;
  operator: string;
  threshold: number;
  value: number | null;
  status: 'passed' | 'failed' | 'not_evaluated';
  period: string;
  origin: string;
}
export interface Validation {
  depth: number;
  nodes: number;
  lookback: number;
  canonical: string;
  tree: Record<string, unknown>;
}
export interface Candidate {
  id: string;
  run_id: string;
  name: string;
  expression: string;
  strategy: string;
  mechanism: string;
  parent_ids: string[];
  hypothesis: string;
  origin: string;
  llm_review: string;
  ordinal: number;
  round: number;
  status: string;
  reason: string;
  fingerprint: string | null;
  validation: Validation | null;
  metrics: null;
  gates: Gate[];
  accepted: false;
}
export interface RunEvent {
  id: number;
  type: string;
  created_at: string;
  payload: { message?: string; state?: string; ordinal?: number; status?: string };
}
export interface ModelStatus {
  provider: string;
  requested_name: string;
  model_id: string | null;
  key_present: boolean;
  configured: boolean;
  verified: false;
  status: string;
}
export interface Capabilities {
  phase: string;
  available_modes: string[];
  live_enabled: false;
  model: ModelStatus;
  worker: string;
  fields: string[];
  operators: Record<string, number>;
  gates: Gate[];
  data_count: number;
  notice: string;
}
export interface Dataset {
  id: string;
  name?: string;
  source?: string;
  status: string;
  sha256?: string;
  validation?: {
    valid: boolean;
    rows: number;
    symbols: number;
    start: string;
    end: string;
    issues: string[];
    note: string;
  } | null;
}
