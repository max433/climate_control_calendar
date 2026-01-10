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
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_EVENT_EMITTER,
)

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

    _LOGGER.info("Services registered: set_flag, clear_flag, force_slot, refresh_now")


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

        _LOGGER.info("Services unregistered")
