import json
import os
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Optional

import caldav
import pytz
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from icalendar import Calendar, Event, vRecur

mcp = FastMCP(
    "iCloud Calendar",
    instructions="Manage iCloud calendar events via CalDAV. Supports listing, creating, updating, and deleting events.",
)

ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"
DEFAULT_CALENDAR = os.getenv("ICLOUD_CALENDAR", "Alex Plugg")


def _get_calendar_name(calendar: caldav.Calendar) -> str:
    props = calendar.get_properties([caldav.dav.DisplayName()])
    return props.get("{DAV:}displayname", "")


def _get_client() -> caldav.DAVClient:
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    if not username or not password:
        raise ValueError(
            "ICLOUD_USERNAME and ICLOUD_PASSWORD environment variables must be set"
        )
    return caldav.DAVClient(url=ICLOUD_CALDAV_URL, username=username, password=password)


def _find_calendar(principal: caldav.Principal, calendar_name: str) -> caldav.Calendar:
    all_cals = principal.calendars()
    for cal in all_cals:
        if _get_calendar_name(cal) == calendar_name:
            return cal
    available = [_get_calendar_name(cal) for cal in all_cals]
    raise ValueError(
        f"Calendar '{calendar_name}' not found. Available: {available}"
    )


def _get_user_timezone(ctx: Optional[Context] = None) -> pytz.tzinfo:
    """Get the user's timezone based on their public IP address from request context."""
    try:
        client_ip = None

        # Try to get client IP from request context
        if ctx and hasattr(ctx, 'request_context') and ctx.request_context:
            request = getattr(ctx.request_context, 'request', None)
            if request and hasattr(request, 'headers'):
                # Check common headers for client IP
                headers = request.headers
                client_ip = (
                    headers.get('X-Forwarded-For', '').split(',')[0].strip() or
                    headers.get('X-Real-IP') or
                    headers.get('CF-Connecting-IP') or  # Cloudflare
                    None
                )

        # If we have a client IP, use it to get timezone
        if client_ip:
            url = f"https://ipapi.co/{client_ip}/json/"
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
            tz_name = data.get("timezone", "UTC")
            return pytz.timezone(tz_name)
        else:
            # Fall back to server's own IP if no client IP available
            with urllib.request.urlopen("https://ipapi.co/json/") as resp:
                data = json.loads(resp.read())
            tz_name = data.get("timezone", "UTC")
            return pytz.timezone(tz_name)
    except Exception:
        # Fall back to UTC if timezone detection fails
        return pytz.UTC


def _event_to_dict(event: caldav.CalendarObjectResource) -> dict:
    cal = Calendar.from_ical(event.data)
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            rrule = component.get("rrule")
            return {
                "uid": str(component.get("uid", "")),
                "summary": str(component.get("summary", "")),
                "description": str(component.get("description", "")),
                "location": str(component.get("location", "")),
                "start": dtstart.dt.isoformat() if dtstart else None,
                "end": dtend.dt.isoformat() if dtend else None,
                "status": str(component.get("status", "")),
                "rrule": rrule.to_ical().decode() if rrule else None,
            }
    return {}


@mcp.resource("calendars://list")
def calendars_resource() -> str:
    """List all available iCloud calendars as a resource.

    Returns a JSON array of objects with 'name' and 'url' for each calendar.
    Exposed as a resource so clients can discover available calendars on connect
    without explicitly invoking a tool.
    """
    client = _get_client()
    principal = client.principal()
    result = [
        {"name": _get_calendar_name(cal), "url": str(cal.url)}
        for cal in principal.calendars()
    ]
    return json.dumps(result)


@mcp.resource("timezone://current")
def timezone_resource() -> str:
    """Get the current user's timezone based on their public IP address.

    Returns a JSON object with ip, timezone, utc_offset, country, and city.
    """
    with urllib.request.urlopen("https://ipapi.co/json/") as resp:
        data = json.loads(resp.read())
    return json.dumps({
        "ip": data.get("ip"),
        "timezone": data.get("timezone"),
        "utc_offset": data.get("utc_offset"),
        "country": data.get("country_name"),
        "city": data.get("city"),
    })


