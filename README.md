# Climate Control Calendar

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/max433/climate_control_calendar.svg)](https://github.com/max433/climate_control_calendar/releases)
[![License](https://img.shields.io/github/license/max433/climate_control_calendar.svg)](LICENSE)

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

3. **🎚️ Slots**: Reusable climate configuration templates
   - Define temperature, HVAC mode, preset, etc.
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

**📖 For more complex scenarios, see [ARCHITECTURE.md](ARCHITECTURE.md#-real-world-power-examples)**

---

## 🔧 Services

The integration provides four services for manual control:

### `climate_control_calendar.set_flag`

Set an override flag to alter automatic behavior.

**Parameters**:
- `flag_type`: `skip_today` | `skip_until_next_slot` | `force_slot`
- `target_slot_id`: Required when `flag_type` is `force_slot`

**Examples**:
```yaml
# Skip all automatic changes until midnight
service: climate_control_calendar.set_flag
data:
  flag_type: skip_today

# Skip current slot, resume at next slot transition
service: climate_control_calendar.set_flag
data:
  flag_type: skip_until_next_slot

# Force specific slot (find slot ID in configuration)
service: climate_control_calendar.set_flag
data:
  flag_type: force_slot
  target_slot_id: a3f5c8d2e1b4
```

### `climate_control_calendar.clear_flag`

Clear active override flag and resume normal operation.

```yaml
service: climate_control_calendar.clear_flag
```

### `climate_control_calendar.force_slot`

Convenience service to force a specific slot (wrapper for `set_flag` with `force_slot` type).

```yaml
service: climate_control_calendar.force_slot
data:
  slot_id: a3f5c8d2e1b4
```

### `climate_control_calendar.refresh_now`

Force immediate coordinator refresh and slot evaluation (bypass 60-second poll interval).

```yaml
service: climate_control_calendar.refresh_now
```

---

## 🛠️ Development Status

**✅ Milestone 1** (Foundation) - Completed:
- Integration structure with config flow
- Calendar monitoring with DataUpdateCoordinator
- Base infrastructure and helpers

**✅ Milestone 2** (Slot Engine) - Completed:
- Slot resolution engine with overnight support
- Event emission system (8 event types)
- Dry run mode with comprehensive logging

**✅ Milestone 3** (Device Control) - Completed:
- Sequential climate payload application
- Override flags with HA Storage persistence
- Four services for manual control
- Retry logic with error handling

**🔄 Milestone 4** (Polish & Release) - In Progress:
- Italian translations ✅
- Documentation (README, debugging guide, API reference)
- Unit tests for critical paths
- v1.0.0 release preparation

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

**Note**: This integration is in early development. Features are being added incrementally following a milestone-based approach. Always test with **Dry Run Mode** enabled first!
