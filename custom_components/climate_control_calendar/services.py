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
    SERVICE_ADD_BINDING,
    SERVICE_REMOVE_BINDING,
    SERVICE_LIST_BINDINGS,
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_EVENT_EMITTER,
    DATA_BINDING_MANAGER,
    CONF_SLOTS,
    CONF_BINDINGS,
    SLOT_ID,
    SLOT_LABEL,
    SLOT_CLIMATE_PAYLOAD,
    BINDING_CALENDARS,
    BINDING_MATCH,
    BINDING_SLOT_ID,
    BINDING_PRIORITY,
    MATCH_TYPE,
    MATCH_VALUE,
)
from .helpers import generate_slot_id, validate_slot_data
from .event_matcher import EventMatcher

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
        # New architecture: slots as reusable templates
        vol.Required("default_climate_payload"): vol.Schema(
            {
                vol.Optional("temperature"): vol.Coerce(float),
                vol.Optional("hvac_mode"): cv.string,
                vol.Optional("preset_mode"): cv.string,
                vol.Optional("fan_mode"): cv.string,
                vol.Optional("swing_mode"): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        ),
        vol.Optional("entity_overrides", default={}): vol.Schema(
            {cv.string: vol.Schema({}, extra=vol.ALLOW_EXTRA)}
        ),
        vol.Optional("excluded_entities", default=[]): cv.ensure_list,
    }
)

SERVICE_REMOVE_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required("slot_id"): cv.string,
    }
)

# Decision D032: New binding services (with target_entities)
SERVICE_ADD_BINDING_SCHEMA = vol.Schema(
    {
        vol.Required("calendars"): vol.Any(
            cv.string,  # "*" for all calendars
            cv.ensure_list,  # List of calendar entity IDs
        ),
        vol.Required("match"): vol.Schema(
            {
                vol.Required("type"): vol.In(EventMatcher.SUPPORTED_MATCH_TYPES),
                vol.Required("value"): cv.string,
            }
        ),
        vol.Required("slot_id"): cv.string,
        vol.Optional("target_entities", default=None): vol.Any(None, cv.ensure_list),  # New!
        vol.Optional("priority", default=None): vol.Any(None, vol.Coerce(int)),  # Now optional (None = use calendar default)
    }
)

SERVICE_REMOVE_BINDING_SCHEMA = vol.Schema(
    {
        vol.Required("binding_id"): cv.string,
    }
)

