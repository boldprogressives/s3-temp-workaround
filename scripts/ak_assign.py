"""Point mailings and pages at the temp copies, or revert them.

Usage:
  python scripts/ak_assign.py --mailing 12345 [--mailing 12346 ...]
  python scripts/ak_assign.py --page short-name [--page other-name ...]
  python scripts/ak_assign.py --revert            # undo every assignment recorded
  python scripts/ak_assign.py --list-pages [N]    # newest N live survey pages, to help choose

Every change is recorded in ak_ids.json so --revert is mechanical.
"""
import sys

from _ak import get, patch, put, load_ids, save_ids, id_from_uri

READ_ONLY = ("id", "resource_uri", "created_at", "updated_at", "lang")


def write_field(uri, obj, field, value):
    """Set one field on an existing object. PATCH first (works on /mailer/ per the
    staging skill); fall back to PUT with the full representation because PATCH
    returns a bare 401 on some resources for this API user."""
    path = uri.replace("/rest/v1", "")
    try:
        patch(path, {field: value})
        return "PATCH"
    except RuntimeError as e:
        if "401" not in str(e):
            raise
    body = {k: v for k, v in obj.items() if k not in READ_ONLY}
    body[field] = value
    put(path, body)
    return "PUT"


def assign_mailing(mid, ids):
    m = get(f"/mailer/{mid}/")
    old = m.get("emailwrapper")
    old_id = id_from_uri(old)
    new_id = ids["wrappers"].get(str(old_id)) or ids["wrappers"].get("2")
    if not new_id:
        raise SystemExit("run ak_clone.py first")
    new_uri = f"/rest/v1/emailwrapper/{new_id}/"
    verb = write_field(m["resource_uri"], m, "emailwrapper", new_uri)
    ids["assignments"].append({"type": "mailing", "id": mid, "uri": m["resource_uri"],
                               "field": "emailwrapper", "old": old, "new": new_uri})
    save_ids(ids)
    print(f"mailing {mid}: wrapper {old_id} -> {new_id} ({verb})")


def assign_page(name, ids):
    """The templateset is not on the page; it is on the page's cms_form (surveyform)."""
    res = get("/page/", name=name)
    if not res["objects"]:
        raise SystemExit(f"no page named {name}")
    p = res["objects"][0]
    form_uri = p.get("cms_form")
    if not form_uri:
        raise SystemExit(f"page {name} has no cms_form; assign its templateset in the admin UI")
    form = get(form_uri.replace("/rest/v1", ""))
    old = form.get("templateset")
    new_id = ids.get("templateset")
    if not new_id:
        raise SystemExit("run ak_clone.py --templateset first")
    new_uri = f"/rest/v1/templateset/{new_id}/"
    verb = write_field(form_uri, form, "templateset", new_uri)
    check = get(form_uri.replace("/rest/v1", "")).get("templateset")
    ids["assignments"].append({"type": "page", "id": p["id"], "name": name, "uri": form_uri,
                               "field": "templateset", "old": old, "new": new_uri})
    save_ids(ids)
    print(f"page {name} (id {p['id']}, form {id_from_uri(form_uri)}): templateset "
          f"{id_from_uri(old)} -> {id_from_uri(check)} ({verb})")


def revert(ids):
    remaining = []
    for a in ids["assignments"]:
        try:
            if not a.get("old"):
                raise RuntimeError("no recorded original; fix by hand")
            obj = get(a["uri"].replace("/rest/v1", ""))
            write_field(a["uri"], obj, a["field"], a["old"])
            print(f"reverted {a['type']} {a['id']} -> {a['old']}")
        except Exception as e:  # keep going, keep the record
            print(f"FAILED to revert {a['type']} {a['id']}: {e}")
            remaining.append(a)
    ids["assignments"] = remaining
    save_ids(ids)


def list_pages(n):
    # The templateset is NOT a field on page/surveypage. It lives on the page's
    # cms_form (/rest/v1/surveyform/<id>/, field "templateset"), so resolve it there.
    res = get("/surveypage/", _limit=n, order_by="-created_at", status="active")
    print(f"{'page id':>7}  {'name':<45} {'form':>7}  {'ts':>5}  created")
    for p in res["objects"]:
        ts, form_id = None, None
        form = p.get("cms_form")
        if form:
            form_id = id_from_uri(form)
            try:
                ts = id_from_uri(get(form.replace("/rest/v1", "")).get("templateset"))
            except Exception as e:
                ts = f"err:{type(e).__name__}"
        print(f"{p['id']:>7}  {p['name']:<45} {form_id or '-':>7}  {ts if ts is not None else '-':>5}"
              f"  {p['created_at'][:10]}")


def main(argv):
    ids = load_ids()
    if "--revert" in argv:
        return revert(ids)
    if "--list-pages" in argv:
        i = argv.index("--list-pages")
        n = int(argv[i + 1]) if i + 1 < len(argv) and argv[i + 1].isdigit() else 25
        return list_pages(n)
    i = 0
    while i < len(argv):
        if argv[i] == "--mailing":
            assign_mailing(int(argv[i + 1]), ids); i += 2
        elif argv[i] == "--page":
            assign_page(argv[i + 1], ids); i += 2
        else:
            i += 1


if __name__ == "__main__":
    main(sys.argv[1:])
