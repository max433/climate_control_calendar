"""Panel registration for Climate Control Calendar."""
import logging
from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .http_api import async_register_api

_LOGGER = logging.getLogger(__name__)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Climate Control Calendar panel in the Home Assistant sidebar.

    This creates a custom panel accessible from the sidebar that displays
    the test HTML interface for the integration.
    """
    # Use WARNING to ensure it shows up in logs
    _LOGGER.warning("🚀 PANEL REGISTRATION STARTING - Climate Control Calendar")

    try:
        # Get the path to our www directory
        integration_path = Path(__file__).parent
        www_path = integration_path / "www"

        _LOGGER.warning(
            "📁 Registering Climate Control Calendar panel. WWW path: %s",
            www_path
        )

        # Step 1: Register static file path
        # This makes files in /www available at /{DOMAIN}/static/
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path=f"/{DOMAIN}/static",
                path=str(www_path),
                cache_headers=False,  # Disable caching for easier development
            )
        ])
        _LOGGER.warning("✅ Static path registered: /%s/static -> %s", DOMAIN, www_path)

        # Step 2: Register HTTP API for frontend data access
        await async_register_api(hass)
        _LOGGER.warning("✅ HTTP API registered: /api/%s/config", DOMAIN)

        # Step 3: Register the panel in the sidebar
        _LOGGER.warning("📋 Calling async_register_built_in_panel...")
        async_register_built_in_panel(
            hass,
            component_name="custom",  # Use 'custom' for custom panels
            sidebar_title="Climate Control",  # Title shown in sidebar
            sidebar_icon="mdi:thermometer-lines",  # Icon in sidebar
            frontend_url_path=DOMAIN,  # URL path: /climate_control_calendar
            config={
                "name": "climate-panel-card",  # Must match custom element name
                "_panel_custom": {
                    "name": "climate-panel-card",  # Custom element tag name
                    "embed_iframe": True,  # CRITICAL: Embed in iframe to avoid conflicts
                    "trust": False,  # Don't trust external content
                    "js_url": f"/{DOMAIN}/static/climate-panel.js",  # Path to JS file
                }
            },
            require_admin=False,  # Allow non-admin users to see the panel
        )

        _LOGGER.warning(
            "✅ Climate Control Calendar panel registered successfully at /%s",
            DOMAIN
        )

    except Exception as err:
        _LOGGER.error(
            "Failed to register Climate Control Calendar panel: %s",
            err,
            exc_info=True
        )
        raise


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the panel when the integration is unloaded."""
    from homeassistant.components.frontend import async_remove_panel

    try:
        # Check if panel exists before removing
        if hass.data.get("frontend_panels", {}).get(DOMAIN):
            _LOGGER.info("Removing Climate Control Calendar panel")
            async_remove_panel(hass, DOMAIN)
        else:
            _LOGGER.debug("Panel %s not found, skipping removal", DOMAIN)

    except Exception as err:
        _LOGGER.error(
            "Failed to unregister Climate Control Calendar panel: %s",
            err,
            exc_info=True
        )
