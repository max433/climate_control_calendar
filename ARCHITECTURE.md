# 🏗️ Climate Control Calendar - Architecture Overview

**Transform any Home Assistant calendar into intelligent climate control**

---

## 🎯 The Big Picture

Climate Control Calendar replaces rigid, time-based heating schedules with **flexible, event-driven climate management**. Your lifestyle changes daily—your heating should too.

```mermaid
graph LR
    A[📅 Calendar Events] -->|Pattern Matching| B[🔗 Bindings]
    B -->|Activate| C[🎚️ Slots]
    C -->|Apply Settings| D[🌡️ Climate Entities]

    style A fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style B fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style C fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff
    style D fill:#F44336,stroke:#C62828,stroke-width:3px,color:#fff
```

---

## 🧩 Core Components

### 1. 📅 **Calendars** - Your Lifestyle as Events

**Any Home Assistant calendar becomes a control source.**

Instead of programming "Monday 9-18 → 21°C", you create calendar events:
- **"Smart Working"** (every workday)
- **"Vacation Mode"** (summer weeks)
- **"Emergency Override"** (ad-hoc event created in 10 seconds)

**Why it's powerful:**
- ✅ Manage schedules in your favorite calendar app (Google Calendar, Outlook, etc.)
- ✅ Recurring events, exceptions, and one-off events all work seamlessly
- ✅ Share calendars with family members
- ✅ Modify on-the-go from your phone
- ✅ Multiple calendars for different zones/purposes

**Example:**
```
Google Calendar → Home Assistant → Climate Control
└─ "WFH Morning" (every Tue/Thu 8-12) → binding matches → applies "Comfort" slot
```

---

### 2. 🔗 **Bindings** - The Smart Pattern Matcher

**Bindings connect calendar events to climate configurations using pattern matching.**

When a calendar event becomes active, bindings check if it matches their patterns.

#### Binding Anatomy:

```yaml
Binding:
  📋 ID: unique_binding_123
  📅 Calendars: calendar.work (or "*" for all)
  🔍 Match Pattern:
      Type: summary_contains
      Value: "Smart Working"
  🎯 Target Slot: slot_comfort_id
  🏠 Target Entities: [climate.studio, climate.bedroom] (optional)
  ⚡ Priority: 10 (higher wins conflicts)
```

#### Pattern Types:

| Type | Description | Example |
|------|-------------|---------|
| `summary` | Exact match | Event "Morning" matches pattern "Morning" |
| `summary_contains` | Partial match | Event "WFH Morning" matches pattern "Morning" |
| `regex` | Regex pattern | Event "smart_work_2024" matches `smart.*` |

#### Priority System:

When **multiple events are active** simultaneously, priority determines which wins:

```
Active Events:
  📅 Event A: "Smart Working" → Binding (priority 5) → Slot 1
  📅 Event B: "Emergency Heat" → Binding (priority 20) → Slot 2
  📅 Event C: "Night Mode" → Binding (priority 3) → Slot 3

Result:
  🏆 Event B wins (priority 20) → Applies Slot 2 to entities
```

#### Multi-Calendar Support:

```
Calendar 1 (Work): "Office Day" → Binding 1 → Slot "Eco"
Calendar 2 (Personal): "Home Renovation" → Binding 2 → Slot "Off"
Calendar 3 (Kids): "School Holiday" → Binding 3 → Slot "Comfort"

All monitored simultaneously, priorities resolve conflicts
```

---

### 3. 🎚️ **Slots** - Climate Configuration Templates

**Slots are reusable climate setting templates.**

Think of slots as "climate profiles" that bindings activate.

#### Slot Anatomy:

