# PCCC S3 temporary workaround

Temporary public mirror of assets normally served from the `s3.boldprogressives.org`
S3 bucket, created 2026-09-03 while that bucket returns `AllAccessDisabled`.

ActionKit email wrappers and page templates reference these files. **Do not delete this
repo after S3 is restored.** Emails already sent point here permanently.

## URL mapping

Any of these S3 prefixes:

```
https://s3.us-east-1.amazonaws.com/s3.boldprogressives.org/
https://s3.amazonaws.com/s3.boldprogressives.org/
//s3.amazonaws.com/s3.boldprogressives.org/
```

becomes:

```
https://cdn.jsdelivr.net/gh/boldprogressives/s3-temp-workaround@main/
```

Files that S3 served as `*.css.gzip` or `*.js.gzip` are stored here decompressed,
without the `.gzip` suffix.

## Contents

- `images/`, `wp-content/`, `partnerlogos/`, `favicon.ico`: mirrored assets at their
  original bucket paths.
- `manifest.json`: the list of paths referenced by ActionKit wrappers 2 and 67 and
  templateset 101.
- `recovery_report.json`: where each file came from and which are still missing.
- `scripts/`: recovery, ActionKit cloning, assignment, and revert tooling. See
  `docs/superpowers/specs/` for the design.

## Adding a new image for an email body

```
python scripts/add_asset.py path/to/image.png
```

Commits, pushes, purges the jsDelivr cache, and prints the URL to use in the email.
