"""Reads my-profile.toml, the one file that holds everything personal.

Every script imports this instead of hard-coding names, titles or locations.
Python 3.11+ (tomllib is in the standard library from 3.11).
"""
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "my-profile.toml")
EXAMPLE = os.path.join(ROOT, "examples", "my-profile.example.toml")

STATES = {"VIC": "Victoria", "NSW": "New South Wales", "QLD": "Queensland", "WA": "Western Australia",
          "SA": "South Australia", "TAS": "Tasmania", "ACT": "Australian Capital Territory",
          "NT": "Northern Territory"}
CAPITALS = {"melbourne", "sydney", "brisbane", "perth", "adelaide", "hobart", "canberra", "darwin"}


def load(required=True):
    if not os.path.exists(PATH):
        if not required:
            return {}
        sys.exit("No my-profile.toml yet. Open this folder in Claude Code and type /setup,\n"
                 "or copy examples/my-profile.example.toml to my-profile.toml and fill it in.")
    try:
        with open(PATH, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"my-profile.toml has a typo: {e}. "
                 "Ask Claude to fix it, or compare it with examples/my-profile.example.toml.")


def words_re(words):
    """Whole-word, case-insensitive match for any phrase in the list. Spaces match any gap."""
    words = [w.strip() for w in words if w.strip()]
    if not words:
        return re.compile(r"(?!x)x")   # matches nothing
    alts = [r"\s+".join(re.escape(p) for p in w.split()) for w in words]
    return re.compile(r"(?i)(?<!\w)(" + "|".join(alts) + r")(?!\w)")


def search():
    s = load().get("search", {})
    city = s.get("city", "Melbourne").strip()
    state = s.get("state", "VIC").strip().upper()
    return {
        "job_titles": s.get("job_titles", ["software engineer"]),
        "city": city,
        "state": state,
        "state_name": STATES.get(state, state),
        "is_capital": city.lower() in CAPITALS,
        "include_remote": s.get("include_remote", True),
        "days": int(s.get("days", 7)),
        "graduate_categories": s.get("graduate_categories", []),
    }


def title_filters():
    f = load().get("filter", {})
    return words_re(f.get("title_words", [])), words_re(f.get("skip_title_words", []))


def location_re():
    s = search()
    # "Remote" on its own is handled by the scanners; "Remote, Canada" must not match here.
    return words_re([s["city"], s["state"], s["state_name"], "australia", "australian", "anz", "apac", "asia pacific"])
