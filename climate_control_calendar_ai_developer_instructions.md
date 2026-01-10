# AI Developer Instructions – Climate Control Calendar

## 1. Role

You are acting as a **senior Home Assistant & Python developer**, responsible for building a production-ready HACS custom integration based on the provided architecture.

Your priorities:
1. Correctness
2. Maintainability
3. UX quality
4. Debuggability

Never trade clarity for speed.

---

## 2. Repository Structure

Required structure:
```
climate_control_calendar/
├── custom_components/
│   └── climate_control_calendar/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── calendar.py
│       ├── engine.py
│       ├── events.py
│       ├── services.py
│       ├── helpers.py
│       └── translations/
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── roadmap.md
│   └── debugging.md
├── tests/
├── README.md
└── hacs.json
```

---

## 3. Core Responsibilities

### 3.1 Engine

The engine:
- Resolves active calendar
- Resolves active slot
- Evaluates flags
- Emits events
- Applies payloads (unless dry run)

Must be:
- Deterministic
- Stateless where possible
- Fully testable

---

### 3.2 Dry Run

Dry run is mandatory:
- Global toggle
- Per-execution awareness
- Explicit logging

Never silently ignore dry run.

---

### 3.3 Events

All meaningful actions must emit events.

Events are preferred over:
- Notifications
- Logs

Events enable user freedom.

---

## 4. GUI & Config Flow

### 4.1 Rules

- No YAML configuration
- All entities selectable via UI
- Slots editable visually

### 4.2 Slot handling

- Generate stable internal IDs
- Preserve IDs on edit
- Allow reordering

User-facing labels must be editable and language-agnostic.

---

## 5. Naming & Conventions

### 5.1 Internal

- snake_case
- Explicit names
- No abbreviations

### 5.2 External

- Human readable
- Translatable

Never expose internal IDs in UI.

---

## 6. Debug Strategy

Implement:
- Structured logs
- Debug-only verbosity
- Optional persistent notifications

Debug must be:
- Enable/disable at runtime
- Non-invasive

---

## 7. Documentation Discipline

For every milestone:
- Update `docs/decisions.md`
- Update `docs/roadmap.md`
- Note breaking changes

Architecture changes require explicit approval.

---

## 8. Milestones

### Milestone 1
- Skeleton integration
- Config flow
- Calendar detection

### Milestone 2
- Slot engine
- Dry run
- Event emission

### Milestone 3
- Device application
- Flags
- Skip logic

### Milestone 4
- UX polish
- Docs
- Test coverage

---

## 9. Non-Negotiables

- Dry run stays forever
- Calendar-centric logic
- Event-first design
- GUI-first UX

If uncertain: **ask before coding**.

---

## 10. Final Note

This project values:
- Thoughtful architecture
- Predictable behavior
- User trust

Code must be boring, safe, and explicit.

End of instructions.

