"""Data coordinator for Climate Control Calendar integration."""
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    LOG_PREFIX_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)


class ClimateControlCalendarCoordinator(DataUpdateCoordinator):
    """Coordinator to manage calendar state and trigger slot evaluation."""

    def __init__(
        self,
        hass: HomeAssistant,
        calendar_entity_id: str,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """
        Initialize coordinator.

        Args:
            hass: Home Assistant instance
            calendar_entity_id: Entity ID of the calendar to monitor
            update_interval: Update interval in seconds
        """
        self.calendar_entity_id = calendar_entity_id
        self._previous_state: str | None = None
        self._previous_event: dict[str, Any] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{calendar_entity_id}",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Fetch calendar state and detect changes.

        Returns:
            Dictionary containing calendar state and metadata

        Raises:
            UpdateFailed: If calendar entity is unavailable
        """
        calendar_state = self.hass.states.get(self.calendar_entity_id)

        if calendar_state is None:
            raise UpdateFailed(
                f"{LOG_PREFIX_COORDINATOR} Calendar entity not found: {self.calendar_entity_id}"
            )

        if calendar_state.state == "unavailable":
            raise UpdateFailed(
                f"{LOG_PREFIX_COORDINATOR} Calendar entity unavailable: {self.calendar_entity_id}"
            )

        # Extract current event data
        current_state = calendar_state.state
        current_event = None

        if current_state == "on":
            # Calendar is active (event in progress)
            attributes = calendar_state.attributes
            current_event = {
                "summary": attributes.get("message", ""),
                "start": attributes.get("start_time"),
                "end": attributes.get("end_time"),
                "description": attributes.get("description", ""),
                "location": attributes.get("location", ""),
            }

        # Detect state change
        state_changed = self._previous_state != current_state
        event_changed = self._previous_event != current_event

        if state_changed:
            _LOGGER.debug(
                "%s Calendar state changed: %s -> %s",
                LOG_PREFIX_COORDINATOR,
                self._previous_state,
                current_state,
            )

        if event_changed and current_event:
            _LOGGER.debug(
                "%s Calendar event changed: %s",
                LOG_PREFIX_COORDINATOR,
                current_event.get("summary", "Unknown"),
            )

        # Update tracking
        self._previous_state = current_state
        self._previous_event = current_event

        return {
            "calendar_entity_id": self.calendar_entity_id,
            "state": current_state,
            "event": current_event,
            "state_changed": state_changed,
            "event_changed": event_changed,
            "last_update": dt_util.utcnow(),
        }

    async def async_refresh_now(self) -> None:
        """Force immediate coordinator refresh."""
        _LOGGER.info("%s Forcing immediate refresh", LOG_PREFIX_COORDINATOR)
        await self.async_request_refresh()

    def get_current_calendar_state(self) -> str | None:
        """
        Get current calendar state.

        Returns:
            Current state ('on', 'off', or None if unavailable)
        """
        if self.data is None:
            return None
        return self.data.get("state")

    def get_current_event(self) -> dict[str, Any] | None:
        """
        Get current calendar event.

        Returns:
            Current event dict or None if no event active
        """
        if self.data is None:
            return None
        return self.data.get("event")

    def is_calendar_active(self) -> bool:
        """
        Check if calendar has an active event.

        Returns:
            True if calendar is active (on), False otherwise
        """
        state = self.get_current_calendar_state()
        return state == "on"
