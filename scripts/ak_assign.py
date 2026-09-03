"""Point mailings and pages at the temp copies, or revert them.

Usage:
  python scripts/ak_assign.py --mailing 12345 [--mailing 12346 ...]
  python scripts/ak_assign.py --page short-name [--page other-name ...]
  python scripts/ak_assign.py --revert            # undo every assignment recorded
  python scripts/ak_assign.py --list-pages [N]    # newest N live survey pages, to help choose

Every change is recorded in ak_ids.json so --revert is mechanical.
"""
import sys

from _ak import get, patch, load_ids, save_ids, id_from_uri


def assign_mailing(mid, ids):
    m = get(f"/mailer/{mid}/")
    old = m.get("emailwrapper")
    old_id = id_from_uri(old)
    new_id = ids["wrappers"].get(str(old_id)) or ids["wrappers"].get("2")
    if not new_id:
        raise SystemExit("run ak_clone.py first")
    patch(f"/mailer/{mid}/", {"emailwrapper": f"/rest/v1/emailwrapper/{new_id}/"})
    ids["assignments"].append({"type": "mailing", "id": mid, "old": old, "new": new_id})
    save_ids(ids)
    print(f"mailing {mid}: wrapper {old_id} -> {new_id}")


def assign_page(name, ids):
    res = get("/page/", name=name)
    if not res["objects"]:
        raise SystemExit(f"no page named {name}")
    p = res["objects"][0]
    old = p.get("template_set") or p.get("templateset")
    new_id = ids.get("templateset")
    if not new_id:
        raise SystemExit("run ak_clone.py --templateset first")
    uri = p["resource_uri"].replace("/rest/v1", "")
    patch(uri, {"template_set": f"/rest/v1/templateset/{new_id}/"})
    ids["assignments"].append({"type": "page", "id": p["id"], "name": name, "old": old, "new": new_id})
    save_ids(ids)
    print(f"page {name} (id {p['id']}): templateset {id_from_uri(old)} -> {new_id}")


def revert(ids):
    remaining = []
    for a in ids["assignments"]:
        try:
            if a["type"] == "mailing":
                patch(f"/mailer/{a['id']}/", {"emailwrapper": a["old"]})
            else:
                patch(f"/page/{a['id']}/", {"template_set": a["old"]})
            print(f"reverted {a['type']} {a['id']} -> {a['old']}")
        except Exception as e:  # keep going, keep the record
            print(f"FAILED to revert {a['type']} {a['id']}: {e}")
            remaining.append(a)
    ids["assignments"] = remaining
    save_ids(ids)


def list_pages(n):
    res = get("/surveypage/", _limit=n, order_by="-created_at", status="active")
    for p in res["objects"]:
        print(f"{p['id']:>7}  {p['name']:<45} ts={id_from_uri(p.get('template_set'))}  {p['created_at'][:10]}")


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
