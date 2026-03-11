"""Utility functions for calendar and event operations."""

from typing import Optional
import xml.etree.ElementTree as ET
import caldav
from icalendar import Calendar


def get_calendar_name(calendar: caldav.Calendar) -> str:
    """Extract display name from CalDAV calendar."""
    props = calendar.get_properties([caldav.dav.DisplayName()])
    return props.get("{DAV:}displayname", "")


def get_calendar_metadata(calendar: caldav.Calendar) -> dict:
    """Retrieve comprehensive metadata for a calendar using standard CalDAV properties.

    Returns:
        Dict with name, url, description, timezone, and supported_components.
    """
    from caldav.elements import dav

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


def update_calendar_properties(calendar: caldav.Calendar, description: Optional[str] = None) -> dict:
    """Update calendar properties using PROPPATCH.

    Args:
        calendar: The calendar object to update
        description: New description for the calendar

    Returns:
        Dict with the updated properties
    """
    if description is None:
        return get_calendar_metadata(calendar)

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
        return get_calendar_metadata(calendar)

    except Exception as e:
        raise ValueError(f"Failed to update calendar properties: {e}")


def find_calendar(principal: caldav.Principal, calendar_name: str) -> caldav.Calendar:
    """Find calendar by display name.

    Args:
        principal: CalDAV principal object
        calendar_name: Display name of the calendar to find

    Returns:
        The matching calendar object

    Raises:
        ValueError: If calendar not found
    """
    all_cals = principal.calendars()
    for cal in all_cals:
        if get_calendar_name(cal) == calendar_name:
            return cal
    available = [get_calendar_name(cal) for cal in all_cals]
    raise ValueError(
        f"Calendar '{calendar_name}' not found. Available: {available}"
    )


def event_to_dict(event: caldav.CalendarObjectResource) -> Optional[dict]:
    """Convert CalDAV event to dictionary.

    Args:
        event: CalDAV event object

    Returns:
        Dictionary representation of the event, or None if parsing fails
    """
    try:
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
    except Exception:
        return None
    return None
