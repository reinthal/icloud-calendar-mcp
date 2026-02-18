# 100 % Vibes

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://github.com/jlowin/fastmcp)
[![CalDAV](https://img.shields.io/badge/protocol-CalDAV-lightgrey.svg)](https://www.rfc-editor.org/rfc/rfc4791)

Takes an ICS file and imports it to an iCloud calendar. Also exposes an MCP server so Claude Code (or any MCP-compatible client) can manage calendar events directly.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ICLOUD_USERNAME` | Yes | — | iCloud account email address |
| `ICLOUD_PASSWORD` | Yes | — | iCloud [app-specific password](https://support.apple.com/en-us/102654) |
| `ICLOUD_CALENDAR` | No | `Alex Plugg` | Name of the target iCloud calendar |

Credentials are stored encrypted in `secrets.env` via [SOPS](https://github.com/getsops/sops) + [Age](https://github.com/FiloSottile/age) and loaded automatically by direnv.

## ICS Import (CLI)

Import an ICS file directly into iCloud:

```bash
uv run python main.py SchemaICAL.ics
# or, if inside the devenv shell:
import SchemaICAL.ics
```

Options:

```
usage: main.py [-h] [--username USERNAME] [--password PASSWORD] [--calendar CALENDAR] ics_file

positional arguments:
  ics_file                    Path to the ICS file to import

options:
  -u, --username USERNAME     iCloud username (falls back to ICLOUD_USERNAME)
  -p, --password PASSWORD     iCloud app-specific password (falls back to ICLOUD_PASSWORD)
  -c, --calendar CALENDAR     Target calendar name (default: Alex Plugg)
```

## MCP Server

`server.py` is a [FastMCP](https://github.com/jlowin/fastmcp) server that exposes CRUD operations on iCloud calendar events.

### Tools

| Tool | Description |
|---|---|
| `list_events` | List events in a date range (defaults to current month) |
| `get_event` | Fetch a single event by UID |
| `create_event` | Create a new event with title, time, description, and location |
| `update_event` | Update any fields of an existing event by UID |
| `delete_event` | Delete an event by UID |

### Installation — Claude Code (user-level)

Register the server globally so it is available in every project:

```bash
claude mcp add --scope user icloud-calendar \
  uv -- run fastmcp run /home/kog/repos/ics-icloud-import/server.py
```

The server reads `ICLOUD_USERNAME`, `ICLOUD_PASSWORD`, and `ICLOUD_CALENDAR` from the environment. These are already available in any shell that loads this repo's direnv config.

### Installation — Claude Desktop (macOS / Windows)

Add the following to your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "icloud-calendar": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/path/to/ics-icloud-import",
        "fastmcp", "run", "/path/to/ics-icloud-import/server.py"
      ],
      "env": {
        "ICLOUD_USERNAME": "your@icloud.com",
        "ICLOUD_PASSWORD": "xxxx-xxxx-xxxx-xxxx",
        "ICLOUD_CALENDAR": "My Calendar"
      }
    }
  }
}
```

Replace `/path/to/ics-icloud-import` with the actual path to this repository.

### Running the server manually

```bash
uv run fastmcp run server.py
```
