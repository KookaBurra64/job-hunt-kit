"""Writing check for anything you are about to send: CV, cover letter, LinkedIn text, messages.

Usage: python tools/copy_check.py FILE [FILE ...]

Reports: counts, dashes, overused words, AI phrase patterns, sentence-length spread.
Readers increasingly spot AI-written text by exactly these. Word list drawn from
https://aimi.lanadey.com/sound-more-human/ and Wikipedia's "Signs of AI writing",
plus extra_banned_words in my-profile.toml.
Detector only, never rewrites.
Exit code 1 if anything is flagged, so it can gate a build step.
"""
import re, sys

WORDS = r"""
leverag\w* utiliz\w* streamlin\w* delv\w* harness\w* foster\w* unlock\w* unleash\w*
fundamentally essentially robust seamless\w* passionate driven results-oriented
responsible\s+for dedicated innovative detail-oriented cutting-edge groundbreaking
revolutioni[sz]\w* journey landscape
testament underscor\w* pivotal watershed tapestry realm beacon embod\w* resonat\w*
nuanced enduring vibrant bustling intricate transformative elevat\w* enhanc\w*
optimi[sz]\w* profound steadfast keen ecosystem synerg\w* holistic empower\w*
incredible amazing game-changing
""".split()
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import myprofile
WORDS += [re.escape(w) for w in myprofile.load(required=False).get("writing", {}).get("extra_banned_words", [])]
WORD_RE = re.compile(r"(?i)\b(" + "|".join(WORDS) + r")\b")

PHRASES = [
    (r"(?i)\bit(?:'s| is) (?:important|worth) (?:to note|noting)\b", "vague attribution"),
    (r"(?i)\bit is (?:important|essential|crucial) to\b", "it-is construction"),
    (r"(?i)\bserves? as\b|\bstands? as\b", "is-substitution (say 'is')"),
    (r"(?i)\bnot (?:just|only|merely) [^.]{1,60}?\bbut (?:also )?\b", "negative parallelism"),
    (r"(?i)\bit's not about [^.]{1,60}?, it's about\b", "negative parallelism"),
    (r"(?i)\b(?:furthermore|moreover|additionally|in addition|subsequently)\b", "filler transition"),
    (r"(?i)\b(?:in summary|to summari[sz]e|in conclusion|ultimately|to put it simply)\b", "summarising phrase"),
    (r"(?i)\bfrom \w+(?: \w+)? to \w+(?: \w+)?\b(?=[,.;])", "possible false range"),
    (r"(?i)\bsheds? light on\b|\bwealth of\b|\ba testament to\b|\bbroader narrative\b|\brich tapestry\b", "stock phrase"),
    (r"(?i)\bembrac(?:e|es|ing) (?:change|the)\b", "stock phrase"),
    (r"(?i)\bplays? a (?:vital|crucial|key|pivotal) role\b", "exaggerated significance"),
    (r"(?i)\b(?:observers|experts|critics|industry reports?) (?:have )?(?:note|suggest|argue)", "weasel attribution"),
    (r"(?i)\bensuring\b|\bhighlighting\b|\bshowcasing\b", "superficial -ing analysis"),
    (r"\*\*[^*\n]{1,40}:\*\*", "bold-title bullet"),
]

def sentences(t):
    t = re.sub(r"\s+", " ", t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", t)
    return [p for p in parts if len(p.split()) > 1]

def check(path):
    t = open(path, encoding="utf-8").read()
    flagged = 0
    print(f"== {path}")
    dashes = t.count("\u2014") + t.count("\u2013")
    print(f"{len(t)} chars, {len(t.split())} words, dashes {dashes}")
    if dashes:
        flagged += dashes
    words = WORD_RE.findall(t)
    if words:
        flagged += len(words)
        print("blacklist:", ", ".join(sorted(set(w.lower() for w in words))))
    for pat, label in PHRASES:
        for m in re.finditer(pat, t):
            flagged += 1
            line = t.count("\n", 0, m.start()) + 1
            print(f"  {label} (line {line}): {m.group(0).strip()!r}")
    s = sentences(t)
    if s:
        n = [len(x.split()) for x in s]
        short = sum(1 for x in n if x < 10); long_ = sum(1 for x in n if x >= 25)
        print(f"sentences {len(n)}, mean {sum(n)/len(n):.1f} words, min {min(n)}, max {max(n)}, "
              f"short(<10) {short} ({100*short//len(n)}%), long(25+) {long_}")
        if 100 * short // len(n) < 20:
            print("  note: under 20% short sentences; vary the rhythm")
        if max(n) - min(n) < 12:
            print("  note: narrow sentence-length range; add a short or a long one")
    return flagged

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    total = sum(check(p) for p in sys.argv[1:])
    sys.exit(1 if total else 0)
