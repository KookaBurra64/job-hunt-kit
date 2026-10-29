#!/usr/bin/env python3
"""Deterministic ATS board scan. No LLM tokens.

Fetches every board in tools/slugs.json ("live" only), normalises the postings,
filters on title and location, and writes a shortlist. An agent then reads the
shortlist and fetches ad text for the handful that matter, instead of doing 700
WebFetch calls to discover them.

    python tools/ats_scan.py                  # full scan, writes sourcing/
    python tools/ats_scan.py --probe canva    # test one slug across all 5 ATS
    python tools/ats_scan.py --all            # no title/seniority filter

Stdlib only. Python 3.11+ (my-profile.toml is read with tomllib).
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUGS = os.path.join(ROOT, "tools", "slugs.json")
OUTDIR = os.path.join(ROOT, "sourcing")
LEDGER = os.path.join(OUTDIR, "checked.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
TIMEOUT = 25

# Which titles and locations count as a match comes from my-profile.toml.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import myprofile  # noqa: E402
WANT, SKIP = myprofile.title_filters()
LOC_AU = myprofile.location_re()
# A role is kept only if the location names your area or Australia, or is bare "Remote"
# with no geography at all. "Remote, Canada" and "Asia (remote)" are dropped.
LOC_BARE_REMOTE = re.compile(
    r"(?i)^[\s,;()-]*(remote|remote[ -]?first|anywhere|global|worldwide|flexible)[\s,;()-]*$")


def get(url, headers=None):
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def norm(company, ats, title, location, url, posted, extra=""):
    return {
        "company": company,
        "ats": ats,
        "title": (title or "").strip(),
        "location": re.sub(r"\s+", " ", str(location or "")).strip(),
        "url": url or "",
        "posted": (posted or "")[:10],
        "extra": extra,
    }


# --- one adapter per ATS. Each returns a list of normalised postings. ---

def f_greenhouse(slug):
    d = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=false" % slug)
    return [norm(slug, "greenhouse", j.get("title"), (j.get("location") or {}).get("name"),
                 j.get("absolute_url"), j.get("updated_at")) for j in d.get("jobs", [])]


def f_lever(slug):
    d = get("https://api.lever.co/v0/postings/%s?mode=json" % slug)
    out = []
    for j in d:
        c = j.get("categories") or {}
        ts = j.get("createdAt")
        posted = datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat() if ts else ""
        loc = c.get("location") or ""
        if j.get("workplaceType"):
            loc = "%s (%s)" % (loc, j["workplaceType"])
        out.append(norm(slug, "lever", j.get("text"), loc, j.get("hostedUrl"), posted,
                        c.get("team") or ""))
    return out


def f_ashby(slug):
    d = get("https://api.ashbyhq.com/posting-api/job-board/%s?includeCompensation=false" % slug)
    out = []
    for j in d.get("jobs", []):
        locs = [j.get("location") or ""]
        locs += [s.get("location", "") for s in (j.get("secondaryLocations") or [])]
        out.append(norm(slug, "ashby", j.get("title"), " / ".join(x for x in locs if x),
                        j.get("jobUrl"), j.get("publishedAt"), j.get("employmentType") or ""))
    return out


def f_workable(slug):
    d = get("https://apply.workable.com/api/v1/widget/accounts/%s?details=true" % slug)
    out = []
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        if str(j.get("telecommuting")).lower() == "true":
            loc += " (remote)"
        out.append(norm(slug, "workable", j.get("title"), loc,
                        j.get("shortlink") or j.get("url"),
                        j.get("published_on") or j.get("created_at")))
    return out


def f_smartrecruiters(slug):
    out, offset = [], 0
    while True:
        d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d"
                % (slug, offset))
        items = d.get("content", [])
        for j in items:
            lo = j.get("location") or {}
            loc = ", ".join(x for x in [lo.get("city"), lo.get("region"), lo.get("country")] if x)
            if lo.get("remote"):
                loc += " (remote)"
            out.append(norm(slug, "smartrecruiters", j.get("name"), loc,
                            "https://jobs.smartrecruiters.com/%s/%s" % (slug, j.get("id")),
                            j.get("releasedDate")))
        offset += len(items)
        if not items or offset >= d.get("totalFound", 0):
            return out


FETCHERS = {"greenhouse": f_greenhouse, "lever": f_lever, "ashby": f_ashby,
            "workable": f_workable, "smartrecruiters": f_smartrecruiters}


def keep(p, unfiltered=False):
    title, loc = p["title"], p["location"]
    if unfiltered:
        return True
    if not WANT.search(title) or SKIP.search(title):
        return False
    if not loc:
        return True  # no location given, let a human judge
    return bool(LOC_AU.search(loc) or LOC_BARE_REMOTE.match(loc))


def scan(pairs, workers=8):
    hits, errs = [], []

    def one(args):
        ats, slug = args
        try:
            return ats, slug, FETCHERS[ats](slug), None
        except urllib.error.HTTPError as e:
            return ats, slug, [], "HTTP %s" % e.code
        except Exception as e:
            return ats, slug, [], "%s: %s" % (type(e).__name__, e)

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for ats, slug, posts, err in ex.map(one, pairs):
            if err:
                errs.append((ats, slug, err))
            else:
                hits.append((ats, slug, posts))
    return hits, errs


def probe(slug):
    print("probing %r against all five ATS" % slug)
    for ats in FETCHERS:
        try:
            n = len(FETCHERS[ats](slug))
            if n:
                print("  OK   %-16s %s  (%d postings)  <- add to slugs.json live.%s"
                      % (ats, slug, n, ats))
            else:
                print("  empty %-15s %s  (200 but no postings, not this company's ATS)"
                      % (ats, slug))
        except Exception as e:
            print("  fail %-16s %s  %s: %s" % (ats, slug, type(e).__name__, str(e)[:60]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", help="test one slug across all five ATS and exit")
    ap.add_argument("--all", action="store_true", help="skip the title and seniority filter")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    if a.probe:
        probe(a.probe)
        return 0

    cfg = json.load(open(SLUGS, encoding="utf-8"))
    pairs = [(ats, s) for ats, slugs in cfg["live"].items() for s in slugs]
    print("scanning %d boards across %d ATS ..." % (len(pairs), len(cfg["live"])))
    hits, errs = scan(pairs, a.workers)

    total = sum(len(p) for _, _, p in hits)
    seen, matches = set(), []
    for _, _, posts in hits:
        for p in posts:
            if not keep(p, a.all):
                continue
            k = (p["company"], p["title"].lower())
            if k in seen:
                continue
            seen.add(k)
            matches.append(p)
    matches.sort(key=lambda p: (p["posted"] or "0000"), reverse=True)

    os.makedirs(OUTDIR, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    jf = os.path.join(OUTDIR, "ats-%s.json" % day)
    mf = os.path.join(OUTDIR, "ats-%s.md" % day)
    with open(jf, "w", encoding="utf-8") as f:
        json.dump({"generated": day, "boards_ok": len(hits), "boards_failed": len(errs),
                   "postings_scanned": total, "matches": matches,
                   "errors": [{"ats": x, "slug": y, "error": z} for x, y, z in errs]},
                  f, indent=2)

    with open(mf, "w", encoding="utf-8") as f:
        f.write("# ATS scan %s\n\n%d candidate roles from %d postings across %d boards "
                "(%d boards failed). Zero LLM tokens.\n\n"
                % (day, len(matches), total, len(hits), len(errs)))
        f.write("| Posted | Company | Title | Location | URL |\n|---|---|---|---|---|\n")
        for p in matches:
            f.write("| %s |\n" % " | ".join(str(p[k] or "").replace("|", "/")
                                             for k in ("posted", "company", "title", "location", "url")))
        if errs:
            f.write("\n## Boards that failed this run\n\n")
            for x, y, z in errs:
                f.write("- %s `%s`: %s\n" % (x, y, z))
            f.write("\nA slug failing repeatedly belongs in `tools/slugs.json` under `dead`.\n")

    # ledger, so the next pass and any agent can skip what was just covered
    led = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    for ats, slug, posts in hits:
        led["%s:%s" % (ats, slug)] = {"last_scanned": day, "postings": len(posts),
                                      "matches": sum(1 for p in posts if keep(p, a.all))}
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(led, f, indent=2, sort_keys=True)

    print("boards ok %d, failed %d" % (len(hits), len(errs)))
    print("postings scanned %d, candidates %d" % (total, len(matches)))
    print("wrote %s" % mf)
    if errs:
        print("failed: %s" % ", ".join("%s:%s" % (x, y) for x, y, _ in errs[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
