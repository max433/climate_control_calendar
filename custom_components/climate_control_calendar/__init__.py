"""Climate Control Calendar integration for Home Assistant."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    CONF_CALENDAR_ENTITY,
    CONF_CLIMATE_ENTITIES,
    CONF_DRY_RUN,
    CONF_DEBUG_MODE,
    CONF_SLOTS,
    DATA_COORDINATOR,
    DATA_ENGINE,
    DATA_EVENT_EMITTER,
    DATA_FLAG_MANAGER,
    DATA_APPLIER,
    DATA_CONFIG,
    DATA_UNSUB,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_DRY_RUN,
    DEFAULT_DEBUG_MODE,
)
from .coordinator import ClimateControlCalendarCoordinator
from .engine import ClimateControlEngine
from .events import EventEmitter
from .flag_manager import FlagManager
from .applier import ClimatePayloadApplier
from .services import async_setup_services, async_unload_services

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
    calendar_entity_id = entry.data.get(CONF_CALENDAR_ENTITY)
    dry_run = entry.data.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
    debug_mode = entry.data.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)

    # Get configuration from options (mutable)
    climate_entities = entry.options.get(CONF_CLIMATE_ENTITIES, [])
    slots = entry.options.get(CONF_SLOTS, [])

    if not calendar_entity_id:
        _LOGGER.error("No calendar entity configured")
        return False

    # Verify calendar entity exists
    if not hass.states.get(calendar_entity_id):
        raise ConfigEntryNotReady(
            f"Calendar entity not found: {calendar_entity_id}. "
            "Please ensure the calendar integration is loaded."
        )

    # Create event emitter
    event_emitter = EventEmitter(hass, entry.entry_id)

    # Create flag manager (M3)
    flag_manager = FlagManager(
        hass=hass,
        entry_id=entry.entry_id,
        event_emitter=event_emitter,
    )

    # Load flags from storage
    await flag_manager.async_load()

    # Create climate payload applier (M3)
    applier = ClimatePayloadApplier(
        hass=hass,
        event_emitter=event_emitter,
    )

    # Create engine (with M3 enhancements)
    engine = ClimateControlEngine(
        hass=hass,
        entry_id=entry.entry_id,
        event_emitter=event_emitter,
        flag_manager=flag_manager,
        applier=applier,
        dry_run=dry_run,
        debug_mode=debug_mode,
    )

    # Create coordinator
    coordinator = ClimateControlCalendarCoordinator(
        hass=hass,
        calendar_entity_id=calendar_entity_id,
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store components in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_ENGINE: engine,
        DATA_EVENT_EMITTER: event_emitter,
        DATA_FLAG_MANAGER: flag_manager,
        DATA_APPLIER: applier,
        DATA_CONFIG: {
            CONF_CALENDAR_ENTITY: calendar_entity_id,
            CONF_DRY_RUN: dry_run,
            CONF_DEBUG_MODE: debug_mode,
            CONF_CLIMATE_ENTITIES: climate_entities,
            CONF_SLOTS: slots,
        },
        DATA_UNSUB: [],
    }

    # Set up coordinator listener to trigger engine evaluation
    async def _handle_coordinator_update() -> None:
        """Handle coordinator updates by running engine evaluation."""
        calendar_state = coordinator.get_current_calendar_state()

        # Run engine evaluation
        result = await engine.evaluate(
            calendar_state=calendar_state,
            slots=slots,
            climate_entities=climate_entities,
        )

        if debug_mode:
            _LOGGER.debug(
                "Engine evaluation complete | Active slot: %s | Changed: %s | Forced: %s",
                result.get("active_slot_id"),
                result.get("changed"),
                result.get("forced"),
            )

    # Register coordinator listener
    unsub_coordinator = coordinator.async_add_listener(_handle_coordinator_update)
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB].append(unsub_coordinator)

    # Trigger initial engine evaluation
    await _handle_coordinator_update()

    # Set up platforms (empty for now, will be added in future milestones)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services (M3) - only on first entry
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)

    _LOGGER.info(
        "Climate Control Calendar setup complete. "
        "Calendar: %s, Dry Run: %s, Slots: %d, Climate entities: %d, Flags enabled: True",
        calendar_entity_id,
        dry_run,
        len(slots),
        len(climate_entities),
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

        # Unload services if last entry
        await async_unload_services(hass)

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
