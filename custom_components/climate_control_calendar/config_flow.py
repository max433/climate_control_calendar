"""Config flow for Climate Control Calendar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_CLIMATE_ENTITIES,
    CONF_DRY_RUN,
    CONF_DEBUG_MODE,
    DEFAULT_DRY_RUN,
    DEFAULT_DEBUG_MODE,
)

_LOGGER = logging.getLogger(__name__)


class ClimateControlCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Climate Control Calendar."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._calendar_entity: str | None = None
        self._climate_entities: list[str] = []
        self._dry_run: bool = DEFAULT_DRY_RUN
        self._debug_mode: bool = DEFAULT_DEBUG_MODE

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - calendar selection."""
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
            self._calendar_entity = user_input[CONF_CALENDAR_ENTITY]

            # Verify calendar entity exists
            if self.hass.states.get(self._calendar_entity) is None:
                errors[CONF_CALENDAR_ENTITY] = "calendar_not_found"
            else:
                # Check if already configured
                await self.async_set_unique_id(self._calendar_entity)
                self._abort_if_unique_id_configured()

                # Proceed to climate entities selection
                return await self.async_step_climate()

        # Build schema for calendar selection
        schema = vol.Schema(
            {
                vol.Required(CONF_CALENDAR_ENTITY): vol.In(
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
                "calendar_entity": self._calendar_entity or "",
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

            # Create the config entry
            return self.async_create_entry(
                title=f"Climate Control ({self._calendar_entity})",
                data={
                    CONF_CALENDAR_ENTITY: self._calendar_entity,
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
                "calendar_entity": self._calendar_entity or "",
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        climate_entities = [
            state.entity_id
            for state in self.hass.states.async_all("climate")
        ]

        current_climate = self.config_entry.options.get(CONF_CLIMATE_ENTITIES, [])
        current_dry_run = self.config_entry.data.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
        current_debug = self.config_entry.data.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CLIMATE_ENTITIES, default=current_climate
                ): cv.multi_select({entity: entity for entity in climate_entities}),
                vol.Optional(CONF_DRY_RUN, default=current_dry_run): cv.boolean,
                vol.Optional(CONF_DEBUG_MODE, default=current_debug): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "calendar_entity": self.config_entry.data.get(CONF_CALENDAR_ENTITY, ""),
            },
        )
