# Development Roadmap

This document outlines the development plan for Climate Control Calendar, organized by milestones.

## Overview

The integration is developed in four major milestones, each building upon the previous one. This incremental approach ensures stability, testability, and clear progress tracking.

---

## Milestone 1: Foundation ✅

**Status**: Completed
**Target Date**: 2026-01-10
**Focus**: Skeleton integration, configuration infrastructure

### Goals
- [x] Create HACS-compatible repository structure
- [x] Implement Config Flow for GUI-based setup
- [x] Calendar entity detection and selection
- [x] Basic coordinator for calendar state monitoring
- [x] Helper utilities (slot ID generation, validation)
- [x] English translations
- [x] Documentation foundation (README, decisions.md)

### Deliverables
- Functional integration that can be installed via HACS
- Config flow allowing users to select calendar and climate entities
- Coordinator polling calendar state every 60 seconds
- Complete documentation of architectural decisions

### Testing Scope
- Config flow validation
- Helper function unit tests
- Coordinator basic functionality

---

## Milestone 2: Slot Engine ✅

**Status**: Completed (Core)
**Completed Date**: 2026-01-10
**Focus**: Time slot evaluation, dry run, event system

### Goals
- [x] Implement slot engine (`engine.py`)
- [x] Slot resolution algorithm (time-based matching)
- [x] Dry run execution with comprehensive logging
- [x] Event emission system (`events.py`)
- [x] Climate payload structure definition
- [x] Overlapping slot validation (Decision D011)
- [x] Engine integration with coordinator
- [ ] Slot configuration UI in Options Flow *(Deferred to M3/M4)*

### Key Features Implemented
- ✅ Time slot definitions with start/end times
- ✅ Day-of-week filtering for slots (default: all days)
- ✅ Active slot detection based on current time and calendar state
- ✅ Event emission for all significant actions
- ✅ Dry run mode with comprehensive "what would happen" logging
- ✅ Event deduplication (emit only on state transitions)
- ✅ Overlapping slot prevention via validation
- ✅ Support for overnight slots (e.g., 23:00-02:00)

### Event Types Implemented
- ✅ `climate_control_calendar_calendar_changed`: Calendar state transition
- ✅ `climate_control_calendar_slot_activated`: Time slot becomes active
- ✅ `climate_control_calendar_slot_deactivated`: Time slot becomes inactive
- ✅ `climate_control_calendar_dry_run_executed`: Dry run action logged
- ✅ `climate_control_calendar_climate_applied`: Climate payload applied (stub for M3)
- ✅ `climate_control_calendar_climate_skipped`: Climate application skipped (stub for M3)
- ✅ `climate_control_calendar_flag_set`: Override flag set (stub for M3)
- ✅ `climate_control_calendar_flag_cleared`: Override flag cleared (stub for M3)

### Architectural Decisions Made
- **D010**: Slot & Calendar Interaction - Slots active only when calendar ON
- **D011**: Overlapping Slots Prevention - Validation rejects overlaps
- **D012**: Climate Payload Structure - All fields optional, at least one required
- **D013**: Slot Days Default - All days (Mon-Sun) if not specified
- **D014**: Engine Trigger Strategy - Every coordinator update (60s)
- **D015**: Event Deduplication - Emit only on state transitions

### Testing Scope
- [ ] Comprehensive engine tests (various time scenarios)
- [ ] Slot resolution algorithm tests
- [ ] Dry run verification tests
- [ ] Event emission tests
- [ ] Overlapping slot validation tests

**Note**: Testing to be completed per M2 testing policy (end-of-milestone). Slot UI management deferred to allow focus on core engine functionality.

---

## Milestone 3: Device Control

**Status**: Planned
**Target Date**: TBD
**Focus**: Climate device application, override flags, skip logic

### Goals
- [ ] Implement climate device control logic
- [ ] Override flag system (skip_until_next_slot, skip_today, force_slot)
- [ ] Flag persistence and management
- [ ] Service implementations (`set_flag`, `clear_flag`, `force_slot`, `refresh_now`)
- [ ] Skip logic priority handling
- [ ] Multi-device application strategy

### Key Features
- Apply climate payloads to devices (temperature, HVAC mode, preset)
- Override flags for temporary behavior changes
- Service calls for manual control
- Sequential device application with error handling
- Dry run support for device operations

### Event Types to Implement
- `climate_applied`: Payload successfully applied to device
- `climate_skipped`: Application skipped due to flag
- `flag_set`: Override flag activated
- `flag_cleared`: Override flag cleared

### Services to Implement
- `set_flag`: Set an override flag
- `clear_flag`: Clear an override flag
- `force_slot`: Force activation of specific slot
- `refresh_now`: Force immediate coordinator refresh

