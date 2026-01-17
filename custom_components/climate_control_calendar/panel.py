"""
Frontend panel registration for Climate Control Calendar.

Registers custom dashboard panel in Home Assistant sidebar.
"""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "/climate_control_calendar_dashboard"
PANEL_TITLE = "Climate Control"
PANEL_ICON = "mdi:calendar-clock"
PANEL_COMPONENT_NAME = "climate-control-panel"


async def async_register_panel(hass: HomeAssistant) -> None:
    """
    Register climate control calendar dashboard panel.

    Creates a custom panel in Home Assistant sidebar with icon.
    """
    # Get path to frontend JS file
    integration_dir = os.path.dirname(__file__)
    frontend_dir = os.path.join(integration_dir, "frontend")
    panel_js_path = os.path.join(frontend_dir, "climate-control-panel.js")

    # Register panel
    await hass.http.async_register_static_path(
        PANEL_URL + "/climate-control-panel.js",
        panel_js_path,
        cache_headers=False,
    )

    # Register as custom panel
    hass.components.frontend.async_register_built_in_panel(
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path="climate_control_calendar",
        config={
            "_panel_custom": {
                "name": PANEL_COMPONENT_NAME,
                "embed_iframe": False,
                "trust_external": False,
                "js_url": PANEL_URL + "/climate-control-panel.js",
            }
        },
        require_admin=False,
    )

    _LOGGER.info(
        "Climate Control Calendar dashboard panel registered at: %s",
        PANEL_URL,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """
    Unregister climate control calendar dashboard panel.
    """
    # Remove panel from frontend
    hass.components.frontend.async_remove_panel("climate_control_calendar")
    _LOGGER.info("Climate Control Calendar dashboard panel unregistered")
