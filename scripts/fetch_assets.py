"""Recover bucket assets from the Wayback Machine into this repo.

Usage:  python scripts/fetch_assets.py [--optional] [--only path ...]

Reads manifest.json, and for each bucket-relative path asks the Wayback CDX API
for the newest HTTP 200 capture under either S3 hostname, then downloads the
original bytes (the ``id_`` flag) and writes them to the same path in the repo.
Files that end in ``.gzip`` are gunzipped and saved without the suffix.
Writes recovery_report.json with found / missing lists.
"""
import gzip
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSTS = ["s3.amazonaws.com", "s3.us-east-1.amazonaws.com"]
BUCKET = "s3.boldprogressives.org"
UA = {"User-Agent": "pccc-s3-workaround/1.0 (+keithr@boldprogressives.org)"}


def cdx_latest(path):
    """Return (original_url, timestamp) of the newest 200 capture, or None."""
    for host in HOSTS:
        for scheme in ("https", "http"):
            url = f"{scheme}://{host}/{BUCKET}/{path}"
            params = {
                "url": url, "output": "json", "fl": "original,timestamp,statuscode",
                "filter": "statuscode:200", "limit": "-5",
            }
            for attempt in range(3):
                try:
                    r = requests.get("https://web.archive.org/cdx/search/cdx",
                                     params=params, headers=UA, timeout=40)
                    if r.status_code != 200 or not r.text.strip():
                        break
                    rows = r.json()
                    if len(rows) > 1:
                        best = rows[-1]
                        return best[0], best[1]
                    break
                except Exception:
                    time.sleep(2 * (attempt + 1))
    return None


def download(original, ts):
    url = f"https://web.archive.org/web/{ts}id_/{original}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def save(path, data):
    dest = path
    if dest.endswith(".gzip"):
        dest = dest[:-5]
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
    full = os.path.join(ROOT, dest)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    return dest, len(data)


def main(argv):
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    paths = list(man["required"])
    if "--optional" in argv:
        paths += man["optional"]
    if "--only" in argv:
        paths = argv[argv.index("--only") + 1:]

    report = {"found": {}, "missing": []}
    for p in paths:
        dest_guess = p[:-5] if p.endswith(".gzip") else p
        if os.path.exists(os.path.join(ROOT, dest_guess)) and "--force" not in argv:
            report["found"][p] = {"dest": dest_guess, "source": "already present"}
            print(f"skip    {p}")
            continue
        hit = cdx_latest(p)
        if not hit:
            report["missing"].append(p)
            print(f"MISSING {p}")
            continue
        data = download(*hit)
        if not data:
            report["missing"].append(p)
            print(f"MISSING {p} (download failed from {hit[1]})")
            continue
        dest, n = save(p, data)
        report["found"][p] = {"dest": dest, "bytes": n, "wayback_ts": hit[1], "original": hit[0]}
        print(f"ok      {p} -> {dest} ({n} bytes, capture {hit[1]})")

    with open(os.path.join(ROOT, "recovery_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nfound={len(report['found'])} missing={len(report['missing'])}")
    for m in report["missing"]:
        print("  still missing:", m)


if __name__ == "__main__":
    main(sys.argv[1:])
