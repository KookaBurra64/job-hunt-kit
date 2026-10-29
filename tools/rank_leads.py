#!/usr/bin/env python
"""Ranks the ads the scanners found, zero LLM tokens.

Reads sourcing/agg-<date>.json (and ats-<date>.json if present) plus the
descriptions in sourcing/agg-<date>-details/, scores each ad with the words,
dealbreakers, salary floor and experience limit in my-profile.toml, and writes
sourcing/rank-<date>.md. Claude reads the top of that file, not 200 ads.

Usage:
    python tools/rank_leads.py                 # today
    python tools/rank_leads.py --date 2026-09-08 --top 40
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import myprofile  # noqa: E402

ROOT = myprofile.ROOT
OUTDIR = os.path.join(ROOT, "sourcing")

R = myprofile.load().get("ranking", {})
# (label, regex, points). Scored once per ad however often the word appears.
SIGNALS = [(w, myprofile.words_re([w]), int(p)) for w, p in R.get("good_words", {}).items()]
SIGNALS += [(w, myprofile.words_re([w]), int(p)) for w, p in R.get("bad_words", {}).items()]
DEALBREAKERS = [(w, myprofile.words_re([w])) for w in R.get("dealbreakers", [])]
FLOOR = int(R.get("salary_floor", 0))
MAX_YEARS = int(R.get("max_years_experience", 0))
_S = myprofile.search()
# Your own area, not all of Australia: a Perth job is outside a Melbourne search.
LOCAL = myprofile.words_re([_S["city"], _S["state"], _S["state_name"]])
REMOTE_AU = re.compile(r"(?i)^[\s,;()-]*remote[\s,;()-]*$|remote.*australia|australia.*remote")

def norm(s):
    """Lower case, punctuation and extra spaces gone: 'Customer Service Officer - NAB' style matching."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


def cell(x):
    """Table-safe text: a | in a job title would split the markdown table."""
    return str(x if x is not None else "").replace("|", "/").replace("\n", " ")


