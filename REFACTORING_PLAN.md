# REFACTORING PLAN - Event-to-Slot Binding System

**Data**: 2026-01-11
**Stato**: Pronto per implementazione
**Branch corrente**: `claude/review-hacs-specs-O4Kix`

---

## SITUAZIONE ATTUALE

### Codice Funzionante ✅
L'integrazione è stata installata e configurata con successo:
- Config flow completo (3 step)
- Coordinator che monitora 1 calendario
- Sistema slot standalone (DA RIMUOVERE)
- Flag manager con persistenza
- Applier sequenziale con retry
- 6 servizi (set_flag, clear_flag, force_slot, refresh_now, add_slot, remove_slot)
- Traduzioni EN + IT
- Debug mode attivo

### Problema Architetturale ❌
Il sistema attuale NON rispecchia l'idea originale del progetto:

**ATTUALE (SBAGLIATO)**:
- 1 solo calendario → solo ON/OFF
- Slot configurati nell'integrazione (duplicazione)
- Eventi calendario NON contengono temperature/logiche
- Cambio profilo DIFFICILE (servizi manuali)

**IDEA ORIGINALE (CORRETTA)**:
- N calendari → N profili
- Eventi calendario contengono tutto (fasce orarie sono eventi ricorrenti)
- Slot nell'integrazione contengono solo climate payload
- Binding collega eventi → slot
- Cambio profilo FACILE (attiva/disattiva calendario)

---

## ARCHITETTURA FINALE CONFERMATA

### Componenti del Sistema

#### 1. CALENDARI (HA nativi)
```
Utente gestisce calendari HA:
- "Smart Working" calendario
  └─ Evento "Mattino" → ricorrente lun-ven 6:00-9:00
  └─ Evento "Lavoro" → ricorrente lun-ven 9:00-18:00
  └─ Evento "Sera" → ricorrente lun-ven 18:00-23:00

- "Turno Notte" calendario
  └─ Eventi con orari notturni

- "Vacanza" calendario
  └─ Evento "Risparmio" → periodo specifico
```

**L'integrazione monitora N calendari contemporaneamente.**

#### 2. SLOT (definizioni climate payload)
```yaml
slots:
  - id: "abc123"
    label: "Comfort Alto"
    climate_payload:
      temperature: 22
      hvac_mode: heat
      preset_mode: comfort

  - id: "def456"
    label: "Eco Ufficio"
    climate_payload:
      temperature: 20
      preset_mode: eco
```

**Slot = solo configurazioni clima, NON contengono orari/giorni**

#### 3. BINDINGS (fulcro del sistema)
```yaml
event_to_slot_bindings:
  # Binding specifico per calendario
  - calendars: ["calendar.smart_working", "calendar.turni"]
    match:
      type: "summary"  # exact match
      value: "Mattino"
    slot_id: "abc123"
    priority: 10

  # Binding fuzzy per tutti i calendari
  - calendars: "*"
    match:
      type: "summary_contains"
      value: "comfort"
    slot_id: "abc123"
    priority: 5

  # Binding regex
  - calendars: ["calendar.external"]
    match:
      type: "regex"
      value: "^Lavoro.*"
    slot_id: "def456"
    priority: 5
```

**Binding = collegamento evento → slot**

---

## REGOLE SISTEMA

### Match Types (estensibile)
1. **`summary`**: Exact match sul titolo evento
2. **`summary_contains`**: Fuzzy match (contiene substring)
3. **`regex`**: Pattern matching
4. **FUTURI**: Altri metodi (description, location, ecc.)

### Calendari Target
- Lista specifica: `["calendar.smart", "calendar.turni"]`
- Wildcard tutti: `"*"`
- Singolo: `["calendar.smart"]`

### Risoluzione Conflitti
1. Trova tutti binding che matchano evento corrente
2. Ordina per priorità (DESC)
3. **A parità priorità → vince ULTIMO**
4. Ritorna 1 slot (1 evento → 1 slot)

