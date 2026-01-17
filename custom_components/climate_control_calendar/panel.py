"""
Frontend panel registration for Climate Control Calendar.

Registers custom dashboard panel in Home Assistant sidebar.
Uses iframe panel approach for HACS custom integrations.
"""
from __future__ import annotations

import logging

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant

from .http_views import DashboardView

_LOGGER = logging.getLogger(__name__)

PANEL_TITLE = "Climate Control"
PANEL_ICON = "mdi:calendar-clock"
PANEL_URL_PATH = "climate_control_calendar"


async def async_register_panel(hass: HomeAssistant) -> None:
    """
    Register climate control calendar dashboard panel.

    Creates an iframe panel in Home Assistant sidebar that points to
    a custom HTTP endpoint serving the dashboard HTML.

    This approach works for HACS custom integrations.
    """
    # Register HTTP view to serve dashboard HTML
    hass.http.register_view(DashboardView)

    # Register iframe panel in sidebar
    async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={"url": DashboardView.url},
        require_admin=False,
    )

    _LOGGER.info(
        "Climate Control Calendar dashboard panel registered at: /%s (iframe → %s)",
        PANEL_URL_PATH,
        DashboardView.url,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """
    Unregister climate control calendar dashboard panel.
    """
    # Remove panel from frontend
    hass.components.frontend.async_remove_panel(PANEL_URL_PATH)
    _LOGGER.info("Climate Control Calendar dashboard panel unregistered")
