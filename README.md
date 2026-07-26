<div align="center">

<img src="frontend/public/brand/nuto-mark.svg" width="88" alt="Nuto, the nutsheLLM acorn mascot">

# nutsheLLM

**Your context, in a nutsheLLM.**

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-d8ff54?labelColor=111611)](https://github.com/Paritok-official/paritok-4b-v1)
[![Live demo](https://img.shields.io/badge/live_demo-Railway-c58b3b?labelColor=111611)](https://nutshellm-production.up.railway.app)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

</div>

nutsheLLM is a quality-aware context optimization workbench for AI applications and
agents. Nuto, its acorn guide, helps make the safety story memorable: trim the
shell, guard the kernel, and prove the answer. The application compresses eligible context with
[Paritok](https://github.com/Paritok-official/paritok-4b-v1), checks whether exact
facts and task performance survived, and automatically retries with safer context
when they did not.

The core question is not only “how many tokens did we remove?” It is “how many
tokens can we remove while preserving useful task performance?”

## What it proves

- **Fair baseline comparison.** The task model, parameters, and instructions are
  identical; only context changes.
- **Explicit context decisions.** Every segment is classified as immutable,
  compressible, or disposable.
- **Exact fact preservation.** Paths, identifiers, signatures, errors, timestamps,
  measurements, stack frames, URLs, and quoted literals must survive byte-for-byte.
- **Real fallback.** nutsheLLM tries PariTok `L2`, then `L1`, then `L0`, and finally
  restores the original context.
- **Honest accounting.** PariTok savings, deterministic duplicate removal, task
  input, evaluation overhead, estimated spend, and latency are reported separately.

## Final live result

The final three-scenario suite achieved **52.2% median input saving with a 100%
deterministic pass rate (3/3)**. Individual savings were 52.2%, 0%, and 71.58%.
The zero-savings checkout result is retained because the safety contract takes
priority over the headline number. See the
[final benchmark](docs/final-benchmark.md) and
[structured evidence](examples/benchmark-summary.json).

## Architecture

```text
React workbench
      │  POST /api/v1/runs
      ▼
FastAPI + temporary SQLite job queue
      │
      ├─ classify segments and lock critical facts
      ├─ call Paritok hosted /compress
      ├─ restore any segment that loses an immutable span
      ├─ call configured OpenAI-compatible task model
      ├─ validate quality and retry at safer levels
      └─ persist content-free aggregate metrics
```

The production artifact is one Docker image. FastAPI serves the compiled React
workbench, runs one recoverable background worker, and stores short-lived results in
SQLite on a mounted volume. See [Architecture](docs/architecture.md) and
[Evaluation methodology](docs/evaluation.md).

## Curated demonstrations

1. **Code debugging:** find a retry-cache key bug while preserving exact files,
   symbols, and test evidence.
2. **Incident response:** retain a checkout failure’s service, start time, peak error
   rate, exact exception, and triggering deployment.
3. **Tool-output analysis:** remove repeated worker health output without losing the
   single disk-pressure anomaly.

Curated answers use deterministic fact validators. Custom tasks use exact invariant
checks and can optionally enable a blind semantic judge. If no reliable validator is
available, the UI says `unverified`; it does not claim success.

## Local development

Requirements: Python 3.11+, Node.js 22+, a PariTok hosted API key, and an
OpenAI-Chat-Completions-compatible model endpoint.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cd frontend && npm ci && cd ..
```

Set runtime values in your shell or secret manager. `config.example` lists every
supported name; it contains placeholders only.

```bash
export PARITOK_API_KEY="..."
export TASK_MODEL_API_KEY="your-Gemini-API-key"
export TASK_MODEL_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
export TASK_MODEL="gemini-3.5-flash-lite"
export SESSION_SIGNING_SECRET="$(openssl rand -hex 32)"
```

Run the API and frontend in separate terminals:

```bash
make api
make web
```

Open `http://127.0.0.1:5173`. API documentation is available at
`http://127.0.0.1:8000/api/docs` outside production.

## Docker

```bash
docker build -t nutshellm .
docker run --rm -p 8000:8000 \
  -v nutshellm-data:/app/data \
  -e PARITOK_API_KEY \
  -e TASK_MODEL_API_KEY \
  -e SESSION_SIGNING_SECRET \
  nutshellm
```

For a production public demo, use the same image:

```bash
docker build -t nutshellm .
```

Then configure `ENVIRONMENT=production`, both `TURNSTILE_SITE_KEY` and
`TURNSTILE_SECRET_KEY`, strict quotas, and explicit model prices. The public site
key is delivered to the frontend at runtime; it is not baked into the image.
`/readyz` fails closed if required production settings are missing. See
[Configuration](docs/configuration.md).

## Task optimization API

Start a curated comparison:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"scenario_id":"checkout-incident","mode":"compare"}'
```

Poll the returned private status URL with the same anonymous-session cookie:

```bash
curl -b cookies.txt http://127.0.0.1:8000/api/v1/runs/RUN_ID
```

Custom input accepts a task and up to 12 typed context segments:

```json
{
  "task": "What caused the failure?",
  "mode": "compare",
  "segments": [
    {
      "id": "logs",
      "kind": "log_output",
      "source": "api.log",
      "content": "..."
    }
  ],
  "turnstile_token": "required for every production run"
}
```

Supported kinds are `file_read`, `log_output`, `tool_result`, `history`,
`documentation`, and `other`. Provider URLs and model names are deployment
configuration, never user input.

## Security and privacy

- Provider and PariTok keys remain backend-only and are never returned or logged.
- Custom content and outputs exist only in the temporary job record and are deleted
  after `RESULT_TTL_SECONDS` (one hour by default).
- Aggregate metrics contain no task, context, or output text.
- Run results are bound to a signed anonymous session, not exposed as public links.
- Every production run requires Turnstile, independent per-IP and per-session
  limits, a global run limit,
  and a global estimated-spend cap.
- Model-generated code is rendered as text and is never executed.
- Request size, segment count, upstream model, retries, timeouts, and provider hosts
  are bounded server-side.

**Operational action:** the PariTok key previously written in local project notes
must be rotated before deployment. This repository contains no copy of that key.

## Validation

```bash
make test
make lint
make typecheck
make build
make docker
```

CI runs Python tests and lint, frontend lint/type-check/build, and a Docker build.
Live provider smoke tests are intentionally secret-gated and must not run for
untrusted pull requests.

## Limits

- v1 supports one environment-configured OpenAI-compatible task-model endpoint.
- It is a task optimization API, not a transparent Chat Completions proxy.
- Arbitrary repositories and generated patches are not executed.
- SQLite and the internal worker require one application replica.
- Token counts use provider-reported usage when available and otherwise are marked
  as estimates.
- Custom task quality is `unverified` unless the optional semantic judge is enabled.

## Submission

The public deployment, measured benchmark export, screenshots, demo recording, and
Devpost fields are operational release tasks tracked in
[the submission checklist](docs/submission-checklist.md). Do not publish a savings
claim until it comes from a completed live run.

## License

Apache License 2.0. Built with [Paritok](https://github.com/Paritok-official/paritok-4b-v1).
