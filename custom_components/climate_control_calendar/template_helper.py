"""Template rendering support for climate payloads.

This module provides utilities to detect and render Jinja2 templates in climate
payload values, allowing dynamic values based on Home Assistant state.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)


def is_template(value: Any) -> bool:
    """Check if value is a Jinja2 template string.

    Args:
        value: Value to check

    Returns:
        True if value appears to be a template (contains {{ and }})
    """
    if not isinstance(value, str):
        return False
    return "{{" in value and "}}" in value


def render_template_value(
    hass: HomeAssistant,
    value: Any,
    field_name: str,
    expected_type: type | None = None,
) -> Any:
    """Render template if needed, otherwise return value as-is.

    Args:
        hass: Home Assistant instance
        value: Value to render (can be template string or static value)
        field_name: Name of field (for logging)
        expected_type: Expected return type (float, int, str, bool)

    Returns:
        Rendered value or original value on error

    Note:
        If template rendering fails, the original value is returned as fallback
        to prevent integration breaking on temporary template errors.
    """
    # If not a template, return value as-is
    if not is_template(value):
        return value

    try:
        # Render template
        template = Template(value, hass)
        rendered = template.async_render()

        # Convert to expected type
        if expected_type == float:
            result = float(rendered)
        elif expected_type == int:
            result = int(rendered)
        elif expected_type == str:
            result = str(rendered).strip()
        elif expected_type == bool:
            # Support various boolean representations
            result = str(rendered).lower() in ("true", "1", "on", "yes")
        else:
            result = rendered

        _LOGGER.debug(
            "Template rendered for %s: '%s' -> %s",
            field_name,
            value,
            result,
        )
        return result

    except (TemplateError, ValueError, TypeError) as err:
        _LOGGER.error(
            "Failed to render template for %s: '%s' (error: %s). Using fallback value.",
            field_name,
            value,
            err,
        )
        # Fallback: return original value (integration continues to work)
        return value


def render_climate_payload(
    hass: HomeAssistant,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Render all template values in a climate payload.

    Args:
        hass: Home Assistant instance
        payload: Climate payload dict (may contain templates)

    Returns:
        New dict with rendered values

    Note:
        Original payload is not modified. A new dict is returned.
    """
    if not payload:
        return {}

    rendered = {}

    # Mapping: field_name -> expected_type
    field_types = {
        "temperature": float,
        "target_temp_high": float,
        "target_temp_low": float,
        "humidity": int,
        "hvac_mode": str,
        "preset_mode": str,
        "fan_mode": str,
        "swing_mode": str,
        "aux_heat": bool,
    }

    for key, value in payload.items():
        if value is None:
            continue

        expected_type = field_types.get(key)
        rendered[key] = render_template_value(hass, value, key, expected_type)

    return rendered
