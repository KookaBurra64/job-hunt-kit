# Start here

This kit turns Claude Code into a job search assistant. It searches Australian job sites
for you, ranks what it finds, and helps you tailor your CV and cover letter for each job.
You do not need to know how to code. You type requests in plain English.

Setup takes about 30 minutes the first time, including installing the app.

## What you need

- A Claude account on a paid plan (Pro, Max, Team or Enterprise). The free plan does not include Claude Code.
- A Windows computer or a Mac.
- Your current CV, ideally as a PDF. A Word file or pasted text also works.

## Step 1: Install the Claude desktop app

Download it from https://claude.com/download, install it and sign in. If you already use
Claude in the desktop app, skip this step.

## Step 2: Install Python

The job search tools are small programs written in Python, so your computer needs it.

1. Go to https://www.python.org/downloads/ and click the big download button.
2. Run the installer. **On Windows, tick "Add python.exe to PATH"** on the first screen,
   then click Install Now. On a Mac, click through the installer.
3. If the Claude app was open, close it and open it again so it finds Python.

If you skip this, Claude notices during setup and offers to install Python for you.

## Step 3: Get your own copy of this kit

The easiest way is to let Claude do it:

1. Make an empty folder somewhere you will find it again, like `Documents\job-hunt`.
2. Open that folder in the Code tab (see Step 4).
3. Paste this message and press Enter:

   > Download https://github.com/KookaBurra64/job-hunt-kit into this folder, including the hidden .claude folder. Then tell me to start a new session here.

Claude downloads the kit into the folder and asks you to start a new session in the same
folder, so it can read the kit's instructions. After that, go to Step 5.

To do it by hand instead, click the green **Code** button at the top of this page, then
**Download ZIP**, and unzip it into your folder.

If you use GitHub, click **Use this template** at the top of this page instead, and
**choose Private**. Your copy will hold your job search, and a public repository can be
read by anyone. The kit's `.gitignore` already keeps your CV, settings and applications off
GitHub, but Private is the safe default.

## Step 4: Open the folder in the Code tab

This kit runs in the **Code** tab of the desktop app, not in an ordinary chat. An ordinary
chat cannot run the job search on your computer.

1. Click **Code** at the top of the left-hand sidebar.
2. Start a new session (**+ New**).
3. Under the message box, choose **Local** as the environment, then choose **Open folder...**
   and pick the folder you unzipped.

Anthropic's own guide, with pictures: https://code.claude.com/docs/en/desktop-quickstart

## Step 5: Say hello

Type "hi" and press Enter. Claude sees you are new and starts the setup. It asks for your CV
first, suggests search settings from it, and then checks a few things with you, one question
at a time. Most answers are "yes" or a small change.

The search tools are small Python programs. If your computer does not have Python, Claude
offers to install it for you. You will need to close and reopen the app once afterwards.

**Claude asks before it runs anything on your computer.** A box appears with the command and
buttons to allow or decline it. Read what it says it is about to do, and allow it if that
matches. Setup takes about 20 minutes, most of it waiting for installs.

## Then, just talk to it

Tell Claude what you want in your own words. For example:

- "Find me some jobs."
- "Help me apply for this one", then paste the job ad.
- "Does this message to the recruiter sound OK?"
- "I heard back from Telstra, they want a phone interview on Tuesday."
- "Help me prepare for Tuesday's interview."

Each time you come back, Claude starts by telling you where you are up to. That might be a
letter you didn't finish, or a company you're waiting to hear from. It keeps notes in a file
called `PLAYBOOK.md`, so you don't have to explain things twice. You can read it and change
it too.

If you like shortcuts, these do the same as asking: `/find-jobs`, `/tailor-cv`,
`/check-my-writing`, `/log-reply` and `/setup`.

## Good to know

- **You stay in charge.** Claude drafts and you approve. It is set up to stop before Submit, so you send every application yourself.
- **It is told not to make things up.** If a job asks for something not on your CV, Claude
  should ask you rather than invent it. AI still gets things wrong, so read every draft before you send it.
- **Your files stay on your computer.** Your settings, CV, letters and applications are kept
  out of GitHub by `.gitignore`.
- **The job site search is a best effort.** It reads the same public pages your browser
  does, without logging in. Sites change, and some days one returns nothing. The search says
  so when that happens.
- **AI usage has limits.** The search runs without AI, so it is cheap. Long back-and-forth on
  one letter uses more. The kit uses the Sonnet model, which goes further on a Pro plan than
  the larger models. You can change the model in the box under the message area. If you hit a
  limit, wait for it to reset.

## Optional extras

During setup, Claude offers to add a free writing tool, no-ai-slop by Peter Yang
(https://github.com/petergyang/no-ai-slop). It edits your letters so they sound less like AI
while keeping your voice. Say yes or no; you can ask for it later too.

One more, if you want help with online application forms. It is someone else's free add-on.
Type `/plugin marketplace add neonwatty/job-apply-plugin`, then
`/plugin install job-apply@neonwatty-plugins`. It fills in LinkedIn Easy Apply, Greenhouse, Lever and Workday forms in your browser, and
  stops before Submit. It needs the Claude in Chrome extension.
