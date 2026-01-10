"""Slot evaluation engine for Climate Control Calendar integration."""
from datetime import datetime, time
import logging
from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_DRY_RUN,
    CONF_DEBUG_MODE,
    SLOT_ID,
    SLOT_LABEL,
    SLOT_TIME_START,
    SLOT_TIME_END,
    SLOT_DAYS,
    SLOT_CLIMATE_PAYLOAD,
    DAYS_OF_WEEK,
    FLAG_FORCE_SLOT,
    LOG_PREFIX_ENGINE,
    LOG_PREFIX_DRY_RUN,
)
from .events import EventEmitter
from .helpers import parse_time_string, get_current_day_name

if TYPE_CHECKING:
    from .flag_manager import FlagManager
    from .applier import ClimatePayloadApplier

_LOGGER = logging.getLogger(__name__)


class ClimateControlEngine:
    """
    Engine for evaluating calendar state and time slots.

    Responsibilities:
    - Resolve active calendar state
    - Resolve active time slot (or forced slot)
    - Handle override flags
    - Apply climate payloads or execute dry run
    - Emit events on state changes
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        event_emitter: EventEmitter,
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
            flag_manager: Override flag manager (optional for M2 compatibility)
            applier: Climate payload applier (optional for M2 compatibility)
            dry_run: Dry run mode enabled
            debug_mode: Debug logging enabled
        """
        self.hass = hass
        self.entry_id = entry_id
        self.event_emitter = event_emitter
        self.flag_manager = flag_manager
        self.applier = applier
        self.dry_run = dry_run
        self.debug_mode = debug_mode

        _LOGGER.info(
            "%s Engine initialized | Dry Run: %s | Debug: %s | Flags: %s | Applier: %s",
            LOG_PREFIX_ENGINE,
            self.dry_run,
            self.debug_mode,
            "enabled" if flag_manager else "disabled",
            "enabled" if applier else "disabled",
        )

    def _is_time_in_slot(
        self,
        current_time: time,
        current_day: str,
        slot: dict[str, Any],
    ) -> bool:
        """
        Check if current time and day match slot definition.

        Args:
            current_time: Current time
            current_day: Current day name (lowercase)
            slot: Slot configuration

        Returns:
            True if current time/day is within slot, False otherwise
        """
        # Check day of week
        slot_days = slot.get(SLOT_DAYS, DAYS_OF_WEEK)  # Default all days
        if current_day not in slot_days:
            return False

        # Parse slot time boundaries
        try:
            slot_start = parse_time_string(slot[SLOT_TIME_START])
            slot_end = parse_time_string(slot[SLOT_TIME_END])
        except (ValueError, KeyError) as err:
            _LOGGER.error(
                "%s Invalid slot time configuration: %s | Error: %s",
                LOG_PREFIX_ENGINE,
                slot.get(SLOT_LABEL, "Unknown"),
                err,
            )
            return False

        # Handle overnight slots (e.g., 23:00 - 02:00)
        if slot_start <= slot_end:
            # Normal slot within same day
            return slot_start <= current_time < slot_end
        else:
            # Overnight slot spans midnight
            return current_time >= slot_start or current_time < slot_end

    def resolve_active_slot(
        self,
        calendar_state: str | None,
        slots: list[dict[str, Any]],
        current_time: time | None = None,
        current_day: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Resolve which slot is currently active.

        Decision D010: Slots are active only when calendar is ON.

        Args:
            calendar_state: Calendar entity state ('on', 'off', etc.)
            slots: List of slot configurations
            current_time: Override current time (for testing)
            current_day: Override current day (for testing)

        Returns:
            Active slot dict or None if no slot active
        """
        # Calendar must be ON for any slot to activate (Decision D010)
        if calendar_state != "on":
            if self.debug_mode:
                _LOGGER.debug(
                    "%s Calendar not active (state: %s), no slot can activate",
                    LOG_PREFIX_ENGINE,
                    calendar_state,
                )
            return None

        # Get current time and day
        now = datetime.now()
        current_time = current_time or now.time()
        current_day = current_day or get_current_day_name()

        if self.debug_mode:
            _LOGGER.debug(
                "%s Evaluating slots | Time: %s | Day: %s | Slots count: %d",
                LOG_PREFIX_ENGINE,
                current_time.strftime("%H:%M"),
                current_day,
                len(slots),
            )

        # Find matching slot
        for slot in slots:
            if self._is_time_in_slot(current_time, current_day, slot):
                slot_label = slot.get(SLOT_LABEL, "Unknown")
                slot_id = slot.get(SLOT_ID)

                _LOGGER.info(
                    "%s Active slot found: %s (ID: %s)",
                    LOG_PREFIX_ENGINE,
                    slot_label,
                    slot_id,
                )

                return slot

        if self.debug_mode:
            _LOGGER.debug(
                "%s No matching slot for current time/day",
                LOG_PREFIX_ENGINE,
            )

        return None

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
        calendar_state: str | None,
        slots: list[dict[str, Any]],
        climate_entities: list[str],
    ) -> dict[str, Any]:
        """
        Evaluate current state and emit appropriate events.

        This is the main entry point called by coordinator on each update.

        Args:
            calendar_state: Current calendar state
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
                "%s Calendar: %s | Slots: %d | Climate entities: %d",
                LOG_PREFIX_ENGINE,
                calendar_state,
                len(slots),
                len(climate_entities),
            )

        # Check flag expiration (D020)
        if self.flag_manager:
            await self.flag_manager.async_check_expiration()

        # Check for forced slot (takes precedence)
        forced_slot_id = None
        if self.flag_manager:
            forced_slot_id = self.flag_manager.get_forced_slot_id()

        active_slot = None

        if forced_slot_id:
            # Force slot active regardless of time/calendar
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
            # Normal slot resolution
            active_slot = self.resolve_active_slot(calendar_state, slots)

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
        }

    async def _handle_slot_activation(
        self,
        slot: dict[str, Any],
        climate_entities: list[str],
    ) -> None:
        """
        Handle slot activation (emit events, apply payload).

        Args:
            slot: Activated slot configuration
            climate_entities: List of climate entities
        """
        slot_id = slot[SLOT_ID]
        slot_label = slot[SLOT_LABEL]
        time_start = slot[SLOT_TIME_START]
        time_end = slot[SLOT_TIME_END]
        climate_payload = slot.get(SLOT_CLIMATE_PAYLOAD, {})

        # Emit slot activation event (handles deduplication)
        self.event_emitter.emit_slot_activated(
            slot_id=slot_id,
            slot_label=slot_label,
            time_start=time_start,
            time_end=time_end,
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
