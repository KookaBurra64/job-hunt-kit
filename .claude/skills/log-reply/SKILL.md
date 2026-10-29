---
name: log-reply
description: Record an employer's reply (rejection, interview, offer, anything) in applications.md and update the summary line. Use when they type /log-reply or mention hearing back from an employer.
---

# Log a reply

1. Ask which company and what they said, if they have not told you. A pasted email is fine.
2. Summarise the reply in a few words, such as "phone screen invite for Tuesday" or "not progressing".
3. Choose an outcome if the reply settles one: `Rejected`, `Interview booked`, `Offer`, `Withdrawn`.
4. Run `python tools/log_response.py "<company>" "<summary>" ["<outcome>"]`.
   - "no row matches": the application was never logged. Add the row to `applications.md`
     first (ask when they applied), then run it again.
   - "matches more than one row": use more of the company name.
5. Update `PLAYBOOK.md`. For an interview, add the date, time and who they meet under
   "Open items and follow-ups". For a rejection, remove the application from "Applications
   in progress".
6. Tell them the updated "So far" line. If it is a rejection, keep it brief and kind. If it is
   an interview, offer to help them prepare: go through the ad in `ads/`, and draft a few
   likely questions with answers drawn from their CV.
