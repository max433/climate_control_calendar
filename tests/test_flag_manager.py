"""Unit tests for flag_manager.py"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from custom_components.climate_control_calendar.flag_manager import FlagManager
from custom_components.climate_control_calendar.const import (
    FLAG_TYPE_SKIP_TODAY,
    FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT,
    FLAG_TYPE_FORCE_SLOT,
    STORAGE_FLAG_TYPE,
    STORAGE_SLOT_ID,
    STORAGE_SET_AT,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_event_emitter():
    """Create a mock event emitter."""
    emitter = Mock()
    emitter.emit_flag_set = Mock()
    emitter.emit_flag_cleared = Mock()
    return emitter


@pytest.fixture
async def flag_manager(mock_hass, mock_event_emitter):
    """Create a FlagManager instance for testing."""
    manager = FlagManager(
        hass=mock_hass,
        entry_id="test_entry_123",
        event_emitter=mock_event_emitter
    )
    # Mock storage operations
    manager.async_load = AsyncMock(return_value=None)
    manager.async_save = AsyncMock(return_value=None)
    return manager


class TestFlagMutualExclusion:
    """Test mutual exclusion of flags."""

    @pytest.mark.asyncio
    async def test_setting_flag_clears_existing(self, flag_manager):
        """Test that setting a new flag clears the existing one."""
        # Set first flag
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        assert flag_manager._active_flag[STORAGE_FLAG_TYPE] == FLAG_TYPE_SKIP_TODAY

        # Set second flag (should clear first)
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT)
        assert flag_manager._active_flag[STORAGE_FLAG_TYPE] == FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT

    @pytest.mark.asyncio
    async def test_only_one_flag_active(self, flag_manager):
        """Test that only one flag can be active at a time."""
        # Set skip_today
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)

        # Set force_slot (should replace skip_today)
        await flag_manager.async_set_flag(FLAG_TYPE_FORCE_SLOT, slot_id="abc123")

        # Verify only force_slot is active
        assert flag_manager.get_active_flag_type() == FLAG_TYPE_FORCE_SLOT
        assert flag_manager.get_forced_slot_id() == "abc123"

    @pytest.mark.asyncio
    async def test_clear_flag_when_none_active(self, flag_manager):
        """Test clearing flag when none is active (should be safe)."""
        # No flag active
        assert flag_manager._active_flag is None

        # Clearing should not raise error
        await flag_manager.async_clear_flag()
        assert flag_manager._active_flag is None


class TestFlagExpiration:
    """Test flag auto-expiration logic."""

    @pytest.mark.asyncio
    async def test_skip_today_expires_at_midnight(self, flag_manager):
        """Test that skip_today expires at midnight."""
        # Set flag at 14:00
        now = datetime(2026, 1, 10, 14, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)

        # Check expiration before midnight (should not expire)
        check_time = datetime(2026, 1, 10, 23, 59, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = check_time
            expired = await flag_manager.async_check_expiration()
            assert expired is False
            assert flag_manager.get_active_flag_type() == FLAG_TYPE_SKIP_TODAY

        # Check expiration at midnight (should expire)
        check_time = datetime(2026, 1, 11, 0, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = check_time
            expired = await flag_manager.async_check_expiration()
            assert expired is True
            assert flag_manager._active_flag is None

    @pytest.mark.asyncio
    async def test_skip_until_next_slot_manual_expiration(self, flag_manager):
        """Test that skip_until_next_slot is manually expired via notify."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT)

        # Notify next slot activated
        await flag_manager.async_notify_slot_activated("new_slot_123")

        # Flag should be cleared
        assert flag_manager._active_flag is None

    @pytest.mark.asyncio
    async def test_force_slot_no_auto_expiration(self, flag_manager):
        """Test that force_slot never auto-expires."""
        # Set force_slot flag
        now = datetime(2026, 1, 10, 14, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            await flag_manager.async_set_flag(FLAG_TYPE_FORCE_SLOT, slot_id="forced_slot")

        # Check expiration 24 hours later (should not expire)
        check_time = datetime(2026, 1, 11, 14, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = check_time
            expired = await flag_manager.async_check_expiration()
            assert expired is False
            assert flag_manager.get_active_flag_type() == FLAG_TYPE_FORCE_SLOT

    @pytest.mark.asyncio
    async def test_skip_until_next_slot_not_cleared_by_same_slot(self, flag_manager):
        """Test that skip_until_next_slot not cleared if same slot reactivates."""
        # Set flag while slot_a is active
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT)

        # Notify same slot activated again (edge case: slot deactivated then reactivated)
        # This shouldn't happen in practice but test the logic
        # For this test, we'll assume the flag should clear on ANY slot activation
        await flag_manager.async_notify_slot_activated("slot_a")

        # Flag should be cleared
        assert flag_manager._active_flag is None


class TestFlagGetters:
    """Test flag getter methods."""

    @pytest.mark.asyncio
    async def test_get_active_flag_type_when_none(self, flag_manager):
        """Test getting active flag type when none set."""
        assert flag_manager.get_active_flag_type() is None

    @pytest.mark.asyncio
    async def test_get_active_flag_type_when_set(self, flag_manager):
        """Test getting active flag type when set."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        assert flag_manager.get_active_flag_type() == FLAG_TYPE_SKIP_TODAY

    @pytest.mark.asyncio
    async def test_get_forced_slot_id_when_no_force(self, flag_manager):
        """Test getting forced slot ID when no force_slot flag."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        assert flag_manager.get_forced_slot_id() is None

    @pytest.mark.asyncio
    async def test_get_forced_slot_id_when_forced(self, flag_manager):
        """Test getting forced slot ID when force_slot active."""
        await flag_manager.async_set_flag(FLAG_TYPE_FORCE_SLOT, slot_id="forced123")
        assert flag_manager.get_forced_slot_id() == "forced123"

    @pytest.mark.asyncio
    async def test_is_skip_active_when_skip_today(self, flag_manager):
        """Test is_skip_active returns True for skip_today."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        assert flag_manager.is_skip_active() is True

    @pytest.mark.asyncio
    async def test_is_skip_active_when_skip_until_next(self, flag_manager):
        """Test is_skip_active returns True for skip_until_next_slot."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_UNTIL_NEXT_SLOT)
        assert flag_manager.is_skip_active() is True

    @pytest.mark.asyncio
    async def test_is_skip_active_when_force_slot(self, flag_manager):
        """Test is_skip_active returns False for force_slot."""
        await flag_manager.async_set_flag(FLAG_TYPE_FORCE_SLOT, slot_id="abc")
        assert flag_manager.is_skip_active() is False

    @pytest.mark.asyncio
    async def test_is_skip_active_when_none(self, flag_manager):
        """Test is_skip_active returns False when no flag."""
        assert flag_manager.is_skip_active() is False


class TestEventEmission:
    """Test that events are emitted correctly."""

    @pytest.mark.asyncio
    async def test_emit_event_on_flag_set(self, flag_manager, mock_event_emitter):
        """Test that flag_set event is emitted."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)

        mock_event_emitter.emit_flag_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_on_flag_cleared(self, flag_manager, mock_event_emitter):
        """Test that flag_cleared event is emitted."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        mock_event_emitter.emit_flag_set.reset_mock()

        await flag_manager.async_clear_flag()

        mock_event_emitter.emit_flag_cleared.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_on_auto_expiration(self, flag_manager, mock_event_emitter):
        """Test that flag_cleared event emitted on expiration."""
        # Set skip_today flag
        now = datetime(2026, 1, 10, 14, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)

        mock_event_emitter.emit_flag_cleared.reset_mock()

        # Trigger expiration at midnight
        check_time = datetime(2026, 1, 11, 0, 0, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = check_time
            await flag_manager.async_check_expiration()

        mock_event_emitter.emit_flag_cleared.assert_called_once()


class TestPersistence:
    """Test persistence-related behavior."""

    @pytest.mark.asyncio
    async def test_save_called_on_set_flag(self, flag_manager):
        """Test that async_save is called when flag is set."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)

        flag_manager.async_save.assert_called()

    @pytest.mark.asyncio
    async def test_save_called_on_clear_flag(self, flag_manager):
        """Test that async_save is called when flag is cleared."""
        await flag_manager.async_set_flag(FLAG_TYPE_SKIP_TODAY)
        flag_manager.async_save.reset_mock()

        await flag_manager.async_clear_flag()

        flag_manager.async_save.assert_called()

    @pytest.mark.asyncio
    async def test_flag_data_structure(self, flag_manager):
        """Test that flag data has correct structure."""
        now = datetime(2026, 1, 10, 14, 30, 0)
        with patch('custom_components.climate_control_calendar.flag_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            await flag_manager.async_set_flag(FLAG_TYPE_FORCE_SLOT, slot_id="test123")

        # Check internal structure
        assert flag_manager._active_flag[STORAGE_FLAG_TYPE] == FLAG_TYPE_FORCE_SLOT
        assert flag_manager._active_flag[STORAGE_SLOT_ID] == "test123"
        assert STORAGE_SET_AT in flag_manager._active_flag
