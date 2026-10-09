# demo-spec.yaml format

The spec is the source of truth. `validate_spec.py` checks it, `verify_telemetry.py` verifies telemetry against it, and `build_dashboard.py` and `traffic_runner.py` both read it.

The `journeys[]` block intentionally follows the same structure as the `ce` CLI's `journeys.yaml`, so a demo spec can seed a real implementation spec later.

## Top level

| Field | Required | Notes |
|---|---|---|
| `version` | yes | `1` |
| `status` | yes | `draft` → `locked` after SE approval |
| `account` | yes | `name`, `slug` (kebab-case), `vertical`, `compelling_event`, `sources[]` (where the context came from) |
| `mode` | yes | `app` or `telemetry-only` |
| `stack` | yes | `frontend`, `backend`, `mobile` (any can be `null`) e.g. `nextjs`, `react`, `fastapi`, `express`, `django`, `go`, `react-native` |
| `demo_env` | yes | `org` (Sentry org slug), `projects` map (`frontend`/`backend`/`mobile` → project slug), `environment` (default `demo-<slug>`), `tags` map (always include `se` and `account`) |
| `journeys` | yes | 1–4 items, see below |
| `dashboards` | no | see below |
| `alerts` | no | see below |
| `demo_flow` | yes | ordered story for the call |

## journeys[]

```yaml
- id: checkout                 # kebab/snake, unique
  name: Checkout
  why: "They lose ~2% of orders when Adyen times out (CTO, discovery call)"
  source: "Gong 2026-09-12 — Discovery"
  slo: { p95_ms: 1500, error_rate: 0.02 }     # optional; drives alerts/talk track
  spans:
    - name: checkout.submit                   # becomes the span name/description
      op: ui.action                           # Sentry op convention
      layer: frontend                         # frontend | backend | mobile
      match: null                             # optional query override for verification
      attributes:
        - key: checkout.payment_provider
          type: string                        # string | number | boolean
          values: [stripe, adyen, paypal]     # for low-cardinality strings
          group_by: true                      # will be used in dashboards (cardinality ≤ ~20)
        - key: checkout.cart_value_usd
          type: number
          example: 129.99
          range: [5, 900]                     # optional, for traffic generation
        - key: user.email
          type: string
          pii: true                           # must be redacted/hashed, never sent raw
  metrics:                                    # optional
    - name: checkout.completed
      type: counter                           # counter | gauge | distribution
      unit: none
      attributes: [checkout.payment_provider]
  logs:                                       # optional
    - message: "payment declined"
      level: warn
      attributes: [checkout.payment_provider]
  failures:                                   # at least one
    - id: payment-timeout
      span: payment.authorize                 # must exist in this journey's spans
      rate: 0.08                              # 0–1, share of journey runs
      error: PaymentGatewayTimeout            # exception type
      message: "Gateway did not respond within 5000ms"
      latency_ms: 5000                        # optional: slow before failing
      when: { checkout.payment_provider: adyen }   # optional bias
  traffic:                                    # used by traffic_runner.py (backend HTTP)
    weight: 3                                 # relative frequency vs other journeys
    steps:
      - method: GET
        path: /api/products
      - method: POST
        path: /api/checkout
        body: { provider: "{checkout.payment_provider}", amount: "{checkout.cart_value_usd}" }
```

`{attribute.key}` placeholders inside `traffic.steps[].body` and `path` are filled with values sampled from that attribute's `values`/`range`/`example`.

## dashboards[]

```yaml
- title: "Acme Pay — Checkout health"
  widgets:
    - title: "p95 authorize latency by provider"
      display: line            # line | area | bar | table | big_number
      span: payment.authorize  # must be a span in the spec (builds the query)
      aggregate: p95(span.duration)
      group_by: [checkout.payment_provider]   # must be attributes on that span
      query: null              # optional extra conditions
      limit: 5
```

## alerts[]

```yaml
- name: "Checkout p95 above SLO"
  span: checkout.submit
  aggregate: p95(span.duration)
  threshold: 1500
  window_min: 10
```

## demo_flow[]

```yaml
- journey: checkout
  show: dashboard            # dashboard | trace | issue | replay | explore | alert
  say: "Here's checkout latency split by provider — Adyen is the outlier you mentioned."
  ask: "Is provider the dimension your on-call would slice by first?"
  quote: "We lose about 2% of orders when Adyen times out."   # optional, verbatim only
```

## Validation rules (enforced by validate_spec.py)

- All required top-level fields are present, and `mode`/`status` have valid values.
- Journey IDs are unique. Each journey has ≥1 span and ≥1 failure.
- Every `failures[].span` and dashboard/alert `span` refers to a defined span.
- Every widget `group_by` key is an attribute on that widget's span.
- `group_by: true` string attributes have `values` with ≤ 20 entries.
- `pii: true` attributes are never used in `group_by` or dashboards.
- Failure `rate` is between 0 and 1.
- Every `demo_flow[].journey` exists.
- `demo_env.tags` includes `se` and `account`.
