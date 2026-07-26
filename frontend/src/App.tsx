import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type {
  Job,
  RunResult,
  Scenario,
  SegmentInput,
  SegmentKind,
  Summary,
} from "./types";
import { Nuto, NutoMark } from "./Nuto";

const TokenChart = lazy(() => import("./TokenChart"));

const kinds: Array<{ value: SegmentKind; label: string }> = [
  { value: "file_read", label: "Source code" },
  { value: "log_output", label: "Logs" },
  { value: "tool_result", label: "Tool output" },
  { value: "history", label: "Conversation history" },
  { value: "documentation", label: "Documentation" },
  { value: "other", label: "Other" },
];

const initialSegment = (): SegmentInput => ({
  id: `context-${crypto.randomUUID().slice(0, 8)}`,
  kind: "log_output",
  content: "",
});

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function Turnstile({
  sitekey,
  resetNonce,
  onToken,
}: {
  sitekey: string;
  resetNonce: number;
  onToken: (token: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!sitekey || !ref.current) return;
    if (!document.getElementById("turnstile-script")) {
      const script = document.createElement("script");
      script.id = "turnstile-script";
      script.src =
        "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    const timer = window.setInterval(() => {
      if (!window.turnstile || !ref.current || widgetIdRef.current) return;
      widgetIdRef.current = window.turnstile.render(ref.current, {
        sitekey,
        action: "nutshellm_run",
        callback: onToken,
        "expired-callback": () => onToken(""),
        "error-callback": () => onToken(""),
        theme: "dark",
      });
      window.clearInterval(timer);
    }, 200);
    return () => {
      window.clearInterval(timer);
      if (widgetIdRef.current) {
        window.turnstile?.remove(widgetIdRef.current);
        widgetIdRef.current = undefined;
      }
    };
  }, [onToken, sitekey]);

  useEffect(() => {
    if (resetNonce === 0 || !widgetIdRef.current) return;
    onToken("");
    window.turnstile?.reset(widgetIdRef.current);
  }, [onToken, resetNonce]);

  return sitekey ? <div className="turnstile" ref={ref} /> : null;
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [turnstileSiteKey, setTurnstileSiteKey] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [task, setTask] = useState("");
  const [segments, setSegments] = useState<SegmentInput[]>([initialSegment()]);
  const [turnstileToken, setTurnstileToken] = useState("");
  const [turnstileResetNonce, setTurnstileResetNonce] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([
      api<Scenario[]>("/api/v1/scenarios"),
      api<Summary>("/api/v1/metrics/summary"),
      api<{ turnstile_site_key: string }>("/api/v1/public-config"),
    ])
      .then(([scenarioData, metrics, publicConfig]) => {
        setScenarios(scenarioData);
        setSummary(metrics);
        setTurnstileSiteKey(publicConfig.turnstile_site_key);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setInterval(() => {
      api<Job>(`/api/v1/runs/${job.id}`)
        .then((next) => {
          setJob(next);
          if (next.status === "complete") {
            setBusy(false);
            api<Summary>("/api/v1/metrics/summary").then(setSummary).catch(() => {});
          }
          if (next.status === "failed") setBusy(false);
        })
        .catch((reason: Error) => {
          setError(reason.message);
          setBusy(false);
        });
    }, 750);
    return () => window.clearInterval(timer);
  }, [job]);

  const customReady = useMemo(
    () => task.trim().length > 0 && segments.every((item) => item.content.trim()),
    [task, segments],
  );
  const humanReady = !turnstileSiteKey || Boolean(turnstileToken);

  async function startRun(payload: Record<string, unknown>) {
    setBusy(true);
    setError("");
    setJob(null);
    try {
      const created = await api<Job>("/api/v1/runs", {
        method: "POST",
        body: JSON.stringify({
          ...payload,
          mode: "compare",
          turnstile_token: turnstileToken || undefined,
        }),
      });
      setJob(created);
      document.getElementById("run")?.scrollIntoView({ behavior: "smooth" });
    } catch (reason) {
      setBusy(false);
      setError(reason instanceof Error ? reason.message : "Could not start run");
    } finally {
      setTurnstileResetNonce((current) => current + 1);
    }
  }

  function updateSegment(index: number, patch: Partial<SegmentInput>) {
    setSegments((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    );
  }

  return (
    <div className="app-shell">
      <header className="nav">
        <a className="brand" href="#top" aria-label="nutsheLLM home">
          <span className="nut-mark"><NutoMark /></span>
          <span className="wordmark">nutshe<b>LLM</b></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#lab">Lab</a>
          <a href="#method">Method</a>
          <a href="#evidence">Evidence</a>
          <a href="https://github.com/almondsun/nutshellm#task-optimization-api">
            API
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-content">
            <div className="eyebrow">
              <span className="pulse" /> Meet Nuto, your context optimizer
            </div>
            <h1 id="hero-title">
              Your context,
              <span className="hero-last-line">in a <em>nutsheLLM.</em></span>
            </h1>
            <p className="hero-copy">
              Nuto trims bloated agent context with PariTok, locks the facts your
              task needs, and checks that the answer still holds up.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#lab">
                Crack open a stress test <span>↘</span>
              </a>
              <a className="button ghost" href="#method">
                See how it works
              </a>
            </div>
            <div className="hero-proof" aria-label="Core guarantees">
              <span><b>01</b> Context sorted</span>
              <span><b>02</b> Kernel guarded</span>
              <span><b>03</b> Answer proven</span>
            </div>
          </div>
          <div className="hero-mascot" aria-label="Nuto sorts context while protecting the useful kernel">
            <div className="context-chip chip-keep"><small>KEEP</small><strong>error_code</strong></div>
            <div className="context-chip chip-trim"><small>COMPRESS</small><strong>repeated logs</strong></div>
            <div className="context-chip chip-drop"><small>DISCARD</small><strong>duplicate noise</strong></div>
            <div className="kernel-orbit" aria-hidden="true" />
            <Nuto pose="hero" label="Nuto, the nutsheLLM acorn mascot" />
            <p><span>Nuto’s rule</span>If the kernel cracks, step back.</p>
          </div>
        </section>

        <section className="metric-strip" id="evidence">
          <Metric label="Measured runs" value={format(summary?.runs)} />
          <Metric label="Tokens saved" value={format(summary?.saved_tokens)} />
          <Metric
            label="Quality passes"
            value={
              summary?.runs
                ? `${Math.round((summary.passed / summary.runs) * 100)}%`
                : "—"
            }
          />
          <Metric
            label="Est. cost saved"
            value={summary ? `$${summary.cost_saved.toFixed(3)}` : "—"}
          />
        </section>

        <section className="section" id="lab">
          <div className="section-heading">
            <div>
              <span className="kicker">Evaluation workbench</span>
              <h2>Crack open a stress test</h2>
            </div>
            <p>
              Each scenario runs the same model twice. Only the supplied context
              changes.
            </p>
          </div>

          <div className="scenario-grid">
            {scenarios.map((scenario, index) => (
              <article className="scenario-card" key={scenario.id}>
                <div className="card-top">
                  <span className="scenario-number">0{index + 1}</span>
                  <span className="tag">{scenario.category}</span>
                </div>
                <h3>{scenario.title}</h3>
                <p>{scenario.description}</p>
                <div className="card-bottom">
                  <span>{scenario.segment_count} context segments</span>
                  <button
                    className="run-button"
                    onClick={() => startRun({ scenario_id: scenario.id })}
                    disabled={busy || !humanReady}
                  >
                    Run <span>→</span>
                  </button>
                </div>
              </article>
            ))}
          </div>
          <Turnstile
            sitekey={turnstileSiteKey}
            resetNonce={turnstileResetNonce}
            onToken={setTurnstileToken}
          />

          <details className="custom-panel">
            <summary>
              <span>Bring your own context</span>
              <small>Limited custom run</small>
            </summary>
            <div className="custom-content">
              <label>
                Task
                <textarea
                  value={task}
                  maxLength={4000}
                  onChange={(event) => setTask(event.target.value)}
                  placeholder="What should the model determine from this context?"
                />
              </label>
              {segments.map((segment, index) => (
                <div className="segment-editor" key={segment.id}>
                  <div className="editor-row">
                    <label>
                      Context type
                      <select
                        value={segment.kind}
                        onChange={(event) =>
                          updateSegment(index, {
                            kind: event.target.value as SegmentKind,
                          })
                        }
                      >
                        {kinds.map((kind) => (
                          <option key={kind.value} value={kind.value}>
                            {kind.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Source (optional)
                      <input
                        value={segment.source || ""}
                        onChange={(event) =>
                          updateSegment(index, { source: event.target.value })
                        }
                        placeholder="src/module.py"
                      />
                    </label>
                  </div>
                  <textarea
                    aria-label={`Context segment ${index + 1}`}
                    value={segment.content}
                    onChange={(event) =>
                      updateSegment(index, { content: event.target.value })
                    }
                    placeholder="Paste source, logs, tool output, or conversation history…"
                  />
                  {segments.length > 1 && (
                    <button
                      className="text-button danger"
                      onClick={() =>
                        setSegments((current) =>
                          current.filter((_, itemIndex) => itemIndex !== index),
                        )
                      }
                    >
                      Remove segment
                    </button>
                  )}
                </div>
              ))}
              <div className="custom-actions">
                <button
                  className="text-button"
                  onClick={() =>
                    setSegments((current) => [...current, initialSegment()])
                  }
                  disabled={segments.length >= 12}
                >
                  + Add context segment
                </button>
                <button
                  className="button primary"
                  disabled={!customReady || busy || !humanReady}
                  onClick={() => startRun({ task, segments })}
                >
                  Compare context
                </button>
              </div>
            </div>
          </details>
        </section>

        {error && (
          <div className="notice error" role="alert">
            <Nuto pose="cautious" />
            <div><strong>Nuto hit a hard shell.</strong><span>{error}</span></div>
          </div>
        )}
        {job && (
          <section className="section run-section" id="run">
            {job.status !== "complete" || !job.result ? (
              <Running status={job.status} error={job.error} />
            ) : (
              <Results result={job.result} />
            )}
          </section>
        )}

        <section className="section method" id="method">
          <div className="section-heading">
            <div>
              <span className="kicker">Safety ladder</span>
              <h2>Keep the kernel intact</h2>
            </div>
          </div>
          <div className="method-grid">
            <Method
              number="01"
              title="Sort the context"
              body="Separate the kernel—immutable facts—from compressible context and duplicate shell."
            />
            <Method
              number="02"
              title="Trim the shell"
              body="Send eligible segments to PariTok at a risk-aware compression level."
            />
            <Method
              number="03"
              title="Guard the kernel"
              body="Restore any segment that changes an exact path, identifier, error, time, or measurement."
            />
            <Method
              number="04"
              title="Prove the answer"
              body="Check task success. If it fails, retry conservatively and finally restore the original."
            />
          </div>
        </section>
      </main>

      <footer>
        <span className="footer-brand"><NutoMark />nutsheLLM</span>
        <p>Built with PariTok for the Token-Efficiency Hackathon.</p>
        <a href="https://github.com/almondsun/nutshellm">Source ↗</a>
      </footer>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Method({
  number,
  title,
  body,
}: {
  number: string;
  title: string;
  body: string;
}) {
  return (
    <article>
      <span>{number}</span>
      <h3>{title}</h3>
      <p>{body}</p>
    </article>
  );
}

function Running({ status, error }: { status: string; error?: string }) {
  const steps = ["Classify", "Compress", "Execute", "Validate"];
  return (
    <div className="running">
      <Nuto pose={status === "failed" ? "cautious" : "running"} label="Nuto processing context" />
      <span className="kicker">{status}</span>
      <h2>{status === "failed" ? "Run stopped" : "Nuto is trimming the shell…"}</h2>
      {error ? <p>{error}</p> : <p>Baseline and optimized paths are running under identical settings.</p>}
      <div className="running-steps">
        {steps.map((step) => <span key={step}>{step}</span>)}
      </div>
    </div>
  );
}

function Results({ result }: { result: RunResult }) {
  const passed = result.validation.status === "passed";
  return (
    <div className="results">
      <div className="result-header">
        <div>
          <span className="kicker">Run complete</span>
          <h2>{passed ? "Kernel intact." : "Evidence ready."}</h2>
          <p>{result.validation.reason}</p>
        </div>
        <div className="result-verdict">
          <Nuto pose={passed ? "success" : "cautious"} />
          <div className={`quality-seal ${result.validation.status}`}>
            <small>Validation</small>
            <strong>{result.validation.status}</strong>
            <span>
              {result.validation.score == null
                ? "No deterministic score"
                : `${Math.round(result.validation.score * 100)} / 100`}
            </span>
          </div>
        </div>
      </div>

      <div className="result-metrics">
        <Metric
          label="Input saved"
          value={`${result.metrics.savings_percent.toFixed(1)}%`}
        />
        <Metric label="Tokens removed" value={format(result.metrics.total_tokens_saved)} />
        <Metric label="PariTok saved" value={format(result.metrics.paritok_tokens_saved)} />
        <Metric label="End-to-end" value={`${(result.metrics.total_latency_ms / 1000).toFixed(1)}s`} />
      </div>

      <div className="evidence-grid">
        <article className="chart-card">
          <div className="card-title">
            <h3>Context footprint</h3>
            <span>Operational input only</span>
          </div>
          <Suspense fallback={<div className="chart-loading">Loading chart…</div>}>
            <TokenChart
              original={result.metrics.original_input_tokens}
              optimized={result.metrics.optimized_input_tokens}
            />
          </Suspense>
          <div className="chart-legend">
            <span><i className="original" /> Original</span>
            <span><i className="optimized" /> Optimized</span>
          </div>
        </article>

        <article className="attempt-card">
          <div className="card-title">
            <h3>Safety ladder</h3>
            <span>{result.fallback ? "Original restored" : "Accepted safely"}</span>
          </div>
          <ol>
            {result.attempts.map((attempt, index) => (
              <li key={`${attempt.level}-${index}`}>
                <span className={`attempt-dot ${attempt.validation.status}`} />
                <div>
                  <strong>{attempt.level === "original" ? "Original" : `${attempt.level} compression`}</strong>
                  <small>
                    {format(attempt.context_tokens)} context tokens · {attempt.validation.status}
                  </small>
                </div>
              </li>
            ))}
          </ol>
          {result.metrics.evaluation_overhead_tokens > 0 && (
            <p className="overhead">
              Evaluation overhead: {format(result.metrics.evaluation_overhead_tokens)} tokens,
              reported separately.
            </p>
          )}
        </article>
      </div>

      <div className="answer-grid">
        <Answer title="Baseline" answer={result.baseline} />
        <Answer title="Optimized" answer={result.optimized} featured />
      </div>

      <div className="segments">
        <div className="card-title">
          <h3>Context decisions</h3>
          <span>Inspect every transformation</span>
        </div>
        {result.final_segments.map((segment) => (
          <details key={segment.id}>
            <summary>
              <span className={`disposition ${segment.disposition}`}>
                {segment.disposition}
              </span>
              <strong>{segment.id}</strong>
              <small>
                {segment.level || "verbatim"} · {format(segment.original_tokens)} →{" "}
                {format(segment.optimized_tokens)} tokens
              </small>
              <span className="recall">
                {Math.round(segment.immutable_recall * 100)}% facts
              </span>
            </summary>
            <p className="decision-reason">{segment.reason}</p>
            <div className="context-pair">
              <pre><code>{segment.original}</code></pre>
              <pre><code>{segment.optimized || "Removed as deterministic duplicate/boilerplate."}</code></pre>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function Answer({
  title,
  answer,
  featured = false,
}: {
  title: string;
  answer?: RunResult["optimized"];
  featured?: boolean;
}) {
  return (
    <article className={featured ? "answer featured" : "answer"}>
      <div className="card-title">
        <h3>{title}</h3>
        {answer && <span>{answer.usage.latency_ms}ms</span>}
      </div>
      <pre>{answer?.text || "Not run in optimize-only mode."}</pre>
    </article>
  );
}

function format(value?: number): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact" }).format(value);
}
