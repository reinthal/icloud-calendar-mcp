import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import caldav
import pytz
from fastmcp import FastMCP
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


def _get_calendar_metadata(calendar: caldav.Calendar) -> dict:
    """Retrieve comprehensive metadata for a calendar using standard CalDAV properties.

    Returns:
        Dict with name, url, description, timezone, and supported_components.
    """
    from caldav.elements import dav, cdav
    import xml.etree.ElementTree as ET

    # Build a PROPFIND request for standard CalDAV properties only
    propfind_xml = '''<?xml version="1.0" encoding="utf-8" ?>
    <D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
        <D:prop>
            <D:displayname />
            <C:calendar-description />
            <C:calendar-timezone />
            <C:supported-calendar-component-set />
        </D:prop>
    </D:propfind>'''

    try:
        # Make direct PROPFIND request
        response = calendar.client.propfind(
            calendar.url,
            props=propfind_xml,
            depth=0
        )

        # Parse the XML response
        tree = response.tree
        ns = {
            'D': 'DAV:',
            'C': 'urn:ietf:params:xml:ns:caldav'
        }

        # Extract properties
        metadata = {
            "name": "",
            "url": str(calendar.url),
            "description": "",
            "timezone": "",
            "supported_components": []
        }

        # Get displayname
        displayname_elem = tree.find('.//D:displayname', ns)
        if displayname_elem is not None and displayname_elem.text:
            metadata["name"] = displayname_elem.text

        # Get description
        desc_elem = tree.find('.//C:calendar-description', ns)
        if desc_elem is not None and desc_elem.text:
            metadata["description"] = desc_elem.text

        # Get timezone (usually contains full VTIMEZONE data)
        tz_elem = tree.find('.//C:calendar-timezone', ns)
        if tz_elem is not None and tz_elem.text:
            # Extract just the timezone ID from the VTIMEZONE data
            tz_text = tz_elem.text
            if "TZID:" in tz_text:
                for line in tz_text.split('\n'):
                    if line.startswith('TZID:'):
                        metadata["timezone"] = line.split(':', 1)[1].strip()
                        break
            else:
                metadata["timezone"] = "UTC"

        # Get supported components
        comp_set = tree.find('.//C:supported-calendar-component-set', ns)
        if comp_set is not None:
            for comp in comp_set.findall('.//C:comp', ns):
                comp_name = comp.get('name')
                if comp_name:
                    metadata["supported_components"].append(comp_name)

    except Exception as e:
        # Fallback to basic properties if advanced retrieval fails
        try:
            props = calendar.get_properties([dav.DisplayName()])
            metadata = {
                "name": props.get("{DAV:}displayname", ""),
                "url": str(calendar.url),
                "description": "",
                "timezone": "",
                "supported_components": []
            }
        except Exception:
            # Last resort fallback
            metadata = {
                "name": "Unknown",
                "url": str(calendar.url),
                "description": "",
                "timezone": "",
                "supported_components": []
            }

    return metadata


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


def _get_user_timezone() -> pytz.tzinfo:
    """Get the timezone for events (hardcoded to Europe/Paris for CET/CEST)."""
    # Hardcoded to Europe/Paris which automatically handles CET (winter) and CEST (summer)
    return pytz.timezone("Europe/Paris")


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

    Returns a JSON array of objects with comprehensive metadata for each calendar.
    Exposed as a resource so clients can discover available calendars on connect
    without explicitly invoking a tool.
    """
    client = _get_client()
    principal = client.principal()
    result = [_get_calendar_metadata(cal) for cal in principal.calendars()]
    return json.dumps(result)


def _update_calendar_properties(calendar: caldav.Calendar, description: Optional[str] = None) -> dict:
    """Update calendar properties using PROPPATCH.

    Args:
        calendar: The calendar object to update
        description: New description for the calendar

    Returns:
        Dict with the updated properties
    """
    import xml.etree.ElementTree as ET

    if description is None:
        return _get_calendar_metadata(calendar)

    # Build PROPPATCH XML request
    proppatch_xml = f'''<?xml version="1.0" encoding="utf-8" ?>
    <D:propertyupdate xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
        <D:set>
            <D:prop>
                <C:calendar-description>{description}</C:calendar-description>
            </D:prop>
        </D:set>
    </D:propertyupdate>'''

    try:
        # Send PROPPATCH request
        response = calendar.client.proppatch(calendar.url, proppatch_xml)

        # Return updated metadata
        return _get_calendar_metadata(calendar)

    except Exception as e:
        raise ValueError(f"Failed to update calendar properties: {e}")


@mcp.tool
def update_calendar_metadata(
    calendar_name: str,
    description: Optional[str] = None
) -> dict:
    """Update metadata for a calendar.

    Args:
        calendar_name: Name of the iCloud calendar to update
        description: New description for the calendar (optional)

    Returns:
        Dict with the updated calendar metadata
    """
    client = _get_client()
    principal = client.principal()
    calendar = _find_calendar(principal, calendar_name)

    return _update_calendar_properties(calendar, description=description)


@mcp.tool
def list_calendars() -> list[dict]:
    """List all available iCloud calendars with comprehensive metadata.

    Returns:
        A list of dicts containing:
        - name: Display name of the calendar
        - url: CalDAV URL for the calendar
        - description: Calendar description (if set)
        - timezone: Calendar timezone information (extracted from VTIMEZONE data)
        - supported_components: List of supported component types (VEVENT, VTODO, etc.)
    """
    client = _get_client()
    principal = client.principal()
    return [_get_calendar_metadata(cal) for cal in principal.calendars()]


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
    # Get server's timezone
    user_tz = _get_user_timezone()

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
        # Get server's timezone
        user_tz = _get_user_timezone()
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
