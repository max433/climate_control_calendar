# API Reference

This document provides a complete reference for all events and services exposed by Climate Control Calendar.

## Table of Contents

- [Events](#events)
- [Services](#services)
- [Automation Examples](#automation-examples)

---

## Events

Climate Control Calendar emits eight event types on the Home Assistant event bus. All events can be used as automation triggers.

### Event Structure

All events follow this structure:

```json
{
  "event_type": "climate_control_calendar_<event_name>",
  "data": {
    "entry_id": "abc123...",
    "timestamp": "2026-01-10T14:30:00.123456",
    // ... event-specific fields
  },
  "origin": "LOCAL",
  "time_fired": "2026-01-10T14:30:00.123456+00:00"
}
```

---

### 1. `climate_control_calendar_calendar_changed`

Emitted when the monitored calendar entity state changes (ON ↔ OFF).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T08:00:00",
  "calendar_entity": "calendar.work_schedule",
  "old_state": "off",
  "new_state": "on",
  "event_summary": "Work From Home"  // Calendar event summary (if available)
}
```

**Use Cases**:
- Trigger notification when calendar activates
- Log calendar state changes
- Trigger scene changes on calendar activation

**Example Automation**:
```yaml
automation:
  - alias: "Notify on Work From Home Day"
    trigger:
      - platform: event
        event_type: climate_control_calendar_calendar_changed
        event_data:
          new_state: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Work from home mode activated: {{ trigger.event.data.event_summary }}"
```

---

### 2. `climate_control_calendar_slot_activated`

Emitted when a time slot becomes active (deduplication ensures this fires only once per slot activation, not on every engine evaluation).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T08:00:47",
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort",
  "time_start": "08:00",
  "time_end": "12:00",
  "climate_payload": {
    "temperature": 22.0,
    "hvac_mode": "heat",
    "preset_mode": "comfort"
  }
}
```

**Use Cases**:
- Trigger lights/scenes when specific slot activates
- Send notifications about active comfort mode
- Log slot activation history

**Example Automation**:
```yaml
automation:
  - alias: "Bright Lights for Work Hours"
    trigger:
      - platform: event
        event_type: climate_control_calendar_slot_activated
        event_data:
          slot_label: "work_hours"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.work_mode_bright
```

---

### 3. `climate_control_calendar_slot_deactivated`

Emitted when the active slot becomes inactive (calendar turns OFF, time window ends, or override flag skips slot).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T12:00:15",
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort",
  "reason": "time_window_ended"  // Or: "calendar_off", "flag_skip"
}
```

**Use Cases**:
- Return devices to default state when slot ends
- Log slot duration
- Trigger cleanup actions

**Example Automation**:
```yaml
automation:
  - alias: "Reset to Eco After Work Slot"
    trigger:
      - platform: event
        event_type: climate_control_calendar_slot_deactivated
        event_data:
          slot_label: "work_hours"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: all
        data:
          preset_mode: eco
```

---

### 4. `climate_control_calendar_climate_applied`

Emitted when climate payload is successfully applied to one or more devices (not in dry run mode).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T08:00:47",
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort",
  "climate_payload": {
    "temperature": 22.0,
    "hvac_mode": "heat"
  },
  "climate_entities": ["climate.living_room", "climate.bedroom"],
  "success_count": 2,
  "total_count": 2,
  "partial_failure": false
}
```

**Use Cases**:
- Verify climate changes were applied successfully
- Alert on partial failures
- Audit trail of climate control actions

**Example Automation**:
```yaml
automation:
  - alias: "Alert on Partial Climate Failure"
    trigger:
      - platform: event
        event_type: climate_control_calendar_climate_applied
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.partial_failure == true }}"
    action:
      - service: notify.homeowner
        data:
          message: "Climate control partially failed: {{ trigger.event.data.success_count }}/{{ trigger.event.data.total_count }} devices"
```

---

### 5. `climate_control_calendar_climate_skipped`

Emitted when climate payload application was skipped due to override flag.

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T08:00:47",
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort",
  "reason": "flag_skip_today",  // Or: "flag_skip_until_next_slot"
  "flag_type": "skip_today"
}
```

**Use Cases**:
- Confirm manual override is working
- Log when and why automatic control was skipped

---

### 6. `climate_control_calendar_dry_run_executed`

Emitted during dry run mode when climate payload would have been applied (but wasn't due to simulation mode).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T08:00:47",
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort",
  "climate_payload": {
    "temperature": 22.0,
    "hvac_mode": "heat"
  },
  "climate_entities": ["climate.living_room", "climate.bedroom"],
  "dry_run": true
}
```

