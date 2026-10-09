# Tailored Demo Harness

A Claude skill that turns an account or a use case into a working Sentry demo: a locked spec, a small instrumented app or synthetic telemetry, realistic traffic with injected failures, verified data in a demo org, dashboards and alerts, and a demo script.

`demo-spec.yaml` is the source of truth. Later artifacts are built from it, and its journeys use the same shape as the `ce` CLI so the spec you demo with can become the spec the customer implements.

## Install

Clone this repo into your Claude Code skills directory. The folder name can be anything; the skill name comes from `SKILL.md` (`tailored-demo`).

```bash
git clone https://github.com/serglom21/tailored-demo-harness.git ~/.claude/skills/tailored-demo
```

Start a new Claude Code session. The skill is available as `/tailored-demo`.

To install it for one project instead of your user:

```bash
mkdir -p .claude/skills
git clone https://github.com/serglom21/tailored-demo-harness.git .claude/skills/tailored-demo
```

## What you need

- **Claude Code.** Phases 1–2 (context and spec) can run in Cowork or Claude Code. Phases 3–6 need a local shell that can run servers and a browser.
- **Python 3** and PyYAML: `pip install pyyaml`
- **A Sentry demo org** (or your sandbox). Never send telemetry to a customer's production org.
- **An auth token** with `project:read`, `event:read`, and `org:read`. Add `org:write` only if you want `build_dashboard.py --create` to create the dashboard.
- **Sentry MCP** (optional, recommended). The agent uses it for current SDK docs and for querying spans and issues. If it is missing, the REST scripts in `scripts/` cover verification.

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

When the prompt names an account, the skill also calls context skills for Gong, Notion, Slack, and an existing Sentry snapshot. If a source is unreachable, it says so and continues. It does not invent quotes or requirements.

## Run a demo

One folder per demo. Start outside this harness repo:

```bash
mkdir acme-pay-demo && cd acme-pay-demo && git init
claude
```

```text
/tailored-demo Acme Pay — they want checkout latency by payment provider and KYC drop-off
```

The skill stops once, after it writes `demo-spec.yaml`, and shows journeys, attributes, failure modes, dashboards, mode, and stack. Approve or edit that summary before it builds. After approval it sets `status: locked`.

To resume later in the same folder:

```text
/tailored-demo continue
```

It reads `demo-spec.yaml` and picks up at the first phase whose outputs are missing.

If you are in a sandbox that cannot keep servers running, finish Phase 2, let it write the project scaffold, and continue in Claude Code with `/tailored-demo continue`.

## What a demo folder looks like

```text
acme-pay-demo/
├── CLAUDE.md                 # from assets/project-CLAUDE.md
├── demo-spec.yaml            # source of truth
├── context-brief.md
├── .env.example              # committed
├── .env                      # DSNs, org, token — gitignored
├── app/                      # app mode only
├── traffic/
│   ├── run.py                # copy of assets/traffic_runner.py
│   └── *.spec.ts             # Playwright journeys
├── sentry/
│   ├── dashboard.json
│   └── verify-report.json
└── docs/
    ├── DEMO_SCRIPT.md
    └── IMPLEMENTATION_GUIDE.md
```

Copy `assets/.env.example` into the demo folder as `.env` and fill it in:

```text
SENTRY_ORG=demo
SENTRY_AUTH_TOKEN=
SENTRY_DSN_FRONTEND=
SENTRY_DSN_BACKEND=
SENTRY_ENVIRONMENT=demo-acme-pay
SENTRY_BASE_URL=https://sentry.io
```

Secrets stay in `.env`. Do not put them in the spec or in `CLAUDE.md`.

## Phases

| Phase | What happens |
|---|---|
| 0. Setup | Creates `app/`, `traffic/`, `sentry/`, `docs/`, copies `CLAUDE.md` and `.env.example`, checks for the Sentry MCP. |
| 1. Context | Pulls calls, Notion, Slack, and existing Sentry state into a context brief of at most 15 lines. With no account, it builds the brief from your use case and `references/verticals.md`. |
| 2. Spec | Writes `demo-spec.yaml` (2–4 journeys, each with a reason, spans, attributes, and at least one failure). Runs `validate_spec.py`. **Stops for your approval.** |
| 3. Build | **`app`**: a small stack-matched app, instrumented exactly to the spec, with failures behind `X-Demo-Fail`. **`telemetry-only`**: a generator under `traffic/` that emits the spec directly. |
| 4. Traffic | Backend journeys go through `traffic/run.py`. Frontend journeys use Playwright so spans and replays are real. Default volume is about 30 minutes of history or at least 500 traces per journey. |
| 5. Verify | Checks that spans, attributes, failure rates, and dashboard queries landed. Fixes and re-runs up to 3 times. A demo is ready only when this is green. |
| 6. Handoff | Writes `sentry/dashboard.json` (and can POST it), lists alerts, and writes `docs/DEMO_SCRIPT.md` plus `docs/IMPLEMENTATION_GUIDE.md`. |

## Scripts

Run these from the demo folder. Paths below assume the user-level install.

```bash
python ~/.claude/skills/tailored-demo/scripts/validate_spec.py demo-spec.yaml
python ~/.claude/skills/tailored-demo/scripts/verify_telemetry.py demo-spec.yaml
python ~/.claude/skills/tailored-demo/scripts/verify_telemetry.py demo-spec.yaml --plan
python ~/.claude/skills/tailored-demo/scripts/build_dashboard.py demo-spec.yaml
python ~/.claude/skills/tailored-demo/scripts/build_dashboard.py demo-spec.yaml --create
```

`--plan` prints the Sentry queries without calling the API. `--create` needs `org:write`.

Re-seed data before a call:

```bash
python traffic/run.py --spec demo-spec.yaml --base-url http://localhost:8000 --minutes 15
```

Trigger a failure on the spot with the header `X-Demo-Fail: <failure_id>` or `?demo_fail=<failure_id>`.

## What's in this repo

| Path | Purpose |
|---|---|
| `SKILL.md` | Instructions the agent follows |
| `references/project-setup.md` | Folder layout, `.env`, MCP setup |
| `references/spec-schema.md` | Full `demo-spec.yaml` format |
| `references/instrumentation-rules.md` | Naming, attributes, span vs metric vs log, PII |
| `references/verticals.md` | Starter journeys by industry |
| `references/traffic-and-failures.md` | Traffic generation and failure injection |
| `references/handoff.md` | Formats for the demo script and implementation guide |
| `assets/demo-spec.example.yaml` | A complete worked example |
| `assets/.env.example` | Env template copied into each demo |
| `assets/project-CLAUDE.md` | Project memory copied into each demo as `CLAUDE.md` |
| `assets/traffic_runner.py` | HTTP traffic driver; copied to `traffic/run.py` |
| `scripts/validate_spec.py` | Spec checks (exit 0 = valid) |
| `scripts/verify_telemetry.py` | Confirms telemetry landed in Sentry |
| `scripts/build_dashboard.py` | Builds dashboard JSON, optionally creates it |

## Guardrails

- Use only fictional data. Do not put real customer data, real end-user names, or the customer's logo or branding in the demo UI.
- Send events only to the demo org and projects named in the spec.
- Keep cardinality low on attributes used in `group_by` (about 20 values or fewer).
- Redact anything marked `pii: true`.