### Engine Logic
```python
def resolve_slot_for_event(event, calendar_id, all_bindings):
    # 1. Filtra binding compatibili con questo calendario
    compatible = [
        b for b in all_bindings
        if matches_calendar(b.calendars, calendar_id)
    ]

    # 2. Filtra binding che matchano questo evento
    matching = [
        b for b in compatible
        if matches_event(b.match, event.summary)
    ]

    if not matching:
        return None  # evento non mappato

    # 3. Ordina per priorità DESC, prendi ultimo a parità
    sorted_bindings = sorted(matching, key=lambda b: b.priority, reverse=True)
    winner = sorted_bindings[0]  # primo dopo sort DESC = max priority

    # Se stessa priorità, sorted mantiene ordine originale
    # quindi ultimo inserito vince

    return get_slot(winner.slot_id)
```

---

## COSA VA CAMBIATO

### DA RIMUOVERE ❌

**File/Sezioni da eliminare/modificare**:
1. `config_flow.py` → Cambia step calendario: da 1 a N calendari
2. `engine.py` → Rimuovi logica slot standalone
3. `services.py` → Rimuovi add_slot/remove_slot (sostituire con add_binding)
4. `coordinator.py` → Da 1 calendario a N calendari
5. `helpers.py` → Rimuovi validate_slot_overlap (slot non hanno più orari)

**Concetti da rimuovere**:
- Slot con time_start/time_end/days
- Validazione overlap slot
- Slot evaluation basata su tempo corrente nell'integrazione

### DA AGGIUNGERE ✅

**Nuovi file**:
1. `binding_manager.py` → Gestisce event-to-slot bindings
2. `event_matcher.py` → Match logic (summary, contains, regex)
3. `calendar_monitor.py` → Multi-calendar coordinator

**Nuove funzionalità**:
1. Config flow multi-calendario
2. Servizi: add_binding, remove_binding, list_bindings
3. Engine che legge eventi da calendari
4. Parsing eventi calendario (`calendar.get_events()`)
5. Risoluzione binding → slot

---

## NUOVA ARCHITETTURA - DETTAGLIO

### Storage Structure
```yaml
# Config Entry Data (immutable)
data:
  calendar_entities: ["calendar.smart_working", "calendar.turni"]
  dry_run: true
  debug_mode: true

# Config Entry Options (mutable)
options:
  climate_entities: ["climate.living_room", "climate.bedroom"]
  slots:
    - id: "abc123"
      label: "Comfort Alto"
      climate_payload:
        temperature: 22
        hvac_mode: heat

  bindings:
    - calendars: ["calendar.smart_working"]
      match:
        type: "summary"
        value: "Mattino"
      slot_id: "abc123"
      priority: 10
```

### Config Flow Changes
```
STEP 1: Seleziona Calendari (multi-select)
├─ calendar.smart_working ✓
├─ calendar.turni ✓
└─ calendar.vacanza ✓

STEP 2: Seleziona Climate Entities (come ora)

STEP 3: Options (dry_run, debug) (come ora)
```

### Coordinator Changes
```python
class MultiCalendarCoordinator(DataUpdateCoordinator):
    """Monitors N calendars."""

    def __init__(self, hass, calendar_entities):
        self.calendar_entities = calendar_entities

    async def _async_update_data(self):
        """Fetch events from ALL calendars."""
        all_events = []

        for calendar_id in self.calendar_entities:
            events = await self._get_calendar_events(calendar_id)
            all_events.extend([
                {
                    "calendar_id": calendar_id,
                    "summary": event["summary"],
                    "start": event["start"],
                    "end": event["end"],
                    "is_active": self._is_event_active_now(event),
                }
                for event in events
            ])

        return {
            "events": all_events,
            "active_events": [e for e in all_events if e["is_active"]],
            "last_update": dt_util.utcnow(),
        }

    async def _get_calendar_events(self, calendar_id):
        """Get events from a single calendar."""
        # Use calendar.get_events service
        now = dt_util.now()
        start = now
        end = now + timedelta(hours=24)  # fetch next 24h

        return await self.hass.services.async_call(
            "calendar",
            "get_events",
            {"entity_id": calendar_id, "start": start, "end": end},
            blocking=True,
            return_response=True,
        )
```

