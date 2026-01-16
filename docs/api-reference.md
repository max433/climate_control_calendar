# API Reference

This document provides a complete reference for all events and services exposed by Climate Control Calendar.

## Table of Contents

- [Events](#events)
- [Services](#services)
- [Automation Examples](#automation-examples)

---

## Events

Climate Control Calendar emits event types on the Home Assistant event bus. All events can be used as automation triggers for observability and integration with other systems.

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

## Services

Climate Control Calendar does not provide manual control services. All control is performed through calendar events and bindings.

**Manual Override Alternatives**:

If you need to temporarily override automatic climate control, use native Home Assistant features:

1. **Disable automation temporarily**: Turn off the calendar entity
   ```yaml
   service: calendar.turn_off
   target:
     entity_id: calendar.your_calendar
   ```

2. **Create temporary calendar event**: Add a calendar event with automation
   ```yaml
   service: calendar.create_event
   target:
     entity_id: calendar.your_calendar
   data:
     summary: "Comfort Mode"
     start_date_time: "{{ now() }}"
     end_date_time: "{{ now() + timedelta(hours=2) }}"
   ```

3. **Use excluded_entities**: Configure specific entities to skip in slot settings

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

### Example 2: Disable Climate Control When Away

Temporarily disable climate control when nobody is home:

```yaml
automation:
  - alias: "Disable Climate When All Away"
    trigger:
      - platform: state
        entity_id: group.family
        to: "not_home"
        for: "00:30:00"  # 30 minutes
    action:
      - service: homeassistant.turn_off
        target:
          entity_id: calendar.your_climate_calendar

  - alias: "Resume Climate When Someone Home"
    trigger:
      - platform: state
        entity_id: group.family
        to: "home"
    action:
      - service: homeassistant.turn_on
        target:
          entity_id: calendar.your_climate_calendar
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

### Example 5: Log All Climate Control Actions

Create a comprehensive log of all climate control activity:

```yaml
automation:
  - alias: "Log All Climate Events"
    trigger:
      - platform: event
        event_type:
          - climate_control_calendar_calendar_changed
          - climate_control_calendar_slot_activated
          - climate_control_calendar_slot_deactivated
          - climate_control_calendar_climate_applied
          - climate_control_calendar_dry_run_executed
          - climate_control_calendar_binding_matched
    action:
      - service: logbook.log
        data:
          name: "Climate Control Calendar"
          message: "{{ trigger.event.event_type }}: {{ trigger.event.data }}"
          entity_id: climate.living_room  # Associate with a climate entity
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
