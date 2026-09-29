# Recipes

Copy-paste workflows for the things people actually do with a Flipper's SD card:
keep it backed up, find out what is on it, and hand somebody else a report. Each
recipe below was run against `tests/fixtures/` before being written down.

## Contents

| Recipe | Use it when |
|---|---|
| [Try the whole pipeline with no device](#try-the-whole-pipeline-with-no-device) | You want to see what the tool does before plugging anything in. |
| [The weekly backup](#the-weekly-backup) | You want a dated mirror of the card and an index that grows with it. |
| [What is new since last time](#what-is-new-since-last-time) | You backed up again and want the diff, not the whole list. |
| [Query the index directly](#query-the-index-directly) | The `report` filters are not the question you are asking. |
| [Hand a report to somebody else](#hand-a-report-to-somebody-else) | A colleague, a client, or a ticket needs the contents of the card. |
| [Pipe it into something else](#pipe-it-into-something-else) | You want the data in `jq`, a spreadsheet or another tool. |
| [Run it on a schedule](#run-it-on-a-schedule) | You would rather not remember to do this. |

---

## Try the whole pipeline with no device

Everything except `devices`, `info` and `backup` works on any folder of Flipper
files, so the bundled fixtures are a complete demo:

```bash
flipperkit index tests/fixtures --db demo.db
flipperkit parse tests/fixtures
flipperkit report --db demo.db -f html -o demo.html
```

```
Indexed 4 new, updated 0. Index now holds 4 artifact(s).
```

Four artifacts, one per supported category. That is the shape of every recipe
below — `index` to load, `parse` to look, `report` to share.

## The weekly backup

The point of dating the destination folder is that `backup` mirrors, and a mirror
forgets. A capture you deleted from the card on Tuesday is gone from a mirror taken
on Wednesday. Dated folders keep the history; the index keeps the memory.

**Windows (PowerShell):**

```powershell
$date = Get-Date -Format 'yyyy-MM-dd'
flipperkit backup "$HOME\flipper\$date" --port COM3
flipperkit index  "$HOME\flipper\$date" --db "$HOME\flipper\flipperkit.db"
flipperkit report --db "$HOME\flipper\flipperkit.db" -f html -o "$HOME\flipper\report.html"
```

**macOS / Linux:**

```bash
date=$(date +%F)
flipperkit backup  ~/flipper/"$date" --port /dev/ttyACM0
flipperkit index   ~/flipper/"$date" --db ~/flipper/flipperkit.db
flipperkit report  --db ~/flipper/flipperkit.db -f html -o ~/flipper/report.html
```

Three things make this safe to run repeatedly:

- `backup` skips a file whose size already matches, so the second run over an
  unchanged card transfers almost nothing. `--force` overrides that.
- `index` deduplicates on SHA-256 of the file content, so re-indexing last week's
  folder alongside this week's does not create duplicate rows — it refreshes
  `last_seen` on the ones that are still there.
- One database across every dated folder is the point. It is the only thing that
  knows a capture existed in August and does not any more.

Mirror one subtree rather than the whole card with `--root`:

```bash
flipperkit backup ~/flipper/nfc-only --port COM3 --root /ext/nfc
```

> **On backing up a device you did not set up yourself:** `sync()` builds local paths
> from the names the device reports and does not yet contain them to the destination
> folder ([#7](https://github.com/juandresrodca/FlipperKit/issues/7)). Mirror your own
> Flipper into a folder you own and this never arises; do not point `backup` at
> somebody else's device and a shared drive until that is closed.

## What is new since last time

`index` records `first_seen` when it meets an artifact and `last_seen` every time it
sees it again. Two dates per row is enough to answer both of the questions worth
asking:

```bash
flipperkit index ~/flipper/2026-09-27 --db ~/flipper/flipperkit.db
```

```
Indexed 3 new, updated 41. Index now holds 44 artifact(s).
```

`3 new` is the answer most weeks. When you want to know *which* three:

```sql
-- captured since a date
SELECT category, subtype, identifier, filename, first_seen
FROM records
WHERE first_seen >= '2026-09-20'
ORDER BY first_seen DESC;
```

And the mirror image — captures the index knows about that were not on the card the
last time you backed it up:

```sql
-- in the index, no longer on the card
SELECT category, filename, identifier, last_seen
FROM records
WHERE last_seen < (SELECT MAX(last_seen) FROM records)
ORDER BY last_seen;
```

## Query the index directly

`report --category` and `report --search` cover the common filters. Anything else is
a SQL question, and the schema is small enough to hold in your head — one table:

| Column | Notes |
|---|---|
| `sha256` | Primary key. Content hash, which is what makes re-indexing idempotent. |
| `path`, `filename` | Where it was when last seen. |
| `category` | `nfc`, `subghz`, `rfid`, `infrared`, `ibutton`. |
| `filetype` | The `Filetype:` header line from the artifact. |
| `subtype` | Protocol or key type, e.g. `Mifare Classic`, `Princeton`, `EM4100`. |
| `frequency` | Hertz, integer, Sub-GHz only. |
| `identifier` | UID / key / data, as printed on the card. |
| `size` | Bytes. |
| `metadata` | Every key/value pair from the file, as JSON. |
| `first_seen`, `last_seen` | UTC ISO-8601. |

```bash
sqlite3 ~/flipper/flipperkit.db
```

**Which frequencies do I actually capture on?**

```sql
SELECT frequency / 1000000.0 AS mhz, COUNT(*) AS n
FROM records
WHERE category = 'subghz' AND frequency IS NOT NULL
GROUP BY frequency
ORDER BY n DESC;
```

**Have I captured the same thing twice under two names?**

```sql
SELECT identifier, category, COUNT(*) AS copies,
       GROUP_CONCAT(filename, ', ') AS files
FROM records
WHERE identifier IS NOT NULL AND identifier <> ''
GROUP BY identifier, category
HAVING COUNT(*) > 1
ORDER BY copies DESC;
```

Identical files cannot show up here — those share a SHA-256 and are one row. This
finds the *same credential* saved twice with different bytes around it, which is the
duplicate that actually wastes your time.

**What did the parser fail to label?**

```sql
SELECT category, filename, path
FROM records
WHERE subtype IS NULL OR identifier IS NULL
ORDER BY category, filename;
```

Rows here are gaps in the parser, not bad captures — the raw key/value pairs are
still in `metadata`, so nothing is lost. `.ir` files show up because infrared has no
single identifier to extract; `.u2f` shows up because `_extract()` has no branch for
it yet ([#6](https://github.com/juandresrodca/FlipperKit/issues/6)).

**Anything in `metadata`, without leaving SQL:**

```sql
SELECT filename,
       json_extract(metadata, '$.Protocol') AS protocol,
       json_extract(metadata, '$.Preset')   AS preset
FROM records
WHERE category = 'subghz';
```

**What is eating the card?**

```sql
SELECT category, COUNT(*) AS n, SUM(size) AS bytes
FROM records
GROUP BY category
ORDER BY bytes DESC;
```

## Hand a report to somebody else

```bash
# self-contained HTML — opens anywhere, no FlipperKit needed at the other end
flipperkit report --db flipperkit.db -f html -o card-contents.html

# markdown, for a ticket, a pull request or a wiki
flipperkit report --db flipperkit.db -f md -o card-contents.md

# one category, one question
flipperkit report --db flipperkit.db -f md --category subghz
flipperkit report --db flipperkit.db -f md --search EM4100
```

The markdown comes out with the summary first, which is usually the only part read:

```markdown
# FlipperKit Report

- **Artifacts:** 4
- **Total size:** 726 bytes
- **By category:** infrared (1), nfc (1), rfid (1), subghz (1)

| Category | Subtype | Identifier | Frequency | File |
| --- | --- | --- | --- | --- |
| nfc | Mifare Classic | `04 A2 26 B1 5C 3D 80` | | sample.nfc |
| subghz | Princeton | `00 00 00 00 00 12 34 56` | 433.92000 MHz | sample.sub |
```

`--category` and `--search` filter the rows *and* the summary, so a filtered report
is internally consistent rather than a full header over a partial table.

> A report contains every UID, key and identifier on the card in plain text. That is
> the point of it, and it is also why it is not a thing to paste into an issue, a
> public gist or a chat with people who were not in the room. The *Legal & ethical
> use* section of the [README](../README.md) is the short version.

## Pipe it into something else

Both `parse` and `report` emit JSON, and they are not the same JSON. `parse --json`
is the artifacts as read from disk. `report -f json` is the index, with a summary
block on top:

```bash
# straight from the files, no database
flipperkit parse ~/flipper/2026-09-27 --json | jq '.records[] | select(.category=="nfc") | .identifier'

# from the index, with the summary
flipperkit report --db flipperkit.db -f json | jq '.summary'
```

```json
{
  "total": 4,
  "total_bytes": 726,
  "by_category": { "infrared": 1, "nfc": 1, "rfid": 1, "subghz": 1 },
  "frequencies": [433920000]
}
```

To a spreadsheet, via the index rather than the JSON — `report` has no CSV format and
SQLite already does this:

```bash
sqlite3 -header -csv flipperkit.db \
  "SELECT category, subtype, identifier, frequency, filename, first_seen FROM records;" \
  > card-contents.csv
```

## Run it on a schedule

Backup needs the Flipper plugged in, so schedule it for a time it usually is, and let
it fail harmlessly when it is not — `flipperkit backup` exits non-zero if the port
cannot be opened.

**Windows — Task Scheduler**, weekly, from a saved `backup.ps1`:

```powershell
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
             -Argument "-NoProfile -File $HOME\flipper\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9pm
Register-ScheduledTask -TaskName 'FlipperKit backup' -Action $action -Trigger $trigger
```

**macOS / Linux — cron**, with the venv's binary by absolute path, because cron has
almost no `PATH`:

```cron
0 21 * * 0  ~/flipper/.venv/bin/flipperkit backup ~/flipper/$(date +\%F) --port /dev/ttyACM0 >> ~/flipper/backup.log 2>&1
```

Escape the `%` in a crontab, or cron truncates the line at it.

On Linux, add yourself to the group that owns the port first, or the scheduled run
fails on permissions where your interactive shell does not —
[`serial-ports.md`](serial-ports.md) has the udev rule and the ModemManager clash.
