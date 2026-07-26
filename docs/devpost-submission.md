# Devpost submission copy

## Elevator pitch

nutsheLLM trims bloated LLM context with PariTok, protects exact facts, and
validates task quality—backing off automatically when compression goes too far.

## Tagline

Your context, in a nutsheLLM.

## Inspiration

AI agents repeatedly resend source files, logs, tool output, documentation, and
conversation history. Removing tokens is easy to measure, but a smaller prompt is
not useful when it loses the one timestamp, error, path, or identifier the task
depends on. We built nutsheLLM to ask the harder question: how much context can we
remove while preserving useful task performance?

## What it does

nutsheLLM compares an original task-model run with a context-optimized run. It
classifies each context segment, locks exact facts, compresses eligible material
with hosted PariTok, and validates the resulting answer. If an aggressive attempt
fails, it steps down through safer compression levels and ultimately restores the
original context. The workbench reports savings, validation evidence, fallback
attempts, latency, and context decisions separately.

Nuto, our acorn optimizer, turns that policy into one memorable rule: compress the
shell, guard the kernel, and prove the answer.

## How we built it

The frontend is a responsive React and TypeScript evaluation workbench. FastAPI
owns classification, PariTok integration, task-model execution, validation,
fallback orchestration, quotas, and content-free aggregate metrics. A temporary
SQLite queue makes runs recoverable, and the compiled frontend and API ship as one
Docker image on Railway.

Curated scenarios cover code debugging, incident response, and noisy tool-output
analysis. They use deterministic fact validators. Exact paths, identifiers,
errors, timestamps, measurements, URLs, and quoted literals must survive
byte-for-byte before compressed context can reach the task model.

## Challenges

The central challenge was separating token reduction from trustworthy reduction.
We had to compare baseline and optimized runs fairly, attribute PariTok savings
separately from deterministic pruning, prevent exact-fact loss, handle provider
rate limits, and make fallback behavior visible rather than silently hiding it.

## Accomplishments

- Three distinct live stress scenarios reached full deterministic validation:
  100% passed (3/3), with 52.2% median provider-reported input saving.
- Compression cannot silently alter extracted critical facts.
- The safety ladder automatically tries `L2 → L1 → L0 → original`.
- Every transformation and fallback attempt is inspectable.
- Public-demo keys stay server-side behind human verification, quotas, and a
  global spend guard.
- The product communicates a technical safety contract through a friendly,
  cohesive brand without hiding the evidence.

## What we learned

Compression quality is task-dependent. A model-level target is not a product-level
guarantee, and a token counter cannot establish answer quality. Reliable context
optimization needs classification, invariant protection, task-aware evaluation,
honest accounting, and a safe escape hatch.

## What's next

Next steps include larger benchmark suites, per-workload policies, more
OpenAI-compatible task providers, stronger custom-task evaluation, and exporting
optimization traces for agent frameworks and observability platforms.

## Links and tags

- Live app: https://nutshellm-production.up.railway.app
- Source: https://github.com/almondsun/nutshellm
- Tags: `PariTok`, `FastAPI`, `React`, `context-compression`, `LLM`,
  `developer-tools`
