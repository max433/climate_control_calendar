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
    CONF_DRY_RUN,
    DATA_COORDINATOR,
    DATA_CONFIG,
    DATA_UNSUB,
    DEFAULT_UPDATE_INTERVAL,
)
from .coordinator import ClimateControlCalendarCoordinator

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

    # Get configuration
    calendar_entity_id = entry.data.get(CONF_CALENDAR_ENTITY)
    dry_run = entry.data.get(CONF_DRY_RUN, True)

    if not calendar_entity_id:
        _LOGGER.error("No calendar entity configured")
        return False

    # Verify calendar entity exists
    if not hass.states.get(calendar_entity_id):
        raise ConfigEntryNotReady(
            f"Calendar entity not found: {calendar_entity_id}. "
            "Please ensure the calendar integration is loaded."
        )

    # Create coordinator
    coordinator = ClimateControlCalendarCoordinator(
        hass=hass,
        calendar_entity_id=calendar_entity_id,
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and config in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_CONFIG: {
            CONF_CALENDAR_ENTITY: calendar_entity_id,
            CONF_DRY_RUN: dry_run,
        },
        DATA_UNSUB: [],
    }

    # Set up platforms (empty for now, will be added in future milestones)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(
        "Climate Control Calendar setup complete. Calendar: %s, Dry Run: %s",
        calendar_entity_id,
        dry_run,
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
