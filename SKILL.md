---
name: tailored-demo
description: Build a customer-tailored, instrumented Sentry demo end to end — from the account's real context (Gong, Notion, Slack) to a locked demo spec, a small app or synthetic telemetry instrumented to that spec, realistic traffic with injected failures, verified data in the demo org, dashboards/alerts, and a demo script. Use when an SE says "build a tailored demo for [account]", "custom demo for [account]", "spin up a demo showing [use case]", "make a demo app that tracks [X]", "demo environment for [account]", or wants to show a prospect their own critical journeys in Sentry. Prefer demo-plan-generator when the SE only wants a talk track over the generic demo, with nothing built.
---

# Tailored Demo

Turns "here's what this customer wants to track" into a working demo in Sentry that has data in it.

## Why this skill exists

Coding agents can already build a Next.js or FastAPI app in minutes, so this skill doesn't. What agents don't know is:

1. **What to instrument** for this customer: which journeys matter, which attributes they will slice by, and spans vs metrics vs logs.
2. **How to make it believable**: realistic traffic, realistic failures, low-cardinality attributes, no empty dashboards.
3. **Whether it actually worked**: did the spans and attributes land in Sentry, and does the dashboard render?

That knowledge lives here. Everything else is delegated to the agent.

The **demo spec** (`demo-spec.yaml`) is the single source of truth. Every later artifact is built from it, and it uses the same journey format as the `ce` CLI (Critical Experience). That way, the spec you demo with can become the spec the customer implements later.

## Inputs

- **Required:** an account name, or a free-text use case ("fintech checkout, wants to slice latency by payment provider").
- **Optional:** stack override, mode (`app` | `telemetry-only`), target Sentry org/projects, demo date.

If neither an account nor a use case is given, ask for one before doing anything.

## Where this runs

- Phases 1–2 (context + spec) work anywhere: Cowork or Claude Code.
- Phases 3–6 need a real local shell that can run servers and a browser, so use **Claude Code** inside the project folder. If you're in a sandbox that can't keep servers running, finish Phase 2, write the project scaffold, and tell the SE to continue in Claude Code with `/tailored-demo continue`.

## Phase 0 — Project setup

If the current folder has no `demo-spec.yaml`, set up the project (see `references/project-setup.md`):

1. Create the layout: `app/`, `traffic/`, `sentry/`, `docs/`.
2. Copy `assets/project-CLAUDE.md` → `./CLAUDE.md` and fill in the account name and SE handle.
3. Copy `assets/.env.example` → `./.env.example`. Ask the SE for DSNs/org/token, or tell them which vars to fill. **Never write secrets into the spec or CLAUDE.md.**
4. Check that the Sentry MCP server is available. If it isn't, tell the SE how to add it (see `references/project-setup.md`), and fall back to the REST scripts in `scripts/`.

If `demo-spec.yaml` already exists, read it and resume at the earliest phase whose outputs are missing.

## Phase 1 — Context

When an account is named, pull context with the existing core skills, in parallel where possible:

| Source | Skill | What to extract |
|---|---|---|
| Calls | `core-skills:get-gong-data` | Compelling event, what they want to track, verbatim quotes, stack mentions |
| Notion | `core-skills:get-notion-data` | Opp page, POC success criteria, technical notes |
| Slack | `core-skills:get-customer-slack` | Objections, recent asks, stakeholders |
| Sentry (if existing org) | `core-skills:get-current-state-snapshot` | Current SDKs/platforms, what's already instrumented |

Distill this into a **context brief** of no more than 15 lines: vertical, stack, top 2–4 journeys they care about, the attributes they'd slice by, the pain/compelling event, and 2–3 quotes with sources.

If a source is unreachable, say which one and continue. Don't invent quotes or requirements. If there's no account, build the brief from the free-text use case plus `references/verticals.md`.

## Phase 2 — Demo spec (SE checkpoint)

Write `demo-spec.yaml` following `references/spec-schema.md`, applying `references/instrumentation-rules.md`. Rules of thumb:

- **2–4 journeys.** Each needs a `why`: a quote or reason traceable to the context brief.
- Per journey: spans (frontend + backend where relevant), attributes with types and example values, optional metrics/logs, and **at least one failure mode** with a rate.
- Dashboards and alerts must only query attributes that the spec emits.
- `demo_flow`: the ordered story for the call, referencing journey IDs.

Run `python scripts/validate_spec.py demo-spec.yaml` and fix every error.

**Stop and show the SE a short summary:** journeys, key attributes, failure modes, dashboards, mode, and stack. Get approval or edits before building. This is the only mandatory pause. After approval, set `status: locked` in the spec.

