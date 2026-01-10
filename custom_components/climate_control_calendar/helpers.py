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
    SLOT_TIME_START,
    SLOT_TIME_END,
    DAYS_OF_WEEK,
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


def validate_time_string(time_str: str) -> bool:
    """
    Validate time string in HH:MM format.

    Args:
        time_str: Time string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def parse_time_string(time_str: str) -> time:
    """
    Parse time string in HH:MM format to time object.

    Args:
        time_str: Time string in HH:MM format

    Returns:
        time object

    Raises:
        ValueError: If time_str is invalid
    """
    dt = datetime.strptime(time_str, "%H:%M")
    return dt.time()


def time_to_string(time_obj: time) -> str:
    """
    Convert time object to HH:MM string.

    Args:
        time_obj: time object

    Returns:
        Time string in HH:MM format
    """
    return time_obj.strftime("%H:%M")


def validate_slot_data(slot_data: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate slot configuration data.

    Args:
        slot_data: Slot configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    required_fields = [SLOT_LABEL, SLOT_TIME_START, SLOT_TIME_END]
    for field in required_fields:
        if field not in slot_data:
            return False, f"Missing required field: {field}"

    # Validate time format
    if not validate_time_string(slot_data[SLOT_TIME_START]):
        return False, f"Invalid start time format: {slot_data[SLOT_TIME_START]}"

    if not validate_time_string(slot_data[SLOT_TIME_END]):
        return False, f"Invalid end time format: {slot_data[SLOT_TIME_END]}"

    # Validate label not empty
    if not slot_data[SLOT_LABEL].strip():
        return False, "Slot label cannot be empty"

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


def get_current_day_name() -> str:
    """
    Get current day name in lowercase English.

    Returns:
        Day name (e.g., 'monday', 'tuesday')
    """
    day_index = datetime.now().weekday()
    return DAYS_OF_WEEK[day_index]


def format_slot_summary(slot_data: dict[str, Any]) -> str:
    """
    Format slot data into human-readable summary.

    Args:
        slot_data: Slot configuration dictionary

    Returns:
        Formatted summary string
    """
    label = slot_data.get(SLOT_LABEL, "Unknown")
    time_start = slot_data.get(SLOT_TIME_START, "??:??")
    time_end = slot_data.get(SLOT_TIME_END, "??:??")

    return f"{label} ({time_start} - {time_end})"
