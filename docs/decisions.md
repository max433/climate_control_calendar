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

### D016: Device Application Strategy - Sequential

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: When applying climate payload to multiple devices, should we process sequentially or in parallel?

**Decision**: **Sequential application** - Apply to one device at a time.

**Implementation**:
```python
for entity_id in climate_entities:
    await apply_payload_to_device(entity_id, payload)
```

**Rationale**:
- **Simplicity**: Easier to implement and debug
- **Error Isolation**: Each device's success/failure is independent and clear
- **Predictable Logging**: Clear sequential log of what happened
- **Acceptable Performance**: Climate control doesn't require sub-second updates

**Alternatives Considered**:
1. Parallel application - Faster but more complex error handling
2. Parallel with chunking - Unnecessary complexity for climate use case

**Performance**: For 5 devices × 2 service calls each, sequential adds ~500ms total. Acceptable for climate control.

---

### D017: Error Handling - Continue with Immediate Retry

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: When one device fails during payload application, how to handle?

**Decision**: **Continue on error with immediate retry** before marking as failed.

**Retry Logic**:
1. Attempt to apply payload
2. If fails: wait 1 second, retry once
3. If still fails: log error, emit failure event, continue to next device
4. At end: report partial success (X of Y devices succeeded)

**Rationale**:
- **Resilience**: Transient errors (momentary unavailability) can succeed on retry
- **Better Than Nothing**: Applying to 4/5 devices better than 0/5
- **User Awareness**: Events show which devices failed
- **Not Aggressive**: Only 1 retry avoids hammering unavailable devices

**Alternatives Considered**:
1. Stop on first error - Too fragile, all-or-nothing
2. Multiple retries - Overkill, delays other devices
3. No retry - Gives up too easily on transient errors

---

### D018: Override Flag Persistence - HA Storage

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: Should override flags persist across Home Assistant restarts?

**Decision**: **Use HA Storage** for flag persistence.

**Implementation**:
- Use `Store` helper from `homeassistant.helpers.storage`
- Storage key: `climate_control_calendar_{entry_id}_flags`
- Version: 1

**Rationale**:
- **Correct Pattern**: Storage designed for runtime state
- **Persistence**: Flags survive restarts (important for user expectations)
- **Separation**: Keeps runtime state separate from configuration (options)
- **Migration Support**: Store versioning allows future schema changes

**Alternatives Considered**:
1. In-memory only - Lost on restart, poor UX
2. ConfigEntry.options - Confuses configuration with runtime state
3. Custom JSON files - Reinventing the wheel

---

### D019: Override Flag Priority - Mutual Exclusion

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: What happens if user sets multiple override flags?

**Decision**: **Mutual exclusion** - Setting a new flag automatically clears any existing flag.

**Behavior**:
```
Active: skip_today
User sets: force_slot "evening"
Result: skip_today cleared, force_slot "evening" active
```

**Rationale**:
- **No Ambiguity**: Always exactly 0 or 1 flag active
- **Predictable**: User knows which flag is in effect
- **Simple Logic**: No priority resolution needed
- **Clear UI**: One active flag to display

**Alternatives Considered**:
1. Priority hierarchy - More complex, harder to understand
2. Allow multiple - Conflicting flags, confusing behavior

---

### D020: Override Flag Expiration - Smart Auto-Clear

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: Should flags automatically clear or require manual clearing?

**Decision**: **Semantic auto-clear** based on flag type:

| Flag | Expiration | Rationale |
|------|------------|-----------|
| `skip_today` | Auto-clear at midnight (00:00) | "Today" ends at midnight |
| `skip_until_next_slot` | Auto-clear when next slot activates | Semantic meaning: skip current, not next |
| `force_slot` | Manual clear only | User controls when to stop forcing |

**Implementation**:
- Engine checks flag expiration on each evaluation
- Expired flags auto-cleared before slot resolution
- Event emitted: `flag_cleared` with reason "expired"

**Rationale**:
- **Semantic Correctness**: Expiration matches flag meaning
- **User Expectations**: "Skip today" should not affect tomorrow
- **Flexibility**: Force slot gives user full control

**Alternatives Considered**:
1. All manual - skip_today staying active tomorrow is confusing
2. All auto-clear - Force slot should be user-controlled

---