```yaml
Slot:
  🆔 ID: slot_comfort_123
  🏷️ Label: "Comfort Mode"
  🌡️ Default Payload:
      # Temperature settings (choose one approach)
      temperature: 21              # Single temperature target
      # OR for heat_cool mode:
      target_temp_high: 25         # Maximum temperature
      target_temp_low: 22          # Minimum temperature

      # HVAC control
      hvac_mode: heat              # heat, cool, heat_cool, auto, off, fan_only, dry
      preset_mode: comfort         # away, home, eco, boost, comfort, etc.

      # Advanced climate control
      humidity: 60                 # Target humidity (0-100%)
      aux_heat: true               # Auxiliary/backup heat (for heat pumps)
      fan_mode: auto               # auto, low, medium, high, off
      swing_mode: both             # off, vertical, horizontal, both

  🏠 Entity Overrides:
      climate.bedroom:
        temperature: 22            # Bedroom warmer
      climate.bathroom:
        temperature: 19            # Bathroom cooler
        humidity: 55               # Lower humidity in bathroom

  🚫 Excluded Entities:
      - climate.garage             # Never control garage
```

#### Why Reusable?

Multiple bindings can activate the same slot:

```
Binding 1: "Morning Work" → Slot "Comfort"
Binding 2: "Afternoon Work" → Slot "Comfort"
Binding 3: "Weekend Active" → Slot "Comfort"

All use same climate settings, no duplication!
```

#### Entity-Specific Overrides:

Control different rooms differently **within the same slot**:

```
Event: "Smart Working" → Slot "Work Mode"
  🏠 Global Default: 21°C
  🛋️ climate.living_room: 21°C (default)
  💼 climate.studio: 23°C (override - working here!)
  🛏️ climate.bedroom: 18°C (override - not using now)
```

---

### 4. 🌡️ **Climate Entities** - The Physical Devices

**Target entities receive climate settings from activated slots.**

#### Flexible Targeting:

| Level | Where Defined | Scope |
|-------|---------------|-------|
| **Global Pool** | Integration config | All entities by default |
| **Binding Target** | Specific binding | Override for this binding only |
| **Slot Override** | Specific slot | Custom settings per entity |
| **Slot Exclusion** | Specific slot | Skip certain entities |

#### Example Flow:

```
Global Pool: [climate.studio, climate.bedroom, climate.living, climate.kitchen]

Event: "Work From Home" active
↓
Binding matches:
  Target: [climate.studio, climate.bedroom]  ← Only these 2
  Priority: 10
↓
Slot "Comfort" applied:
  climate.studio: 23°C (entity override)
  climate.bedroom: 21°C (default payload)
  climate.living: unchanged (not in binding target)
  climate.kitchen: unchanged (not in binding target)
```

---

## 🚀 Real-World Power Examples

### Example 1: **Flexible Smart Working Schedule**

**Problem:** Work-from-home days vary week to week.

**Old Way (time-based):**
```
❌ Hardcoded: Mon-Fri 9-17 → 21°C
   Problem: What about vacation? Sick days? Irregular schedules?
```

**New Way (event-based):**
```
✅ Calendar: Create "WFH" event on days you work from home
   Binding: "WFH" → Slot "Work Comfort" (23°C studio, 19°C bedroom)

   Flexibility:
   - Delete event → no heating that day
   - Add exception → heating follows
   - Recurring with exclusions → fully flexible
```

---

### Example 2: **Multi-Zone with Priorities**

**Scenario:** 3 zones, different schedules, emergency override.

```
Calendars:
  📅 calendar.zone_living: "Living Active" events
  📅 calendar.zone_sleeping: "Sleeping Zone" events
  📅 calendar.emergencies: "Emergency Heat" events

Bindings:
  🔗 Binding 1: calendar.zone_living → "Living" → Slot "Comfort" (priority 5)
     Target: [climate.living, climate.kitchen]

  🔗 Binding 2: calendar.zone_sleeping → "Sleep" → Slot "Night" (priority 5)
     Target: [climate.bedroom, climate.bathroom]

  🔗 Binding 3: calendar.emergencies → "Emergency" → Slot "Max Heat" (priority 99)
     Target: "*" (all entities)

Scenario:
  ⏰ 14:00: "Living Active" event ongoing → Living zone at 21°C
  ⏰ 22:00: "Sleep" event starts → Sleeping zone at 18°C, living continues 21°C
  ⏰ 02:00: Add "Emergency Heat" event from phone (burst pipe!)
           → ALL zones immediately switch to 25°C (priority 99 wins)
```

---

### Example 3: **Vacation + Weekly Maid Service**

