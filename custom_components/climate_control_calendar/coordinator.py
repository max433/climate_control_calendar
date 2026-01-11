"""Data coordinator for Climate Control Calendar integration.

DEPRECATED: This module now serves as a compatibility wrapper.
The actual implementation is in calendar_monitor.MultiCalendarCoordinator.

Decision D033: Multi-Calendar Support - This file maintains backward compatibility
while the integration transitions to the new multi-calendar architecture.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .calendar_monitor import MultiCalendarCoordinator
from .const import DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ClimateControlCalendarCoordinator(MultiCalendarCoordinator):
    """
    Legacy coordinator class for backward compatibility.

    This class now wraps MultiCalendarCoordinator and provides the same
    interface as before, but supports monitoring multiple calendars.

    DEPRECATED: Use MultiCalendarCoordinator directly for new code.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        calendar_entity_id: str | list[str],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """
        Initialize coordinator.

        Args:
            hass: Home Assistant instance
            calendar_entity_id: Single calendar ID (legacy) or list of calendar IDs
            update_interval: Update interval in seconds
        """
        # Convert single calendar to list for backward compatibility
        if isinstance(calendar_entity_id, str):
            calendar_entities = [calendar_entity_id]
            self.calendar_entity_id = calendar_entity_id  # Keep for legacy access
        else:
            calendar_entities = calendar_entity_id
            self.calendar_entity_id = calendar_entities[0] if calendar_entities else None

        # Initialize parent MultiCalendarCoordinator
        super().__init__(
            hass=hass,
            calendar_entities=calendar_entities,
            update_interval=update_interval,
        )

    def get_current_calendar_state(self) -> str | None:
        """
        Get current calendar state (legacy method).

        For single calendar: returns its state.
        For multiple calendars: returns 'on' if any calendar is active.

        Returns:
            Current state ('on', 'off', or None if unavailable)
        """
        if self.data is None:
            return None

        # If monitoring single calendar (legacy mode), return its state
        if len(self.calendar_entities) == 1:
            calendar_states = self.data.get("calendar_states", {})
            return calendar_states.get(self.calendar_entities[0])

        # Multi-calendar mode: return 'on' if any calendar active
        return "on" if self.is_any_calendar_active() else "off"

    def get_current_event(self) -> dict[str, Any] | None:
        """
        Get current calendar event (legacy method).

        For single calendar: returns its active event.
        For multiple calendars: returns first active event.

        Returns:
            Current event dict or None if no event active
        """
        active_events = self.get_active_events()

        if not active_events:
            return None

        # Return first active event
        return active_events[0]

    def is_calendar_active(self) -> bool:
        """
        Check if calendar has an active event (legacy method).

        Returns:
            True if any calendar is active (on), False otherwise
        """
        return self.is_any_calendar_active()


# Export MultiCalendarCoordinator for direct use in new code
__all__ = ["ClimateControlCalendarCoordinator", "MultiCalendarCoordinator"]
