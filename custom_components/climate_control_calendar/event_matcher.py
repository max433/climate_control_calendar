"""Event matching logic for binding resolution.

This module implements the pattern matching system that determines whether
a calendar event matches a binding rule. It supports multiple match types
that can be extended in the future.

Decision D032: Event-to-Slot Binding System
"""
from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)


class EventMatcher:
    """
    Matches calendar events against binding rules.

    Supports multiple match types:
    - summary: Exact match on event summary/title
    - summary_contains: Substring match (fuzzy)
    - regex: Regular expression pattern matching

    Future extensibility:
    - description: Match on event description
    - location: Match on event location
    - attributes: Match on custom attributes
    """

    # Supported match types
    MATCH_TYPE_SUMMARY = "summary"
    MATCH_TYPE_SUMMARY_CONTAINS = "summary_contains"
    MATCH_TYPE_REGEX = "regex"

    # Future match types (not yet implemented)
    MATCH_TYPE_DESCRIPTION = "description"
    MATCH_TYPE_LOCATION = "location"

    SUPPORTED_MATCH_TYPES = [
        MATCH_TYPE_SUMMARY,
        MATCH_TYPE_SUMMARY_CONTAINS,
        MATCH_TYPE_REGEX,
    ]

    @classmethod
    def matches(
        cls,
        match_config: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        """
        Check if an event matches a binding rule.

        Args:
            match_config: Match configuration containing:
                - type: Match type (summary, summary_contains, regex)
                - value: Pattern to match against
            event: Calendar event containing:
                - summary: Event title/summary
                - description: Event description (optional)
                - location: Event location (optional)

        Returns:
            True if event matches the pattern, False otherwise

        Examples:
            >>> match_config = {"type": "summary", "value": "Mattino"}
            >>> event = {"summary": "Mattino"}
            >>> EventMatcher.matches(match_config, event)
            True

            >>> match_config = {"type": "summary_contains", "value": "comfort"}
            >>> event = {"summary": "High comfort mode"}
            >>> EventMatcher.matches(match_config, event)
            True

            >>> match_config = {"type": "regex", "value": "^Work.*"}
            >>> event = {"summary": "Working from home"}
            >>> EventMatcher.matches(match_config, event)
            True
        """
        match_type = match_config.get("type")
        match_value = match_config.get("value")

        if not match_type or not match_value:
            _LOGGER.warning(
                "Invalid match config: missing type or value | config=%s",
                match_config,
            )
            return False

        if match_type not in cls.SUPPORTED_MATCH_TYPES:
            _LOGGER.warning(
                "Unsupported match type: %s | Supported: %s",
                match_type,
                cls.SUPPORTED_MATCH_TYPES,
            )
            return False

        # Dispatch to specific match method
        if match_type == cls.MATCH_TYPE_SUMMARY:
            return cls._match_summary_exact(match_value, event)
        elif match_type == cls.MATCH_TYPE_SUMMARY_CONTAINS:
            return cls._match_summary_contains(match_value, event)
        elif match_type == cls.MATCH_TYPE_REGEX:
            return cls._match_regex(match_value, event)

        return False

    @staticmethod
    def _match_summary_exact(pattern: str, event: dict[str, Any]) -> bool:
        """
        Exact match on event summary.

        Case-sensitive exact string comparison.

        Args:
            pattern: Expected summary value
            event: Calendar event

        Returns:
            True if summary matches exactly
        """
        event_summary = event.get("summary", "")
        return event_summary == pattern

    @staticmethod
    def _match_summary_contains(substring: str, event: dict[str, Any]) -> bool:
        """
        Substring match on event summary (fuzzy match).

        Case-insensitive substring search.

        Args:
            substring: Substring to search for
            event: Calendar event

        Returns:
            True if summary contains the substring
        """
        event_summary = event.get("summary", "")
        return substring.lower() in event_summary.lower()

    @staticmethod
    def _match_regex(pattern: str, event: dict[str, Any]) -> bool:
        """
        Regular expression match on event summary.

        Uses Python re.match() which matches from the beginning of the string.
        To match anywhere in the string, use pattern like ".*keyword.*"

        Args:
            pattern: Regular expression pattern
            event: Calendar event

        Returns:
            True if summary matches the regex pattern
        """
        event_summary = event.get("summary", "")

        try:
            return bool(re.match(pattern, event_summary))
        except re.error as err:
            _LOGGER.error(
                "Invalid regex pattern: %s | Error: %s",
                pattern,
                err,
            )
            return False

    @classmethod
    def validate_match_config(cls, match_config: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate a match configuration.

        Args:
            match_config: Match configuration to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if "type" not in match_config:
            return False, "Missing required field: type"

        if "value" not in match_config:
            return False, "Missing required field: value"

        match_type = match_config["type"]
        match_value = match_config["value"]

        # Check match type is supported
        if match_type not in cls.SUPPORTED_MATCH_TYPES:
            return False, f"Unsupported match type: {match_type}. Supported: {cls.SUPPORTED_MATCH_TYPES}"

        # Validate match value is not empty
        if not match_value or not str(match_value).strip():
            return False, "Match value cannot be empty"

        # Type-specific validation
        if match_type == cls.MATCH_TYPE_REGEX:
            # Validate regex pattern
            try:
                re.compile(match_value)
            except re.error as err:
                return False, f"Invalid regex pattern: {err}"

        return True, None


def matches_calendar(
    calendar_filter: str | list[str],
    calendar_id: str,
) -> bool:
    """
    Check if a calendar ID matches a calendar filter.

    Supports:
    - Wildcard "*" matches all calendars
    - Specific list of calendar IDs
    - Single calendar ID (as string or single-item list)

    Args:
        calendar_filter: Calendar filter (wildcard "*" or list of calendar IDs)
        calendar_id: Calendar entity ID to check

    Returns:
        True if calendar matches the filter

    Examples:
        >>> matches_calendar("*", "calendar.work")
        True

        >>> matches_calendar(["calendar.work"], "calendar.work")
        True

        >>> matches_calendar(["calendar.work", "calendar.home"], "calendar.home")
        True

        >>> matches_calendar(["calendar.work"], "calendar.vacation")
        False
    """
    # Wildcard matches all
    if calendar_filter == "*":
        return True

    # Convert single string to list
    if isinstance(calendar_filter, str):
        calendar_filter = [calendar_filter]

    # Check if calendar_id is in the list
    return calendar_id in calendar_filter
