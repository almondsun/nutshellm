# Evaluation methodology

## Fairness contract

Baseline and optimized calls use the same final model, system instructions, task,
temperature, and requested output. Context is the only intended variable. Provider
usage is authoritative when supplied; fallback tokenizer counts are marked as
estimates.

## Context safety

Before compression, nutsheLLM extracts exact:

- paths and stack frames;
- function and class signatures;
- identifiers and error codes;
- exception types and messages;
- timestamps and measurements;
- URLs and quoted literals.

Every extracted span must appear byte-for-byte in the compressed candidate. A
segment with less than 100% recall is restored before the task model sees it. This
is a conservative guard, not proof that every semantic fact survived.

## Task-quality validation

Curated scenarios define groups of expected facts. A group passes when the response
contains at least one accepted representation. All groups must pass. The three
fixtures cover code debugging, incident response, and anomaly extraction.

For arbitrary tasks, deterministic ground truth is unavailable. If the optional
judge is disabled, the result is labelled `unverified`. If enabled, a separate
structured call compares baseline and optimized answers blindly and requires both
`equivalent=true` and a score of at least 0.8.

Judge input/output tokens and cost are reported as evaluation overhead. They are
never subtracted from operational context or presented as PariTok savings.

## Savings attribution

- **PariTok saved:** tokens removed from final accepted segments by the hosted
  compressor.
- **Directly pruned:** tokens from exact duplicate or known boilerplate segments.
- **Total input saved:** baseline provider input minus accepted optimized provider
  input. This includes constant prompt overhead and may differ from the first two
  segment-level values.
- **Estimated cost saved:** total input saved multiplied by the explicitly configured
  input price. A zero price means unavailable, not free.
- **Estimated run cost:** all baseline, attempt, fallback, and judge usage. It powers
  reporting; a conservative worst-case reservation made before enqueue powers
  the public-demo budget guard.

Do not claim a target saving from model targets alone. Publish the measured median
and quality pass rate from completed runs.

The submission benchmark and its redacted per-scenario evidence are recorded in
[Final live benchmark](final-benchmark.md).
