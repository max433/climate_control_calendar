# Climate Control Calendar

## 1. Overview

**Climate Control Calendar** is a Home Assistant custom integration (HACS) designed to manage climate devices (primarily heating valves, future-proof for AC and multi-mode devices) based on **calendar-driven habits**.

The core idea is simple and strict:
- **Calendars define *habits*** (presence, smart working, holidays, etc.)
- **Time slots (fasce)** inside calendars define *what should happen when*
- **Devices receive targets** (temperature, HVAC mode, options) *only if not overridden*

The integration is **event-driven**, **GUI-driven**, and supports **dry-run simulation** for safe testing.

---

## 2. Design Principles

### 2.1 Core principles
- Habit-based, not reactive control
- One active calendar at a time
- Unlimited calendars and unlimited time slots per calendar
- No hardcoded room logic
- User customizations via native Home Assistant tools (automations, helpers, labels)

### 2.2 Explicit non-goals
- No PID or temperature feedback control
- No weather-based logic
- No AI optimization (out of scope)

---

## 3. Conceptual Model

### 3.1 Calendar
A **calendar** represents a *habit profile*.

Examples:
- Smart Working
- Office Days
- Holiday
- Default / Always Home

Properties:
- Backed by a Home Assistant `calendar.*` entity
- Can contain recurring events
- Events act only as **time markers**, not data containers

Naming convention (recommended):
```
calendar.climate_<profile_name>
```

---

### 3.2 Time Slot (Fascia)

A **time slot** represents a configuration active during a time window.

Characteristics:
- Defined in GUI (integration config)
- Any number per calendar
- Identified internally by a **stable generated ID** (UUID-like)
- User sees only labels (not IDs)

Each slot contains:
- Start time
- End time
- Climate payload

---

### 3.3 Climate Payload

The payload defines what is applied to devices:

Possible fields:
- `temperature`
- `hvac_mode` (heat, cool, off, auto, etc.)
- `preset_mode` (eco, comfort, away, frost)
- `aux_heat`
- `fan_mode`

Slots may omit fields (device-specific compatibility applies).

---

## 4. Devices

### 4.1 Supported devices

- `climate.*` entities
- Valves (heating-only)
- AC / heat pumps (multi-mode)

### 4.2 Device abstraction

Each device has:
- Capabilities (read from HA)
- Assigned rooms/areas (HA native)
- Optional **override flags**

---

## 5. Override Flags

### 5.1 Definition

Override flags are **per-device**, temporary states that instruct the engine to **ignore slot application**.

Examples:
- `manual_override`
- `holiday`
- `maintenance`
- `room_skipped`

### 5.2 Behavior (fixed decision)

If **any relevant flag is present** on a device:
- Slot is ignored
- No temperature/mode is applied
- Event is emitted (`device_skipped`)

Flags always have:
- Source
- Optional expiration timestamp

---

## 6. Room / Device Skipping

Rooms (or single devices) can be **temporarily excluded** from the engine:
- Implemented as a flag with expiration
- Used for manual interventions
- Fully event-notified

This is the **only supported per-room override** (fixed architectural decision).

---

## 7. Active Calendar Resolution

At any time:
1. Integration determines the **active calendar**
2. Determines the **current time slot** inside it
3. Evaluates devices
4. Applies or skips

Triggers:
- Calendar state change
- Slot boundary crossing
- Manual override changes

---

## 8. Dry Run Mode

### 8.1 Purpose

Dry run allows:
- Full simulation
- Event emission
- Logging
- Notifications

**Without writing to devices**.

### 8.2 Behavior

When enabled:
- All logic runs
- All decisions are logged
- No `climate.set_*` services are called

Dry run is a **first-class feature** and must never be removed.

---

## 9. Events

The integration emits HA events:

- `climate_control_calendar_slot_changed`
- `climate_control_calendar_device_applied`
- `climate_control_calendar_device_skipped`
- `climate_control_calendar_dry_run`

Events are the primary integration point for user automations.

---

## 10. GUI & UX

### 10.1 Configuration flow

- Config Flow (UI only)
- Calendar selection
- Slot editor (add/remove/reorder)
- Device inclusion
- Dry run toggle

### 10.2 UX goals

- No YAML required
- Labels instead of IDs
- Safe defaults
- Visual clarity

---

## 11. Typical Use Cases

### 11.1 Fixed weekly routine
- Single calendar
- Weekly recurring events
- Multiple slots per day

### 11.2 Rotating shifts
- Multiple calendars
- User switches active calendar weekly

### 11.3 Temporary room exclusion
- User flags a room for 1 day
- Engine skips it
- Automatic re-entry

---

## 12. Architectural Decisions (Fixed)

- Calendar-driven logic is core and non-negotiable
- One active calendar at a time
- Slot count is arbitrary
- Room override via skip flag only
- No per-room time slots

---

## 13. Future Extensions (Non-breaking)

- Cooling profiles
- Mixed heating/cooling seasons
- Smart presets
- Analytics panel

---

## 14. Terminology

| Term | Meaning |
|-----|--------|
| Calendar | Habit profile |
| Slot/Fascia | Time-based configuration |
| Payload | What is applied to devices |
| Flag | Override condition |
| Dry Run | Simulation mode |

---

End of document.

