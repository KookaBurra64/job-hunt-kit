---
name: check-my-writing
description: Check a CV, cover letter, LinkedIn post or message for AI-sounding words, dashes and filler before it is sent. Use when they type /check-my-writing or ask whether some text sounds like AI.
---

# Check my writing

1. If they pasted text, save it to `letters/check-<short-name>.txt`. If they named a file, use that.
2. Run `python tools/copy_check.py <file>`.
3. Explain each flag in plain words, with the line it is on. Example: "'leverage' is a word
   recruiters now read as AI. 'Use' says the same thing."
4. Offer a fixed version that changes only the flagged parts and keeps everything else as
   they wrote it. Show it, and save it only if they say yes.

If they want a fuller edit than that, and `.claude/skills/no-ai-slop/` exists, use the
no-ai-slop skill. If it is not there, offer to add it (setup step 6 has the steps).

A clean result means the common AI patterns are gone. It does not mean the writing is good.
If something reads as vague or puffed up, say so in one line.
