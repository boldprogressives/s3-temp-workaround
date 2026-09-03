"""Add an image (or any file) to the mirror and print its CDN URL.

Usage:  python scripts/add_asset.py <file> [--dest images/other_name.png]

Copies the file into images/ (or --dest), commits, pushes to main, purges the
jsDelivr cache for that path, and prints the URL to paste into an email body.
"""
import os
import shutil
import subprocess
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDN = "https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/"


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    src = argv[0]
    dest = argv[argv.index("--dest") + 1] if "--dest" in argv else "images/" + os.path.basename(src)
    dest = dest.replace("\\", "/")
    full = os.path.join(ROOT, dest)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    shutil.copyfile(src, full)
    subprocess.check_call(["git", "-C", ROOT, "add", dest])
    subprocess.check_call(["git", "-C", ROOT, "commit", "-q", "-m", f"Add {dest}"])
    subprocess.check_call(["git", "-C", ROOT, "push", "-q", "origin", "main"])
    try:
        requests.get("https://purge.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/" + dest, timeout=30)
    except Exception as e:
        print("cache purge failed (harmless for new files):", e)
    url = CDN + dest
    r = requests.head(url, timeout=30, allow_redirects=True)
    print(url)
    print("CDN status:", r.status_code, r.headers.get("content-type"))


if __name__ == "__main__":
    main(sys.argv[1:])
