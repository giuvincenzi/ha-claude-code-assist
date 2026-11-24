---
paths:
  - ".github/**"
  - "scripts/release*"
  - "ha_claude_code_assist/CHANGELOG.md"
  - "ha_claude_code_assist/config.yaml"
  - "ha_claude_code_assist/Dockerfile"
  - "custom_components/ha_claude_code_assist/manifest.json"
  - "custom_components/ha_claude_code_assist/__init__.py"
  - "ha_claude_code_assist/core/ha_cca/app.py"
---

# Build and release

How the app is built and how the app and the integration are released.

- The Supervisor builds the app on the user's machine from its `Dockerfile`; no image is
  published. Claude Code is Anthropic's ("All rights reserved"): an image with it inside would
  redistribute it. `build_app` builds the app on GitHub on each processor of `arch` in
  `config.yaml`, as the Supervisor would.
- Workflows (`.github/workflows/`): names lowercase with underscores, the workflow named after the
  phase, the job after the action. Each declares its own `permissions`; the default token stays
  read only (Settings > Actions > General).
- The repository is public: no secret anywhere in it (commits, pull requests, issues, workflow
  logs). Secrets go only in GitHub's encrypted secrets. Before merging a pull request from someone
  else, check what it changes in `scripts/`, `.github/workflows/` and the Makefile.
- Releases are deterministic: the version and the CHANGELOG's sections are never edited by hand.
- `ha_claude_code_assist/CHANGELOG.md` (the app's Changelog tab) starts with `## Unreleased`,
  split into `### Added`, `### Changed` and `### Fixed`. Every user-visible change adds its line
  there, in its own pull request.
- The version is in `config.yaml` (the Supervisor offers the app's update when it changes) and in
  the integration's `manifest.json`, always the same (`unit_test` checks). Only the release pull
  request changes it (`block_version_change`). At runtime the app reads its own from the
  Supervisor and the integration from its manifest: no other copy anywhere.

## Making a release

1. `create_release_pr`, only when the owner asks: Actions > `create_release_pr` > Run workflow on
   `main`. It stops when `## Unreleased` has no entries or a release pull request is open.
   Otherwise the next version is the latest tag plus a minor step with Added or Changed entries, a
   patch step with Fixed only (0.1.0 first). It moves the entries under `## X.Y.Z`, writes X.Y.Z
   in both files and opens `release/X.Y.Z`, "Release X.Y.Z" (`scripts/release.mjs`). It needs the
   setting "Allow GitHub Actions to create and approve pull requests" (Settings > Actions >
   General).
2. Its tests wait for a maintainer: the pull request was opened by `github-actions[bot]`, so
   GitHub holds its workflows until **Approve workflows to run**. Tests started another way do not
   count for the pull request.
3. `make app-smoke` passes on the release branch (the end-to-end tests run only locally,
   `testing.md`), the owner checks the pull request (version, CHANGELOG) and approves the merge.
4. `publish_release` starts with the merge: the version has no tag yet and the CHANGELOG has its
   section. It runs the tests and publishes the GitHub Release `vX.Y.Z` with that section as its
   notes; the Marketplace and HACS offer the integration's update from it. A failed job is retried
   with **Re-run failed jobs**.

When the owner asks Claude for the release pull request, Claude does steps 1 and 2 and stops
before the merge:

- `gh workflow run create_release_pr.yml --ref main`, then `gh run watch` on its run.
- It approves, as the owner, the run of `test.yml` with event `pull_request` on `release/X.Y.Z`
  in status `action_required`, only for that pull request and never for another:
  `gh run list --branch release/X.Y.Z --workflow test.yml --json databaseId,event,conclusion`,
  then `gh api -X POST repos/{owner}/{repo}/actions/runs/<id>/approve`.
- It waits for the checks and gives the link, the version and the entries. The merge waits for
  the owner's explicit OK.
