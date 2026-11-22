# HA Claude Code Assist

A Home Assistant app (`ha_claude_code_assist/`) that runs Claude Code with the owner's Claude
subscription as a personal assistant, with a chat panel in the Home Assistant sidebar, and the
integration that makes it an Assist conversation agent (`custom_components/`).

## Rule files

The rules live in `.claude/rules/`, one file per topic. Each opens with a short paragraph saying
what it covers, then its bullets:

- `working-rules.md`: how Claude works with the owner on this project
- `git-workflow.md`: how every change is made in git and reaches `main`
- `build-and-release.md`: how the app is built and how the app and the integration are released
- `architecture.md`: how the app and its core are organized
- `sessions.md`: how conversations map to Claude Code sessions and processes
- `data.md`: what the app keeps in `/data` and how it stays compatible
- `prompt.md`: the system prompt and the internal tools Claude uses
- `ui.md`: how the panel is built and must look
- `testing.md`: which tests exist and when they run
- `dev-environment.md`: the Makefile, the containers and the test Home Assistant
- `docs.md`: the README files, the user documentation and how every text the user reads is written

When a rule file is added, removed or renamed, update this list.

## When to write a rule

A rule is the exception, not the record of a change: most changes need none. Write one only
for what someone could break without knowing it and cannot see quickly in the code: a
constraint, a decision taken among options, a convention a reader would not guess, a trap of
a tool. Never for what a feature does (the user documentation), what a function does (its
comment), what a test already enforces, or history (the commit).

## How to write a rule

- One fact lives in one file only. Search `.claude/rules/` first.
- Code rules have `paths:` covering every place they can be broken.
- One fact per bullet, at most three lines; name the code or the check that carries it.
- English, the code as it is today, plain words; nothing private (names, local paths, hosts,
  tokens).
- A change that makes a rule untrue updates or deletes it in the same change.
