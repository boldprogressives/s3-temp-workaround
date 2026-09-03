# Handoff: PCCC S3 outage workaround (2026-09-03)

Written for whoever picks this up next (Codex, Claude, or a human). Read this, then
`docs/superpowers/specs/2026-09-03-s3-temp-workaround-design.md` for the design rationale.

## Situation

The S3 bucket `s3.boldprogressives.org` returns HTTP 403 `AllAccessDisabled` on every
object. AWS will not restore it before 2026-09-04. ActionKit mass mailings, auto-emails,
and survey pages load logo, icons, buttons, CSS and JS from that bucket.

Keith approved this approach: a public GitHub mirror served by jsDelivr, plus temporary
copies of the ActionKit wrapper/templateset with URLs rewritten. Originals are never
edited. Everything is reversible. The repo must stay up permanently afterwards because
emails sent today point at it.

## State as of this handoff

### Done

- Repo `boldprogressives/s3-temp-workaround` (public) created and pushed. Local clone is
  this directory, `C:\dev\PCCC_S3_Temp_Workaround`, branch `main`.
- CDN base URL, verified serving correct content types:
  `https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/<bucket path>`
- GitHub Pages enabled as a fallback host: `https://boldprogressives.github.io/s3-temp-workaround/<bucket path>`
- 25 of 28 required assets recovered from the Wayback Machine (`recovery_report.json`).
  Gzipped CSS/JS were decompressed and stored without the `.gzip` suffix.
  `wp-content/themes/premise/ak/jquery.embedly.min.js` is an empty stub (never archived;
  only affects auto-embedded video on pages).
- ActionKit copies created via REST and recorded in `ak_ids.json`:
  - email wrapper **114** = copy of wrapper 2 "2013 Mailing Template (standard)"
  - email wrapper **115** = copy of wrapper 67 "2016 Auto-Email Template"
  - templateset **157** = copy of templateset 101 "[LIVE] 2016 Default With Sharing"
  All named `TEMP S3 workaround - <original name>`.
- Memory note saved for Claude Code at
  `~/.claude/projects/C--dev-PCCC-S3-Temp-Workaround/memory/`.

### Verified (2026-09-03, after cloning)

- Wrappers 114/115 and all 88 templates in set 157: zero `amazonaws.com` references,
  72 distinct jsDelivr URLs, none ending in `.gzip`.
- Originals (wrapper 2, wrapper 67, templateset 101 and its 88 templates) byte-identical
  to a pre-write snapshot. Set 101 is still the site default.
- Known gaps in set 157 that do not matter for survey pages: the two `.txt` event
  tell-a-friend templates are empty because ActionKit's validator refuses `.txt`
  filenames over REST; `ngpvan_payments_confirm.html` kept stock content.
- Wrapper **113** is a probe created by mistake during diagnosis. It is hidden and renamed
  `ZZ IGNORE - probe created in error 2026-09-03 (unused)`. Ignore it.
- The 15 newest live survey pages all use templateset 101, so set 157 covers them.
- `scripts/ak_assign.py` was rewritten to write `templateset` on the page's surveyform
  and to fall back from PATCH to PUT. The read path (`--list-pages`) is tested. The write
  path has NOT been exercised yet; test on one page and check the printed before/after.

### Not done

1. **Three images never recovered** (not in Wayback, Chrome cache, Gmail, Drive, or disk).
   Keith decided on 2026-09-03, all applied:
   - Mamdani sticker: the block was already inside an HTML comment in wrapper 2, so it is
     hidden in wrapper 114 too. Nothing to do.
   - `images/Icon-X.png`: committed as a copy of the Twitter bird `Icon-TW.png`. Replace
     with the real X icon later if Keith supplies it (then purge the jsDelivr cache).
   - Bluesky: the `<td>` containing the `Icon-BSKY.png` link was removed from wrapper 114
     via PUT. Wrapper 2 still has it.
2. **No mailing or page has been assigned yet.** Keith will name mailing ids and survey
   page short names.
3. **Verification in the wild**: load one converted survey page and confirm zero 403s;
   stage a test mailing on wrapper 114 and send to Keith.
4. `ak_assign.py --page` may need the cms_form fix (see gotchas). Test on one page first.

