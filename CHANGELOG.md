# Changelog

All notable changes to FlipperKit are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version stays below `1.0.0`, a minor bump may change the CLI surface;
patch releases will not.

## [Unreleased]

Nothing in this section changes behaviour — everything released so far is in
`0.1.0`. The entries below are the project scaffolding added since the tag.

### Added

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
- Terminal screenshots in the README, rendered as SVG under `docs/screenshots/`
  so they stay legible on both GitHub themes and cost no raster bytes.
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
