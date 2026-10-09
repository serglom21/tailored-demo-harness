# Project setup

One folder per demo. Everything the agent needs to resume is inside it.

## Layout

```
acme-pay-demo/
├── CLAUDE.md                 # from assets/project-CLAUDE.md — project memory for the agent
├── demo-spec.yaml            # source of truth (Phase 2)
├── context-brief.md          # Phase 1 output, with sources
├── .env.example              # committed; .env is gitignored
├── .env                      # DSNs, org, auth token (SE fills in)
├── .mcp.json                 # Sentry MCP for this project (optional if configured globally)
├── app/                      # app mode only
│   ├── web/                  # frontend
│   └── api/                  # backend
├── traffic/
│   ├── run.py                # copy of assets/traffic_runner.py
│   └── *.spec.ts             # Playwright journeys
├── sentry/
│   ├── dashboard.json
│   └── verify-report.json    # last verify_telemetry.py result
└── docs/
    ├── DEMO_SCRIPT.md
    └── IMPLEMENTATION_GUIDE.md
```

## Sentry side (one-time per SE, then per demo)

- Use the shared demo org (or your own sandbox org). Create one project per layer, e.g. `acme-pay-web` and `acme-pay-api`, or reuse generic ones and rely on `environment` + `account` tags to separate demos.
- Create an auth token with `project:read`, `event:read`, and `org:read`. Add `org:write` only if you want `build_dashboard.py --create` to create the dashboard.

## .env

```
SENTRY_ORG=demo
SENTRY_AUTH_TOKEN=            # for verify/dashboard scripts
SENTRY_DSN_FRONTEND=
SENTRY_DSN_BACKEND=
SENTRY_ENVIRONMENT=demo-acme-pay
SENTRY_BASE_URL=https://sentry.io
```

## Sentry MCP

Claude Code (per project or user scope):

```
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

Or add it to `.mcp.json`. Authenticate when prompted. The agent uses it to look up current SDK docs and to query spans and issues during verification. When the MCP isn't available, the REST scripts in `scripts/` cover verification.

## Running it

```
mkdir acme-pay-demo && cd acme-pay-demo && git init
claude
> /tailored-demo Acme Pay — they want checkout latency by payment provider and KYC drop-off
```

The skill stops once, after the spec, for your approval. To resume later in the same folder:

```
> /tailored-demo continue
```

It reads `demo-spec.yaml` and picks up at the first phase whose outputs are missing.
