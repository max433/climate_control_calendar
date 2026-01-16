"""Event emission system for Climate Control Calendar integration."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_CALENDAR_CHANGED,
    EVENT_SLOT_ACTIVATED,
    EVENT_SLOT_DEACTIVATED,
    EVENT_CLIMATE_APPLIED,
    EVENT_DRY_RUN_EXECUTED,
    EVENT_BINDING_MATCHED,
    EVENT_EVALUATION_COMPLETE,
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

    def emit_binding_matched(
        self,
        binding_id: str,
        event_summary: str,
        calendar_id: str,
        slot_id: str,
        slot_label: str,
        match_type: str,
        match_value: str,
        priority: int,
        target_entities: list[str] | None = None,
    ) -> None:
        """
        Emit binding matched event (when calendar event matches binding pattern).

        Args:
            binding_id: Binding ID that matched
            event_summary: Calendar event summary
            calendar_id: Source calendar entity ID
            slot_id: Target slot ID
            slot_label: Target slot label
            match_type: Match type (summary, summary_contains, regex)
            match_value: Match pattern value
            priority: Binding priority
            target_entities: Specific target entities (None = global pool)
        """
        self._emit_event(
            EVENT_BINDING_MATCHED,
            {
                "binding_id": binding_id,
                "event_summary": event_summary,
                "calendar_id": calendar_id,
                "slot_id": slot_id,
                "slot_label": slot_label,
                "match_type": match_type,
                "match_value": match_value,
                "priority": priority,
                "target_entities": target_entities or "global_pool",
            },
        )

        _LOGGER.info(
            "Binding matched: '%s' → Slot '%s' | Event: '%s' from %s | Priority: %d",
            match_value,
            slot_label,
            event_summary,
            calendar_id,
            priority,
        )

    def emit_evaluation_complete(
        self,
        active_events_count: int,
        bindings_matched: int,
        entities_applied: int,
        forced_slot_id: str | None = None,
        dry_run: bool = True,
        debug_mode: bool = False,
    ) -> None:
        """
        Emit evaluation complete event (summary of evaluation cycle).

        Args:
            active_events_count: Number of active calendar events processed
            bindings_matched: Number of bindings that matched
            entities_applied: Number of entities that had payloads applied
            forced_slot_id: Forced slot ID if force_slot flag active
            dry_run: Dry run mode status
            debug_mode: Debug mode status
        """
        self._emit_event(
            EVENT_EVALUATION_COMPLETE,
            {
                "active_events_count": active_events_count,
                "bindings_matched": bindings_matched,
                "entities_applied": entities_applied,
                "forced_slot_id": forced_slot_id,
                "forced": forced_slot_id is not None,
                "dry_run": dry_run,
                "debug_mode": debug_mode,
            },
        )

        _LOGGER.info(
            "Evaluation complete: %d events → %d bindings matched → %d entities | Forced: %s | Dry run: %s",
            active_events_count,
            bindings_matched,
            entities_applied,
            forced_slot_id or "No",
            "Yes" if dry_run else "No",
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
