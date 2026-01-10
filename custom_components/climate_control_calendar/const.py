"""Constants for Climate Control Calendar integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "climate_control_calendar"

# Config flow steps
CONF_CALENDAR_ENTITY: Final = "calendar_entity"
CONF_CLIMATE_ENTITIES: Final = "climate_entities"
CONF_DRY_RUN: Final = "dry_run"
CONF_DEBUG_MODE: Final = "debug_mode"
CONF_SLOTS: Final = "slots"
CONF_OVERRIDE_FLAGS: Final = "override_flags"

# Slot configuration keys
SLOT_ID: Final = "id"
SLOT_LABEL: Final = "label"
SLOT_TIME_START: Final = "time_start"
SLOT_TIME_END: Final = "time_end"
SLOT_DAYS: Final = "days"
SLOT_CLIMATE_PAYLOAD: Final = "climate_payload"

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

# Storage keys
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}_storage"

# Coordinator data keys
DATA_COORDINATOR: Final = "coordinator"
DATA_ENGINE: Final = "engine"
DATA_EVENT_EMITTER: Final = "event_emitter"
DATA_CONFIG: Final = "config"
DATA_UNSUB: Final = "unsub"

# Day names (internal)
DAYS_OF_WEEK: Final = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday"
]

# Logging prefixes
LOG_PREFIX_ENGINE: Final = "[Engine]"
LOG_PREFIX_COORDINATOR: Final = "[Coordinator]"
LOG_PREFIX_CONFIG_FLOW: Final = "[ConfigFlow]"
LOG_PREFIX_DRY_RUN: Final = "[DRY RUN]"
