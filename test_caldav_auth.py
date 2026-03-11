#!/usr/bin/env python3
"""Test CalDAV authentication with Protonmail SMTP credentials."""

import os
import sys
import caldav

def test_protonmail_caldav():
    """Test Protonmail CalDAV connection."""
    url = os.getenv("PROTONMAIL_CALDAV_URL", "https://calendar.protonmail.com/dav/")
    username = os.getenv("PROTONMAIL_SMTP_USERNAME")
    password = os.getenv("PROTONMAIL_SMTP_TOKEN")

    if not username or not password:
        print("❌ Error: PROTONMAIL_SMTP_USERNAME and PROTONMAIL_SMTP_TOKEN must be set")
        return False

    print(f"Testing CalDAV connection to: {url}")
    print(f"Username configured: {username[:3]}***{username[-3:] if len(username) > 6 else '***'}")

    try:
        client = caldav.DAVClient(url=url, username=username, password=password)
        principal = client.principal()

        print("✅ Authentication successful!")

        # Try to list calendars
        calendars = principal.calendars()
        print(f"✅ Found {len(calendars)} calendar(s):")

        for cal in calendars:
            cal_name = cal.name or "Unnamed"
            print(f"   - {cal_name}")

        return True

    except caldav.lib.error.AuthorizationError as e:
        print(f"❌ Authentication failed: {e}")
        print("\nPossible issues:")
        print("  1. SMTP credentials may not work for CalDAV")
        print("  2. You may need an app-specific password for CalDAV")
        print("  3. You may need Protonmail Bridge running locally")
        return False

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_protonmail_caldav()
    sys.exit(0 if success else 1)
