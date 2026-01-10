# Architectural Decisions

This document tracks all significant architectural and design decisions made during the development of Climate Control Calendar.

## Format

Each decision is documented with:
- **Date**: When the decision was made
- **Context**: What prompted the decision
- **Decision**: What was decided
- **Rationale**: Why this choice was made
- **Alternatives Considered**: Other options that were evaluated
- **Status**: Current (Active, Superseded, Deprecated)

---

## Decision Log

### D001: Storage Strategy - ConfigEntry.data + ConfigEntry.options

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Need to decide how to persist integration configuration (calendar selection, dry run toggle, slots, device assignments).

**Decision**: Use hybrid approach:
- `ConfigEntry.data` for immutable initial choices (calendar entity, dry run toggle, debug mode)
- `ConfigEntry.options` for dynamic configuration (climate entities, slots, override flags)

**Rationale**:
- `options` support modification without integration reload via Options Flow
- Separates static setup from dynamic runtime configuration
- Standard pattern in Home Assistant ecosystem
- Better UX for users modifying slots frequently

**Alternatives Considered**:
1. Only `ConfigEntry.data` - Requires full reload for any change
2. Only `ConfigEntry.options` - Less clear separation of concerns
3. External storage (JSON files) - Non-standard, harder to manage

---

### D002: Slot ID Generation - SHA256 Truncated to 12 Characters

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Need stable, unique identifiers for time slots that persist across edits and reordering.

**Decision**: Generate slot IDs using SHA256 hash of `{label}_{timestamp}`, truncated to first 12 hexadecimal characters.

**Example**: `"morning_comfort_1704902400.0"` → `a3f5c8d2e1b4`

**Rationale**:
- **Stable**: Same label + timestamp always produces same ID
- **Unique**: 48-bit entropy prevents collisions (281 trillion combinations)
- **Compact**: 12 chars more readable in logs than full UUID (36 chars)
- **Deterministic**: Reproducible for testing
- **Collision-resistant**: Timestamp component ensures uniqueness even with identical labels

**Alternatives Considered**:
1. UUID v4 - More verbose, less readable, but also valid
2. Sequential integers - Break on reordering, not stable
3. Label as ID - Not unique, breaks with duplicates
4. 16-char truncation - Longer but overkill for our use case

---

### D003: Calendar Monitoring - DataUpdateCoordinator with Polling

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Need to monitor calendar entity state changes to trigger slot evaluation.

**Decision**: Implement `DataUpdateCoordinator` that polls calendar entity every 60 seconds (configurable).

**Rationale**:
- **Standard Pattern**: Home Assistant's recommended approach for integrations
- **Built-in Features**: Automatic error handling, retry logic, debouncing
- **Efficiency**: Built-in caching prevents unnecessary updates
- **Reliability**: More robust than pure event listeners under load
- **Predictable**: Consistent update cadence easier to debug

**Alternatives Considered**:
1. Event listener on `state_changed` - More reactive but can miss events under load
2. Manual polling loop - Reinventing the wheel, error-prone
3. Hybrid (coordinator + event listener) - Overkill for current needs, can revisit in M3

**Update Interval**: Default 60s, may be adjusted based on testing in M2/M3.

---

### D004: Initial Language Support - English Only

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Decide which languages to support in initial release.

**Decision**: Start with English (EN) only. Italian (IT) will be added in Milestone 4.

**Rationale**:
- **Faster Development**: Single language reduces translation overhead during rapid iteration
- **Structure Ready**: Translation framework in place, adding languages is straightforward
- **User Testing**: Easier to gather English-speaking user feedback first
- **M4 Focus**: UX polish phase (M4) is appropriate time for localization

**Alternatives Considered**:
1. EN + IT from start - Doubles maintenance during development
2. Only IT (native language) - Limits international adoption
3. Multi-language from start - Premature optimization

**Future Plan**: Add IT translations in M4, community contributions for other languages welcome.

---

### D005: Testing Strategy - End-of-Milestone

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Decide when to write unit/integration tests.

**Decision**: Write comprehensive tests at the end of each milestone, not during development.

**Rationale**:
- **Stable Code**: Test against stabilized features after milestone completion
- **Less Churn**: Avoid rewriting tests for rapidly changing code
- **Focus**: Developers can focus on implementation, then validation
- **Critical Coverage**: Engine and slot resolution (M2) will have priority test coverage

**Scope per Milestone**:
- **M1**: Config flow validation, helpers, coordinator basic tests
- **M2**: Comprehensive engine tests, slot resolution, dry run verification
- **M3**: Device application tests, flag behavior tests
- **M4**: Integration tests, edge cases, performance tests

**Alternatives Considered**:
1. TDD (test-first) - Slows rapid prototyping in exploratory phase
2. No tests until M4 - Too risky, critical bugs could slip through
3. Continuous testing - Best practice but slower for R&D phase

---

