# Dashboard Panel - User Guide

## Overview

The Climate Control Calendar Dashboard provides a **read-only** visualization of your system's current state and timeline. It's designed for monitoring, debugging, and understanding what your automation is doing.

## Features

### 1. Live Overview
Shows real-time system status:
- **Active Slot**: Which climate profile is currently active
- **Trigger Reason**: Which calendar event and binding triggered it
- **Affected Entities**: Status of all climate entities being controlled
- **Auto-refresh**: Updates automatically when coordinator polls (every 60s)

### 2. Timeline View
Displays today's schedule:
- **Events List**: All calendar events matched to slots
- **Coverage Analysis**: Percentage of day covered by automations
- **Gap Detection**: Identifies time periods without automation control
- **Visual Timeline**: Shows active, upcoming, and past events

## Accessing the Dashboard

After installing the integration:

1. **Sidebar Access**: Look for "Climate Control" in the Home Assistant sidebar
2. **Icon**: Calendar with clock icon (mdi:calendar-clock)
3. **Direct URL**: http://your-ha-instance/climate_control_calendar

## What You'll See

### Active Slot Card (Green)
```
🟢 Active Slot: "Riscaldamento Notte"
📅 Triggered by: Calendar "Casa" → Pattern "*notte*"
📆 Event: "Riscaldamento casa notte"
⏱️ Active: 22:00 → 07:00

🎯 Affected Climate Entities (3)
✅ climate.soggiorno → 20°C (heat)
✅ climate.camera → 20°C (heat)
✅ climate.bagno → 19°C (heat)
```

### No Active Slot (Gray)
```
No active slot - No calendar events matched to bindings
```

### Timeline Card
```
📅 Today's Timeline (2026-01-17)
Coverage: 95%
████████████████████░

Events & Slots Applied (5)
🟢 00:00 - 07:00: "Notte" → Slot: "Riscaldamento Notte"
🔵 07:00 - 09:00: "Mattina" → Slot: "Mattina"
⚪ 09:00 - 18:00: "Lavoro" → Slot: "Smart Working" (past)

⚠️ Coverage Gaps (1)
08:00 - 09:00 (1h): No matching events/bindings
```

## Understanding Status Icons

- 🟢 **Active**: Event is currently active (now is within event time range)
- 🔵 **Upcoming**: Event starts in the future
- ⚪ **Past**: Event has already ended
- ✅ **OK**: Entity is responding and configured correctly
- ⚠️ **Warning**: Entity unavailable or minor issue
- ❌ **Error**: Entity not found

## Coverage Analysis

### Good Coverage (100%)
```
✅ Full day coverage - No gaps
```

### Partial Coverage (<100%)
```
⚠️ Coverage Gaps (2)
08:00-09:00 (1h): No matching events/bindings
14:00-17:00 (3h): No matching events/bindings
```

**What this means:**
- During gap periods, climate entities retain their last applied state
- No automatic control happens during gaps
- Consider adding calendar events or bindings for these periods

## Testing with Fake Climate Entities

To test all dashboard features without real hardware:

1. **Add test entities** to your `configuration.yaml`:
   ```yaml
   # See docs/test-climate-entities.yaml for full configuration
   ```

2. **Create calendar events**:
   - Add events to your calendar with titles matching your bindings
   - Example: "Riscaldamento notte" (matches pattern "*notte*")

3. **Configure bindings**:
   - Use Climate Control Calendar config flow
   - Add bindings that match your test calendar events

4. **Monitor dashboard**:
   - Open dashboard panel
   - Watch Live Overview update when events become active
   - Check Timeline for daily schedule

## Real-time Updates

The dashboard subscribes to coordinator updates via WebSocket:

- **Automatic refresh**: When coordinator polls calendars (every 60s)
- **Manual refresh**: Click "🔄 Refresh" button in header
- **No polling**: Dashboard only updates when data changes

## Troubleshooting

### Dashboard shows "Loading..."
- Check browser console for errors
- Verify integration is loaded: Developer Tools → States → search "climate_control_calendar"
- Restart Home Assistant

### "No active slot" always showing
- Check calendar has events with matching bindings
- Verify event times overlap with current time
- Review binding patterns in configuration

### Coverage analysis shows gaps
- **Expected**: Not all hours need automation
- **Fix**: Add calendar events for gap periods, or
- **Accept**: Entities will maintain last applied state during gaps

### Entities showing "Unavailable"
- Climate entity is offline or disabled
- Check entity state: Developer Tools → States
- Fix underlying entity issue

## Theme Support

The dashboard automatically adapts to Home Assistant theme:

- **Light mode**: Uses light theme colors
- **Dark mode**: Uses dark theme colors
- **Custom themes**: Inherits your active theme colors

Uses CSS variables:
- `--primary-color`: Accent colors
- `--card-background-color`: Card backgrounds
- `--primary-text-color`: Text colors
- `--success-color`: Active slot indicator
- `--warning-color`: Warnings and gaps

## Performance

- **Lightweight**: No heavy computations in frontend
- **Efficient**: Data aggregated by backend service layer
- **Cached**: WebSocket subscription prevents redundant polling
- **Responsive**: Works on desktop, tablet, and mobile

## Future Enhancements (Planned)

- [ ] Week view timeline
- [ ] Conflict detection (multiple bindings same priority)
- [ ] Export timeline as PDF/image
- [ ] Edit configuration directly from dashboard
- [ ] Statistics and charts (most used slots, coverage trends)

## Technical Details

### Architecture
```
Frontend Panel (Lit Element)
    ↓ WebSocket
Backend API (websocket.py)
    ↓
Dashboard Service (dashboard_service.py)
    ↓ Aggregates data from
[Coordinator] [Engine] [BindingManager]
```

### WebSocket Commands
- `climate_control_calendar/get_live_state`: Current state
- `climate_control_calendar/get_timeline`: Daily timeline
- `climate_control_calendar/subscribe_updates`: Real-time updates

### Data Flow
1. Coordinator polls calendars (every 60s)
2. Engine evaluates events → bindings → slots
3. Dashboard Service aggregates live state
4. WebSocket pushes update to frontend
5. Frontend re-renders

---

**Need help?** Open an issue: https://github.com/max433/climate_control_calendar/issues
