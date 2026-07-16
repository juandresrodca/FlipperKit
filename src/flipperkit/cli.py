"""FlipperKit command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, db, parsers, report
from .backup import sync

app = typer.Typer(
    add_completion=False,
    help="A companion CLI toolkit for the Flipper Zero: backup, parse, index and report.",
)
console = Console()


def _load_client(port: str, baudrate: int):
    """Import and open a serial client lazily so non-device commands need no hardware."""
    from .client import FlipperClient, FlipperError

    try:
        return FlipperClient(port, baudrate=baudrate).open()
    except FlipperError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the FlipperKit version."""
    console.print(f"FlipperKit {__version__}")


@app.command()
def devices() -> None:
    """List serial ports so you can find your Flipper's COM port."""
    from .client import FlipperError, available_ports

    try:
        ports = available_ports()
    except FlipperError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    if not ports:
        console.print("[yellow]No serial ports found.[/yellow] Is the Flipper plugged in?")
        return
    table = Table(title="Serial ports")
    table.add_column("Device", style="cyan")
    table.add_column("Description")
    for device, description in ports:
        table.add_row(device, description)
    console.print(table)


@app.command()
def info(
    port: str = typer.Option(..., "--port", "-p", help="Serial port, e.g. COM3 or /dev/ttyACM0."),
    baudrate: int = typer.Option(115200, "--baudrate", "-b"),
) -> None:
    """Show device information from a connected Flipper."""
    client = _load_client(port, baudrate)
    try:
        data = client.device_info()
    finally:
        client.close()
    if not data:
        console.print("[yellow]No device info returned.[/yellow]")
        return
    table = Table(title="Flipper device info")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    console.print(table)


@app.command()
def backup(
    dest: Path = typer.Argument(..., help="Local folder to mirror the SD card into."),
    port: str = typer.Option(..., "--port", "-p", help="Serial port, e.g. COM3 or /dev/ttyACM0."),
    baudrate: int = typer.Option(115200, "--baudrate", "-b"),
    root: str = typer.Option("/ext", "--root", help="Remote path to mirror."),
    force: bool = typer.Option(False, "--force", help="Re-download files even if size matches."),
) -> None:
    """Back up the Flipper SD card to a local folder."""
    client = _load_client(port, baudrate)

    def progress(path: str, action: str) -> None:
        colour = "green" if action == "downloaded" else "dim"
        console.print(f"[{colour}]{action:>10}[/] {path}")

    try:
        result = sync(client, dest, root=root, force=force, on_file=progress)
    finally:
        client.close()

    s = result.summary
    console.print(
        f"\n[bold]Done.[/bold] {s['downloaded']} downloaded, "
        f"{s['skipped']} skipped, {s['errors']} errors, "
        f"{s['bytes_written']} bytes."
    )
    for path, err in result.errors:
        console.print(f"[red]error[/red] {path}: {err}")


@app.command()
def parse(
    path: Path = typer.Argument(..., help="A Flipper file or a folder to scan."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Parse Flipper artifacts and print a summary."""
    records = parsers.parse_path(path)
    if as_json:
        console.print_json(report.render_json(records))
        return
    if not records:
        console.print("[yellow]No recognized Flipper files found.[/yellow]")
        return
    table = Table(title=f"{len(records)} artifact(s)")
    table.add_column("Category", style="cyan")
    table.add_column("Subtype")
    table.add_column("Identifier", style="green")
    table.add_column("Frequency", justify="right")
    table.add_column("File")
    for r in records:
        freq = f"{r.frequency / 1_000_000:.5f} MHz" if r.frequency else ""
        table.add_row(r.category, r.subtype or "", r.identifier or "", freq, r.filename)
    console.print(table)


@app.command()
def index(
    path: Path = typer.Argument(..., help="A Flipper file or folder to index."),
    database: Path = typer.Option(Path("flipperkit.db"), "--db", help="SQLite index path."),
) -> None:
    """Parse artifacts and store them in the SQLite index."""
    records = parsers.parse_path(path)
    conn = db.connect(database)
    try:
        counts = db.index_records(conn, records)
        totals = db.stats(conn)
    finally:
        conn.close()
    console.print(
        f"Indexed [green]{counts['inserted']}[/green] new, "
        f"updated [cyan]{counts['updated']}[/cyan]. "
        f"Index now holds {totals['total']} artifact(s)."
    )


@app.command()
def report_cmd(
    database: Path = typer.Option(Path("flipperkit.db"), "--db", help="SQLite index path."),
    fmt: str = typer.Option("html", "--format", "-f", help="html | md | json."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write to a file instead of stdout."),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category."),
    search: Optional[str] = typer.Option(None, "--search", help="Filter by text."),
) -> None:
    """Generate a report from the SQLite index."""
    conn = db.connect(database)
    try:
        records = db.load_records(conn, category=category, search=search)
    finally:
        conn.close()

    try:
        rendered = report.render(records, fmt)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    if out:
        out.write_text(rendered, encoding="utf-8")
        console.print(f"Wrote {len(records)} record(s) to [cyan]{out}[/cyan].")
    else:
        print(rendered)


# `report` is a reserved-feeling name; expose the command as `report` in the CLI.
app.command(name="report")(report_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