### D006: Config Flow Structure - Three-Step Wizard

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Design the initial setup flow for users adding the integration.

**Decision**: Implement three-step wizard:
1. **Calendar Selection**: Choose calendar entity from dropdown
2. **Climate Entities**: Multi-select climate devices (optional)
3. **Options**: Configure dry run and debug toggles

**Rationale**:
- **Progressive Disclosure**: Breaks complex setup into manageable chunks
- **Validation**: Each step validates before proceeding
- **Flexibility**: Climate entities optional (can be added later via Options Flow)
- **Clear Purpose**: Each step has single, focused task

**Options Flow**: Allows post-setup modification of climate entities and operational flags without reload.

**Alternatives Considered**:
1. Single-step form - Overwhelming, poor UX for complex config
2. Two-step (calendar + everything else) - Less structured
3. Four+ steps - Over-engineered for current needs

---

### D007: Dry Run as Default

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Decide default value for dry run mode.

**Decision**: Dry run defaults to `True` (enabled).

**Rationale**:
- **Safety First**: Prevents accidental climate changes on first install
- **Testing Encouragement**: Forces users to validate configuration before going live
- **Explicit Opt-In**: User must consciously disable dry run to affect devices
- **Logging**: All dry run actions logged, helping users understand behavior

**Alternatives Considered**:
1. Default `False` (active mode) - Too risky for new users
2. Forced dry run for first 24h - Overly restrictive
3. Dry run per-device - Too granular for initial implementation

**Future**: May add per-slot dry run override in M3.

---

### D008: Event-First Design

**Date**: 2026-01-10
**Milestone**: M1 (foundation), M2 (implementation)
**Status**: Active

**Context**: How should the integration communicate state changes and actions?

**Decision**: Emit Home Assistant events for all significant actions:
- `climate_control_calendar_calendar_changed`
- `climate_control_calendar_slot_activated`
- `climate_control_calendar_slot_deactivated`
- `climate_control_calendar_climate_applied`
- `climate_control_calendar_climate_skipped`
- `climate_control_calendar_dry_run_executed`
- `climate_control_calendar_flag_set`
- `climate_control_calendar_flag_cleared`

**Rationale**:
- **Automation Freedom**: Users can trigger any action on these events
- **Observability**: Events provide audit trail of all actions
- **Extensibility**: Third-party integrations can react to events
- **Better than Notifications**: Events more flexible than persistent notifications

**Event Payload Structure**: All events include timestamp, entry_id, and context-specific data.

**Alternatives Considered**:
1. Only logging - Not user-accessible for automations
2. Persistent notifications - Clutters UI, less flexible
3. Attributes on entities - Limited, not time-series

---

### D009: No YAML Configuration

**Date**: 2026-01-10
**Milestone**: M1
**Status**: Active

**Context**: Support YAML configuration alongside GUI?

**Decision**: **No YAML support**. GUI-only configuration via Config Flow and Options Flow.

**Rationale**:
- **User Experience**: GUI more accessible to non-technical users
- **Validation**: UI enforces correct data types and formats
- **Modern Standard**: HACS integrations moving toward GUI-first
- **Maintainability**: Single configuration path easier to maintain
- **Visual Slot Editing**: Complex slot configuration better suited to UI (future M3)

**Alternatives Considered**:
1. YAML + GUI - Maintenance burden, potential conflicts
2. YAML only - Poor UX, high error rate
3. YAML for advanced users - Fragmentation, support burden

**Exception**: Services can be called via YAML automations (intentional).

---

### D010: Slot & Calendar Interaction Logic

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: Define when time slots should be active in relation to calendar state.

**Decision**: Slots are active **only when calendar is ON** and current time matches slot time window.

**Logic**:
```
IF calendar_state == "on" AND current_time in slot_window:
    slot is active
ELSE:
    slot is inactive
```

**Rationale**:
- **Intuitive**: Calendar ON = "this pattern is active now"
- **Clear Semantics**: Slots represent behaviors for when calendar pattern is active
- **No Ambiguity**: Calendar OFF = nothing happens, regardless of time
- **Use Case Alignment**: "Smart Working calendar active → apply work-from-home slots"

**Alternatives Considered**:
1. Slots independent of calendar state - Calendar becomes meaningless switch
2. Configurable per slot - Unnecessary complexity for M2

---

### D011: Overlapping Slots Prevention

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: Handle situation where multiple slots have overlapping time windows.

**Decision**: **Prevent overlapping slots** via validation in config flow. Reject slot creation/edit if it overlaps with existing slot.

**Overlap Definition**: Two slots overlap if they share any time window on the same day(s).

**Example (REJECTED)**:
- Slot A: Mon-Fri 06:00-09:00
- Slot B: Mon-Fri 08:00-12:00
- Overlap: Mon-Fri 08:00-09:00 ❌

**Rationale**:
- **No Ambiguity**: User always knows which slot applies
- **Simpler Engine**: No priority resolution logic needed
- **Clear Feedback**: Validation error guides user to fix config
- **Predictable**: No hidden priority rules to learn

