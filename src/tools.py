"""MCP tool implementations for calendar operations."""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytz
from icalendar import Calendar, Event, vRecur

from .providers import ProviderRegistry
from .utils import get_calendar_name, get_calendar_metadata, update_calendar_properties, find_calendar, event_to_dict


DEFAULT_CALENDAR = os.getenv("ICLOUD_CALENDAR", "Alex Plugg")


def list_calendars() -> list[dict]:
    """List all available calendars from all configured providers with comprehensive metadata.

    Returns:
        A list of dicts containing:
        - name: Display name with provider prefix
        - provider: Provider identifier (icloud, protonmail, etc.)
        - url: CalDAV URL for the calendar
        - description: Calendar description (if set)
        - timezone: Calendar timezone information (extracted from VTIMEZONE data)
        - supported_components: List of supported component types (VEVENT, VTODO, etc.)
    """
    registry = ProviderRegistry()
    all_calendars = []

    for provider in registry.get_enabled_providers():
        try:
            client = provider.get_client()
            principal = client.principal()
            for cal in principal.calendars():
                metadata = get_calendar_metadata(cal)
                # Add provider information
                metadata["name"] = provider.add_prefix(metadata["name"])
                metadata["provider"] = provider.name
                all_calendars.append(metadata)
        except Exception as e:
            # Log warning but continue with other providers
            print(f"Warning: Failed to fetch calendars from {provider.display_name}: {e}")

    return all_calendars


def update_calendar_metadata(
    calendar_name: str,
    description: Optional[str] = None
) -> dict:
    """Update metadata for a calendar.

    Args:
        calendar_name: Full calendar name with provider prefix (e.g. '[iCloud] Work')
        description: New description for the calendar (optional)

    Returns:
        Dict with the updated calendar metadata including provider information
    """
    registry = ProviderRegistry()
    provider, base_name = registry.find_provider_for_calendar(calendar_name)

    client = provider.get_client()
    principal = client.principal()
    calendar = find_calendar(principal, base_name)

    metadata = update_calendar_properties(calendar, description=description)
    # Add provider information
    metadata["name"] = provider.add_prefix(metadata["name"])
    metadata["provider"] = provider.name
    return metadata


def list_events(
    calendar_name: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict]:
    """List calendar events from specified calendar or all calendars.

    Args:
        calendar_name: Full calendar name with provider prefix (e.g. '[iCloud] Work').
                      Defaults to all calendars from all providers.
        start: ISO 8601 start datetime. Defaults to start of current month.
        end: ISO 8601 end datetime. Defaults to 30 days after start.

    Returns:
        List of event dicts with 'calendar' and 'provider' fields added.
    """
    tz = pytz.UTC
    if start:
        start_dt = datetime.fromisoformat(start)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tz)
    else:
        now = datetime.now(tz)
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if end:
        end_dt = datetime.fromisoformat(end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=tz)
    else:
        end_dt = start_dt + timedelta(days=30)

    registry = ProviderRegistry()
    all_events = []

    if calendar_name:
        # Single calendar from specific provider
        provider, base_name = registry.find_provider_for_calendar(calendar_name)
        providers_calendars = [(provider, [base_name])]
    else:
        # All calendars from all providers
        providers_calendars = []
        for provider in registry.get_enabled_providers():
            try:
                client = provider.get_client()
                principal = client.principal()
                cal_names = [get_calendar_name(cal) for cal in principal.calendars()]
                providers_calendars.append((provider, cal_names))
            except Exception:
                pass

    # Fetch events from each provider's calendars
    for provider, cal_names in providers_calendars:
        client = provider.get_client()
        principal = client.principal()

        for cal_name in cal_names:
            try:
                cal = find_calendar(principal, cal_name)
                events = cal.date_search(start=start_dt, end=end_dt, expand=True)

                for e in events:
                    event_dict = event_to_dict(e)
                    if event_dict:
                        event_dict["calendar"] = provider.add_prefix(cal_name)
                        event_dict["provider"] = provider.name
                        all_events.append(event_dict)
            except Exception:
                # Skip calendars that don't support VEVENT or have errors
                pass

    return all_events