**Use Cases**:
- Test slot configuration without affecting devices
- Verify timing and payloads before going live
- Development and debugging

**Example Automation**:
```yaml
automation:
  - alias: "Log Dry Run Actions for Review"
    trigger:
      - platform: event
        event_type: climate_control_calendar_dry_run_executed
    action:
      - service: logbook.log
        data:
          name: "Climate Dry Run"
          message: "Would apply {{ trigger.event.data.climate_payload }} to {{ trigger.event.data.climate_entities }}"
```

---

### 7. `climate_control_calendar_flag_set`

Emitted when an override flag is set via service call.

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T14:30:00",
  "flag_type": "skip_today",  // Or: "skip_until_next_slot", "force_slot"
  "slot_id": null,  // Populated for force_slot
  "set_via": "service_call"
}
```

**Use Cases**:
- Confirm manual override activated
- Log manual interventions
- Trigger UI updates (e.g., display active flag)

---

### 8. `climate_control_calendar_flag_cleared`

Emitted when an override flag is cleared (manually or auto-expired).

**Event Data**:
```json
{
  "entry_id": "abc123",
  "timestamp": "2026-01-10T23:59:59",
  "previous_flag_type": "skip_today",
  "reason": "expired",  // Or: "manual_clear", "replaced_by_new_flag"
  "cleared_via": "auto_expiration"  // Or: "service_call"
}
```

**Use Cases**:
- Confirm automatic control resumed
- Log flag lifecycle
- Update UI

**Example Automation**:
```yaml
automation:
  - alias: "Notify When Manual Skip Expires"
    trigger:
      - platform: event
        event_type: climate_control_calendar_flag_cleared
        event_data:
          reason: expired
    action:
      - service: notify.mobile_app
        data:
          message: "Climate control override expired, resuming automatic control"
```

---

## Services

Climate Control Calendar provides four services for manual control. All services ignore dry run mode (manual actions always execute).

### 1. `climate_control_calendar.set_flag`

Set an override flag to temporarily alter automatic behavior.

**Service Data Schema**:
```yaml
flag_type: skip_today | skip_until_next_slot | force_slot  # Required
target_slot_id: string  # Required only when flag_type is force_slot
```

**Parameters**:

- **`flag_type`** (required):
  - `skip_today`: Skip all automatic climate changes until midnight (00:00)
  - `skip_until_next_slot`: Skip current slot, resume at next slot transition
  - `force_slot`: Force activation of specific slot, ignoring calendar and time

- **`target_slot_id`** (conditional):
  - Required when `flag_type` is `force_slot`
  - Optional (ignored) for `skip_*` flags
  - Must be a valid slot ID from your configuration

**Examples**:

```yaml
# Skip all automatic changes today
service: climate_control_calendar.set_flag
data:
  flag_type: skip_today

# Skip current slot only
service: climate_control_calendar.set_flag
data:
  flag_type: skip_until_next_slot

# Force specific slot
service: climate_control_calendar.set_flag
data:
  flag_type: force_slot
  target_slot_id: a3f5c8d2e1b4