### D021: Service Call Validation - Strict

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: How to validate service call parameters?

**Decision**: **Strict validation** at service call time.

**Rules**:
- `set_flag` with `flag_type: force_slot` **requires** `slot_id` parameter
- `set_flag` with `flag_type: skip_*` **ignores** `slot_id` if provided
- Missing required parameters → Service call error (not silent failure)

**Example**:
```yaml
# Valid
service: climate_control_calendar.set_flag
data:
  flag_type: force_slot
  slot_id: a3f5c8d2e1b4

# Invalid - raises error
service: climate_control_calendar.set_flag
data:
  flag_type: force_slot
  # Missing slot_id
```

**Rationale**:
- **Immediate Feedback**: User knows instantly if call is wrong
- **Better UX**: Error message guides correction
- **Type Safety**: Prevents runtime surprises

**Alternatives Considered**:
1. Lenient validation - Runtime errors harder to debug

---

### D022: Slot UI Management - Deferred to M4

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: Should M3 implement slot management UI?

**Decision**: **Defer to M4** - Focus M3 on device application and flags.

**M3 Workaround**: Slots managed via Developer Tools (Services) or direct options edit.

**Rationale**:
- **Priority**: Device control functionality more critical than UI polish
- **M4 Focus**: M4 is designated for UX improvements
- **Complexity**: Slot UI requires multi-step form, validation feedback, day selection widgets
- **Timeline**: Keeps M3 focused and achievable

**M4 Scope**: Full slot CRUD UI with visual time picker, day selection, overlap validation feedback.

---

### D023: Services and Dry Run Mode - Services Override

**Date**: 2026-01-10
**Milestone**: M3
**Status**: Active

**Context**: Should service calls respect dry run mode?

**Decision**: **Services ignore dry run** - Manual actions always execute.

**Behavior**:
```
Integration: dry_run = true
User calls: climate_control_calendar.force_slot
Result: Slot actually forced (dry run bypassed for this manual action)
```

**Rationale**:
- **User Intent**: Service call is explicit manual override
- **Testing**: Users can test manual controls even during dry run phase
- **Separation**: Dry run applies to automatic behavior, not manual commands
- **Escape Hatch**: Provides way to force action when needed

**Alternatives Considered**:
1. Services respect dry run - User has no way to manually control during testing

**Exception**: Dry run flag itself doesn't affect service call validation, only automatic slot application.

---

### D024: Slot UI Management - Documentation Workaround for v1.0

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: Building a full GUI for slot management (CRUD operations with time pickers, day selection, overlap validation) is complex and time-consuming.

**Decision**: **Skip slot UI for v1.0**. Provide documentation workaround using Developer Tools → Services or direct ConfigEntry.options editing.

**Workaround**:
- Users can manually edit slots via Developer Tools
- Documentation includes step-by-step examples
- Future v2.0 can add dedicated UI once core functionality proven

**Rationale**:
- **Time to Market**: v1.0 focuses on core climate control functionality
- **Technical Users First**: Early adopters comfortable with workarounds
- **Proven Demand**: Build UI after validating user demand
- **Complexity vs Value**: Complex multi-step form better deferred to v2.0

**Alternatives Considered**:
1. Full slot CRUD UI - Delays v1.0 release significantly
2. Basic single-slot form - Half-measure, still complex
3. YAML configuration - Goes against D009 (GUI-first)

**Future**: v2.0 will include visual slot editor with drag-and-drop time ranges.

---

### D025: Italian Translations - Scope for v1.0

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: Which parts of the integration need Italian translations?

**Decision**: Translate **config flow and services only** for v1.0.

**Scope**:
- ✅ Config flow steps (calendar selection, climate entities, options)
- ✅ Service names and descriptions
- ✅ Error messages shown in UI
- ❌ README (remains English only for international audience)
- ❌ Documentation files (English preferred for technical docs)
- ❌ Code comments (English standard)

**Implementation**: Create `translations/it.json` mirroring structure of `translations/en.json`.

**Rationale**:
- **User-Facing First**: UI strings most important for Italian users
- **International Docs**: README in English reaches broader audience
- **Standard Practice**: Most HACS integrations keep docs in English

**Alternatives Considered**:
1. Full Italian docs - Maintenance burden, fragments community
2. No Italian translations - Poor UX for native language users

