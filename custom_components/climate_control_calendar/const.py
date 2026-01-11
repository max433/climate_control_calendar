"""Constants for Climate Control Calendar integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "climate_control_calendar"

# Config flow steps
CONF_CALENDAR_ENTITIES: Final = "calendar_entities"  # Changed from singular to plural (Decision D033)
CONF_CLIMATE_ENTITIES: Final = "climate_entities"
CONF_DRY_RUN: Final = "dry_run"
CONF_DEBUG_MODE: Final = "debug_mode"
CONF_SLOTS: Final = "slots"
CONF_BINDINGS: Final = "bindings"  # New: Event-to-slot bindings (Decision D032)
CONF_OVERRIDE_FLAGS: Final = "override_flags"

# Slot configuration keys (Decision D034: Simplified slots - only climate payload)
SLOT_ID: Final = "id"
SLOT_LABEL: Final = "label"
SLOT_CLIMATE_PAYLOAD: Final = "climate_payload"
# Removed: SLOT_TIME_START, SLOT_TIME_END, SLOT_DAYS (now handled by calendar events)

# Binding configuration keys (Decision D032)
BINDING_ID: Final = "id"
BINDING_CALENDARS: Final = "calendars"
BINDING_MATCH: Final = "match"
BINDING_SLOT_ID: Final = "slot_id"
BINDING_PRIORITY: Final = "priority"

# Match configuration keys
MATCH_TYPE: Final = "type"
MATCH_VALUE: Final = "value"

# Climate payload keys
PAYLOAD_TEMPERATURE: Final = "temperature"
PAYLOAD_HVAC_MODE: Final = "hvac_mode"
PAYLOAD_PRESET_MODE: Final = "preset_mode"

# Override flag types
FLAG_SKIP_UNTIL_NEXT_SLOT: Final = "skip_until_next_slot"
FLAG_SKIP_TODAY: Final = "skip_today"
FLAG_FORCE_SLOT: Final = "force_slot"

# Default values
DEFAULT_DRY_RUN: Final = True
DEFAULT_DEBUG_MODE: Final = False
DEFAULT_UPDATE_INTERVAL: Final = 60  # seconds

# Event types
EVENT_CALENDAR_CHANGED: Final = f"{DOMAIN}_calendar_changed"
EVENT_SLOT_ACTIVATED: Final = f"{DOMAIN}_slot_activated"
EVENT_SLOT_DEACTIVATED: Final = f"{DOMAIN}_slot_deactivated"
EVENT_CLIMATE_APPLIED: Final = f"{DOMAIN}_climate_applied"
EVENT_CLIMATE_SKIPPED: Final = f"{DOMAIN}_climate_skipped"
EVENT_DRY_RUN_EXECUTED: Final = f"{DOMAIN}_dry_run_executed"
EVENT_FLAG_SET: Final = f"{DOMAIN}_flag_set"
EVENT_FLAG_CLEARED: Final = f"{DOMAIN}_flag_cleared"

# Service names
SERVICE_SET_FLAG: Final = "set_flag"
SERVICE_CLEAR_FLAG: Final = "clear_flag"
SERVICE_FORCE_SLOT: Final = "force_slot"
SERVICE_REFRESH_NOW: Final = "refresh_now"
# Slot services (kept for backward compatibility, manage slots without time/days)
SERVICE_ADD_SLOT: Final = "add_slot"
SERVICE_REMOVE_SLOT: Final = "remove_slot"
# Binding services (Decision D032: Event-to-slot binding system)
SERVICE_ADD_BINDING: Final = "add_binding"
SERVICE_REMOVE_BINDING: Final = "remove_binding"
SERVICE_LIST_BINDINGS: Final = "list_bindings"

# Storage keys
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}_storage"

# Coordinator data keys
DATA_COORDINATOR: Final = "coordinator"
DATA_ENGINE: Final = "engine"
DATA_EVENT_EMITTER: Final = "event_emitter"
DATA_FLAG_MANAGER: Final = "flag_manager"
DATA_APPLIER: Final = "applier"
DATA_CONFIG: Final = "config"
DATA_UNSUB: Final = "unsub"
DATA_BINDING_MANAGER: Final = "binding_manager"  # New: Binding manager instance

# Logging prefixes
LOG_PREFIX_ENGINE: Final = "[Engine]"
LOG_PREFIX_COORDINATOR: Final = "[Coordinator]"
LOG_PREFIX_CONFIG_FLOW: Final = "[ConfigFlow]"
LOG_PREFIX_DRY_RUN: Final = "[DRY RUN]"
