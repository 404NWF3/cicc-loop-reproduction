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
  generator?: 'local' | 'deepseek';
  max_model_cny?: number;
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
    novel: number;
    model_calls: number;
    tokens: number;
  };
  created_at: string;
  updated_at: string;
  started_at: string | null;
  error: string | null;
  checkpoint: Record<string, unknown>;
  is_experiment: boolean;
  notice: string;
}
export interface Gate {
  id: string;
  name: string;
  key: string;
  operator: string;
  threshold: number;
  value: number | null;
  status: 'passed' | 'failed' | 'not_evaluated' | 'not_applicable';
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
  review?: { verdict: string; explanation: string; reason_code?: string };
  ordinal: number;
  round: number;
  status: string;
  reason: string;
  fingerprint: string | null;
  validation: Validation | null;
  metrics: Record<string, number | null> | null;
  gates: Gate[];
  accepted: boolean;
  is_experiment?: boolean;
  direction?: number;
  discovery_ic?: number | null;
  periods?: Record<
    string,
    { annual_excess: number | null; sharpe: number | null; calmar: number | null }
  >;
  series?: { date: string; nav: number; benchmark: number; relative: number }[];
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
  live_enabled: boolean;
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

export interface ExperimentResult {
  id: string;
  status: string;
  started_at_utc: string;
  asset_count: number;
  rows: number;
  seed: number;
  seconds: number;
  experiment_version?: string;
  random_seeds?: number[];
  research_note?: string;
  accepted_factors?: {
    id: string;
    branch: string;
    expression: string;
    direction: number;
    discovery_ic: number;
    metrics: { calmar: number; max_correlation: number | null };
    periods: Record<string, { annual_excess: number; sharpe: number }>;
  }[];
  holdout?: Record<
    string,
    {
      status: string;
      factors: {
        id: string;
        annual_excess: number | null;
        sharpe: number | null;
        max_drawdown: number | null;
        rank_ic: number | null;
      }[];
      composite: {
        annual_excess: number | null;
        sharpe: number | null;
        max_drawdown: number | null;
        factor_count: number;
      } | null;
    }
  >;
  model: { id: string; name: string; thinking: string };
  periods: Record<string, string[]>;
  data_commit: string;
  data_sha256: string;
  protocol_sha256: string;
  budget: {
    run_requests: number;
    run_tokens: number;
    run_cost_upper_bound_cny: number;
    hard_cap_cny: number;
    cost_upper_bound_cny?: number;
  };
  verification: {
    status: string;
    peak_price_usage_estimate_cny: number;
    max_ic_absolute_error: number;
    max_nav_absolute_error: number;
  };
  branches: Record<
    string,
    {
      attempts: number;
      legal: number;
      backtested: number;
      accepted: number;
      unique_expressions: number;
      unique_skeletons: number;
      outcomes: Record<string, number>;
    }
  >;
  baselines: {
    id: string;
    name: string;
    expression: string;
    direction: number;
    discovery_ic: number | null;
    periods: Record<string, { annual_excess: number | null; sharpe: number | null }>;
  }[];
  sources: Record<string, string>;
}
