"""HTTP API endpoints for Climate Control Calendar frontend."""
import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DATA_CONFIG,
    DATA_ENGINE,
    DATA_COORDINATOR,
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


class ClimateControlStatusView(HomeAssistantView):
    """View to handle status/monitoring data requests from frontend."""

    url = f"/api/{DOMAIN}/status"
    name = f"api:{DOMAIN}:status"
    requires_auth = True

    def __init__(self, hass: HomeAssistant):
        """Initialize the view."""
        self.hass = hass
        _LOGGER.warning("🔥 ClimateControlStatusView.__init__ called")

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for status/monitoring data."""
        _LOGGER.info("HTTP API: GET /api/%s/status - REQUEST RECEIVED!", DOMAIN)

        try:
            # Get first available config entry data
            for entry_data in self.hass.data.get(DOMAIN, {}).values():
                config = entry_data.get(DATA_CONFIG, {})
                engine = entry_data.get(DATA_ENGINE)
                coordinator = entry_data.get(DATA_COORDINATOR)

                # Get configuration
                slots = config.get(CONF_SLOTS, [])
                bindings = config.get(CONF_BINDINGS, [])
                calendars = config.get(CONF_CALENDAR_ENTITIES, [])
                climate_entities = config.get("climate_entities", [])

                # Get climate entities states
                climate_states = []
                for entity_id in climate_entities:
                    state = self.hass.states.get(entity_id)
                    if state:
                        climate_states.append({
                            "entity_id": entity_id,
                            "state": state.state,
                            "attributes": dict(state.attributes),
                            "last_changed": state.last_changed.isoformat(),
                            "last_updated": state.last_updated.isoformat(),
                        })

                # Get active calendar events
                active_events = []
                from datetime import datetime, timedelta
                now = datetime.now()

                for calendar_id in calendars:
                    # Get calendar state
                    cal_state = self.hass.states.get(calendar_id)
                    if cal_state and cal_state.state == "on":
                        # Calendar has an active event
                        attrs = cal_state.attributes
                        active_events.append({
                            "calendar_id": calendar_id,
                            "summary": attrs.get("message", ""),
                            "description": attrs.get("description", ""),
                            "start": attrs.get("start_time", ""),
                            "end": attrs.get("end_time", ""),
                            "location": attrs.get("location", ""),
                            "all_day": attrs.get("all_day", False),
                        })

                # Try to get engine state if available
                engine_state = {
                    "has_engine": engine is not None,
                    "last_evaluation": None,
                    "active_slot": None,
                }

                if engine and hasattr(engine, '_last_evaluation_time'):
                    engine_state["last_evaluation"] = engine._last_evaluation_time.isoformat() if engine._last_evaluation_time else None

                # Get matched bindings (from last evaluation if available)
                matched_bindings = []
                if engine and hasattr(engine, '_last_matched_bindings'):
                    matched_bindings = engine._last_matched_bindings or []

                return self.json({
                    "timestamp": now.isoformat(),
                    "active_events": active_events,
                    "climate_states": climate_states,
                    "matched_bindings": matched_bindings,
                    "engine_state": engine_state,
                    "summary": {
                        "total_slots": len(slots),
                        "total_bindings": len(bindings),
                        "total_calendars": len(calendars),
                        "total_climates": len(climate_entities),
                        "active_events_count": len(active_events),
                        "climates_on": len([c for c in climate_states if c["state"] != "off"]),
                    }
                })

            # No config found
            _LOGGER.warning("HTTP API: No status data found")
            return self.json({
                "timestamp": datetime.now().isoformat(),
                "active_events": [],
                "climate_states": [],
                "matched_bindings": [],
                "engine_state": {"has_engine": False},
                "summary": {
                    "total_slots": 0,
                    "total_bindings": 0,
                    "total_calendars": 0,
                    "total_climates": 0,
                    "active_events_count": 0,
                    "climates_on": 0,
                }
            })

        except Exception as err:
            _LOGGER.error("HTTP API: Error getting status: %s", err, exc_info=True)
            return self.json_message(
                f"Error getting status: {err}",
                status_code=500
            )


async def async_register_api(hass: HomeAssistant) -> None:
    """Register HTTP API endpoints."""
    _LOGGER.warning("🔥 async_register_api CALLED - Registering HTTP API for %s", DOMAIN)

    # Register config endpoint
    config_view = ClimateControlConfigView(hass)
    hass.http.register_view(config_view)

    # Register status endpoint
    status_view = ClimateControlStatusView(hass)
    hass.http.register_view(status_view)

    _LOGGER.warning("🔥 HTTP API VIEWS REGISTERED:")
    _LOGGER.warning("🔥   - /api/%s/config", DOMAIN)
    _LOGGER.warning("🔥   - /api/%s/status", DOMAIN)
