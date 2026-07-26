# Configuration

All configuration comes from process environment variables. `config.example`
contains non-secret placeholders that can be copied into a deployment platform.

| Variable | Default | Purpose |
|---|---:|---|
| `ENVIRONMENT` | `development` | Set `production` to enable fail-closed readiness and secure cookies. |
| `DATABASE_PATH` | `data/nutshellm.sqlite3` | SQLite database on a persistent volume. |
| `RESULT_TTL_SECONDS` | `3600` | Maximum lifetime of context-bearing job results. |
| `PARITOK_API_KEY` | unset | Backend-only hosted PariTok access. |
| `PARITOK_BASE_URL` | PariTok hosted API | Fixed compression service base. |
| `PARITOK_MODEL` | `paritok-4b-v1` | Compressor model attribution. |
| `TASK_MODEL_API_KEY` | unset | Backend-only final-model access. |
| `TASK_MODEL_BASE_URL` | OpenAI v1 API | OpenAI Chat Completions compatible base. |
| `TASK_MODEL` | `gpt-4.1-mini` | Allowlisted final model for all public runs. |
| `TASK_MAX_OUTPUT_TOKENS` | `1200` | Hard cap for each generated task or judge answer. |
| `TASK_REASONING_EFFORT` | unset | Optional compatible-provider reasoning level; production Gemini uses `low`. |
| `TASK_MODEL_MAX_RETRIES` | `1` | Bounded retry count for provider rate limits. |
| `TASK_MODEL_RETRY_MAX_DELAY_SECONDS` | `35` | Maximum server-requested delay before the single retry. |
| `JUDGE_MODEL` | task model | Optional semantic evaluator model. |
| `ENABLE_LLM_JUDGE` | `false` | Enable custom answer comparison. |
| `TASK_INPUT_USD_PER_MTOK` | `0` | Explicit input price used for estimates. |
| `TASK_OUTPUT_USD_PER_MTOK` | `0` | Explicit output price used for estimates. |
| `TURNSTILE_SITE_KEY` | unset | Public widget key served to the frontend at runtime. |
| `TURNSTILE_SECRET_KEY` | unset | Private verification key required for every production run. |
| `TURNSTILE_EXPECTED_HOSTNAMES` | unset | Comma-separated hostname allowlist checked during verification. |
| `SESSION_SIGNING_SECRET` | insecure placeholder | Required random HMAC secret in production. |
| `PER_IP_DAILY_RUN_LIMIT` | `5` | Independently enforced per IP and signed session. |
| `GLOBAL_DAILY_RUN_LIMIT` | `100` | Daily server-funded run ceiling. |
| `GLOBAL_DAILY_BUDGET_USD` | `10` | Stop new runs after estimated spend reaches this value. |
| `MAX_TASK_CHARS` | `4000` | Custom task limit. |
| `MAX_SEGMENTS` | `12` | Custom segment limit. |
| `MAX_CONTEXT_CHARS` | `50000` | Total custom context limit. |
| `TRUSTED_PROXY_CIDRS` | unset | Proxy CIDRs allowed to supply the first forwarded IP. |

The frontend obtains the public Turnstile site key from the backend at runtime.
The corresponding secret stays a backend-only runtime setting.

## Railway deployment

1. Build from the repository Dockerfile.
2. Attach a persistent volume at `/app/data`.
3. Keep one replica; the internal queue is not distributed.
4. Configure every production requirement in Railway Variables.
5. Set the Turnstile site and secret keys as Railway runtime variables.
6. Set the health-check path to `/readyz`.
7. Point Turnstile at the final HTTPS domain.

Never put a real key in `config.example`, an image build argument, frontend
variables, logs, screenshots, or submission material.
