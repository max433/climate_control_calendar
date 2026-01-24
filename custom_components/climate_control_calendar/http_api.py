"""HTTP API endpoints for Climate Control Calendar frontend."""
import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DATA_CONFIG,
    CONF_SLOTS,
    CONF_BINDINGS,
    CONF_CALENDAR_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)

# Log module import
_LOGGER.warning("🔥 http_api.py MODULE LOADED - This should appear in logs!")


class ClimateControlConfigView(HomeAssistantView):
    """View to handle config data requests from frontend."""

    url = f"/api/{DOMAIN}/config"
    name = f"api:{DOMAIN}:config"
    requires_auth = True

    def __init__(self, hass: HomeAssistant):
        """Initialize the view."""
        self.hass = hass
        _LOGGER.warning("🔥 ClimateControlConfigView.__init__ called")

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for configuration data."""
        _LOGGER.warning("🔥 HTTP API: GET /api/%s/config - REQUEST RECEIVED!", DOMAIN)

        try:
            # Get first available config entry data
            for entry_data in self.hass.data.get(DOMAIN, {}).values():
                config = entry_data.get(DATA_CONFIG, {})

                slots = config.get(CONF_SLOTS, [])
                bindings = config.get(CONF_BINDINGS, [])
                calendars = config.get(CONF_CALENDAR_ENTITIES, [])
                climate_entities = config.get("climate_entities", [])
                calendar_configs = config.get("calendar_configs", {})
                dry_run = config.get("dry_run", True)
                debug_mode = config.get("debug_mode", False)

                _LOGGER.info(
                    "HTTP API: Returning config - slots=%d, bindings=%d, calendars=%d",
                    len(slots),
                    len(bindings),
                    len(calendars),
                )

                return self.json({
                    "slots": slots,
                    "bindings": bindings,
                    "calendars": calendars,
                    "climate_entities": climate_entities,
                    "calendar_configs": calendar_configs,
                    "dry_run": dry_run,
                    "debug_mode": debug_mode,
                })

            # No config found
            _LOGGER.warning("HTTP API: No config data found")
            return self.json({
                "slots": [],
                "bindings": [],
                "calendars": [],
                "climate_entities": [],
                "dry_run": True,
                "debug_mode": False,
            })

        except Exception as err:
            _LOGGER.error("HTTP API: Error getting config: %s", err, exc_info=True)
            return self.json_message(
                f"Error getting configuration: {err}",
                status_code=500
            )

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to update basic configuration."""
        _LOGGER.warning("🔥 HTTP API: POST /api/%s/config - REQUEST RECEIVED!", DOMAIN)

        try:
            data = await request.json()
            _LOGGER.info("HTTP API: Received update data: %s", data)

            # Get first config entry
            config_entry = None
            for entry_id in self.hass.data.get(DOMAIN, {}).keys():
                config_entry = self.hass.config_entries.async_get_entry(entry_id)
                if config_entry:
                    break

            if not config_entry:
                return self.json_message("No config entry found", status_code=404)

            # Update data (immutable fields: calendars, dry_run, debug_mode)
            new_data = {**config_entry.data}
            if "calendar_entities" in data:
                new_data[CONF_CALENDAR_ENTITIES] = data["calendar_entities"]
            if "dry_run" in data:
                new_data["dry_run"] = data["dry_run"]
            if "debug_mode" in data:
                new_data["debug_mode"] = data["debug_mode"]

            # Update options (mutable fields: climate_entities, calendar_configs)
            new_options = {**config_entry.options}
            if "climate_entities" in data:
                new_options["climate_entities"] = data["climate_entities"]
            if "calendar_configs" in data:
                new_options["calendar_configs"] = data["calendar_configs"]

            # Apply updates
            self.hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                options=new_options,
            )

            _LOGGER.info("HTTP API: Config updated successfully")
            return self.json({"status": "ok", "message": "Configuration updated"})

        except Exception as err:
            _LOGGER.error("HTTP API: Error updating config: %s", err, exc_info=True)
            return self.json_message(
                f"Error updating configuration: {err}",
                status_code=500
            )


async def async_register_api(hass: HomeAssistant) -> None:
    """Register HTTP API endpoints."""
    _LOGGER.warning("🔥 async_register_api CALLED - Registering HTTP API for %s", DOMAIN)

    # Register config endpoint
    view = ClimateControlConfigView(hass)
    hass.http.register_view(view)

    _LOGGER.warning("🔥 HTTP API VIEW REGISTERED: /api/%s/config", DOMAIN)
    _LOGGER.warning("🔥 View URL: %s", view.url)
    _LOGGER.warning("🔥 View name: %s", view.name)
