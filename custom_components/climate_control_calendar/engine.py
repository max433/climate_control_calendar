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
    ) -> list[tuple[dict[str, Any], list[str] | None, int]]:
        """
        Resolve slots for all active calendar events using binding manager.

        New architecture: Returns list of (slot, target_entities, priority) tuples.

        Args:
            active_events: List of active calendar events from coordinator
            available_slots: List of available slot configurations

        Returns:
            List of (slot, target_entities, priority) tuples for all matched bindings
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

        resolved_bindings = []

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

            # Resolve slot for this event via binding manager (returns tuple or None)
            result = self.binding_manager.resolve_slot_for_event(
                event=event,
                calendar_id=calendar_id,
                available_slots=available_slots,
            )

            if result:
                slot, target_entities, priority = result
                resolved_bindings.append((slot, target_entities, priority))
                _LOGGER.info(
                    "%s Event '%s' resolved to slot: %s (ID: %s), entities: %s, priority: %d",
                    LOG_PREFIX_ENGINE,
                    event_summary,
                    slot.get(SLOT_LABEL),
                    slot.get(SLOT_ID),
                    target_entities or "global",
                    priority,
                )
            else:
                if self.debug_mode:
                    _LOGGER.debug(
                        "%s No binding found for event '%s' from %s",
                        LOG_PREFIX_ENGINE,
                        event_summary,
                        calendar_id,
                    )

        return resolved_bindings

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
            # Normal slot resolution via bindings (New architecture)
            resolved_bindings = self.resolve_slots_for_active_events(
                active_events=active_events,
                available_slots=slots,
            )

            # New architecture: Apply ALL resolved bindings, not just first!
            # Bindings already sorted by priority in binding_manager
            if resolved_bindings:
                await self._apply_multiple_slots(
                    resolved_bindings=resolved_bindings,
                    climate_entities_pool=climate_entities,
                )

        # Note: Slot activation/deactivation tracking removed in new architecture
        # Multiple slots can be active simultaneously, tracked at entity level

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
            "bindings_applied": len(resolved_bindings) if not forced_slot_id else 0,
        }

    async def _apply_multiple_slots(
        self,
        resolved_bindings: list[tuple[dict[str, Any], list[str] | None, int]],
        climate_entities_pool: list[str],
    ) -> None:
        """
        Apply multiple slots with priority-based conflict resolution.

        New architecture: Multiple bindings can be active simultaneously.
        Priority determines which slot wins for entities with conflicts.

        Args:
            resolved_bindings: List of (slot, target_entities, priority) tuples
            climate_entities_pool: Global climate entities pool (fallback)
        """
        # Sort by priority DESC (higher priority wins conflicts)
        sorted_bindings = sorted(
            resolved_bindings,
            key=lambda x: x[2],  # x[2] = priority
            reverse=True,
        )

        # Track which entities have been applied (entity_id → slot_id)
        applied_entities: dict[str, str] = {}

        _LOGGER.info(
            "%s Applying %d bindings (sorted by priority)",
            LOG_PREFIX_ENGINE,
            len(sorted_bindings),
        )

        for slot, target_entities, priority in sorted_bindings:
            slot_id = slot.get("id")
            slot_label = slot.get("label")

            # Determine entities to apply to
            if target_entities is None:
                # Use global pool
                entities_for_this_binding = climate_entities_pool
            else:
                # Use specific entities from binding
                entities_for_this_binding = target_entities

            # Apply entity_overrides and excluded_entities from slot
            excluded = set(slot.get("excluded_entities", []))
            entity_overrides = slot.get("entity_overrides", {})

            # Filter out excluded entities
            entities_to_apply = [
                e for e in entities_for_this_binding
                if e not in excluded
            ]

            # Filter out entities already applied by higher priority binding
            entities_available = [
                e for e in entities_to_apply
                if e not in applied_entities
            ]

            if not entities_available:
                _LOGGER.debug(
                    "%s Slot '%s' (priority=%d): all entities already handled by higher priority",
                    LOG_PREFIX_ENGINE,
                    slot_label,
                    priority,
                )
                continue

            _LOGGER.info(
                "%s Applying slot '%s' (priority=%d) to %d entities: %s",
                LOG_PREFIX_ENGINE,
                slot_label,
                priority,
                len(entities_available),
                entities_available,
            )

            # Apply slot to available entities
            await self._apply_slot_to_entities(
                slot=slot,
                entities=entities_available,
                entity_overrides=entity_overrides,
            )

            # Mark entities as applied
            for entity_id in entities_available:
                applied_entities[entity_id] = slot_id

    async def _apply_slot_to_entities(
        self,
        slot: dict[str, Any],
        entities: list[str],
        entity_overrides: dict[str, dict[str, Any]],
    ) -> None:
        """
        Apply a slot to specific entities, respecting entity_overrides.

        Args:
            slot: Slot configuration
            entities: Entities to apply to
            entity_overrides: Entity-specific payload overrides
        """
        slot_id = slot.get("id")
        slot_label = slot.get("label")

        # Get default payload (support both old and new key names)
        default_payload = slot.get("default_climate_payload") or slot.get("climate_payload", {})

        # Group entities by payload (default vs override)
        entities_by_payload: dict[str, list[str]] = {}

        for entity_id in entities:
            if entity_id in entity_overrides:
                # Use override payload
                override_payload = entity_overrides[entity_id]
                payload_key = str(override_payload)  # Use str representation as key
                if payload_key not in entities_by_payload:
                    entities_by_payload[payload_key] = []
                entities_by_payload[payload_key].append(entity_id)
            else:
                # Use default payload
                payload_key = str(default_payload)
                if payload_key not in entities_by_payload:
                    entities_by_payload[payload_key] = []
                entities_by_payload[payload_key].append(entity_id)

        # Apply each unique payload to its entities
        for payload_str, entity_list in entities_by_payload.items():
            # Reconstruct payload from first entity in group
            if entity_list[0] in entity_overrides:
                payload = entity_overrides[entity_list[0]]
            else:
                payload = default_payload

            await self._apply_payload_to_entities(
                slot_id=slot_id,
                slot_label=slot_label,
                payload=payload,
                entities=entity_list,
            )

    async def _apply_payload_to_entities(
        self,
        slot_id: str,
        slot_label: str,
        payload: dict[str, Any],
        entities: list[str],
    ) -> None:
        """
        Apply a climate payload to a list of entities.

        Args:
            slot_id: Slot ID (for logging/events)
            slot_label: Slot label (for logging/events)
            payload: Climate payload to apply
            entities: Entities to apply to
        """
        # Check if application should be skipped (flags)
        if self.flag_manager and self.flag_manager.should_skip_application():
            flag_type = self.flag_manager.get_active_flag_type()
            _LOGGER.info(
                "%s Skipping climate application due to flag: %s",
                LOG_PREFIX_ENGINE,
                flag_type,
            )
            # Emit skip events
            for entity_id in entities:
                self.event_emitter.emit_climate_skipped(
                    climate_entity_id=entity_id,
                    slot_id=slot_id,
                    slot_label=slot_label,
                    reason=f"override_flag_{flag_type}",
                )
            return

        # Apply payload or dry run
        if self.dry_run:
            self._execute_dry_run(
                slot_id=slot_id,
                slot_label=slot_label,
                climate_payload=payload,
                climate_entities=entities,
            )
        else:
            if self.applier:
                await self._execute_application(
                    slot_id=slot_id,
                    slot_label=slot_label,
                    climate_payload=payload,
                    climate_entities=entities,
                )
            else:
                _LOGGER.warning(
                    "%s Applier not available, falling back to dry run logging",
                    LOG_PREFIX_ENGINE,
                )
                self._execute_dry_run(
                    slot_id=slot_id,
                    slot_label=slot_label,
                    climate_payload=payload,
                    climate_entities=entities,
                )

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