**Alternatives Considered**:
1. First defined wins - Order-dependent, fragile
2. Last defined wins - Confusing for users
3. Most specific wins - Complex to implement and explain
4. Allow with warning - Doesn't solve ambiguity

**Implementation**: `validate_slot_overlap()` in helpers.py checks all existing slots before accepting new/modified slot.

---

### D012: Climate Payload Structure - All Optional

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: Define required vs. optional fields in climate payload configuration.

**Decision**: **All fields optional**, at least one must be present.

**Supported Fields**:
- `temperature`: Target temperature (float)
- `hvac_mode`: heat, cool, heat_cool, auto, off, dry, fan_only
- `preset_mode`: away, home, eco, comfort, sleep, activity (device-specific)
- `fan_mode`: auto, low, medium, high (device-specific)
- `swing_mode`: on, off, vertical, horizontal (device-specific)

**Valid Payloads**:
```json
{"temperature": 22.0}
{"hvac_mode": "off"}
{"temperature": 20.0, "hvac_mode": "heat", "preset_mode": "eco"}
```

**Invalid Payload**:
```json
{}  // At least one field required
```

**Rationale**:
- **Flexibility**: Support diverse use cases (temp-only, mode-only, combined)
- **Device Compatibility**: Not all devices support all features
- **User Control**: User decides what to control
- **Use Cases**: Night mode might only set "off", morning might set temp+mode

**Validation**: Config flow validates at least one field present.

---

### D013: Slot Days of Week - Default All Days

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: What days should a slot apply to if user doesn't specify?

**Decision**: **All days (Mon-Sun)** if not explicitly configured.

**Behavior**:
```python
slot_days = user_input.get("days", ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])
```

**Rationale**:
- **Simplicity**: Most common case is "apply every day"
- **Progressive Enhancement**: User can refine later
- **Less Friction**: New users can create basic slot without day selection
- **Explicit Override**: User can narrow to specific days if needed

**Alternatives Considered**:
1. No days default - Forces selection, annoying for simple cases
2. Weekdays default - Too opinionated, not universal
3. Current day only - Too narrow, poor default

---

### D014: Engine Trigger Strategy

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: When should the slot evaluation engine execute?

**Decision**: **Engine runs on every coordinator update** (every 60 seconds).

**Trigger Events**:
1. Coordinator update tick (every 60s) → evaluate slots
2. Calendar state change → coordinator updates → evaluate slots

**Slot Activation Latency**: Maximum 60 seconds from slot time boundary.

**Example**:
- Slot "Morning" starts at 06:00:00
- Coordinator next tick: 06:00:47
- Slot activates at 06:00:47 (47s delay)

**Rationale**:
- **Simplicity**: Reuse existing coordinator infrastructure
- **Acceptable Latency**: 60s delay acceptable for climate control
- **Reliability**: Single update mechanism, no race conditions
- **Resource Efficient**: No additional timers/schedulers

**Alternatives Considered**:
1. Only on calendar state change - Misses time-based slot transitions
2. Every minute (separate scheduler) - Additional complexity, marginal improvement
3. Event-based on time boundaries - Over-engineered for climate control

**Future Optimization**: Can reduce to 30s if user feedback indicates 60s too slow.

---

### D015: Event Deduplication

**Date**: 2026-01-10
**Milestone**: M2
**Status**: Active

**Context**: Prevent event spam when slot remains active across multiple engine evaluations.

**Decision**: **Emit events only on state transitions**, not on every evaluation.

**Implementation**:
- Track last active slot ID
- Emit `slot_activated` only when slot ID changes from previous
- Emit `slot_deactivated` when active slot becomes None
- Emit `climate_applied` only when actually applying new payload

**Example (60s evaluations)**:
```
06:00:00 → Slot A activates → emit slot_activated
06:01:00 → Slot A still active → NO EVENT
06:02:00 → Slot A still active → NO EVENT
...
09:00:00 → Slot A deactivates → emit slot_deactivated
```

**Rationale**:
- **Meaningful Events**: Each event represents actual state change
- **Automation-Friendly**: No spam, automations trigger only on real changes
- **Log Clarity**: Logs show transitions, not redundant checks
- **Performance**: Fewer events = less processing

**Alternatives Considered**:
1. Emit on every evaluation - Spams logs and event bus
2. Throttle events (max 1/minute) - Still redundant, arbitrary limit

---

## Future Decisions

The following areas require decisions in upcoming milestones:

### M3 Decisions Needed
- Override flag persistence across restarts
- Skip logic priority (multiple flags active)
- Device application strategy (sequential vs. parallel)

### M4 Decisions Needed
- Diagnostic data collection
- Performance optimization targets
- Backward compatibility policy for v1.0

---

**Last Updated**: 2026-01-10 (M2 decisions added)
**Next Review**: End of Milestone 3
