# Final live benchmark

Measured on 2026-07-25 against the configured hosted PariTok compressor and
Gemini task model. Baseline and optimized calls used the same task model,
instructions, and parameters; supplied context was the intended variable.

## Result

**Median input saving: 52.2%. Deterministic quality pass rate: 100% (3/3).**

| Scenario | Original input | Optimized input | Saved | Validation |
| --- | ---: | ---: | ---: | --- |
| Retry-cache bug | 1,387 | 663 | 52.2% | Passed, 100/100 |
| Checkout incident | 2,477 | 2,477 | 0.0% | Passed, 100/100 |
| Tool-output anomaly | 3,016 | 857 | 71.58% | Passed, 100/100 |

Across the suite, provider-reported input fell from 6,880 to 3,997 tokens: 2,883
tokens removed, or 41.9% in aggregate.

The checkout scenario intentionally remains a zero-savings result. The accepted
pipeline did not report a provider-level reduction while enforcing its exact-fact
contract. It is retained because nutsheLLM optimizes only when it can preserve
task evidence; it does not replace an honest safety outcome with a stronger
marketing number.

## Reproducibility

The structured summary is in
[`examples/benchmark-summary.json`](../examples/benchmark-summary.json). Each row
links to its complete redacted result containing provider usage, validation checks,
attempts, segment decisions, answers, and latency. Anonymous run identifiers are
removed, and the examples contain only public curated scenario content.

The landing page's aggregate metric strip includes earlier development attempts.
Its historical pass percentage is not the final benchmark result and must not be
used in submission claims.
