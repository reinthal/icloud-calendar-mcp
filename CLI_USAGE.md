# iCloud Calendar CLI Usage Guide

The `icloud-cal` command-line tool provides a convenient way to manage your iCloud calendars directly from the terminal.

## Installation

```bash
# Install from source (development)
uv pip install -e .

# Or install from git (when published)
pip install git+https://github.com/yourusername/icloud-calendar-mcp.git
```

## Prerequisites

Set the following environment variables:

```bash
export ICLOUD_USERNAME="your-apple-id@icloud.com"
export ICLOUD_PASSWORD="your-app-specific-password"
export ICLOUD_CALENDAR="Your Default Calendar"  # Optional
```

## Commands

### List Calendars

Display all available iCloud calendars with metadata:

```bash
icloud-cal list-calendars

# JSON output
icloud-cal list-calendars --json
```

### List Events

List events from calendars with optional filtering:

```bash
# List all events from all calendars (current month)
icloud-cal list-events

# List events from a specific calendar
icloud-cal list-events --calendar "Alex Plugg"

# List events with date range
icloud-cal list-events --start "2026-03-01T00:00:00" --end "2026-03-31T23:59:59"

# Combine filters
icloud-cal list-events --calendar "Work" --start "2026-03-11T00:00:00"

# JSON output
icloud-cal list-events --json
```

### Get Event

Retrieve details of a specific event by UID:

```bash
icloud-cal get-event <uid>

# Specify calendar
icloud-cal get-event <uid> --calendar "Alex Plugg"

# JSON output
icloud-cal get-event <uid> --json
```

### Create Event

Create a new calendar event:

```bash
# Basic event
icloud-cal create-event "Meeting with Team" \
  --start "2026-03-15T10:00:00" \
  --end "2026-03-15T11:00:00"

# Full event with all options
icloud-cal create-event "Project Review" \
  --start "2026-03-15T14:00:00" \
  --end "2026-03-15T15:30:00" \
  --calendar "Work" \
  --description "Q1 project review meeting" \
  --location "Conference Room A"

# Recurring event
icloud-cal create-event "Weekly Standup" \
  --start "2026-03-17T09:00:00" \
  --end "2026-03-17T09:30:00" \
  --rrule "FREQ=WEEKLY;BYDAY=MO,WE,FR"

# JSON output
icloud-cal create-event "Event" --start "..." --end "..." --json
```

### Update Event

Update an existing event (only specified fields are changed):

```bash
# Update summary
icloud-cal update-event <uid> --summary "Updated Meeting Title"

# Update time
icloud-cal update-event <uid> \
  --start "2026-03-15T11:00:00" \
  --end "2026-03-15T12:00:00"

# Update multiple fields
icloud-cal update-event <uid> \
  --summary "New Title" \
  --description "New description" \
  --location "New Location"

# Specify calendar
icloud-cal update-event <uid> --calendar "Work" --summary "Updated"

# JSON output
icloud-cal update-event <uid> --summary "..." --json
```

### Delete Event

Delete an event from your calendar:

```bash
# Interactive confirmation
icloud-cal delete-event <uid>

# Skip confirmation
icloud-cal delete-event <uid> -y

# Specify calendar
icloud-cal delete-event <uid> --calendar "Work" -y

# JSON output
icloud-cal delete-event <uid> -y --json
```

### Update Calendar Metadata

Update calendar description and other metadata:

```bash
# Update description
icloud-cal update-calendar "Work" \
  --description "Work-related events and meetings"

# JSON output
icloud-cal update-calendar "Work" --description "..." --json
```

## Output Formats

All commands support two output formats:

1. **Pretty Table** (default): Human-readable tables with colors
2. **JSON** (--json flag): Machine-readable JSON for scripting

## Examples

### Daily Agenda

```bash
# View today's events
icloud-cal list-events \
  --start "$(date +%Y-%m-%d)T00:00:00" \
  --end "$(date +%Y-%m-%d)T23:59:59"
```

### Quick Event Creation

```bash
# Create a 1-hour meeting starting now
icloud-cal create-event "Quick Meeting" \
  --start "$(date -u +%Y-%m-%dT%H:%M:%S)" \
  --end "$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%S)"
```

### Scripting with JSON

```bash
# Get all events as JSON and process with jq
icloud-cal list-events --json | jq '.result[] | select(.summary | contains("Meeting"))'

# Count events
icloud-cal list-events --json | jq '.result | length'
```

## Tips

- **Calendar Names**: Use the name without the `[iCloud]` prefix (e.g., "Alex Plugg" not "[iCloud] Alex Plugg")
- **Dates**: Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`
- **Timezones**: Dates without timezone are treated as UTC
- **UIDs**: Get event UIDs from `list-events` or `create-event` output
- **Colors**: The CLI uses colored output - pipe to `less -R` to preserve colors

## Help

Get help for any command:

```bash
icloud-cal --help
icloud-cal create-event --help
icloud-cal list-events --help
```
