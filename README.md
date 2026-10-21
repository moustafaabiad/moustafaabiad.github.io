# Invitation site

Static invitation page (English / Arabic) with a personal link per guest and an RSVP that posts to a Google Form.

- `index.html` — the built page (do not edit by hand)
- `assets/` — artwork
- `src/page.html` — the page source; `src/data/guests.json` — the guest list copy embedded in the page;
  `src/config.json` — form id and site URL
- `src/sync_guests.py [<export>]` — rebuild `src/data/guests.json` from the "Invitation - guest list (live)" sheet
  (Guests tab). Accepts the sheet's "Web page" (zip) or CSV export, a saved Drive export, or a markdown table.
  Prints what changed; refuses to shrink the list by more than 30 % unless `--force` is given.
- `python3 src/build.py` — rebuild `index.html`
- `bash publish.sh [<export>]` — sync + build + commit + push in one step (does nothing when the list is unchanged)

## Guest list updates

The guest list is maintained in the Google Sheet. The site carries a copy of it, refreshed by a daily task
(every morning, Paris time) that exports the sheet, runs `publish.sh` and pushes only when something changed.
Each guest's link is `https://moustafaabiad.github.io/?g=<id>`; the `id` column of the sheet is the stable key,
so renaming a guest keeps their link as long as the id stays the same.