@mcp.tool
def list_calendars() -> list[dict]:
    """List all available iCloud calendars.

    Returns:
        A list of dicts with 'name' and 'url' for each calendar.
    """
    client = _get_client()
    principal = client.principal()
    result = []
    for cal in principal.calendars():
        name = _get_calendar_name(cal)
        result.append({"name": name, "url": str(cal.url)})
    return result


@mcp.tool
def list_events(
    calendar_name: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict]:
    """List calendar events from an iCloud calendar.

    Args:
        calendar_name: Name of the iCloud calendar. Defaults to all calendars.
        start: ISO 8601 start datetime for filtering (e.g. '2026-01-01T00:00:00').
               Defaults to the beginning of the current month.
        end: ISO 8601 end datetime for filtering (e.g. '2026-01-31T23:59:59').
             Defaults to 30 days after start.
    """
    tz = pytz.UTC
    if start:
        start_dt = datetime.fromisoformat(start).replace(tzinfo=tz)
    else:
        now = datetime.now(tz)
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if end:
        end_dt = datetime.fromisoformat(end).replace(tzinfo=tz)
    else:
        end_dt = start_dt + timedelta(days=30)

    client = _get_client()
    principal = client.principal()

    if calendar_name:
        calendars = [_find_calendar(principal, calendar_name)]
    else:
        calendars = principal.calendars()

    all_events = []
    for cal in calendars:
        cal_display_name = _get_calendar_name(cal)
        try:
            events = cal.date_search(start=start_dt, end=end_dt, expand=True)
            for e in events:
                event_dict = _event_to_dict(e)
                if event_dict:
                    event_dict["calendar"] = cal_display_name
                    all_events.append(event_dict)
        except Exception:
            # Skip calendars that don't support VEVENT date search (e.g. reminders)
            pass

    return all_events


@mcp.tool
def get_event(uid: str, calendar_name: Optional[str] = None) -> dict:
    """Get a single calendar event by its UID.

    Args:
        uid: The unique identifier of the event.
        calendar_name: Name of the iCloud calendar. Defaults to searching all calendars.
    """
    client = _get_client()
    principal = client.principal()

    if calendar_name:
        calendars = [_find_calendar(principal, calendar_name)]
    else:
        calendars = principal.calendars()

    for cal in calendars:
        try:
            for event in cal.events():
                parsed = Calendar.from_ical(event.data)
                for component in parsed.walk():
                    if component.name == "VEVENT" and str(component.get("uid", "")) == uid:
                        return _event_to_dict(event)
        except Exception:
            pass

    raise ValueError(f"Event with UID '{uid}' not found")