### Testing Scope
- Device application tests
- Flag behavior tests (priority, persistence)
- Service call tests
- Error handling tests

---

## Milestone 4: Polish & Release

**Status**: Planned
**Target Date**: TBD
**Focus**: UX improvements, documentation, testing, localization

### Goals
- [ ] Italian (IT) translations
- [ ] Enhanced slot management UI
- [ ] Diagnostics and troubleshooting tools
- [ ] Comprehensive end-to-end tests
- [ ] Performance optimization
- [ ] User guide and examples
- [ ] Debugging documentation
- [ ] Release preparation (v1.0.0)

### Key Features
- Visual slot editor in Options Flow
- Diagnostic data collection
- Enhanced debug logging with filtering
- User-friendly error messages
- Example automations and use cases

### Documentation to Complete
- `docs/debugging.md`: Troubleshooting guide
- User guide with common scenarios
- API reference for events and services
- Migration guide (if needed)

### Testing Scope
- Integration tests (full workflows)
- Performance tests (multiple devices, many slots)
- Edge case tests
- UI/UX testing with real users

---

## Post-1.0 Roadmap

Features planned for future versions after stable 1.0 release:

### Version 1.1
- Multi-calendar support (calendar hierarchy)
- Slot templates (reusable configurations)
- Advanced scheduling (date ranges, exceptions)

### Version 1.2
- Zone-based control (different rooms, different calendars)
- Climate entity grouping
- Conditional slot activation (based on weather, occupancy)

### Version 2.0
- Machine learning for optimal scheduling
- Energy optimization mode
- Integration with energy dashboard
- Advanced analytics and reporting

---

## Release Strategy

### Alpha Phase (M1-M2)
- Internal testing only
- Breaking changes allowed
- Frequent updates

### Beta Phase (M3)
- Limited public testing
- Feature-complete
- Breaking changes with migration path
- HACS beta channel

### Stable Release (M4)
- Version 1.0.0
- Public HACS release
- Semantic versioning
- Backward compatibility guarantee

---

## Breaking Change Policy

### Pre-1.0 (Development)
- Breaking changes allowed between milestones
- Documented in release notes
- Migration instructions provided

### Post-1.0 (Stable)
- Breaking changes only in major versions (2.0, 3.0)
- Deprecation warnings one version in advance
- Automatic migration when possible
- Clear upgrade documentation

---

## Community Contributions

We welcome contributions in these areas:

### Development
- Bug fixes
- Feature implementations (from roadmap)
- Performance improvements
- Test coverage expansion

### Documentation
- Translation to additional languages
- Use case examples
- Tutorial videos
- Troubleshooting guides

### Testing
- Beta testing new features
- Bug reports with reproductions
- Performance feedback

---

## Success Metrics

### M1 (Foundation)
- ✅ Integration installs without errors
- ✅ Config flow completes successfully
- ✅ Coordinator polls calendar correctly

### M2 (Slot Engine)
- Slot resolution accuracy: 100%
- Event emission reliability: 100%
- Dry run logs comprehensible to users

### M3 (Device Control)
- Climate control success rate: >95%
- Flag behavior correctness: 100%
- Service response time: <1s

### M4 (Polish)
- User setup time: <5 minutes
- Documentation completeness: 100%
- Test coverage: >80%

---

## Dependencies & Blockers

### External Dependencies
- Home Assistant Calendar integration (prerequisite)
- Home Assistant Climate integration (prerequisite)
- Python 3.11+ (HA requirement)

### Known Blockers
- None currently identified

---

## Timeline Estimates

**Note**: These are rough estimates and may change based on development progress and feedback.

- **M1**: 1 week ✅ (Completed 2026-01-10)
- **M2**: 1 day ✅ (Completed 2026-01-10) - *Faster than expected!*
- **M3**: 2-3 weeks
- **M4**: 2 weeks
- **Total**: ~6-7 weeks to v1.0.0

---

**Last Updated**: 2026-01-10 (M2 completed)
**Next Review**: End of Milestone 3

---

## Changelog

### 2026-01-10 (Evening) - M2 Completed
- Completed Milestone 2 (Slot Engine) core functionality
- Implemented engine.py with slot resolution algorithm
- Implemented events.py with full event emission system
- Added overlapping slot validation (Decision D011)
- Integrated engine with coordinator
- Documented 6 new architectural decisions (D010-D015)
- Deferred slot UI management to M3/M4 to focus on engine quality

### 2026-01-10 (Morning) - M1 Completed
- Created roadmap document
- Completed Milestone 1 (Foundation)
- Defined M2-M4 goals and scope