---

### D026: Testing Priority - Unit Tests for Critical Paths

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: Comprehensive test coverage ideal but time-consuming. Prioritize most critical code.

**Decision**: Write unit tests for **critical business logic only** in v1.0.

**Test Priorities**:
1. **helpers.py**: Slot ID generation, overlap detection, payload validation
2. **flag_manager.py**: Expiration logic, mutual exclusion, persistence
3. **engine.py**: Slot resolution, flag integration, edge cases (overnight slots)

**Not Tested in v1.0**:
- Coordinator (HA framework well-tested)
- Config flow (manual testing sufficient)
- Event emitter (thin wrapper around HA event bus)

**Coverage Target**: ~60-70% for critical modules (not 100%).

**Rationale**:
- **Risk-Based**: Test where bugs have highest impact
- **Pragmatic**: Balance quality with release timeline
- **Incremental**: Add more tests in v1.1+ based on bug reports

**Alternatives Considered**:
1. 100% coverage - Unrealistic timeline, diminishing returns
2. No tests - Too risky for v1.0 release
3. Integration tests only - Miss unit-level edge cases

---

### D027: Documentation Level - Quick Start Focus

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: How comprehensive should v1.0 documentation be?

**Decision**: **Quick start focused** with three docs:

1. **README.md**: Installation, prerequisites, 3-4 usage scenarios, quick start
2. **docs/debugging.md**: Troubleshooting guide (logs, common errors, dry run)
3. **docs/api-reference.md**: Events and services reference (automation examples)

**Not Included in v1.0**:
- Advanced configuration guide (deferred to wiki/blog posts)
- Architecture deep-dive (decisions.md sufficient)
- Video tutorials (community-driven)

**Rationale**:
- **Get Started Fast**: New users need quick wins
- **Common Use Cases**: Cover 80% of scenarios
- **Self-Service**: Debugging guide reduces support burden
- **Automation Examples**: API reference enables power users

**Alternatives Considered**:
1. Minimal README only - Insufficient for new users
2. Comprehensive docs - Premature, preferences unclear until user feedback

---

### D028: Diagnostics - Rely on Existing Observability

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: Should we implement dedicated diagnostics download feature?

**Decision**: **Skip dedicated diagnostics** for v1.0. Existing logging and events sufficient.

**Observability Tools**:
- **Logs**: Detailed logging at INFO (dry run, slot changes) and DEBUG (engine internals)
- **Events**: All state changes emit events (automation debugging)
- **Developer Tools**: States show current slot, flags, last update time

**Rationale**:
- **Sufficient Coverage**: Logs + events provide complete audit trail
- **Standard Tools**: Users already know HA logs and Developer Tools
- **Complexity**: Diagnostics feature requires UI, data collection, privacy handling
- **YAGNI**: No user demand proven yet

**Future**: If support requests show need, add in v1.1+.

**Alternatives Considered**:
1. Full diagnostics download - Overengineering for v1.0
2. Minimal system info dump - Still requires UI, limited value

---

### D029: Version Number - v1.0.0 Release Strategy

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: What version number for end of M4?

**Decision**: **v1.0.0** - First stable release.

**Rationale**:
- **Feature Complete**: All core functionality implemented (M1-M4)
- **Tested**: Critical paths have unit tests
- **Documented**: README, debugging guide, API reference complete
- **Signal Stability**: v1.0 communicates production-ready to users
- **Semantic Versioning**: Commit to backward compatibility from this point

**Pre-Release Approach**: No beta/RC versions for v1.0 (user cannot test currently).

**Alternatives Considered**:
1. v0.1.0 (cautious) - Undersells completeness
2. v1.0.0-beta - No testing infrastructure, adds confusion

---

### D030: README Examples - Scenario-Based Approach

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: What examples should README include?

**Decision**: **3-4 real-world scenarios** with calendar + slot configurations.

**Scenarios**:
1. **Smart Working**: Home office days with differentiated slots
2. **Vacation Mode**: Away calendar turns off heating except morning/evening
3. **Weekend/Weekday**: Different comfort profiles
4. **Night Setback**: Automated temperature reduction overnight

**Format**: Each scenario shows:
- Use case description
- Calendar event configuration
- Example slots with time windows
- Expected climate behavior

