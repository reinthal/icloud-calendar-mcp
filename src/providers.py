"""CalDAV provider implementations for multi-provider calendar support."""

import os
from typing import Optional
import caldav


class CalDAVProvider:
    """Base class for CalDAV provider implementations."""

    def __init__(self, name: str, display_name: str):
        """Initialize provider.

        Args:
            name: Internal provider identifier (e.g., "icloud", "protonmail")
            display_name: Human-readable name for display (e.g., "iCloud", "Protonmail")
        """
        self.name = name
        self.display_name = display_name
        self.prefix = f"[{display_name}]"

    def get_client(self) -> caldav.DAVClient:
        """Return configured CalDAV client.

        Must be implemented by subclasses.

        Returns:
            Configured CalDAV client

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def is_enabled(self) -> bool:
        """Check if provider credentials are configured.

        Must be implemented by subclasses.

        Returns:
            True if credentials are available, False otherwise
        """
        raise NotImplementedError

    def add_prefix(self, calendar_name: str) -> str:
        """Add provider prefix to calendar name.

        Args:
            calendar_name: Base calendar name

        Returns:
            Prefixed calendar name (e.g., "[iCloud] Work")
        """
        return f"{self.prefix} {calendar_name}"

    def strip_prefix(self, full_name: str) -> str:
        """Remove provider prefix from calendar name.

        Args:
            full_name: Full calendar name with prefix

        Returns:
            Calendar name without prefix
        """
        return full_name.replace(self.prefix, "").strip()


class ICloudProvider(CalDAVProvider):
    """iCloud CalDAV provider implementation."""

    def __init__(self):
        """Initialize iCloud provider with standard CalDAV URL."""
        super().__init__("icloud", "iCloud")
        self.url = "https://caldav.icloud.com/"

    def get_client(self) -> caldav.DAVClient:
        """Create iCloud CalDAV client.

        Returns:
            Configured CalDAV client for iCloud

        Raises:
            ValueError: If credentials are not configured
        """
        username = os.getenv("ICLOUD_USERNAME")
        password = os.getenv("ICLOUD_PASSWORD")
        if not username or not password:
            raise ValueError("ICLOUD_USERNAME and ICLOUD_PASSWORD must be set")
        return caldav.DAVClient(url=self.url, username=username, password=password)

    def is_enabled(self) -> bool:
        """Check if iCloud credentials are configured.

        Returns:
            True if both username and password are set
        """
        return bool(os.getenv("ICLOUD_USERNAME") and os.getenv("ICLOUD_PASSWORD"))


class ProtonmailProvider(CalDAVProvider):
    """Protonmail CalDAV provider implementation."""

    def __init__(self):
        """Initialize Protonmail provider with CalDAV URL."""
        super().__init__("protonmail", "Protonmail")
        self.url = os.getenv("PROTONMAIL_CALDAV_URL", "https://calendar.protonmail.com/dav/")

    def get_client(self) -> caldav.DAVClient:
        """Create Protonmail CalDAV client.

        Uses SMTP credentials for CalDAV authentication.

        Returns:
            Configured CalDAV client for Protonmail

        Raises:
            ValueError: If credentials are not configured
        """
        username = os.getenv("PROTONMAIL_SMTP_USERNAME")
        password = os.getenv("PROTONMAIL_SMTP_TOKEN")
        if not username or not password:
            raise ValueError("PROTONMAIL_SMTP_USERNAME and PROTONMAIL_SMTP_TOKEN must be set")
        return caldav.DAVClient(url=self.url, username=username, password=password)

    def is_enabled(self) -> bool:
        """Check if Protonmail credentials are configured.

        Returns:
            True if both username and password are set
        """
        return bool(os.getenv("PROTONMAIL_SMTP_USERNAME") and
                   os.getenv("PROTONMAIL_SMTP_TOKEN"))


class ProviderRegistry:
    """Manages all configured CalDAV providers."""

    def __init__(self):
        """Initialize registry with all available providers."""
        self.providers = {
            "icloud": ICloudProvider(),
            "protonmail": ProtonmailProvider(),
        }

    def get_enabled_providers(self) -> list[CalDAVProvider]:
        """Return list of providers with valid credentials.

        Returns:
            List of enabled providers
        """
        return [p for p in self.providers.values() if p.is_enabled()]

    def find_provider_for_calendar(self, calendar_name: str) -> tuple[CalDAVProvider, str]:
        """Parse calendar name to find provider and extract base name.

        Args:
            calendar_name: Full calendar name (may include provider prefix)

        Returns:
            Tuple of (provider, calendar_name_without_prefix)

        Raises:
            ValueError: If provider cannot be determined

        Examples:
            "[iCloud] Work" -> (ICloudProvider, "Work")
            "[Protonmail] Personal" -> (ProtonmailProvider, "Personal")
            "Work" -> (ICloudProvider, "Work")  # Backward compatibility
        """
        # Check for explicit provider prefix
        for provider in self.providers.values():
            if calendar_name.startswith(provider.prefix):
                return provider, provider.strip_prefix(calendar_name)

        # Fallback: unprefixed names default to iCloud for backward compatibility
        if self.providers["icloud"].is_enabled():
            return self.providers["icloud"], calendar_name

        raise ValueError(
            f"Cannot determine provider for calendar '{calendar_name}'. "
            f"Use format '[Provider] CalendarName' or configure iCloud credentials."
        )
