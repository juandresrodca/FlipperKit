# Security Policy

FlipperKit does not attack anything. It backs up an SD card, parses the text files the
Flipper already wrote, indexes them and renders a report. That sounds like a small
security surface, and mostly it is — but it is not zero, because **every byte this tool
handles comes from somewhere you do not control**: a device on a serial port, or a
folder of captured artefacts. This policy says where that matters and how to report it
when it goes wrong.

## Reporting a vulnerability

Email **juandresrodca@gmail.com** with `FlipperKit security` in the subject. That is the
channel that always works. If [private vulnerability
reporting](https://github.com/juandresrodca/FlipperKit/security/advisories/new) is
available to you on this repository, it is the better route — it keeps the report, the
fix and the advisory in one place.

**Please do not open a public issue** for something that lets an attacker write outside
a destination folder, execute code, or read a file the user did not point the tool at.
Everything else — a parser that mis-reads a `.sub` file, a crash, a wrong frequency —
is a normal [issue](https://github.com/juandresrodca/FlipperKit/issues), and public is
better for those.

Include the artefact file that triggers it if you can. **Synthetic fixtures only** —
the same rule [CONTRIBUTING.md](CONTRIBUTING.md) applies to tests applies here: do not
send a real capture from a real system.

| Stage | Target |
|---|---|
| Acknowledgement | 72 hours |
| Assessment | 7 days |
| Fix or documented caveat | 30 days |
| Credit | given unless you ask otherwise |

This is a personal project maintained outside working hours. There is no bug bounty;
there is a genuine commitment to answering you.

## Supported versions

Pre-1.0, and installed from a git clone rather than a package index. Only `main` gets
fixes — there is no backporting to a tagged version, and `flipperkit update` is a
`git pull --ff-only` onto whatever branch you checked out.

| Version | Supported |
|---|---|
| `main` | ✅ |
| `0.1.x` tags | ⚠️ update to `main` |

## Where the real surface is

In rough order of how much a bug there would cost you:

**1. The backup destination path.** `sync()` builds each local path from the names the
device reports over the serial CLI, and the walk in `_walk()` concatenates them without
checking that the result stays inside the destination folder. A device that reports a
name containing `..` — tampered firmware, or something that is not a Flipper at all
sitting on that port — could in principle place a file outside the folder you named.
Tracked in [#7](https://github.com/juandresrodca/FlipperKit/issues/7); treat a working
escape as a vulnerability report, not an issue comment.

**2. The parsers.** `parsers.py` reads attacker-influenced text: anyone can hand you a
`.nfc` or `.sub` file. It does no `eval`, no `pickle`, no dynamic import, and reads
whole files into memory — so the realistic failure is a crash or a pathological
allocation on a hostile file, not code execution. Both are worth reporting.

**3. The report output.** `render_html()` escapes every field it interpolates with
`html.escape`, including the filename. **`render_markdown()` does not** — a filename or
identifier containing `|`, backticks or raw HTML will break the table, and will inject
into the page if you render that Markdown to HTML somewhere that allows raw HTML.
Reports built from artefacts you did not capture yourself should be treated accordingly.

**4. `flipperkit update`.** It runs `git fetch` and `git pull --ff-only` against the
`origin` of your clone. It verifies nothing beyond fast-forwardability: no signature
check, no pinned commit. It is as trustworthy as the remote you cloned from and the
account that can push to it. It also does not reinstall dependencies, so a pull that
adds one leaves you running without it.

**5. What the index and the reports contain.** The SQLite database and every report
hold the identifiers, keys and protocols pulled out of your captures. `flipperkit.db`
and `report.html` are **credential material for whatever those captures came from** —
back them up and share them with that in mind. Nothing in FlipperKit encrypts them, and
nothing redacts them.

**6. The serial port.** `client.py` opens the port you name and writes CLI commands to
it. `is_flipper_port()` matches on USB VID/PID and description, which is a convenience
for `flipperkit devices`, not an authentication check — anything can claim to be a
Flipper. Do not point `--port` at a device you do not recognise.

## Out of scope

- **The Flipper Zero firmware itself.** Report those to
  [flipperdevices/flipperzero-firmware](https://github.com/flipperdevices/flipperzero-firmware).
- **What you do with a capture.** The legal and ethical boundary is in the README, and
  no policy here changes it: FlipperKit is for artefacts you lawfully captured from your
  own devices or from systems you are explicitly authorised to test.
- **A dependency CVE with no path through this code.** Say which call reaches it and it
  is in scope immediately; a raw scanner report without one is not.
- **Anything that needs the attacker to already be running code as you.** If they can
  write to your clone, `flipperkit update` is the least of it.

## Hardening a FlipperKit setup

- Back up into a **dedicated folder** you own, never a shared or synced one, and never
  a path whose parent you would mind being written to.
- Keep `flipperkit.db` and generated reports out of any repository. The
  [`.gitignore`](.gitignore) covers the obvious names; check before you commit anyway.
- Install into a virtual environment (`pip install -e ".[dev]"`), so a dependency change
  cannot reach the rest of your Python.
- Run `pytest` after `flipperkit update`. It is green with no device attached, which
  makes it a cheap check that the pull did not break the thing you are about to point at
  your hardware.