```

**Behavior**:
- Only one flag can be active at a time (mutual exclusion)
- Setting a new flag automatically clears any existing flag
- Emits `climate_control_calendar_flag_set` event

**Automation Example**:
```yaml
automation:
  - alias: "Skip Climate Control When Away"
    trigger:
      - platform: state
        entity_id: person.homeowner
        to: "not_home"
    action:
      - service: climate_control_calendar.set_flag
        data:
          flag_type: skip_today
```

---

### 2. `climate_control_calendar.clear_flag`

Clear the currently active override flag and resume normal automatic behavior.

**Service Data Schema**: None (no parameters required)

**Example**:
```yaml
service: climate_control_calendar.clear_flag
```

**Behavior**:
- Clears active flag (if any)
- If no flag active, service has no effect (safe to call)
- Emits `climate_control_calendar_flag_cleared` event

**Automation Example**:
```yaml
automation:
  - alias: "Resume Climate Control When Home"
    trigger:
      - platform: state
        entity_id: person.homeowner
        to: "home"
    action:
      - service: climate_control_calendar.clear_flag
```

---

### 3. `climate_control_calendar.force_slot`

Convenience service to force activation of a specific slot. This is a wrapper for `set_flag` with `flag_type: force_slot`.

**Service Data Schema**:
```yaml
slot_id: string  # Required
```

**Parameters**:

- **`slot_id`** (required): ID of the slot to force activate

**Example**:
```yaml
service: climate_control_calendar.force_slot
data:
  slot_id: a3f5c8d2e1b4
```

**Behavior**:
- Forces specified slot to activate immediately
- Ignores calendar state and time restrictions
- Slot remains active until flag is manually cleared
- Equivalent to: `set_flag` with `flag_type: force_slot` and `target_slot_id: <slot_id>`

**Automation Example**:
```yaml
automation:
  - alias: "Force Comfort Mode on Button Press"
    trigger:
      - platform: state
        entity_id: input_button.comfort_mode
    action:
      - service: climate_control_calendar.force_slot
        data:
          slot_id: "{{ state_attr('climate_control_calendar.config', 'comfort_slot_id') }}"
```

---

### 4. `climate_control_calendar.refresh_now`

Force immediate coordinator refresh and slot evaluation. Bypasses the normal 60-second poll interval.

**Service Data Schema**: None (no parameters required)

**Example**:
```yaml
service: climate_control_calendar.refresh_now
```

**Behavior**:
- Immediately fetches calendar state
- Immediately evaluates slots and applies climate payload
- Useful for testing configuration changes without waiting

**Use Cases**:
- Apply configuration changes immediately after modifying slots
- Test slot activation manually
- Recover from coordinator errors

**Automation Example**:
```yaml
automation:
  - alias: "Refresh Climate Control on Slot Config Change"
    trigger:
      - platform: event
        event_type: climate_control_calendar_config_updated  # Custom event you emit
    action:
      - service: climate_control_calendar.refresh_now
```

---

## Automation Examples

### Example 1: Notification on Slot Activation

Get notified when your morning comfort slot activates:

```yaml
automation:
  - alias: "Notify Morning Comfort Active"
    trigger:
      - platform: event
        event_type: climate_control_calendar_slot_activated
        event_data:
          slot_label: "morning_comfort"
    action:
      - service: notify.mobile_app_phone
        data:
          message: "Good morning! Heating set to {{ trigger.event.data.climate_payload.temperature }}°C"
```

---

### Example 2: Automatic Override When Away

Skip climate control when nobody is home:

```yaml
automation:
  - alias: "Skip Climate When All Away"
    trigger:
      - platform: state
        entity_id: group.family
        to: "not_home"
        for: "00:30:00"  # 30 minutes
    action:
      - service: climate_control_calendar.set_flag
        data:
          flag_type: skip_today

  - alias: "Resume Climate When Someone Home"
    trigger:
      - platform: state
        entity_id: group.family
        to: "home"
    action:
      - service: climate_control_calendar.clear_flag
