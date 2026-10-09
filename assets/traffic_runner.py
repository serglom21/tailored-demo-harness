#!/usr/bin/env python3
"""Drive backend journeys from demo-spec.yaml with realistic values and injected failures.

Copy into the demo project as traffic/run.py.

Usage:
  python traffic/run.py --spec demo-spec.yaml --base-url http://localhost:8000 \
      [--minutes 30] [--rps 2] [--seed 42] [--dry-run]

Failure injection: sends `X-Demo-Fail: <failure_id>` per each failure's `rate`
(biased by its `when` clause). The app is responsible for raising the real error.
"""
import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_.]+)\}")


def sample_attr(a, rng):
    if a.get("values"):
        return rng.choice(a["values"])
    if a.get("type") == "number":
        lo, hi = a.get("range") or [0, (a.get("example") or 100) * 2]
        v = rng.uniform(lo, hi)
        return round(v, 2) if isinstance(a.get("example"), float) or isinstance(lo, float) else int(v)
    if a.get("type") == "boolean":
        return rng.random() < 0.5
    return a.get("example", f'{a["key"].split(".")[-1]}_{rng.randint(1, 999):03d}')


def fill(obj, values):
    if isinstance(obj, str):
        whole = PLACEHOLDER.fullmatch(obj)
        if whole:  # keep native type for "{attr}"
            return values.get(whole.group(1), obj)
        return PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), m.group(0))), obj)
    if isinstance(obj, dict):
        return {k: fill(v, values) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fill(v, values) for v in obj]
    return obj


def pick_failures(journey, values, rng):
    hit = []
    for fl in journey.get("failures") or []:
        when = fl.get("when") or {}
        if when and not all(values.get(k) == v for k, v in when.items()):
            continue
        if rng.random() < fl["rate"]:
            hit.append(fl["id"])
    return hit


def run_journey(base_url, journey, rng, dry_run, tags):
    attrs = {}
    for s in journey.get("spans") or []:
        for a in s.get("attributes") or []:
            if a["key"] not in attrs and not a.get("pii"):
                attrs[a["key"]] = sample_attr(a, rng)
    fails = pick_failures(journey, attrs, rng)
    headers = {"Content-Type": "application/json",
               "X-Demo-Tags": ",".join(f"{k}={v}" for k, v in tags.items())}
    if fails:
        headers["X-Demo-Fail"] = ",".join(fails)
    for step in (journey.get("traffic") or {}).get("steps") or []:
        path = fill(step["path"], attrs)
        body = fill(step.get("body"), attrs) if step.get("body") is not None else None
        url = base_url.rstrip("/") + path
        if dry_run:
            print(f'{journey["id"]:10} {step["method"]:6} {path:30} fail={fails or "-"} body={json.dumps(body)}')
            continue
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=step["method"], headers=headers)
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except urllib.error.HTTPError:
            break  # expected for injected failures; stop the journey like a real user
        except urllib.error.URLError as e:
            sys.exit(f"Cannot reach {url}: {e.reason}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="demo-spec.yaml")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--rps", type=float, default=2)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--iterations", type=int, default=None, help="stop after N journeys")
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = yaml.safe_load(f)
    rng = random.Random(args.seed)
    journeys = [j for j in spec["journeys"] if (j.get("traffic") or {}).get("steps")]
    if not journeys:
        sys.exit("No journeys with traffic.steps in spec")
    weights = [(j.get("traffic") or {}).get("weight", 1) for j in journeys]
    tags = spec["demo_env"].get("tags") or {}

    deadline = time.time() + args.minutes * 60
    n, failed = 0, 0
    while time.time() < deadline and (args.iterations is None or n < args.iterations):
        j = rng.choices(journeys, weights)[0]
        if run_journey(args.base_url, j, rng, args.dry_run, tags):
            failed += 1
        n += 1
        if not args.dry_run:
            time.sleep(rng.expovariate(args.rps))
            if n % 50 == 0:
                print(f"{n} journeys, {failed} with injected failures")
    print(f"Done: {n} journeys, {failed} with injected failures")


if __name__ == "__main__":
    main()