**Scenario:** Away for 2 weeks, but maid comes every Tuesday morning.

```
Calendar:
  📅 "Vacation" (2 weeks, all-day event)
  📅 "Maid Service" (every Tuesday 8-11)

Bindings:
  🔗 Binding 1: "Vacation" → Slot "Away" (priority 5)
     Payload: {temperature: 15, preset_mode: away}

  🔗 Binding 2: "Maid Service" → Slot "Comfort" (priority 10)
     Payload: {temperature: 20, hvac_mode: heat}

Result:
  📅 Mon, Wed-Sun: 15°C (away mode)
  📅 Tuesday 8-11: 20°C (maid working, priority 10 wins)
  📅 Tuesday 11:01: Back to 15°C (maid event ends, vacation resumes)
```

No manual intervention needed! Calendar handles it.

---

### Example 4: **Per-Room Custom Schedules**

**Scenario:** Kids' room needs different schedule than master bedroom.

```
Slots:
  🎚️ Slot "Night Adults":
     Default: 18°C
     Overrides:
       climate.master_bedroom: 17°C (adults like cooler)

  🎚️ Slot "Night Kids":
     Default: 20°C
     Overrides:
       climate.kids_room: 21°C (kids need warmer)

Bindings:
  🔗 "Adult Sleep" → Slot "Night Adults" → Entities: [climate.master_bedroom]
  🔗 "Kids Sleep" → Slot "Night Kids" → Entities: [climate.kids_room, climate.playroom]

Calendar Events:
  📅 "Adult Bedtime" (22:00-07:00) → 17°C master
  📅 "Kids Bedtime" (20:00-07:00) → 21°C kids room, 20°C playroom
```

Different schedules, different temperatures, one integration!

---

### Example 5: **Advanced Climate Features for Modern HVAC**

**Scenario:** Heat pump with humidity control and temperature range management.

```
Slots:
  🎚️ Slot "Summer Comfort":
     Temperature Range: 22-25°C (heat_cool mode)
     Humidity: 60%
     Fan Mode: auto
     HVAC Mode: heat_cool

  🎚️ Slot "Winter Efficient":
     Temperature: 21°C
     HVAC Mode: heat
     Auxiliary Heat: ON (backup heat for cold days)
     Fan Mode: low

  🎚️ Slot "Dehumidify":
     HVAC Mode: dry
     Humidity: 50%
     Fan Mode: high
     Swing Mode: both

Bindings:
  🔗 "Summer Season" → Slot "Summer Comfort" (priority 5)
  🔗 "Winter Season" → Slot "Winter Efficient" (priority 5)
  🔗 "Humidity Alert" → Slot "Dehumidify" (priority 15)

Calendar Events:
  📅 "Summer" (June 1 - Sep 30, all-day)
  📅 "Winter" (Nov 1 - Mar 31, all-day)
  📅 "High Humidity Day" (created manually when needed)

Result:
  🌞 Summer: Maintains temperature between 22-25°C with humidity at 60%
  ❄️ Winter: Fixed 21°C with auxiliary heat for efficient heat pump operation
  💧 Humid Days: Dehumidify mode overrides seasonal settings (priority 15)
```

**Why this works:**
- Temperature range prevents constant on/off cycling in heat_cool mode
- Humidity control maintains comfort and prevents mold
- Auxiliary heat improves efficiency on very cold days
- Priority system allows weather-based overrides

---

## 🧠 Decision Engine: The Brain Behind Climate Control

The Decision Engine is the intelligent core that transforms calendar events into climate actions. It evaluates events, conditions, and templates through a multi-step resolution process.

### 📊 Resolution Flow

