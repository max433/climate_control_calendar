# Installation Guide

Climate Control Calendar can be installed in two ways: via HACS (when available on GitHub) or manually.

## Option 1: HACS Installation (Recommended for GitHub)

**Note**: HACS installation only works when the repository is available on GitHub.

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu (top right)
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/max433/climate_control_calendar`
6. Category: Integration
7. Click "Add"
8. Find "Climate Control Calendar" and click "Download"
9. Restart Home Assistant

---

## Option 2: Manual Installation

### Using the Installation Script (Linux/macOS)

1. Navigate to the repository directory:
   ```bash
   cd /path/to/climate_control_calendar
   ```

2. Run the installation script with your Home Assistant config path:
   ```bash
   ./install.sh /path/to/homeassistant/config
   ```

   **Common paths**:
   - Docker: `/config`
   - Home Assistant Core: `~/.homeassistant`
   - Home Assistant Supervised: `/usr/share/hassio/homeassistant`
   - HAOS: `/config` (from SSH add-on or terminal)

3. Restart Home Assistant

### Manual Copy (All Platforms)

1. Locate your Home Assistant configuration directory:
   - **Docker**: Usually `/config` or bind-mounted to your host
   - **Core**: Usually `~/.homeassistant` or `/home/homeassistant/.homeassistant`
   - **Supervised/HAOS**: `/usr/share/hassio/homeassistant` or `/config`

2. Create the `custom_components` directory if it doesn't exist:
   ```bash
   mkdir -p /path/to/config/custom_components
   ```

3. Copy the integration folder:
   ```bash
   cp -r custom_components/climate_control_calendar /path/to/config/custom_components/
   ```

4. Verify the structure:
   ```
   config/
   ├── configuration.yaml
   └── custom_components/
       └── climate_control_calendar/
           ├── __init__.py
           ├── manifest.json
           ├── strings.json
           ├── config_flow.py
           ├── coordinator.py
           ├── engine.py
           ├── events.py
           ├── flag_manager.py
           ├── applier.py
           ├── services.py
           ├── helpers.py
           ├── const.py
           └── translations/
               ├── en.json
               └── it.json
   ```

5. Restart Home Assistant

---

## Adding the Integration

After installation and restart:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Climate Control Calendar**
4. Follow the configuration wizard:
   - **Step 1**: Select the calendar entity to monitor
   - **Step 2**: Select climate devices to control (optional)
   - **Step 3**: Configure dry run and debug options

---

## Prerequisites

Before adding the integration, ensure you have:

- ✅ **Home Assistant 2024.1.0 or newer**
- ✅ **At least one calendar integration** configured:
  - Google Calendar
  - Local Calendar
  - Nextcloud Calendar
  - CalDAV
  - Any other calendar integration
- ✅ **Climate entities** to control (thermostats, climate devices, etc.)

If you don't have a calendar configured, you'll see an error when trying to add the integration.

---

## Verification

After installation, verify the integration is loaded:

1. Check Home Assistant logs for:
   ```
   INFO (MainThread) [homeassistant.setup] Setting up climate_control_calendar
   ```

2. Check that the integration appears in:
   - Settings → Devices & Services → Integrations

3. If using debug mode, check for:
   ```
   DEBUG (MainThread) [custom_components.climate_control_calendar] ...
   ```

---

## Troubleshooting

### Integration Not Found

If "Climate Control Calendar" doesn't appear in the integration list:

1. Verify files are in the correct location:
   ```bash
   ls -la /path/to/config/custom_components/climate_control_calendar/manifest.json
   ```

2. Check Home Assistant logs for errors:
   ```bash
   tail -f /path/to/config/home-assistant.log | grep climate_control_calendar
   ```

3. Restart Home Assistant again (sometimes requires two restarts)

### "Invalid handler specified" Error

This means `strings.json` is missing. Verify:
```bash
ls -la /path/to/config/custom_components/climate_control_calendar/strings.json
```

If missing, re-copy the integration files.

### "No calendar entities found" Error

You need to install and configure a calendar integration first:

1. Go to Settings → Devices & Services
2. Add a calendar integration (e.g., Google Calendar, Local Calendar)
3. Configure the calendar
4. Try adding Climate Control Calendar again

---

## Updating

### Manual Update

1. Remove old installation:
   ```bash
   rm -rf /path/to/config/custom_components/climate_control_calendar
   ```

2. Copy new version:
   ```bash
   cp -r custom_components/climate_control_calendar /path/to/config/custom_components/
   ```

3. Restart Home Assistant

### HACS Update

If installed via HACS:

1. Go to HACS → Integrations
2. Find "Climate Control Calendar"
3. Click "Update" if available
4. Restart Home Assistant

---

## Uninstallation

1. Remove the integration from Home Assistant:
   - Settings → Devices & Services
   - Find "Climate Control Calendar"
   - Click three dots → Delete

2. Remove files:
   ```bash
   rm -rf /path/to/config/custom_components/climate_control_calendar
   ```

3. Restart Home Assistant

---

## Support

- **Documentation**: See [README.md](README.md) for usage examples
- **Debugging**: See [docs/debugging.md](docs/debugging.md) for troubleshooting
- **API Reference**: See [docs/api-reference.md](docs/api-reference.md) for events and services
- **Issues**: Report bugs at https://github.com/max433/climate_control_calendar/issues
