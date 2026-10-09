#!/usr/bin/env python3
"""Verify that the telemetry described in demo-spec.yaml actually landed in Sentry.

Checks per journey:
  - each span arrives (count > 0)
  - each non-PII attribute is present on that span
  - each failure mode shows up as errors, at roughly its configured rate
  - each dashboard widget query returns data

Usage:
  python verify_telemetry.py demo-spec.yaml [--period 24h] [--out sentry/verify-report.json] [--plan]

Env (or .env): SENTRY_ORG, SENTRY_AUTH_TOKEN, SENTRY_BASE_URL (default https://sentry.io)
--plan prints the queries it would run, without calling Sentry (useful with the Sentry MCP).

Note: Sentry's search syntax for custom span attributes can vary by dataset/version. If a
check errors with HTTP 400, set `match:` on that span in the spec, or run the printed
query through the Sentry MCP instead.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import Sentry, attr_has_query, load_dotenv, load_spec, span_index, span_query  # noqa: E402

RATE_TOLERANCE = 0.5  # observed rate may be within ±50% of configured


def plan(spec):
    env = spec["demo_env"]
    idx = span_index(spec)
    checks = []
    for j in spec["journeys"]:
        for s in j["spans"]:
            proj = env["projects"].get(s["layer"])
            base = span_query(s)
            checks.append(("span", j["id"], s["name"], "spans", base, proj, None))
            for a in s.get("attributes") or []:
                if a.get("pii"):
                    # PII must NOT be present raw; flag for manual check
                    checks.append(("pii", j["id"], f'{s["name"]}.{a["key"]}', "spans",
                                   f"{base} {attr_has_query(a)}", proj, None))
                    continue
                checks.append(("attr", j["id"], f'{s["name"]}.{a["key"]}', "spans",
                               f"{base} {attr_has_query(a)}", proj, None))
        for fl in j.get("failures") or []:
            sp = idx[fl["span"]]
            proj = env["projects"].get(sp["layer"])
            checks.append(("failure", j["id"], fl["id"], "errors",
                           f'error.type:{fl["error"]}', proj, fl))
    for d in spec.get("dashboards") or []:
        for w in d.get("widgets") or []:
            sp = idx.get(w["span"])
            if not sp:
                continue
            q = span_query(sp) + (f' {w["query"]}' if w.get("query") else "")
            checks.append(("widget", sp["journey"], w["title"], "spans", q,
                           env["projects"].get(sp["layer"]), None))
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--period", default="24h")
    ap.add_argument("--out", default="sentry/verify-report.json")
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args()

    spec = load_spec(args.spec)
    env = spec["demo_env"]
    environment = env.get("environment")
    checks = plan(spec)

    if args.plan:
        for kind, jid, name, ds, q, proj, _ in checks:
            print(f"[{kind:7}] {jid:12} {name:45} dataset={ds} project={proj} env={environment}\n          query: {q}")
        return

    load_dotenv()
    org = os.environ.get("SENTRY_ORG") or env["org"]
    token = os.environ.get("SENTRY_AUTH_TOKEN")
    if not token:
        sys.exit("SENTRY_AUTH_TOKEN not set (use --plan to print queries instead)")
    sentry = Sentry(org, token, os.environ.get("SENTRY_BASE_URL", "https://sentry.io"))

    results, span_counts = [], {}
    for kind, jid, name, ds, q, proj, fl in checks:
        r = {"kind": kind, "journey": jid, "name": name, "query": q}
        try:
            n = sentry.count(ds, q, [proj], environment, args.period)
            r["count"] = n
            if kind == "span":
                span_counts[name] = n
                r["ok"] = n > 0
            elif kind == "attr":
                parent = span_counts.get(name.rsplit(".", 1)[0]) or 0
                r["ok"] = n > 0
                r["coverage"] = round(n / parent, 3) if parent else None
            elif kind == "pii":
                # presence of a PII attribute is acceptable only if hashed; flag for review
                r["ok"] = True
                r["note"] = "present — confirm value is hashed/redacted" if n else "not sent (good)"
            elif kind == "failure":
                parent = span_counts.get(fl["span"]) or 0
                observed = n / parent if parent else 0
                r["observed_rate"] = round(observed, 3)
                r["expected_rate"] = fl["rate"]
                low = fl["rate"] * (1 - RATE_TOLERANCE)
                r["ok"] = n > 0 and observed >= low
                if fl.get("when"):
                    r["note"] = "rate is biased by `when`; overall rate is expected to be lower"
                    r["ok"] = n > 0
            elif kind == "widget":
                r["ok"] = n > 0
        except Exception as e:  # noqa: BLE001
            r["ok"] = False
            r["error"] = str(e)
        results.append(r)
        mark = "✅" if r["ok"] else "❌"
        extra = r.get("error") or r.get("note") or (
            f'rate {r.get("observed_rate")} vs {r.get("expected_rate")}' if kind == "failure" else f'count={r.get("count")}')
        print(f"{mark} [{kind:7}] {jid:12} {name:45} {extra}")

    journeys = {}
    for r in results:
        journeys.setdefault(r["journey"], True)
        journeys[r["journey"]] &= r["ok"]
    summary = {"environment": environment, "period": args.period,
               "journeys": {k: ("green" if v else "red") for k, v in journeys.items()},
               "checks": results}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print("\n" + " · ".join(f"{k} {'✅' if v == 'green' else '❌'}" for k, v in summary["journeys"].items()))
    print(f"Report: {args.out}")
    sys.exit(0 if all(journeys.values()) else 1)


if __name__ == "__main__":
    main()
