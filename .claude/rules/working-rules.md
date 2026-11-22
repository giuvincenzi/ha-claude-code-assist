# Working rules

How Claude works with the owner on this project. Loaded in every session.

- English only in the project: code, identifiers, comments, documentation, rules, commit
  messages.
- Ask before changing anything: describe what changes and why, wait for an explicit OK. The OK
  covers that plan only; a change of scope is asked again.
- Never commit, push or merge without the owner's explicit consent, every time; changes reach
  `main` only through a pull request (`git-workflow.md`). The repository is public: analysis,
  notes and measurements stay out of it.
- Think, don't just execute: check what the owner asks against the project and say so, with the
  reason, when something looks wrong or there is a better way. The owner decides.
- Professional solutions only: no workarounds or shortcuts that only make a request or a test
  pass. Fix bugs at the root cause and explain the cause first.
- Do not guess: check the source or the documentation (Claude Code, Home Assistant, libraries)
  before relying on a behaviour, and say what was verified and what was not.
- Follow how Home Assistant apps are normally made before inventing a structure of our own.
- Never print a secret (token, password) and never write private data or references to other
  projects of the owner in the repository.
- Project knowledge goes in these rules, the code or the documentation, not in Claude's personal
  memory.
