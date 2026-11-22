# Git workflow

How every change is made in git and reaches `main`. Loaded in every session.

- At the start of every session a `SessionStart` hook (`.claude/settings.json`) fast-forwards
  `main` to `origin/main` only when it is safe (on `main`, no local changes, no merge commit);
  otherwise it prints why, and Claude tells the owner before starting. The hook stays POSIX shell:
  Claude Code runs it with `sh`.
- Every change, however small (code, docs, rules, workflows), gets its own worktree from
  `origin/main`, made with `git fetch origin` and
  `git worktree add .worktrees/<branch> -b <branch> origin/main`. Work and test there: the `make`
  commands work from any worktree. `.worktrees/` is ignored by git, and the Supervisor skips
  folders starting with a dot, so the test environment never sees a worktree's copy of the app.
- The test environment runs the checkout `make dev-up` was started from: to try a branch end to
  end, start it from that worktree, with a copy of `.env` (ignored by git, so a new worktree has
  none).
- Then push the branch, open a pull request to `main` and stop. Claude never merges on its own:
  only after the owner approves that pull request, with the checks green. Then remove the worktree
  and delete the local branch (GitHub deletes the remote one on merge).
- `main` is protected by the ruleset "Protect main" (Settings > Rules): changes only through pull
  requests, merged by squash or rebase (linear history), with `unit_test` and `build_test` passed
  on a branch up to date with `main`. Renaming those jobs of `test.yml` needs the ruleset changed
  in the same moment, or no pull request can be merged.
- The release pull request (`release/X.Y.Z`) is opened only by `create_release_pr`, never by hand
  (`build-and-release.md`).
