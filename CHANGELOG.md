# Changelog

All notable changes to FlipperKit are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version stays below `1.0.0`, a minor bump may change the CLI surface;
patch releases will not.

## [Unreleased]

### Fixed

- **A fresh install could not run any command.** `cli.py` imports `click` directly
  but `pyproject.toml` never declared it; Typer supplied it transitively until
  `0.26.0` dropped the dependency and vendored click privately, so every command
  raised `ModuleNotFoundError: No module named 'click'` on a clean environment.
  `click>=8.0` is now a declared dependency, and a subprocess test exercises the
  entry point so it cannot regress unseen
  ([#8](https://github.com/juandresrodca/FlipperKit/issues/8)).

- **`CONTRIBUTING.md` told contributors no CI would run their changes.** It had said
  so since before `ci.yml` landed on 29 September and was never updated, so a
  first-time contributor had no reason to expect the suite to run at all. It now
  describes the matrix that does run, and names the two caveats nothing else stated:
  3.10 and 3.12 go untested, and no linter runs — the half of
  [#5](https://github.com/juandresrodca/FlipperKit/issues/5) still open.

- **`CODE_OF_CONDUCT.md` named four escalation tiers with nobody to report to.**
  Both *Enforcement Responsibilities* and *Enforcement* were missing from the
  shipped Contributor Covenant 2.1 text, leaving consequences stated and no address
  to invoke them at, while the README and `CONTRIBUTING.md` both route participants
  there. Both sections are restored, using the address `SECURITY.md` already
  publishes and stating the conduct route as distinct from the security one.

- **CI's Python 3.9 job on Linux has failed since late October.** `ubuntu-latest`
  moved to Ubuntu 26.04, and `setup-python` has no 3.9 build for it: 3.9 is end of
  life, and its last build (3.9.25) ships for Ubuntu 22.04 and 24.04 only, so the
  job stopped before installing anything. It now runs on `ubuntu-24.04`, while 3.11
  and 3.13 stay on `ubuntu-latest`. The same change moves `actions/checkout` and
  `actions/setup-python` to v7.

### Added

- Continuous integration: the test suite runs on every push and pull request across
  nine jobs — Python 3.9, 3.11 and 3.13 on each of Linux, macOS and Windows —
  installing the package the way a user would, so a missing dependency fails in CI
  rather than on someone's machine. 3.10 and 3.12 are not in the matrix, although
  `requires-python` admits them.
- A subprocess test that runs `python -m flipperkit version` and `--help`, turning a
  broken entry point into a failing test instead of a broken install.
- Dependabot watches the manifest itself: `pip` weekly for the dependencies
  `pyproject.toml` declares, with minor and patch bumps grouped into one pull
  request, and `github-actions` monthly for the versions `ci.yml` pins. Until now
  nothing in the repository read the manifest between pushes — CI resolves it fresh
  on every run, so an advisory against a declared dependency stayed invisible
  unless a job happened to fail.

- `CONTRIBUTING.md`: repository layout, the hardware boundary, a worked example
  of adding a parser end to end, and the rule that every fixture must be
  synthetic.
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).
- `SECURITY.md`: how to report privately, what is supported, and the six places
  the tool's surface actually is — the unchecked backup destination path (#7),
  the parsers, the unescaped Markdown renderer, `flipperkit update`, the key
  material sitting in the index and the reports, and the serial port itself.
- `docs/serial-ports.md`: what the Flipper enumerates as on USB, the port naming
  and permission model on Windows, macOS and Linux (including the udev rule that
  stops ModemManager probing the port), and the three gaps in `is_flipper_port()`
  that auto-detection has to close first (#1). Linked from the README usage
  section.
- `docs/recipes.md`: the commands assembled into workflows — a dated weekly backup
  that relies on size-skip and SHA-256 deduplication being idempotent, the SQL for
  *what is new since last time* and *what did the parser fail to label*, filtered
  reports, the two different JSON shapes `parse` and `report` emit, and scheduling
  on Task Scheduler and cron. Every recipe was run against `tests/fixtures/` before
  being written. Linked from the README usage section.
- `docs/compatibility.md`: what FlipperKit actually asks of the firmware — three CLI
  commands, five file extensions, and nothing that writes to the device — checked
  against the official, Unleashed, Momentum and Xtreme sources, so a *which firmware
  are you on* question can be answered before it is asked. Its tested-status table
  states plainly that none of the four has a recorded end-to-end run against
  hardware. Linked from the README usage section.
- Terminal screenshots in the README, rendered as SVG under `docs/screenshots/`
  so they stay legible on both GitHub themes and cost no raster bytes.
- `.gitattributes` declares the raster and video types binary. The file
  normalized everything to LF and named the four Flipper artifact extensions as
  text, but carried no binary block at all, so the first PNG or MP4 added beside
  the SVGs in `docs/screenshots/` would have relied on git sniffing a NUL byte in
  its first 8,000 bytes to escape end-of-line normalization. Nothing is corrupt
  today — the repository tracks no binary — which is why the declaration costs
  nothing to add now and is expensive to add after the fact.
- This changelog.

## [0.1.0] - 2026-07-17

First tagged release. The four commands the README describes all work against a
Flipper Zero over USB, and everything except `client.py` is exercised by
`pytest` with no device attached.

### Added

- `flipperkit backup` — mirror the SD card into a local directory, skipping
  files whose contents have not changed.
- `flipperkit parse` — read Flipper's key/value text format and print a table.
  `.nfc`, `.sub`, `.rfid`, `.ir` and `.ibtn` get category-specific fields
  extracted; `.u2f` is recognised as a category but not yet field-extracted
  (tracked in [#2](https://github.com/juandresrodca/FlipperKit/issues/2)).
- `flipperkit index` — index parsed artifacts into SQLite, deduplicating by
  SHA-256 so re-running a backup does not duplicate rows.
- `flipperkit report` — render the index as JSON, Markdown or a self-contained
  HTML report.
- `flipperkit devices` and `flipperkit info` — list candidate serial ports and
  query the attached device. Port detection matches the STM32 VID/PID
  `0483:5740` first and falls back to the port description, so `--port` is
  usually unnecessary.
- `flipperkit update` — check GitHub for newer commits and fast-forward a git
  clone, surfacing fetch failures rather than reporting a false "up to date".
- `flipperkit version` and an ASCII banner on `--help`.

[Unreleased]: https://github.com/juandresrodca/FlipperKit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/juandresrodca/FlipperKit/releases/tag/v0.1.0
