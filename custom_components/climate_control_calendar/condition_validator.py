"""Condition validation and evaluation for Climate Control Calendar.

This module provides utilities to validate and evaluate conditions on bindings,
allowing bindings to activate only when specific conditions are met.

Supported condition types:
- state: Check entity state
- numeric_state: Check numeric value above/below threshold
- time: Check time range and weekday
- template: Custom Jinja2 template condition
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

# Maximum number of conditions per binding (UI limit)
MAX_CONDITIONS_PER_BINDING = 5


def validate_condition_config(cond: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate a single condition configuration.

    Args:
        cond: Condition dict with 'type' and type-specific fields

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(cond, dict):
        return False, "Condition must be a dictionary"

    cond_type = cond.get("type") or cond.get("condition")
    if not cond_type:
        return False, "Condition must have 'type' or 'condition' field"

    # Validate based on type
    if cond_type == "state":
        return _validate_state_condition(cond)
    elif cond_type == "numeric_state":
        return _validate_numeric_state_condition(cond)
    elif cond_type == "time":
        return _validate_time_condition(cond)
    elif cond_type == "template":
        return _validate_template_condition(cond)
    else:
        return False, f"Unsupported condition type: {cond_type}"


def _validate_state_condition(cond: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate state condition."""
    if "entity_id" not in cond:
        return False, "state condition requires 'entity_id'"

    if "state" not in cond:
        return False, "state condition requires 'state'"

    return True, None


def _validate_numeric_state_condition(cond: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate numeric_state condition."""
    if "entity_id" not in cond:
        return False, "numeric_state condition requires 'entity_id'"

    has_above = "above" in cond
    has_below = "below" in cond

    if not has_above and not has_below:
        return False, "numeric_state condition requires at least 'above' or 'below'"

    # Validate numeric values
    if has_above:
        try:
            float(cond["above"])
        except (ValueError, TypeError):
            return False, "'above' must be a number"

    if has_below:
        try:
            float(cond["below"])
        except (ValueError, TypeError):
            return False, "'below' must be a number"

    return True, None


def _validate_time_condition(cond: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate time condition."""
    has_after = "after" in cond
    has_before = "before" in cond
    has_weekday = "weekday" in cond

    if not has_after and not has_before and not has_weekday:
        return False, "time condition requires at least 'after', 'before', or 'weekday'"

    # Basic validation (HA will do full validation at runtime)
    return True, None


def _validate_template_condition(cond: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate template condition."""
    if "value_template" not in cond:
        return False, "template condition requires 'value_template'"

    template_str = cond["value_template"]
    if not isinstance(template_str, str):
        return False, "'value_template' must be a string"

    if "{{" not in template_str or "}}" not in template_str:
        return False, "'value_template' must contain Jinja2 template markers ({{ }})"

    return True, None


async def check_conditions(
    hass: HomeAssistant,
    conditions: list[dict[str, Any]],
) -> bool:
    """Check if all conditions are met (AND logic).

    Args:
        hass: Home Assistant instance
        conditions: List of condition dicts

    Returns:
        True if all conditions pass, False otherwise

    Note:
        Uses Home Assistant's native condition validators for maximum compatibility.
        All conditions must pass (AND logic).
    """
    if not conditions:
        # No conditions = always pass
        return True

    try:
        # Normalize condition format for HA validator
        normalized_conditions = []
        for cond in conditions:
            # HA expects 'condition' key, but we use 'type' in UI
            normalized = cond.copy()
            if "type" in normalized and "condition" not in normalized:
                normalized["condition"] = normalized["type"]

            normalized_conditions.append(normalized)

        # Use HA's native condition checker
        # This handles all condition types and edge cases
        result = condition.async_from_config(
            hass, normalized_conditions
        )

        # Evaluate the condition
        return result(hass)

    except vol.Invalid as err:
        _LOGGER.error("Invalid condition configuration: %s", err)
        return False
    except Exception as err:
        _LOGGER.error("Error evaluating conditions: %s", err)
        return False


def format_condition_summary(cond: dict[str, Any]) -> str:
    """Format a condition as human-readable summary.

    Args:
        cond: Condition dict

    Returns:
        Human-readable string describing the condition
    """
    cond_type = cond.get("type") or cond.get("condition")

    if cond_type == "state":
        entity = cond.get("entity_id", "unknown")
        state = cond.get("state", "unknown")
        return f"State: {entity} = {state}"

    elif cond_type == "numeric_state":
        entity = cond.get("entity_id", "unknown")
        above = cond.get("above")
        below = cond.get("below")

        if above is not None and below is not None:
            return f"Numeric: {entity} between {above} and {below}"
        elif above is not None:
            return f"Numeric: {entity} > {above}"
        else:
            return f"Numeric: {entity} < {below}"

    elif cond_type == "time":
        parts = []
        if "after" in cond:
            parts.append(f"after {cond['after']}")
        if "before" in cond:
            parts.append(f"before {cond['before']}")
        if "weekday" in cond:
            weekdays = cond["weekday"]
            if isinstance(weekdays, list):
                parts.append(f"on {', '.join(weekdays)}")
            else:
                parts.append(f"on {weekdays}")

        return f"Time: {' and '.join(parts)}"

    elif cond_type == "template":
        template = cond.get("value_template", "")
        # Truncate long templates
        if len(template) > 50:
            template = template[:47] + "..."
        return f"Template: {template}"

    return f"Unknown condition type: {cond_type}"
