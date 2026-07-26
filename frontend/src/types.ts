export type SegmentKind =
  | "file_read"
  | "log_output"
  | "tool_result"
  | "history"
  | "documentation"
  | "other";

export interface Scenario {
  id: string;
  title: string;
  category: string;
  description: string;
  segment_count: number;
}

export interface SegmentInput {
  id: string;
  kind: SegmentKind;
  source?: string;
  content: string;
}

export interface ModelAnswer {
  text: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    latency_ms: number;
    estimated: boolean;
  };
}

export interface SegmentDecision {
  id: string;
  kind: SegmentKind;
  disposition: "immutable" | "compressible" | "disposable";
  reason: string;
  original: string;
  optimized: string;
  level?: string;
  original_tokens: number;
  optimized_tokens: number;
  immutable_recall: number;
  paritok_applied: boolean;
  restored: boolean;
  critical_spans: Array<{ kind: string; text: string }>;
}

export interface Validation {
  status: "passed" | "failed" | "unverified" | "inconclusive";
  score?: number;
  reason: string;
  checks: Array<Record<string, unknown>>;
}

export interface Attempt {
  level: string;
  segments: SegmentDecision[];
  answer: ModelAnswer;
  validation: Validation;
  context_tokens: number;
  compression_latency_ms: number;
}

export interface RunResult {
  run_id: string;
  scenario_id?: string;
  mode: "compare" | "optimize";
  task: string;
  baseline?: ModelAnswer;
  optimized: ModelAnswer;
  final_segments: SegmentDecision[];
  attempts: Attempt[];
  validation: Validation;
  fallback?: string;
  metrics: {
    original_input_tokens: number;
    optimized_input_tokens: number;
    paritok_tokens_saved: number;
    directly_pruned_tokens: number;
    total_tokens_saved: number;
    savings_percent: number;
    estimated_input_cost_saved_usd: number;
    evaluation_overhead_tokens: number;
    evaluation_overhead_cost_usd: number;
    estimated_total_run_cost_usd: number;
    total_latency_ms: number;
  };
}

export interface Job {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  created_at: string;
  expires_at: string;
  result?: RunResult;
  error?: string;
}

export interface Summary {
  runs: number;
  original_tokens: number;
  optimized_tokens: number;
  saved_tokens: number;
  cost_saved: number;
  avg_latency_ms: number;
  passed: number;
}
