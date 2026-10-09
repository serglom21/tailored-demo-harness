# Handoff formats

## docs/DEMO_SCRIPT.md (for the SE, internal)

```markdown
# <Account> — Tailored demo script
Demo env: <org>/<projects> · environment `<env>` · re-seed: `python traffic/run.py --minutes 15`
Verify status (last run <timestamp>): checkout ✅ · search ✅ · onboarding ⚠️ (replay missing)

| # | Journey | Show (link) | Say | Ask | Customer quote |
|---|---------|-------------|-----|-----|----------------|
| 1 | checkout | [Dashboard](…) | … | … | "…" — CTO, Gong 09/12 |
| 2 | checkout | [Trace](…) | … | … | |
| 3 | checkout | [Issue: PaymentGatewayTimeout](…) | … | … | |

## Live tricks
- Trigger a failure on the spot: open <app-url>/checkout?demo_fail=payment-timeout
- …

## If something breaks
- No data in the last 15 min → re-run traffic
- Trace missing backend spans → check trace propagation targets
```

Rules: follow the `demo_flow` order. Every row has a real, clickable link from the verify run. Quotes are verbatim and include their source, or are left out. Keep it to one screen if possible.

## docs/IMPLEMENTATION_GUIDE.md (for the customer, external)

```markdown
# Instrumenting <journey names> with Sentry

## What you'll get
One paragraph per journey: what question it answers for them.

## Per journey
### Checkout
- Spans to add (name, op, where in your code)
- Attributes (key, type, why), with PII guidance
- Failures to capture as errors
- Snippet for <their stack> (generic, not the demo app's internals)

## Dashboards & alerts
Import `sentry/dashboard.json` · recommended alerts with thresholds

## Production settings
Sampling recommendation, environment/release tagging, PII scrubbing

## Next step
"Want your coding agent to do this? Run `ce` on your service" (link to the CE kit), when relevant
```

Rules: no internal notes, no deal context, and nothing from Gong except what the customer themselves said they want.