@mcp.tool
def create_event(
    summary: str,
    start: str,
    end: str,
    calendar_name: str = DEFAULT_CALENDAR,
    description: str = "",
    location: str = "",
    rrule: Optional[str] = None,
    ctx: Context = CurrentContext,
) -> dict:
    """Create a new calendar event in an iCloud calendar.

    Args:
        summary: Title of the event.
        start: ISO 8601 start datetime (e.g. '2026-03-15T10:00:00').
        end: ISO 8601 end datetime (e.g. '2026-03-15T11:00:00').
        calendar_name: Name of the iCloud calendar.
        description: Optional event description.
        location: Optional event location.
        rrule: Optional iCalendar RRULE string for recurring events
               (e.g. 'FREQ=WEEKLY;BYDAY=MO,WE,FR' or 'FREQ=DAILY;COUNT=5'
               or 'FREQ=MONTHLY;UNTIL=20261231T235959Z').

    Returns:
        The created event as a dict with its assigned UID.
    """
    # Get user's timezone from client IP in request context
    user_tz = _get_user_timezone(ctx)

    start_dt = datetime.fromisoformat(start)
    if start_dt.tzinfo is None:
        start_dt = user_tz.localize(start_dt)
    end_dt = datetime.fromisoformat(end)
    if end_dt.tzinfo is None:
        end_dt = user_tz.localize(end_dt)

    event_uid = str(uuid.uuid4())

    cal = Calendar()
    cal.add("prodid", "-//iCloud Calendar MCP//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("uid", event_uid)
    event.add("summary", summary)
    event.add("dtstart", start_dt)
    event.add("dtend", end_dt)
    event.add("dtstamp", datetime.now(pytz.UTC))
    if description:
        event.add("description", description)
    if location:
        event.add("location", location)
    if rrule:
        event.add("rrule", vRecur.from_ical(rrule))
    event.add("status", "CONFIRMED")

    cal.add_component(event)

    client = _get_client()
    principal = client.principal()
    calendar = _find_calendar(principal, calendar_name)
    calendar.save_event(cal.to_ical().decode("utf-8"))

    return {
        "uid": event_uid,
        "summary": summary,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "description": description,
        "location": location,
        "status": "CONFIRMED",
        "rrule": rrule,
    }


@mcp.tool
def update_event(
    uid: str,
    summary: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    calendar_name: str = DEFAULT_CALENDAR,
    ctx: Context = CurrentContext,
) -> dict:
    """Update an existing calendar event by UID. Only provided fields are changed.

    Args:
        uid: The unique identifier of the event to update.
        summary: New title (optional).
        start: New ISO 8601 start datetime (optional).
        end: New ISO 8601 end datetime (optional).
        description: New description (optional).
        location: New location (optional).
        calendar_name: Name of the iCloud calendar.

    Returns:
        The updated event as a dict.
    """
    client = _get_client()
    principal = client.principal()
    calendar = _find_calendar(principal, calendar_name)

    target_event = None
    for event in calendar.events():
        cal = Calendar.from_ical(event.data)
        for component in cal.walk():
            if component.name == "VEVENT" and str(component.get("uid", "")) == uid:
                target_event = event
                break
        if target_event:
            break

    if not target_event:
        raise ValueError(f"Event with UID '{uid}' not found in calendar '{calendar_name}'")

    # Parse existing data
    existing_cal = Calendar.from_ical(target_event.data)
    existing = {}
    for component in existing_cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            existing = {
                "summary": str(component.get("summary", "")),
                "description": str(component.get("description", "")),
                "location": str(component.get("location", "")),
                "start": dtstart.dt if dtstart else None,
                "end": dtend.dt if dtend else None,
            }
            break

    # Apply updates
    new_summary = summary if summary is not None else existing["summary"]
    new_description = description if description is not None else existing["description"]
    new_location = location if location is not None else existing["location"]

    def _parse_dt(s: str) -> datetime:
        # Get user's timezone from client IP in request context
        user_tz = _get_user_timezone(ctx)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = user_tz.localize(dt)
        return dt

    new_start = _parse_dt(start) if start else existing["start"]
    new_end = _parse_dt(end) if end else existing["end"]

    # Delete old event and create updated one
    target_event.delete()

    new_cal = Calendar()
    new_cal.add("prodid", "-//iCloud Calendar MCP//EN")
    new_cal.add("version", "2.0")

    new_event = Event()
    new_event.add("uid", uid)
    new_event.add("summary", new_summary)
    new_event.add("dtstart", new_start)
    new_event.add("dtend", new_end)
    new_event.add("dtstamp", datetime.now(pytz.UTC))
    new_event.add("sequence", 1)
    if new_description:
        new_event.add("description", new_description)
    if new_location:
        new_event.add("location", new_location)
    new_event.add("status", "CONFIRMED")

    new_cal.add_component(new_event)
    calendar.save_event(new_cal.to_ical().decode("utf-8"))

    return {
        "uid": uid,
        "summary": new_summary,
        "start": new_start.isoformat() if new_start else None,
        "end": new_end.isoformat() if new_end else None,
        "description": new_description,
        "location": new_location,
        "status": "CONFIRMED",
    }


@mcp.tool
def delete_event(uid: str, calendar_name: str = DEFAULT_CALENDAR) -> dict:
    """Delete a calendar event by its UID.

    Args:
        uid: The unique identifier of the event to delete.
        calendar_name: Name of the iCloud calendar.

    Returns:
        Confirmation dict with the deleted event's UID and summary.
    """
    client = _get_client()
    principal = client.principal()
    calendar = _find_calendar(principal, calendar_name)

    for event in calendar.events():
        cal = Calendar.from_ical(event.data)
        for component in cal.walk():
            if component.name == "VEVENT" and str(component.get("uid", "")) == uid:
                summary = str(component.get("summary", ""))
                event.delete()
                return {"deleted": True, "uid": uid, "summary": summary}

    raise ValueError(f"Event with UID '{uid}' not found in calendar '{calendar_name}'")


if __name__ == "__main__":
    mcp.run()
