#!/usr/bin/env python3
"""Validate a tailored-demo spec (demo-spec.yaml).

Usage: python validate_spec.py demo-spec.yaml
Exit 0 = valid (warnings allowed), 1 = errors.
"""
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

MODES = {"app", "telemetry-only"}
STATUSES = {"draft", "locked"}
ATTR_TYPES = {"string", "number", "boolean"}
LAYERS = {"frontend", "backend", "mobile"}
DISPLAYS = {"line", "area", "bar", "table", "big_number"}
SHOWS = {"dashboard", "trace", "issue", "replay", "explore", "alert"}
MAX_GROUP_BY_VALUES = 20


def load(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def validate(spec):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    for field in ("version", "status", "account", "mode", "stack", "demo_env", "journeys", "demo_flow"):
        if field not in spec:
            err(f"missing top-level field: {field}")
    if errors:
        return errors, warnings

    if spec["status"] not in STATUSES:
        err(f"status must be one of {sorted(STATUSES)}")
    if spec["mode"] not in MODES:
        err(f"mode must be one of {sorted(MODES)}")

    acct = spec["account"] or {}
    for k in ("name", "slug", "vertical", "compelling_event"):
        if not acct.get(k):
            err(f"account.{k} is required")
    if not acct.get("sources"):
        warn("account.sources is empty — where did the requirements come from?")

    env = spec["demo_env"] or {}
    for k in ("org", "projects", "environment"):
        if not env.get(k):
            err(f"demo_env.{k} is required")
    tags = env.get("tags") or {}
    for k in ("se", "account"):
        if k not in tags:
            err(f"demo_env.tags.{k} is required")

    journeys = spec["journeys"] or []
    if not 1 <= len(journeys) <= 4:
        err(f"journeys: expected 1–4, got {len(journeys)}")

    span_index = {}  # span name -> {attr key -> attr}
    journey_ids = set()
    for j in journeys:
        jid = j.get("id") or "<missing id>"
        if jid in journey_ids:
            err(f"duplicate journey id: {jid}")
        journey_ids.add(jid)
        if not j.get("why"):
            err(f"journey {jid}: 'why' is required (trace it to the customer)")
        spans = j.get("spans") or []
        if not spans:
            err(f"journey {jid}: needs at least one span")
        local_spans = set()
        for s in spans:
            sname = s.get("name")
            if not sname:
                err(f"journey {jid}: span missing name")
                continue
            if any(ch.isdigit() for ch in sname.split(".")[-1]) and len(sname) > 40:
                warn(f"span {sname}: looks dynamic — span names must be stable")
            if not s.get("op"):
                err(f"span {sname}: op is required")
            if s.get("layer") not in LAYERS:
                err(f"span {sname}: layer must be one of {sorted(LAYERS)}")
            proj = (env.get("projects") or {}).get(s.get("layer"))
            if spec["mode"] == "app" and s.get("layer") in LAYERS and not proj:
                err(f"span {sname}: no demo_env.projects.{s.get('layer')} defined")
            attrs = {}
            for a in s.get("attributes") or []:
                key = a.get("key")
                if not key:
                    err(f"span {sname}: attribute missing key")
                    continue
                if a.get("type") not in ATTR_TYPES:
                    err(f"{sname}.{key}: type must be one of {sorted(ATTR_TYPES)}")
                if a.get("group_by"):
                    if a.get("pii"):
                        err(f"{sname}.{key}: pii attribute cannot be group_by")
                    if a.get("type") == "string":
                        vals = a.get("values") or []
                        if not vals:
                            err(f"{sname}.{key}: group_by string needs 'values'")
                        elif len(vals) > MAX_GROUP_BY_VALUES:
                            err(f"{sname}.{key}: {len(vals)} values > {MAX_GROUP_BY_VALUES} (cardinality)")
                if a.get("type") == "number" and a.get("example") is not None and not isinstance(a["example"], (int, float)):
                    err(f"{sname}.{key}: number attribute example must be numeric")
                attrs[key] = a
            if sname in span_index and span_index[sname] != attrs:
                warn(f"span {sname} defined more than once with different attributes; merging")
                span_index[sname] = {**span_index[sname], **attrs}
            else:
                span_index[sname] = attrs
            local_spans.add(sname)

        failures = j.get("failures") or []
        if not failures:
            err(f"journey {jid}: needs at least one failure mode")
        for fl in failures:
            fid = fl.get("id") or "<missing id>"
            if fl.get("span") not in local_spans:
                err(f"failure {fid}: span '{fl.get('span')}' not defined in journey {jid}")
            rate = fl.get("rate")
            if not isinstance(rate, (int, float)) or not 0 < rate <= 1:
                err(f"failure {fid}: rate must be in (0, 1]")
            if not fl.get("error"):
                err(f"failure {fid}: 'error' (exception type) is required")
            for k in (fl.get("when") or {}):
                if k not in span_index.get(fl.get("span"), {}):
                    warn(f"failure {fid}: 'when' key {k} is not an attribute on {fl.get('span')}")

        if spec["mode"] == "app" and any(s.get("layer") == "backend" for s in spans):
            if not (j.get("traffic") or {}).get("steps"):
                warn(f"journey {jid}: no traffic.steps — backend traffic runner can't drive it")

    for d in spec.get("dashboards") or []:
        for w in d.get("widgets") or []:
            t = w.get("title", "<untitled>")
            if w.get("display") not in DISPLAYS:
                err(f"widget '{t}': display must be one of {sorted(DISPLAYS)}")
            sp = w.get("span")
            if sp not in span_index:
                err(f"widget '{t}': span '{sp}' not defined")
                continue
            if not w.get("aggregate"):
                err(f"widget '{t}': aggregate is required")
            for g in w.get("group_by") or []:
                a = span_index[sp].get(g)
                if not a:
                    err(f"widget '{t}': group_by '{g}' is not an attribute of {sp}")
                elif a.get("pii"):
                    err(f"widget '{t}': group_by '{g}' is PII")

    for al in spec.get("alerts") or []:
        if al.get("span") not in span_index:
            err(f"alert '{al.get('name')}': span '{al.get('span')}' not defined")

    flow = spec["demo_flow"] or []
    if not flow:
        err("demo_flow is empty")
    for i, step in enumerate(flow, 1):
        if step.get("journey") not in journey_ids:
            err(f"demo_flow[{i}]: journey '{step.get('journey')}' not defined")
        if step.get("show") not in SHOWS:
            err(f"demo_flow[{i}]: show must be one of {sorted(SHOWS)}")
        if not step.get("say"):
            warn(f"demo_flow[{i}]: no 'say' talking point")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    errors, warnings = validate(load(sys.argv[1]))
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{'INVALID' if errors else 'VALID'} — {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
