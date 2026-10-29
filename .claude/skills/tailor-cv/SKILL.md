---
name: tailor-cv
description: Tailor the CV and write a cover letter for one job ad, check both, and build Word and PDF copies. Use when they type /tailor-cv, paste a job ad, or ask for help applying to a specific job.
---

# Tailor a CV and cover letter

1. **Get the ad.** If they gave a link, try to fetch it. Seek, LinkedIn, Indeed and Jora block
   web tools (see `tools/blocked-domains.txt`). For those, ask them to copy the ad text and
   paste it. Save it as `ads/<company>-<job-title>.md`.
2. **List what the ad asks for.** Show the essential requirements as a short list, marking which
   ones their CV already covers. For each gap, ask whether they have that experience. Never
   assume.
3. **Tailored CV.** Copy `my-cv.md` to `letters/cv-<company>.md`. Reorder bullets and skills so
   the ones the ad cares about come first, and adjust the summary. Use their real experience
   and the ad's wording where the two genuinely match. Do not add anything they have not told
   you.
4. **Cover letter.** Write `letters/<company>.txt`: three or four short paragraphs, under 300
   words. Cover why this company, the two or three strongest matches with a fact or number
   each, and a plain close. Start with "Dear Hiring Manager," unless the ad names someone.
5. **Check both:**
   - `python tools/copy_check.py letters/cv-<company>.md letters/<company>.txt`
   - `python tools/criteria_check.py ads/<file>.md letters/cv-<company>.md letters/<company>.txt`

   Fix what they flag: dashes, overused words, a requirement with no answer, a sentence that
   points at a gap.
6. **Show the full text of both** and wait for their changes or OK. Explain anything the
   checks flagged that you left as is.
7. **Build the files:**
   - `python tools/build_cv.py "output/<Name> CV - <Company>.docx" letters/cv-<company>.md`
   - `python tools/build_letter.py "output/<Name> Cover Letter - <Company>.docx" letters/<company>.txt`

   If the CV runs over the page limit, cut the weakest bullets with them and rebuild.
8. **After they apply**, add a row to `applications.md`: today's date, company, role, where
   they applied, contact if any, then the response, outcome and files columns. Leave the
   response and outcome blank. Add a line to "Applications in progress" in `PLAYBOOK.md` for
   anything the table can't hold, such as a named contact or something they promised to send.
   If they changed your wording in a way that says something about how they write, add it to
   "Voice and writing rules".

They submit the application themselves. If they want help with the form and have the Claude
in Chrome extension, you can fill it in. Stop before Submit.
