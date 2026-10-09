# Traffic and failure injection

A demo with an empty dashboard or a single trace isn't a demo. The goal is to have enough history to show charts that look real, with failures happening at believable rates.

## The failure-injection convention

All generated apps honor one request header:

```
X-Demo-Fail: <failure_id>[,<failure_id>...]
```

- The backend middleware reads the header and stores the requested failure IDs in request context.
- At the span named in `failures[].span`, the code checks whether its failure ID was requested. If it was, the code optionally sleeps `latency_ms` and then raises the spec's exception type with the spec's message.
- The frontend passes the header through when the page URL has `?demo_fail=<id>`, so the SE can trigger a failure live during the call.

Traffic stays dumb (it decides *when* to fail), the app stays honest (the failure is real code that raises a real exception), and the SE can reproduce any failure on demand.

## Backend traffic: `assets/traffic_runner.py`

```
python traffic/run.py --spec demo-spec.yaml --base-url http://localhost:8000 --minutes 30 --rps 2
```

- Picks a journey by `traffic.weight` and samples attribute values from `values`/`range`/`example`.
- Fills the `{attr}` placeholders in the steps and sends them in order.
- Adds `X-Demo-Fail` according to each failure's `rate`, biased by `when`.
- `--dry-run` prints the requests without sending them.

Copy it into the project as `traffic/run.py` during Phase 4.

## Frontend traffic: Playwright

Write one script per frontend journey (`traffic/<journey>.spec.ts` or `.py`):
- Drive the real UI (click, type, submit), because that's what produces `ui.action`/pageload spans and replays.
- Randomize the inputs from the spec's attribute values.
- Visit with `?demo_fail=<id>` for the fraction of runs set by the failure's rate.
- Loop with headless Chromium for N minutes.

## How much

- ≥ 500 traces per journey, or ~30 minutes of steady traffic, whichever comes first.
- Re-seed 15–30 minutes before the call so the "last 1h" views look alive.
- Vary latency on purpose. Add small random jitter, plus a slow tail on the attribute value the story is about (e.g. Adyen is slower).

## Telemetry-only mode

Skip the app. Write `traffic/generate.py` (or `.ts`) that uses the SDK to:
- Start a transaction or root span per journey run with child spans that match the spec, and set the attributes.
- Raise and capture the spec's exception types at the configured rates.
- Emit the spec's metrics and logs inside the active span.

Run it with a fixed seed so the shape of the data is reproducible.
