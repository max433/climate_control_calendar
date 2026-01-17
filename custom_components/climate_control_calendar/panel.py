"""
Frontend panel registration for Climate Control Calendar.

Registers custom dashboard panel in Home Assistant sidebar.
"""
from __future__ import annotations

import logging
import os

from homeassistant.components import panel_custom
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PANEL_TITLE = "Climate Control"
PANEL_ICON = "mdi:calendar-clock"
PANEL_URL_PATH = "climate_control_calendar"
PANEL_COMPONENT_NAME = "climate-control-panel"


async def async_register_panel(hass: HomeAssistant) -> None:
    """
    Register climate control calendar dashboard panel.

    Creates a custom panel in Home Assistant sidebar with icon.
    """
    # Get path to frontend directory
    integration_dir = os.path.dirname(__file__)
    frontend_dir = os.path.join(integration_dir, "frontend")

    # Register frontend directory as static path
    # This serves all files from frontend/ at /_ccc_static/
    hass.http.register_static_path(
        "/_ccc_static",
        frontend_dir,
        cache_headers=False,
    )

    # Register as custom panel using panel_custom component
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT_NAME,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        js_url="/_ccc_static/climate-control-panel.js",
        module_url=None,
        embed_iframe=False,
        require_admin=False,
        config=None,
    )

    _LOGGER.info(
        "Climate Control Calendar dashboard panel registered at: /%s",
        PANEL_URL_PATH,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """
    Unregister climate control calendar dashboard panel.
    """
    # Remove panel from frontend
    hass.components.frontend.async_remove_panel(PANEL_URL_PATH)
    _LOGGER.info("Climate Control Calendar dashboard panel unregistered")
