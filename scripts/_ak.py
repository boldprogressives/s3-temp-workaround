"""Minimal ActionKit REST helper shared by the workaround scripts.

Credentials: ACTIONKIT_USERNAME / ACTIONKIT_PASSWORD from the environment,
C:/dev/PCCC_Email_Drafting/.env, or ~/.claude/.env (first hit wins).
"""
import json
import os
import re

import requests

BASE = "https://act.boldprogressives.org/rest/v1"
CDN = "https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/"
S3_PREFIX = re.compile(
    r"(?:https?:)?//(?:s3\.us-east-1\.amazonaws\.com|s3\.amazonaws\.com)/s3\.boldprogressives\.org/"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDS_PATH = os.path.join(ROOT, "ak_ids.json")


def _env():
    found = {}
    for p in [os.path.join("C:/dev/PCCC_Email_Drafting", ".env"),
              os.path.expanduser("~/.claude/.env")]:
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*)", line)
                    if m and m.group(1) not in found:
                        found[m.group(1)] = m.group(2).strip().strip("'\"")
        except OSError:
            pass
    for k in ("ACTIONKIT_USERNAME", "ACTIONKIT_PASSWORD"):
        if os.environ.get(k):
            found[k] = os.environ[k]
    return found


_E = _env()
AUTH = (_E.get("ACTIONKIT_USERNAME"), _E.get("ACTIONKIT_PASSWORD"))
HDR = {"Accept": "application/json", "Content-Type": "application/json"}


def get(path, **params):
    r = requests.get(BASE + path, auth=AUTH, headers=HDR, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def post(path, payload):
    r = requests.post(BASE + path, auth=AUTH, headers=HDR, data=json.dumps(payload), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:500]}")
    loc = r.headers.get("Location", "")
    return loc


def patch(path, payload):
    r = requests.patch(BASE + path, auth=AUTH, headers=HDR, data=json.dumps(payload), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"PATCH {path} -> {r.status_code}: {r.text[:500]}")
    return r


def rewrite(text):
    """Apply the S3 -> jsDelivr rewrite rule, dropping .gzip suffixes."""
    if not text:
        return text
    out = S3_PREFIX.sub(CDN, text)
    out = re.sub(r"(cdn\.jsdelivr\.net/gh/boldprogressives/s3-temp-workaround@main/[^\s\"'()<>]+?)\.gzip",
                 r"\1", out)
    return out


def load_ids():
    try:
        with open(IDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {"wrappers": {}, "templateset": None, "assignments": []}


def save_ids(d):
    with open(IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def id_from_uri(uri):
    m = re.search(r"/(\d+)/?$", uri or "")
    return int(m.group(1)) if m else None
