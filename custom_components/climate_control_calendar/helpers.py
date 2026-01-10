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
    SLOT_DAYS,
    SLOT_CLIMATE_PAYLOAD,
    PAYLOAD_TEMPERATURE,
    PAYLOAD_HVAC_MODE,
    PAYLOAD_PRESET_MODE,
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


def do_slots_overlap(
    slot_a: dict[str, Any],
    slot_b: dict[str, Any],
) -> bool:
    """
    Check if two slots have overlapping time windows on any shared day.

    Decision D011: Prevent overlapping slots via validation.

    Args:
        slot_a: First slot configuration
        slot_b: Second slot configuration

    Returns:
        True if slots overlap, False otherwise
    """
    # Get days for each slot (default all days)
    days_a = set(slot_a.get(SLOT_DAYS, DAYS_OF_WEEK))
    days_b = set(slot_b.get(SLOT_DAYS, DAYS_OF_WEEK))

    # Check if they share any days
    shared_days = days_a & days_b
    if not shared_days:
        # No shared days = no overlap
        return False

    # Parse time ranges
    try:
        start_a = parse_time_string(slot_a[SLOT_TIME_START])
        end_a = parse_time_string(slot_a[SLOT_TIME_END])
        start_b = parse_time_string(slot_b[SLOT_TIME_START])
        end_b = parse_time_string(slot_b[SLOT_TIME_END])
    except (ValueError, KeyError) as err:
        _LOGGER.error("Invalid time format in slot overlap check: %s", err)
        return False

    # Check time overlap
    # Two time ranges overlap if:
    # - start_a < end_b AND start_b < end_a (for normal ranges)
    # Need to handle overnight slots specially

    # Normalize overnight slots to minutes since midnight for comparison
    def time_to_minutes(t: time) -> int:
        return t.hour * 60 + t.minute

    # Convert to minutes
    start_a_min = time_to_minutes(start_a)
    end_a_min = time_to_minutes(end_a)
    start_b_min = time_to_minutes(start_b)
    end_b_min = time_to_minutes(end_b)

    # Handle overnight slots
    # If end < start, it's an overnight slot (e.g., 23:00 - 02:00)
    # We need to check overlap in two segments:
    # 1. [start, midnight]
    # 2. [midnight, end]

    def ranges_overlap(s1: int, e1: int, s2: int, e2: int, overnight1: bool, overnight2: bool) -> bool:
        """Check if two time ranges overlap, considering overnight spans."""
        if not overnight1 and not overnight2:
            # Both normal ranges
            return s1 < e2 and s2 < e1
        elif overnight1 and not overnight2:
            # Slot A is overnight, B is normal
            # A overlaps if B overlaps with [start_a, midnight] OR [midnight, end_a]
            return (s2 < 1440 and s1 < 1440 and s2 >= s1) or (e2 > 0 and e2 <= e1)
        elif not overnight1 and overnight2:
            # Slot B is overnight, A is normal
            return (s1 < 1440 and s2 < 1440 and s1 >= s2) or (e1 > 0 and e1 <= e2)
        else:
            # Both overnight - they definitely overlap
            return True

    overnight_a = end_a_min <= start_a_min
    overnight_b = end_b_min <= start_b_min

    # Adjust end times for overnight slots (represent as next day)
    if overnight_a:
        end_a_min += 1440  # Add 24h
    if overnight_b:
        end_b_min += 1440

    # Check overlap
    return ranges_overlap(start_a_min, end_a_min, start_b_min, end_b_min, overnight_a, overnight_b)


def validate_slot_overlap(
    new_slot: dict[str, Any],
    existing_slots: list[dict[str, Any]],
    skip_slot_id: str | None = None,
) -> tuple[bool, str | None]:
    """
    Validate that new slot doesn't overlap with existing slots.

    Decision D011: Prevent overlapping slots.

    Args:
        new_slot: New slot to validate
        existing_slots: List of existing slot configurations
        skip_slot_id: Slot ID to skip in validation (for editing existing slot)

    Returns:
        Tuple of (is_valid, error_message)
    """
    new_slot_label = new_slot.get(SLOT_LABEL, "Unknown")

    for existing_slot in existing_slots:
        # Skip comparison with itself (when editing)
        existing_slot_id = existing_slot.get(SLOT_ID)
        if skip_slot_id and existing_slot_id == skip_slot_id:
            continue

        if do_slots_overlap(new_slot, existing_slot):
            existing_label = existing_slot.get(SLOT_LABEL, "Unknown")
            existing_time = f"{existing_slot.get(SLOT_TIME_START)} - {existing_slot.get(SLOT_TIME_END)}"

            return False, (
                f"Slot '{new_slot_label}' overlaps with existing slot '{existing_label}' "
                f"({existing_time}). Overlapping slots are not allowed."
            )

    return True, None
