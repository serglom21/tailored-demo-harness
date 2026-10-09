# Instrumentation rules

These rules are the Sentry opinions the agent wouldn't have on its own. Apply them when writing the spec and the code.

**Always confirm current SDK method names and init options via the Sentry MCP or docs.sentry.io before writing code.** The APIs change, so the rules below describe intent, not syntax.

## Pick the right signal

| The customer wants to… | Use |
|---|---|
| See how long a step takes, find slow outliers, follow a request across services | **Span** with attributes |
| Count business outcomes (orders, signups, retries) or track a value over time cheaply | **Metric** (counter / gauge / distribution) |
| Keep a searchable record of what happened (decline reasons, config states) | **Log**, connected to the trace |
| Get paged and triaged when something breaks | **Error** (exception) → Issue, plus an alert |
| See what the user saw | **Session Replay** (frontend only) |

Default to **spans with attributes**, since that's what makes Explore and dashboards useful. Add a metric only when the customer explicitly cares about a count or rate that spans don't model well. Don't duplicate the same signal three ways just to show SKUs.

## Naming

- Span names: `<domain>.<action>`, lowercase, stable, and **without IDs or user input** (`checkout.submit`, not `checkout for order 123`).
- Span ops: follow Sentry conventions where one exists (`http.client`, `http.server`, `db.query`, `ui.action`, `ui.load`, `queue.publish`, `queue.process`, `cache.get`). Use `function` for custom business logic.
- Attribute keys: namespaced and snake_case (`checkout.payment_provider`, `search.result_count`). Reuse the customer's own words for domain concepts.

## Attributes

- **Types matter.** Numbers must be sent as numbers, otherwise they can't be aggregated (p95, avg, sum). Booleans should be booleans.
- **Cardinality.** Anything you'll `group_by` needs ≤ ~20 distinct values. High-cardinality values (order ID, user ID) are fine as attributes for lookup, but never group by them.
- **Put attributes on the span where the decision happens** (the provider on the authorize span, not only on the page-load span).
- Aim for 2–5 attributes per span. Each one should answer a question the customer asked.

## PII

- `pii: true` attributes must be hashed or dropped before they're sent. In app mode, show the redaction in code. It's a good talking point.
- Never put emails, names, or card data in span names, log messages, or error messages.
- Use fictional users only (`user_0042`, `demo+42@example.com`).

## Distributed tracing

- Frontend → backend calls must propagate trace headers so a single trace covers both layers. Verify this explicitly. It's the most common demo-breaker.
- Backend → mock third party (payment gateway, search vendor): model it as an `http.client` span to a fake host, which makes the third-party dependency visible.

## Errors

- Every failure mode raises a **real exception type** named in the spec (`PaymentGatewayTimeout`). Don't capture a string message, because typed exceptions group cleanly into issues.
- Add the failure's relevant attributes as tags/context so the issue can be filtered the same way the dashboard is.
- Attach the release and environment so release health and suspect commits work if you show them.

## Sampling

- Demo environments use 100% traces and 100% replay-on-error. In the implementation guide, tell the customer what production sampling should look like. Never recommend 100% there.
