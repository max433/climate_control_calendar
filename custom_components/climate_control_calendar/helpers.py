"""Helper functions for Climate Control Calendar integration."""
import hashlib
import logging
from datetime import datetime, time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    SLOT_ID,
    SLOT_LABEL,
    SLOT_CLIMATE_PAYLOAD,
    PAYLOAD_TEMPERATURE,
    PAYLOAD_HVAC_MODE,
    PAYLOAD_PRESET_MODE,
)

_LOGGER = logging.getLogger(__name__)


def generate_slot_id(label: str, timestamp: float | None = None) -> str:
    """
    Generate stable slot ID using SHA256 truncated to 12 hex characters.

    Args:
        label: Human-readable slot label
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        12-character hexadecimal slot ID
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()

    source = f"{label}_{timestamp}"
    hash_full = hashlib.sha256(source.encode()).hexdigest()
    return hash_full[:12]


# REMOVED: validate_time_string(), parse_time_string(), time_to_string() (Decision D034)
# Time range handling removed from slot system - now managed by calendar events.


def validate_slot_data(slot_data: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate slot configuration data.

    Decision D034: Simplified slot validation - only label and climate payload required.
    Time/day fields removed from slot structure.

    Args:
        slot_data: Slot configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields (Decision D034: only label required now)
    if SLOT_LABEL not in slot_data:
        return False, "Missing required field: label"

    # Validate label not empty
    if not slot_data[SLOT_LABEL].strip():
        return False, "Slot label cannot be empty"

    # Validate climate payload if present
    if SLOT_CLIMATE_PAYLOAD in slot_data:
        valid, error = validate_climate_payload(slot_data[SLOT_CLIMATE_PAYLOAD])
        if not valid:
            return False, f"Invalid climate payload: {error}"

    return True, None


def get_calendar_entities(hass: HomeAssistant) -> list[str]:
    """
    Get all available calendar entities from Home Assistant.

    Args:
        hass: Home Assistant instance

    Returns:
        List of calendar entity IDs
    """
    entity_reg = er.async_get(hass)
    calendar_entities = []

    for entity in entity_reg.entities.values():
        if entity.domain == "calendar":
            calendar_entities.append(entity.entity_id)

    # Also check current states for calendars not in registry
    for entity_id in hass.states.async_entity_ids("calendar"):
        if entity_id not in calendar_entities:
            calendar_entities.append(entity_id)

    return sorted(calendar_entities)


def get_climate_entities(hass: HomeAssistant) -> list[str]:
    """
    Get all available climate entities from Home Assistant.

    Args:
        hass: Home Assistant instance

    Returns:
        List of climate entity IDs
    """
    entity_reg = er.async_get(hass)
    climate_entities = []

    for entity in entity_reg.entities.values():
        if entity.domain == "climate":
            climate_entities.append(entity.entity_id)

    # Also check current states for climate entities not in registry
    for entity_id in hass.states.async_entity_ids("climate"):
        if entity_id not in climate_entities:
            climate_entities.append(entity_id)

    return sorted(climate_entities)


def format_slot_summary(slot_data: dict[str, Any]) -> str:
    """
    Format slot data into human-readable summary.

    Decision D034: Slots no longer have time ranges.

    Args:
        slot_data: Slot configuration dictionary

    Returns:
        Formatted summary string
    """
    label = slot_data.get(SLOT_LABEL, "Unknown")
    slot_id = slot_data.get(SLOT_ID, "no-id")

    return f"{label} (ID: {slot_id})"


def validate_climate_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate climate payload structure.

    Decision D012: All fields optional, at least one must be present.

    Args:
        payload: Climate payload dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not payload:
        return False, "Climate payload cannot be empty (at least one field required)"

    # Valid payload keys
    valid_keys = [
        PAYLOAD_TEMPERATURE,
        PAYLOAD_HVAC_MODE,
        PAYLOAD_PRESET_MODE,
        "fan_mode",
        "swing_mode",
    ]

    # Check at least one valid key present
    has_valid_key = any(key in payload for key in valid_keys)
    if not has_valid_key:
        return False, f"Climate payload must contain at least one valid field: {valid_keys}"

    # Validate temperature if present
    if PAYLOAD_TEMPERATURE in payload:
        temp = payload[PAYLOAD_TEMPERATURE]
        if not isinstance(temp, (int, float)):
            return False, f"Temperature must be numeric, got: {type(temp).__name__}"
        if temp < -50 or temp > 50:
            return False, f"Temperature out of range (-50 to 50): {temp}"

    return True, None


# REMOVED: do_slots_overlap() - No longer needed (Decision D034)
# Slots no longer have time ranges, so overlap validation is not applicable.
# Event timing is now managed by calendar events, not slot definitions.

# REMOVED: validate_slot_overlap() - No longer needed (Decision D034)
# With event-to-slot binding system, multiple slots can coexist without conflicts.
# Conflicts are resolved via binding priority, not time-based overlap prevention.
