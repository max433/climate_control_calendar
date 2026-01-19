# Climate Control Calendar

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/max433/climate_control_calendar.svg)](https://github.com/max433/climate_control_calendar/releases)
[![GitHub Downloads](https://img.shields.io/github/downloads/max433/climate_control_calendar/total.svg)](https://github.com/max433/climate_control_calendar/releases)
[![GitHub Stars](https://img.shields.io/github/stars/max433/climate_control_calendar.svg?style=social)](https://github.com/max433/climate_control_calendar/stargazers)
[![License](https://img.shields.io/github/license/max433/climate_control_calendar.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)

![Climate Control Calendar](icon.svg)

A Home Assistant custom integration that manages climate devices (thermostats, valves) based on calendar events representing different usage patterns.

## 🎯 Concept

**Climate Control Calendar** transforms your Home Assistant calendars into intelligent climate control. Instead of rigid time-based schedules, you create calendar events that trigger climate profiles:

- 📅 **"Smart Working"** → activates comfort mode in studio
- 🏖️ **"Summer Vacation"** → switches to energy-saving mode
- 🏠 **"Weekend Home"** → higher comfort levels all day
- 🌙 **"Night Mode"** → reduces temperatures for sleep
- 🚨 **"Emergency Heat"** → instant override from your phone

**The power?** Manage your heating schedule from any calendar app (Google Calendar, Outlook, etc.), with changes active within 60 seconds. No restart needed!

## ✨ Key Features

### 🎯 Event-Based Architecture
- **📅 Any Calendar Works**: Google Calendar, Local Calendar, Office 365, CalDAV
- **🔗 Pattern Matching Bindings**: Event "Smart Working" → activates "Comfort" slot
- **🎚️ Reusable Climate Profiles**: Define slots once, use with multiple events
- **⚡ Priority System**: Multiple events active? Highest priority wins
- **🏠 Per-Entity Control**: Different temperatures for different rooms in same slot

### 🚀 Smart Behavior
- **Active Event Fetching**: New events detected within 60 seconds
- **Change Detection**: Applies climate ONLY when events start/end (not every minute)
- **Multi-Calendar Support**: Monitor multiple calendars simultaneously
- **Conflict Resolution**: Automatic priority-based resolution for overlapping events
- **Target Entity Flexibility**: Global pool + per-binding overrides + per-slot exclusions

### 🛠️ Developer-Friendly
- **Dry Run Mode**: Test without touching real devices
- **Rich Event System**: 10+ event types for automation triggers
- **Debug Logging**: Comprehensive logs for troubleshooting
- **GUI Configuration**: Everything configurable through UI (no YAML)
- **Service Calls**: Manual override and control services

## 🚀 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu (top right)
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/max433/climate_control_calendar`
6. Category: Integration
7. Click "Add"
8. Find "Climate Control Calendar" and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/max433/climate_control_calendar/releases)
2. Extract the `climate_control_calendar` folder
3. Copy to `config/custom_components/climate_control_calendar`
4. Restart Home Assistant

## 📋 Prerequisites

- Home Assistant 2024.1.0 or newer
- At least one calendar integration configured (Google Calendar, Local Calendar, etc.)
- Climate entities to control (thermostats, climate devices, etc.)

## ⚙️ Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Climate Control Calendar**
4. Follow the setup wizard:
   - **Step 1**: Select the calendar entity to monitor
   - **Step 2**: Select climate devices to control
   - **Step 3**: Configure dry run and debug options

### Configuration Options

- **Dry Run Mode**: When enabled, the integration simulates actions without actually controlling devices. Highly recommended for testing.
- **Debug Mode**: Enables verbose logging for troubleshooting.

## 📚 How It Works

### Architecture Overview

```
📅 Calendar Events  →  🔗 Bindings  →  🎚️ Slots  →  🌡️ Climate Entities
   (your schedule)    (pattern match)  (profiles)    (your devices)
```

### Core Concepts

1. **📅 Calendars**: Any Home Assistant calendar becomes a control source
   - Create events like "Smart Working", "Vacation", "Night Mode"
   - Multiple calendars supported for different zones/purposes

2. **🔗 Bindings**: Pattern matchers that connect events to slots
   - Match by exact name, partial text, or regex pattern
   - Set priorities for conflict resolution
   - Target specific entities or use global pool

### 3. 🎚️ **Slots**: Reusable climate configuration templates
   - Define temperature, HVAC mode, preset, etc.
   - Temperature range support for heat_cool mode
   - Humidity control for compatible devices
   - Auxiliary heat control for heat pumps
   - Fan and swing mode configuration
   - Per-entity overrides for room-specific settings
   - Exclude entities that should never be controlled

4. **⚡ Priority System**: When multiple events are active
   - Higher priority binding wins for conflicting entities
   - Different priorities for different rooms simultaneously
   - Emergency overrides (priority 99) always win

### Workflow Example

```
1. Calendar Event "Smart Working" becomes active
          ↓
2. Binding matches pattern "Smart Working"
          ↓
3. Activates Slot "Comfort Mode" (21°C, heat)
          ↓
4. Applied to climate.studio (23°C override) + climate.bedroom (21°C default)
          ↓
5. When event ends → revert to next active binding or default state
```

**📖 For detailed architecture explanation, see [ARCHITECTURE.md](ARCHITECTURE.md)**

## 💡 Quick Start Examples

### Example 1: Simple Smart Working Schedule

**Goal**: Warmer studio when working from home, scheduled via calendar

**Configuration**:

1. **Create Slot** "Comfort"
   - Temperature: 21°C, HVAC Mode: heat
   - Entity Override: climate.studio → 23°C

2. **Create Binding** "WFH → Comfort"
   - Pattern: "WFH" (summary_contains)
   - Slot: "Comfort"
   - Priority: 10

3. **Create Calendar Events**
   - "WFH Tuesday" (every Tuesday 9-17)
   - "WFH Thursday" (every Thursday 9-17)

**Result**: On WFH days, studio heats to 23°C and other rooms to 21°C. Non-WFH days: no changes.

---

### Example 2: Vacation + Maid Service Override

**Goal**: Energy saving during vacation, but warm for Tuesday maid visits

**Configuration**:

1. **Slots**:
   - "Away": 15°C, eco mode
   - "Comfort": 20°C, heat mode

2. **Bindings**:
   - "Vacation" → "Away" slot (priority 5)
   - "Maid Service" → "Comfort" slot (priority 10)

3. **Calendar**:
   - "Summer Vacation" (2 weeks)
   - "Maid Service" (every Tuesday 8-11, recurring)

**Result**:
- Most days: 15°C (away)
- Tuesday 8-11: 20°C (maid working, priority 10 overrides vacation)
- Tuesday 11:01+: Back to 15°C automatically

---

### Example 3: Multi-Zone with Emergency Override

**Goal**: Different schedules for living zone vs sleeping zone, with emergency button

**Configuration**:

1. **Slots**:
   - "Living Active": 21°C
   - "Sleeping": 18°C
   - "Emergency Heat": 25°C

2. **Bindings**:
   - "Living" → "Living Active" (target: [climate.living, climate.kitchen], priority 5)
   - "Sleep" → "Sleeping" (target: [climate.bedroom], priority 5)
   - "Emergency" → "Emergency Heat" (target: all, priority 99)

3. **Calendars**:
   - "Living Active Hours" (daily 7-22)
   - "Sleep Hours" (daily 22-7)
   - "Emergency" (create when needed from phone!)

**Result**: Living zone and sleeping zone follow independent schedules. Create "Emergency Heat" event from phone → all zones instantly go to 25°C (priority 99 wins).

---

### Example 4: Advanced Climate Control (Heat Pumps & Humidity)

**Goal**: Full climate control with heat pump, humidity management, and temperature ranges

**Configuration**:

1. **Slots**:
   - "Summer Cooling":
     - Temperature Range: 22-25°C (heat_cool mode)
     - Humidity: 60%
     - Fan Mode: auto
     - HVAC Mode: heat_cool

   - "Winter Heating":
     - Temperature: 21°C
     - HVAC Mode: heat
     - Auxiliary Heat: On (for heat pumps)
     - Fan Mode: low

   - "Dehumidify":
     - HVAC Mode: dry
     - Humidity: 50%
     - Fan Mode: high

2. **Bindings**:
   - "Summer" → "Summer Cooling" (priority 5)
   - "Winter" → "Winter Heating" (priority 5)
   - "Humid Day" → "Dehumidify" (priority 10)

3. **Calendar**:
   - "Summer Season" (June-September)
   - "Winter Season" (November-March)
   - "High Humidity Alert" (created when needed)

**Result**:
- Summer: Maintains 22-25°C range with 60% humidity
- Winter: 21°C with backup heat for efficient heat pump operation
- Humid days: Dehumidify mode overrides (priority 10) even during summer/winter

---

**📖 For more complex scenarios, see [ARCHITECTURE.md](ARCHITECTURE.md#-real-world-power-examples)**

---

## 🔧 Manual Override

Climate Control Calendar uses a pure event-driven architecture. All control is performed via calendar events and bindings.

**To temporarily override automatic control, use native Home Assistant features:**

```yaml
# Disable climate control temporarily
service: homeassistant.turn_off
target:
  entity_id: calendar.your_climate_calendar

# Re-enable when needed
service: homeassistant.turn_on
target:
  entity_id: calendar.your_climate_calendar
```

**Alternative: Create temporary calendar events**

```yaml
# Force "Comfort Mode" for next 2 hours
service: calendar.create_event
target:
  entity_id: calendar.your_climate_calendar
data:
  summary: "Comfort Mode"  # Must match a binding pattern
  start_date_time: "{{ now() }}"
  end_date_time: "{{ now() + timedelta(hours=2) }}"
```

---

## 🧠 Decision Engine

Climate Control Calendar uses an intelligent decision engine that evaluates calendar events, conditions, and templates to determine the optimal climate settings.

### Resolution Flow

```
1. 📅 Active Events Detection (every 60s)
   ↓
2. 🔗 Pattern Matching (bindings)
   ↓
3. ✅ Condition Evaluation (optional smart filters)
   ↓
4. ⚡ Priority Resolution (highest wins)
   ↓
5. 🎚️ Slot Activation (climate profile)
   ↓
6. 🌡️ Template Rendering (dynamic values)
   ↓
7. 🔄 Change Detection (apply only if different)
   ↓
8. 🎯 Entity Application (control devices)
```

### 🎨 Template Support

**Make climate values dynamic with Jinja2 templates:**

```yaml
# Static value
temperature: 21.5

# Dynamic template
temperature: "{{ states('input_number.target_temp') | float }}"

# Complex logic
temperature: "{{ states('sensor.outdoor_temp') | float + 2 }}"
humidity: "{{ 60 if states('sensor.outdoor_humidity') | int > 70 else 50 }}"
```

**Supported fields:** temperature, target_temp_high, target_temp_low, humidity

**Benefits:**
- Adapt to outdoor temperature sensors
- Use input helpers for user-adjustable targets
- Calculate relative temperatures (outdoor + offset)
- Smooth transitions based on conditions

**Change Detection:** Templates are re-evaluated every 60 seconds. If the rendered value changes, settings are re-applied automatically.

### 🎯 Condition Support

**Add smart activation logic to bindings:**

Conditions allow bindings to activate only when specific criteria are met. All conditions must pass (AND logic).

**Example - Heating only if cold outside + window closed:**

```yaml
bindings:
  - id: smart_heating
    match:
      type: summary_contains
      value: "WFH"
    conditions:
      - type: numeric_state
        entity_id: sensor.external_temp
        below: 15
      - type: state
        entity_id: binary_sensor.window
        state: 'off'
    slot_id: comfort_slot
    priority: 10
```

**Supported Condition Types:**

| Type | Description | Example Use Case |
|------|-------------|------------------|
| `state` | Check entity state | Window closed, presence detected |
| `numeric_state` | Numeric comparison (above/below) | Temperature thresholds, battery levels |
| `time` | Time range + weekday filter | Work hours only, weekend schedules |
| `template` | Custom Jinja2 logic | Complex multi-sensor conditions |

**Behavior Notes:**
- Conditions are evaluated every 60 seconds (same as template rendering)
- When conditions become false, entities keep their last applied state
- Use multiple bindings with different priorities to handle state transitions
- Conditions can contain templates for dynamic threshold logic

**Configuration:** Conditions are configured via YAML editor (GUI wizard planned for future release).

---

## 📖 Documentation

- [Architecture Decisions](docs/decisions.md) - All architectural decisions from M1-M4
- [Debugging Guide](docs/debugging.md) - Troubleshooting and common issues
- [API Reference](docs/api-reference.md) - Events and services for automations
- [Technical Specifications](climate_control_calendar_technical_architecture.md) - Detailed architecture
- [Developer Instructions](climate_control_calendar_ai_developer_instructions.md) - Contributing guidelines
- [Roadmap](docs/roadmap.md) - Development milestones and timeline

## 🤝 Contributing

Contributions are welcome! Please read the [developer instructions](climate_control_calendar_ai_developer_instructions.md) for coding standards and architecture guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Bug Reports

Please report bugs on the [GitHub Issues](https://github.com/max433/climate_control_calendar/issues) page.

## 💬 Support

For questions and support, please use [GitHub Discussions](https://github.com/max433/climate_control_calendar/discussions).

---

**Note**: Always test new configurations with **Dry Run Mode** enabled first!
