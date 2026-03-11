import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastmcp import FastMCP

# Import tools and resources from modules
from src.tools import (
    list_calendars,
    list_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    update_calendar_metadata,
)
from src.resources import get_calendars_resource, get_timezone_resource

# Initialize MCP server
mcp = FastMCP(
    "Multi-Provider Calendar",
    instructions="Manage iCloud and Protonmail calendar events via CalDAV. Supports listing, creating, updating, and deleting events.",
)

# Register tools
mcp.tool(list_calendars)
mcp.tool(list_events)
mcp.tool(get_event)
mcp.tool(create_event)
mcp.tool(update_event)
mcp.tool(delete_event)
mcp.tool(update_calendar_metadata)


# Register resources
@mcp.resource("calendars://list")
def calendars_resource() -> str:
    """List all available calendars from all providers as a resource.

    Returns a JSON array of objects with comprehensive metadata for each calendar.
    Exposed as a resource so clients can discover available calendars on connect
    without explicitly invoking a tool.
    """
    return get_calendars_resource()


@mcp.resource("timezone://current")
def timezone_resource() -> str:
    """Get current timezone information.

    Returns:
        JSON string containing timezone information
    """
    return get_timezone_resource()


# Run server
if __name__ == "__main__":
    mcp.run()
