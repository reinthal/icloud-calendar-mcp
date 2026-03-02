# iCloud Calendar MCP Development

## MCP Server Usage

**IMPORTANT**: This repository contains a local development MCP server. When working with iCloud calendar operations, always use the local development server tools:

- `mcp__icloud-calendar__*` (local dev server)

**DO NOT** use the production server:
- ~~`mcp__claude_ai_icloud-calendar-mcp__*`~~ (production server)

The local development server is the one being actively developed and tested in this repository.

## Timezone Handling

The server automatically detects the client's timezone based on their IP address when creating or updating events:

1. **Client IP Detection**: Extracts the client IP from request headers (`X-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP`)
2. **Timezone Lookup**: Uses ipapi.co to determine timezone from the client IP
3. **Fallback**: Falls back to server timezone if client IP is unavailable, then to UTC if all else fails

When a datetime string is provided without timezone information (e.g., `2026-03-02T10:00:00`), the server will localize it to the client's detected timezone.