## How to run things

All scripts are in `scripts/`, run from the repo root with plain `python`. They need
`requests`. ActionKit credentials load automatically from
`C:/dev/PCCC_Email_Drafting/.env` (`ACTIONKIT_USERNAME`, `ACTIONKIT_PASSWORD`).
API base: `https://act.boldprogressives.org/rest/v1`.

```
python scripts/fetch_assets.py                 # re-run recovery, skips files already present
python scripts/fetch_assets.py --only images/x.png --force
python scripts/ak_clone.py --dry-run           # shows what would be rewritten; safe
python scripts/ak_assign.py --list-pages 15    # newest live survey pages
python scripts/ak_assign.py --mailing 12345    # point a mailing at wrapper 114 (or 115 if it used 67)
python scripts/ak_assign.py --page short-name  # point a survey page at templateset 157
python scripts/ak_assign.py --revert           # undo every recorded assignment
python scripts/add_asset.py C:\path\hero.png   # add a body image, prints its CDN URL
```

Manual add of an image without the script:

```
copy the file into images\, then
git add images\NAME.png && git commit -m "Add NAME.png" && git push
```

New files are live on jsDelivr within about a minute. Replacing an existing filename
needs a purge: GET `https://purge.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/<path>`.

## Verification checklist

1. `GET /rest/v1/emailwrapper/114/` and `/115/`: the `template` field contains no
   `amazonaws.com` and no `.gzip`; every asset URL starts with the CDN base.
2. `GET /rest/v1/templateset/157/` then each template in `templates`: same check on
   `wrapper.html`, `thanks.html`, `test-wrapper.html`, `test-thanks.html`.
3. `GET /rest/v1/emailwrapper/2/`, `/67/`, `/templateset/101/`: still reference S3
   (that is, untouched).
4. For each CDN URL referenced by the copies, an HTTP GET returns 200 with a sensible
   content type. Python: `requests.get(url).status_code`.
5. Browser: open a survey page that uses templateset 157, check DevTools network tab
   for any 403 or 404.

## Gotchas discovered

- ActionKit REST: POSTing `lang` on `/emailwrapper/` returns a bare 401 for this API
  user. Omit it; new objects default to the same language.
- ActionKit REST: PATCH on `/emailwrapper/<id>/` also returns a bare 401. Use PUT with
  the full object minus `id`, `resource_uri`, `created_at`, `updated_at`, `lang`.
  Returns 204 on success.
- A new templateset created via POST is born with its own default templates. Overwrite
  them by filename with PUT (full representation), then POST any filenames that did not
  exist. `ak_clone.py` does this.
- The templateset is NOT a field on `/page/` or `/surveypage/`. It lives on the page's
  `cms_form` (`/rest/v1/surveyform/<id>/`, field `templateset`). `--list-pages` resolves
  it there. `--page` assignment must PATCH the surveyform's `templateset`, not the page.
- Wayback CDX API is slow and sometimes times out. `fetch_assets.py` retries; a full run
  takes 10 to 20 minutes. The `archive.org/wayback/available` endpoint is faster but
  gives only one snapshot.
- jsDelivr caches `@main` for up to 12 hours; purge after replacing a file.
- Raw `raw.githubusercontent.com` URLs will not work for CSS/JS (served as text/plain).
- Keith's house style: no em-dashes, no curly quotes in anything user-facing.

## Revert procedure (when S3 is back)

1. Confirm `https://s3.us-east-1.amazonaws.com/s3.boldprogressives.org/images/logo5.gif`
   returns 200.
2. `python scripts/ak_assign.py --revert`
3. Staging goes back to wrapper 2 (mass) / 67 (auto) and templateset 101.
4. Optionally set `hidden: true` on wrappers 114/115 and templateset 157 via PATCH.
   Do not delete them: any mailing sent with them keeps referencing them.
5. Leave the GitHub repo public and intact forever.

## People and places

- Keith Rouda, keithr@boldprogressives.org, GitHub `krouda-bp` (org admin of `boldprogressives`).
- Central skills repo with ActionKit staging conventions: `C:/dev/PCCC_Skills/skills/pccc-email-stage/`.