```

---

### Example 3: Scene Changes on Slot Transitions

Change lighting scenes when work hours slot activates:

```yaml
automation:
  - alias: "Work Mode Scene"
    trigger:
      - platform: event
        event_type: climate_control_calendar_slot_activated
        event_data:
          slot_label: "work_hours"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.work_mode

  - alias: "Evening Scene After Work"
    trigger:
      - platform: event
        event_type: climate_control_calendar_slot_deactivated
        event_data:
          slot_label: "work_hours"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.evening_relax
```

---

### Example 4: Alert on Climate Application Failure

Get notified if climate payload fails to apply to any device:

```yaml
automation:
  - alias: "Alert on Climate Failure"
    trigger:
      - platform: event
        event_type: climate_control_calendar_climate_applied
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.partial_failure }}"
    action:
      - service: notify.homeowner
        data:
          title: "Climate Control Issue"
          message: >
            Failed to apply climate settings to some devices.
            Success: {{ trigger.event.data.success_count }}/{{ trigger.event.data.total_count }}
            Slot: {{ trigger.event.data.slot_label }}
```

---

### Example 5: Force Comfort Mode via Dashboard Button

Create a button to force comfort mode regardless of schedule:

**Input Button** (configuration.yaml):
```yaml
input_button:
  force_comfort_mode:
    name: Force Comfort Mode
    icon: mdi:fire
```

**Automation**:
```yaml
automation:
  - alias: "Force Comfort on Button Press"
    trigger:
      - platform: state
        entity_id: input_button.force_comfort_mode
    action:
      - service: climate_control_calendar.force_slot
        data:
          slot_id: "a3f5c8d2e1b4"  # Your comfort slot ID
      - service: notify.mobile_app
        data:
          message: "Comfort mode forced. Call clear_flag service to resume automatic control."
```

---

### Example 6: Log All Climate Control Actions

Create a comprehensive log of all climate control activity:

```yaml
automation:
  - alias: "Log All Climate Events"
    trigger:
      - platform: event
        event_type:
          - climate_control_calendar_slot_activated
          - climate_control_calendar_slot_deactivated
          - climate_control_calendar_climate_applied
          - climate_control_calendar_flag_set
          - climate_control_calendar_flag_cleared
    action:
      - service: logbook.log
        data:
          name: "Climate Control Calendar"
          message: "{{ trigger.event.event_type }}: {{ trigger.event.data }}"
          entity_id: climate.living_room  # Associate with a climate entity
```

---

### Example 7: Conditional Slot Forcing Based on Temperature

Force heating slot if temperature drops below threshold:

```yaml
automation:
  - alias: "Emergency Heat on Cold"
    trigger:
      - platform: numeric_state
        entity_id: sensor.indoor_temperature
        below: 16
    action:
      - service: climate_control_calendar.force_slot
        data:
          slot_id: "emergency_heat_slot_id"
      - service: notify.mobile_app
        data:
          message: "Emergency heating activated due to low temperature: {{ states('sensor.indoor_temperature') }}°C"
```

---

## Finding Slot IDs

Slot IDs are generated when slots are created (12-character SHA256 hash). To find your slot IDs:

### Method 1: Via Logs (Debug Mode)

Enable debug mode and check logs during slot activation:
```
DEBUG: Active slot resolved: 'morning_comfort' (a3f5c8d2e1b4)
```

### Method 2: Via Events

Listen for `slot_activated` events in Developer Tools → Events:
```json
{
  "slot_id": "a3f5c8d2e1b4",
  "slot_label": "morning_comfort"
}
```

### Method 3: Via Configuration Storage

Check `.storage/climate_control_calendar_<entry_id>` file (advanced users only).

---

## Version

This API reference is for **Climate Control Calendar v1.0.0**.

For the latest version, see the [GitHub repository](https://github.com/max433/climate_control_calendar).
