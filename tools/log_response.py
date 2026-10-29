"""Log an employer's reply in applications.md and refresh the "so far" line.

Usage: python tools/log_response.py COMPANY "RESPONSE TEXT" ["OUTCOME TEXT"]
  COMPANY  part of the company name, any case (e.g. "telstra")
  RESPONSE appended to the Response cell, prefixed with today's date
  OUTCOME  replaces the Outcome cell if given (e.g. "Rejected", "Interview booked", "Offer")

Read the email, then run this (or ask Claude: /log-reply). The summary line is recomputed from the table.
"""
import os, re, sys, datetime, io

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "applications.md")
# Columns: Submitted | Company | Role | Where applied | Contact | Response | Outcome | Files
RESPONSE, OUTCOME = 5, 6

def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    company, response = argv[1], argv[2]
    outcome = argv[3] if len(argv) > 3 else None
    today = datetime.date.today().isoformat()
    lines = io.open(PATH, encoding="utf-8").read().split("\n")
    hit = None
    for i, line in enumerate(lines):
        if not line.startswith("| 20"): continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8: continue
        if company.lower() in cells[1].lower() or company.lower() in cells[2].lower():
            if hit is not None:
                sys.exit(f"'{company}' matches more than one row; be more specific")
            hit = i
    if hit is None:
        sys.exit(f"no row matches '{company}'")
    cells = [c.strip() for c in lines[hit].strip().strip("|").split("|")]
    cells[RESPONSE] = (cells[RESPONSE] + "; " if cells[RESPONSE] else "") + f"{today} {response}"
    if outcome:
        cells[OUTCOME] = outcome
    lines[hit] = "| " + " | ".join(cells) + " |"
    print("updated:", cells[1], "|", cells[RESPONSE], "|", cells[OUTCOME])

    # funnel line
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines if l.startswith("| 20")]
    n = len(rows)
    rej = [r[1] for r in rows if r[OUTCOME].lower().startswith("reject")]
    interviews = [r[1] for r in rows if re.match(r"(?i)(?:interview|phone screen|screen booked|call booked|offer)", r[OUTCOME])]
    other = [r[1] for r in rows if r[RESPONSE] and r[1] not in rej and r[1] not in interviews]
    first = min(r[0][:10] for r in rows)
    days = (datetime.date.today() - datetime.date.fromisoformat(first)).days or 1
    rate = n / (days / 7)
    funnel = (f"So far, {today}: {n} submitted, {len(rej)} rejections ({', '.join(rej) or 'none'}), "
              f"{len(interviews)} interviews{(' (' + ', '.join(interviews) + ')') if interviews else ''}, "
              f"{len(other)} other responses{(' (' + ', '.join(other) + ')') if other else ''}. "
              f"{rate:.1f} applications a week over {days} days.")
    for i, l in enumerate(lines):
        if l.startswith("So far,"):
            lines[i] = funnel; break
    io.open(PATH, "w", encoding="utf-8").write("\n".join(lines))
    print(funnel)

if __name__ == "__main__":
    main(sys.argv)
