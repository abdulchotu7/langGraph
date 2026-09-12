---
name: commit
description: Create a git checkpoint commit in this repo. Use when the user asks to commit, save, or checkpoint their work.
---

# Commit

1. Run `git status --short` and `git diff --stat` to see what's changed.
2. Stage everything in scope: `git add -A` (or specific paths if the user named them).
3. Commit locally with a short imperative message, e.g. `weather agent: add currency tool`.
4. Report the commit hash and what went in.
5. NEVER push — pushing needs explicit user approval.
