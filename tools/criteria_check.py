"""Checks your CV and cover letter answer every requirement in a job ad.

Usage: python tools/criteria_check.py AD_FILE PACK_FILE [PACK_FILE ...]
       python tools/criteria_check.py --criteria CRITERIA.txt PACK_FILE [PACK_FILE ...]

AD_FILE is the saved ad (ads/*.md) or the position description text (ads/*-pd.txt).
Criteria are the bullets under headings such as Essential, Key Selection Criteria,
Your skills and experience, What you'll bring, Requirements. Desirable bullets are
optional. With --criteria, one criterion per line; prefix a line with "D:" for desirable.

For each criterion, prints the sentence in the pack that answers it best, or BLANK.
Then flags gap vocabulary: any sentence that points at something you do not have.
Two rules: (1) never name a gap, (2) every essential criterion gets at least a sentence.
Detector only, never rewrites. Exit code 1 on a BLANK essential or any gap phrase.
"""
import re, sys

BULLET = re.compile(r"^\s*(?:[•·▪■\-\*–]|\d+[.)])\s+(.*)")
OPEN = re.compile(r"(?i)^\W*(?:essential|desirable|key selection criteria|selection criteria|"
                  r"your skills and experience|skills and experience|what you.ll bring|what you bring|"
                  r"about you|requirements|what we.re looking for|qualifications and experience|"
                  r"qualifications|must have|nice to have|you have|ideally|the ideal candidate|"
                  r"you will have|we.re looking for|who we.re looking for|you.re the right fit|the right fit if|who you are|experience|"
                  r"what you.ll need|what you need|to be successful|to succeed|key requirements|essential criteria|skills . experience|"
                  r"required experience|required qualifications|required skills|nice.to.have|bonus points|qualifications . competencies|"
                  r"useful experience|technical requirements|what we need)\b.{0,40}$")
OPTIONAL = re.compile(r"(?i)desirable|nice.to.have|ideally|bonus|preferred|useful|advantageous")
CLOSE = re.compile(r"(?i)^\W*(?:what we offer|benefits|perks|application process|other requirements|"
                   r"why work|about us|about the role|about the company|what you.ll (?:do|achieve)|"
                   r"responsibilities|key accountabilities|important information|how to apply|"
                   r"role purpose|role context|the role|salary|location|what.s on offer|on offer|ready to|next steps|"
                   r"day to day|what you.ll be doing|your responsibilities|you.ll be|key responsibilities|certification|what success looks like|"
                   r"recruitment|application contact|job summary|interview process|about the job|candidate mapping|applied with|"
                   r"what .{1,24} offers?|what we offer you|why join|perks)\b")

STOP = set("""a an the and or of to in on for with at by from as is are be been being was were
this that these those it its into over under across within without than then so such which who
whom whose what when where how including include includes included experience demonstrated
ability proven strong practical relevant working work skills skill knowledge understanding
plus etc your you our we they their them his her one at least least well also both either
role position candidate team environment using use used e g eg ie""".split())

# Small synonym map so the matcher sees the pack's wording. Only true equivalences.
SYN = {
    "llm": "language model", "llms": "language models", "genai": "generative ai",
    "ci/cd": "ci cd", "postgres": "postgresql", "js": "javascript", "ts": "typescript",
    "k8s": "kubernetes", "ml": "machine learning", "api": "apis",
}

GAPS = [
    (r"(?i)\bgaps?\b", "names a gap"),
    (r"(?i)\b(?:would|will|am) (?:be )?clos(?:e|ing)\b", "closing a gap"),
    (r"(?i)\bin the first (?:few )?(?:weeks|months)\b", "deferred competence"),
    (r"(?i)\bmy \w+ is \w+ native\b", "reframes a miss (my X is Y)"),
    (r"(?i)\bnot yet\b", "not yet"),
    (r"(?i)\b(?:limited|little|no|without) (?:direct |prior |commercial |production |hands.on )?experience\b", "disclaims experience"),
    (r"(?i)\bstill learning\b|\bnew to\b|\bunfamiliar\b|\bhave not (?:used|worked|built|deployed)\b|\bhaven.t\b", "disclaims experience"),
    (r"(?i)\bI (?:lack|would need to learn|would have to learn)\b", "disclaims experience"),
    (r"(?i)\bweak(?:er|ness|est)?\b", "weakness named"),
    (r"(?i)\balthough I\b|\bwhile I have not\b|\beven though I\b", "concession opener"),
]

def norm(t):
    t = t.lower()
    for k, v in SYN.items():
        t = re.sub(r"(?<![\w/])" + re.escape(k) + r"(?![\w/])", v, t)
    return t

def words(t):
    return [w.rstrip(".") for w in re.findall(r"[a-z][a-z0-9+#.]*", norm(t)) if w.rstrip(".") not in STOP and len(w) > 1]

