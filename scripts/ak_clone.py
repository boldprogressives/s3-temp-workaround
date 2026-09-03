"""Clone ActionKit email wrappers 2 and 67 and templateset 101 with S3 URLs rewritten.

Usage:  python scripts/ak_clone.py [--wrappers] [--templateset] [--dry-run]

Creates copies named "TEMP S3 workaround - <original name>". Never edits originals.
Records the new ids in ak_ids.json. Safe to re-run: existing copies are reused.
"""
import sys

from _ak import get, post, patch, rewrite, load_ids, save_ids, id_from_uri

PREFIX = "TEMP S3 workaround - "
WRAPPER_IDS = [2, 67]
TEMPLATESET_ID = 101
WRAPPER_TEXT_FIELDS = ["template", "text_template", "amp_template",
                       "unsubscribe_html", "unsubscribe_text", "unsubscribe_amp_html"]


def clone_wrapper(src_id, ids, dry):
    key = str(src_id)
    if key in ids["wrappers"]:
        print(f"wrapper {src_id}: copy already exists as {ids['wrappers'][key]}")
        return
    src = get(f"/emailwrapper/{src_id}/")
    payload = {"name": PREFIX + src["name"], "lang": src.get("lang"), "hidden": False}
    changed = 0
    for f in WRAPPER_TEXT_FIELDS:
        v = src.get(f)
        nv = rewrite(v)
        if nv != v:
            changed += 1
        payload[f] = nv
    print(f"wrapper {src_id} '{src['name']}': {changed} fields rewritten")
    if dry:
        return
    loc = post("/emailwrapper/", payload)
    new_id = id_from_uri(loc)
    ids["wrappers"][key] = new_id
    save_ids(ids)
    print(f"  -> created wrapper {new_id}")


def clone_templateset(ids, dry):
    if ids.get("templateset"):
        print(f"templateset: copy already exists as {ids['templateset']}")
        return
    src = get(f"/templateset/{TEMPLATESET_ID}/")
    tmpls = [get(u.replace("/rest/v1", "")) for u in src["templates"]]
    changed = [t["filename"] for t in tmpls if rewrite(t["code"]) != t["code"]]
    print(f"templateset {TEMPLATESET_ID} '{src['name']}': {len(tmpls)} templates, "
          f"{len(changed)} need rewriting: {', '.join(changed)}")
    if dry:
        return
    loc = post("/templateset/", {
        "name": PREFIX + src["name"],
        "description": "Temporary copy with S3 assets served from GitHub/jsDelivr. Created 2026-09-03.",
        "lang": src.get("lang"), "editable": True, "hidden": False, "is_default": False,
    })
    new_id = id_from_uri(loc)
    print(f"  -> created templateset {new_id}")
    # A new templateset is born with its own default templates. Overwrite each by filename.
    new = get(f"/templateset/{new_id}/")
    existing = {}
    for u in new["templates"]:
        t = get(u.replace("/rest/v1", ""))
        existing[t["filename"]] = t["resource_uri"]
    for t in tmpls:
        code = rewrite(t["code"])
        if t["filename"] in existing:
            patch(existing[t["filename"]].replace("/rest/v1", ""), {"code": code})
        else:
            post("/template/", {"filename": t["filename"], "code": code,
                                "templateset": f"/rest/v1/templateset/{new_id}/"})
    ids["templateset"] = new_id
    save_ids(ids)
    print(f"  -> {len(tmpls)} templates written into templateset {new_id}")


def main(argv):
    dry = "--dry-run" in argv
    do_w = "--wrappers" in argv or not any(a in argv for a in ("--wrappers", "--templateset"))
    do_t = "--templateset" in argv or not any(a in argv for a in ("--wrappers", "--templateset"))
    ids = load_ids()
    if do_w:
        for w in WRAPPER_IDS:
            clone_wrapper(w, ids, dry)
    if do_t:
        clone_templateset(ids, dry)


if __name__ == "__main__":
    main(sys.argv[1:])
