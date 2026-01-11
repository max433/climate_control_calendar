"""Binding manager for event-to-slot resolution.

This module manages the bindings between calendar events and climate slots.
It handles priority-based conflict resolution when multiple bindings match
the same event.

Decision D032: Event-to-Slot Binding System
Decision D033: Multi-Calendar Support
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .event_matcher import EventMatcher, matches_calendar

_LOGGER = logging.getLogger(__name__)


class BindingManager:
    """
    Manages event-to-slot bindings with priority resolution.

    Responsibilities:
    - Load/save bindings from/to config entry options
    - Add/remove bindings
    - Resolve which slot to use for a given event
    - Handle priority-based conflict resolution
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """
        Initialize binding manager.

        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID
        """
        self.hass = hass
        self.entry_id = entry_id
        self._bindings: list[dict[str, Any]] = []

    async def async_load(self, bindings: list[dict[str, Any]] | None = None) -> None:
        """
        Load bindings from config entry options or provided list.

        Args:
            bindings: Optional bindings list (if None, loads from config entry)
        """
        if bindings is not None:
            self._bindings = bindings
            _LOGGER.debug("Loaded %d bindings from provided list", len(self._bindings))
            return

        # Load from config entry
        from homeassistant.config_entries import ConfigEntry

        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not entry:
            _LOGGER.warning("Config entry not found: %s", self.entry_id)
            self._bindings = []
            return

        self._bindings = entry.options.get("bindings", [])
        _LOGGER.info("Loaded %d bindings from config entry", len(self._bindings))

    def get_all_bindings(self) -> list[dict[str, Any]]:
        """
        Get all bindings.

        Returns:
            List of binding configurations
        """
        return self._bindings.copy()

    def resolve_slot_for_event(
        self,
        event: dict[str, Any],
        calendar_id: str,
        available_slots: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Resolve which slot to use for a given calendar event.

        Resolution algorithm (Decision D032):
        1. Filter bindings that match the calendar
        2. Filter bindings that match the event
        3. Sort by priority (DESC)
        4. At same priority, last defined wins
        5. Return the winning slot

        Args:
            event: Calendar event with 'summary' and other attributes
            calendar_id: Calendar entity ID
            available_slots: List of available slot configurations

        Returns:
            Matched slot or None if no binding matches

        Example:
            >>> event = {"summary": "Morning"}
            >>> calendar_id = "calendar.work"
            >>> available_slots = [{"id": "slot1", "label": "Comfort"}]
            >>> binding_manager.resolve_slot_for_event(event, calendar_id, available_slots)
            {"id": "slot1", "label": "Comfort", ...}
        """
        # Step 1: Filter bindings for this calendar
        calendar_bindings = [
            b for b in self._bindings
            if matches_calendar(b.get("calendars", []), calendar_id)
        ]

        if not calendar_bindings:
            _LOGGER.debug(
                "No bindings found for calendar: %s",
                calendar_id,
            )
            return None

        # Step 2: Filter bindings that match this event
        matching_bindings = []
        for binding in calendar_bindings:
            match_config = binding.get("match", {})
            if EventMatcher.matches(match_config, event):
                matching_bindings.append(binding)

        if not matching_bindings:
            _LOGGER.debug(
                "No matching bindings for event '%s' on calendar %s",
                event.get("summary", "Unknown"),
                calendar_id,
            )
            return None

        # Step 3: Sort by priority DESC
        # Python's sort is stable, so equal priorities maintain insertion order
        # To make "last defined wins", we rely on stable sort
        sorted_bindings = sorted(
            matching_bindings,
            key=lambda b: b.get("priority", 0),
            reverse=True,
        )

        # Step 4: Take first (highest priority, or last inserted if tie)
        winner = sorted_bindings[0]
        slot_id = winner.get("slot_id")

        _LOGGER.info(
            "Event '%s' on %s matched binding (priority=%d) -> slot_id=%s",
            event.get("summary", "Unknown"),
            calendar_id,
            winner.get("priority", 0),
            slot_id,
        )

        # Step 5: Find and return the slot
        slot = self._find_slot_by_id(available_slots, slot_id)
        if not slot:
            _LOGGER.warning(
                "Binding references non-existent slot ID: %s",
                slot_id,
            )
            return None

        return slot

    @staticmethod
    def _find_slot_by_id(
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
            if slot.get("id") == slot_id:
                return slot
        return None

    async def async_add_binding(
        self,
        calendars: str | list[str],
        match_config: dict[str, Any],
        slot_id: str,
        priority: int = 0,
    ) -> str:
        """
        Add a new binding.

        Args:
            calendars: Calendar filter ("*" or list of calendar IDs)
            match_config: Match configuration (type, value)
            slot_id: Target slot ID
            priority: Binding priority (higher = more important)

        Returns:
            Generated binding ID

        Raises:
            HomeAssistantError: If validation fails or config entry not found
        """
        # Validate match config
        valid, error = EventMatcher.validate_match_config(match_config)
        if not valid:
            raise HomeAssistantError(f"Invalid match configuration: {error}")

        # Generate binding ID
        binding_id = self._generate_binding_id(calendars, match_config, slot_id)

        # Create binding
        new_binding = {
            "id": binding_id,
            "calendars": calendars,
            "match": match_config,
            "slot_id": slot_id,
            "priority": priority,
        }

        # Add to list
        self._bindings.append(new_binding)

        # Persist to config entry
        await self._persist_bindings()

        _LOGGER.info(
            "Binding added: %s | calendars=%s, slot=%s, priority=%d",
            binding_id,
            calendars,
            slot_id,
            priority,
        )

        return binding_id

    async def async_remove_binding(self, binding_id: str) -> bool:
        """
        Remove a binding by ID.

        Args:
            binding_id: Binding ID to remove

        Returns:
            True if removed, False if not found

        Raises:
            HomeAssistantError: If config entry not found
        """
        original_count = len(self._bindings)
        self._bindings = [b for b in self._bindings if b.get("id") != binding_id]

        if len(self._bindings) == original_count:
            _LOGGER.warning("Binding not found: %s", binding_id)
            return False

        # Persist to config entry
        await self._persist_bindings()

        _LOGGER.info("Binding removed: %s", binding_id)
        return True

    async def async_update_binding(
        self,
        binding_id: str,
        calendars: str | list[str] | None = None,
        match_config: dict[str, Any] | None = None,
        slot_id: str | None = None,
        priority: int | None = None,
    ) -> bool:
        """
        Update an existing binding.

        Args:
            binding_id: Binding ID to update
            calendars: New calendar filter (optional)
            match_config: New match configuration (optional)
            slot_id: New slot ID (optional)
            priority: New priority (optional)

        Returns:
            True if updated, False if not found

        Raises:
            HomeAssistantError: If validation fails or config entry not found
        """
        # Find binding
        binding = None
        for b in self._bindings:
            if b.get("id") == binding_id:
                binding = b
                break

        if not binding:
            _LOGGER.warning("Binding not found: %s", binding_id)
            return False

        # Update fields
        if calendars is not None:
            binding["calendars"] = calendars

        if match_config is not None:
            # Validate match config
            valid, error = EventMatcher.validate_match_config(match_config)
            if not valid:
                raise HomeAssistantError(f"Invalid match configuration: {error}")
            binding["match"] = match_config

        if slot_id is not None:
            binding["slot_id"] = slot_id

        if priority is not None:
            binding["priority"] = priority

        # Persist to config entry
        await self._persist_bindings()

        _LOGGER.info("Binding updated: %s", binding_id)
        return True

    async def _persist_bindings(self) -> None:
        """
        Persist bindings to config entry options.

        Raises:
            HomeAssistantError: If config entry not found
        """
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if not entry:
            raise HomeAssistantError(f"Config entry not found: {self.entry_id}")

        # Update config entry options
        new_options = {**entry.options, "bindings": self._bindings}
        self.hass.config_entries.async_update_entry(entry, options=new_options)

        _LOGGER.debug("Bindings persisted to config entry")

    @staticmethod
    def _generate_binding_id(
        calendars: str | list[str],
        match_config: dict[str, Any],
        slot_id: str,
    ) -> str:
        """
        Generate a stable binding ID.

        Uses SHA256 hash of binding definition, truncated to 12 hex characters.

        Args:
            calendars: Calendar filter
            match_config: Match configuration
            slot_id: Target slot ID

        Returns:
            12-character hexadecimal binding ID
        """
        # Create stable representation
        cal_str = str(calendars) if isinstance(calendars, str) else ",".join(sorted(calendars))
        match_str = f"{match_config.get('type')}:{match_config.get('value')}"
        source = f"binding_{cal_str}_{match_str}_{slot_id}"

        # Hash and truncate
        hash_full = hashlib.sha256(source.encode()).hexdigest()
        return hash_full[:12]

    def count_bindings(self) -> int:
        """
        Get count of bindings.

        Returns:
            Number of bindings
        """
        return len(self._bindings)

    def get_bindings_for_calendar(self, calendar_id: str) -> list[dict[str, Any]]:
        """
        Get all bindings that apply to a specific calendar.

        Args:
            calendar_id: Calendar entity ID

        Returns:
            List of matching bindings
        """
        return [
            b for b in self._bindings
            if matches_calendar(b.get("calendars", []), calendar_id)
        ]

    def get_bindings_for_slot(self, slot_id: str) -> list[dict[str, Any]]:
        """
        Get all bindings that reference a specific slot.

        Args:
            slot_id: Slot ID

        Returns:
            List of bindings referencing this slot
        """
        return [
            b for b in self._bindings
            if b.get("slot_id") == slot_id
        ]