### Engine Changes
```python
class ClimateControlEngine:
    """Evaluates active events and resolves slots via bindings."""

    async def evaluate(self, coordinator_data, slots, bindings, climate_entities):
        """Main evaluation loop."""
        active_events = coordinator_data["active_events"]

        if not active_events:
            # No events active → deactivate
            await self._deactivate_all()
            return

        # Find slots for all active events
        active_slots = []
        for event in active_events:
            slot = self._resolve_slot(event, bindings, slots)
            if slot:
                active_slots.append(slot)

        if not active_slots:
            # Events exist but no binding matched
            _LOGGER.warning("Active events but no slot matched")
            return

        # Apply first active slot (or implement priority)
        await self._apply_slot(active_slots[0], climate_entities)

    def _resolve_slot(self, event, bindings, slots):
        """Resolve which slot to use for this event."""
        calendar_id = event["calendar_id"]
        summary = event["summary"]

        # Filter bindings for this calendar
        matching_bindings = [
            b for b in bindings
            if self._matches_calendar(b["calendars"], calendar_id)
            and self._matches_event(b["match"], summary)
        ]

        if not matching_bindings:
            return None

        # Sort by priority DESC, last wins at same priority
        sorted_bindings = sorted(
            matching_bindings,
            key=lambda b: b["priority"],
            reverse=True
        )

        winner = sorted_bindings[0]
        slot_id = winner["slot_id"]

        # Find slot by ID
        return next((s for s in slots if s["id"] == slot_id), None)

    def _matches_calendar(self, calendar_list, calendar_id):
        """Check if calendar matches."""
        if calendar_list == "*":
            return True
        return calendar_id in calendar_list

    def _matches_event(self, match_config, summary):
        """Check if event matches pattern."""
        match_type = match_config["type"]
        value = match_config["value"]

        if match_type == "summary":
            return summary == value
        elif match_type == "summary_contains":
            return value in summary
        elif match_type == "regex":
            import re
            return bool(re.match(value, summary))

        return False
```

### Services Changes
```yaml
# REMOVE
- climate_control_calendar.add_slot
- climate_control_calendar.remove_slot

# ADD
- climate_control_calendar.add_binding
- climate_control_calendar.remove_binding
- climate_control_calendar.list_bindings
```

**New Service: add_binding**
```yaml
service: climate_control_calendar.add_binding
data:
  calendars: ["calendar.smart_working"]  # or "*"
  match:
    type: "summary"  # or "summary_contains", "regex"
    value: "Mattino"
  slot_id: "abc123"
  priority: 10
```

---

## PIANO DI IMPLEMENTAZIONE

### FASE 1: Preparazione
1. ✅ Commit e push tutto il codice attuale
2. ✅ Creare questo documento di refactoring
3. ✅ Nuovo branch: `refactor/event-binding-system`

### FASE 2: Nuovi componenti
1. Creare `event_matcher.py` (match logic)
2. Creare `binding_manager.py` (gestione bindings)
3. Creare `calendar_monitor.py` (multi-calendar coordinator)

### FASE 3: Modifiche esistenti
1. Modificare `config_flow.py` → multi-calendario
2. Modificare `coordinator.py` → usa calendar_monitor
3. Modificare `engine.py` → usa binding resolution
4. Modificare `services.py` → nuovi servizi binding
5. Modificare `const.py` → nuove costanti
6. Modificare `helpers.py` → rimuovi validazioni slot vecchie

### FASE 4: Testing
1. Installare integrazione refactorata
2. Configurare multi-calendario
3. Creare slot
4. Creare binding
5. Testare risoluzione eventi

### FASE 5: Cleanup
1. Rimuovere codice vecchio commentato
2. Aggiornare unit tests
3. Aggiornare documentazione
4. Merge su main

---

## DECISIONI CONFERMATE

### D032: Event-to-Slot Binding System
**Data**: 2026-01-11
**Decisione**: Implementare sistema binding tra eventi calendario e slot
**Match types**: summary, summary_contains, regex (estensibile)
**Calendar target**: Lista specifica o wildcard "*"
**Conflict resolution**: Priority DESC, ultimo vince a parità
**Ratio**: 1 evento → 1 slot

### D033: Multi-Calendar Support
**Data**: 2026-01-11
**Decisione**: Supportare N calendari contemporaneamente
**Config flow**: Multi-select calendari
**Coordinator**: Monitora tutti i calendari configurati
**Engine**: Valuta eventi da tutti i calendari

### D034: Slot Semplificati
**Data**: 2026-01-11
**Decisione**: Slot contengono SOLO climate payload
**Rimosso**: time_start, time_end, days (vanno negli eventi calendario)
**Mantiene**: id, label, climate_payload
**Validazione**: Solo climate payload, NO overlap check

---

## NOTE IMPORTANTI

