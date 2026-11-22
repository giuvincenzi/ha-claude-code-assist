// The release's version and CHANGELOG sections (.claude/rules/build-and-release.md). Used by the create_release_pr
// workflow (the next version, the CHANGELOG section, the version in the files), the publish_release workflow (whether a
// push is a release, the release notes) and the test workflow (the two version files agree):
//
//   node scripts/release.mjs next              the next version, from the release tags vX.Y.Z and "## Unreleased"
//   node scripts/release.mjs move <version>    "## Unreleased"'s entries under "## <version>", printed too
//   node scripts/release.mjs notes <version>   the release notes of <version>: its CHANGELOG section
//   node scripts/release.mjs version           the version of the app and the integration (fails when they differ)
//   node scripts/release.mjs set <version>     writes <version> in both
//
// The next version is the latest tag vX.Y.Z plus a minor step (X.Y+1.0) when "## Unreleased" has entries under
// "### Added" or "### Changed", a patch step (X.Y.Z+1) when it has entries only under "### Fixed". The first release,
// with no tag yet, is 0.1.0.
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/** @typedef {'Added' | 'Changed' | 'Fixed'} Subsection */
/** @typedef {[number, number, number]} Version */

/** @type {string[]} */
const SUBSECTIONS = ['Added', 'Changed', 'Fixed'];
const FIRST_VERSION = '0.1.0';
// The app's changelog: Home Assistant shows it in the app's Changelog tab.
export const CHANGELOG = 'ha_claude_code_assist/CHANGELOG.md';
// The app's version (the Supervisor offers an update when it changes) and the integration's (the Marketplace and HACS
// read it): always the same, written only by a release.
export const APP_CONFIG = 'ha_claude_code_assist/config.yaml';
export const INTEGRATION_MANIFEST = 'custom_components/ha_claude_code_assist/manifest.json';

const VERSION_RE = /^\d+\.\d+\.\d+$/;
const CONFIG_VERSION_RE = /^version: "(\d+\.\d+\.\d+)"$/m;
const MANIFEST_VERSION_RE = /"version": "\d+\.\d+\.\d+"/;

/**
 * The lines of a "## <title>" section, without its heading; null when there is none.
 * @param {string} changelog
 * @param {string} title
 */
export function section(changelog, title) {
  const lines = changelog.split('\n');
  const start = lines.findIndex((line) => line.trim() === `## ${title}`);
  if (start < 0) return null;
  const end = lines.findIndex((line, index) => index > start && line.startsWith('## '));
  return lines.slice(start + 1, end < 0 ? lines.length : end);
}

/**
 * How many entries ("- " lines) each subsection has. Fails on an entry outside a known subsection.
 * @param {string[]} lines
 * @param {string} title
 */
export function countEntries(lines, title) {
  /** @type {Record<Subsection, number>} */
  const counts = { Added: 0, Changed: 0, Fixed: 0 };
  /** @type {Subsection | null} */
  let current = null;
  for (const line of lines) {
    const heading = /^### (.+)$/.exec(line);
    if (heading) {
      const name = (heading[1] ?? '').trim();
      if (!SUBSECTIONS.includes(name)) {
        throw new Error(`${CHANGELOG} "## ${title}": unknown subsection "### ${name}" (use Added, Changed or Fixed).`);
      }
      current = /** @type {Subsection} */ (name);
      continue;
    }
    if (line.startsWith('- ')) {
      if (!current) throw new Error(`${CHANGELOG} "## ${title}": an entry outside Added, Changed and Fixed: ${line}`);
      counts[current]++;
    }
  }
  return counts;
}

/**
 * The lines of "## Unreleased"; fails when it is missing or has no entries (nothing to release).
 * @param {string} changelog
 */
export function unreleased(changelog) {
  const lines = section(changelog, 'Unreleased');
  if (!lines) throw new Error(`${CHANGELOG} has no "## Unreleased" section.`);
  const counts = countEntries(lines, 'Unreleased');
  if (counts.Added + counts.Changed + counts.Fixed === 0) {
    throw new Error(`${CHANGELOG} "## Unreleased" has no entries: nothing to release.`);
  }
  return lines;
}

/**
 * The newest release among the tag names ("v1.2.3" -> [1, 2, 3]); null when there is none.
 * @param {string[]} tags
 * @returns {Version | null}
 */
