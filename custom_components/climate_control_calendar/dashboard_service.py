"""
Dashboard Data Service - Aggrega dati per frontend dashboard.

Espone API uniforme per dashboard senza duplicare logica esistente.
Aggrega dati da coordinator, engine, binding_manager.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .binding_manager import BindingManager
    from .coordinator import ClimateControlCalendarCoordinator
    from .engine import Engine


class DashboardDataService:
    """Servizio dati per dashboard (no logica business, solo aggregazione)."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ClimateControlCalendarCoordinator,
        engine: Engine,
        binding_manager: BindingManager,
        config_entry: ConfigEntry,
    ):
        """Initialize dashboard service."""
        self.hass = hass
        self.coordinator = coordinator
        self.engine = engine
        self.binding_manager = binding_manager
        self.config_entry = config_entry

    # ═══════════════════════════════════════════════════════════
    # LIVE STATE (cosa succede ora)
    # ═══════════════════════════════════════════════════════════

    async def get_live_state(self) -> dict[str, Any]:
        """
        Stato live sistema.

        Returns:
            {
                "active_slot": {...} | None,
                "trigger_reason": {...} | None,
                "affected_entities": [...],
                "timestamp": "2026-01-17T15:30:00+01:00"
            }
        """
        # Ottieni slot attivo dall'ultimo evaluate()
        active_slot = self.engine.last_active_slot

        if not active_slot:
            return {
                "active_slot": None,
                "trigger_reason": None,
                "affected_entities": [],
                "timestamp": dt_util.now().isoformat(),
            }

        # Trova evento/binding che ha triggerato questo slot
        trigger = await self._find_trigger_reason(active_slot)

        # Stato entità climate
        entities_status = await self._get_climate_entities_status(
            active_slot.get("entities", [])
        )

        return {
            "active_slot": active_slot,
            "trigger_reason": trigger,
            "affected_entities": entities_status,
            "timestamp": dt_util.now().isoformat(),
        }

    async def _find_trigger_reason(
        self, active_slot: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Trova evento calendario e binding che hanno triggerato lo slot attivo.

        Args:
            active_slot: Slot attualmente attivo

        Returns:
            {
                "calendar_event": "Riscaldamento Notte",
                "calendar_id": "calendar.casa",
                "matched_binding": {...},
                "event_start": "2026-01-17T22:00:00+01:00",
                "event_end": "2026-01-18T07:00:00+01:00"
            }
        """
        slot_id = active_slot.get("id")
        now = dt_util.now()

        # Trova bindings per questo slot
        slot_bindings = [
            b for b in self.binding_manager.bindings if b["slot_id"] == slot_id
        ]

        if not slot_bindings:
            return None

        # Cerca eventi attivi che matchano uno dei bindings
        calendar_events = self.coordinator.data or []

        for event in calendar_events:
            # Controlla se evento è attivo ora
            if not (event["start"] <= now < event["end"]):
                continue

            # Cerca binding che matcha questo evento
            matched_binding = self.binding_manager.find_best_match(
                event_summary=event["summary"], calendar_id=event["calendar_id"]
            )

            if matched_binding and matched_binding["slot_id"] == slot_id:
                return {
                    "calendar_event": event["summary"],
                    "calendar_id": event["calendar_id"],
                    "matched_binding": matched_binding,
                    "event_start": event["start"].isoformat(),
                    "event_end": event["end"].isoformat(),
                }

        return None

    async def _get_climate_entities_status(
        self, entity_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Ottieni stato corrente entità climate.

        Args:
            entity_ids: Lista entity_id climate

        Returns:
            [
                {
                    "entity_id": "climate.soggiorno",
                    "current_temperature": 20.5,
                    "target_temperature": 20.0,
                    "hvac_mode": "heat",
                    "status": "ok" | "unavailable" | "not_found"
                },
                ...
            ]
        """
        statuses = []
        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state:
                if state.state == "unavailable":
                    statuses.append({"entity_id": entity_id, "status": "unavailable"})
                else:
                    statuses.append({
                        "entity_id": entity_id,
                        "friendly_name": state.attributes.get("friendly_name", entity_id),
                        "current_temperature": state.attributes.get(
                            "current_temperature"
                        ),
                        "target_temperature": state.attributes.get("temperature"),
                        "hvac_mode": state.state,
                        "fan_mode": state.attributes.get("fan_mode"),
                        "preset_mode": state.attributes.get("preset_mode"),
                        "status": "ok",
                    })
            else:
                statuses.append({"entity_id": entity_id, "status": "not_found"})
        return statuses

    # ═══════════════════════════════════════════════════════════
    # TIMELINE (giornata)
    # ═══════════════════════════════════════════════════════════

    async def get_timeline(self, date: datetime | None = None) -> dict[str, Any]:
        """
        Timeline eventi giornata con slot applicati.

        Args:
            date: Data da analizzare (default: oggi)

        Returns:
            {
                "date": "2026-01-17",
                "events": [
                    {
                        "start": "00:00:00",
                        "end": "07:00:00",
                        "calendar_event": "Riscaldamento Notte",
                        "calendar_id": "calendar.casa",
                        "matched_binding": {...},
                        "applied_slot": {...},
                        "status": "active" | "upcoming" | "past"
                    },
                    ...
                ],
                "coverage_percentage": 100.0,
                "gaps": [...]
            }
        """
        if date is None:
            date = dt_util.now()

        # Ottieni eventi calendario per la giornata
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Usa dati coordinator (già ha eventi parsed)
        calendar_events = self.coordinator.data or []

        # Filtra eventi della giornata
        day_events = [
            e
            for e in calendar_events
            if self._event_overlaps_range(e, start_of_day, end_of_day)
        ]

        # Match eventi → bindings → slots
        timeline_entries = []
        for event in day_events:
            binding = self.binding_manager.find_best_match(
                event_summary=event["summary"], calendar_id=event["calendar_id"]
            )

            if binding:
                slot = self._get_slot_by_id(binding["slot_id"])
                timeline_entries.append({
                    "start": event["start"].strftime("%H:%M:%S"),
                    "end": event["end"].strftime("%H:%M:%S"),
                    "start_datetime": event["start"].isoformat(),
                    "end_datetime": event["end"].isoformat(),
                    "calendar_event": event["summary"],
                    "calendar_id": event["calendar_id"],
                    "matched_binding": binding,
                    "applied_slot": slot,
                    "status": self._get_event_status(event, dt_util.now()),
                })
            else:
                # Evento senza binding (non verrà applicato)
                timeline_entries.append({
                    "start": event["start"].strftime("%H:%M:%S"),
                    "end": event["end"].strftime("%H:%M:%S"),
                    "start_datetime": event["start"].isoformat(),
                    "end_datetime": event["end"].isoformat(),
                    "calendar_event": event["summary"],
                    "calendar_id": event["calendar_id"],
                    "matched_binding": None,
                    "applied_slot": None,
                    "status": self._get_event_status(event, dt_util.now()),
                })

        # Ordina per orario inizio
        timeline_entries.sort(key=lambda x: x["start_datetime"])

        # Analizza copertura
        coverage, gaps = self._analyze_coverage(
            timeline_entries, start_of_day, end_of_day
        )

        return {
            "date": date.date().isoformat(),
            "events": timeline_entries,
            "coverage_percentage": coverage,
            "gaps": gaps,
        }

    def _event_overlaps_range(
        self, event: dict[str, Any], range_start: datetime, range_end: datetime
    ) -> bool:
        """Check if event overlaps with time range."""
        return event["start"] < range_end and event["end"] > range_start

    def _get_event_status(
        self, event: dict[str, Any], now: datetime
    ) -> str:
        """Get event status relative to current time."""
        if event["start"] <= now < event["end"]:
            return "active"
        elif now < event["start"]:
            return "upcoming"
        else:
            return "past"

    def _get_slot_by_id(self, slot_id: str) -> dict[str, Any] | None:
        """Trova slot by ID."""
        slots = self.config_entry.options.get("slots", [])
        return next((s for s in slots if s["id"] == slot_id), None)

    def _analyze_coverage(
        self,
        timeline_entries: list[dict[str, Any]],
        start_of_day: datetime,
        end_of_day: datetime,
    ) -> tuple[float, list[dict[str, Any]]]:
        """
        Analizza copertura giornata.

        Args:
            timeline_entries: Eventi timeline con slot applicati
            start_of_day: Inizio giornata
            end_of_day: Fine giornata

        Returns:
            (coverage_percentage, gaps_list)
            coverage_percentage: 0-100
            gaps_list: [{"start": "08:00", "end": "09:00", "duration_hours": 1}, ...]
        """
        # Filtra solo eventi con slot applicato
        covered_events = [
            e for e in timeline_entries if e["applied_slot"] is not None
        ]

        if not covered_events:
            # Nessuna copertura
            return 0.0, [
                {
                    "start": start_of_day.strftime("%H:%M"),
                    "end": end_of_day.strftime("%H:%M"),
                    "duration_hours": 24.0,
                }
            ]

        # Crea lista intervalli coperti
        covered_ranges = []
        for event in covered_events:
            event_start = dt_util.parse_datetime(event["start_datetime"])
            event_end = dt_util.parse_datetime(event["end_datetime"])

            # Clamp agli orari giornata
            event_start = max(event_start, start_of_day)
            event_end = min(event_end, end_of_day)

            covered_ranges.append((event_start, event_end))

        # Merge intervalli sovrapposti
        merged_ranges = self._merge_time_ranges(covered_ranges)

        # Calcola ore coperte
        covered_seconds = sum(
            (end - start).total_seconds() for start, end in merged_ranges
        )
        total_seconds = (end_of_day - start_of_day).total_seconds()
        coverage_percentage = (covered_seconds / total_seconds) * 100

        # Trova gaps (intervalli non coperti)
        gaps = []
        current_time = start_of_day

        for range_start, range_end in merged_ranges:
            if current_time < range_start:
                # Gap trovato
                gap_duration_hours = (range_start - current_time).total_seconds() / 3600
                gaps.append({
                    "start": current_time.strftime("%H:%M"),
                    "end": range_start.strftime("%H:%M"),
                    "duration_hours": round(gap_duration_hours, 1),
                })
            current_time = max(current_time, range_end)

        # Check gap finale
        if current_time < end_of_day:
            gap_duration_hours = (end_of_day - current_time).total_seconds() / 3600
            gaps.append({
                "start": current_time.strftime("%H:%M"),
                "end": end_of_day.strftime("%H:%M"),
                "duration_hours": round(gap_duration_hours, 1),
            })

        return round(coverage_percentage, 1), gaps

    def _merge_time_ranges(
        self, ranges: list[tuple[datetime, datetime]]
    ) -> list[tuple[datetime, datetime]]:
        """
        Merge overlapping time ranges.

        Args:
            ranges: [(start1, end1), (start2, end2), ...]

        Returns:
            Merged ranges sorted by start time
        """
        if not ranges:
            return []

        # Ordina per start time
        sorted_ranges = sorted(ranges, key=lambda x: x[0])

        merged = [sorted_ranges[0]]

        for current_start, current_end in sorted_ranges[1:]:
            last_start, last_end = merged[-1]

            if current_start <= last_end:
                # Overlap, merge
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                # No overlap
                merged.append((current_start, current_end))

        return merged