### Eventi Calendario
- Gli eventi ricorrenti sono gestiti da HA automaticamente
- `calendar.get_events()` ritorna già eventi espansi
- Non serve gestire rrule nell'integrazione

### Backward Compatibility
- ⚠️ Breaking change totale
- Utenti devono riconfigurare da zero
- Versione: bump a 2.0.0 (major)

### GUI Future
- Tutti i servizi progettati pensando alla GUI futura
- GUI mostrerà:
  - Lista eventi da calendari
  - Drag & drop evento → slot
  - Suggerimenti intelligenti
  - Preview binding attivi

### Testing Strategy
- Unit test per event_matcher
- Unit test per binding_manager
- Integration test con calendari mock
- Manual test con Google Calendar

---

## FILE DA CREARE

### `event_matcher.py`
```python
"""Event matching logic for binding resolution."""

class EventMatcher:
    """Matches events against binding rules."""

    @staticmethod
    def matches(match_config: dict, event_summary: str) -> bool:
        """Check if event matches the pattern."""
        # Implement match logic
        pass
```

### `binding_manager.py`
```python
"""Manages event-to-slot bindings."""

class BindingManager:
    """Manages bindings with priority resolution."""

    def __init__(self, hass, entry_id):
        self._hass = hass
        self._entry_id = entry_id
        self._bindings = []

    async def async_load(self):
        """Load bindings from config entry options."""
        pass

    def resolve_slot(self, event, calendar_id, slots):
        """Resolve which slot to use for this event."""
        pass

    async def async_add_binding(self, binding):
        """Add a new binding."""
        pass

    async def async_remove_binding(self, binding_id):
        """Remove a binding."""
        pass
```

### `calendar_monitor.py`
```python
"""Multi-calendar monitoring coordinator."""

class MultiCalendarCoordinator(DataUpdateCoordinator):
    """Monitors multiple calendars simultaneously."""

    def __init__(self, hass, calendar_entities, update_interval):
        self.calendar_entities = calendar_entities
        # Initialize coordinator

    async def _async_update_data(self):
        """Fetch events from all calendars."""
        pass
```

---

## ESEMPI D'USO FINALE

### Setup iniziale
```yaml
# Config Flow
1. Seleziona calendari:
   - calendar.smart_working ✓
   - calendar.vacanza ✓

2. Seleziona climate entities:
   - climate.soggiorno ✓
   - climate.camera ✓

3. Options:
   - Dry run: true
   - Debug: true
```

### Crea slot via servizio
```yaml
service: climate_control_calendar.add_slot
data:
  label: "Comfort Mattino"
  climate_payload:
    temperature: 22
    hvac_mode: heat
    preset_mode: comfort

# Ritorna: slot_id "abc123"
```

### Crea binding via servizio
```yaml
service: climate_control_calendar.add_binding
data:
  calendars: ["calendar.smart_working"]
  match:
    type: "summary"
    value: "Mattino"
  slot_id: "abc123"
  priority: 10

# Ora evento "Mattino" → applica Comfort Mattino
```

### Cambio profilo
```
Attiva calendario "Smart Working" → eventi "Mattino/Lavoro/Sera" attivi
Disattiva "Smart Working", attiva "Vacanza" → eventi "Risparmio" attivi

Facilissimo, dalla UI calendario HA!
```

---

## DOMANDE APERTE / DA DECIDERE

1. **Più eventi attivi contemporaneamente**: Come gestiamo?
   - Opzione A: Applica primo slot trovato
   - Opzione B: Priority anche tra eventi (non solo binding)
   - **PROPOSTA**: A, più semplice

2. **Eventi senza binding**: Log warning o silenzio?
   - **PROPOSTA**: Log warning (debug), aiuta troubleshooting

3. **Servizio list_events**: Utile per debug?
   - **PROPOSTA**: Sì, mostra eventi attivi + slot risolti

4. **Calendario rimosso da HA**: Come gestiamo?
   - **PROPOSTA**: Log error, ignora calendario, continua con altri

---

## STATO REPOSITORY

**Branch**: `claude/review-hacs-specs-O4Kix`
**Ultimo commit**: feat: Add add_slot and remove_slot services
**Prossimo branch**: `refactor/event-binding-system`

**Pronto per refactoring completo!** 🚀

---

**Fine documento - Pronto per nuova sessione**
