"""Event emission system for Climate Control Calendar integration."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_CALENDAR_CHANGED,
    EVENT_SLOT_ACTIVATED,
    EVENT_SLOT_DEACTIVATED,
    EVENT_CLIMATE_APPLIED,
    EVENT_CLIMATE_SKIPPED,
    EVENT_DRY_RUN_EXECUTED,
    EVENT_FLAG_SET,
    EVENT_FLAG_CLEARED,
)

_LOGGER = logging.getLogger(__name__)


class EventEmitter:
    """Handles event emission for Climate Control Calendar."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """
        Initialize event emitter.

        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID for this integration instance
        """
        self.hass = hass
        self.entry_id = entry_id
        self._last_active_slot_id: str | None = None

    def _emit_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """
        Emit Home Assistant event with base metadata.

        Args:
            event_type: Event type constant
            event_data: Event-specific data
        """
        # Add base metadata
        full_event_data = {
            "entry_id": self.entry_id,
            "timestamp": dt_util.utcnow().isoformat(),
            **event_data,
        }

        self.hass.bus.fire(event_type, full_event_data)

        _LOGGER.debug(
            "Event emitted: %s | Data: %s",
            event_type,
            full_event_data,
        )

    def emit_calendar_changed(
        self,
        calendar_entity_id: str,
        old_state: str | None,
        new_state: str,
        event_summary: str | None = None,
    ) -> None:
        """
        Emit calendar state change event.

        Args:
            calendar_entity_id: Calendar entity ID
            old_state: Previous state
            new_state: New state
            event_summary: Calendar event summary if applicable
        """
        self._emit_event(
            EVENT_CALENDAR_CHANGED,
            {
                "calendar_entity_id": calendar_entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "event_summary": event_summary,
            },
        )

    def emit_slot_activated(
        self,
        slot_id: str,
        slot_label: str,
        time_start: str,
        time_end: str,
        climate_payload: dict[str, Any],
    ) -> None:
        """
        Emit slot activation event (only on transition).

        Args:
            slot_id: Slot ID
            slot_label: Human-readable slot label
            time_start: Slot start time (HH:MM)
            time_end: Slot end time (HH:MM)
            climate_payload: Climate settings to apply
        """
        # Check if this is a new activation (deduplication)
        if self._last_active_slot_id == slot_id:
            _LOGGER.debug(
                "Slot %s (%s) still active, skipping duplicate activation event",
                slot_id,
                slot_label,
            )
            return

        self._last_active_slot_id = slot_id

        self._emit_event(
            EVENT_SLOT_ACTIVATED,
            {
                "slot_id": slot_id,
                "slot_label": slot_label,
                "time_start": time_start,
                "time_end": time_end,
                "climate_payload": climate_payload,
            },
        )

        _LOGGER.info(
            "Slot activated: %s (%s - %s) | Payload: %s",
            slot_label,
            time_start,
            time_end,
            climate_payload,
        )

    def emit_slot_deactivated(
        self,
        slot_id: str,
        slot_label: str,
        reason: str = "time_window_ended",
    ) -> None:
        """
        Emit slot deactivation event.

        Args:
            slot_id: Slot ID
            slot_label: Human-readable slot label
            reason: Reason for deactivation
        """
        # Only emit if there was an active slot
        if self._last_active_slot_id is None:
            return

        self._last_active_slot_id = None

        self._emit_event(
            EVENT_SLOT_DEACTIVATED,
            {
                "slot_id": slot_id,
                "slot_label": slot_label,
                "reason": reason,
            },
        )

        _LOGGER.info(
            "Slot deactivated: %s | Reason: %s",
            slot_label,
            reason,
        )

    def emit_climate_applied(
        self,
        climate_entity_id: str,
        slot_id: str,
        slot_label: str,
        payload: dict[str, Any],
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """
        Emit climate payload application event.

        Args:
            climate_entity_id: Target climate entity
            slot_id: Source slot ID
            slot_label: Source slot label
            payload: Applied climate payload
            success: Whether application succeeded
            error: Error message if failed
        """
        self._emit_event(
            EVENT_CLIMATE_APPLIED,
            {
                "climate_entity_id": climate_entity_id,
                "slot_id": slot_id,
                "slot_label": slot_label,
                "payload": payload,
                "success": success,
                "error": error,
            },
        )

        if success:
            _LOGGER.info(
                "Climate payload applied: %s → %s",
                climate_entity_id,
                payload,
            )
        else:
            _LOGGER.error(
                "Climate payload failed: %s → %s | Error: %s",
                climate_entity_id,
                payload,
                error,
            )

    def emit_climate_skipped(
        self,
        climate_entity_id: str,
        slot_id: str,
        slot_label: str,
        reason: str,
    ) -> None:
        """
        Emit climate application skipped event.

        Args:
            climate_entity_id: Target climate entity
            slot_id: Source slot ID
            slot_label: Source slot label
            reason: Reason for skipping
        """
        self._emit_event(
            EVENT_CLIMATE_SKIPPED,
            {
                "climate_entity_id": climate_entity_id,
                "slot_id": slot_id,
                "slot_label": slot_label,
                "reason": reason,
            },
        )

        _LOGGER.info(
            "Climate application skipped: %s | Reason: %s",
            climate_entity_id,
            reason,
        )

    def emit_dry_run_executed(
        self,
        slot_id: str,
        slot_label: str,
        climate_entity_id: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Emit dry run execution event.

        Args:
            slot_id: Source slot ID
            slot_label: Source slot label
            climate_entity_id: Target climate entity
            payload: Payload that would be applied
        """
        self._emit_event(
            EVENT_DRY_RUN_EXECUTED,
            {
                "slot_id": slot_id,
                "slot_label": slot_label,
                "climate_entity_id": climate_entity_id,
                "payload": payload,
            },
        )

        _LOGGER.warning(
            "[DRY RUN] Would apply to %s: %s (from slot: %s)",
            climate_entity_id,
            payload,
            slot_label,
        )

    def emit_flag_set(
        self,
        flag_type: str,
        target_slot_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit override flag set event.

        Args:
            flag_type: Flag type (skip_until_next_slot, skip_today, force_slot)
            target_slot_id: Target slot ID if applicable
            metadata: Additional flag metadata
        """
        self._emit_event(
            EVENT_FLAG_SET,
            {
                "flag_type": flag_type,
                "target_slot_id": target_slot_id,
                "metadata": metadata or {},
            },
        )

        _LOGGER.info(
            "Override flag set: %s | Target: %s",
            flag_type,
            target_slot_id or "N/A",
        )

    def emit_flag_cleared(
        self,
        flag_type: str,
        reason: str = "manual_clear",
    ) -> None:
        """
        Emit override flag cleared event.

        Args:
            flag_type: Flag type cleared
            reason: Reason for clearing
        """
        self._emit_event(
            EVENT_FLAG_CLEARED,
            {
                "flag_type": flag_type,
                "reason": reason,
            },
        )

        _LOGGER.info(
            "Override flag cleared: %s | Reason: %s",
            flag_type,
            reason,
        )

    def reset_deduplication(self) -> None:
        """Reset internal deduplication state (useful for testing)."""
        self._last_active_slot_id = None

    def get_last_active_slot_id(self) -> str | None:
        """
        Get last active slot ID (for engine state tracking).

        Returns:
            Last active slot ID or None
        """
        return self._last_active_slot_id