```mermaid
graph TD
    A[⏰ Coordinator Tick<br/>Every 60s] --> B[📅 Fetch Active Events<br/>calendar.get_events]
    B --> C{🔗 Pattern Matching<br/>Bindings Check}
    C -->|Match Found| D{✅ Condition Evaluation<br/>All Must Pass}
    C -->|No Match| END1[❌ Skip Event]
    D -->|Conditions Pass| E[⚡ Priority Resolution<br/>Highest Wins]
    D -->|Conditions Fail| END2[❌ Skip Binding]
    E --> F[🎚️ Slot Activation<br/>Get Climate Profile]
    F --> G[🌡️ Template Rendering<br/>Resolve Dynamic Values]
    G --> H{🔄 Change Detection<br/>Different from Last?}
    H -->|Changed| I[🎯 Apply to Entities<br/>climate.set_*]
    H -->|Same| END3[✅ Skip Apply]
    I --> END4[✅ Done]

    style A fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style E fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style G fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff
    style I fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
```

### 🔍 Step-by-Step Breakdown

#### Step 1: 📅 Active Events Detection

**When:** Every 60 seconds (coordinator polling)

**What:** Fetch events from all monitored calendars

```python
# Service call to calendar integration
events = await hass.services.async_call(
    "calendar",
    "get_events",
    {
        "entity_id": "calendar.work",
        "start_date_time": now - 1h,
        "end_date_time": now + 24h,
    }
)
```

**Output:** List of active calendar events

---

#### Step 2: 🔗 Pattern Matching

**What:** Each active event is tested against all bindings

**Match Types:**

| Type | Logic | Example |
|------|-------|---------|
| `summary` | Exact match | Event "WFH" matches binding pattern "WFH" |
| `summary_contains` | Partial match | Event "WFH Tuesday" matches pattern "WFH" |
| `regex` | Regex pattern | Event "smart_work_2024" matches `smart.*` |

**Code:**
```python
for binding in bindings:
    if binding["calendars"] != "*":
        if event.calendar_id not in binding["calendars"]:
            continue  # Skip - wrong calendar

    match_type = binding["match"]["type"]
    pattern = binding["match"]["value"]

    if match_type == "summary" and event.summary == pattern:
        matched_bindings.append(binding)
    elif match_type == "summary_contains" and pattern in event.summary:
        matched_bindings.append(binding)
    elif match_type == "regex" and re.match(pattern, event.summary):
        matched_bindings.append(binding)
```

**Output:** List of bindings that matched the event

---

#### Step 3: ✅ Condition Evaluation (NEW)

**What:** Filter bindings based on smart conditions

**When:** After pattern matching, before priority resolution

**Logic:** ALL conditions must pass (AND logic)

**Example:**
```yaml
conditions:
  - type: numeric_state
    entity_id: sensor.external_temp
    below: 15                      # ✅ Pass if temp < 15°C
  - type: state
    entity_id: binary_sensor.window
    state: 'off'                   # ✅ Pass if window closed
  - type: time
    after: '08:00'
    before: '18:00'
    weekday: [mon, tue, wed, thu, fri]  # ✅ Pass if work hours
```

**Supported Condition Types:**

##### 🔵 State Condition
Check if entity has specific state:
```yaml
- type: state
  entity_id: binary_sensor.window_living
  state: 'off'                    # Window must be closed
```

##### 🔵 Numeric State Condition
Compare numeric entity values:
```yaml
- type: numeric_state
  entity_id: sensor.outdoor_temp
  below: 15                       # Outdoor temp < 15°C
  above: 5                        # AND > 5°C (optional)
```

##### 🔵 Time Condition
Time range and weekday filters:
```yaml
- type: time
  after: '08:00'                  # After 8 AM
  before: '18:00'                 # Before 6 PM
  weekday: [mon, tue, wed, thu, fri]  # Weekdays only
```

##### 🔵 Template Condition
Custom Jinja2 logic:
```yaml
- type: template
  value_template: >
    {{ states('sensor.outdoor_temp')|float < 15 and
       states('binary_sensor.window')|string == 'off' }}
```

**Code:**
```python
async def check_conditions(hass, conditions):
    if not conditions:
        return True  # No conditions = always pass

    for condition in conditions:
        result = await condition.async_from_config(hass, condition)
        if not result(hass):
            return False  # One failed = binding skipped

    return True  # All passed
```

**Behavior Notes:**
- Conditions re-evaluated every 60 seconds (same as coordinator cycle)
- If conditions become false, entity keeps last applied state
- Use multiple bindings with priority to handle state transitions
- Templates in conditions support dynamic threshold logic