SERVICE_LIST_BINDINGS_SCHEMA = vol.Schema({})  # No parameters


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
        SERVICE_ADD_BINDING: SERVICE_ADD_BINDING_SCHEMA,
        SERVICE_REMOVE_BINDING: SERVICE_REMOVE_BINDING_SCHEMA,
        SERVICE_LIST_BINDINGS: SERVICE_LIST_BINDINGS_SCHEMA,
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
        """
        Handle add_slot service call.

        New architecture: slots with default payload + optional overrides/exclusions.
        """
        label = call.data["label"]
        default_climate_payload = call.data["default_climate_payload"]
        entity_overrides = call.data.get("entity_overrides", {})
        excluded_entities = call.data.get("excluded_entities", [])

        # Generate slot ID
        from homeassistant.util import dt as dt_util
        slot_id = generate_slot_id(label, dt_util.utcnow().timestamp())

        new_slot = {
            SLOT_ID: slot_id,
            SLOT_LABEL: label,
            "default_climate_payload": default_climate_payload,
            "entity_overrides": entity_overrides,
            "excluded_entities": excluded_entities,
        }

        # Validate slot data
        valid, error = validate_slot_data(new_slot)
        if not valid:
            _LOGGER.error("Invalid slot data provided: %s", error)
            raise vol.Invalid(f"Invalid slot configuration: {error}")

        _LOGGER.info("Service call: add_slot | label=%s, id=%s", label, slot_id)

        # Add to all config entries (or first one)
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No Climate Control Calendar integration found")
            return

        entry = entries[0]  # Use first entry
        current_slots = entry.options.get(CONF_SLOTS, [])

        # Decision D034: No overlap validation needed (slots are event-independent)

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

    async def handle_add_binding(call: ServiceCall) -> None:
        """
        Handle add_binding service call.

        New architecture: bindings with target_entities and priority.
        """
        calendars = call.data["calendars"]
        match_config = call.data["match"]
        slot_id = call.data["slot_id"]
        target_entities = call.data.get("target_entities")  # New: can be None
        priority = call.data.get("priority")  # New: can be None (use calendar default)

        _LOGGER.info(
            "Service call: add_binding | calendars=%s, match=%s, slot=%s, entities=%s, priority=%s",
            calendars,
            match_config,
            slot_id,
            target_entities or "global",
            priority if priority is not None else "calendar_default",
        )

        # Add binding via binding manager
        for entry_data in hass.data.get(DOMAIN, {}).values():
            binding_manager = entry_data.get(DATA_BINDING_MANAGER)
            if binding_manager:
                try:
                    binding_id = await binding_manager.async_add_binding(
                        calendars=calendars,
                        match_config=match_config,
                        slot_id=slot_id,
                        target_entities=target_entities,  # New parameter
                        priority=priority,  # Can be None
                    )
                    _LOGGER.info("Binding added successfully: %s", binding_id)

                    # Force refresh to apply immediately
                    coordinator = entry_data.get(DATA_COORDINATOR)
                    if coordinator:
                        await coordinator.async_request_refresh()

                    return  # Success
                except Exception as err:
                    _LOGGER.error("Failed to add binding: %s", err)
                    raise vol.Invalid(f"Failed to add binding: {err}")

        _LOGGER.error("No binding manager found")
        raise vol.Invalid("Binding manager not available")

    async def handle_remove_binding(call: ServiceCall) -> None:
        """Handle remove_binding service call."""
        binding_id = call.data["binding_id"]

        _LOGGER.info("Service call: remove_binding | binding_id=%s", binding_id)

        # Remove binding via binding manager
        for entry_data in hass.data.get(DOMAIN, {}).values():
            binding_manager = entry_data.get(DATA_BINDING_MANAGER)
            if binding_manager:
                success = await binding_manager.async_remove_binding(binding_id)
                if success:
                    _LOGGER.info("Binding removed successfully: %s", binding_id)

                    # Force refresh
                    coordinator = entry_data.get(DATA_COORDINATOR)
                    if coordinator:
                        await coordinator.async_request_refresh()

                    return  # Success
                else:
                    _LOGGER.warning("Binding ID not found: %s", binding_id)
                    raise vol.Invalid(f"Binding ID not found: {binding_id}")

        _LOGGER.error("No binding manager found")
        raise vol.Invalid("Binding manager not available")

    async def handle_list_bindings(call: ServiceCall) -> dict[str, Any]:
        """
        Handle list_bindings service call.

        Returns:
            Dict with bindings list
        """
        _LOGGER.info("Service call: list_bindings")

        # Get bindings from binding manager
        for entry_data in hass.data.get(DOMAIN, {}).values():
            binding_manager = entry_data.get(DATA_BINDING_MANAGER)
            if binding_manager:
                bindings = binding_manager.get_all_bindings()
                _LOGGER.info("Returning %d bindings", len(bindings))
                return {"bindings": bindings}

        _LOGGER.warning("No binding manager found")
        return {"bindings": []}

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

    # Decision D032: Register binding services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_BINDING,
        handle_add_binding,
        schema=SERVICE_ADD_BINDING_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_BINDING,
        handle_remove_binding,
        schema=SERVICE_REMOVE_BINDING_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_BINDINGS,
        handle_list_bindings,
        schema=SERVICE_LIST_BINDINGS_SCHEMA,
        supports_response=True,  # This service returns data
    )

    _LOGGER.info(
        "Services registered: set_flag, clear_flag, force_slot, refresh_now, "
        "add_slot, remove_slot, add_binding, remove_binding, list_bindings"
    )


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
        hass.services.async_remove(DOMAIN, SERVICE_ADD_BINDING)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_BINDING)
        hass.services.async_remove(DOMAIN, SERVICE_LIST_BINDINGS)

        _LOGGER.info("Services unregistered")
