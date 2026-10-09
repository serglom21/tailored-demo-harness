#!/usr/bin/env python3
"""Build Sentry dashboard JSON from demo-spec.yaml (and optionally create it).

Usage:
  python build_dashboard.py demo-spec.yaml [--out sentry/dashboard.json] [--create]

--create POSTs each dashboard to the org (needs SENTRY_AUTH_TOKEN with org:write).
The payload targets span-based widgets (widgetType "spans"). If your Sentry version
rejects a field, adjust here or create the dashboard via the Sentry MCP / UI import.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import Sentry, attr_field, load_dotenv, load_spec, span_index, span_query  # noqa: E402

DISPLAY = {"line": "line", "area": "area", "bar": "bar", "table": "table", "big_number": "big_number"}


def widget_payload(w, span, layout_y):
    attr_types = {a["key"]: a.get("type") for a in span.get("attributes") or []}
    cols = [attr_field(g, attr_types.get(g)) for g in w.get("group_by") or []]
    agg = w["aggregate"]
    conditions = span_query(span) + (f' {w["query"]}' if w.get("query") else "")
    display = DISPLAY[w["display"]]
    is_table = display == "table"
    return {
        "title": w["title"],
        "displayType": display,
        "widgetType": "spans",
        "interval": "5m",
        "limit": w.get("limit", 5) if cols else None,
        "queries": [{
            "name": "",
            "fields": cols + [agg],
            "aggregates": [agg],
            "columns": cols,
            "fieldAliases": [],
            "conditions": conditions,
            "orderby": f"-{agg}" if (cols or is_table) else "",
        }],
        "layout": {"x": 0 if layout_y % 2 == 0 else 3, "y": (layout_y // 2) * 2,
                   "w": 6 if is_table else 3, "h": 2, "minH": 2},
    }


def build(spec):
    idx = span_index(spec)
    env = spec["demo_env"]
    out = []
    for d in spec.get("dashboards") or []:
        widgets = [widget_payload(w, idx[w["span"]], i) for i, w in enumerate(d.get("widgets") or [])]
        out.append({
            "title": d["title"],
            "widgets": widgets,
            "projects": [],  # resolved to IDs on --create
            "environment": [env["environment"]] if env.get("environment") else [],
            "period": "24h",
            "filters": {},
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="sentry/dashboard.json")
    ap.add_argument("--create", action="store_true")
    args = ap.parse_args()

    spec = load_spec(args.spec)
    dashboards = build(spec)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(dashboards[0] if len(dashboards) == 1 else dashboards, f, indent=2)
    print(f"Wrote {len(dashboards)} dashboard(s) → {args.out}")

    if args.create:
        load_dotenv()
        token = os.environ.get("SENTRY_AUTH_TOKEN")
        if not token:
            sys.exit("SENTRY_AUTH_TOKEN not set")
        org = os.environ.get("SENTRY_ORG") or spec["demo_env"]["org"]
        base = os.environ.get("SENTRY_BASE_URL", "https://sentry.io")
        sentry = Sentry(org, token, base)
        project_ids = [int(sentry.project_id(p)) for p in spec["demo_env"]["projects"].values() if p]
        for d in dashboards:
            d["projects"] = project_ids
            res = sentry.create_dashboard(d)
            print(f"Created: {base.rstrip('/')}/organizations/{org}/dashboard/{res.get('id')}/")


if __name__ == "__main__":
    main()
