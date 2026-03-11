"""MCP resource definitions for calendar data."""

import json
import urllib.request
from .providers import ProviderRegistry
from .utils import get_calendar_metadata


def get_calendars_resource() -> str:
    """List all available calendars from all providers as a resource.

    Returns a JSON array of objects with comprehensive metadata for each calendar.
    Exposed as a resource so clients can discover available calendars on connect
    without explicitly invoking a tool.

    Returns:
        JSON string containing array of calendar objects with:
        - name: Display name with provider prefix
        - provider: Provider identifier
        - url: CalDAV URL
        - description: Calendar description (if set)
        - timezone: Calendar timezone information
        - supported_components: List of supported component types
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
        except Exception:
            # Skip providers with errors
            pass

    return json.dumps(all_calendars)


def get_timezone_resource() -> str:
    """Get current timezone information based on IP address.

    Returns:
        JSON string containing timezone information
    """
    try:
        with urllib.request.urlopen("https://ipapi.co/json/") as resp:
            data = json.loads(resp.read())
        return json.dumps({
            "ip": data.get("ip"),
            "timezone": data.get("timezone"),
            "utc_offset": data.get("utc_offset"),
            "country": data.get("country_name"),
            "city": data.get("city"),
        })
    except Exception:
        return json.dumps({"error": "Failed to fetch timezone"})
