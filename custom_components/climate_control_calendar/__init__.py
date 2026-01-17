"""Climate Control Calendar integration for Home Assistant."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITIES,  # Changed from CONF_CALENDAR_ENTITY (Decision D033)
    CONF_CLIMATE_ENTITIES,
    CONF_DRY_RUN,
    CONF_DEBUG_MODE,
    CONF_SLOTS,
    CONF_BINDINGS,  # New: bindings (Decision D032)
    CONF_CALENDAR_CONFIGS,  # New: calendar configs
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_EVENT_EMITTER,
    DATA_APPLIER,
    DATA_BINDING_MANAGER,  # New: binding manager
    DATA_DASHBOARD_SERVICE,  # New: dashboard service
    DATA_CONFIG,
    DATA_UNSUB,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_DRY_RUN,
    DEFAULT_DEBUG_MODE,
)
from .coordinator import ClimateControlCalendarCoordinator
from .engine import ClimateControlEngine
from .events import EventEmitter
from .applier import ClimatePayloadApplier
from .binding_manager import BindingManager  # New import
from .dashboard_service import DashboardDataService  # Dashboard service
from .services import async_setup_services, async_unload_services
from . import websocket  # WebSocket API
from . import panel  # Frontend panel

_LOGGER = logging.getLogger(__name__)

# Platforms to be set up (will be extended in future milestones)
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up Climate Control Calendar from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup successful, False otherwise
    """
    _LOGGER.info("Setting up Climate Control Calendar integration")

    # Get configuration from data (immutable)
    calendar_entities = entry.data.get(CONF_CALENDAR_ENTITIES, [])  # Changed to plural (Decision D033)
    dry_run = entry.data.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
    debug_mode = entry.data.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

    # Get configuration from options (mutable)
    climate_entities = entry.options.get(CONF_CLIMATE_ENTITIES, [])
    slots = entry.options.get(CONF_SLOTS, [])
    bindings = entry.options.get(CONF_BINDINGS, [])  # New: bindings (Decision D032)
    calendar_configs = entry.options.get(CONF_CALENDAR_CONFIGS, {})  # New: calendar configs

    if not calendar_entities:
        _LOGGER.error("No calendar entities configured")
        return False

    # Verify all calendar entities exist
    missing_calendars = [
        cal for cal in calendar_entities
        if not hass.states.get(cal)
    ]
    if missing_calendars:
        raise ConfigEntryNotReady(
            f"Calendar entities not found: {missing_calendars}. "
            "Please ensure the calendar integration is loaded."
        )

    # Create event emitter
    event_emitter = EventEmitter(hass, entry.entry_id)

    # Create binding manager (New architecture: with calendar_configs)
    binding_manager = BindingManager(
        hass=hass,
        entry_id=entry.entry_id,
        calendar_configs=calendar_configs,  # New parameter
    )

    # Load bindings from config entry
    await binding_manager.async_load(bindings=bindings)

    # Create climate payload applier
    applier = ClimatePayloadApplier(
        hass=hass,
        event_emitter=event_emitter,
    )

    # Create engine (Decision D032: now with binding_manager, D035: removed flag_manager)
    engine = ClimateControlEngine(
        hass=hass,
        entry_id=entry.entry_id,
        event_emitter=event_emitter,
        binding_manager=binding_manager,  # New parameter
        applier=applier,
        dry_run=dry_run,
        debug_mode=debug_mode,
    )

    # Create coordinator (Decision D033: multi-calendar support)
    coordinator = ClimateControlCalendarCoordinator(
        hass=hass,
        calendar_entity_id=calendar_entities,  # Now passes list of calendar IDs
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create dashboard service for frontend panel
    dashboard_service = DashboardDataService(
        hass=hass,
        coordinator=coordinator,
        engine=engine,
        binding_manager=binding_manager,
        config_entry=entry,
    )

    # Store components in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_ENGINE: engine,
        DATA_EVENT_EMITTER: event_emitter,
        DATA_APPLIER: applier,
        DATA_BINDING_MANAGER: binding_manager,  # New: store binding manager
        DATA_DASHBOARD_SERVICE: dashboard_service,  # New: store dashboard service
        DATA_CONFIG: {
            CONF_CALENDAR_ENTITIES: calendar_entities,  # Changed from singular
            CONF_DRY_RUN: dry_run,
            CONF_DEBUG_MODE: debug_mode,
            CONF_CLIMATE_ENTITIES: climate_entities,
            CONF_SLOTS: slots,
            CONF_BINDINGS: bindings,  # New: store bindings
            CONF_CALENDAR_CONFIGS: calendar_configs,  # New: store calendar configs
        },
        DATA_UNSUB: [],
    }

    # Set up coordinator listener to trigger engine evaluation (Decision D032)
    async def _async_handle_coordinator_update() -> None:
        """Handle coordinator updates by running engine evaluation (async implementation)."""
        # Get active events from multi-calendar coordinator
        active_events = coordinator.get_active_events()

        # Run engine evaluation with event-based resolution
        result = await engine.evaluate(
            active_events=active_events,  # Changed from calendar_state
            slots=slots,
            climate_entities=climate_entities,
        )

        if debug_mode:
            _LOGGER.debug(
                "Engine evaluation complete | Active slot: %s | Changed: %s | Forced: %s | Events: %d",
                result.get("active_slot_id"),
                result.get("changed"),
                result.get("forced"),
                result.get("active_events_count", 0),
            )

    def _handle_coordinator_update() -> None:
        """Handle coordinator updates (sync wrapper for listener)."""
        hass.async_create_task(_async_handle_coordinator_update())

    # Register coordinator listener
    unsub_coordinator = coordinator.async_add_listener(_handle_coordinator_update)
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB].append(unsub_coordinator)

    # Trigger initial engine evaluation
    await _async_handle_coordinator_update()

    # Set up platforms (empty for now, will be added in future milestones)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services, WebSocket handlers, and dashboard panel - only on first entry
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)
        websocket.async_register_websocket_handlers(hass)
        await panel.async_register_panel(hass)

    _LOGGER.info(
        "Climate Control Calendar setup complete. "
        "Calendars: %d, Dry Run: %s, Slots: %d, Bindings: %d, Climate entities: %d, "
        "Calendar configs: %d",
        len(calendar_entities),
        dry_run,
        len(slots),
        len(bindings),
        len(climate_entities),
        len(calendar_configs),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload successful
    """
    _LOGGER.info("Unloading Climate Control Calendar integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cleanup stored data
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)

        # Cancel any subscriptions
        for unsub in entry_data.get(DATA_UNSUB, []):
            unsub()

        # Unload services and panel if last entry
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            await panel.async_unregister_panel(hass)

        _LOGGER.info("Climate Control Calendar unloaded successfully")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload config entry when options change.

    Args:
        hass: Home Assistant instance
        entry: Config entry to reload
    """
    _LOGGER.info("Reloading Climate Control Calendar integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Migrate old config entry to new format.

    Args:
        hass: Home Assistant instance
        entry: Config entry to migrate

    Returns:
        True if migration successful
    """
    _LOGGER.debug("Migrating Climate Control Calendar config entry from version %s", entry.version)

    # Currently version 1, no migration needed
    # Future versions will implement migration logic here

    return True
