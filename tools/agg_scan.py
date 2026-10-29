#!/usr/bin/env python
"""Job board scan, zero LLM tokens.

Searches Seek, Jora, Talent.com, Workday career sites and, where they apply,
GradConnection, Built In Melbourne and Careers Vic. LinkedIn and Indeed are off unless
extra_sources in my-profile.toml switches them on: their terms do not allow automated access. What it searches for and where
comes from my-profile.toml. These sites block AI web tools but answer plain HTTP with a
browser User-Agent. They can rate limit or change their pages without notice; a source
that returns zero is flagged so you know.

  Seek      https://www.seek.com.au/api/jobsearch/v5/search   JSON, public

  Seek      https://www.seek.com.au/api/jobsearch/v5/search   JSON, public
  LinkedIn  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search   HTML cards, no login
            https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>             HTML detail, no login

Usage:
    python tools/agg_scan.py                 # last 7 days, your city + remote AU, filtered
    python tools/agg_scan.py --days 3
    python tools/agg_scan.py --all           # skip the title and seniority filter
    python tools/agg_scan.py --details       # also fetch the description for every kept ad
                                             # into sourcing/agg-<date>-details/<source>-<id>.txt

Writes sourcing/agg-<date>.md and .json. Reuses the WANT, SKIP and location
regexes from ats_scan.py so the two scans agree on what a candidate is.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ats_scan import WANT, SKIP, LOC_AU, LOC_BARE_REMOTE, UA  # noqa: E402

ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "sourcing")

import myprofile  # noqa: E402
P = myprofile.search()
TITLES = P["job_titles"]
CITY_STATE = f"{P['city']} {P['state']}"          # "Melbourne VIC", the form Jora, Talent and Indeed take

SEEK_KEYWORDS = TITLES
SEEK_WHERE = [f"All {CITY_STATE}" if P["is_capital"] else CITY_STATE]
SEEK_REMOTE_KEYWORDS = ["remote " + t for t in TITLES[:3]] if P["include_remote"] else []

LI_KEYWORDS = TITLES
LI_LOCATION = f"{P['city']}, {P['state_name']}, Australia"
LI_REMOTE_LOCATION = "Australia"
LI_PAGE = 10           # cards per guest call
LI_MAX_START = 90      # 10 pages per keyword, plenty for a 7 day window


def http(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                               "Accept-Language": "en-AU,en;q=0.9"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # 403 too: Jora and Seek detail pages throw intermittent 403s that pass on a retry
            if e.code in (403, 429) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    return ""


# ----------------------------------------------------------------- Seek
def seek_search(keywords, where, days, page):
    q = {"siteKey": "AU-Main", "sourcesystem": "houston", "where": where, "keywords": keywords,
         "dateRange": str(days), "page": str(page), "pageSize": "100", "sortmode": "ListedDate"}
    return json.loads(http("https://www.seek.com.au/api/jobsearch/v5/search?" + urllib.parse.urlencode(q)))


def seek_rows(days):
    rows = {}
    jobs = [(k, w) for k in SEEK_KEYWORDS for w in SEEK_WHERE] + [(k, "Australia") for k in SEEK_REMOTE_KEYWORDS]

    def one(kw):
        k, w = kw
        out = []
        page = 1
        while page <= 5:
            try:
                d = seek_search(k, w, days, page)
            except Exception as e:  # noqa: BLE001
                return out, f"seek {k!r} {w!r} p{page}: {e}"
            data = d.get("data", [])
            out.extend(data)
            if len(data) < 100:
                break
            page += 1
        return out, None

    errs = []
    with cf.ThreadPoolExecutor(6) as ex:
        for data, err in ex.map(one, jobs):
            if err:
                errs.append(err)
            for x in data:
                jid = str(x["id"])
                if jid in rows:
                    continue
                loc = ", ".join(l.get("label", "") for l in x.get("locations", [])) or x.get("locationWhereValue", "")
                wa = (x.get("workArrangements") or {}).get("displayText", "")
                rows[jid] = {
                    "source": "seek", "id": jid,
                    "company": x.get("companyName") or (x.get("advertiser") or {}).get("description", ""),
                    "title": x.get("title", ""), "location": loc, "mode": wa,
                    "salary": x.get("salaryLabel", ""), "type": ", ".join(x.get("workTypes", [])),
                    "posted": (x.get("listingDate") or "")[:10], "teaser": x.get("teaser", ""),
                    "url": f"https://www.seek.com.au/job/{jid}",
                }
    return list(rows.values()), errs


def seek_detail(jid):
    h = http(f"https://www.seek.com.au/job/{jid}", accept="text/html")
    # The ad body is the div with data-automation="jobAdDetails" (verified 2026-09-08).
    k = h.find('data-automation="jobAdDetails"')
    if k > 0:
        seg = h[k:]
        e = re.search(r'data-automation="job-detail-(apply|footer|salary)|<footer|id="footer', seg)
        seg = seg[:e.start()] if e else seg[:40000]
        body = strip(seg)
        if len(body) > 200:
            return body
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try:
            j = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        nodes = j.get("@graph", [j]) if isinstance(j, dict) else j
        for n in nodes:
            if isinstance(n, dict) and n.get("@type") == "JobPosting" and n.get("description"):
                return strip(n["description"])
    # Fallback: Seek embeds the ad body in its Apollo state as "content"
    m = re.search(r'"content":"((?:[^"\\]|\\.)*)"', h)
    if m:
        try:
            return strip(json.loads('"' + m.group(1) + '"'))
        except Exception:  # noqa: BLE001
            pass
    return ""


# ------------------------------------------------------------- LinkedIn
def li_search(keywords, location, days, start, remote=False):
    q = {"keywords": keywords, "location": location, "f_TPR": f"r{days * 86400}", "start": str(start)}
    if remote:
        q["f_WT"] = "2"
    h = http("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(q),
             accept="text/html")
    cards = []
    for card in re.findall(r'<li>(.*?)</li>', h, re.S):
        m = re.search(r'urn:li:jobPosting:(\d+)', card)
        if not m:
            continue
        t = re.search(r'base-search-card__title">\s*(.*?)\s*<', card, re.S)
        c = re.search(r'base-search-card__subtitle">\s*(?:<a[^>]*>)?\s*(.*?)\s*<', card, re.S)
        l = re.search(r'job-search-card__location">\s*(.*?)\s*<', card, re.S)
        d = re.search(r'<time[^>]*datetime="([^"]+)"', card)
        cards.append({"source": "linkedin", "id": m.group(1),
                      "title": html.unescape(t.group(1)) if t else "", "company": html.unescape(c.group(1)) if c else "",
                      "location": html.unescape(l.group(1)) if l else "", "mode": "Remote" if remote else "",
                      "salary": "", "type": "", "posted": d.group(1) if d else "", "teaser": "",
                      "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}"})
    return cards


def li_rows(days):
    rows = {}
    jobs = [(k, LI_LOCATION, False) for k in LI_KEYWORDS]
    if P["include_remote"]:
        jobs += [(k, LI_REMOTE_LOCATION, True) for k in LI_KEYWORDS[:4]]

    def one(job):
        k, loc, remote = job
        out = []
        for start in range(0, LI_MAX_START + 1, LI_PAGE):
            try:
                cards = li_search(k, loc, days, start, remote)
            except Exception as e:  # noqa: BLE001
                return out, f"linkedin {k!r} {loc!r} start={start}: {e}"
            out.extend(cards)
            if len(cards) < LI_PAGE:
                break
            time.sleep(0.5)
        return out, None

    errs = []
    with cf.ThreadPoolExecutor(3) as ex:   # LinkedIn rate limits harder than Seek
        for cards, err in ex.map(one, jobs):
            if err:
                errs.append(err)
            for c in cards:
                rows.setdefault(c["id"], c)
    return list(rows.values()), errs


def li_detail(jid):
    h = http(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}", accept="text/html")
    m = re.search(r'show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', h, re.S)
    body = strip(m.group(1)) if m else ""
    crit = re.findall(r'description__job-criteria-text[^>]*>\s*(.*?)\s*<', h, re.S)
    head = "Criteria: " + " | ".join(html.unescape(c.strip()) for c in crit) if crit else ""
    return (head + "\n\n" + body).strip()


# ------------------------------------------------- Jora (search HTML, cards carry JSON)
JORA_QUERIES = TITLES[:6]


def jora_rows(days):
    rows, errs = {}, []
    for q in JORA_QUERIES:
        for page in (1, 2):
            u = ("https://au.jora.com/j?" + urllib.parse.urlencode(
                {"sp": "search", "q": q, "l": CITY_STATE, "a": str(min(days, 7)), "p": str(page)}))
            try:
                h = http(u, accept="text/html")
            except Exception as e:  # noqa: BLE001
                errs.append(f"jora {q!r} p{page}: {e}"); break
            n = 0
            for card in re.findall(r'<div id="r_[0-9a-f]+" class="job-card(.*?)(?=<div id="r_[0-9a-f]+" class="job-card|<div id="footer|$)', h, re.S):
                m = re.search(r'data-braze-job-panel-view="([^"]+)"', card)
                if not m:
                    continue
                try:
                    j = json.loads(html.unescape(m.group(1)))
                except Exception:  # noqa: BLE001
                    continue
                jid = j.get("job_id", "")
                if not jid or jid in rows:
                    continue
                n += 1
                listed = re.search(r'job-listed-date[^>]*>\s*(.*?)\s*<', card, re.S)
                sal = re.search(r'job-salary[^>]*>\s*(.*?)\s*<', card, re.S)
                rows[jid] = {"source": "jora", "id": jid, "company": html.unescape(j.get("company_name", "")),
                             "title": html.unescape(j.get("job_title", "")), "location": html.unescape(j.get("location", "")),
                             "mode": "", "salary": html.unescape(sal.group(1)) if sal else "", "type": "",
                             "posted": html.unescape(listed.group(1)) if listed else "", "teaser": "",
                             "url": f"https://au.jora.com/job/{jid}"}
            if n < 15:
                break
            time.sleep(0.5)
    return list(rows.values()), errs


# ---------------------------------------- Talent.com (listing gives ids, detail gives text)
TALENT_QUERIES = TITLES[:6]


def talent_ids(days):
    ids, errs = [], []
    for q in TALENT_QUERIES:
        u = "https://au.talent.com/jobs?" + urllib.parse.urlencode({"k": q, "l": CITY_STATE, "date": str(min(days, 7))})
        try:
            h = http(u, accept="text/html")
        except Exception as e:  # noqa: BLE001
            errs.append(f"talent {q!r}: {e}"); continue
        for m in re.finditer(r'/view\?id=(\d+)', h):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    if not P["include_remote"]:
        return ids, errs
    u = "https://au.talent.com/jobs?" + urllib.parse.urlencode({"k": "remote " + TITLES[0], "l": "Australia", "date": str(min(days, 7))})
    try:
        for m in re.finditer(r'/view\?id=(\d+)', http(u, accept="text/html")):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    except Exception as e:  # noqa: BLE001
        errs.append(f"talent remote: {e}")
    return ids, errs


def talent_detail(jid):
    """Returns (row, body). Description sits after the literal 'Job description</span>' marker."""
    h = http(f"https://au.talent.com/view?id={jid}", accept="text/html")
    t = re.search(r'<title>(.*?)</title>', h, re.S)
    title = html.unescape(t.group(1)) if t else ""
    # "<title> – <company> – Job <location>" or "... – Remote job <location>"
    parts = [p.strip() for p in re.split(r'\s[–-]\s', title)]
    role = parts[0] if parts else ""
    company = parts[1] if len(parts) > 1 else ""
    loc = re.sub(r'^(Remote )?[Jj]ob\s*', '', parts[2]) if len(parts) > 2 else ""
    mode = "Remote" if len(parts) > 2 and parts[2].lower().startswith("remote") else ""
    k = h.find("Job description</span>")
    body = ""
    if k > 0:
        seg = h[k:]; e = seg.find("styles_relatedJobsColumn"); seg = seg[:e if e > 0 else 20000]
        body = strip(seg).replace("Job description", "", 1).strip()
    posted = ""
    m = re.search(r'datePosted"\s*:\s*"([^"]+)"', h)
    if m:
        posted = m.group(1)[:10]
    else:
        m = re.search(r'(\d+) days? ago', h)
        if m:
            posted = (dt.date.today() - dt.timedelta(days=int(m.group(1)))).isoformat()
        elif re.search(r'\b(today|hours? ago)\b', h):
            posted = dt.date.today().isoformat()
    row = {"source": "talent", "id": jid, "company": company, "title": role, "location": loc, "mode": mode,
           "salary": "", "type": "", "posted": posted, "teaser": "",
           "url": f"https://au.talent.com/view?id={jid}"}
    return row, body


def talent_rows(days, ddir=None):
    ids, errs = talent_ids(days)
    rows = []

    def one(jid):
        try:
            row, body = talent_detail(jid)
        except Exception as e:  # noqa: BLE001
            return None, f"talent detail {jid}: {e}"
        if ddir and body and keep(row):
            with open(os.path.join(ddir, f"talent-{safe_id(jid)}.txt"), "w", encoding="utf-8") as f:
                f.write(f"{row['company']} | {row['title']} | {row['location']} | {row['mode']} | posted {row['posted']}\n{row['url']}\n\n{body}\n")
        return row, None

    with cf.ThreadPoolExecutor(4) as ex:
        for row, err in ex.map(one, ids):
            if err:
                errs.append(err)
            elif row:
                rows.append(row)
    return rows, errs


# ------------------------------------------------------- GradConnection
def gradconn_rows(days):
    rows, errs = {}, []
    # Only runs when my-profile.toml lists graduate_categories (GradConnection's own category slugs).
    city = P["city"].lower().replace(" ", "-")
    paths = [f"graduate-jobs/{c}/{w}/" for c in P["graduate_categories"] for w in (city, "australia")]
    for path in paths:
        try:
            h = http("https://au.gradconnection.com/" + path, accept="text/html")
        except Exception as e:  # noqa: BLE001
            errs.append(f"gradconnection {path}: {e}"); continue
        for m in re.finditer(r'href="(/employers/([^/"]+)/jobs/([^/"]+)/)"[^>]*>\s*<h3>(.*?)</h3>', h, re.S):
            url, emp, slug, title = m.groups()
            title = html.unescape(title)
            if slug in rows or title.lower().startswith("event"):
                continue
            rows[slug] = {"source": "gradconnection", "id": slug, "company": emp.replace("-", " ").title(),
                          "title": title, "location": CITY_STATE if not path.endswith("/australia/") else "Australia",
                          "mode": "", "salary": "", "type": "Graduate", "posted": "", "teaser": "",
                          "url": "https://au.gradconnection.com" + url}
    return list(rows.values()), errs


def gradconn_detail(url):
    h = http(url, accept="text/html")
    m = re.search(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S)
    if m:
        try:
            j = json.loads(m.group(1))
            nodes = j if isinstance(j, list) else j.get("@graph", [j])
            for n in nodes:
                if isinstance(n, dict) and n.get("description"):
                    return strip(n["description"])
        except Exception:  # noqa: BLE001
            pass
    m = re.search(r'(?:job-description|campaign-content)[^>]*>(.*?)</section>', h, re.S)
    return strip(m.group(1)) if m else strip(h)[:6000]


# ----------------------------------------------------- Built In Melbourne
def builtin_rows(days):
    rows, errs = {}, []
    if P["city"].lower() != "melbourne":     # Built In only has a Melbourne site, and only tech roles
        return [], []
    for page in (1, 2, 3):
        u = f"https://builtinmelbourne.com/jobs/dev-engineering?daysSinceUpdated={min(days, 7)}&page={page}"
        try:
            h = http(u, accept="text/html")
        except Exception as e:  # noqa: BLE001
            errs.append(f"builtin p{page}: {e}"); break
        n = 0
        # markup changed by 2026-09-30 (the old pattern silently matched nothing): each card is
        # <div id="job-card-<id>"> holding data-id="company-title", data-id="job-card-title" and the location icon
        starts = [(m.start(), m.group(1)) for m in re.finditer(r'id="job-card-(\d+)"', h)]
        for i, (pos, jid) in enumerate(starts):
            card = h[pos:starts[i + 1][0] if i + 1 < len(starts) else pos + 8000]
            t = re.search(r'<a[^>]+href="(/job/[^"]+)"[^>]*data-id="job-card-title"[^>]*>(.*?)</a>', card, re.S)
            if not t or jid in rows:
                continue
            title = html.unescape(re.sub(r'<[^>]+>', '', t.group(2))).strip()
            n += 1
            c = re.search(r'data-id="company-title"[^>]*>\s*<span>([^<]+)</span>', card)
            l = re.search(r'fa-location-dot.*?<span[^>]*>\s*([^<]+)<', card, re.S)
            md = re.search(r'fa-house-building.*?<span[^>]*>\s*([^<]+)<', card, re.S)
            rows[jid] = {"source": "builtin", "id": jid, "company": html.unescape(c.group(1)).strip() if c else "",
                         "title": title, "location": html.unescape(l.group(1)).strip() if l else "Melbourne VIC",
                         "mode": md.group(1).strip() if md else "", "salary": "", "type": "", "posted": "", "teaser": "",
                         "url": "https://builtinmelbourne.com" + t.group(1)}
        if n == 0:
            if page == 1:
                errs.append("builtin p1: page loaded but 0 cards parsed (markup change?)")
            break
    return list(rows.values()), errs


def builtin_detail(url):
    h = http(url, accept="text/html")
    m = re.search(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S)
    if m:
        try:
            j = json.loads(m.group(1))
            if isinstance(j, dict) and j.get("description"):
                return strip(j["description"])
        except Exception:  # noqa: BLE001
            pass
    m = re.search(r'job-description[^>]*>(.*?)</div>\s*</div>', h, re.S)
    return strip(m.group(1)) if m else ""


# ----------------------------------------------------- Indeed (added 2026-10-06)
# Search pages answer a browser UA with the job cards as JSON in window.mosaic.providerData;
# viewjob detail pages 403, so Indeed is list only, like Jora.
INDEED_QUERIES = [(t, CITY_STATE) for t in TITLES[:6]] + ([("remote " + TITLES[0], "Australia")] if P["include_remote"] else [])


def curl(url):
    # Indeed 403s urllib and Windows' own System32 curl.exe (TLS fingerprint) but answers Git's mingw curl.
    # A bare "curl" in subprocess finds System32 first, so resolve PATH order with shutil.which.
    import shutil, subprocess
    r = subprocess.run([shutil.which("curl") or "curl", "-s", "-L", "--max-time", "30", "-A", UA, "-H", "Accept-Language: en-AU,en;q=0.9",
                        "-w", "\n%{http_code}", url], capture_output=True, timeout=40)
    body, _, code = r.stdout.decode("utf-8", "replace").rpartition("\n")
    if code != "200":
        raise RuntimeError(f"HTTP {code}")
    return body


def indeed_rows(days):
    rows, errs = {}, []
    for q, loc in INDEED_QUERIES:
        for start in (0, 10, 20):
            u = "https://au.indeed.com/jobs?" + urllib.parse.urlencode(
                {"q": q, "l": loc, "fromage": str(min(days, 14)), "start": str(start)})
            try:
                h = curl(u)
            except Exception as e:  # noqa: BLE001
                errs.append(f"indeed {q!r} start={start}: {e}"); break
            m = re.search(r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});\s*\n', h, re.S)
            if not m:
                if start == 0:
                    errs.append(f"indeed {q!r}: no job card JSON (markup change or bot wall?)")
                break
            try:
                res = json.loads(m.group(1))["metaData"]["mosaicProviderJobCardsModel"]["results"]
            except Exception as e:  # noqa: BLE001
                errs.append(f"indeed {q!r}: {e}"); break
            n = 0
            for j in res:
                jk = j.get("jobkey", "")
                if not jk or jk in rows:
                    continue
                n += 1
                pub = j.get("pubDate")
                rows[jk] = {"source": "indeed", "id": jk, "company": j.get("company", ""),
                            "title": j.get("displayTitle", ""), "location": j.get("formattedLocation", ""),
                            "mode": "Remote" if j.get("remoteLocation") else "",
                            "salary": (j.get("salarySnippet") or {}).get("text", ""), "type": "",
                            "posted": dt.datetime.fromtimestamp(pub / 1000).date().isoformat() if pub else "",
                            "teaser": "", "url": f"https://au.indeed.com/viewjob?jk={jk}"}
            if n == 0:
                break
            time.sleep(1)
    return list(rows.values()), errs


# ------------------------------------------- Careers Vic, Victorian government (added 2026-10-06)
# Careers Vic finds nothing for two-word searches, so it gets the single words from title_words.
VIC_QUERIES = myprofile.load().get("filter", {}).get("title_words", [])[:6] or [t.split()[-1] for t in TITLES[:3]]


def vic_rows(days):
    # no posted date on the listing; "Applications close" stands in, and the rank diff handles repeats
    rows, errs = {}, []
    if P["state"] != "VIC":                  # Victorian government jobs only
        return [], []
    for q in VIC_QUERIES:
        for page in (0, 1, 2):
            u = "https://www.careers.vic.gov.au/jobs?" + urllib.parse.urlencode({"keywords": q, "page": str(page)})
            try:
                h = http(u, accept="text/html")
            except Exception as e:  # noqa: BLE001
                errs.append(f"vic {q!r} p{page}: {e}"); break
            n = 0
            cards = h.split('class="job-searchResult"')[1:]
            for card in cards:
                t = re.search(r'href="(/job/[^"]+-(\d+))"[^>]*>\s*<h3>(.*?)</h3>', card, re.S)
                if not t or t.group(2) in rows:
                    continue
                n += 1
                f = {k.strip(): strip(v) for k, v in re.findall(r'<strong>([^<]+):</strong></p>\s*<p>(.*?)</p>', card, re.S)}
                org = re.search(r'</h3></a>\s*<p[^>]*>([^<]+)</p>', card)
                rows[t.group(2)] = {"source": "vic", "id": t.group(2), "company": html.unescape(org.group(1)).strip() if org else "",
                                    "title": html.unescape(strip(t.group(3))), "location": f.get("Location", "") + " VIC",
                                    "mode": "", "salary": f.get("Salary", ""), "type": f.get("Work Type", ""),
                                    "posted": "", "teaser": "closes " + f.get("Applications close", ""),
                                    "url": "https://www.careers.vic.gov.au" + t.group(1)}
            if n == 0:
                if page == 0 and not cards:
                    errs.append(f"vic {q!r}: 0 cards parsed (markup change?)")
                break
    return list(rows.values()), errs


def vic_detail(url):
    h = http(url, accept="text/html")
    s = strip(h)
    i = s.find("About the")
    return s[i:i + 8000] if i >= 0 else s[:8000]


# ------------------------------------------ Workday CXS JSON (added 2026-10-06)
# Probed 2026-10-06. 200: the five below. 422 (tenant exists, site name unknown, find it on the
# careers page before adding): coles, auspost, medibank, anz, monash, unimelb, carsales, aglenergy,
# originenergy, wesfarmers, kmart, nine, suncorp, westpac, deakin, bendigoadelaide. 401: seek.
# 404: bupa, transurban, iress.
WORKDAY = [("reagroup", "wd3", "reacareers", "REA Group"), ("dowjones", "wd1", "News_Corp_Australia_Careers", "News Corp Australia"),
           ("nab", "wd3", "nab_careers", "NAB"), ("telstra", "wd3", "Telstra_Careers", "Telstra"),
           ("cba", "wd3", "CommBank_Careers", "Commonwealth Bank"),
           # Added 2026-10-29, each checked to return postings: office and graduate roles for the wider kit audience.
           ("bunnings", "wd3", "Careers", "Bunnings"), ("nbn", "wd3", "nbncareers", "NBN Co"),
           ("csl", "wd1", "CSL_External", "CSL"), ("rmit", "wd3", "rmit_careers", "RMIT University"),
           ("uq", "wd3", "uqcareers", "University of Queensland"), ("bdoau", "wd105", "BDOEarlyCareers", "BDO Australia")]
WORKDAY_QUERIES = TITLES[:4]


def _wd_post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def workday_rows(days, ddir=None):
    rows, errs = {}, []
    for tenant, wd, site, name in WORKDAY:
        base = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
        paths = {}
        for q in WORKDAY_QUERIES:
            try:
                d = _wd_post(base + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q})
            except Exception as e:  # noqa: BLE001
                errs.append(f"workday {tenant} {q!r}: {e}"); break
            for p in d.get("jobPostings", []):
                m = re.search(r'Posted (Today|Yesterday|(\d+) Days? Ago)', p.get("postedOn", ""))
                age = 0 if m and m.group(1) == "Today" else 1 if m and m.group(1) == "Yesterday" else int(m.group(2)) if m else 99
                if age <= days:
                    paths[p["externalPath"]] = (p, age)
        def detail(path):
            try:
                return path, json.loads(http(base + path))["jobPostingInfo"], None
            except Exception as e:  # noqa: BLE001
                return path, None, f"workday detail {tenant}{path}: {e}"
        with cf.ThreadPoolExecutor(4) as ex:
            got = list(ex.map(detail, paths))
        for path, info, err in got:
            if err:
                errs.append(err); continue
            p, age = paths[path]
            jid = info.get("jobReqId") or path.rsplit("_", 1)[-1]
            row = {"source": "workday", "id": f"{tenant}-{jid}", "company": name, "title": info.get("title", p.get("title", "")),
                   "location": info.get("location", p.get("locationsText", "")), "mode": "", "salary": "",
                   "type": info.get("timeType", ""), "posted": (dt.date.today() - dt.timedelta(days=age)).isoformat(),
                   "teaser": "", "url": info.get("externalUrl", "")}
            rows[row["id"]] = row
            if ddir:
                with open(os.path.join(ddir, f"workday-{safe_id(row['id'])}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"{name} | {row['title']} | {row['location']} | | | posted {row['posted']}\n{row['url']}\n\n"
                            f"{strip(info.get('jobDescription', ''))}\n")
    return list(rows.values()), errs


# --------------------------------------------------------------- shared
def safe_id(x):
    """Job IDs come from the job sites; keep only safe characters before using one in a file name."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(x))[:80] or "unknown"