**Rationale**:
- **Relatable**: Users see themselves in scenarios
- **Copy-Paste Ready**: Examples provide starting templates
- **Cover Common Cases**: 4 scenarios address majority of use cases
- **Visual Learning**: Easier than abstract documentation

**Alternatives Considered**:
1. Single generic example - Too abstract
2. 10+ scenarios - Overwhelming, dilutes focus

---

### D031: Breaking Changes Policy - Semantic Versioning

**Date**: 2026-01-10
**Milestone**: M4
**Status**: Active

**Context**: How to handle future breaking changes post-v1.0?

**Decision**: **Strict semantic versioning** compliance.

**Policy**:
- **Major version (2.0.0)**: Breaking changes allowed (storage schema, API changes)
- **Minor version (1.1.0)**: New features, backward compatible
- **Patch version (1.0.1)**: Bug fixes only, no new features

**Stability Promise**:
- ConfigEntry.data schema frozen for 1.x series
- ConfigEntry.options schema can extend (new optional fields) but not break
- Event payload structure frozen (can add fields, not remove)
- Service signatures frozen (can add optional params, not change required)

**Rationale**:
- **User Trust**: Predictable upgrades, no surprise breakage
- **Standard Practice**: Semantic versioning widely understood
- **Migration Path**: Major versions allow clean breaks when needed

**Alternatives Considered**:
1. "Move fast, break things" - Erodes user trust
2. Freeze forever - Prevents necessary evolution

---

### D032: Event-to-Slot Binding System

**Date**: 2026-01-15
**Milestone**: Post-v1.0 Refactoring
**Status**: Active

**Context**: Original implementation used time-based slot matching (slot has time_start/time_end). This created tight coupling between calendar events and time windows, limiting flexibility.

**Decision**: **Refactor to event-to-slot binding system** where calendar events are matched to slots via configurable patterns (summary, description, category).

**Architecture**:
- **Bindings**: Map calendar events → slots via pattern matching
- **Slots**: Reusable climate profiles (no time windows)
- **Engine**: Resolves active events → bindings → slots → applies to entities

**Rationale**:
- **Flexibility**: Same slot can be triggered by different events
- **Reusability**: Slots are templates, not tied to specific times
- **Event-Driven**: True reactive architecture, not time-polling hybrid
- **Multi-Calendar**: Natural support for multiple calendars

**Alternatives Considered**:
1. Keep time-based slots - Less flexible, calendar becomes just on/off switch
2. Hybrid approach - Unnecessary complexity

---

### D033: Multi-Calendar Support

**Date**: 2026-01-15
**Milestone**: Post-v1.0 Refactoring
**Status**: Active

**Context**: Original implementation monitored single calendar entity. Users requested support for multiple calendars (e.g., work calendar + vacation calendar).

**Decision**: **Support multiple calendar entities** with priority-based conflict resolution.

**Implementation**:
- `CONF_CALENDAR_ENTITIES` (list) replaces `CONF_CALENDAR_ENTITY` (string)
- `MultiCalendarCoordinator` monitors all calendars simultaneously
- Each calendar can have priority configured
- Bindings can target specific calendars or wildcard "*"

**Rationale**:
- **Real-World Use Case**: Users have multiple calendar sources
- **Priority Resolution**: Higher priority calendar wins conflicts
- **Backward Compatible**: Single calendar works as before

**Alternatives Considered**:
1. Separate integration instances - Poor UX, duplicate config
2. Calendar groups - HA doesn't support this natively

---

### D034: Slots as Reusable Templates

**Date**: 2026-01-15
**Milestone**: Post-v1.0 Refactoring
**Status**: Active

**Context**: After D032 (event-to-slot bindings), slots no longer need time_start/time_end fields.

**Decision**: **Slots are pure climate templates** without temporal information.

**Slot Structure**:
```json
{
  "id": "a3f5c8d2e1b4",
  "label": "comfort_mode",
  "default_climate_payload": {
    "temperature": 22.0,
    "hvac_mode": "heat"
  },
  "entity_overrides": {},
  "excluded_entities": []
}
```

**Rationale**:
- **Separation of Concerns**: Bindings handle "when", slots handle "what"
- **Reusability**: Same slot can be used by multiple bindings
- **Cleaner Data Model**: No redundant temporal data

