"""Unit tests for helpers.py"""
import pytest
from datetime import datetime
from custom_components.climate_control_calendar.helpers import (
    generate_slot_id,
    validate_slot_data,
    validate_climate_payload,
    do_slots_overlap,
    validate_slot_overlap,
)


class TestSlotIDGeneration:
    """Test slot ID generation."""

    def test_generate_slot_id_deterministic(self):
        """Test that same label + timestamp produces same ID."""
        label = "morning_comfort"
        timestamp = 1704902400.0

        id1 = generate_slot_id(label, timestamp)
        id2 = generate_slot_id(label, timestamp)

        assert id1 == id2

    def test_generate_slot_id_length(self):
        """Test that slot ID is exactly 12 characters."""
        slot_id = generate_slot_id("test_slot", 1234567890.0)
        assert len(slot_id) == 12

    def test_generate_slot_id_hexadecimal(self):
        """Test that slot ID contains only hex characters."""
        slot_id = generate_slot_id("test_slot", 1234567890.0)
        assert all(c in "0123456789abcdef" for c in slot_id)

    def test_generate_slot_id_different_labels(self):
        """Test that different labels produce different IDs."""
        timestamp = 1704902400.0

        id1 = generate_slot_id("label_one", timestamp)
        id2 = generate_slot_id("label_two", timestamp)

        assert id1 != id2

    def test_generate_slot_id_different_timestamps(self):
        """Test that different timestamps produce different IDs."""
        label = "morning_comfort"

        id1 = generate_slot_id(label, 1704902400.0)
        id2 = generate_slot_id(label, 1704902401.0)

        assert id1 != id2

    def test_generate_slot_id_auto_timestamp(self):
        """Test that omitting timestamp uses current time."""
        id1 = generate_slot_id("test")
        id2 = generate_slot_id("test")

        # Should be different because timestamps differ
        assert id1 != id2


class TestClimatePayloadValidation:
    """Test climate payload validation."""

    def test_validate_payload_temperature_only(self):
        """Test valid payload with only temperature."""
        payload = {"temperature": 22.0}
        assert validate_climate_payload(payload) is True

    def test_validate_payload_hvac_mode_only(self):
        """Test valid payload with only HVAC mode."""
        payload = {"hvac_mode": "heat"}
        assert validate_climate_payload(payload) is True

    def test_validate_payload_all_fields(self):
        """Test valid payload with all fields."""
        payload = {
            "temperature": 21.0,
            "hvac_mode": "heat",
            "preset_mode": "comfort",
            "fan_mode": "auto",
            "swing_mode": "off"
        }
        assert validate_climate_payload(payload) is True

    def test_validate_payload_empty(self):
        """Test that empty payload is invalid."""
        payload = {}
        assert validate_climate_payload(payload) is False

    def test_validate_payload_invalid_temperature_type(self):
        """Test that non-numeric temperature is invalid."""
        payload = {"temperature": "twenty"}
        assert validate_climate_payload(payload) is False

    def test_validate_payload_invalid_hvac_mode(self):
        """Test that invalid HVAC mode is rejected."""
        payload = {"hvac_mode": "invalid_mode"}
        assert validate_climate_payload(payload) is False

    def test_validate_payload_valid_hvac_modes(self):
        """Test all valid HVAC modes."""
        valid_modes = ["heat", "cool", "heat_cool", "auto", "off", "dry", "fan_only"]

        for mode in valid_modes:
            payload = {"hvac_mode": mode}
            assert validate_climate_payload(payload) is True, f"Mode {mode} should be valid"