export function latestVersion(tags) {
  const versions = tags.flatMap((tag) => {
    const match = /^v(\d+)\.(\d+)\.(\d+)$/.exec(tag);
    return match ? [/** @type {Version} */ ([Number(match[1]), Number(match[2]), Number(match[3])])] : [];
  });
  versions.sort((a, b) => b[0] - a[0] || b[1] - a[1] || b[2] - a[2]);
  return versions[0] ?? null;
}

/**
 * The version after the latest release for the entries of "## Unreleased".
 * @param {Version | null} latest
 * @param {string[]} entries
 */
export function nextVersion(latest, entries) {
  const counts = countEntries(entries, 'Unreleased');
  if (!latest) return FIRST_VERSION;
  const [major, minor, patch] = latest;
  return counts.Added + counts.Changed > 0 ? `${major}.${minor + 1}.0` : `${major}.${minor}.${patch + 1}`;
}

/**
 * The CHANGELOG with "## Unreleased"'s entries under "## <version>", and an empty "## Unreleased" above it.
 * @param {string} changelog
 * @param {string} version
 */
export function moveUnreleased(changelog, version) {
  const entries = unreleased(changelog).join('\n').trim();
  const lines = changelog.split('\n');
  const start = lines.findIndex((line) => line.trim() === '## Unreleased');
  const end = lines.findIndex((line, index) => index > start && line.startsWith('## '));
  const after = end < 0 ? [] : lines.slice(end);
  const text = [...lines.slice(0, start), '## Unreleased', '', `## ${version}`, '', entries, '', ...after].join('\n');
  return { changelog: `${text.trimEnd()}\n`, entries };
}

/**
 * The release notes of a version: its CHANGELOG section. Fails when it is missing or has no entries.
 * @param {string} changelog
 * @param {string} version
 */
export function releaseNotes(changelog, version) {
  const lines = section(changelog, version);
  if (!lines?.some((line) => line.startsWith('- ')))
    throw new Error(`${CHANGELOG} has no entries under "## ${version}".`);
  return lines.join('\n').trim();
}

/**
 * The version written in the app's config.yaml and in the integration's manifest.json. Fails when either is missing
 * or they differ: the app and the integration are released together.
 * @param {string} config
 * @param {string} manifest
 */
export function currentVersion(config, manifest) {
  const app = CONFIG_VERSION_RE.exec(config)?.[1];
  if (!app) throw new Error(`${APP_CONFIG} has no line version: "X.Y.Z".`);
  const integration = JSON.parse(manifest).version;
  if (typeof integration !== 'string' || !VERSION_RE.test(integration)) {
    throw new Error(`${INTEGRATION_MANIFEST} has no "version": "X.Y.Z".`);
  }
  if (app !== integration) {
    throw new Error(`${APP_CONFIG} says ${app} and ${INTEGRATION_MANIFEST} says ${integration}: they must be the same.`);
  }
  return app;
}

/**
 * config.yaml and manifest.json with <version> in place of the current one.
 * @param {string} config
 * @param {string} manifest
 * @param {string} version
 */
export function withVersion(config, manifest, version) {
  if (!VERSION_RE.test(version)) throw new Error(`Not a version X.Y.Z: ${version}`);
  currentVersion(config, manifest);
  // Only the value changes, so both files keep their own layout.
  return {
    config: config.replace(CONFIG_VERSION_RE, `version: "${version}"`),
    manifest: manifest.replace(MANIFEST_VERSION_RE, `"version": "${version}"`),
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [command, version] = process.argv.slice(2);
  const read = (/** @type {string} */ path) => readFileSync(path, 'utf8');
  if (command === 'next') {
    const tags = execFileSync('git', ['tag', '--list', 'v*'], { encoding: 'utf8' }).split('\n');
    console.log(nextVersion(latestVersion(tags), unreleased(read(CHANGELOG))));
  } else if (command === 'move' && version) {
    const moved = moveUnreleased(read(CHANGELOG), version);
    writeFileSync(CHANGELOG, moved.changelog);
    console.log(moved.entries);
  } else if (command === 'notes' && version) {
    console.log(releaseNotes(read(CHANGELOG), version));
  } else if (command === 'version') {
    console.log(currentVersion(read(APP_CONFIG), read(INTEGRATION_MANIFEST)));
  } else if (command === 'set' && version) {
    const files = withVersion(read(APP_CONFIG), read(INTEGRATION_MANIFEST), version);
    writeFileSync(APP_CONFIG, files.config);
    writeFileSync(INTEGRATION_MANIFEST, files.manifest);
  } else {
    throw new Error('Usage: node scripts/release.mjs next | move <version> | notes <version> | version | set <version>');
  }
}
