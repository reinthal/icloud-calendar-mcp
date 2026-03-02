# iCloud Calendar MCP Development

## MCP Server Usage

**IMPORTANT**: This repository contains a local development MCP server. When working with iCloud calendar operations, always use the local development server tools:

- `mcp__icloud-calendar__*` (local dev server)

**DO NOT** use the production server:
- ~~`mcp__claude_ai_icloud-calendar-mcp__*`~~ (production server)

The local development server is the one being actively developed and tested in this repository.

## Timezone Handling

The server uses Europe/Paris timezone (CET/CEST) for all events:

- **Hardcoded Timezone**: All events use Europe/Paris which automatically handles CET (winter, UTC+1) and CEST (summer, UTC+2) transitions

When a datetime string is provided without timezone information (e.g., `2026-03-02T10:00:00`), the server will localize it to Europe/Paris timezone. For timezone-aware operations, you can provide ISO 8601 datetime strings with timezone information (e.g., `2026-03-02T10:00:00-05:00`).
