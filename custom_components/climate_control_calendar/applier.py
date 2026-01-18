"""Climate payload applier for Climate Control Calendar integration."""
import asyncio
import logging
from typing import Any

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_SWING_MODE,
    ATTR_TEMPERATURE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    PAYLOAD_TEMPERATURE,
    PAYLOAD_HVAC_MODE,
    PAYLOAD_PRESET_MODE,
    PAYLOAD_FAN_MODE,
    PAYLOAD_SWING_MODE,
    PAYLOAD_TARGET_TEMP_HIGH,
    PAYLOAD_TARGET_TEMP_LOW,
    PAYLOAD_HUMIDITY,
    PAYLOAD_AUX_HEAT,
)
from .events import EventEmitter
from .template_helper import render_climate_payload

_LOGGER = logging.getLogger(__name__)

# Retry configuration (Decision D017)
RETRY_DELAY_SECONDS = 1.0
MAX_RETRIES = 1


class ClimatePayloadApplier:
    """
    Applies climate payloads to devices.

    Decisions:
    - D016: Sequential application
    - D017: Continue on error with immediate retry
    """

    def __init__(
        self,
        hass: HomeAssistant,
        event_emitter: EventEmitter,
    ) -> None:
        """
        Initialize applier.

        Args:
            hass: Home Assistant instance
            event_emitter: Event emitter instance
        """
        self.hass = hass
        self.event_emitter = event_emitter

    async def apply_to_devices(
        self,
        climate_entities: list[str],
        payload: dict[str, Any],
        slot_id: str,
        slot_label: str,
    ) -> dict[str, Any]:
        """
        Apply climate payload to multiple devices sequentially.

        Decision D016: Sequential application.
        Decision D017: Continue on error with retry.

        Args:
            climate_entities: List of climate entity IDs
            payload: Climate payload to apply
            slot_id: Source slot ID
            slot_label: Source slot label

        Returns:
            Result summary with successes and failures
        """
        if not climate_entities:
            _LOGGER.warning("No climate entities to apply payload to")
            return {"total": 0, "succeeded": 0, "failed": 0, "results": []}

        if not payload:
            _LOGGER.warning("Empty payload, nothing to apply")
            return {"total": 0, "succeeded": 0, "failed": 0, "results": []}

        _LOGGER.info(
            "Applying payload from slot '%s' to %d devices",
            slot_label,
            len(climate_entities),
        )

        results = []
        succeeded = 0
        failed = 0

        # Sequential application (D016)
        for entity_id in climate_entities:
            result = await self._apply_to_single_device(
                entity_id=entity_id,
                payload=payload,
                slot_id=slot_id,
                slot_label=slot_label,
            )

            results.append(result)

            if result["success"]:
                succeeded += 1
            else:
                failed += 1

        summary = {
            "total": len(climate_entities),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

        _LOGGER.info(
            "Application complete: %d/%d succeeded",
            succeeded,
            len(climate_entities),
        )

        return summary

    async def _apply_to_single_device(
        self,
        entity_id: str,
        payload: dict[str, Any],
        slot_id: str,
        slot_label: str,
    ) -> dict[str, Any]:
        """
        Apply payload to single device with retry.

        Decision D017: Retry once on failure.

        Args:
            entity_id: Climate entity ID
            payload: Climate payload
            slot_id: Source slot ID
            slot_label: Source slot label

        Returns:
            Result dict with success/error info
        """
        attempt = 0
        last_error = None

        # Try up to MAX_RETRIES + 1 times (initial + retries)
        while attempt <= MAX_RETRIES:
            try:
                await self._execute_payload(entity_id, payload)

                # Success!
                self.event_emitter.emit_climate_applied(
                    climate_entity_id=entity_id,
                    slot_id=slot_id,
                    slot_label=slot_label,
                    payload=payload,
                    success=True,
                    error=None,
                )

                _LOGGER.info(
                    "Successfully applied payload to %s%s",
                    entity_id,
                    f" (attempt {attempt + 1})" if attempt > 0 else "",
                )

                return {
                    "entity_id": entity_id,
                    "success": True,
                    "attempts": attempt + 1,
                    "error": None,
                }

            except Exception as err:
                last_error = str(err)
                attempt += 1

                if attempt <= MAX_RETRIES:
                    # Retry after delay
                    _LOGGER.warning(
                        "Failed to apply to %s (attempt %d/%d): %s. Retrying in %ss...",
                        entity_id,
                        attempt,
                        MAX_RETRIES + 1,
                        err,
                        RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    # Final failure
                    _LOGGER.error(
                        "Failed to apply to %s after %d attempts: %s",
                        entity_id,
                        attempt,
                        err,
                    )

        # All retries exhausted
        self.event_emitter.emit_climate_applied(
            climate_entity_id=entity_id,
            slot_id=slot_id,
            slot_label=slot_label,
            payload=payload,
            success=False,
            error=last_error,
        )

        return {
            "entity_id": entity_id,
            "success": False,
            "attempts": MAX_RETRIES + 1,
            "error": last_error,
        }

    async def _execute_payload(
        self,
        entity_id: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Execute climate payload by calling appropriate services.

        Renders any Jinja2 templates in payload values before applying.

        Args:
            entity_id: Climate entity ID
            payload: Climate payload (may contain templates)

        Raises:
            HomeAssistantError: If service call fails
        """
        # Render templates in payload (if any)
        rendered_payload = render_climate_payload(self.hass, payload)

        _LOGGER.debug(
            "Applying payload to %s: original=%s, rendered=%s",
            entity_id,
            payload,
            rendered_payload,
        )

        # Apply temperature (range or single)
        # Priority: target_temp_high/low > temperature (for heat_cool mode)
        if PAYLOAD_TARGET_TEMP_HIGH in rendered_payload and PAYLOAD_TARGET_TEMP_LOW in rendered_payload:
            # Use temperature range (for heat_cool mode)
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    "target_temp_high": rendered_payload[PAYLOAD_TARGET_TEMP_HIGH],
                    "target_temp_low": rendered_payload[PAYLOAD_TARGET_TEMP_LOW],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set temperature range %s-%s°C on %s",
                rendered_payload[PAYLOAD_TARGET_TEMP_LOW],
                rendered_payload[PAYLOAD_TARGET_TEMP_HIGH],
                entity_id,
            )
        elif PAYLOAD_TEMPERATURE in rendered_payload:
            # Use single temperature
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_TEMPERATURE: rendered_payload[PAYLOAD_TEMPERATURE],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set temperature %s°C on %s",
                rendered_payload[PAYLOAD_TEMPERATURE],
                entity_id,
            )

        # Apply HVAC mode
        if PAYLOAD_HVAC_MODE in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_HVAC_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_HVAC_MODE: rendered_payload[PAYLOAD_HVAC_MODE],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set HVAC mode '%s' on %s",
                rendered_payload[PAYLOAD_HVAC_MODE],
                entity_id,
            )

        # Apply preset mode
        if PAYLOAD_PRESET_MODE in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_PRESET_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_PRESET_MODE: rendered_payload[PAYLOAD_PRESET_MODE],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set preset mode '%s' on %s",
                rendered_payload[PAYLOAD_PRESET_MODE],
                entity_id,
            )

        # Apply fan mode
        if PAYLOAD_FAN_MODE in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_FAN_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_FAN_MODE: rendered_payload[PAYLOAD_FAN_MODE],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set fan mode '%s' on %s",
                rendered_payload[PAYLOAD_FAN_MODE],
                entity_id,
            )

        # Apply swing mode
        if PAYLOAD_SWING_MODE in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_SWING_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_SWING_MODE: rendered_payload[PAYLOAD_SWING_MODE],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set swing mode '%s' on %s",
                rendered_payload[PAYLOAD_SWING_MODE],
                entity_id,
            )

        # Apply humidity
        if PAYLOAD_HUMIDITY in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_humidity",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "humidity": rendered_payload[PAYLOAD_HUMIDITY],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set humidity %s%% on %s",
                rendered_payload[PAYLOAD_HUMIDITY],
                entity_id,
            )

        # Apply auxiliary heat
        if PAYLOAD_AUX_HEAT in rendered_payload:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_aux_heat",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "aux_heat": rendered_payload[PAYLOAD_AUX_HEAT],
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set auxiliary heat %s on %s",
                "ON" if rendered_payload[PAYLOAD_AUX_HEAT] else "OFF",
                entity_id,
            )
