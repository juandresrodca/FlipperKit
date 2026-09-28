## What this changes

<!-- One or two sentences. One change per pull request — a parser, a bug fix or a doc
     correction, not all three. -->

Closes #

## What you ran

<!-- Paste the `pytest` output, or say which parts you could not run and why. There is no
     CI yet (#5), so this is the only signal a reviewer gets. -->

```
```

- [ ] `pytest` is green locally
- [ ] Tested against a real Flipper Zero — firmware version: <!-- or: fixtures only -->

## Checklist

- [ ] Branched from `master` (`main` does not exist here)
- [ ] `client.py` is still the only module that imports `serial`
- [ ] Any new fixture in `tests/fixtures/` is **synthetic** — no real UID, key, rolling code or card data
- [ ] A new parser is listed in the README's **Supported artifacts** table
- [ ] Anything a user would notice is in `CHANGELOG.md` under *Unreleased*
- [ ] No unrelated reformatting — there is no formatter configured, and it buries the diff

## Anything the reviewer should know

<!-- Hardware-dependent changes carry more weight here, because they cannot be fully
     verified without a device. Say what you could and could not check. -->
