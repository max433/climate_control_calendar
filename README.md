# Climate Control Calendar

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/max433/climate_control_calendar.svg)](https://github.com/max433/climate_control_calendar/releases)
[![License](https://img.shields.io/github/license/max433/climate_control_calendar.svg)](LICENSE)

A Home Assistant custom integration that manages climate devices (thermostats, valves) based on calendar events representing different usage patterns.

## 🎯 Concept

**Climate Control Calendar** transforms your Home Assistant calendars into intelligent climate control profiles. Instead of programming complex schedules, you simply create calendar events that represent your lifestyle:

- 📅 **"Smart Working Week"** - Warmer temperature during work hours
- 🏖️ **"Summer Vacation"** - Energy-saving mode while away
- 🏠 **"Weekend Home"** - Comfort settings for relaxation
- 🌙 **"Night Mode"** - Lower temperatures for better sleep

The integration automatically detects active calendar events and applies corresponding climate settings to your devices.

## ✨ Key Features

- **Calendar-Driven**: Control climate based on calendar events
- **Time Slots**: Define temperature/mode profiles for different times of day
- **Dry Run Mode**: Test configurations without actually changing device states
- **Event System**: Full event emission for automation triggers
- **Override Flags**: Temporarily skip or force specific behaviors
- **GUI Configuration**: No YAML needed - everything configurable through UI
- **Multi-Device**: Control multiple climate entities simultaneously

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

### Core Concepts

1. **Calendar Entity**: A Home Assistant calendar that represents your usage patterns
2. **Time Slots**: Configured time windows (e.g., "Morning 06:00-09:00") with associated climate settings
3. **Climate Payload**: Temperature, HVAC mode, preset, fan, and swing settings to apply when a slot is active
4. **Engine**: The logic that evaluates active calendar, time slots, override flags, and applies settings to devices
5. **Override Flags**: Manual controls to skip or force specific slot behaviors

### Typical Workflow

```
Calendar Event Active → Engine Evaluates → Finds Matching Slot → Applies Climate Payload → Devices Updated
                     ↑
                Override Flags (optional manual control)
```

## 💡 Usage Examples

### Scenario 1: Smart Working from Home

**Use Case**: When working from home, you want warmer temperatures during work hours and eco mode outside work hours.

**Setup**:
- **Calendar**: Create "WFH" (Work From Home) events on days you work from home
- **Slots** (active when calendar ON):
  - `morning_warmup`: 06:00-09:00, Mon-Fri → `{temperature: 22, hvac_mode: heat}`
  - `work_hours`: 09:00-18:00, Mon-Fri → `{temperature: 21, preset_mode: comfort}`
  - `evening_eco`: 18:00-23:00, Mon-Fri → `{temperature: 19, preset_mode: eco}`
  - `night_off`: 23:00-06:00 → `{hvac_mode: off}`

**Behavior**: On WFH days, heating automatically adjusts throughout the day. On office days (calendar OFF), no automatic changes occur.

---

### Scenario 2: Vacation Mode

**Use Case**: During vacation, minimize energy usage but prevent freezing/overheating.

**Setup**:
- **Calendar**: Create "Vacation" event spanning vacation dates
- **Slots** (active when calendar ON):
  - `away_mode`: 00:00-23:59 → `{temperature: 15, preset_mode: away, hvac_mode: heat}`
  - `morning_check`: 08:00-09:00 → `{temperature: 18, hvac_mode: heat}` (prevent mold)

**Behavior**: While vacation event is active, maintain minimal heating. When vacation ends (calendar OFF), normal patterns resume automatically.

---

### Scenario 3: Weekend vs Weekday

**Use Case**: Different comfort levels for weekends (more time at home) vs weekdays (out during day).

**Setup**:
- **Calendar**: Create recurring "Weekend Comfort" event for Saturdays and Sundays
- **Slots** (active when calendar ON):
  - `morning_comfort`: 07:00-12:00, Sat-Sun → `{temperature: 22, preset_mode: comfort}`
  - `afternoon_active`: 12:00-22:00, Sat-Sun → `{temperature: 21, hvac_mode: heat}`
  - `night_sleep`: 22:00-07:00, Sat-Sun → `{temperature: 18, preset_mode: sleep}`

**Behavior**: On weekends, enjoy higher comfort levels all day. Weekdays follow different calendar/slots or rely on thermostat defaults.

---

### Scenario 4: Night Setback with Override

**Use Case**: Automatic night temperature reduction, but ability to override when sick or cold.

**Setup**:
- **Calendar**: Create "Active Heating Season" event for winter months
- **Slots** (active when calendar ON):
  - `day_comfort`: 06:00-22:00 → `{temperature: 21, hvac_mode: heat}`
  - `night_setback`: 22:00-06:00 → `{temperature: 17, hvac_mode: heat}`

**Manual Override**:
```yaml
# Skip tonight's setback (automation or script)
service: climate_control_calendar.set_flag
data:
  flag_type: skip_until_next_slot
```

**Behavior**: Normally reduces temperature at night. Use override flag when you want to maintain day temperature through the night.

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
