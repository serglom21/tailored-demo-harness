"""Shared helpers for tailored-demo scripts (stdlib + PyYAML only)."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml")


def load_spec(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_dotenv(path=".env"):
    """Minimal .env loader; does not override existing env vars."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def span_index(spec):
    """name -> span dict (attributes merged across journeys)."""
    idx = {}
    for j in spec.get("journeys") or []:
        for s in j.get("spans") or []:
            cur = idx.setdefault(s["name"], {**s, "journey": j["id"], "attributes": []})
            keys = {a["key"] for a in cur["attributes"]}
            cur["attributes"] += [a for a in s.get("attributes") or [] if a["key"] not in keys]
    return idx


def span_query(span):
    """Search query that isolates one spec span. Override per span with `match`."""
    if span.get("match"):
        return span["match"]
    return f'span.op:{span["op"]} span.description:"{span["name"]}"'


def attr_has_query(attr):
    key = attr["key"]
    if attr.get("type") == "number":
        return f"has:tags[{key},number]"
    return f"has:{key}"


def attr_field(key, attr_type):
    return f"tags[{key},number]" if attr_type == "number" else key


class Sentry:
    def __init__(self, org, token, base_url="https://sentry.io"):
        self.org, self.token = org, token
        self.base = base_url.rstrip("/")
        self._project_ids = {}

    def _req(self, method, path, params=None, body=None):
        url = f"{self.base}/api/0{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")[:300]
            raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from None

    def project_id(self, slug):
        if slug not in self._project_ids:
            self._project_ids[slug] = self._req("GET", f"/projects/{self.org}/{slug}/")["id"]
        return self._project_ids[slug]

    def count(self, dataset, query, project_slugs, environment, period="24h"):
        params = {
            "dataset": dataset,
            "field": ["count()"],
            "query": query,
            "statsPeriod": period,
            "project": [self.project_id(p) for p in project_slugs],
        }
        if environment:
            params["environment"] = environment
        res = self._req("GET", f"/organizations/{self.org}/events/", params)
        rows = (res or {}).get("data") or []
        return int(rows[0].get("count()", 0)) if rows else 0

    def create_dashboard(self, payload):
        return self._req("POST", f"/organizations/{self.org}/dashboards/", body=payload)