**Alternatives Considered**:
1. Keep time fields as optional - Confusing, invites misuse
2. Rename to "profiles" - Slot terminology already established

---

### D035: Removal of Override Flags and Manual Control Services

**Date**: 2026-01-16
**Milestone**: Post-v1.0 Architecture Cleanup
**Status**: Active

**Context**: After event-driven refactoring (D032), override flags (skip_today, force_slot, skip_until_next_slot) and their associated services contradict the integration's core philosophy: "control climate via calendar events".

**Problem Identified**:
- **Architectural Inconsistency**: Flags create "parallel control path" bypassing event-driven logic
- **Hidden State**: Flag state stored internally, not visible in HA UI
- **Legacy Code**: Flags introduced in M3 (pre-event-driven refactoring)
- **Philosophy Violation**: "Use calendar events for control" ← → "But here are services to ignore calendar"

**Decision**: **Remove flag system entirely** - Eliminate FlagManager, flag storage, and manual override services.

**Services Removed**:
- `climate_control_calendar.set_flag`
- `climate_control_calendar.clear_flag`
- `climate_control_calendar.force_slot`
- `climate_control_calendar.refresh_now` (only used by flag services)

**Events Removed**:
- `climate_control_calendar_flag_set`
- `climate_control_calendar_flag_cleared`
- `climate_control_calendar_climate_skipped` (only emitted when flag active)

**Services Retained**:
- `add_slot` / `remove_slot` - Configuration management
- `add_binding` / `remove_binding` - Configuration management
- `list_bindings` - Diagnostics

**Alternative Approach for Manual Override**:
Users can achieve same functionality using native HA features:
- **Skip today**: Temporarily disable calendar entity
- **Force slot**: Create temporary calendar event with automation
- **Skip specific entities**: Use `excluded_entities` in slot config

**Rationale**:
- **Architectural Purity**: Truly event-driven, no parallel control paths
- **Simplicity**: ~500 lines of code removed (flag_manager.py + service handlers)
- **Visibility**: All state visible in HA UI (calendar entities, events)
- **Native Integration**: Uses standard HA patterns (entities, automations)
- **Maintainability**: Less state = fewer bugs

**Impact**:
- ✅ Core functionality unchanged (calendar → bindings → slots → climate)
- ✅ Event system intact (all observability events retained)
- ✅ Configuration services retained (slot/binding management)
- ❌ Users lose quick manual override (acceptable trade-off for cleaner architecture)

**Alternatives Considered**:
1. Keep flags but make visible as entities - Still parallel control path
2. Keep only force_slot - Half-measure, doesn't solve architecture issue
3. Add calendar entity automation examples - Chosen approach

**Migration Path**: No breaking changes for users who don't use flag services (majority).

---

### D036: Template Support for Dynamic Climate Values

**Date**: 2026-01-25
**Milestone**: Post-v1.0 (Web UI Enhancement)
**Status**: Active

**Context**: Static climate values (temperature: 21.0) are inflexible. Users want climate to adapt to real-time conditions like outdoor temperature, user preferences via input helpers, or time-based calculations.

**Decision**: **Support Jinja2 templates** in climate payload fields (temperature, target_temp_high, target_temp_low, humidity).

**Implementation**:
- Add `template_helper.py` with template detection and rendering functions
- Detect templates by `{{ }}` markers in string values
- Render templates every 60 seconds during engine evaluation
- Type conversion ensures correct data types (float for temps, int for humidity)
- Change detection compares rendered values to trigger re-application
- Web UI accepts both numeric and template values in text inputs

**Example**:
```json
{
  "temperature": "{{ states('sensor.outdoor_temp') | float + 2 }}",
  "humidity": "{{ 60 if states('sensor.outdoor_humidity') | int > 70 else 50 }}"
}
```

**Rationale**:
- **Adaptability**: Climate responds to real-time sensor data
- **User Control**: Non-technical users adjust via input_number helpers
- **Energy Efficiency**: Dynamic setbacks based on occupancy/weather
- **Standard Tech**: Jinja2 already used throughout Home Assistant

**Error Handling**:
- Invalid syntax → Fallback to original value, log error
- Render failure → Keep last known value, emit warning
- Type conversion failure → Use fallback value

