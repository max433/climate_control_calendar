"""Multi-calendar monitoring coordinator.

This module implements a coordinator that monitors multiple calendars
simultaneously and determines which events are currently active.

Decision D033: Multi-Calendar Support
"""
from __future__ import annotations

from datetime import datetime, timedelta
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
)

_LOGGER = logging.getLogger(__name__)


class MultiCalendarCoordinator(DataUpdateCoordinator):
    """
    Coordinator that monitors multiple calendars simultaneously.

    Responsibilities:
    - Fetch events from N configured calendars
    - Determine which events are currently active
    - Detect calendar state changes
    - Provide unified data structure for engine consumption

    Note: This coordinator fetches events using calendar state + attributes.
    Future enhancement: Support calendar.get_events service for fetching
    upcoming events (requires HA 2023.10+).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        calendar_entities: list[str],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """
        Initialize multi-calendar coordinator.

        Args:
            hass: Home Assistant instance
            calendar_entities: List of calendar entity IDs to monitor
            update_interval: Update interval in seconds
        """
        self.calendar_entities = calendar_entities
        self._previous_active_events: dict[str, dict[str, Any]] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_multi_calendar",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Fetch events from all configured calendars using calendar.get_events service.

        Returns:
            Dictionary containing:
            - events: List of all events (active + upcoming)
            - active_events: List of currently active events
            - calendar_states: Dict of calendar_id -> state
            - last_update: Update timestamp

        Raises:
            UpdateFailed: If critical error occurs
        """
        all_events = []
        active_events = []
        calendar_states = {}
        errors = []

        now = dt_util.now()

        # Fetch events in a time window: from 1 hour ago to 24 hours in the future
        # This ensures we catch events that just started
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=24)

        # Fetch events from each calendar
        for calendar_id in self.calendar_entities:
            try:
                calendar_state = self.hass.states.get(calendar_id)

                if calendar_state is None:
                    _LOGGER.warning(
                        "Calendar entity not found: %s (skipping)",
                        calendar_id,
                    )
                    errors.append(f"Calendar not found: {calendar_id}")
                    continue

                if calendar_state.state == "unavailable":
                    _LOGGER.warning(
                        "Calendar entity unavailable: %s (skipping)",
                        calendar_id,
                    )
                    errors.append(f"Calendar unavailable: {calendar_id}")
                    continue

                # Store calendar state for reference
                calendar_states[calendar_id] = calendar_state.state

                # Use calendar.get_events service to fetch events actively
                try:
                    response = await self.hass.services.async_call(
                        "calendar",
                        "get_events",
                        {
                            "entity_id": calendar_id,
                            "start_date_time": start_time.isoformat(),
                            "end_date_time": end_time.isoformat(),
                        },
                        blocking=True,
                        return_response=True,
                    )

                    calendar_events = response.get(calendar_id, {}).get("events", [])

                    _LOGGER.debug(
                        "[COORDINATOR] Fetched %d events from %s using get_events service",
                        len(calendar_events),
                        calendar_id,
                    )

                    # Process each event
                    for event_raw in calendar_events:
                        event_data = self._parse_event_from_service(
                            calendar_id,
                            event_raw,
                            now,
                        )

                        if event_data:
                            all_events.append(event_data)

                            # Check if event is currently active
                            if event_data.get("is_active"):
                                active_events.append(event_data)

                                # Log event change
                                prev_event = self._previous_active_events.get(calendar_id)
                                if not prev_event or prev_event.get("summary") != event_data.get("summary"):
                                    _LOGGER.info(
                                        "Active event on %s: %s",
                                        calendar_id,
                                        event_data.get("summary", "Unknown"),
                                    )

                                self._previous_active_events[calendar_id] = event_data

                    # If no active events, clear previous
                    if calendar_id not in [e["calendar_id"] for e in active_events if e["calendar_id"] == calendar_id]:
                        if calendar_id in self._previous_active_events:
                            _LOGGER.debug(
                                "Calendar %s no longer has active event",
                                calendar_id,
                            )
                            del self._previous_active_events[calendar_id]

                except Exception as service_err:
                    _LOGGER.warning(
                        "[COORDINATOR] Failed to use calendar.get_events for %s: %s - falling back to state method",
                        calendar_id,
                        service_err,
                    )

                    # Fallback to old method if service fails
                    if calendar_state.state == "on":
                        event_data = self._extract_event_from_state(
                            calendar_id,
                            calendar_state,
                            now,
                        )

                        if event_data:
                            all_events.append(event_data)
                            active_events.append(event_data)
                            self._previous_active_events[calendar_id] = event_data

            except Exception as err:
                _LOGGER.error(
                    "Error fetching events from %s: %s",
                    calendar_id,
                    err,
                )
                errors.append(f"Error on {calendar_id}: {err}")

        # Log summary
        _LOGGER.info(
            "[COORDINATOR] Calendar update complete | Total events: %d | Active events: %d | Errors: %d",
            len(all_events),
            len(active_events),
            len(errors),
        )

        # If all calendars failed, raise UpdateFailed
        if len(errors) == len(self.calendar_entities) and len(errors) > 0:
            raise UpdateFailed(f"All calendars failed: {errors}")

        return {
            "events": all_events,
            "active_events": active_events,
            "calendar_states": calendar_states,
            "errors": errors,
            "last_update": dt_util.utcnow(),
        }

    def _parse_event_from_service(
        self,
        calendar_id: str,
        event_raw: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any] | None:
        """
        Parse event data from calendar.get_events service response.

        Args:
            calendar_id: Calendar entity ID
            event_raw: Raw event dict from service
            now: Current timestamp

        Returns:
            Parsed event data dict or None if unable to parse
        """
        try:
            summary = event_raw.get("summary", "")
            start_str = event_raw.get("start")
            end_str = event_raw.get("end")

            if not summary:
                _LOGGER.warning(
                    "Event from %s has no summary, skipping",
                    calendar_id,
                )
                return None

            # Parse start/end times
            start_dt = dt_util.parse_datetime(start_str) if start_str else None
            end_dt = dt_util.parse_datetime(end_str) if end_str else None

            if not start_dt or not end_dt:
                _LOGGER.warning(
                    "Event '%s' from %s has invalid start/end times, skipping",
                    summary,
                    calendar_id,
                )
                return None

            # Determine if event is currently active
            is_active = start_dt <= now < end_dt

            event = {
                "calendar_id": calendar_id,
                "summary": summary,
                "start": start_str,
                "end": end_str,
                "description": event_raw.get("description", ""),
                "location": event_raw.get("location", ""),
                "is_active": is_active,
            }

            return event

        except Exception as err:
            _LOGGER.error(
                "Error parsing event from %s: %s",
                calendar_id,
                err,
            )
            return None

    def _extract_event_from_state(
        self,
        calendar_id: str,
        calendar_state: Any,
        now: datetime,
    ) -> dict[str, Any] | None:
        """
        Extract event data from calendar state (fallback method).

        Args:
            calendar_id: Calendar entity ID
            calendar_state: Calendar state object
            now: Current timestamp

        Returns:
            Event data dict or None if unable to extract
        """
        try:
            attributes = calendar_state.attributes

            # Extract event data
            event = {
                "calendar_id": calendar_id,
                "summary": attributes.get("message", ""),
                "start": attributes.get("start_time"),
                "end": attributes.get("end_time"),
                "description": attributes.get("description", ""),
                "location": attributes.get("location", ""),
                "is_active": True,  # State is "on", so event is active
            }

            # Validate we have minimum required data
            if not event["summary"]:
                _LOGGER.warning(
                    "Calendar %s has active event but no summary",
                    calendar_id,
                )
                event["summary"] = "Unnamed Event"

            return event

        except Exception as err:
            _LOGGER.error(
                "Error extracting event from %s: %s",
                calendar_id,
                err,
            )
            return None

    def get_active_events(self) -> list[dict[str, Any]]:
        """
        Get currently active events.

        Returns:
            List of active event dicts
        """
        if self.data is None:
            return []
        return self.data.get("active_events", [])

    def get_all_events(self) -> list[dict[str, Any]]:
        """
        Get all events (active + upcoming).

        Returns:
            List of all event dicts
        """
        if self.data is None:
            return []
        return self.data.get("events", [])

    def get_calendar_state(self, calendar_id: str) -> str | None:
        """
        Get state of a specific calendar.

        Args:
            calendar_id: Calendar entity ID

        Returns:
            Calendar state ('on', 'off', etc.) or None if not found
        """
        if self.data is None:
            return None
        calendar_states = self.data.get("calendar_states", {})
        return calendar_states.get(calendar_id)

    def is_any_calendar_active(self) -> bool:
        """
        Check if any monitored calendar has an active event.

        Returns:
            True if at least one calendar is active
        """
        active_events = self.get_active_events()
        return len(active_events) > 0

    def get_active_events_for_calendar(self, calendar_id: str) -> list[dict[str, Any]]:
        """
        Get active events for a specific calendar.

        Args:
            calendar_id: Calendar entity ID

        Returns:
            List of active events for this calendar
        """
        active_events = self.get_active_events()
        return [
            event for event in active_events
            if event.get("calendar_id") == calendar_id
        ]

    async def async_refresh_now(self) -> None:
        """Force immediate coordinator refresh."""
        _LOGGER.info("Forcing immediate refresh for all calendars")
        await self.async_request_refresh()


# Helper function to create coordinator
def create_multi_calendar_coordinator(
    hass: HomeAssistant,
    calendar_entities: list[str],
    update_interval: int = DEFAULT_UPDATE_INTERVAL,
) -> MultiCalendarCoordinator:
    """
    Create a multi-calendar coordinator instance.

    Args:
        hass: Home Assistant instance
        calendar_entities: List of calendar entity IDs
        update_interval: Update interval in seconds

    Returns:
        MultiCalendarCoordinator instance
    """
    return MultiCalendarCoordinator(
        hass=hass,
        calendar_entities=calendar_entities,
        update_interval=update_interval,
    )