**Output:** List of bindings that passed conditions

---

#### Step 4: ⚡ Priority Resolution

**What:** Handle conflicts when multiple bindings target same entities

**Logic:** For each entity, the highest-priority binding wins

**Example:**
```yaml
# Active bindings after pattern match + conditions
Binding A: priority 5,  target: [climate.living, climate.studio]
Binding B: priority 10, target: [climate.studio]
Binding C: priority 7,  target: [climate.bedroom]

# Resolution per entity:
climate.living:  Binding A (priority 5, no conflict)
climate.studio:  Binding B (priority 10, wins over A)
climate.bedroom: Binding C (priority 7, no conflict)
```

**Code:**
```python
entity_to_binding = {}

for entity_id in all_entities:
    best_binding = None
    best_priority = -1

    for binding in condition_passed_bindings:
        if entity_id in binding_target_entities(binding):
            if binding["priority"] > best_priority:
                best_binding = binding
                best_priority = binding["priority"]

    if best_binding:
        entity_to_binding[entity_id] = best_binding
```

**Output:** Dictionary mapping each entity to winning binding

---

#### Step 5: 🎚️ Slot Activation

**What:** Retrieve climate profile from winning binding's slot

**Structure:**
```yaml
slot:
  id: comfort_slot
  label: "Comfort Mode"
  default_climate_payload:
    temperature: 21              # Static value
    hvac_mode: heat
    humidity: 60
  entity_overrides:
    climate.studio:
      temperature: 23            # Studio warmer
```

**Output:** Slot configuration for each entity

---

#### Step 6: 🌡️ Template Rendering (NEW)

**What:** Resolve dynamic template values in climate payloads

**When:** After slot activation, before applying to entities

**Supported Fields:**
- `temperature`
- `target_temp_high`
- `target_temp_low`
- `humidity`

**Examples:**

##### Static Value (No Template)
```yaml
temperature: 21.5
# ↓ Rendering
temperature: 21.5              # No change
```

##### Simple Template
```yaml
temperature: "{{ states('input_number.target_temp') | float }}"
# ↓ Rendering (input_number.target_temp = 22.5)
temperature: 22.5
```

##### Complex Template with Logic
```yaml
temperature: "{{ states('sensor.outdoor_temp') | float + 2 }}"
# ↓ Rendering (sensor.outdoor_temp = 10)
temperature: 12.0

humidity: "{{ 60 if states('sensor.outdoor_humidity')|int > 70 else 50 }}"
# ↓ Rendering (sensor.outdoor_humidity = 75)
humidity: 60
```

##### Multi-Sensor Template
```yaml
temperature: >
  {% set outdoor = states('sensor.outdoor_temp')|float %}
  {% set delta = states('input_number.temp_offset')|float %}
  {{ (outdoor + delta) | round(1) }}
# ↓ Rendering (outdoor = 10, offset = 3)
temperature: 13.0
```

**Code:**
```python
def render_climate_payload(hass, payload):
    rendered = {}

    for key, value in payload.items():
        if is_template(value):  # Contains {{ }}
            try:
                template = Template(value, hass)
                rendered_value = template.async_render()

                # Convert to expected type
                if key in ["temperature", "target_temp_high", "target_temp_low"]:
                    rendered[key] = float(rendered_value)
                elif key == "humidity":
                    rendered[key] = int(rendered_value)
                else:
                    rendered[key] = rendered_value
            except Exception as err:
                _LOGGER.error(f"Template render failed for {key}: {err}")
                rendered[key] = None
        else:
            rendered[key] = value  # Static value

    return rendered
```

**Benefits:**
- Adapt to outdoor temperature sensors
- Use input helpers for user-adjustable targets
- Calculate relative temperatures (outdoor + offset)
- Dynamic humidity based on weather conditions
- Smooth transitions without multiple bindings

**Output:** Climate payload with all templates resolved to concrete values

---

#### Step 7: 🔄 Change Detection (Payload-Aware)

**What:** Compare rendered payload with previous to avoid redundant applications

**Why:** Reduce entity updates, cleaner history, less system load

