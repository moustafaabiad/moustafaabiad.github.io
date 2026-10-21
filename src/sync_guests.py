"""Rebuild data/guests.json from the live Google Sheet "Invitation - guest list (live)".
Usage: save the sheet's table (the markdown table returned by the Drive reader, or a CSV export) to a file, then
       python3 sync_guests.py <file>      (CSV when the file ends with .csv, otherwise markdown table)
Columns: id | Guest | First name (EN) | First name (AR) | Gender | Plus one | Plus-one first name (EN) |
         Plus-one first name (AR) | Plus-one full name | Group | Link      (one invitation = the guest + optional +1)
"""
import csv, json, re, sys

src = sys.argv[1]
rows = []
if src.endswith(".csv"):
    with open(src, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.reader(fh)]
else:
    for line in open(src, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= set(":- "):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
# header row = the one that starts with "id"
hi = next(i for i, r in enumerate(rows) if r and r[0].lower() == "id")
hdr = [h.strip().lower() for h in rows[hi]]
col = {h: i for i, h in enumerate(hdr)}
def get(r, name):
    i = col.get(name.lower()); return r[i].strip() if i is not None and i < len(r) else ""
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
guests, seen = [], {}
for r in rows[hi + 1:]:
    name = get(r, "guest")
    if not name:
        continue
    gid = get(r, "id"); gid = slug(name) if (not gid or gid.startswith("=")) else gid
    if gid in seen:                      # duplicate names get -2, -3 …
        seen[gid] += 1; gid = f"{gid}-{seen[gid]}"
    else:
        seen[gid] = 1
    plus = get(r, "plus one").lower() in ("yes", "y", "true", "1")
    people = [{"first": get(r, "first name (en)") or name.split(" ")[0], "firstAr": get(r, "first name (ar)"), "gender": (get(r, "gender") or "M").upper()[:1]}]
    pf, pfa, pfull = get(r, "plus-one first name (en)"), get(r, "plus-one first name (ar)"), get(r, "plus-one full name")
    open_seats = 0
    invite = name
    if plus:
        if pf or pfa:
            people.append({"first": pf or pfa, "firstAr": pfa, "gender": ""})
            sur = name.split(" ", 1)[1] if " " in name else ""
            psur = pfull.split(" ", 1)[1] if " " in pfull else ""
            invite = f"{people[0]['first']} & {pf} {sur}".strip() if (sur and psur == sur) else f"{name} & {pfull or pf}"
        else:
            open_seats = 1
    guests.append({"id": gid, "invite": invite, "group": get(r, "group"), "people": people, "open": open_seats})
json.dump(guests, open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "data", "guests.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("invitations:", len(guests), "| seats:", sum(len(g["people"]) + g["open"] for g in guests), "| with +1:", sum(1 for g in guests if len(g["people"]) + g["open"] > 1))
