# Firmware compatibility

The first question on any Flipper tool issue is *which firmware are you on*. This page
answers it in advance: what FlipperKit actually requires of the firmware, which of the
four common firmwares provide it, and — the part most compatibility tables leave out —
what has and has not been tested.

**Short answer:** FlipperKit uses three CLI commands and five file extensions. All four
firmwares below implement all three commands identically, so FlipperKit is expected to
work on any of them. None of them has a recorded end-to-end run against hardware —
[see the tested-status table](#tested-status--read-this-before-quoting-the-table-above).

---

## The four firmwares

Verified against the GitHub API on **4 October 2026**.

| Firmware | Repository | Latest release | Status |
|---|---|---|---|
| **Official** | [flipperdevices/flipperzero-firmware](https://github.com/flipperdevices/flipperzero-firmware) | `1.4.3` (Dec 2025) | Actively developed |
| **Unleashed** | [DarkFlippers/unleashed-firmware](https://github.com/DarkFlippers/unleashed-firmware) | `unlshd-093` (Sep 2026) | Actively developed |
| **Momentum** | [Next-Flip/Momentum-Firmware](https://github.com/Next-Flip/Momentum-Firmware) | `mntm-012` (Dec 2025) | Actively developed |
| **Xtreme** | [Flipper-XFW/Xtreme-Firmware](https://github.com/Flipper-XFW/Xtreme-Firmware) | `XFW-0053` (Feb 2024) | **Archived.** Repository read-only since Nov 2024; Momentum is its successor |

Xtreme is listed because a lot of devices are still running it and its users still file
issues. It is not listed as a supported target — it receives no fixes from anyone, so
any defect found only there is a defect you keep.

## What FlipperKit requires

Three commands and nothing else. FlipperKit never flashes, never writes to the device,
and never calls an application CLI — so the enormous feature differences between these
firmwares are almost entirely outside its surface.

| Requirement | Used by | Official | Unleashed | Momentum | Xtreme |
|---|---|---|---|---|---|
| `device_info` | `flipperkit info` | ✅ | ✅ | ✅ | ✅ |
| `storage list <path>` | `backup`, `flipperkit ls` | ✅ | ✅ | ✅ | ✅ |
| `storage read <path>` | `backup` | ✅ | ✅ | ✅ | ✅ |
| CLI prompt `>: ` | response framing | ✅ | ✅ | ✅ | ✅ |
| SD root at `/ext` | `backup --root` default | ✅ | ✅ | ✅ | ✅ |

Checked by reading
[`applications/services/storage/storage_cli.c`](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/applications/services/storage/storage_cli.c)
on the `dev` branch of each repository on 4 October 2026. All four register the same
`list`, `read`, `read_chunks`, `write`, `stat`, `info`, `md5` and `tree` subcommands.
Official and Unleashed are byte-identical in that file; Momentum and Xtreme differ only
in unrelated parts.

That is the whole reason a single tool covers all four: every fork inherits the
`storage` service from upstream and none of them has had a reason to change its wire
format.

### The one place the wire format bites

All four print a file entry as:

```c
printf("\t[F] %s %lub\r\n", name, (uint32_t)(fileinfo.size));
```

— a leading tab, and a size with a **`b` suffix**: `\t[F] demo.nfc 1024b`.

FlipperKit's parser currently expects a bare integer there, so it keeps the suffix on the
filename and reports every size as `0`. This affects **all four firmwares equally** — it
is a FlipperKit bug, not a compatibility difference. Tracked as
[#11](https://github.com/juandresrodca/FlipperKit/issues/11). Until it is fixed, prefer
copying the SD card from a card reader over `flipperkit backup`.

## SD card layout

The artifact directories FlipperKit cares about are upstream's and are the same
everywhere:

| Path | Holds | Official | Unleashed | Momentum | Xtreme |
|---|---|---|---|---|---|
| `/ext/nfc` | `.nfc` | ✅ | ✅ | ✅ | ✅ |
| `/ext/subghz` | `.sub` | ✅ | ✅ | ✅ | ✅ |
| `/ext/lfrfid` | `.rfid` | ✅ | ✅ | ✅ | ✅ |
| `/ext/infrared` | `.ir` | ✅ | ✅ | ✅ | ✅ |
| `/ext/ibutton` | `.ibtn` | ✅ | ✅ | ✅ | ✅ |

The forks add directories rather than move these: extra applications under
`/ext/apps`, their own per-app state under `/ext/apps_data`, their own settings files,
and in Unleashed's and Momentum's case considerably more Sub-GHz and NFC assets. Those
cost backup time and bytes; they do not change where an artifact lives.

`backup` walks whatever is under `--root` (default `/ext`), so a fork's extra
directories are mirrored too. Narrow it when you only want captures:

```bash
flipperkit backup --port COM3 --root /ext/nfc --dest ./backups
flipperkit backup --port COM3 --root /ext/subghz --dest ./backups
```

## File formats

Every artifact is a small UTF-8 text file with a `Filetype:` header, a `Version:`
header, `#` comment lines and `Key: value` pairs. FlipperKit parses the pairs
generically and keeps anything it does not recognise in an extras dictionary, so a
fork's additional fields survive a round trip rather than breaking the parse.

| Format | Fork differences that reach FlipperKit |
|---|---|
| `.nfc` | Unleashed and Momentum ship extra parsers and card types, which add `Key: value` pairs. Collected as extras. |
| `.sub` | Unleashed and Momentum support protocols and frequencies the official firmware refuses, so `Frequency:` may be outside the official region range. Recorded as read — FlipperKit does not validate frequencies, and deliberately: what is legal to transmit is a matter for your jurisdiction, not for a parser. |
| `.rfid` | No known divergence. |
| `.ir` | No known divergence. |
| `.ibtn` | Parsed only partially today — see [#2](https://github.com/juandresrodca/FlipperKit/issues/2) and [#6](https://github.com/juandresrodca/FlipperKit/issues/6). Not firmware-dependent. |
| `.u2f` | Not parsed; indexed with a null subtype. [#6](https://github.com/juandresrodca/FlipperKit/issues/6). Not firmware-dependent. |

`storage read` streams the body as text, which is correct for these artifacts and wrong
for anything genuinely binary. Binary-safe transfer via `storage read_chunks` is
[#3](https://github.com/juandresrodca/FlipperKit/issues/3).

## Tested status — read this before quoting the table above

| Firmware | Hardware-tested | Source-verified | Last checked |
|---|---|---|---|
| Official | ❌ **no recorded end-to-end run** | ✅ | 4 October 2026 |
| Unleashed | ❌ **no recorded end-to-end run** | ✅ | 4 October 2026 |
| Momentum | ❌ **no recorded end-to-end run** | ✅ | 4 October 2026 |
| Xtreme | ❌ **no recorded end-to-end run**, and the firmware is archived | ✅ | 4 October 2026 |

*Source-verified* means the CLI commands, their output format and the SD paths were read
out of that firmware's own source on the date shown. *Hardware-tested* means someone
plugged in a Flipper running it and `backup` completed end to end.

So every ✅ in the tables above is source-verified, and not one of them is
hardware-tested. That is a strong prediction — the forks share the file, byte for byte in
two cases — but a prediction is not a test, and marking it as one would be the single
most useless thing this page could do.

There is also positive evidence that the serial path has not been run against a device
on *any* firmware: bug [#11](https://github.com/juandresrodca/FlipperKit/issues/11) makes
every backed-up file land with its size welded onto the filename, which nobody could
run once and fail to notice. The parsing and reporting half of FlipperKit is covered by
tests and works on files copied from an SD card by hand; the `backup` command over
serial is the untested half.

**Whatever firmware you are on, you are the first.** Please run:

```bash
flipperkit devices
flipperkit info --port <your port>
flipperkit backup --port <your port> --root /ext/nfc --dest ./test-backup
```

…and open an issue with the firmware name and version from `flipperkit info`, whether
each command worked, and the first few lines of `flipperkit ls /ext` if the listing looks
wrong. A transcript of raw `storage list` output is even better, because it can become a
regression test and then nobody needs the hardware again. That is enough to flip a ❌ to
a ✅, and it is the most useful contribution this repository can receive right now.

## Related

- [docs/serial-ports.md](serial-ports.md) — what the device enumerates as, and the
  per-OS port rules. Those are firmware-independent: the USB descriptors come from the
  shared CDC configuration.
- [docs/recipes.md](recipes.md) — worked examples.