**Logic:**

```python
# Track previous rendered payloads (not just binding IDs)
_previous_applied_payloads = {}

for entity_id, slot in resolved_entities.items():
    # Build current payload (default + overrides)
    current_payload = slot["default_climate_payload"].copy()
    if entity_id in slot["entity_overrides"]:
        current_payload.update(slot["entity_overrides"][entity_id])

    # Render templates in current payload
    rendered_current = render_climate_payload(hass, current_payload)

    # Compare with previous rendered payload
    prev_rendered = _previous_applied_payloads.get(entity_id)

    # Detect change
    if prev_rendered != rendered_current:
        # Apply to entity
        await apply_climate_payload(entity_id, rendered_current)

        # Update tracking
        _previous_applied_payloads[entity_id] = rendered_current
    else:
        # No change - skip application
        _LOGGER.debug(f"No change for {entity_id}, skipping")
```

**Example Scenario:**

```yaml
# First cycle (10:00:00)
Template: "{{ states('sensor.outdoor_temp')|float + 2 }}"
Rendered: 12.0 (outdoor = 10)
Action: APPLY (first time)

# Second cycle (10:01:00)
Template: "{{ states('sensor.outdoor_temp')|float + 2 }}"
Rendered: 12.0 (outdoor still 10)
Action: SKIP (no change)

# Third cycle (10:02:00)
Template: "{{ states('sensor.outdoor_temp')|float + 2 }}"
Rendered: 13.0 (outdoor changed to 11)
Action: APPLY (value changed)
```

**Output:** Decision to apply or skip for each entity

---

#### Step 8: 🎯 Entity Application

**What:** Apply climate settings to physical devices

**Services Used:**

```python
# Single temperature target
await hass.services.async_call(
    "climate",
    "set_temperature",
    {
        "entity_id": "climate.living",
        "temperature": 21.5,
        "hvac_mode": "heat",
    }
)

# Temperature range (heat_cool mode)
await hass.services.async_call(
    "climate",
    "set_temperature",
    {
        "entity_id": "climate.bedroom",
        "target_temp_high": 25,
        "target_temp_low": 22,
        "hvac_mode": "heat_cool",
    }
)

# Humidity
await hass.services.async_call(
    "climate",
    "set_humidity",
    {
        "entity_id": "climate.studio",
        "humidity": 60,
    }
)

# Other settings
await hass.services.async_call(
    "climate",
    "set_hvac_mode",
    {"entity_id": "climate.living", "hvac_mode": "heat"}
)
```

**Output:** Climate entities updated with new settings

---

### 🎯 Complete Example: Smart Heating with All Features

**Scenario:** Activate heating only if outdoor temp < 15°C, window closed, work hours, with dynamic indoor target.

**Configuration:**

```yaml
bindings:
  - id: smart_wfh_heating
    calendars: calendar.work
    match:
      type: summary_contains
      value: "WFH"
    conditions:
      # Only if cold outside
      - type: numeric_state
        entity_id: sensor.outdoor_temp
        below: 15
      # Only if window closed
      - type: state
        entity_id: binary_sensor.window_living
        state: 'off'
      # Only during work hours
      - type: time
        after: '08:00'
        before: '18:00'
        weekday: [mon, tue, wed, thu, fri]
    slot_id: dynamic_comfort
    priority: 10

slots:
  - id: dynamic_comfort
    label: "Dynamic Comfort"
    default_climate_payload:
      # Dynamic: outdoor temp + 5°C offset
      temperature: "{{ states('sensor.outdoor_temp')|float + 5 }}"
      hvac_mode: heat
      # Dynamic: higher humidity if dry outside
      humidity: "{{ 60 if states('sensor.outdoor_humidity')|int < 40 else 50 }}"
    entity_overrides:
      climate.studio:
        # Studio: outdoor temp + 7°C (warmer for working)
        temperature: "{{ states('sensor.outdoor_temp')|float + 7 }}"
```

**Execution Timeline:**

