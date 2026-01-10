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
3. **Climate Payload**: Temperature and HVAC mode to apply when a slot is active
4. **Engine**: The logic that evaluates active calendar, time slots, and applies settings

### Typical Workflow

```
Calendar Event Active → Engine Evaluates → Finds Matching Slot → Applies Climate Payload
```

## 🛠️ Development Status

This integration is under active development. Current milestone:

**✅ Milestone 1** (Completed):
- Skeleton integration structure
- Config flow with calendar detection
- Coordinator for calendar polling
- Base infrastructure

**🔄 Milestone 2** (In Progress):
- Slot engine implementation
- Dry run execution
- Event emission system

**📋 Upcoming**:
- Device application logic (M3)
- Override flags (M3)
- UX polish and documentation (M4)

## 📖 Documentation

- [Technical Architecture](climate_control_calendar_technical_architecture.md)
- [Developer Instructions](climate_control_calendar_ai_developer_instructions.md)
- [Architecture Decisions](docs/decisions.md) *(coming soon)*
- [Debugging Guide](docs/debugging.md) *(coming soon)*

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
