"""FlipperKit command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer.core import TyperGroup

from . import __version__, db, parsers, report
from .backup import sync

console = Console()


class BannerGroup(TyperGroup):
    """Top-level group that prints the ASCII banner above `--help`.

    Only the root group uses this class, so subcommand help (e.g.
    `flipperkit info --help`) stays clean and banner-free.
    """

    def format_help(self, ctx, formatter) -> None:
        from .banner import render_banner

        render_banner(console)
        super().format_help(ctx, formatter)


app = typer.Typer(
    cls=BannerGroup,
    add_completion=False,
    help="A companion CLI toolkit for the Flipper Zero: backup, parse, index and report.",
)

# A concrete, copy-pasteable example for each command, shown when a command is
# invoked incorrectly (instead of the bare "Try '... --help'" hint).
COMMAND_EXAMPLES = {
    "version": "flipperkit version",
    "devices": "flipperkit devices",
    "info": "flipperkit info --port COM3",
    "backup": "flipperkit backup ./backups --port COM3 --root /ext/nfc",
    "parse": "flipperkit parse ./backups",
    "index": "flipperkit index ./backups --db flipperkit.db",
    "report": "flipperkit report --db flipperkit.db --format html --out report.html",
    "update": "flipperkit update",
}


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
    table.add_column("Device")
    table.add_column("Description")
    table.add_column("")
    flipper_ports = []
    for device, description, is_flipper in ports:
        if is_flipper:
            flipper_ports.append(device)
            table.add_row(
                f"[bold green]{device}[/bold green]",
                f"[bold green]{description}[/bold green]",
                "[bold green]<- Flipper[/bold green]",
            )
        else:
            table.add_row(f"[cyan]{device}[/cyan]", description, "")
    console.print(table)

    if len(flipper_ports) == 1:
        console.print(f"\nFlipper detected on [bold green]{flipper_ports[0]}[/bold green] - "
                      f"use it as [green]--port {flipper_ports[0]}[/green].")
    elif len(flipper_ports) > 1:
        console.print(f"\n[yellow]Multiple Flipper-like ports:[/yellow] {', '.join(flipper_ports)}. "
                      "Pass the right one with --port.")
    else:
        console.print("\n[dim]No Flipper detected. Plug it in, unlock it, and close qFlipper.[/dim]")


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
def update(
    check_only: bool = typer.Option(False, "--check", help="Only check for updates; don't apply."),
    force: bool = typer.Option(False, "--force", help="Update even with uncommitted local changes."),
) -> None:
    """Check the git repo for a newer version and update in place."""
    import subprocess
    import sys

    from . import updater

    root = updater.repo_root()
    run = updater.git_runner(root)

    if not updater.is_git_repo(run):
        console.print(
            "[yellow]FlipperKit was not installed from a git clone,[/yellow] so it can't "
            "self-update. Reinstall from source: [green]pip install --upgrade "
            "git+https://github.com/juandresrodca/FlipperKit[/green]"
        )
        raise typer.Exit(code=1)

    remote = updater.remote_url(run) or "origin"
    branch = updater.current_branch(run) or "main"
    console.print(f"Checking [cyan]{remote}[/cyan] (origin/{branch}) for updates ...")
    status = updater.check(run)

    if not status.fetched:
        console.print(f"[red]Could not reach the remote:[/red] {status.fetch_error}")
        console.print("[yellow]Check your network/credentials and try again.[/yellow] "
                      "(Not reporting 'up to date' from stale local data.)")
        raise typer.Exit(code=1)

    if status.behind == 0:
        console.print(f"[green]Already up to date[/green] ({__version__}, {status.local}, "
                      f"branch {status.branch}).")
        return

    console.print(f"Update available: [bold]{status.behind}[/bold] new commit(s) on "
                  f"origin/{status.branch}.")
    if check_only:
        console.print("Run [green]flipperkit update[/green] to apply.")
        return

    if status.dirty and not force:
        console.print("[yellow]You have uncommitted local changes.[/yellow] Commit or stash "
                      "them, or re-run with [green]flipperkit update --force[/green].")
        raise typer.Exit(code=1)

    ok, message = updater.pull(run)
    if not ok:
        console.print(f"[red]Update failed:[/red] {message}")
        raise typer.Exit(code=1)

    new_sha = updater.short_sha(run)
    console.print(f"[green]Updated[/green] {status.local} -> {new_sha}.")

    # If dependencies changed, sync them (editable install picks up code automatically).
    _, changed = run("diff", "--name-only", f"{status.local}", "HEAD")
    if "pyproject.toml" in changed:
        console.print("Dependencies changed - syncing with pip ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(root), "-q"])

    console.print("Restart flipperkit to use the new version.")


@app.command("report")
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


def _show_usage_error(exc) -> None:
    """Render a usage error with a concrete example instead of a bare help hint."""
    ctx = getattr(exc, "ctx", None)
    if ctx is not None:
        console.print(ctx.get_usage(), style="dim")
    console.print(
        Panel(exc.format_message(), title="Error", title_align="left",
              border_style="red", padding=(0, 1))
    )

    command = getattr(ctx, "command", None) if ctx else None
    example = COMMAND_EXAMPLES.get(getattr(command, "name", None))
    if example:
        console.print(
            Panel(f"[green]{example}[/green]", title="Example", title_align="left",
                  border_style="green", padding=(0, 1))
        )
    else:
        # Group-level error (e.g. unknown command): point at the command list.
        console.print("Try [green]flipperkit --help[/green] to see all commands.")


def main() -> None:
    """Entry point. Intercepts usage errors to show a real example."""
    import sys

    import click
    from typer.main import get_command

    command = get_command(app)
    try:
        code = command(standalone_mode=False)
    except click.UsageError as exc:
        _show_usage_error(exc)
        sys.exit(exc.exit_code or 2)
    except click.ClickException as exc:
        exc.show()
        sys.exit(exc.exit_code)
    except click.exceptions.Abort:
        console.print("[red]Aborted.[/red]")
        sys.exit(1)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