```
⏰ 08:00 - Calendar event "WFH Tuesday" starts
  ↓
📅 Event fetched: "WFH Tuesday" active
  ↓
🔗 Pattern match: "WFH" in "WFH Tuesday" ✅
  ↓
✅ Condition 1: outdoor_temp = 12°C (< 15) ✅
✅ Condition 2: window = 'off' ✅
✅ Condition 3: time = 08:00 (within 08:00-18:00) ✅
✅ Condition 4: weekday = Tuesday (in mon-fri) ✅
  ↓
⚡ Priority resolution: binding priority 10 (no conflicts)
  ↓
🎚️ Slot activated: "Dynamic Comfort"
  ↓
🌡️ Template rendering:
    climate.living:
      temperature: "{{ 12 + 5 }}" → 17.0°C
      humidity: "{{ 60 if 35 < 40 else 50 }}" → 60%
    climate.studio:
      temperature: "{{ 12 + 7 }}" → 19.0°C
      humidity: 60%
  ↓
🔄 Change detection: First time → APPLY
  ↓
🎯 Entity application:
    climate.living: 17°C, 60% humidity
    climate.studio: 19°C, 60% humidity

⏰ 10:00 - Outdoor temp rises to 14°C, humidity to 45%
  ↓
✅ All conditions still pass
  ↓
🌡️ Template re-render:
    climate.living: 19.0°C (14+5), 50% humidity (45 not < 40)
    climate.studio: 21.0°C (14+7), 50% humidity
  ↓
🔄 Change detection: Different from previous → APPLY
  ↓
🎯 Update entities with new values

⏰ 12:00 - Window opened
  ↓
✅ Condition 2 FAILS: window = 'on' ❌
  ↓
❌ Binding skipped (conditions not met)
  ↓
🏠 Entities keep last applied state (21°C / 19°C)
     (Use another binding with priority to revert, or wait for window close)

⏰ 12:15 - Window closed again
  ↓
✅ All conditions pass again ✅
  ↓
🌡️ Templates re-render with current outdoor temp
  ↓
🔄 Change detection determines if values changed
  ↓
🎯 Apply if different from current state

⏰ 18:00 - Event ends
  ↓
📅 No active events
  ↓
🏠 Entities remain in last state
     (Configure default binding or off-hours slot if needed)
```

**Key Takeaways:**
1. **Conditions filter when bindings activate** (not just pattern match)
2. **Templates make values dynamic** (adapt to sensors)
3. **Change detection prevents redundant updates** (only when values change)
4. **Priority handles conflicts** (highest wins)
5. **When conditions fail, state persists** (use multiple bindings for fallbacks)

---

## 🔄 Event-Driven Architecture Benefits

### ✅ Change Detection

The system **only applies climate changes when events start or end**, not every 60 seconds.

```
Old Way:
  ⏱️ 10:00:00 - Apply 21°C
  ⏱️ 10:01:00 - Apply 21°C (redundant!)
  ⏱️ 10:02:00 - Apply 21°C (redundant!)

New Way:
  ⏱️ 10:00:00 - Event starts → Apply 21°C ✅
  ⏱️ 10:01:00 - No change → Nothing
  ⏱️ 10:02:00 - No change → Nothing
  ⏱️ 12:00:00 - Event ends → Apply new settings ✅
```

**Benefits:**
- 🚀 Reduced entity state updates
- 🔋 Less system load
- 📊 Cleaner logbook/history
- 🔔 One notification per change (not spam)

---

### ✅ Active Event Fetching

The coordinator **actively fetches events** every 60 seconds using `calendar.get_events` service.

```
Old Way:
  Wait for HA to update calendar entity state → might be delayed

New Way:
  Every 60s: Fetch events from -1h to +24h → immediate detection
```

**Benefits:**
- ⚡ New events detected within 60 seconds
- 🔄 No need to restart integration
- 📱 Create event on phone → active in 1 minute
- 🎯 Reliable even with slow calendar syncs

---

### ✅ Multi-Event Simultaneous Handling

Multiple events can be active **at the same time** with smart conflict resolution.