class TestSlotOverlapDetection:
    """Test slot overlap detection."""

    def test_no_overlap_sequential_slots(self):
        """Test that sequential slots don't overlap."""
        slot_a = {
            "time_start": "06:00",
            "time_end": "09:00",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
        slot_b = {
            "time_start": "09:00",
            "time_end": "12:00",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is False

    def test_overlap_same_time_same_days(self):
        """Test that identical slots overlap."""
        slot_a = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday", "tuesday"]
        }
        slot_b = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday", "tuesday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is True

    def test_overlap_partial_time_overlap(self):
        """Test that partial time overlap is detected."""
        slot_a = {
            "time_start": "06:00",
            "time_end": "10:00",
            "days": ["monday"]
        }
        slot_b = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is True

    def test_no_overlap_different_days(self):
        """Test that same time on different days doesn't overlap."""
        slot_a = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday", "tuesday"]
        }
        slot_b = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["wednesday", "thursday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is False

    def test_overlap_one_common_day(self):
        """Test overlap when slots share one day."""
        slot_a = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday", "tuesday", "wednesday"]
        }
        slot_b = {
            "time_start": "10:00",
            "time_end": "14:00",
            "days": ["wednesday", "thursday", "friday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is True

    def test_overnight_slot_overlap_detection(self):
        """Test overlap detection with overnight slots."""
        # Overnight slot: 23:00 -> 02:00
        slot_a = {
            "time_start": "23:00",
            "time_end": "02:00",
            "days": ["monday"]
        }
        # Morning slot: 01:00 -> 06:00
        slot_b = {
            "time_start": "01:00",
            "time_end": "06:00",
            "days": ["monday"]
        }

        # Should overlap because overnight slot extends to 02:00 next day
        assert do_slots_overlap(slot_a, slot_b) is True

    def test_overnight_no_overlap_before(self):
        """Test overnight slot doesn't overlap with earlier slot."""
        # Overnight: 23:00 -> 02:00
        slot_a = {
            "time_start": "23:00",
            "time_end": "02:00",
            "days": ["monday"]
        }
        # Evening: 18:00 -> 22:00
        slot_b = {
            "time_start": "18:00",
            "time_end": "22:00",
            "days": ["monday"]
        }

        assert do_slots_overlap(slot_a, slot_b) is False


class TestSlotDataValidation:
    """Test slot data validation."""

    def test_validate_slot_valid_data(self):
        """Test validation of valid slot data."""
        slot_data = {
            "label": "morning_comfort",
            "time_start": "06:00",
            "time_end": "09:00",
            "days": ["monday", "tuesday", "wednesday"],
            "climate_payload": {"temperature": 22.0}
        }

        assert validate_slot_data(slot_data) is True

    def test_validate_slot_missing_label(self):
        """Test that missing label fails validation."""
        slot_data = {
            "time_start": "06:00",
            "time_end": "09:00",
            "climate_payload": {"temperature": 22.0}
        }

        assert validate_slot_data(slot_data) is False

    def test_validate_slot_invalid_time_format(self):
        """Test that invalid time format fails validation."""
        slot_data = {
            "label": "test",
            "time_start": "6:00",  # Should be "06:00"
            "time_end": "09:00",
            "climate_payload": {"temperature": 22.0}
        }

        assert validate_slot_data(slot_data) is False

    def test_validate_slot_invalid_payload(self):
        """Test that invalid climate payload fails validation."""
        slot_data = {
            "label": "test",
            "time_start": "06:00",
            "time_end": "09:00",
            "climate_payload": {}  # Empty payload
        }

        assert validate_slot_data(slot_data) is False


class TestSlotOverlapValidation:
    """Test validate_slot_overlap function."""

    def test_validate_no_overlap_with_existing_slots(self):
        """Test validation passes when no overlap."""
        new_slot = {
            "time_start": "12:00",
            "time_end": "18:00",
            "days": ["monday"]
        }
        existing_slots = [
            {
                "time_start": "06:00",
                "time_end": "09:00",
                "days": ["monday"]
            },
            {
                "time_start": "18:00",
                "time_end": "22:00",
                "days": ["monday"]
            }
        ]

        result = validate_slot_overlap(new_slot, existing_slots)
        assert result["valid"] is True
        assert result["overlaps_with"] is None

    def test_validate_detects_overlap(self):
        """Test validation fails when overlap detected."""
        new_slot = {
            "time_start": "08:00",
            "time_end": "12:00",
            "days": ["monday"]
        }
        existing_slots = [
            {
                "id": "existing_slot_123",
                "label": "morning_comfort",
                "time_start": "06:00",
                "time_end": "10:00",
                "days": ["monday"]
            }
        ]

        result = validate_slot_overlap(new_slot, existing_slots)
        assert result["valid"] is False
        assert result["overlaps_with"] == "existing_slot_123"

    def test_validate_no_existing_slots(self):
        """Test validation passes with no existing slots."""
        new_slot = {
            "time_start": "06:00",
            "time_end": "09:00",
            "days": ["monday"]
        }
        existing_slots = []

        result = validate_slot_overlap(new_slot, existing_slots)
        assert result["valid"] is True
        assert result["overlaps_with"] is None
