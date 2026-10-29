---
name: setup
description: First-time setup. Read their CV, suggest search settings from it, confirm the rest by asking, then write my-profile.toml, my-cv.md, applications.md and PLAYBOOK.md. Use when my-profile.toml does not exist, or they ask to set up or start again.
---

# Setup

Goal: by the end, `my-profile.toml`, `my-cv.md`, `applications.md` and `PLAYBOOK.md` exist,
and they know they can just tell you what they want. Takes about 10 minutes. Say so up front.

## 1. Check the computer is ready

Run `python --version`. It must be 3.11 or newer. Then `python -c "import docx, pypdf"`.

- **Python missing or too old: offer to install it for them.** Most people will not have it.
  - On Windows, run `winget install --id Python.Python.3.12 -e`.
  - On a Mac, run `brew install python@3.12` if `brew --version` works. Otherwise send them to
    python.org/downloads.
  - Before running anything, tell them a permission box will pop up and they should click Allow.
  - If the install command fails, walk them through python.org/downloads instead. On Windows,
    remind them to tick "Add python.exe to PATH" on the installer's first screen.
  - After any install, they need to close and reopen the app before Python is found. Say so,
    and tell them to just say "hi" again after they reopen it.
- Import fails: run `python -m pip install -r requirements.txt`. Before running it, explain that
  it adds the two small tools that make Word and PDF files, and that a permission box will
  pop up for it: click Allow.
- LibreOffice is optional: it makes the PDF copies and counts pages. Offer
  `winget install --id TheDocumentFoundation.LibreOffice -e` on Windows. Do not push it.
- On Windows, if `python` opens the Microsoft Store or says it is not found, try `py` instead,
  and use `py` for every command from then on.

## 2. Their CV first

Ask for their current CV. Easiest to hardest: drag a PDF into the chat (the + button next to
the message box also works), copy the CV file into this folder, or paste the text. For a
Word file in the folder, read it with `python -c "import docx,sys; print('\n'.join(p.text for p in docx.Document(sys.argv[1]).paragraphs))" FILE`. Then ask one
thing: is it up to date? If not, ask what has changed since.

Keep their CV and every file made from it out of the `examples` folder: that folder is
uploaded if they ever put their copy on GitHub. Their CV file can go in the main folder.

Turn it into `my-cv.md` in the same shape as `examples/example-cv.md`: `# Name`, a contact
line, then `##` sections and `-` bullets. Keep their words. Do not improve it or add claims yet.

## 3. Suggest settings from the CV

From the CV, work out:
- name, phone, email, LinkedIn and city (for the letter header and the search location)
- likely job titles, from their current and past roles
- skills and tools they use (for `good_words`)
- years of experience, from the dates

## 4. Confirm, one question at a time

Each question offers your CV-based guess as the default, so most answers are "yes" or a small
change. Fill in `examples/my-profile.example.toml` and save it as `my-profile.toml`. Keep the
comments in the file.

1. **What job do you want next?** Ask this outright, even if the CV makes it look obvious. A
   CV shows where they have been, not where they are heading, and career changers need
   different searches. Turn the answer into 4 to 8 `job_titles`, phrased the way people search
   on Seek, and fill `title_words` with the core nouns ("developer", "nurse", "analyst").
2. Where, and would you take remote work? Suggest the city on the CV. Fills `city`, `state` and `include_remote`.
3. Any level you are not after? Senior, manager, junior, intern. Fills `skip_title_words`.
4. "Your CV mentions X, Y and Z. Are those what you want to use most?" Add anything else that
   makes a job a great fit, such as an industry, hybrid work or a company size. Fills `good_words`
   (3 for very important, 1 for nice to have).
5. What rules a job out? Clearances, night shift, long commutes, contract only. Fills
   `dealbreakers` and `bad_words`.
6. Lowest salary you would take? Then confirm the years of experience you worked out. Fills
   `salary_floor` and `max_years_experience`.
7. Confirm the contact details you took from the CV. Tell them these stay on this computer only.
8. Only if the CV points to a recent graduate, offer `graduate_categories`.

## 5. Create the other files

- Copy `examples/applications.template.md` to `applications.md`.
- Copy `examples/PLAYBOOK.template.md` to `PLAYBOOK.md`. Fill in "Start here" and "What I'm
  looking for" from this conversation, including the reasons behind their answers. Add
  anything they said about how they want to sound to "Voice and writing rules".
- Run `python tools/build_cv.py "output/My CV.docx"` so they can see their CV in Word. Point
  them to the `output` folder.

## 6. Offer the writing tool

Ask once: "There's a free writing tool that edits your letters so they sound less like AI,
while keeping your own voice. Want me to add it?" Name it: no-ai-slop by Peter Yang, MIT licence.

On a yes, download these three files from that exact version (do not use `main`; the version
is fixed so a later change to someone else's repo can't change what runs here) into
`.claude/skills/no-ai-slop/`:

    https://raw.githubusercontent.com/petergyang/no-ai-slop/000650b156983f5159695b441477f4e63b25dc85/skills/no-ai-slop/SKILL.md
    https://raw.githubusercontent.com/petergyang/no-ai-slop/000650b156983f5159695b441477f4e63b25dc85/skills/no-ai-slop/eval.md
    https://raw.githubusercontent.com/petergyang/no-ai-slop/000650b156983f5159695b441477f4e63b25dc85/LICENSE

Use `python -c "import urllib.request,sys; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" URL FILE`
for each. Tell them it is ready from their next session. On a no, note it in `PLAYBOOK.md` and
do not ask again.

## 7. What next

Tell them, in two or three lines, that they can now just talk to you: "find me some jobs",
"help me apply for this one" with an ad pasted in, "does this sound OK?". Offer to run the
first job search now.
