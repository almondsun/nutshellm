# Final benchmark evidence

[`benchmark-summary.json`](benchmark-summary.json) records the final live suite:
**52.2% median input saving and 100% deterministic quality passes (3/3).**

| Evidence | Input saving | Validation |
| --- | ---: | --- |
| [`retry-cache-bug.json`](retry-cache-bug.json) | 52.2% | Passed, 100/100 |
| [`checkout-incident.json`](checkout-incident.json) | 0.0% | Passed, 100/100 |
| [`tool-output-anomaly.json`](tool-output-anomaly.json) | 71.58% | Passed, 100/100 |

Each file is a provider-measured result containing the public curated scenario,
model answers, usage, validation checks, context decisions, and fallback evidence.
Anonymous run identifiers are removed. No fabricated benchmark output is
committed.