# A sentence that restates the ad ("Your stack is Python and React on Azure") is not evidence for it.
RESTATES = re.compile(r"(?i)\b(?:your (?:stack|pd|position description|ad|team|role)|you (?:ask|describe|are looking|want|need)|the (?:pd|ad) (?:asks|says|lists))\b")

def sentences(t):
    t = re.sub(r"(?m)^\s*#+\s.*$", "", t)          # markdown headings are not sentences
    t = re.sub(r"(?m)^\s*[-*•]\s+", "", t)      # bullets: keep the text, drop the marker
    t = re.sub(r"\s+", " ", t)
    parts = re.split(r"(?<=[.!?:])\s+(?=[A-Z\"'(])", t)
    return [p.strip() for p in parts if len(p.split()) > 2 and not RESTATES.search(p)]

def read_text(path):
    b = open(path, "rb").read()
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:            # agg_scan ad files can be cp1252
        return b.decode("cp1252", errors="replace")

def criteria_from_ad(path):
    out, section, optional = [], None, False
    cur, bullets = None, 0
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line:
            if cur:
                out.append((cur, optional)); cur = None
            continue
        if OPEN.match(line) and not BULLET.match(line) and len(line.split()) <= 8:
            if cur:
                out.append((cur, optional)); cur = None
            section, optional, bullets = line, bool(OPTIONAL.search(line)), 0
            continue
        if CLOSE.match(line) and len(line.split()) <= 8:
            if cur:
                out.append((cur, optional)); cur = None
            section = None
            continue
        if section is None:
            continue
        m = BULLET.match(line)
        if m:
            if cur:
                out.append((cur, optional))
            cur = m.group(1).strip(); bullets += 1
        elif bullets == 0 and not line.endswith(":") and len(line.split()) > 3:
            for part in sentences(line):       # LinkedIn or paragraph style: no marker, one criterion per sentence
                out.append((part, optional))
        elif cur and not line.isupper() and not line.endswith(":") and len(line.split()) > 3:
            cur += " " + line            # wrapped PD line
        elif cur:
            out.append((cur, optional)); cur = None
    if cur:
        out.append((cur, optional))
    seen, uniq = set(), []
    for c, o in out:
        k = re.sub(r"\W+", " ", c.lower()).strip()
        if k not in seen and len(c.split()) >= 3:
            seen.add(k); uniq.append((c, o))
    return uniq

def criteria_from_file(path):
    out = []
    for line in open(path, encoding="utf-8").read().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tag = line[:2].upper()
        out.append((line[2:].strip() if tag in ("D:", "E:", "K:") else line, tag == "D:"))
    return out

def score(crit, sent):
    cw = set(words(crit)); sw = set(words(sent))
    if not cw:
        return 0.0, set()
    hits = cw & sw
    for c in cw - hits:              # stem credit: deploy/deployment, orchestrat...
        if len(c) > 5 and any(s.startswith(c[:6]) for s in sw):
            hits.add(c)
    return len(hits) / len(cw), hits

def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    if argv[1] == "--criteria":
        crits, packs = criteria_from_file(argv[2]), argv[3:]
    else:
        crits, packs = criteria_from_ad(argv[1]), argv[2:]
    if not crits:
        sys.exit("no criteria found; pass --criteria FILE with one per line")
    text = "\n".join(open(p, encoding="utf-8").read() for p in packs)
    sents = sentences(text)
    flagged = 0
    print(f"== {len(crits)} criteria against {', '.join(packs)} ({len(sents)} sentences)\n")
    for i, (c, opt) in enumerate(crits, 1):
        best = max(((score(c, s), s) for s in sents), key=lambda x: x[0][0], default=((0, set()), ""))
        (r, hits), s = best
        tag = "desirable" if opt else "ESSENTIAL"
        status = "ok" if r >= 0.34 or len(hits) >= 3 else ("thin" if hits else "BLANK")
        if status == "BLANK" and not opt:
            flagged += 1
        print(f"{i}. [{tag}] {c}")
        if status == "BLANK":
            print("   -> BLANK: nothing in the pack touches this\n")
        else:
            print(f"   -> {status} ({len(hits)} words: {', '.join(sorted(hits))})")
            print(f"      {s[:220]}{'...' if len(s) > 220 else ''}\n")
    print("== gap vocabulary")
    any_gap = False
    for pat, label in GAPS:
        for m in re.finditer(pat, text):
            any_gap = True; flagged += 1
            line = text.count("\n", 0, m.start()) + 1
            ctx = text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
            print(f"  {label} (line {line}): ...{ctx.strip()}...")
    if not any_gap:
        print("  none")
    return flagged

if __name__ == "__main__":
    sys.exit(1 if main(sys.argv) else 0)
