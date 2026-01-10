"""Override flag manager for Climate Control Calendar integration."""
from datetime import datetime, time
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    FLAG_SKIP_UNTIL_NEXT_SLOT,
    FLAG_SKIP_TODAY,
    FLAG_FORCE_SLOT,
    STORAGE_VERSION,
)
from .events import EventEmitter

_LOGGER = logging.getLogger(__name__)

# Storage constants
STORAGE_FLAG_TYPE = "flag_type"
STORAGE_SLOT_ID = "slot_id"
STORAGE_SET_AT = "set_at"


class FlagManager:
    """
    Manages override flags with persistence.

    Decisions:
    - D018: HA Storage for persistence
    - D019: Mutual exclusion (one flag at a time)
    - D020: Smart auto-clear based on flag type
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        event_emitter: EventEmitter,
    ) -> None:
        """
        Initialize flag manager.

        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID
            event_emitter: Event emitter instance
        """
        self.hass = hass
        self.entry_id = entry_id
        self.event_emitter = event_emitter

        # Storage
        self._store = Store(
            hass,
            version=STORAGE_VERSION,
            key=f"{DOMAIN}_{entry_id}_flags",
        )

        # Current active flag (loaded from storage)
        self._active_flag: dict[str, Any] | None = None

    async def async_load(self) -> None:
        """Load flags from storage."""
        data = await self._store.async_load()

        if data:
            self._active_flag = data
            _LOGGER.info(
                "Loaded flag from storage: %s",
                self._active_flag.get(STORAGE_FLAG_TYPE),
            )
        else:
            self._active_flag = None
            _LOGGER.debug("No stored flags found")

    async def async_save(self) -> None:
        """Save current flag to storage."""
        await self._store.async_save(self._active_flag)

    async def async_set_flag(
        self,
        flag_type: str,
        slot_id: str | None = None,
    ) -> None:
        """
        Set an override flag.

        Decision D019: Mutual exclusion - clears existing flag first.

        Args:
            flag_type: Type of flag (skip_today, skip_until_next_slot, force_slot)
            slot_id: Target slot ID (required for force_slot)

        Raises:
            ValueError: If force_slot without slot_id
        """
        # Validate force_slot has slot_id
        if flag_type == FLAG_FORCE_SLOT and not slot_id:
            raise ValueError(f"Flag type '{FLAG_FORCE_SLOT}' requires slot_id parameter")

        # Clear existing flag (mutual exclusion - D019)
        if self._active_flag:
            old_flag_type = self._active_flag.get(STORAGE_FLAG_TYPE)
            _LOGGER.info(
                "Clearing existing flag '%s' due to mutual exclusion",
                old_flag_type,
            )

        # Set new flag
        self._active_flag = {
            STORAGE_FLAG_TYPE: flag_type,
            STORAGE_SLOT_ID: slot_id,
            STORAGE_SET_AT: datetime.now().isoformat(),
        }

        # Persist
        await self.async_save()

        # Emit event
        self.event_emitter.emit_flag_set(
            flag_type=flag_type,
            target_slot_id=slot_id,
            metadata={"set_at": self._active_flag[STORAGE_SET_AT]},
        )

        _LOGGER.info(
            "Flag set: %s%s",
            flag_type,
            f" (slot_id: {slot_id})" if slot_id else "",
        )

    async def async_clear_flag(self, reason: str = "manual_clear") -> None:
        """
        Clear active flag.

        Args:
            reason: Reason for clearing (manual_clear, expired, etc.)
        """
        if not self._active_flag:
            _LOGGER.debug("No active flag to clear")
            return

        flag_type = self._active_flag.get(STORAGE_FLAG_TYPE)

        # Clear flag
        self._active_flag = None

        # Persist
        await self.async_save()

        # Emit event
        self.event_emitter.emit_flag_cleared(
            flag_type=flag_type,
            reason=reason,
        )

        _LOGGER.info("Flag cleared: %s (reason: %s)", flag_type, reason)

    async def async_check_expiration(
        self,
        current_slot_id: str | None = None,
    ) -> None:
        """
        Check if active flag should auto-expire.

        Decision D020: Smart auto-clear based on flag type.

        Args:
            current_slot_id: Currently active slot ID (for skip_until_next_slot)
        """
        if not self._active_flag:
            return

        flag_type = self._active_flag.get(STORAGE_FLAG_TYPE)

        # Check skip_today expiration (midnight)
        if flag_type == FLAG_SKIP_TODAY:
            now = datetime.now()
            if now.time() < time(0, 1):  # Within first minute of new day
                _LOGGER.info("skip_today expired (new day started)")
                await self.async_clear_flag(reason="expired_new_day")
                return

        # Check skip_until_next_slot expiration (slot changed)
        if flag_type == FLAG_SKIP_UNTIL_NEXT_SLOT:
            if current_slot_id is not None:
                _LOGGER.info(
                    "skip_until_next_slot expired (new slot activated: %s)",
                    current_slot_id,
                )
                await self.async_clear_flag(reason="expired_next_slot")
                return

        # force_slot does not auto-expire (Decision D020)

    def get_active_flag(self) -> dict[str, Any] | None:
        """
        Get currently active flag.

        Returns:
            Active flag dict or None
        """
        return self._active_flag

    def get_active_flag_type(self) -> str | None:
        """
        Get active flag type.

        Returns:
            Flag type string or None
        """
        if self._active_flag:
            return self._active_flag.get(STORAGE_FLAG_TYPE)
        return None

    def should_skip_application(self) -> bool:
        """
        Check if current flag indicates skipping climate application.

        Returns:
            True if should skip, False otherwise
        """
        flag_type = self.get_active_flag_type()
        return flag_type in [FLAG_SKIP_TODAY, FLAG_SKIP_UNTIL_NEXT_SLOT]

    def get_forced_slot_id(self) -> str | None:
        """
        Get forced slot ID if force_slot flag is active.

        Returns:
            Slot ID if force_slot active, None otherwise
        """
        if self.get_active_flag_type() == FLAG_FORCE_SLOT:
            return self._active_flag.get(STORAGE_SLOT_ID)
        return None

    def has_active_flag(self) -> bool:
        """
        Check if any flag is active.

        Returns:
            True if flag active, False otherwise
        """
        return self._active_flag is not None
