"""Render parsed Flipper records as JSON, Markdown or a standalone HTML page."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Dict, List

from .models import FlipperRecord


def summarize(records: List[FlipperRecord]) -> Dict[str, object]:
    """Aggregate counts used by every report format."""
    by_category: Dict[str, int] = {}
    frequencies = set()
    total_bytes = 0
    for r in records:
        by_category[r.category] = by_category.get(r.category, 0) + 1
        total_bytes += r.size
        if r.frequency:
            frequencies.add(r.frequency)
    return {
        "total": len(records),
        "total_bytes": total_bytes,
        "by_category": by_category,
        "frequencies": sorted(frequencies),
    }


def render_json(records: List[FlipperRecord]) -> str:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": summarize(records),
        "records": [r.as_dict() for r in records],
    }
    return json.dumps(payload, indent=2)


def render_markdown(records: List[FlipperRecord]) -> str:
    summary = summarize(records)
    lines: List[str] = ["# FlipperKit Report", ""]
    lines.append(f"- **Artifacts:** {summary['total']}")
    lines.append(f"- **Total size:** {summary['total_bytes']} bytes")
    cats = ", ".join(f"{k} ({v})" for k, v in summary["by_category"].items()) or "none"
    lines.append(f"- **By category:** {cats}")
    lines.append("")
    lines.append("| Category | Subtype | Identifier | Frequency | File |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in records:
        freq = f"{r.frequency / 1_000_000:.5f} MHz" if r.frequency else ""
        lines.append(
            f"| {r.category} | {r.subtype or ''} | `{r.identifier or ''}` | {freq} | {r.filename} |"
        )
    lines.append("")
    return "\n".join(lines)


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlipperKit Report</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
          margin: 0; background: #0d1117; color: #e6edf3; }}
  header {{ padding: 2rem 1.5rem 1rem; border-bottom: 1px solid #21262d; }}
  h1 {{ margin: 0; font-size: 1.4rem; color: #ff8c1a; }}
  .meta {{ color: #8b949e; font-size: .8rem; margin-top: .35rem; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: .75rem; padding: 1.25rem 1.5rem; }}
  .card {{ background: #161b22; border: 1px solid #21262d; border-radius: 8px;
           padding: .75rem 1rem; min-width: 120px; }}
  .card .n {{ font-size: 1.6rem; font-weight: 700; }}
  .card .l {{ color: #8b949e; font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }}
  .wrap {{ overflow-x: auto; padding: 0 1.5rem 2.5rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .85rem; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #21262d; white-space: nowrap; }}
  th {{ color: #8b949e; text-transform: uppercase; font-size: .7rem; letter-spacing: .04em; }}
  tr:hover td {{ background: #161b22; }}
  code {{ color: #7ee787; }}
  .tag {{ display: inline-block; padding: .1rem .5rem; border-radius: 999px;
          background: #1f2937; color: #58a6ff; font-size: .7rem; }}
  footer {{ padding: 1rem 1.5rem; color: #8b949e; font-size: .75rem; border-top: 1px solid #21262d; }}
</style>
</head>
<body>
<header>
  <h1>FlipperKit Report</h1>
  <div class="meta">Generated {generated_at} · {total} artifacts · {total_bytes} bytes</div>
</header>
<section class="cards">{cards}</section>
<div class="wrap">
<table>
  <thead><tr><th>Category</th><th>Subtype</th><th>Identifier</th><th>Frequency</th><th>Size</th><th>File</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>
<footer>Built with FlipperKit — authorized lab use only.</footer>
</body>
</html>
"""


def render_html(records: List[FlipperRecord]) -> str:
    summary = summarize(records)

    cards = [_card(str(summary["total"]), "artifacts")]
    for category, count in summary["by_category"].items():
        cards.append(_card(str(count), category))

    rows = []
    for r in records:
        freq = f"{r.frequency / 1_000_000:.5f} MHz" if r.frequency else ""
        rows.append(
            "<tr>"
            f"<td><span class='tag'>{html.escape(r.category)}</span></td>"
            f"<td>{html.escape(r.subtype or '')}</td>"
            f"<td><code>{html.escape(r.identifier or '')}</code></td>"
            f"<td>{html.escape(freq)}</td>"
            f"<td>{r.size}</td>"
            f"<td>{html.escape(r.filename)}</td>"
            "</tr>"
        )

    return _HTML_TEMPLATE.format(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        total=summary["total"],
        total_bytes=summary["total_bytes"],
        cards="".join(cards),
        rows="".join(rows),
    )


def _card(number: str, label: str) -> str:
    return f"<div class='card'><div class='n'>{html.escape(number)}</div><div class='l'>{html.escape(label)}</div></div>"


RENDERERS = {
    "json": render_json,
    "md": render_markdown,
    "markdown": render_markdown,
    "html": render_html,
}


def render(records: List[FlipperRecord], fmt: str) -> str:
    try:
        return RENDERERS[fmt](records)
    except KeyError as exc:
        raise ValueError(f"Unknown report format: {fmt!r}") from exc
