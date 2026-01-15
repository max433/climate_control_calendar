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
CONF_CALENDAR_CONFIGS: Final = "calendar_configs"  # New: Per-calendar configuration
CONF_OVERRIDE_FLAGS: Final = "override_flags"

# Slot configuration keys (New architecture: slots as reusable templates)
SLOT_ID: Final = "id"
SLOT_LABEL: Final = "label"
SLOT_DEFAULT_CLIMATE_PAYLOAD: Final = "default_climate_payload"  # Renamed from climate_payload
SLOT_ENTITY_OVERRIDES: Final = "entity_overrides"  # New: Entity-specific payload overrides
SLOT_EXCLUDED_ENTITIES: Final = "excluded_entities"  # New: Entities to skip
# Legacy support (will be converted to default_climate_payload)
SLOT_CLIMATE_PAYLOAD: Final = "climate_payload"  # Deprecated, use default_climate_payload

# Binding configuration keys (New architecture: entities in bindings)
BINDING_ID: Final = "id"
BINDING_CALENDARS: Final = "calendars"
BINDING_MATCH: Final = "match"
BINDING_SLOT_ID: Final = "slot_id"
BINDING_TARGET_ENTITIES: Final = "target_entities"  # New: Specific entities for this binding
BINDING_PRIORITY: Final = "priority"

# Calendar configuration keys
CALENDAR_CONFIG_ENABLED: Final = "enabled"
CALENDAR_CONFIG_DEFAULT_PRIORITY: Final = "default_priority"
CALENDAR_CONFIG_DESCRIPTION: Final = "description"

# Match configuration keys
MATCH_TYPE: Final = "type"
MATCH_VALUE: Final = "value"

# Climate payload keys
PAYLOAD_TEMPERATURE: Final = "temperature"
PAYLOAD_HVAC_MODE: Final = "hvac_mode"
PAYLOAD_PRESET_MODE: Final = "preset_mode"
PAYLOAD_FAN_MODE: Final = "fan_mode"
PAYLOAD_SWING_MODE: Final = "swing_mode"
# Advanced climate payload keys (new)
PAYLOAD_TARGET_TEMP_HIGH: Final = "target_temp_high"
PAYLOAD_TARGET_TEMP_LOW: Final = "target_temp_low"
PAYLOAD_HUMIDITY: Final = "humidity"
PAYLOAD_AUX_HEAT: Final = "aux_heat"

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
EVENT_BINDING_MATCHED: Final = f"{DOMAIN}_binding_matched"  # New: Binding matched event
EVENT_EVALUATION_COMPLETE: Final = f"{DOMAIN}_evaluation_complete"  # New: Evaluation summary

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
