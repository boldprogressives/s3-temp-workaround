"""Clone ActionKit email wrappers 2 and 67 and templateset 101 with S3 URLs rewritten.

Usage:  python scripts/ak_clone.py [--wrappers] [--templateset] [--dry-run]

Creates copies named "TEMP S3 workaround - <original name>". Never edits originals.
Records the new ids in ak_ids.json. Safe to re-run: existing copies are reused.
"""
import re
import sys

from _ak import get, post, put, rewrite, load_ids, save_ids, id_from_uri

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
    # 'lang' is deliberately omitted: POSTing it returns a bare 401 for this API
    # user, and a new wrapper defaults to the same language as the originals.
    payload = {"name": PREFIX + src["name"], "hidden": False}
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


# ActionKit rejects writes to any filename that does not match this, even for
# legacy templates that already exist under such a name in the source set.
VALID_FILENAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*\.(html|css|js)$")


def _templates_of(ts_id):
    """One bulk call instead of one GET per template."""
    return get("/template/", templateset=ts_id, _limit=500)["objects"]


def clone_templateset(ids, dry):
    src = get(f"/templateset/{TEMPLATESET_ID}/")
    tmpls = _templates_of(TEMPLATESET_ID)
    changed = [t["filename"] for t in tmpls if rewrite(t["code"]) != t["code"]]
    print(f"templateset {TEMPLATESET_ID} '{src['name']}': {len(tmpls)} templates, "
          f"{len(changed)} need rewriting: {', '.join(changed)}")
    if dry:
        return

    new_id = ids.get("templateset")
    if new_id:
        print(f"templateset: reusing existing copy {new_id}, syncing templates")
    else:
        loc = post("/templateset/", {
            "name": PREFIX + src["name"],
            "description": "Temporary copy with S3 assets served from GitHub/jsDelivr. Created 2026-09-03.",
            "editable": True, "hidden": False, "is_default": False,
        })
        new_id = id_from_uri(loc)
        # Record the id BEFORE the long write loop, so a mid-run failure cannot
        # orphan the templateset and make a re-run create a duplicate.
        ids["templateset"] = new_id
        save_ids(ids)
        print(f"  -> created templateset {new_id}")

    # A new templateset is born with its own default templates. Overwrite by filename.
    existing = {t["filename"]: t for t in _templates_of(new_id)}
    ts_uri = f"/rest/v1/templateset/{new_id}/"
    wrote = skipped = already = 0
    unwritable = []
    for t in tmpls:
        fn, code = t["filename"], rewrite(t["code"])
        cur = existing.get(fn)
        if cur and cur["code"] == code:
            already += 1
            continue
        if not VALID_FILENAME.match(fn):
            # ActionKit's own validator refuses these; nothing the API can do.
            unwritable.append(fn)
            skipped += 1
            continue
        body = {"filename": fn, "code": code, "templateset": ts_uri}
        if cur:
            # complete representation, so PUT cannot null out a field
            put(cur["resource_uri"].replace("/rest/v1", ""), body)
        else:
            post("/template/", body)
        wrote += 1
        if wrote % 20 == 0:
            print(f"     ... {wrote} written")
    print(f"  -> templateset {new_id}: {wrote} written, {already} already correct, "
          f"{skipped} skipped")
    if unwritable:
        print(f"  !! filenames ActionKit refuses to write (left as-is): {', '.join(unwritable)}")


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
