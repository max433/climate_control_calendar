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


class ClimateControlConfigView(HomeAssistantView):
    """View to handle config data requests from frontend."""

    url = f"/api/{DOMAIN}/config"
    name = f"api:{DOMAIN}:config"
    requires_auth = True

    def __init__(self, hass: HomeAssistant):
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for configuration data."""
        _LOGGER.info("HTTP API: GET /api/%s/config", DOMAIN)

        try:
            # Get first available config entry data
            for entry_data in self.hass.data.get(DOMAIN, {}).values():
                config = entry_data.get(DATA_CONFIG, {})

                slots = config.get(CONF_SLOTS, [])
                bindings = config.get(CONF_BINDINGS, [])
                calendars = config.get(CONF_CALENDAR_ENTITIES, [])

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
                })

            # No config found
            _LOGGER.warning("HTTP API: No config data found")
            return self.json({
                "slots": [],
                "bindings": [],
                "calendars": [],
            })

        except Exception as err:
            _LOGGER.error("HTTP API: Error getting config: %s", err, exc_info=True)
            return self.json_message(
                f"Error getting configuration: {err}",
                status_code=500
            )


async def async_register_api(hass: HomeAssistant) -> None:
    """Register HTTP API endpoints."""
    _LOGGER.info("Registering HTTP API endpoints for %s", DOMAIN)

    # Register config endpoint
    hass.http.register_view(ClimateControlConfigView(hass))

    _LOGGER.info("HTTP API endpoints registered: /api/%s/config", DOMAIN)
