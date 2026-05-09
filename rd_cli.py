#!/usr/bin/env python3
"""CLI tool for Real-Debrid automation."""

import asyncio
import click
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import settings
from rd_api import RealDebridClient, RealDebridError
from download_manager import DownloadManager


console = Console()


@click.group()
@click.option("--token", envvar="RD_TOKEN", help="Real-Debrid API token")
@click.option("--token-file", envvar="RD_TOKEN_FILE", help="Path to file containing token")
@click.pass_context
def cli(ctx, token, token_file):
    """Real-Debrid Download Automation CLI"""
    if token_file:
        settings.rd_token_file = token_file
    if token:
        settings.rd_token = token

    try:
        settings.validate()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj["client"] = RealDebridClient(settings.get_token())


@cli.command()
@click.pass_context
def user(ctx):
    """Show current user info."""
    client = ctx.obj["client"]

    async def _run():
        try:
            info = await client.get_user()
            table = Table(title="Real-Debrid User")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            for key, val in info.items():
                table.add_row(str(key), str(val))
            console.print(table)
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.argument("link")
@click.option("--password", help="Password for protected links")
@click.pass_context
def check(ctx, link, password):
    """Check if a link is supported."""
    client = ctx.obj["client"]

    async def _run():
        try:
            result = await client.check_link(link)
            console.print(json.dumps(result, indent=2))
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.argument("link")
@click.option("--password", help="Password for protected links")
@click.option("--download/--no-download", default=True, help="Download the file after unrestriciting")
@click.option("--output-dir", default=".", help="Output directory for downloads")
@click.pass_context
def unrestrict(ctx, link, password, download, output_dir):
    """Unrestrict a link and optionally download."""
    client = ctx.obj["client"]

    async def _run():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Unrestriciting link...", total=None)

                result = await client.unrestrict_link(link, password)
                progress.update(task, description="[green]Link unrestricited![/green]")

            console.print(json.dumps(result, indent=2))

            if download:
                download_url = result.get("download")
                if download_url:
                    filename = result.get("filename", "unknown")
                    dm = DownloadManager(output_dir=output_dir)
                    download_id = await dm.download_file(download_url, filename)

                    # Wait and show progress
                    while True:
                        prog = dm.get_progress(download_id)
                        if prog and prog.status in ("completed", "failed", "cancelled"):
                            break
                        await asyncio.sleep(0.5)

                    if prog.status == "completed":
                        console.print(f"[green]Download completed:[/green] {output_dir}/{filename}")
                    else:
                        console.print(f"[red]Download failed:[/red] {prog.error}")
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.argument("magnet")
@click.pass_context
def magnet(ctx, magnet):
    """Add a magnet link."""
    client = ctx.obj["client"]

    async def _run():
        try:
            result = await client.add_magnet(magnet)
            console.print(json.dumps(result, indent=2))
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.option("--limit", default=10, help="Number of torrents to show")
@click.pass_context
def torrents(ctx, limit):
    """List your torrents."""
    client = ctx.obj["client"]

    async def _run():
        try:
            torrent_list = await client.list_torrents(limit)
            table = Table(title="Torrents")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Progress", style="yellow")
            table.add_column("Status", style="magenta")

            for t in torrent_list:
                table.add_row(
                    str(t.get("id", "")),
                    str(t.get("filename", "")),
                    str(t.get("progress", 0)) + "%",
                    str(t.get("status", "")),
                )
            console.print(table)
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.argument("torrent_id")
@click.pass_context
def torrent_info(ctx, torrent_id):
    """Show info for a specific torrent."""
    client = ctx.obj["client"]

    async def _run():
        try:
            info = await client.get_torrent_info(torrent_id)
            console.print(json.dumps(info, indent=2))
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.pass_context
def hosts(ctx):
    """List supported hosts."""
    client = ctx.obj["client"]

    async def _run():
        try:
            hosts = await client.get_hosts()
            console.print(", ".join(sorted(hosts)))
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


@cli.command()
@click.pass_context
def traffic(ctx):
    """Show traffic information."""
    client = ctx.obj["client"]

    async def _run():
        try:
            traffic_info = await client.get_traffic()
            table = Table(title="Traffic")
            table.add_column("Host", style="cyan")
            table.add_column("Used", style="green")

            for host, used in traffic_info.items():
                table.add_row(host, f"{used / (1024**3):.2f} GB")
            console.print(table)
        except RealDebridError as e:
            console.print(f"[red]Error:[/red] {e}")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
