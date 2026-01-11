"""Slot evaluation engine for Climate Control Calendar integration.

Decision D032: Event-to-Slot Binding System
This engine now resolves slots via event-to-slot bindings instead of time-based matching.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    SLOT_ID,
    SLOT_LABEL,
    SLOT_CLIMATE_PAYLOAD,
    FLAG_FORCE_SLOT,
    LOG_PREFIX_ENGINE,
    LOG_PREFIX_DRY_RUN,
)
from .events import EventEmitter

if TYPE_CHECKING:
    from .flag_manager import FlagManager
    from .applier import ClimatePayloadApplier
    from .binding_manager import BindingManager

_LOGGER = logging.getLogger(__name__)


class ClimateControlEngine:
    """
    Engine for evaluating calendar events and resolving slots via bindings.

    Responsibilities (Decision D032, D033):
    - Receive active events from multi-calendar coordinator
    - Resolve event → slot via BindingManager
    - Handle override flags (force_slot)
    - Apply climate payloads or execute dry run
    - Emit events on state changes
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        event_emitter: EventEmitter,
        binding_manager: "BindingManager | None" = None,
        flag_manager: "FlagManager | None" = None,
        applier: "ClimatePayloadApplier | None" = None,
        dry_run: bool = True,
        debug_mode: bool = False,
    ) -> None:
        """
        Initialize engine.

        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID
            event_emitter: Event emitter instance
            binding_manager: Binding manager for event-to-slot resolution
            flag_manager: Override flag manager (optional)
            applier: Climate payload applier (optional)
            dry_run: Dry run mode enabled
            debug_mode: Debug logging enabled
        """
        self.hass = hass
        self.entry_id = entry_id
        self.event_emitter = event_emitter
        self.binding_manager = binding_manager
        self.flag_manager = flag_manager
        self.applier = applier
        self.dry_run = dry_run
        self.debug_mode = debug_mode

        _LOGGER.info(
            "%s Engine initialized | Dry Run: %s | Debug: %s | Bindings: %s | Flags: %s | Applier: %s",
            LOG_PREFIX_ENGINE,
            self.dry_run,
            self.debug_mode,
            "enabled" if binding_manager else "disabled",
            "enabled" if flag_manager else "disabled",
            "enabled" if applier else "disabled",
        )

    def resolve_slots_for_active_events(
        self,
        active_events: list[dict[str, Any]],
        available_slots: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Resolve slots for all active calendar events using binding manager.

        Decision D032: Event-to-slot binding resolution.

        Args:
            active_events: List of active calendar events from coordinator
            available_slots: List of available slot configurations

        Returns:
            List of resolved slots (one per matching event)
        """
        if not self.binding_manager:
            _LOGGER.warning(
                "%s No binding manager available, cannot resolve slots",
                LOG_PREFIX_ENGINE,
            )
            return []

        if not active_events:
            if self.debug_mode:
                _LOGGER.debug(
                    "%s No active events, no slots to resolve",
                    LOG_PREFIX_ENGINE,
                )
            return []

        if self.debug_mode:
            _LOGGER.debug(
                "%s Resolving slots for %d active events",
                LOG_PREFIX_ENGINE,
                len(active_events),
            )

        resolved_slots = []

        for event in active_events:
            calendar_id = event.get("calendar_id")
            event_summary = event.get("summary", "Unknown")

            if self.debug_mode:
                _LOGGER.debug(
                    "%s Processing event: '%s' from %s",
                    LOG_PREFIX_ENGINE,
                    event_summary,
                    calendar_id,
                )

            # Resolve slot for this event via binding manager
            slot = self.binding_manager.resolve_slot_for_event(
                event=event,
                calendar_id=calendar_id,
                available_slots=available_slots,
            )

            if slot:
                resolved_slots.append(slot)
                _LOGGER.info(
                    "%s Event '%s' resolved to slot: %s (ID: %s)",
                    LOG_PREFIX_ENGINE,
                    event_summary,
                    slot.get(SLOT_LABEL),
                    slot.get(SLOT_ID),
                )
            else:
                if self.debug_mode:
                    _LOGGER.debug(
                        "%s No binding found for event '%s' from %s",
                        LOG_PREFIX_ENGINE,
                        event_summary,
                        calendar_id,
                    )

        return resolved_slots

    def _find_slot_by_id(
        self,
        slots: list[dict[str, Any]],
        slot_id: str,
    ) -> dict[str, Any] | None:
        """
        Find slot by ID.

        Args:
            slots: List of slot configurations
            slot_id: Slot ID to find

        Returns:
            Slot dict or None if not found
        """
        for slot in slots:
            if slot.get(SLOT_ID) == slot_id:
                return slot
        return None

    async def evaluate(
        self,
        active_events: list[dict[str, Any]],
        slots: list[dict[str, Any]],
        climate_entities: list[str],
    ) -> dict[str, Any]:
        """
        Evaluate active calendar events and resolve slots via bindings.

        This is the main entry point called by coordinator on each update.

        Decision D032: Changed from calendar_state to active_events.

        Args:
            active_events: List of currently active calendar events
            slots: List of configured slots
            climate_entities: List of climate entities to control

        Returns:
            Evaluation result with active slot info
        """
        if self.debug_mode:
            _LOGGER.debug(
                "%s === Engine Evaluation Start ===",
                LOG_PREFIX_ENGINE,
            )
            _LOGGER.debug(
                "%s Active events: %d | Slots: %d | Climate entities: %d",
                LOG_PREFIX_ENGINE,
                len(active_events),
                len(slots),
                len(climate_entities),
            )

        # Check flag expiration
        if self.flag_manager:
            await self.flag_manager.async_check_expiration()

        # Check for forced slot (takes precedence)
        forced_slot_id = None
        if self.flag_manager:
            forced_slot_id = self.flag_manager.get_forced_slot_id()

        active_slot = None

        if forced_slot_id:
            # Force slot active regardless of events/bindings
            active_slot = self._find_slot_by_id(slots, forced_slot_id)
            if active_slot:
                _LOGGER.info(
                    "%s Forcing slot: %s (ID: %s)",
                    LOG_PREFIX_ENGINE,
                    active_slot.get(SLOT_LABEL),
                    forced_slot_id,
                )
            else:
                _LOGGER.warning(
                    "%s Forced slot ID not found: %s",
                    LOG_PREFIX_ENGINE,
                    forced_slot_id,
                )
        else:
            # Normal slot resolution via bindings (Decision D032)
            resolved_slots = self.resolve_slots_for_active_events(
                active_events=active_events,
                available_slots=slots,
            )

            # If multiple events matched, take first resolved slot
            # TODO: Implement priority between events if needed
            if resolved_slots:
                active_slot = resolved_slots[0]
                if len(resolved_slots) > 1:
                    _LOGGER.info(
                        "%s Multiple events matched (%d), using first resolved slot: %s",
                        LOG_PREFIX_ENGINE,
                        len(resolved_slots),
                        active_slot.get(SLOT_LABEL),
                    )

        # Get previous active slot for change detection
        previous_slot_id = self.event_emitter.get_last_active_slot_id()
        current_slot_id = active_slot.get(SLOT_ID) if active_slot else None

        # Handle slot activation
        if active_slot and current_slot_id != previous_slot_id:
            await self._handle_slot_activation(active_slot, climate_entities)

        # Handle slot deactivation
        elif not active_slot and previous_slot_id is not None:
            self._handle_slot_deactivation(previous_slot_id)

        # No change - already logged by event emitter deduplication
        elif active_slot and current_slot_id == previous_slot_id:
            if self.debug_mode:
                _LOGGER.debug(
                    "%s Slot unchanged: %s",
                    LOG_PREFIX_ENGINE,
                    active_slot.get(SLOT_LABEL),
                )

        if self.debug_mode:
            _LOGGER.debug(
                "%s === Engine Evaluation End ===",
                LOG_PREFIX_ENGINE,
            )

        return {
            "active_slot": active_slot,
            "active_slot_id": current_slot_id,
            "previous_slot_id": previous_slot_id,
            "changed": current_slot_id != previous_slot_id,
            "forced": forced_slot_id is not None,
            "active_events_count": len(active_events),
        }

    async def _handle_slot_activation(
        self,
        slot: dict[str, Any],
        climate_entities: list[str],
    ) -> None:
        """
        Handle slot activation (emit events, apply payload).

        Decision D034: Slots no longer contain time_start/time_end.

        Args:
            slot: Activated slot configuration
            climate_entities: List of climate entities
        """
        slot_id = slot[SLOT_ID]
        slot_label = slot[SLOT_LABEL]
        climate_payload = slot.get(SLOT_CLIMATE_PAYLOAD, {})

        # Emit slot activation event (handles deduplication)
        # Note: time_start/time_end removed (Decision D034)
        self.event_emitter.emit_slot_activated(
            slot_id=slot_id,
            slot_label=slot_label,
            time_start="N/A",  # No longer in slot definition
            time_end="N/A",    # No longer in slot definition
            climate_payload=climate_payload,
        )

        # Check if application should be skipped (D019)
        if self.flag_manager and self.flag_manager.should_skip_application():
            flag_type = self.flag_manager.get_active_flag_type()
            _LOGGER.info(
                "%s Skipping climate application due to flag: %s",
                LOG_PREFIX_ENGINE,
                flag_type,
            )

            # Emit skip events for each entity
            for entity_id in climate_entities:
                self.event_emitter.emit_climate_skipped(
                    climate_entity_id=entity_id,
                    slot_id=slot_id,
                    slot_label=slot_label,
                    reason=f"override_flag_{flag_type}",
                )
            return

        # Apply payload or dry run
        if self.dry_run:
            # Dry run mode
            self._execute_dry_run(
                slot_id=slot_id,
                slot_label=slot_label,
                climate_payload=climate_payload,
                climate_entities=climate_entities,
            )
        else:
            # Real application (M3)
            if self.applier:
                await self._execute_application(
                    slot_id=slot_id,
                    slot_label=slot_label,
                    climate_payload=climate_payload,
                    climate_entities=climate_entities,
                )
            else:
                _LOGGER.warning(
                    "%s Applier not available, falling back to dry run logging",
                    LOG_PREFIX_ENGINE,
                )
                self._execute_dry_run(
                    slot_id=slot_id,
                    slot_label=slot_label,
                    climate_payload=climate_payload,
                    climate_entities=climate_entities,
                )

    def _handle_slot_deactivation(self, previous_slot_id: str) -> None:
        """
        Handle slot deactivation.

        Args:
            previous_slot_id: Previously active slot ID
        """
        # Note: We don't have slot label here, just ID
        # In real scenario, would look up from config
        self.event_emitter.emit_slot_deactivated(
            slot_id=previous_slot_id,
            slot_label=f"Slot {previous_slot_id}",
            reason="time_window_ended",
        )

    async def _execute_application(
        self,
        slot_id: str,
        slot_label: str,
        climate_payload: dict[str, Any],
        climate_entities: list[str],
    ) -> None:
        """
        Execute real climate payload application.

        Args:
            slot_id: Source slot ID
            slot_label: Source slot label
            climate_payload: Climate settings
            climate_entities: Target climate entities
        """
        if not climate_entities:
            _LOGGER.warning(
                "%s No climate entities configured, nothing to apply",
                LOG_PREFIX_ENGINE,
            )
            return

        if not climate_payload:
            _LOGGER.warning(
                "%s Slot has empty climate payload, nothing to apply",
                LOG_PREFIX_ENGINE,
            )
            return

        _LOGGER.info(
            "%s Applying payload from slot '%s' to %d devices",
            LOG_PREFIX_ENGINE,
            slot_label,
            len(climate_entities),
        )

        # Call applier
        result = await self.applier.apply_to_devices(
            climate_entities=climate_entities,
            payload=climate_payload,
            slot_id=slot_id,
            slot_label=slot_label,
        )

        _LOGGER.info(
            "%s Application result: %d/%d succeeded",
            LOG_PREFIX_ENGINE,
            result["succeeded"],
            result["total"],
        )

    def _execute_dry_run(
        self,
        slot_id: str,
        slot_label: str,
        climate_payload: dict[str, Any],
        climate_entities: list[str],
    ) -> None:
        """
        Execute dry run simulation (log what would happen).

        Args:
            slot_id: Source slot ID
            slot_label: Source slot label
            climate_payload: Climate settings
            climate_entities: Target climate entities
        """
        _LOGGER.warning(
            "%s === DRY RUN MODE ACTIVE ===",
            LOG_PREFIX_DRY_RUN,
        )

        if not climate_entities:
            _LOGGER.warning(
                "%s No climate entities configured, nothing to apply",
                LOG_PREFIX_DRY_RUN,
            )
            return

        if not climate_payload:
            _LOGGER.warning(
                "%s Slot has empty climate payload, nothing to apply",
                LOG_PREFIX_DRY_RUN,
            )
            return

        _LOGGER.warning(
            "%s Slot activated: %s (ID: %s)",
            LOG_PREFIX_DRY_RUN,
            slot_label,
            slot_id,
        )

        _LOGGER.warning(
            "%s Climate payload: %s",
            LOG_PREFIX_DRY_RUN,
            climate_payload,
        )

        for entity_id in climate_entities:
            # Emit dry run event
            self.event_emitter.emit_dry_run_executed(
                slot_id=slot_id,
                slot_label=slot_label,
                climate_entity_id=entity_id,
                payload=climate_payload,
            )

        _LOGGER.warning(
            "%s Would apply to %d climate entities: %s",
            LOG_PREFIX_DRY_RUN,
            len(climate_entities),
            climate_entities,
        )

        _LOGGER.warning(
            "%s === END DRY RUN ===",
            LOG_PREFIX_DRY_RUN,
        )

    def set_dry_run(self, enabled: bool) -> None:
        """
        Update dry run mode at runtime.

        Args:
            enabled: Enable or disable dry run
        """
        old_value = self.dry_run
        self.dry_run = enabled

        _LOGGER.info(
            "%s Dry run mode changed: %s → %s",
            LOG_PREFIX_ENGINE,
            old_value,
            enabled,
        )

    def set_debug_mode(self, enabled: bool) -> None:
        """
        Update debug mode at runtime.

        Args:
            enabled: Enable or disable debug logging
        """
        old_value = self.debug_mode
        self.debug_mode = enabled

        _LOGGER.info(
            "%s Debug mode changed: %s → %s",
            LOG_PREFIX_ENGINE,
            old_value,
            enabled,
        )
