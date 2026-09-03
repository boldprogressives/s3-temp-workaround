# S3 temporary workaround for ActionKit emails and survey pages

Date: 2026-09-03. Status: approved by Keith in chat, implementation in progress.

## Problem

Every object in the `s3.boldprogressives.org` bucket returns HTTP 403 `AllAccessDisabled`.
AWS will not restore access before 2026-09-04. ActionKit mailings and survey pages load
their logo, social icons, buttons, CSS, and JS from that bucket, so they render broken.

## Goal

Within hours, have a mass-mailing wrapper, an auto-email wrapper, and a survey page
templateset in ActionKit that render correctly without S3, applied only to the mailings
and pages Keith names. Fully reversible tomorrow.

## Design

### Hosting

- Public GitHub repo `boldprogressives/s3-temp-workaround`.
- Files are stored at the same path they had inside the bucket, e.g. `images/logo5.gif`.
- Served through jsDelivr: `https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/<path>`.
- Files that S3 served pre-gzipped (`*.css.gzip`, `*.js.gzip`) are stored decompressed
  without the `.gzip` suffix, and the ActionKit copies reference the new name.
- GitHub Pages is optionally enabled as a second host.
- The repo stays up after S3 returns, because sent emails keep pointing at it.

### URL rewrite rule

Any of these prefixes:

    https://s3.us-east-1.amazonaws.com/s3.boldprogressives.org/
    https://s3.amazonaws.com/s3.boldprogressives.org/
    http://s3.amazonaws.com/s3.boldprogressives.org/
    //s3.amazonaws.com/s3.boldprogressives.org/

becomes `https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/`,
and `.gzip` is dropped from the filename.

### Asset recovery

`scripts/fetch_assets.py` reads `manifest.json`, fetches original bytes from the Wayback
Machine (`web.archive.org/web/<ts>id_/<url>`) for each path, gunzips where needed, and
writes `recovery_report.json` listing what was found and what is still missing.
Fallbacks for missing files, in order: Chrome cache on Keith's machine, Google's image
proxy for a recent PCCC send in Keith's Gmail, files supplied by Keith.

### ActionKit copies

`scripts/ak_clone.py` clones email wrappers 2 and 67 and templateset 101 into copies whose
names start with `TEMP S3 workaround -`, applying the rewrite rule. Originals are never
edited. Templates that reference `.gzip` files are rewritten to the decompressed name.

### Assignment and revert

`scripts/ak_assign.py --mailing <id>` sets a mailing's wrapper to the temp copy.
`scripts/ak_assign.py --page <short name>` sets a page's templateset to the temp copy.
`--revert` restores the original. `ak_ids.json` records every id the scripts create and
every assignment made, so revert is mechanical.

### New body images

`scripts/add_asset.py <file>` copies a file into `images/`, commits, pushes, purges the
jsDelivr cache for that path, and prints the URL to paste into the email body.

### Verification

- Load one converted survey page in the browser and confirm no 403 responses.
- Stage a test mailing on the temp wrapper and send it to Keith.

## Out of scope

- Partner logos in the page wrapper. They render only on partner-specific pages.
- Editing the originals or changing the site default templateset.