## Phase 3 — Build

Choose based on `mode`:

**`app` mode** (default when the customer needs to see code, or the demo is about SDK setup):
- Match the customer's stack where possible (from context). Otherwise use Next.js + a small backend in their backend language.
- Build only what the journeys need, usually 2–5 screens/endpoints. No auth, no real payments, no database unless a journey is about the DB.
- **Look up current SDK APIs** via the Sentry MCP or docs.sentry.io before writing instrumentation code. Do not rely on memory for SDK method names or init options.
- Instrument exactly what the spec says: same span names/ops, attribute keys, and types. Redact anything with `pii: true`.
- Implement **failure injection** through the `X-Demo-Fail: <failure_id>` header convention (see `references/traffic-and-failures.md`), so traffic can trigger failures deterministically.
- Tag every event with `environment` and the `demo_env.tags` from the spec (e.g. `se`, `account`).

**`telemetry-only` mode** (use when the point is "what you'll see in Sentry", not the code):
- Write a single generator under `traffic/` that uses the SDK (or OTLP) to emit the spec's traces, attributes, metrics, logs, and errors directly. There's no app to maintain.

## Phase 4 — Traffic

Follow `references/traffic-and-failures.md`:
- Backend journeys: `assets/traffic_runner.py` drives HTTP steps from the spec and applies failure rates through the header.
- Frontend journeys: write a short Playwright script per journey under `traffic/`. Real browser sessions are what produce frontend spans and replays.
- Run enough traffic for the charts to look real: by default ~30 min of history or ≥500 traces per journey. Vary the attribute values using the spec's `values`/`example`.

## Phase 5 — Verify (loop until green)

Run `python scripts/verify_telemetry.py demo-spec.yaml`, or use the Sentry MCP to run the same checks. For each journey, check:
- Each span arrives (count > 0 in the demo environment).
- Each attribute is present (`has:<key>`) and has the right type. Numeric attributes must be aggregatable.
- Each failure mode shows up as an error/issue at roughly its configured rate.
- Each dashboard widget query returns data.

When a check fails, fix the instrumentation or traffic, re-run traffic, and verify again. **Stop after 3 loops** and report what's still failing and why. Never tell the SE the demo is ready while checks are red.

## Phase 6 — Dashboards, alerts, handoff

1. `python scripts/build_dashboard.py demo-spec.yaml` writes `sentry/dashboard.json`. Add `--create` to POST it to the org (needs a token with `org:write`). Alternatively, create it through the MCP if that's supported.
2. Create the spec's alerts the same way, or list them in `docs/` for manual setup if the API path isn't available.
3. Write `docs/DEMO_SCRIPT.md` in the format in `references/handoff.md`: the click path in `demo_flow` order, with direct links to traces, dashboards, and issues, plus customer quotes and questions to ask at each step.
4. Write `docs/IMPLEMENTATION_GUIDE.md`, the customer-facing "how to do this in your code" doc. Use generic snippets per journey, not the demo app's internals.
5. If `app` mode and the SE wants it, push the repo with `gh repo create` (private by default).

## Output to the SE

End with a short message:
- Status: green/red per journey from the last verify run.
- Links: dashboard, one example trace per journey, and the repo (if pushed).
- Files: `demo-spec.yaml`, `docs/DEMO_SCRIPT.md`, `docs/IMPLEMENTATION_GUIDE.md`, `sentry/dashboard.json`.
- One line: "To re-seed data before the call: `python traffic/run.py --minutes 15`" (or the equivalent).
- An offer to post a summary to the account's opp channel (`core-skills:compose-slack-message`).

## Guardrails

- Use only fictional data in the demo. Never use real customer data, names of real end users, or the customer's logo or branding in the app UI.
- Send to the **demo org/projects in the spec**, never to the customer's production org.
- Keep attribute cardinality low on anything used in `group_by` (≤ ~20 values).
- Secrets live only in `.env`, which is gitignored.

## Reference files

- `references/project-setup.md`: folder layout, `.env`, MCP setup, running in Claude Code
- `references/spec-schema.md`: the full `demo-spec.yaml` format, with field rules
- `references/instrumentation-rules.md`: naming, attributes, span vs metric vs log, PII
- `references/verticals.md`: starter journey patterns by industry
- `references/traffic-and-failures.md`: traffic generation and the failure-injection convention
- `references/handoff.md`: formats for DEMO_SCRIPT.md and IMPLEMENTATION_GUIDE.md
- `assets/demo-spec.example.yaml`: a complete worked example
- `scripts/validate_spec.py`, `scripts/verify_telemetry.py`, `scripts/build_dashboard.py`, `assets/traffic_runner.py`
