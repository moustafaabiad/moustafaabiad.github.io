# Invitation site

Static invitation page (English / Arabic) with a personal link per guest and an RSVP that posts to a Google Form.

- `index.html` — the built page (do not edit by hand)
- `assets/` — artwork
- `src/page.html` — the page source; `src/data/guests.json` — the guest list copy; `src/config.json` — form id and site URL
- `src/sync_guests.py <csv-or-table.txt>` — rebuild the guest list from the "Invitation - guest list (live)" sheet (Guests tab)
- `python3 src/build.py` — rebuild `index.html`
