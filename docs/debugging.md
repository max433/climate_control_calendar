# Debugging Guide

This guide helps you troubleshoot common issues with Climate Control Calendar.

## Table of Contents

- [Enable Debug Logging](#enable-debug-logging)
- [Understanding Dry Run Mode](#understanding-dry-run-mode)
- [Common Issues](#common-issues)
- [Viewing Events](#viewing-events)
- [Checking Integration State](#checking-integration-state)
- [Log Analysis](#log-analysis)

---

## Enable Debug Logging

### Method 1: Via Integration Options

1. Go to **Settings** → **Devices & Services**
2. Find **Climate Control Calendar**
3. Click **Configure**
4. Enable **Debug Mode**
5. Click **Submit**

### Method 2: Via configuration.yaml

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.climate_control_calendar: debug
```

Restart Home Assistant after editing `configuration.yaml`.

### What Debug Logging Shows

Debug logs include:
- Coordinator update cycles (every 60 seconds)
- Calendar state changes detected
- Slot resolution details (why a slot matched or didn't match)
- Engine evaluation decisions
- Flag expiration checks
- Climate payload construction
- Device application attempts and results

---

## Understanding Dry Run Mode

**Dry run mode is ENABLED by default** for safety. This means the integration simulates all actions without actually controlling devices.

### How to Identify Dry Run Mode

**In Logs** (look for these messages):
```
[DRY RUN] Would apply climate payload to climate.living_room: {...}
[DRY RUN] Slot 'morning_comfort' would be activated
```

**In Events** (event data includes `dry_run: true`):
```json
{
  "event_type": "climate_control_calendar_dry_run_executed",
  "data": {
    "slot_id": "a3f5c8d2e1b4",
    "climate_payload": {...},
    "dry_run": true
  }
}
```

### Disabling Dry Run (Going Live)

1. Go to **Settings** → **Devices & Services**
2. Find **Climate Control Calendar**
3. Click **Configure**
4. **Uncheck** "Dry Run Mode"
5. Click **Submit**

**⚠️ Warning**: Disabling dry run will allow the integration to control your climate devices. Ensure your slots are configured correctly before doing this.

---

## Common Issues

### Issue 1: Integration Not Controlling Devices

**Symptoms**: No temperature changes, logs show activity but devices unchanged.

**Possible Causes**:

1. **Dry run mode is enabled** (most common)
   - Solution: Disable dry run mode (see above)
   - Verify: Check logs for `[DRY RUN]` prefix

2. **Calendar is OFF**
   - Solution: Ensure your calendar event is active (check calendar entity state in Developer Tools)
   - Verify: `calendar.your_calendar` state should be `on`

3. **No matching slot for current time**
   - Solution: Check slot time windows match current time and day of week
   - Verify: Enable debug logging and check "No active slot found" messages

4. **Override flag active**
   - Solution: Check if a `skip_*` flag is set
   - Verify: Call `climate_control_calendar.clear_flag` service

---

### Issue 2: Slot Not Activating at Expected Time

**Symptoms**: Time window reached but slot doesn't activate.

**Debugging Steps**:

1. **Enable debug logging** and watch for slot resolution messages
2. **Check calendar state**:
   ```yaml
   # In Developer Tools → States
   calendar.your_calendar: on  # Must be "on" for slots to activate
   ```

3. **Verify slot configuration**:
   - Time window includes current time (e.g., 08:30 is between 08:00-09:00)
   - Day of week matches (e.g., Monday matches if today is Monday)
   - Overnight slots: `23:00-02:00` works, but ensure logic accounts for day boundary

4. **Check for overlapping slots**:
   - Integration prevents overlapping slots by design (Decision D011)
   - If slot creation failed due to overlap, you won't see it in configuration

5. **Coordinator update timing**:
   - Engine evaluates every 60 seconds (Decision D014)
   - Slot activation may have up to 60-second delay from exact time boundary
   - Example: Slot starts at 08:00:00, coordinator ticks at 08:00:47 → slot activates at 08:00:47

---

### Issue 3: Climate Payload Not Applied to Some Devices

**Symptoms**: Some devices update, others don't.

**Debugging Steps**:

1. **Check logs for device-specific errors**:
   ```
   ERROR: Failed to apply climate payload to climate.bedroom: <error details>
   ```

2. **Verify device availability**:
   - Go to Developer Tools → States
   - Check if device state is `unavailable` or `unknown`

3. **Check device capabilities**:
   - Not all climate devices support all features
   - Example: Some thermostats don't support `preset_mode`
   - Solution: Adjust climate payload to only use supported features

4. **Retry logic**:
   - Integration automatically retries once after 1 second (Decision D017)
   - If still failing, device may be genuinely unavailable
   - Check Home Assistant logs for device-specific errors

---

### Issue 4: Events Not Emitting

**Symptoms**: Automations not triggering on Climate Control Calendar events.

**Debugging Steps**:

1. **Listen for events in Developer Tools**:
   - Go to Developer Tools → Events
   - Listen for `climate_control_calendar_*`
   - Trigger action (e.g., manually call `refresh_now` service)

2. **Check event deduplication**:
   - Events only emit on state transitions (Decision D015)
   - If slot remains active across multiple evaluations, no new event
   - Example: `slot_activated` emits once when slot starts, not every 60 seconds

3. **Verify automation trigger syntax**:
   ```yaml
   trigger:
     - platform: event
       event_type: climate_control_calendar_slot_activated
       event_data:
         slot_id: a3f5c8d2e1b4  # Optional: filter by specific slot
   ```

---

### Issue 5: Override Flags Not Working as Expected

**Symptoms**: Flag set but behavior doesn't change.

**Debugging Steps**:

1. **Check flag mutual exclusion**:
   - Only one flag can be active at a time (Decision D019)
   - Setting a new flag clears the previous one
   - Verify with debug logs: "Clearing existing flag before setting new one"

2. **Check flag expiration**:
   - `skip_today`: Auto-expires at midnight (00:00)
   - `skip_until_next_slot`: Auto-expires when next slot activates
   - `force_slot`: Manual clear only (never auto-expires)
   - Solution: Check current time vs expiration conditions

3. **Verify flag persistence**:
   - Flags persist across Home Assistant restarts (HA Storage)
   - Check storage file: `.storage/climate_control_calendar_<entry_id>_flags`
   - Don't manually edit this file (use services instead)

---

## Viewing Events

### Via Developer Tools

1. Go to **Developer Tools** → **Events**
2. In "Listen to events" section, enter: `climate_control_calendar_*` (or specific event type)
3. Click **Start Listening**
4. Trigger actions (calendar state change, service calls, etc.)
5. Events appear in real-time below

### Via Logs

Events also appear in logs at INFO level:
```
INFO: Event emitted: climate_control_calendar_slot_activated
```

Enable debug logging to see full event payloads.

---

## Checking Integration State

### Via Developer Tools → States

The integration doesn't create entities (it controls existing climate entities), but you can check:

1. **Calendar entity state**:
   ```
   calendar.your_calendar
   State: on/off
   Attributes: event details (summary, start, end)
   ```

2. **Climate entity states** (after payload application):
   ```
   climate.living_room
   State: heat/cool/off
   Attributes:
     temperature: 21.0
     current_temperature: 19.5
     hvac_mode: heat
     preset_mode: comfort
   ```

### Via Integration Page

1. Go to **Settings** → **Devices & Services**
2. Find **Climate Control Calendar**
3. Check configuration entries
4. Review options (dry run, debug, climate entities)

---

## Log Analysis

### Typical Healthy Log Sequence

```
INFO: Coordinator update: calendar state = on
DEBUG: Evaluating slots: 4 slots configured
DEBUG: Checking slot 'morning_comfort': time_match=True, day_match=True
DEBUG: Active slot resolved: 'morning_comfort' (a3f5c8d2e1b4)
INFO: Slot activated: morning_comfort
DEBUG: Applying climate payload to 3 devices
DEBUG: Applied to climate.living_room: success (1 attempt)
DEBUG: Applied to climate.bedroom: success (1 attempt)
DEBUG: Applied to climate.office: success (1 attempt)
INFO: Climate payload applied to 3/3 devices
INFO: Event emitted: climate_control_calendar_slot_activated
```

### Red Flags in Logs

**Problem: Calendar entity not found**
```
ERROR: Calendar entity calendar.work_schedule not found
```
Solution: Check calendar entity ID, ensure calendar integration is loaded.

---

**Problem: All devices failing**
```
ERROR: Failed to apply climate payload to climate.living_room: Service not found
ERROR: Failed to apply climate payload to climate.bedroom: Service not found
```
Solution: Climate integration may not be loaded, or devices unavailable.

---

**Problem: Constant slot activation/deactivation**
```
INFO: Slot activated: morning_comfort
INFO: Slot deactivated: morning_comfort
INFO: Slot activated: morning_comfort
INFO: Slot deactivated: morning_comfort
```
Solution: Calendar state rapidly toggling, or slot time boundary issue. Check calendar entity.

---

**Problem: Overlapping slots detected during config**
```
ERROR: Slot validation failed: overlaps with existing slot 'morning_comfort'
```
Solution: Adjust slot time windows to prevent overlap (Decision D011).

---

## Advanced Debugging

### Check Storage Files

Flags are stored in `.storage/climate_control_calendar_<entry_id>_flags`:

```json
{
  "version": 1,
  "key": "climate_control_calendar_abc123_flags",
  "data": {
    "flag_type": "skip_today",
    "slot_id": null,
    "set_at": "2026-01-10T14:30:00"
  }
}
```

**⚠️ Warning**: Don't manually edit storage files. Use services instead.

---

### Manually Trigger Evaluation

Force immediate slot evaluation (bypass 60-second interval):

```yaml
service: climate_control_calendar.refresh_now
```

Useful for testing slot transitions without waiting.

---

### Test Slot Configuration Without Devices

1. Enable **Dry Run Mode**
2. Enable **Debug Mode**
3. Watch logs for slot evaluation details
4. Verify slots activate at expected times
5. Once validated, disable dry run to go live

---

## Getting Help

If you've tried the above steps and still have issues:

1. **Enable debug logging**
2. **Capture logs** covering the problem period (at least 5 minutes)
3. **Note your configuration**:
   - Calendar entity ID
   - Number and configuration of slots
   - Climate entities controlled
   - Dry run mode status
4. **Open an issue** on [GitHub Issues](https://github.com/max433/climate_control_calendar/issues) with:
   - Problem description
   - Logs (sanitize personal data)
   - Configuration details
   - Home Assistant version

---

**Tip**: Most issues are resolved by checking:
1. Is dry run mode enabled? (most common)
2. Is calendar state ON?
3. Does current time fall within a slot window?
4. Are debug logs enabled?
