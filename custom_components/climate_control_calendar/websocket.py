"""
WebSocket API for Climate Control Calendar dashboard.

Provides real-time data access for frontend panel.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket command handlers."""
    websocket_api.async_register_command(hass, ws_get_live_state)
    websocket_api.async_register_command(hass, ws_get_timeline)
    websocket_api.async_register_command(hass, ws_subscribe_updates)
    _LOGGER.info("Climate Control Calendar WebSocket handlers registered")


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/get_live_state",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_get_live_state(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """
    Get current live state of the system.

    Returns active slot, trigger reason, affected entities.
    """
    entry_id = msg["entry_id"]

    # Get dashboard service from hass.data
    if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
        connection.send_error(
            msg["id"], "not_found", f"Integration entry {entry_id} not found"
        )
        return

    dashboard_service = hass.data[DOMAIN][entry_id].get("dashboard_service")
    if not dashboard_service:
        connection.send_error(
            msg["id"], "not_loaded", "Dashboard service not initialized"
        )
        return

    try:
        data = await dashboard_service.get_live_state()
        connection.send_result(msg["id"], data)
    except Exception as err:
        _LOGGER.exception("Error getting live state: %s", err)
        connection.send_error(msg["id"], "unknown_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/get_timeline",
        vol.Required("entry_id"): str,
        vol.Optional("date"): str,  # ISO format YYYY-MM-DD
    }
)
@websocket_api.async_response
async def ws_get_timeline(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """
    Get timeline for specific date.

    Returns events with matched bindings, slots, and coverage analysis.
    """
    entry_id = msg["entry_id"]

    # Get dashboard service from hass.data
    if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
        connection.send_error(
            msg["id"], "not_found", f"Integration entry {entry_id} not found"
        )
        return

    dashboard_service = hass.data[DOMAIN][entry_id].get("dashboard_service")
    if not dashboard_service:
        connection.send_error(
            msg["id"], "not_loaded", "Dashboard service not initialized"
        )
        return

    # Parse date if provided
    date = None
    if "date" in msg:
        try:
            date_str = msg["date"]
            date = dt_util.parse_datetime(f"{date_str}T00:00:00")
        except (ValueError, TypeError) as err:
            connection.send_error(
                msg["id"], "invalid_format", f"Invalid date format: {err}"
            )
            return

    try:
        data = await dashboard_service.get_timeline(date)
        connection.send_result(msg["id"], data)
    except Exception as err:
        _LOGGER.exception("Error getting timeline: %s", err)
        connection.send_error(msg["id"], "unknown_error", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/subscribe_updates",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_subscribe_updates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """
    Subscribe to real-time updates.

    Sends update notifications when coordinator refreshes data.
    """
    entry_id = msg["entry_id"]

    # Get coordinator from hass.data
    if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
        connection.send_error(
            msg["id"], "not_found", f"Integration entry {entry_id} not found"
        )
        return

    coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
    if not coordinator:
        connection.send_error(
            msg["id"], "not_loaded", "Coordinator not initialized"
        )
        return

    @callback
    def forward_update() -> None:
        """Forward coordinator update to WebSocket client."""
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {"type": "update", "timestamp": dt_util.now().isoformat()},
            )
        )

    # Subscribe to coordinator updates
    # Coordinator uses async_add_listener for updates
    remove_listener = coordinator.async_add_listener(forward_update)

    # Store unsubscribe function
    @callback
    def unsubscribe() -> None:
        """Unsubscribe from updates."""
        remove_listener()

    connection.subscriptions[msg["id"]] = unsubscribe

    # Send success response
    connection.send_result(msg["id"], {"success": True})
