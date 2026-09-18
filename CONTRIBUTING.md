# Contributing to FlipperKit

Three of the open issues are labelled *good first issue* and one of them
([#4](https://github.com/juandresrodca/FlipperKit/issues/4)) is an outright
request for help — which was a bit rich with no file telling anyone how to
build, test or submit anything. This is that file.

The single most useful thing to know before you start: **you do not need a
Flipper Zero to contribute to most of this repository.** The hardware boundary
is one module. Everything else runs against files on disk.

## Setting up

Python 3.9 or newer.

```bash
git clone https://github.com/juandresrodca/FlipperKit
cd FlipperKit
python -m venv .venv
. .venv/Scripts/activate      # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -e ".[dev]"
pytest
```

`pytest` should be green on a machine with no device attached. If it is not,
that is a bug worth an issue before you write anything else.

There is **no CI yet** — issue
[#5](https://github.com/juandresrodca/FlipperKit/issues/5) tracks adding it, and
deciding a `ruff` baseline is part of it. Until that lands, nothing runs the
suite for you when you open a pull request. Run it locally and say in the PR
that you did.

## The one architectural rule

```
src/flipperkit/
├── client.py    # the ONLY module that imports pyserial
├── backup.py    # sync logic over a small RemoteFS protocol → fake it in tests
├── parsers.py   # Flipper text format → FlipperRecord
├── db.py        # SQLite index, de-duplicated by SHA-256
├── report.py    # JSON / Markdown / HTML renderers
└── cli.py       # Typer wiring
```

**`client.py` is the only module allowed to `import serial`.** That is not a
style preference — it is what keeps the test suite runnable without hardware,
and it is the first thing a review will check. If your change needs device data
somewhere else, pass it in, or express the dependency as a protocol the way
`backup.py` does with `RemoteFS`.

`tests/test_client.py` exercises the client against a fake transport, so even
the serial wrapper is testable. Follow that pattern rather than adding a real
device to the loop.

## Adding a parser — worked example

This is the most common contribution, and issue
[#2](https://github.com/juandresrodca/FlipperKit/issues/2) is exactly it: `.u2f`
files are recognised as a category but nothing pulls fields out of them yet.

Four steps, in order:

**1. Map the extension** in `EXT_CATEGORY` at the top of `parsers.py`, if it is
not there already:

```python
EXT_CATEGORY = {
    ".nfc": "nfc",
    ...
    ".u2f": "u2f",
}
```

**2. Add a branch to `_extract()`** that pulls the fields that matter for that
category. The contract is `(subtype, identifier, frequency, extra)`: `subtype`
is the protocol or device type a human would name it by, `identifier` is the
thing you would search for, `frequency` is `None` for anything that is not
sub-GHz, and `extra` is category-specific metadata merged into the record.

```python
elif category == "u2f":
    subtype = first(pairs, "Filetype")     # check a real .u2f file for the
    identifier = first(pairs, "Key")       # actual key names before you commit
```

The key names above are a sketch of the shape, not a spec — open a `.u2f` file
the Flipper wrote and use what is actually in it.

Use the `first()` and `all_values()` helpers rather than re-walking the pairs —
`all_values()` exists because infrared files repeat `name:` once per stored
signal, and a new format that repeats keys should use it too.

**3. Add a fixture** to `tests/fixtures/` named `sample.<ext>`. Keep it minimal:
the header, and just enough keys for the assertions. Look at `sample.sub` for
the size to aim for.

**4. Add a test** to `tests/test_parsers.py` in the existing shape — assert the
category, the subtype, the identifier, and anything you put in `extra`:

```python
def test_parse_u2f():
    rec = parsers.parse_file(FIXTURES / "sample.u2f")
    assert rec.category == "u2f"
    assert rec.subtype == "<whatever your branch pulls out>"
```

Then update the **Supported artifacts** table in the README. A parser that works
but is not in that table does not exist as far as a reader is concerned.

## Fixtures must be synthetic

**Never commit an artifact captured from real hardware that is not yours, and
never commit a real credential of any kind** — no live NFC UID from a building
badge, no rolling code from a car, no card data. Every file in
`tests/fixtures/` is invented, and that is a hard rule, not a preference.

The UIDs and keys in the existing fixtures are made up. Yours should be too.
`00 00 00 00 00 12 34 56` is a perfectly good key for a test. If a fixture would
only be realistic with a real capture in it, the test is asking the wrong
question.

This matters more here than in most repositories: the repository's whole
legal and ethical position (see the README) is that FlipperKit
organises artifacts you lawfully captured from your own devices. A fixture
directory full of other people's badge IDs would make that a lie.

## Pull requests

- **One change per pull request.** A parser, a bug fix, a doc correction — not
  all three.
- **Branch from `master`.** That is the default branch here; `main` does not
  exist.
- **Say what you ran.** `pytest` output, and whether you tested against a real
  Flipper or only against fixtures. Both are fine; the reviewer needs to know
  which.
- **Describe hardware-dependent changes carefully.** Anything touching
  `client.py`, serial timeouts or the `storage read` chunking
  ([#3](https://github.com/juandresrodca/FlipperKit/issues/3)) cannot be fully
  verified without a device, so the PR description carries more weight than
  usual. Say which firmware version you tested on.
- **Keep the CLI surface stable.** `flipperkit backup|parse|index|report` and
  their flags are documented in the README and people have them in scripts.
  Adding a flag is easy; renaming one needs a reason.
- Match the surrounding style: type hints, a docstring on public functions,
  British or American spelling as the file already uses it. There is no
  formatter configured yet — do not reformat files you are not otherwise
  changing, as it buries the actual diff.

## Reporting a bug

Open an [issue](https://github.com/juandresrodca/FlipperKit/issues) with:

- the command you ran and the full output,
- your OS and Python version (`python --version`),
- for a parsing bug, a **synthetic** file that reproduces it — redact or invent
  the identifiers,
- for a device bug, your Flipper's firmware version and the port
  (`flipperkit devices`).

Port detection is the usual suspect on a device bug. `is_flipper_port()` matches
the STM32 VID/PID `0483:5740` first and falls back to the description string, so
a device that is not detected is worth reporting with the full `flipperkit
devices` output — that is the data
[#1](https://github.com/juandresrodca/FlipperKit/issues/1) needs.

## Security

Do not open a public issue for a security problem. Report it privately through
[Security → Report a vulnerability](https://github.com/juandresrodca/FlipperKit/security/advisories/new),
or email **juandresrodca@gmail.com** with `FlipperKit security` in the subject.

## Code of conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