```
Scenario:
  📅 Event A: "Base Heating" (priority 5) → all entities
  📅 Event B: "Studio Work" (priority 10) → climate.studio
  📅 Event C: "Guest Room" (priority 7) → climate.guest

Resolution:
  🏠 climate.living: Event A (priority 5, no conflict)
  🏠 climate.studio: Event B (priority 10, wins over A)
  🏠 climate.guest: Event C (priority 7, no conflict)
  🏠 climate.bedroom: Event A (priority 5, no conflict)
```

Each entity gets the highest-priority binding targeting it!

---

## 🎨 Visual Architecture

```mermaid
graph TB
    subgraph "📅 Calendar Layer"
        C1[Google Calendar]
        C2[Local Calendar]
        C3[Office 365]
    end

    subgraph "🔄 Integration Core"
        COORD[Coordinator<br/>Active Event Fetcher]
        ENGINE[Engine<br/>Binding Resolver]
    end

    subgraph "🔗 Configuration"
        B1[Binding 1<br/>Pattern: 'Work'<br/>Priority: 10]
        B2[Binding 2<br/>Pattern: 'Vacation'<br/>Priority: 5]
        B3[Binding 3<br/>Pattern: 'Emergency'<br/>Priority: 99]
    end

    subgraph "🎚️ Climate Profiles"
        S1[Slot: Comfort<br/>21°C heat]
        S2[Slot: Away<br/>15°C eco]
        S3[Slot: Max<br/>25°C boost]
    end

    subgraph "🌡️ Devices"
        E1[climate.studio]
        E2[climate.bedroom]
        E3[climate.living]
    end

    C1 --> COORD
    C2 --> COORD
    C3 --> COORD

    COORD -->|Active Events| ENGINE

    ENGINE -->|Match Pattern| B1
    ENGINE -->|Match Pattern| B2
    ENGINE -->|Match Pattern| B3

    B1 -->|Activate| S1
    B2 -->|Activate| S2
    B3 -->|Activate| S3

    S1 -->|Apply Settings| E1
    S1 -->|Apply Settings| E2
    S2 -->|Apply Settings| E3

    style C1 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px
    style C2 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px
    style C3 fill:#4CAF50,stroke:#2E7D32,stroke-width:2px
    style ENGINE fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style COORD fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
```

---

## 📊 Comparison: Old vs New

| Aspect | Time-Based (Old) | Event-Based (New) |
|--------|------------------|-------------------|
| **Schedule Changes** | Edit code/config | Create calendar event |
| **Exceptions** | Complex logic | Delete/move event |
| **Mobile Management** | ❌ Restart needed | ✅ Calendar app on phone |
| **Recurring Patterns** | Manual config | Native calendar recurrence |
| **Family Sharing** | ❌ Single admin | ✅ Shared calendar |
| **Conflicting Events** | ❌ Complex conditions | ✅ Automatic priority resolution |
| **Vacation Mode** | Disable integration | Create vacation event |
| **Emergency Override** | Manual climate adjustment | 10-second calendar event |
| **Multi-Zone** | Complex automations | Multiple bindings/calendars |

---

## 🎓 Summary: Why This Architecture?

### 🧠 **Separation of Concerns**

- **Calendars**: When things happen (your lifestyle)
- **Bindings**: What triggers what (pattern matching)
- **Slots**: How to configure climate (reusable profiles)
- **Priorities**: Who wins conflicts (explicit rules)

### 🔧 **Flexibility**

- Change schedules without restarting HA
- Mix recurring, one-off, and exceptional events
- Override anything with higher-priority events
- Control entities globally or per-binding

### 🚀 **Power**

- Multiple calendars for different purposes
- Complex scenarios with simple configuration
- Real-time responsiveness to calendar changes
- Family-friendly (everyone uses calendar apps)

### 💡 **Simplicity**

- Non-technical users manage via calendar
- Technical users configure bindings once
- Pattern matching instead of complex conditions
- Priority system handles conflicts automatically

---

## 📚 Next Steps

- **[README.md](README.md)**: Installation and quick start
- **[Examples Documentation](docs/)**: Detailed configuration examples
- **[GitHub Discussions](https://github.com/max433/climate_control_calendar/discussions)**: Ask questions and share setups

---

**Built with ❤️ for smart home enthusiasts who want flexibility without complexity.**
