# {{ACCOUNT_NAME}} — Tailored Sentry demo

This project was set up by the `tailored-demo` skill. SE: {{SE_HANDLE}}. Demo date: {{DEMO_DATE}}.

## Ground rules for any agent working here
- `demo-spec.yaml` is the source of truth. Change the spec first, then the code, then re-verify.
- Only instrument what the spec defines: the same span names, ops, attribute keys and types.
- Before writing SDK code, check current Sentry SDK APIs through the Sentry MCP or docs.sentry.io.
- All failures go through the `X-Demo-Fail` header / `?demo_fail=` convention. Never add random failures in app code.
- Use only fictional data. Never write secrets outside `.env`. Send to the demo org/projects in the spec only.
- A demo is "ready" only when `python <skill>/scripts/verify_telemetry.py demo-spec.yaml` is green.

## Commands
- App: see `app/README.md` (written during build)
- Traffic: `python traffic/run.py --spec demo-spec.yaml --base-url http://localhost:8000 --minutes 15`
- Verify: `python <skill>/scripts/verify_telemetry.py demo-spec.yaml`
- Dashboard: `python <skill>/scripts/build_dashboard.py demo-spec.yaml [--create]`

## Status
<!-- the skill updates this after each phase -->
- [ ] Context brief
- [ ] Spec locked
- [ ] Built
- [ ] Traffic running
- [ ] Verified
- [ ] Dashboards + handoff docs
