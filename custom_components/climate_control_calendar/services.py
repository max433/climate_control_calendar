"""Service handlers for Climate Control Calendar integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    FLAG_SKIP_UNTIL_NEXT_SLOT,
    FLAG_SKIP_TODAY,
    FLAG_FORCE_SLOT,
    SERVICE_SET_FLAG,
    SERVICE_CLEAR_FLAG,
    SERVICE_FORCE_SLOT,
    SERVICE_REFRESH_NOW,
    SERVICE_ADD_SLOT,
    SERVICE_REMOVE_SLOT,
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_EVENT_EMITTER,
    CONF_SLOTS,
    SLOT_ID,
    SLOT_LABEL,
    SLOT_TIME_START,
    SLOT_TIME_END,
    SLOT_DAYS,
    SLOT_CLIMATE_PAYLOAD,
    DAYS_OF_WEEK,
)
from .helpers import generate_slot_id, validate_slot_data, validate_slot_overlap

_LOGGER = logging.getLogger(__name__)

# Service parameter names
ATTR_FLAG_TYPE = "flag_type"
ATTR_SLOT_ID = "slot_id"
ATTR_TARGET_SLOT_ID = "target_slot_id"

# Valid flag types
VALID_FLAG_TYPES = [
    FLAG_SKIP_UNTIL_NEXT_SLOT,
    FLAG_SKIP_TODAY,
    FLAG_FORCE_SLOT,
]

# Service schemas (Decision D021: Strict validation)
SERVICE_SET_FLAG_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_FLAG_TYPE): vol.In(VALID_FLAG_TYPES),
        vol.Optional(ATTR_TARGET_SLOT_ID): cv.string,
    }
)

SERVICE_CLEAR_FLAG_SCHEMA = vol.Schema({})

SERVICE_FORCE_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SLOT_ID): cv.string,
    }
)

SERVICE_REFRESH_NOW_SCHEMA = vol.Schema({})

SERVICE_ADD_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required("label"): cv.string,
        vol.Required("time_start"): cv.string,
        vol.Required("time_end"): cv.string,
        vol.Optional("days", default=DAYS_OF_WEEK): vol.All(cv.ensure_list, [vol.In(DAYS_OF_WEEK)]),
        vol.Required("climate_payload"): vol.Schema(
            {
                vol.Optional("temperature"): vol.Coerce(float),
                vol.Optional("hvac_mode"): cv.string,
                vol.Optional("preset_mode"): cv.string,
                vol.Optional("fan_mode"): cv.string,
                vol.Optional("swing_mode"): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    }
)

SERVICE_REMOVE_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required("slot_id"): cv.string,
    }
)


def get_service_schemas() -> dict[str, vol.Schema]:
    """
    Get service schemas for registration.

    Returns:
        Dict of service name to schema
    """
    return {
        SERVICE_SET_FLAG: SERVICE_SET_FLAG_SCHEMA,
        SERVICE_CLEAR_FLAG: SERVICE_CLEAR_FLAG_SCHEMA,
        SERVICE_FORCE_SLOT: SERVICE_FORCE_SLOT_SCHEMA,
        SERVICE_REFRESH_NOW: SERVICE_REFRESH_NOW_SCHEMA,
        SERVICE_ADD_SLOT: SERVICE_ADD_SLOT_SCHEMA,
        SERVICE_REMOVE_SLOT: SERVICE_REMOVE_SLOT_SCHEMA,
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """
    Set up services for the integration.

    Args:
        hass: Home Assistant instance
    """
    async def handle_set_flag(call: ServiceCall) -> None:
        """
        Handle set_flag service call.

        Decision D021: Strict validation.
        Decision D023: Services ignore dry run.
        """
        flag_type = call.data[ATTR_FLAG_TYPE]
        target_slot_id = call.data.get(ATTR_TARGET_SLOT_ID)

        # Strict validation (D021)
        if flag_type == FLAG_FORCE_SLOT and not target_slot_id:
            raise vol.Invalid(
                f"Service parameter '{ATTR_TARGET_SLOT_ID}' is required "
                f"when flag_type is '{FLAG_FORCE_SLOT}'"
            )

        _LOGGER.info(
            "Service call: set_flag | flag_type=%s, slot_id=%s",
            flag_type,
            target_slot_id,
        )

        # Apply to all config entries (or could be targeted)
        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if "flag_manager" in entry_data:
                flag_manager = entry_data["flag_manager"]
                await flag_manager.async_set_flag(
                    flag_type=flag_type,
                    slot_id=target_slot_id,
                )

                # Force immediate evaluation to apply flag
                coordinator = entry_data.get(DATA_COORDINATOR)
                if coordinator:
                    await coordinator.async_request_refresh()

    async def handle_clear_flag(call: ServiceCall) -> None:
        """Handle clear_flag service call."""
        _LOGGER.info("Service call: clear_flag")

        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if "flag_manager" in entry_data:
                flag_manager = entry_data["flag_manager"]
                await flag_manager.async_clear_flag(reason="manual_clear_service")

                # Force immediate evaluation
                coordinator = entry_data.get(DATA_COORDINATOR)
                if coordinator:
                    await coordinator.async_request_refresh()

    async def handle_force_slot(call: ServiceCall) -> None:
        """
        Handle force_slot service call.

        This is a convenience wrapper for set_flag with flag_type=force_slot.
        """
        slot_id = call.data[ATTR_SLOT_ID]

        _LOGGER.info("Service call: force_slot | slot_id=%s", slot_id)

        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            if "flag_manager" in entry_data:
                flag_manager = entry_data["flag_manager"]
                await flag_manager.async_set_flag(
                    flag_type=FLAG_FORCE_SLOT,
                    slot_id=slot_id,
                )

                # Force immediate evaluation
                coordinator = entry_data.get(DATA_COORDINATOR)
                if coordinator:
                    await coordinator.async_request_refresh()

    async def handle_refresh_now(call: ServiceCall) -> None:
        """Handle refresh_now service call."""
        _LOGGER.info("Service call: refresh_now")

        for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
            coordinator = entry_data.get(DATA_COORDINATOR)
            if coordinator:
                await coordinator.async_request_refresh()

    async def handle_add_slot(call: ServiceCall) -> None:
        """Handle add_slot service call."""
        label = call.data["label"]
        time_start = call.data["time_start"]
        time_end = call.data["time_end"]
        days = call.data.get("days", DAYS_OF_WEEK)
        climate_payload = call.data["climate_payload"]

        # Generate slot ID
        from homeassistant.util import dt as dt_util
        slot_id = generate_slot_id(label, dt_util.utcnow().timestamp())

        new_slot = {
            SLOT_ID: slot_id,
            SLOT_LABEL: label,
            SLOT_TIME_START: time_start,
            SLOT_TIME_END: time_end,
            SLOT_DAYS: days,
            SLOT_CLIMATE_PAYLOAD: climate_payload,
        }

        # Validate slot data
        if not validate_slot_data(new_slot):
            _LOGGER.error("Invalid slot data provided")
            raise vol.Invalid("Invalid slot configuration")

        _LOGGER.info("Service call: add_slot | label=%s, id=%s", label, slot_id)

        # Add to all config entries (or first one)
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Climate Control Calendar integration found")
            return

        entry = entries[0]  # Use first entry
        current_slots = entry.options.get(CONF_SLOTS, [])

        # Check for overlaps
        overlap_check = validate_slot_overlap(new_slot, current_slots)
        if not overlap_check["valid"]:
            _LOGGER.error("Slot overlaps with existing slot: %s", overlap_check["overlaps_with"])
            raise vol.Invalid(f"Slot overlaps with existing slot ID: {overlap_check['overlaps_with']}")

        # Add new slot
        updated_slots = current_slots + [new_slot]
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_SLOTS: updated_slots}
        )

        _LOGGER.info("Slot added successfully: %s (ID: %s)", label, slot_id)

        # Force refresh to apply immediately
        for entry_data in hass.data.get(DOMAIN, {}).values():
            coordinator = entry_data.get(DATA_COORDINATOR)
            if coordinator:
                await coordinator.async_request_refresh()

    async def handle_remove_slot(call: ServiceCall) -> None:
        """Handle remove_slot service call."""
        slot_id = call.data["slot_id"]

        _LOGGER.info("Service call: remove_slot | slot_id=%s", slot_id)

        # Remove from all config entries
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Climate Control Calendar integration found")
            return

        entry = entries[0]
        current_slots = entry.options.get(CONF_SLOTS, [])

        # Find and remove slot
        updated_slots = [s for s in current_slots if s.get(SLOT_ID) != slot_id]

        if len(updated_slots) == len(current_slots):
            _LOGGER.warning("Slot ID not found: %s", slot_id)
            raise vol.Invalid(f"Slot ID not found: {slot_id}")

        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_SLOTS: updated_slots}
        )

        _LOGGER.info("Slot removed successfully: %s", slot_id)

        # Force refresh
        for entry_data in hass.data.get(DOMAIN, {}).values():
            coordinator = entry_data.get(DATA_COORDINATOR)
            if coordinator:
                await coordinator.async_request_refresh()

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FLAG,
        handle_set_flag,
        schema=SERVICE_SET_FLAG_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_FLAG,
        handle_clear_flag,
        schema=SERVICE_CLEAR_FLAG_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_SLOT,
        handle_force_slot,
        schema=SERVICE_FORCE_SLOT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_NOW,
        handle_refresh_now,
        schema=SERVICE_REFRESH_NOW_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_SLOT,
        handle_add_slot,
        schema=SERVICE_ADD_SLOT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_SLOT,
        handle_remove_slot,
        schema=SERVICE_REMOVE_SLOT_SCHEMA,
    )

    _LOGGER.info("Services registered: set_flag, clear_flag, force_slot, refresh_now, add_slot, remove_slot")


async def async_unload_services(hass: HomeAssistant) -> None:
    """
    Unload services when last config entry is removed.

    Args:
        hass: Home Assistant instance
    """
    # Only unload if no more config entries
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_FLAG)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR_FLAG)
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_SLOT)
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_NOW)
        hass.services.async_remove(DOMAIN, SERVICE_ADD_SLOT)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_SLOT)

        _LOGGER.info("Services unregistered")
