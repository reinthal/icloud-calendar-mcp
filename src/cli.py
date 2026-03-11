#!/usr/bin/env python3
"""iCloud Calendar CLI - Command-line interface for iCloud calendar management."""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from .tools import (
    list_calendars,
    list_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    update_calendar_metadata,
)

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="icloud-cal")
def cli():
    """iCloud Calendar CLI - Manage your iCloud calendars from the command line."""
    pass


@cli.command("list-calendars")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_list_calendars(output_json: bool):
    """List all available iCloud calendars."""
    try:
        calendars = list_calendars()

        if output_json:
            console.print(JSON(json.dumps(calendars, indent=2)))
        else:
            table = Table(title="iCloud Calendars", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Timezone", style="yellow")
            table.add_column("Components", style="green")

            for cal in calendars:
                table.add_row(
                    cal["name"],
                    cal.get("description", "")[:50] + ("..." if len(cal.get("description", "")) > 50 else ""),
                    cal.get("timezone", ""),
                    ", ".join(cal.get("supported_components", []))
                )

            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("list-events")
@click.option("--calendar", "-c", help="Calendar name (without [iCloud] prefix)")
@click.option("--start", "-s", help="Start date (ISO 8601 format)")
@click.option("--end", "-e", help="End date (ISO 8601 format)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_list_events(calendar: Optional[str], start: Optional[str], end: Optional[str], output_json: bool):
    """List calendar events."""
    try:
        events = list_events(calendar_name=calendar, start=start, end=end)

        if output_json:
            console.print(JSON(json.dumps(events, indent=2)))
        else:
            if not events:
                console.print("[yellow]No events found[/yellow]")
                return

            table = Table(title=f"Events ({len(events)} found)", show_header=True)
            table.add_column("Summary", style="cyan", width=30)
            table.add_column("Start", style="green")
            table.add_column("End", style="green")
            table.add_column("Location", style="yellow", width=20)
            table.add_column("Calendar", style="magenta")

            for event in events:
                # Parse and format dates
                start_dt = event.get("start", "")
                end_dt = event.get("end", "")

                table.add_row(
                    event.get("summary", "")[:30],
                    start_dt[:19] if start_dt else "",
                    end_dt[:19] if end_dt else "",
                    event.get("location", "")[:20],
                    event.get("calendar", "")
                )

            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("get-event")
@click.argument("uid")
@click.option("--calendar", "-c", help="Calendar name (without [iCloud] prefix)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_get_event(uid: str, calendar: Optional[str], output_json: bool):
    """Get a specific event by UID."""
    try:
        event = get_event(uid=uid, calendar_name=calendar)

        if output_json:
            console.print(JSON(json.dumps(event, indent=2)))
        else:
            console.print(f"[cyan]Summary:[/cyan] {event.get('summary', '')}")
            console.print(f"[green]Start:[/green] {event.get('start', '')}")
            console.print(f"[green]End:[/green] {event.get('end', '')}")
            console.print(f"[yellow]Location:[/yellow] {event.get('location', '')}")
            console.print(f"[white]Description:[/white] {event.get('description', '')}")
            console.print(f"[magenta]Calendar:[/magenta] {event.get('calendar', '')}")
            console.print(f"[dim]UID:[/dim] {event.get('uid', '')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("create-event")
@click.argument("summary")
@click.option("--start", "-s", required=True, help="Start datetime (ISO 8601)")
@click.option("--end", "-e", required=True, help="End datetime (ISO 8601)")
@click.option("--calendar", "-c", default="Alex Plugg", help="Calendar name (without [iCloud] prefix)")
@click.option("--description", "-d", default="", help="Event description")
@click.option("--location", "-l", default="", help="Event location")
@click.option("--rrule", help="Recurrence rule (e.g., FREQ=WEEKLY;BYDAY=MO,WE,FR)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_create_event(summary: str, start: str, end: str, calendar: str, description: str, location: str, rrule: Optional[str], output_json: bool):
    """Create a new calendar event."""
    try:
        event = create_event(
            summary=summary,
            start=start,
            end=end,
            calendar_name=calendar,
            description=description,
            location=location,
            rrule=rrule
        )

        if output_json:
            console.print(JSON(json.dumps(event, indent=2)))
        else:
            console.print(f"[green]✓[/green] Event created successfully!")
            console.print(f"[cyan]Summary:[/cyan] {event.get('summary', '')}")
            console.print(f"[dim]UID:[/dim] {event.get('uid', '')}")
            console.print(f"[magenta]Calendar:[/magenta] {event.get('calendar', '')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("update-event")
@click.argument("uid")
@click.option("--summary", help="New summary")
@click.option("--start", help="New start datetime (ISO 8601)")
@click.option("--end", help="New end datetime (ISO 8601)")
@click.option("--description", help="New description")
@click.option("--location", help="New location")
@click.option("--calendar", "-c", default="Alex Plugg", help="Calendar name (without [iCloud] prefix)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_update_event(uid: str, summary: Optional[str], start: Optional[str], end: Optional[str],
                     description: Optional[str], location: Optional[str], calendar: str, output_json: bool):
    """Update an existing event."""
    try:
        event = update_event(
            uid=uid,
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            calendar_name=calendar
        )

        if output_json:
            console.print(JSON(json.dumps(event, indent=2)))
        else:
            console.print(f"[green]✓[/green] Event updated successfully!")
            console.print(f"[cyan]Summary:[/cyan] {event.get('summary', '')}")
            console.print(f"[dim]UID:[/dim] {event.get('uid', '')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("delete-event")
@click.argument("uid")
@click.option("--calendar", "-c", default="Alex Plugg", help="Calendar name (without [iCloud] prefix)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_delete_event(uid: str, calendar: str, yes: bool, output_json: bool):
    """Delete an event."""
    try:
        if not yes and not output_json:
            if not click.confirm(f"Delete event {uid}?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        result = delete_event(uid=uid, calendar_name=calendar)

        if output_json:
            console.print(JSON(json.dumps(result, indent=2)))
        else:
            console.print(f"[green]✓[/green] Event deleted successfully!")
            console.print(f"[dim]Summary:[/dim] {result.get('summary', '')}")
            console.print(f"[dim]UID:[/dim] {result.get('uid', '')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


@cli.command("update-calendar")
@click.argument("calendar")
@click.option("--description", "-d", help="New calendar description")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cmd_update_calendar(calendar: str, description: Optional[str], output_json: bool):
    """Update calendar metadata."""
    try:
        result = update_calendar_metadata(calendar_name=calendar, description=description)

        if output_json:
            console.print(JSON(json.dumps(result, indent=2)))
        else:
            console.print(f"[green]✓[/green] Calendar updated successfully!")
            console.print(f"[cyan]Name:[/cyan] {result.get('name', '')}")
            console.print(f"[white]Description:[/white] {result.get('description', '')}")
            console.print(f"[yellow]Timezone:[/yellow] {result.get('timezone', '')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