def agg_scan_safe_id(x):
    """Same rule as safe_id in agg_scan.py, so ranked ads find their saved text."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(x))[:80] or "unknown"


YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)", re.I)
MONEY = re.compile(r"\$?\s?(\d{2,3})(?:[,.](\d{3}))?\s*(k\b|,000|000)?", re.I)


def salary_max(s):
    """Largest annual figure in a salary string, or None. '$110k - $130k' -> 130000."""
    if not s:
        return None
    vals = []
    for m in MONEY.finditer(s):
        n = int(m.group(1))
        if m.group(2):
            n = n * 1000 + int(m.group(2))
        elif m.group(3):
            n *= 1000
        if 40_000 <= n <= 400_000:
            vals.append(n)
    return max(vals) if vals else None


def score(text):
    pts, tags = 0, []
    for label, rx, p in SIGNALS:
        if rx.search(text):
            pts += p
            tags.append(label)
    for label, rx in DEALBREAKERS:
        if rx.search(text):
            pts -= 50
            tags.append("DEALBREAKER:" + label)
    yrs = [int(m.group(1)) for m in YEARS.finditer(text) if 0 < int(m.group(1)) <= 15]
    if yrs and MAX_YEARS:
        mn = min(yrs)
        if mn > MAX_YEARS:
            pts -= 10; tags.append(f"asks {mn}+ yrs")
        elif mn == MAX_YEARS:
            pts -= 2; tags.append(f"asks {mn} yrs")
        else:
            pts += 1; tags.append(f"asks {mn} yrs")
    return pts, tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()

    rows = []
    for fn in (f"agg-{a.date}.json", f"ats-{a.date}.json"):
        p = os.path.join(OUTDIR, fn)
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        rows += d.get("candidates") or d.get("matches") or []
    if not rows:
        sys.exit(f"Nothing to rank for {a.date}. Run tools/agg_scan.py (and tools/ats_scan.py) first.")

    ddir = os.path.join(OUTDIR, f"agg-{a.date}-details")
    details = {}
    for fn in glob.glob(os.path.join(ddir, "*.txt")):
        details[os.path.basename(fn)[:-4]] = open(fn, encoding="utf-8").read()

    # Known: the ad's URL is already in ads/ or applications.md, or applications.md has a row
    # with the same company and job title. Whole values only, so "NAB" never matches "enabled".
    saved = [open(f, encoding="utf-8", errors="ignore").read()
             for f in glob.glob(os.path.join(ROOT, "ads", "*.md")) + glob.glob(os.path.join(ROOT, "applications.md"))]
    known_urls = {u.rstrip(").,") for t in saved for u in re.findall(r"https?://\S+", t)}
    applied = set()
    app = os.path.join(ROOT, "applications.md")
    if os.path.exists(app):
        for line in open(app, encoding="utf-8", errors="ignore"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("| 20") and len(cells) >= 3:
                applied.add((norm(cells[1]), norm(cells[2])))

    out = []
    for r in rows:
        key = f"{r.get('source', r.get('ats', ''))}-{agg_scan_safe_id(r.get('id', ''))}"
        body = details.get(key, "")
        text = " ".join([r.get("title", ""), r.get("teaser", ""), r.get("salary", ""), r.get("type", ""), body])
        pts, tags = score(text)
        if not body:
            tags.append("no-detail")
        smax = salary_max(r.get("salary", ""))
        if FLOOR and smax and smax < FLOOR:
            pts -= 5; tags.append("below-salary-floor")
        loc = r.get("location", "") or ""
        if not (LOCAL.search(loc) or REMOTE_AU.search(loc) or r.get("mode") == "Remote"):
            pts -= 2; tags.append("outside-area")
        known = r.get("url", "") in known_urls or (
            bool(norm(r.get("company"))) and (norm(r.get("company")), norm(r.get("title"))) in applied)
        out.append((pts, r, tags, known))

    # The same job is often on Seek, Jora and a careers page at once. Keep the best-scoring copy
    # (ties go to the one with ad text) and say where else it was seen.
    best = {}
    for x in out:
        k = (norm(x[1].get("company")), norm(x[1].get("title")))
        if not k[0]:
            k = (x[1].get("url", ""), "")
        if k not in best:
            best[k] = (x, [])
        else:
            cur, others = best[k]
            if (x[0], "no-detail" not in x[2]) > (cur[0], "no-detail" not in cur[2]):
                best[k] = (x, others + [cur[1].get("source", cur[1].get("ats", ""))])
            else:
                others.append(x[1].get("source", x[1].get("ats", "")))
    out = []
    for (pts, r, tags, known), others in best.values():
        if others:
            tags = tags + ["also on " + "/".join(sorted(set(others)))]
        out.append((pts, r, tags, known))
    # Highest score first; newest first among equal scores
    out.sort(key=lambda x: x[1].get("posted", "") or "", reverse=True)
    out.sort(key=lambda x: x[0], reverse=True)

    good = [x for x in out if x[0] > 0 and not any(t.startswith("DEALBREAKER") for t in x[2])]
    md = [f"# Ranked jobs {a.date}", "",
          f"{len(out)} ads scored by tools/rank_leads.py using my-profile.toml. Higher is better; the tags show "
          f"which of your words matched. 'seen before' means it is already in ads/ or applications.md. "
          f"'no-detail' means only the job title was scored (the site gave no ad text), so the score is low.", "",
          "| # | Score | Posted | Source | Company | Title | Location | Remote | Salary | Tags | URL |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, (pts, r, tags, known) in enumerate(out[:a.top], 1):
        md.append("| " + " | ".join(cell(v) for v in (
            i, pts, r.get('posted', '')[:10], r.get('source', r.get('ats', '')), r.get('company', ''),
            r.get('title', ''), r.get('location', ''), 'yes' if r.get('mode') == 'Remote' else '', r.get('salary', ''),
            ', '.join(tags) + (', seen before' if known else ''), r.get('url', ''))) + " |")
    md += ["", f"## Worth a look ({len(good)})", "",
           "Positive score and no dealbreakers. New ones first.", ""]
    for pts, r, tags, known in sorted(good, key=lambda x: x[3]):
        md.append(f"- {pts} | {r.get('company', '')} | {r.get('title', '')} | {r.get('location', '')}{' (remote)' if r.get('mode') == 'Remote' else ''} | "
                  f"{'seen before | ' if known else ''}{r.get('url', '')}")
    p = os.path.join(OUTDIR, f"rank-{a.date}.md")
    open(p, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"ranked {len(out)}, {len(good)} worth a look; wrote {p}")


if __name__ == "__main__":
    main()
