"""Config flow for Climate Control Calendar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITIES,  # Changed from CONF_CALENDAR_ENTITY (Decision D033)
    CONF_CLIMATE_ENTITIES,
    CONF_DRY_RUN,
    CONF_DEBUG_MODE,
    DEFAULT_DRY_RUN,
    DEFAULT_DEBUG_MODE,
)

_LOGGER = logging.getLogger(__name__)


def validate_and_build_slot_payload(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Validate slot input and build climate payload.

    Returns:
        tuple: (climate_payload, errors)
    """
    climate_payload = {}
    errors = {}

    # Temperature (single value)
    temp_input = user_input.get("temperature")
    if temp_input is not None and temp_input != "":
        try:
            temp = float(temp_input)
            if temp < -50 or temp > 50:
                errors["temperature"] = "invalid_temperature"
            else:
                climate_payload["temperature"] = temp
        except (ValueError, TypeError):
            errors["temperature"] = "invalid_temperature"

    # Temperature range (for heat_cool mode)
    temp_high_input = user_input.get("target_temp_high")
    temp_low_input = user_input.get("target_temp_low")

    temp_high = None
    temp_low = None

    if temp_high_input is not None and temp_high_input != "":
        try:
            temp_high = float(temp_high_input)
            if temp_high < -50 or temp_high > 50:
                errors["target_temp_high"] = "invalid_temperature"
            else:
                climate_payload["target_temp_high"] = temp_high
        except (ValueError, TypeError):
            errors["target_temp_high"] = "invalid_temperature"

    if temp_low_input is not None and temp_low_input != "":
        try:
            temp_low = float(temp_low_input)
            if temp_low < -50 or temp_low > 50:
                errors["target_temp_low"] = "invalid_temperature"
            else:
                climate_payload["target_temp_low"] = temp_low
        except (ValueError, TypeError):
            errors["target_temp_low"] = "invalid_temperature"

    # Cross-validation: if both range temps are set, low must be < high
    if (temp_high is not None and temp_low is not None and
        "target_temp_high" not in errors and "target_temp_low" not in errors):
        if temp_low >= temp_high:
            errors["target_temp_low"] = "temp_range_invalid"
            errors["target_temp_high"] = "temp_range_invalid"

    # Cross-validation: temperature and range are mutually exclusive
    if "temperature" in climate_payload and ("target_temp_high" in climate_payload or "target_temp_low" in climate_payload):
        errors["base"] = "temperature_conflict"

    # HVAC mode (only save if explicitly set)
    hvac_mode = user_input.get("hvac_mode")
    if hvac_mode and hvac_mode.strip():
        climate_payload["hvac_mode"] = hvac_mode

    # Preset mode (only save if explicitly set)
    preset_mode = user_input.get("preset_mode")
    if preset_mode and preset_mode.strip():
        climate_payload["preset_mode"] = preset_mode

    # Humidity control (only if provided and not empty)
    humidity_input = user_input.get("humidity")
    if humidity_input is not None and humidity_input != "":
        try:
            humidity = int(humidity_input)
            if humidity < 0 or humidity > 100:
                errors["humidity"] = "invalid_humidity"
            else:
                climate_payload["humidity"] = humidity
        except (ValueError, TypeError):
            errors["humidity"] = "invalid_humidity"

    # Auxiliary heat (string: "on"/"off"/"" from selector)
    aux_heat = user_input.get("aux_heat", "").strip()
    if aux_heat == "on":
        climate_payload["aux_heat"] = True
    elif aux_heat == "off":
        climate_payload["aux_heat"] = False
    # If aux_heat is "" (not configured), don't add to payload

    # Validate at least one climate setting is configured
    if not climate_payload and "base" not in errors:
        errors["base"] = "no_climate_settings"

    return climate_payload, errors


class ClimateControlCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Climate Control Calendar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._calendar_entities: list[str] = []  # Changed from singular to plural (Decision D033)
        self._climate_entities: list[str] = []
        self._dry_run: bool = DEFAULT_DRY_RUN
        self._debug_mode: bool = DEFAULT_DEBUG_MODE

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - calendar selection (multi-select)."""
        errors: dict[str, str] = {}

        # Get available calendar entities
        calendar_entities = [
            state.entity_id
            for state in self.hass.states.async_all("calendar")
        ]

        if not calendar_entities:
            _LOGGER.error("No calendar entities found")
            return self.async_abort(reason="no_calendars")

        if user_input is not None:
            self._calendar_entities = user_input.get(CONF_CALENDAR_ENTITIES, [])

            # Validate at least one calendar selected
            if not self._calendar_entities:
                errors[CONF_CALENDAR_ENTITIES] = "no_calendars_selected"
            else:
                # Verify all calendar entities exist
                invalid_calendars = [
                    cal for cal in self._calendar_entities
                    if self.hass.states.get(cal) is None
                ]
                if invalid_calendars:
                    errors[CONF_CALENDAR_ENTITIES] = "calendar_not_found"
                else:
                    # Create unique_id from sorted calendar list (Decision D033)
                    import hashlib
                    calendars_str = ",".join(sorted(self._calendar_entities))
                    unique_id = hashlib.sha256(calendars_str.encode()).hexdigest()[:16]
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    # Proceed to climate entities selection
                    return await self.async_step_climate()

        # Build schema for calendar multi-selection (Decision D033)
        schema = vol.Schema(
            {
                vol.Required(CONF_CALENDAR_ENTITIES): cv.multi_select(
                    {entity: entity for entity in calendar_entities}
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "calendar_count": str(len(calendar_entities)),
            },
        )

    async def async_step_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle climate entities selection step."""
        errors: dict[str, str] = {}

        # Get available climate entities
        climate_entities = [
            state.entity_id
            for state in self.hass.states.async_all("climate")
        ]

        if user_input is not None:
            self._climate_entities = user_input.get(CONF_CLIMATE_ENTITIES, [])
            return await self.async_step_options()

        # Build schema for climate selection
        schema = vol.Schema(
            {
                vol.Optional(CONF_CLIMATE_ENTITIES, default=[]): cv.multi_select(
                    {entity: entity for entity in climate_entities}
                ),
            }
        )

        return self.async_show_form(
            step_id="climate",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "calendar_entities": ", ".join(self._calendar_entities) if self._calendar_entities else "",
                "climate_count": str(len(climate_entities)),
            },
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration options step."""
        if user_input is not None:
            self._dry_run = user_input.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
            self._debug_mode = user_input.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

            # Create the config entry (Decision D033: Multi-calendar support)
            # Title shows count of calendars instead of single calendar name
            calendar_count = len(self._calendar_entities)
            title = f"Climate Control ({calendar_count} calendar{'s' if calendar_count != 1 else ''})"

            return self.async_create_entry(
                title=title,
                data={
                    CONF_CALENDAR_ENTITIES: self._calendar_entities,  # Changed from singular
                    CONF_DRY_RUN: self._dry_run,
                    CONF_DEBUG_MODE: self._debug_mode,
                },
                options={
                    CONF_CLIMATE_ENTITIES: self._climate_entities,
                },
            )

        # Build schema for options
        schema = vol.Schema(
            {
                vol.Optional(CONF_DRY_RUN, default=DEFAULT_DRY_RUN): cv.boolean,
                vol.Optional(CONF_DEBUG_MODE, default=DEFAULT_DEBUG_MODE): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=schema,
            description_placeholders={
                "calendar_entities": ", ".join(self._calendar_entities) if self._calendar_entities else "",
                "climate_count": str(len(self._climate_entities)),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ClimateControlCalendarOptionsFlow:
        """Get the options flow handler."""
        return ClimateControlCalendarOptionsFlow(config_entry)


class ClimateControlCalendarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Climate Control Calendar."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._temp_data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show main configuration menu."""
        from .const import CONF_SLOTS, CONF_BINDINGS

        # Get current stats
        calendar_entities = self.config_entry.data.get(CONF_CALENDAR_ENTITIES, [])
        climate_entities = self.config_entry.options.get(CONF_CLIMATE_ENTITIES, [])
        slots = self.config_entry.options.get(CONF_SLOTS, [])
        bindings = self.config_entry.options.get(CONF_BINDINGS, [])

        return self.async_show_menu(
            step_id="init",
            menu_options=["basic", "calendars", "slots", "bindings", "yaml_editor"],
            description_placeholders={
                "calendar_count": str(len(calendar_entities)),
                "climate_count": str(len(climate_entities)),
                "slot_count": str(len(slots)),
                "binding_count": str(len(bindings)),
            },
        )

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle basic settings configuration."""
        if user_input is not None:
            # Update options
            new_options = {**self.config_entry.options}
            new_options[CONF_CLIMATE_ENTITIES] = user_input.get(CONF_CLIMATE_ENTITIES, [])

            # Update data (calendars, dry_run and debug_mode)
            new_data = {**self.config_entry.data}
            new_data[CONF_CALENDAR_ENTITIES] = user_input.get(CONF_CALENDAR_ENTITIES, [])
            new_data[CONF_DRY_RUN] = user_input.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
            new_data[CONF_DEBUG_MODE] = user_input.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

            # Update both data and options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
                options=new_options,
            )

            return self.async_create_entry(title="", data=new_options)

        # Get available calendar entities
        calendar_entities = [
            state.entity_id
            for state in self.hass.states.async_all("calendar")
        ]

        # Get available climate entities
        climate_entities = [
            state.entity_id
            for state in self.hass.states.async_all("climate")
        ]

        current_calendars = self.config_entry.data.get(CONF_CALENDAR_ENTITIES, [])
        current_climate = self.config_entry.options.get(CONF_CLIMATE_ENTITIES, [])
        current_dry_run = self.config_entry.data.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
        current_debug = self.config_entry.data.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CALENDAR_ENTITIES, default=current_calendars
                ): cv.multi_select({entity: entity for entity in calendar_entities}),
                vol.Optional(
                    CONF_CLIMATE_ENTITIES, default=current_climate
                ): cv.multi_select({entity: entity for entity in climate_entities}),
                vol.Optional(CONF_DRY_RUN, default=current_dry_run, description={"suggested_value": current_dry_run}): cv.boolean,
                vol.Optional(CONF_DEBUG_MODE, default=current_debug, description={"suggested_value": current_debug}): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="basic",
            data_schema=schema,
        )

    async def async_step_calendars(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle calendar configuration selection."""
        from .const import CONF_CALENDAR_CONFIGS

        calendar_entities = self.config_entry.data.get(CONF_CALENDAR_ENTITIES, [])

        if not calendar_entities:
            return self.async_abort(reason="no_calendars")

        if user_input is not None:
            # Store selected calendar and move to detail step
            self._temp_data["selected_calendar"] = user_input.get("calendar_id")
            return await self.async_step_calendar_detail()

        # Build calendar list for display
        calendar_list = "\n".join([f"• {cal}" for cal in calendar_entities])

        schema = vol.Schema(
            {
                vol.Required("calendar_id"): vol.In(
                    {cal: cal for cal in calendar_entities}
                ),
            }
        )

        return self.async_show_form(
            step_id="calendars",
            data_schema=schema,
            description_placeholders={
                "calendar_list": calendar_list,
            },
        )

    async def async_step_calendar_detail(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle detailed calendar configuration."""
        from .const import CONF_CALENDAR_CONFIGS, CONF_BINDINGS

        calendar_id = self._temp_data.get("selected_calendar")
        if not calendar_id:
            return await self.async_step_calendars()

        if user_input is not None:
            # Update calendar configs
            new_options = {**self.config_entry.options}
            calendar_configs = new_options.get(CONF_CALENDAR_CONFIGS, {})

            calendar_configs[calendar_id] = {
                "enabled": user_input.get("enabled", True),
                "default_priority": user_input.get("default_priority", 0),
                "description": user_input.get("description", ""),
            }

            new_options[CONF_CALENDAR_CONFIGS] = calendar_configs
            return self.async_create_entry(title="", data=new_options)

        # Get current config for this calendar
        calendar_configs = self.config_entry.options.get(CONF_CALENDAR_CONFIGS, {})
        current_config = calendar_configs.get(calendar_id, {})

        # Count bindings from this calendar
        bindings = self.config_entry.options.get(CONF_BINDINGS, [])
        binding_count = sum(
            1 for b in bindings
            if calendar_id in b.get("calendars", []) or b.get("calendars") == "*"
        )

        schema = vol.Schema(
            {
                vol.Optional("enabled", default=current_config.get("enabled", True)): cv.boolean,
                vol.Optional("default_priority", default=current_config.get("default_priority", 0)): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("description", default=current_config.get("description", "")): cv.string,
            }
        )

        return self.async_show_form(
            step_id="calendar_detail",
            data_schema=schema,
            description_placeholders={
                "calendar_name": calendar_id,
                "binding_count": str(binding_count),
            },
        )

    async def async_step_slots(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show slots management menu."""
        from .const import CONF_SLOTS

        slots = self.config_entry.options.get(CONF_SLOTS, [])

        return self.async_show_menu(
            step_id="slots",
            menu_options=["add_slot", "edit_slot", "delete_slot", "view_slots"],
            description_placeholders={
                "slot_count": str(len(slots)),
            },
        )

    async def async_step_add_slot(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new slot."""
        from .const import CONF_SLOTS
        from .helpers import generate_slot_id, validate_slot_data
        import time

        errors = {}

        if user_input is not None:
            label = user_input.get("label", "").strip()
            excluded_entities = user_input.get("excluded_entities")

            if not label:
                errors["label"] = "invalid_slot_id"
            else:
                # Build and validate climate payload using helper
                climate_payload, payload_errors = validate_and_build_slot_payload(user_input)
                errors.update(payload_errors)

                if not errors:
                    # Create new slot
                    slot_id = generate_slot_id(label, time.time())
                    new_slot = {
                        "id": slot_id,
                        "label": label,
                        "default_climate_payload": climate_payload,
                    }

                    # Add excluded_entities if provided
                    if excluded_entities:
                        new_slot["excluded_entities"] = excluded_entities

                    # Validate
                    valid, error_msg = validate_slot_data(new_slot)
                    if not valid:
                        errors["base"] = "unknown"
                        _LOGGER.error("Slot validation failed: %s", error_msg)
                    else:
                        # Add to slots
                        new_options = {**self.config_entry.options}
                        slots = new_options.get(CONF_SLOTS, [])
                        slots.append(new_slot)
                        new_options[CONF_SLOTS] = slots

                        return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required("label"): cv.string,
                vol.Optional("temperature"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-50,
                        max=50,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C",
                    ),
                ),
                vol.Optional("target_temp_high"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-50,
                        max=50,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C",
                    ),
                ),
                vol.Optional("target_temp_low"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-50,
                        max=50,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C",
                    ),
                ),
                vol.Optional("hvac_mode"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["heat", "cool", "heat_cool", "auto", "off", "fan_only", "dry"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional("preset_mode"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    ),
                ),
                vol.Optional("humidity"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                    ),
                ),
                vol.Optional("aux_heat"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "", "label": "Not configured"},
                            {"value": "on", "label": "On"},
                            {"value": "off", "label": "Off"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional("excluded_entities"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="climate",
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="add_slot",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_slot(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle slot editing selection."""
        from .const import CONF_SLOTS

        slots = self.config_entry.options.get(CONF_SLOTS, [])

        if not slots:
            return self.async_abort(reason="slot_not_found")

        if user_input is not None:
            self._temp_data["selected_slot_id"] = user_input.get("slot_id")
            return await self.async_step_edit_slot_detail()

        # Build slot selector
        slot_options = {slot["id"]: f"{slot['label']} ({slot['id']})" for slot in slots}

        schema = vol.Schema(
            {
                vol.Required("slot_id"): vol.In(slot_options),
            }
        )

        return self.async_show_form(
            step_id="edit_slot",
            data_schema=schema,
            description_placeholders={
                "slot_count": str(len(slots)),
            },
        )

    async def async_step_edit_slot_detail(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle slot editing details."""
        from .const import CONF_SLOTS, CONF_BINDINGS
        from .helpers import validate_slot_data

        slot_id = self._temp_data.get("selected_slot_id")
        if not slot_id:
            return await self.async_step_edit_slot()

        slots = self.config_entry.options.get(CONF_SLOTS, [])
        slot = next((s for s in slots if s["id"] == slot_id), None)

        if not slot:
            return self.async_abort(reason="slot_not_found")

        errors = {}

        if user_input is not None:
            label = user_input.get("label", "").strip()
            excluded_entities = user_input.get("excluded_entities")

            if not label:
                errors["label"] = "invalid_slot_id"
            else:
                # Build and validate climate payload using helper
                climate_payload, payload_errors = validate_and_build_slot_payload(user_input)
                errors.update(payload_errors)

                if not errors:
                    # Update slot
                    slot["label"] = label
                    slot["default_climate_payload"] = climate_payload

                    # Update excluded_entities
                    if excluded_entities:
                        slot["excluded_entities"] = excluded_entities
                    elif "excluded_entities" in slot:
                        # Remove if now empty
                        del slot["excluded_entities"]

                    # Validate
                    valid, error_msg = validate_slot_data(slot)
                    if not valid:
                        errors["base"] = "unknown"
                        _LOGGER.error("Slot validation failed: %s", error_msg)
                    else:
                        # Save
                        new_options = {**self.config_entry.options}
                        new_options[CONF_SLOTS] = slots
                        return self.async_create_entry(title="", data=new_options)

        # Get current payload
        current_payload = slot.get("default_climate_payload") or slot.get("climate_payload", {})
        current_excluded_entities = slot.get("excluded_entities") or []

        # Count bindings using this slot
        bindings = self.config_entry.options.get(CONF_BINDINGS, [])
        binding_count = sum(1 for b in bindings if b.get("slot_id") == slot_id)

        # Build suggested values dict for form pre-population
        # Convert aux_heat boolean to string for SelectSelector
        aux_heat_value = current_payload.get("aux_heat")
        if aux_heat_value is True:
            aux_heat_str = "on"
        elif aux_heat_value is False:
            aux_heat_str = "off"
        else:
            aux_heat_str = ""

        suggested_values = {
            "label": slot.get("label", ""),
            "temperature": current_payload.get("temperature"),
            "target_temp_high": current_payload.get("target_temp_high"),
            "target_temp_low": current_payload.get("target_temp_low"),
            "hvac_mode": current_payload.get("hvac_mode"),
            "preset_mode": current_payload.get("preset_mode", ""),
            "humidity": current_payload.get("humidity"),
            "aux_heat": aux_heat_str,
            "excluded_entities": current_excluded_entities,
        }

        schema = vol.Schema(
            {
                vol.Required("label"): cv.string,
                vol.Optional("temperature"): vol.Coerce(float),
                vol.Optional("target_temp_high"): vol.Coerce(float),
                vol.Optional("target_temp_low"): vol.Coerce(float),
                vol.Optional("hvac_mode"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["heat", "cool", "heat_cool", "auto", "off", "fan_only", "dry"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=False,
                    ),
                ),
                vol.Optional("preset_mode"): cv.string,
                vol.Optional("humidity"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                vol.Optional("aux_heat"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "", "label": "Not configured"},
                            {"value": "on", "label": "On"},
                            {"value": "off", "label": "Off"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional("excluded_entities"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="climate",
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="edit_slot_detail",
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
            description_placeholders={
                "slot_label": slot.get("label", ""),
                "slot_id": slot_id,
                "binding_count": str(binding_count),
            },
        )

    async def async_step_delete_slot(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle slot deletion."""
        from .const import CONF_SLOTS

        slots = self.config_entry.options.get(CONF_SLOTS, [])

        if not slots:
            return self.async_abort(reason="slot_not_found")

        if user_input is not None:
            slot_id = user_input.get("slot_id")

            # Remove slot
            new_options = {**self.config_entry.options}
            new_slots = [s for s in slots if s["id"] != slot_id]
            new_options[CONF_SLOTS] = new_slots

            return self.async_create_entry(title="", data=new_options)

        # Build slot selector
        slot_options = {slot["id"]: f"{slot['label']} ({slot['id']})" for slot in slots}

        schema = vol.Schema(
            {
                vol.Required("slot_id"): vol.In(slot_options),
            }
        )

        return self.async_show_form(
            step_id="delete_slot",
            data_schema=schema,
            description_placeholders={
                "slot_count": str(len(slots)),
            },
        )

    async def async_step_view_slots(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display all slots."""
        from .const import CONF_SLOTS

        slots = self.config_entry.options.get(CONF_SLOTS, [])

        if not slots:
            slots_summary = "No slots configured yet."
        else:
            slots_summary = "\n".join([
                f"• {slot['label']} (ID: {slot['id']})\n  Payload: {slot.get('default_climate_payload') or slot.get('climate_payload', {})}"
                for slot in slots
            ])

        # This is a display-only step, return to menu
        return self.async_show_menu(
            step_id="view_slots",
            menu_options=[],  # No options, user will go back
            description_placeholders={
                "slots_summary": slots_summary,
            },
        )

    async def async_step_bindings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show bindings management menu."""
        from .const import CONF_BINDINGS

        bindings = self.config_entry.options.get(CONF_BINDINGS, [])

        return self.async_show_menu(
            step_id="bindings",
            menu_options=["add_binding", "edit_binding", "delete_binding", "view_bindings"],
            description_placeholders={
                "binding_count": str(len(bindings)),
            },
        )

    async def async_step_add_binding(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new binding."""
        from .const import CONF_BINDINGS, CONF_SLOTS
        from .event_matcher import EventMatcher
        import hashlib

        errors = {}

        if user_input is not None:
            calendars = user_input.get("calendars", "*")
            match_type = user_input.get("match_type")
            match_value = user_input.get("match_value", "").strip()
            slot_id = user_input.get("slot_id")
            priority = user_input.get("priority")
            target_entities = user_input.get("target_entities")

            if not match_value:
                errors["match_value"] = "invalid_pattern"
            elif not slot_id:
                errors["slot_id"] = "invalid_slot_id"
            else:
                # Validate match config
                match_config = {"type": match_type, "value": match_value}
                valid, error_msg = EventMatcher.validate_match_config(match_config)

                if not valid:
                    errors["match_value"] = "invalid_pattern"
                    _LOGGER.error("Match config validation failed: %s", error_msg)
                else:
                    # Generate binding ID
                    source = f"binding_{calendars}_{match_type}:{match_value}_{slot_id}"
                    binding_id = hashlib.sha256(source.encode()).hexdigest()[:12]

                    # Create binding
                    new_binding = {
                        "id": binding_id,
                        "calendars": calendars,
                        "match": match_config,
                        "slot_id": slot_id,
                        "priority": priority if priority is not None else None,
                        "target_entities": target_entities if target_entities else None,
                    }

                    # Add to bindings
                    new_options = {**self.config_entry.options}
                    bindings = new_options.get(CONF_BINDINGS, [])
                    bindings.append(new_binding)
                    new_options[CONF_BINDINGS] = bindings

                    return self.async_create_entry(title="", data=new_options)

        # Get available slots and calendars
        slots = self.config_entry.options.get(CONF_SLOTS, [])
        calendar_entities = self.config_entry.data.get(CONF_CALENDAR_ENTITIES, [])

        if not slots:
            return self.async_abort(reason="slot_not_found")

        slot_options = {slot["id"]: f"{slot['label']}" for slot in slots}
        calendar_options = {"*": "All Calendars (*)", **{cal: cal for cal in calendar_entities}}

        schema = vol.Schema(
            {
                vol.Required("calendars", default="*"): vol.In(calendar_options),
                vol.Required("match_type", default="summary_contains"): vol.In({
                    "summary": "Exact Summary Match",
                    "summary_contains": "Summary Contains",
                    "regex": "Regular Expression",
                }),
                vol.Required("match_value"): cv.string,
                vol.Required("slot_id"): vol.In(slot_options),
                vol.Optional("priority"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=100))),
                vol.Optional("target_entities"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="climate",
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="add_binding",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_binding(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle binding editing selection."""
        from .const import CONF_BINDINGS

        bindings = self.config_entry.options.get(CONF_BINDINGS, [])

        if not bindings:
            return self.async_abort(reason="binding_not_found")

        if user_input is not None:
            self._temp_data["selected_binding_id"] = user_input.get("binding_id")
            return await self.async_step_edit_binding_detail()

        # Build binding selector
        binding_options = {
            b["id"]: f"{b.get('match', {}).get('value', 'Unknown')} → {b.get('slot_id', 'Unknown')}"
            for b in bindings
        }

        schema = vol.Schema(
            {
                vol.Required("binding_id"): vol.In(binding_options),
            }
        )

        return self.async_show_form(
            step_id="edit_binding",
            data_schema=schema,
            description_placeholders={
                "binding_count": str(len(bindings)),
            },
        )

    async def async_step_edit_binding_detail(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle binding editing details."""
        from .const import CONF_BINDINGS, CONF_SLOTS
        from .event_matcher import EventMatcher
        import hashlib

        binding_id = self._temp_data.get("selected_binding_id")
        if not binding_id:
            return await self.async_step_edit_binding()

        bindings = self.config_entry.options.get(CONF_BINDINGS, [])
        binding = next((b for b in bindings if b["id"] == binding_id), None)

        if not binding:
            return self.async_abort(reason="binding_not_found")

        errors = {}

        if user_input is not None:
            calendars = user_input.get("calendars", "*")
            match_type = user_input.get("match_type")
            match_value = user_input.get("match_value", "").strip()
            slot_id = user_input.get("slot_id")
            priority = user_input.get("priority")
            target_entities = user_input.get("target_entities")

            if not match_value:
                errors["match_value"] = "invalid_pattern"
            elif not slot_id:
                errors["slot_id"] = "invalid_slot_id"
            else:
                # Validate match config
                match_config = {"type": match_type, "value": match_value}
                valid, error_msg = EventMatcher.validate_match_config(match_config)

                if not valid:
                    errors["match_value"] = "invalid_pattern"
                    _LOGGER.error("Match config validation failed: %s", error_msg)
                else:
                    # Update binding
                    binding["calendars"] = calendars
                    binding["match"] = match_config
                    binding["slot_id"] = slot_id
                    binding["priority"] = priority if priority is not None else None
                    binding["target_entities"] = target_entities if target_entities else None

                    # Save
                    new_options = {**self.config_entry.options}
                    new_options[CONF_BINDINGS] = bindings
                    return self.async_create_entry(title="", data=new_options)

        # Get available slots and calendars
        slots = self.config_entry.options.get(CONF_SLOTS, [])
        calendar_entities = self.config_entry.data.get(CONF_CALENDAR_ENTITIES, [])

        if not slots:
            return self.async_abort(reason="slot_not_found")

        slot_options = {slot["id"]: f"{slot['label']}" for slot in slots}
        calendar_options = {"*": "All Calendars (*)", **{cal: cal for cal in calendar_entities}}

        # Get current values
        current_calendars = binding.get("calendars", "*")
        current_match = binding.get("match", {})
        current_match_type = current_match.get("type", "summary_contains")
        current_match_value = current_match.get("value", "")
        current_slot_id = binding.get("slot_id")
        current_priority = binding.get("priority")
        current_target_entities = binding.get("target_entities") or []

        schema = vol.Schema(
            {
                vol.Required("calendars", default=current_calendars): vol.In(calendar_options),
                vol.Required("match_type", default=current_match_type): vol.In({
                    "summary": "Exact Summary Match",
                    "summary_contains": "Summary Contains",
                    "regex": "Regular Expression",
                }),
                vol.Required("match_value", default=current_match_value): cv.string,
                vol.Required("slot_id", default=current_slot_id): vol.In(slot_options),
                vol.Optional("priority", default=current_priority): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=100))),
                vol.Optional("target_entities", default=current_target_entities): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="climate",
                        multiple=True,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="edit_binding_detail",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "binding_id": binding_id,
                "match_pattern": current_match_value,
            },
        )

    async def async_step_delete_binding(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle binding deletion."""
        from .const import CONF_BINDINGS

        bindings = self.config_entry.options.get(CONF_BINDINGS, [])

        if not bindings:
            return self.async_abort(reason="binding_not_found")

        if user_input is not None:
            binding_id = user_input.get("binding_id")

            # Remove binding
            new_options = {**self.config_entry.options}
            new_bindings = [b for b in bindings if b["id"] != binding_id]
            new_options[CONF_BINDINGS] = new_bindings

            return self.async_create_entry(title="", data=new_options)

        # Build binding selector
        binding_options = {
            b["id"]: f"{b.get('match', {}).get('value', 'Unknown')} → {b.get('slot_id', 'Unknown')}"
            for b in bindings
        }

        schema = vol.Schema(
            {
                vol.Required("binding_id"): vol.In(binding_options),
            }
        )

        return self.async_show_form(
            step_id="delete_binding",
            data_schema=schema,
            description_placeholders={
                "binding_count": str(len(bindings)),
            },
        )

    async def async_step_view_bindings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display all bindings."""
        from .const import CONF_BINDINGS

        bindings = self.config_entry.options.get(CONF_BINDINGS, [])

        if not bindings:
            bindings_summary = "No bindings configured yet."
        else:
            bindings_summary = "\n".join([
                f"• {b.get('match', {}).get('value', 'Unknown')} → Slot: {b.get('slot_id', 'Unknown')} (Priority: {b.get('priority', 'default')})"
                for b in bindings
            ])

        # This is a display-only step, return to menu
        return self.async_show_menu(
            step_id="view_bindings",
            menu_options=[],
            description_placeholders={
                "bindings_summary": bindings_summary,
            },
        )

    async def async_step_yaml_editor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show YAML editor menu."""
        return self.async_show_menu(
            step_id="yaml_editor",
            menu_options=["edit_slots_yaml", "edit_bindings_yaml", "edit_calendar_configs_yaml"],
        )

    async def async_step_edit_slots_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit slots in YAML format."""
        from .const import CONF_SLOTS
        import yaml

        errors = {}

        if user_input is not None:
            yaml_content = user_input.get("yaml_content", "").strip()

            try:
                new_slots = yaml.safe_load(yaml_content)

                if not isinstance(new_slots, list):
                    errors["yaml_content"] = "invalid_yaml"
                else:
                    # Validate all slots
                    from .helpers import validate_slot_data
                    for slot in new_slots:
                        valid, error_msg = validate_slot_data(slot)
                        if not valid:
                            errors["yaml_content"] = "invalid_yaml"
                            _LOGGER.error("Slot validation failed: %s", error_msg)
                            break

                    if not errors:
                        # Save
                        new_options = {**self.config_entry.options}
                        new_options[CONF_SLOTS] = new_slots
                        return self.async_create_entry(title="", data=new_options)

            except yaml.YAMLError as err:
                errors["yaml_content"] = "invalid_yaml"
                _LOGGER.error("YAML parsing failed: %s", err)

        # Get current slots as YAML
        slots = self.config_entry.options.get(CONF_SLOTS, [])
        try:
            import yaml
            current_yaml = yaml.dump(slots, default_flow_style=False, allow_unicode=True)
        except Exception as err:
            current_yaml = f"Error: {err}"

        schema = vol.Schema(
            {
                vol.Required("yaml_content", default=current_yaml): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        multiple=False,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="edit_slots_yaml",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "section": "Slots",
                "current_yaml": current_yaml,
            },
        )

    async def async_step_edit_bindings_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit bindings in YAML format."""
        from .const import CONF_BINDINGS
        import yaml

        errors = {}

        if user_input is not None:
            yaml_content = user_input.get("yaml_content", "").strip()

            try:
                new_bindings = yaml.safe_load(yaml_content)

                if not isinstance(new_bindings, list):
                    errors["yaml_content"] = "invalid_yaml"
                else:
                    # Basic validation
                    from .event_matcher import EventMatcher
                    for binding in new_bindings:
                        if "match" in binding:
                            valid, error_msg = EventMatcher.validate_match_config(binding["match"])
                            if not valid:
                                errors["yaml_content"] = "invalid_yaml"
                                break

                    if not errors:
                        # Save
                        new_options = {**self.config_entry.options}
                        new_options[CONF_BINDINGS] = new_bindings
                        return self.async_create_entry(title="", data=new_options)

            except yaml.YAMLError as err:
                errors["yaml_content"] = "invalid_yaml"
                _LOGGER.error("YAML parsing failed: %s", err)

        # Get current bindings as YAML
        bindings = self.config_entry.options.get(CONF_BINDINGS, [])
        try:
            import yaml
            current_yaml = yaml.dump(bindings, default_flow_style=False, allow_unicode=True)
        except Exception as err:
            current_yaml = f"Error: {err}"

        schema = vol.Schema(
            {
                vol.Required("yaml_content", default=current_yaml): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        multiple=False,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="edit_bindings_yaml",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "section": "Bindings",
                "current_yaml": current_yaml,
            },
        )

    async def async_step_edit_calendar_configs_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit calendar configs in YAML format."""
        from .const import CONF_CALENDAR_CONFIGS
        import yaml

        errors = {}

        if user_input is not None:
            yaml_content = user_input.get("yaml_content", "").strip()

            try:
                new_configs = yaml.safe_load(yaml_content)

                if not isinstance(new_configs, dict):
                    errors["yaml_content"] = "invalid_yaml"
                else:
                    # Save
                    new_options = {**self.config_entry.options}
                    new_options[CONF_CALENDAR_CONFIGS] = new_configs
                    return self.async_create_entry(title="", data=new_options)

            except yaml.YAMLError as err:
                errors["yaml_content"] = "invalid_yaml"
                _LOGGER.error("YAML parsing failed: %s", err)

        # Get current calendar configs as YAML
        calendar_configs = self.config_entry.options.get(CONF_CALENDAR_CONFIGS, {})
        try:
            import yaml
            current_yaml = yaml.dump(calendar_configs, default_flow_style=False, allow_unicode=True)
        except Exception as err:
            current_yaml = f"Error: {err}"

        schema = vol.Schema(
            {
                vol.Required("yaml_content", default=current_yaml): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        multiple=False,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="edit_calendar_configs_yaml",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "section": "Calendar Configs",
                "current_yaml": current_yaml,
            },
        )