**Alternatives Considered**:
1. Static values only - Too inflexible for advanced users
2. Custom expression language - Reinventing the wheel
3. Automation-based workarounds - Poor UX, complex setup

---

### D037: Condition System for Smart Binding Activation

**Date**: 2026-01-25
**Milestone**: Post-v1.0 (Web UI Enhancement)
**Status**: Active

**Context**: Calendar event matching alone isn't always sufficient. Users want bindings to activate only when additional criteria are met (e.g., "only heat if outdoor temp < 15°C and window closed").

**Decision**: **Support optional conditions on bindings** with 4 condition types: state, numeric_state, time, template.

**Implementation**:
- Add `condition_validator.py` for validation and evaluation
- Use Home Assistant's native `condition.async_from_config()` for evaluation
- Conditions evaluated every 60 seconds (same as templates)
- ALL conditions must pass (AND logic) for binding to activate
- Web UI provides visual condition builder with type-specific forms

**Supported Types**:
1. **State**: Check if entity equals specific state
2. **Numeric State**: Compare numeric value with above/below thresholds
3. **Time**: Time range (after/before) + weekday filter
4. **Template**: Custom Jinja2 expression returning boolean

**Example**:
```json
{
  "conditions": [
    {"type": "numeric_state", "entity_id": "sensor.outdoor_temp", "below": 15},
    {"type": "state", "entity_id": "binary_sensor.window", "state": "off"}
  ]
}
```

**Rationale**:
- **Intelligence**: Bindings react to context, not just calendar
- **Energy Saving**: Avoid heating when window open or outdoor warm
- **Flexibility**: 4 condition types cover most use cases
- **Native Integration**: Reuses HA's battle-tested condition system

**Behavior Notes**:
- Conditions failing → Binding doesn't activate (entities keep last state)
- Multiple bindings → Priority still resolves conflicts
- Max 5 conditions per binding (performance limit)

**Alternatives Considered**:
1. No conditions - Users build complex automation workarounds
2. OR logic support - Confusing, AND logic more intuitive
3. Unlimited conditions - Risk of performance degradation

---

### D038: Web UI as Primary Configuration Interface

**Date**: 2026-01-25
**Milestone**: Post-v1.0 (Web UI Enhancement)
**Status**: Active

**Context**: Config flow GUI wizard (3-step setup) is limited for managing slots, bindings, templates, and conditions. Advanced features need richer interface.

**Decision**: **Implement full-featured web panel** as primary configuration method.

**Implementation**:
- Custom Lovelace panel registered at `/climate-control-calendar`
- Single-page app with 4 tabs: Config, Monitor, Charts, About
- Full CRUD for slots and bindings via HTTP API endpoints
- Visual condition builder with type-specific forms
- Template support in text inputs with syntax hints
- Entity selector dropdowns, priority inputs, pattern matching UI
- Bilingual support (English + Italian) with i18n system

**Features**:
- **Config Tab**: Manage slots, bindings, global settings
- **Monitor Tab**: Real-time dashboard with active events, slots, conditions
- **Charts Tab**: Historical data visualization (future)
- **About Tab**: Documentation links, version info

**Rationale**:
- **Rich UX**: Modal dialogs, tabs, visual builders better than config flow
- **Advanced Features**: Templates and conditions need text inputs, not wizards
- **Real-Time Feedback**: Monitor tab shows current state instantly
- **Scalability**: Easier to add features vs. expanding config flow steps

**Config Flow Deprecation**:
- Config flow still used for initial setup (calendar/entity selection)
- Advanced features (slots, bindings, templates) only via web UI
- Config flow options flow simplified or removed

**Alternatives Considered**:
1. Expand config flow - Multi-step wizards become unwieldy
2. YAML configuration - Violates D009 (GUI-first philosophy)
3. Separate integration for UI - Fragmentation, poor UX

---

## Future Decisions

The following areas may require decisions in future milestones:

### Post-v1.0 (v1.1+)
- Performance optimization targets (if performance issues reported)
- Additional language support based on community demand
- Advanced monitoring and analytics features
- Historical data visualization in Charts tab

---

**Last Updated**: 2026-01-25 (D036-D038: Template, condition, and web UI support)
**Next Review**: After user feedback on template and condition features
