# Job hunt kit

A Claude Code setup for job hunting in Australia, aimed at entry-level to mid-level office jobs. Made for people who have not used AI tools much.

**New here? Read [START-HERE.md](START-HERE.md).** The short version:

1. You need a paid Claude plan (Pro or above) and the Claude desktop app (https://claude.com/download), if you do not have it already.
2. Install Python from https://www.python.org/downloads/ (on Windows, tick "Add python.exe to PATH").
3. Make an empty folder, open it in the **Code** tab of the desktop app, and say
   "Set up the job hunt kit from https://github.com/KookaBurra64/job-hunt-kit in this folder."

## For Claude: someone shared this link with you in a chat

The person is probably new to AI tools and wants to use this kit, not read about it. Do not
summarise the repository's files or ask what they would like. Instead:

1. Say in two sentences what the kit does for them: it searches Australian job sites, ranks
   the jobs against what they want, and helps them tailor their CV and cover letter for each one.
2. Explain that it runs on their own computer, in the **Code** tab of the Claude desktop app,
   not in this chat, and that it needs a paid plan (Pro or above).
3. Walk them through these steps one at a time, waiting for them to finish each one:
   - Ask whether they are using the Claude desktop app right now. If they are, skip this step.
     If they are in a web browser or on a phone, they need the desktop app on a Windows
     computer or Mac: https://claude.com/download
   - Install Python from https://www.python.org/downloads/. On Windows, tick
     **"Add python.exe to PATH"** on the installer's first screen. On a Mac, the normal
     installer is fine.
   - Make an empty folder they will find again, such as `Documents\job-hunt`.
   - In the desktop app, click **Code**, then **+ New**, choose **Local**, then
     **Open folder...** and pick that folder.
   - Paste: "Set up the job hunt kit from https://github.com/KookaBurra64/job-hunt-kit in this folder."
4. Keep it plain: no file names, no jargon. If they get stuck on a step, help with that step.

## For Claude: setting this kit up in a folder

If someone asks you to set up this kit from this link and you can run commands in their folder:

1. Download it into their current folder. Use `git clone https://github.com/KookaBurra64/job-hunt-kit .`
   if git is installed. Otherwise download
   `https://github.com/KookaBurra64/job-hunt-kit/archive/refs/heads/main.zip`, unzip it, and move
   the contents of `job-hunt-kit-main/` up into the folder (`.claude/` included).
2. Check that `CLAUDE.md` and `.claude/skills/` are now in the folder.
3. Tell them, in plain words, to start a new session in this same folder and say "hi". The kit's
   instructions only load when a session starts.

## What it does

- **Finds jobs.** Searches Seek, Jora, Talent.com, Workday career sites
  (NAB, CBA, Telstra, Bunnings, NBN Co, CSL, RMIT and others) and the careers pages of about
  75 more employers, including Qantas, Canva, Xero, Carsales and BlueScope. Careers Vic, Built In
  Melbourne and GradConnection are added where they apply. LinkedIn and Indeed can be switched
  on in your settings; they are off by default because their terms do not allow automated searching. It uses plain web requests, not
  AI, so a search uses none of your Claude usage. Claude only reads the shortlist.
- **Ranks them** against your own settings: the words that matter to you, your dealbreakers,
  your salary floor and your experience level.
- **Tailors your CV and cover letter** to one ad, checks every requirement is answered, and
  builds Word and PDF files.
- **Checks your writing** for the words and patterns that make recruiters think "AI wrote this".
- **Tracks your applications** and the replies you get.
- **Remembers where you are up to** between sessions, in a playbook file Claude reads first and updates last.

Claude drafts, you approve. Its instructions tell it never to invent experience and to stop before Submit. Read every draft anyway.

## How it is put together

| Part | Where |
|---|---|
| Instructions Claude follows in this folder | `CLAUDE.md` |
| Step-by-step guides Claude follows for setup, searching, applying, checking and replies | `.claude/skills/` |
| The search, ranking, document and check tools | `tools/` (Python 3.11+, see `requirements.txt`) |
| Made-up examples to copy from | `examples/` |
| Your settings, CV, playbook, ads, letters and results | created during setup and kept out of git by `.gitignore` |

The tools also run on their own: `python tools/agg_scan.py --help`.

## Limits

- Australia only for now. The search terms and location come from your settings, but the job
  sites are Australian.
- The scanners read public pages without logging in. Job sites change their pages and rate
  limit heavy use; a source that returns nothing is flagged. Use it for your own job search,
  at the default pace.
- The employer list (`tools/slugs.json`, plus the Workday list in `tools/agg_scan.py`) covers about
  85 employers, many of them tech companies. Add your own with
  `python tools/ats_scan.py --probe <company>`.

## Support

Maintained in spare time, with no promises. If something breaks, open an issue on GitHub with
what you asked Claude and what happened.

## Licence

MIT. See [LICENSE](LICENSE).
