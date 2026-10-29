---
name: find-jobs
description: Search Australian job sites for roles that match my-profile.toml, rank them, and walk the person through the best ones. Use when they type /find-jobs or ask to look for jobs.
---

# Find jobs

The scripts do the searching, so this costs very little AI usage. Do not browse job sites
with web tools instead.

1. If `my-profile.toml` is missing, do the setup skill first. Read "What I'm looking for" in
   `PLAYBOOK.md`: it holds preferences the settings file can't, and you should use them when
   choosing what to show.
2. Tell them the search takes 5 to 15 minutes. Then run, as one background command:
   `python tools/ats_scan.py; python tools/agg_scan.py --details; python tools/rank_leads.py`
   For a quick first try, use `python tools/agg_scan.py --quick --details` instead of the middle step.
3. When it finishes, check the lines the scanner printed. A source that found zero is marked
   "ZERO". Mention it in one line. Usually the site was busy, and the next run picks it up.
4. Read the top 20 rows of `sourcing/rank-<today>.md` and its "Worth a look" list. Skip any
   marked "seen before".
5. Show the best 5 to 10 as a short numbered list: company, job title, location, salary if
   shown, and one line on why it fits, from the tags. Do not paste ad text.
6. Ask which ones they want to look at. For each one they pick, save the ad text to
   `ads/<company>-<job-title>.md`. The text is in `sourcing/agg-<today>-details/` when the
   scanner got it; otherwise ask them to paste it.
7. Offer to help them apply for the ones they like (the tailor-cv skill).

When they turn a job down, note the reason in "What I'm looking for" in `PLAYBOOK.md` (for
example "no call centre roles") so it isn't suggested again.

If the results look thin and they mention LinkedIn, explain that LinkedIn is off by default
because its terms do not allow automated searching, and that `extra_sources` in
`my-profile.toml` turns it on if they decide to. Indeed is not searched at all; they can
browse it themselves and paste in any ad they like. It is their call; do not push either way.

If the results look wrong, offer to adjust `my-profile.toml`. Too many senior roles: add
words to `skip_title_words`. Nothing relevant: broaden `job_titles`. Then run `rank_leads.py`
again; it re-scores what was already found without searching again.
