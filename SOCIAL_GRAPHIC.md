# Climate Control Calendar

## Control your home heating with any calendar app

---

```mermaid
graph TB
    title[<b>Climate Control Calendar Architecture</b>]

    subgraph cal ["📅 YOUR CALENDARS"]
        c1["Google Calendar<br/>'Smart Working'<br/>'Vacation Mode'<br/>'Weekend Comfort'"]
        c2["Local Calendar<br/>'Night Mode'<br/>'Guest Visits'<br/>'Emergency Override'"]
    end

    subgraph bind ["🔗 BINDINGS - Pattern Matching"]
        b1["Match: 'Smart Working'<br/>Priority: 10<br/>→ Slot: Comfort"]
        b2["Match: 'Vacation'<br/>Priority: 5<br/>→ Slot: Away"]
        b3["Match: 'Summer'<br/>Priority: 7<br/>→ Slot: Summer"]
        b4["Match: 'Emergency'<br/>Priority: 99<br/>→ Slot: Emergency"]
    end

    subgraph slots ["🎚️ SLOTS - Climate Profiles"]
        s1["Comfort<br/>21°C, Heat Mode<br/>Studio: 23°C override<br/>Bedroom: 19°C override"]
        s2["Away<br/>15°C, Eco Mode<br/>All entities<br/>Low humidity: 50%"]
        s3["Summer<br/>22-25°C Range (heat_cool)<br/>Humidity: 60%<br/>Fan: Auto"]
        s4["Emergency<br/>25°C, Max Heat<br/>Aux Heat: ON<br/>Priority 99"]
    end

    subgraph devices ["🌡️ YOUR CLIMATE DEVICES"]
        d1["climate.studio"]
        d2["climate.bedroom"]
        d3["climate.living"]
        d4["climate.kitchen"]
    end

    cal --> bind
    bind --> slots
    slots --> devices

    note1["✨ Create events in any calendar app<br/>⚡ Changes active within 60 seconds<br/>🎯 Priority system resolves conflicts<br/>🏠 Per-entity customization<br/>🌡️ Temperature ranges for heat_cool mode<br/>💧 Humidity & aux heat control<br/>🔔 Notifications only on changes"]

    style cal fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#000
    style bind fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style slots fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff
    style devices fill:#F44336,stroke:#C62828,stroke-width:3px,color:#fff
    style note1 fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
```

---

## How It Works

1. **📅 Create Calendar Events** - Use Google Calendar, Outlook, or any HA calendar
2. **🔗 Bindings Match Patterns** - "Smart Working" event → activates "Comfort" slot
3. **🎚️ Slots Apply Settings** - 21°C with per-room overrides
4. **🌡️ Devices Updated** - Only when events start/end (no spam!)

---

## Real Example

```yaml
Calendar Event: "Work From Home" (Tue/Thu 9-17)
    ↓
Binding Matches: "Work" pattern
    ↓
Activates Slot: "Comfort Mode"
    ↓
Applies:
  🏠 climate.studio: 23°C (working here!)
  🏠 climate.bedroom: 19°C (not using)
  🏠 climate.living: 21°C (default)
```

**Emergency override?** Create "Emergency Heat" event → priority 99 → instant activation!

---

## Advanced Example: Heat Pump with Humidity Control

```yaml
Calendar Event: "Summer Comfort" (Jun-Sep)
    ↓
Binding Matches: "Summer" pattern
    ↓
Activates Slot: "Summer Mode"
    ↓
Applies:
  🌡️ Temperature Range: 22-25°C (heat_cool mode)
  💧 Humidity: 60% (prevents mold)
  🌬️ Fan Mode: Auto
  🏠 All climate entities controlled
```

**Why temperature range?** Prevents constant on/off cycling, saves energy!

---

## Why Event-Based > Time-Based?

| Feature | Time-Based ⏰ | Event-Based 📅 |
|---------|--------------|----------------|
| Change schedule | Edit config + restart | Move calendar event |
| Vacation mode | Disable automation | Create "Vacation" event |
| Family control | ❌ Tech-only | ✅ Everyone uses calendar |
| Exceptions | Complex conditions | Delete/modify event |
| Mobile access | ❌ | ✅ Calendar app |

---

## Get Started

🔗 **GitHub**: [max433/climate_control_calendar](https://github.com/max433/climate_control_calendar)

📦 **HACS**: Search "Climate Control Calendar"

📚 **Docs**: Full architecture guide in repo

---

**Transform your heating schedule from rigid code to flexible calendar events!**

*Built for Home Assistant • Open Source • MIT License*