def get_event(uid: str, calendar_name: Optional[str] = None) -> dict:
    """Get a single calendar event by its UID.

    Args:
        uid: The unique identifier of the event.
        calendar_name: Optional full calendar name with provider prefix.
                      Defaults to searching all calendars from all providers.

    Returns:
        Event dict with 'calendar' and 'provider' fields.

    Raises:
        ValueError: If event not found
    """
    registry = ProviderRegistry()

    if calendar_name:
        # Search specific calendar
        provider, base_name = registry.find_provider_for_calendar(calendar_name)
        providers_to_search = [(provider, [base_name])]
    else:
        # Search all providers and their calendars
        providers_to_search = []
        for provider in registry.get_enabled_providers():
            try:
                client = provider.get_client()
                principal = client.principal()
                cal_names = [get_calendar_name(cal) for cal in principal.calendars()]
                providers_to_search.append((provider, cal_names))
            except Exception:
                pass

    for provider, cal_names in providers_to_search:
        client = provider.get_client()
        principal = client.principal()

        for cal_name in cal_names:
            try:
                cal = find_calendar(principal, cal_name)
                for event in cal.events():
                    parsed = Calendar.from_ical(event.data)
                    for component in parsed.walk():
                        if component.name == "VEVENT" and str(component.get("uid", "")) == uid:
                            event_dict = event_to_dict(event)
                            if event_dict:
                                event_dict["calendar"] = provider.add_prefix(cal_name)
                                event_dict["provider"] = provider.name
                                return event_dict
            except Exception:
                pass

    raise ValueError(f"Event with UID '{uid}' not found in any calendar")


def create_event(
    summary: str,
    start: str,
    end: str,
    calendar_name: str = DEFAULT_CALENDAR,
    description: str = "",
    location: str = "",
    rrule: Optional[str] = None,
) -> dict:
    """Create a new calendar event in any calendar (iCloud or Protonmail).

    Args:
        summary: Title of the event.
        start: ISO 8601 start datetime.
        end: ISO 8601 end datetime.
        calendar_name: Full calendar name with provider prefix (e.g. '[Protonmail] Personal').
                      Defaults to DEFAULT_CALENDAR for backward compatibility.
        description: Optional event description.
        location: Optional event location.
        rrule: Optional iCalendar RRULE string for recurring events.

    Returns:
        The created event as a dict with its assigned UID.
    """
    registry = ProviderRegistry()
    provider, base_name = registry.find_provider_for_calendar(calendar_name)

    # Parse datetimes
    start_dt = datetime.fromisoformat(start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=pytz.UTC)
    end_dt = datetime.fromisoformat(end)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=pytz.UTC)

    event_uid = str(uuid.uuid4())

    # Build iCalendar event
    cal = Calendar()
    cal.add("prodid", "-//Multi-Provider Calendar MCP//EN")
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

    # Save to provider-specific calendar
    client = provider.get_client()
    principal = client.principal()
    calendar = find_calendar(principal, base_name)
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
        "calendar": provider.add_prefix(base_name),
        "provider": provider.name,
    }


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
        calendar_name: Full calendar name with provider prefix.

    Returns:
        The updated event as a dict.

    Raises:
        ValueError: If event not found
    """
    # Add provider routing
    registry = ProviderRegistry()
    provider, base_name = registry.find_provider_for_calendar(calendar_name)

    client = provider.get_client()
    principal = client.principal()
    calendar = find_calendar(principal, base_name)

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
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt

    new_start = _parse_dt(start) if start else existing["start"]
    new_end = _parse_dt(end) if end else existing["end"]

    # Delete old event and create updated one
    target_event.delete()

    new_cal = Calendar()
    new_cal.add("prodid", "-//Multi-Provider Calendar MCP//EN")
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
        "calendar": provider.add_prefix(base_name),
        "provider": provider.name,
    }


def delete_event(uid: str, calendar_name: str = DEFAULT_CALENDAR) -> dict:
    """Delete a calendar event by its UID.

    Args:
        uid: The unique identifier of the event to delete.
        calendar_name: Full calendar name with provider prefix.

    Returns:
        Confirmation dict with the deleted event's UID and summary.

    Raises:
        ValueError: If event not found
    """
    # Add provider routing
    registry = ProviderRegistry()
    provider, base_name = registry.find_provider_for_calendar(calendar_name)

    client = provider.get_client()
    principal = client.principal()
    calendar = find_calendar(principal, base_name)

    for event in calendar.events():
        cal = Calendar.from_ical(event.data)
        for component in cal.walk():
            if component.name == "VEVENT" and str(component.get("uid", "")) == uid:
                summary = str(component.get("summary", ""))
                event.delete()
                return {
                    "deleted": True,
                    "uid": uid,
                    "summary": summary,
                    "calendar": provider.add_prefix(base_name),
                    "provider": provider.name,
                }

    raise ValueError(f"Event with UID '{uid}' not found in calendar '{calendar_name}'")