def strip(s):
    s = re.sub(r'<br\s*/?>|</p>|</li>|</div>|</h\d>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    return re.sub(r'\n\s*\n+', '\n', s).strip()


def keep(r, unfiltered=False):
    if unfiltered:
        return True
    t = r["title"]
    if not WANT.search(t) or SKIP.search(t):
        return False
    loc = r["location"] or ""
    return bool(LOC_AU.search(loc) or LOC_BARE_REMOTE.match(loc) or r["mode"] == "Remote")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=P["days"])
    ap.add_argument("--all", action="store_true", help="skip the title and seniority filter")
    ap.add_argument("--details", action="store_true", help="fetch descriptions for kept ads")
    ap.add_argument("--quick", action="store_true", help="Seek and Talent.com only, for a fast first try")
    extra = [x for x in myprofile.load().get("search", {}).get("extra_sources", []) if x in ("linkedin", "indeed")]
    ap.add_argument("--sources", default=",".join(["seek", "jora", "talent", "gradconnection", "builtin", "vic", "workday"] + extra),
                    help="comma list; Glassdoor, Prosple and Adzuna block scripts (403/400 on 2026-09-08); "
                         "Indeed search pages answer since 2026-10-06, its detail pages still 403")
    a = ap.parse_args()
    src = {"seek", "talent"} if a.quick else set(a.sources.split(","))

    day = dt.date.today().isoformat()
    ddir = os.path.join(OUTDIR, f"agg-{day}-details")
    if a.details:
        os.makedirs(ddir, exist_ok=True)
    rows, errs = [], []
    fetchers = {"seek": seek_rows, "linkedin": li_rows, "jora": jora_rows, "gradconnection": gradconn_rows,
                "builtin": builtin_rows, "talent": lambda d: talent_rows(d, ddir if a.details else None),
                "indeed": indeed_rows, "vic": vic_rows, "workday": lambda d: workday_rows(d, ddir if a.details else None)}
    for name, fn in fetchers.items():
        if name not in src:
            continue
        try:
            r, e = fn(a.days)
        except Exception as ex:  # noqa: BLE001
            r, e = [], [f"{name}: {ex}"]
        rows += r; errs += e
        flag = "  <-- ZERO, check this source" if not r else ""
        print(f"{name}: {len(r)} postings, {len(e)} errors{flag}", file=sys.stderr)

    kept = [r for r in rows if keep(r, a.all)]
    kept.sort(key=lambda r: (r["posted"] or ""), reverse=True)
    print(f"postings scanned {len(rows)}, candidates {len(kept)}", file=sys.stderr)

    if a.details and kept:
        DETAIL = {"seek": lambda r: seek_detail(r["id"]), "linkedin": lambda r: li_detail(r["id"]),
                  "gradconnection": lambda r: gradconn_detail(r["url"]), "builtin": lambda r: builtin_detail(r["url"]),
                  "vic": lambda r: vic_detail(r["url"])}

        def fetch(r):
            fn = os.path.join(ddir, f"{r['source']}-{safe_id(r['id'])}.txt")
            if os.path.exists(fn) or r["source"] not in DETAIL:   # jora and indeed detail pages 403; talent and workday written during scan
                return None
            try:
                body = DETAIL[r["source"]](r)
            except Exception as e:  # noqa: BLE001
                return f"detail {r['source']} {r['id']}: {e}"
            with open(fn, "w", encoding="utf-8") as f:
                f.write(f"{r['company']} | {r['title']} | {r['location']} | {r['mode']} | {r['salary']} | "
                        f"posted {r['posted']}\n{r['url']}\n\n{body}\n")
            time.sleep(0.4)
            return None

        with cf.ThreadPoolExecutor(3) as ex:
            errs += [e for e in ex.map(fetch, kept) if e]
        print(f"details written to {ddir}", file=sys.stderr)

    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, f"agg-{day}.json"), "w", encoding="utf-8") as f:
        json.dump({"generated": day, "days": a.days, "scanned": len(rows), "errors": errs, "candidates": kept},
                  f, indent=1, ensure_ascii=False)
    md = [f"# Aggregator scan {day}", "",
          f"{len(kept)} candidate roles from {len(rows)} postings, last {a.days} days. Zero LLM tokens.", "",
          "| Posted | Source | Company | Title | Location | Mode | Salary | URL |", "|---|---|---|---|---|---|---|---|"]
    for r in kept:
        md.append(f"| {r['posted']} | {r['source']} | {r['company']} | {r['title']} | {r['location']} | "
                  f"{r['mode']} | {r['salary']} | {r['url']} |")
    if errs:
        md += ["", "## Errors", ""] + [f"- {e}" for e in errs]
    with open(os.path.join(OUTDIR, f"agg-{day}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"wrote {os.path.join(OUTDIR, f'agg-{day}.md')}", file=sys.stderr)


if __name__ == "__main__":
    main()
