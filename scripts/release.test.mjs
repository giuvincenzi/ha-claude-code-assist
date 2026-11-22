// Tests of scripts/release.mjs, run by `make test` (node --test).
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  currentVersion,
  latestVersion,
  moveUnreleased,
  nextVersion,
  releaseNotes,
  unreleased,
  withVersion,
} from './release.mjs';

const CHANGELOG = `# Changelog

## Unreleased

### Added

- Voice through Assist.

### Fixed

- The panel reconnects after a restart.

## 0.1.0

### Added

- First version.
`;

const CONFIG = `name: HA Claude Code Assist
version: "0.1.0"
slug: ha_claude_code_assist
`;

const MANIFEST = `{
  "domain": "ha_claude_code_assist",
  "after_dependencies": ["assist_pipeline", "hassio"],
  "version": "0.1.0"
}
`;

test('the first release is 0.1.0', () => {
  assert.equal(nextVersion(latestVersion([]), unreleased(CHANGELOG)), '0.1.0');
});

test('added or changed entries make a minor release, fixes only a patch', () => {
  const latest = latestVersion(['v0.1.0', 'v0.2.3', 'not-a-version', 'v0.10.0']);
  assert.deepEqual(latest, [0, 10, 0]);
  assert.equal(nextVersion(latest, ['### Changed', '- Something.']), '0.11.0');
  assert.equal(nextVersion(latest, ['### Fixed', '- Something.']), '0.10.1');
});

test('nothing to release without entries, and entries must be in a known subsection', () => {
  assert.throws(() => unreleased('# Changelog\n\n## Unreleased\n\n## 0.1.0\n\n### Added\n\n- x\n'), /no entries/);
  assert.throws(() => unreleased('# Changelog\n\n## Unreleased\n\n- loose\n'), /outside Added, Changed and Fixed/);
  assert.throws(() => unreleased('# Changelog\n\n## Unreleased\n\n### Removed\n\n- x\n'), /unknown subsection/);
});

test('the unreleased entries move under the new version, with an empty Unreleased above', () => {
  const { changelog, entries } = moveUnreleased(CHANGELOG, '0.2.0');
  assert.match(changelog, /^# Changelog\n\n## Unreleased\n\n## 0\.2\.0\n\n### Added\n\n- Voice through Assist\./);
  assert.match(changelog, /- The panel reconnects after a restart\.\n\n## 0\.1\.0\n/);
  assert.equal(entries.split('\n')[0], '### Added');
  assert.equal(releaseNotes(changelog, '0.2.0'), entries);
});

test('a version without a CHANGELOG section has no release notes', () => {
  assert.throws(() => releaseNotes(CHANGELOG, '0.3.0'), /no entries under "## 0\.3\.0"/);
});

test('the app and the integration have one version', () => {
  assert.equal(currentVersion(CONFIG, MANIFEST), '0.1.0');
  const other = MANIFEST.replace('"0.1.0"', '"0.2.0"');
  assert.throws(() => currentVersion(CONFIG, other), /must be the same/);
  assert.throws(() => currentVersion('name: x\n', MANIFEST), /no line version/);
});

test('a release writes its version in both files and changes nothing else', () => {
  const files = withVersion(CONFIG, MANIFEST, '0.2.0');
  assert.equal(files.config, CONFIG.replace('version: "0.1.0"', 'version: "0.2.0"'));
  assert.equal(files.manifest, MANIFEST.replace('"version": "0.1.0"', '"version": "0.2.0"'));
  assert.equal(currentVersion(files.config, files.manifest), '0.2.0');
  assert.throws(() => withVersion(CONFIG, MANIFEST, 'v0.2.0'), /Not a version/);
});
