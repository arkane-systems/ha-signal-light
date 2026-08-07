"""Config flow for the Accent & Signal Light integration.

Guides the user through adding a new instance via the HA integrations UI.
The flow collects three pieces of information:

1. **Name** — a human-readable label for this instance (e.g. "Living Room
   Accent & Signal Light").  Defaults to the domain name; the user is free
   to change it.

2. **Underlying light entity** — the ``entity_id`` of the physical light (or
   light group) that this instance will control.

3. **Signal wake priority** — the minimum priority a signal must exceed to turn
   the light on while the base layer is off.

Validation
----------
* The supplied entity_id must belong to a currently-loaded entity in the
  ``light`` domain.
* Duplicate entries for the same underlying entity are rejected; only one
  instance may manage a given physical light.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_SIGNAL_WAKE_PRIORITY,
    CONF_UNDERLYING_ENTITY_ID,
    DEFAULT_SIGNAL_WAKE_PRIORITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────


def _get_light_entity_ids(hass: HomeAssistant) -> list[str]:
    """Return the entity_ids of all currently-loaded light entities."""
    registry = er.async_get(hass)
    return sorted(
        entry.entity_id
        for entry in registry.entities.values()
        if entry.domain == LIGHT_DOMAIN
    )


def _existing_underlying_ids(hass: HomeAssistant) -> set[str]:
    """Return the underlying entity_ids already claimed by existing entries."""
    return {
        entry.data[CONF_UNDERLYING_ENTITY_ID]
        for entry in hass.config_entries.async_entries(DOMAIN)
    }


# ── Config flow ───────────────────────────────────────────────────────────────


class SignalLightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Accent & Signal Light.

    Presents a single form that collects the name, underlying entity_id, and
    signal wake priority, then creates the config entry.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step shown when the user clicks 'Add integration'.

        When *user_input* is ``None`` (first visit) the form is rendered.
        When *user_input* is provided (form submitted) validation is run and,
        if successful, the config entry is created.

        Args:
            user_input: Data submitted by the user, or ``None`` on first render.

        Returns:
            A :class:`~homeassistant.data_entry_flow.FlowResult`.
        """
        errors: dict[str, str] = {}

        # Collect the entity_ids of available lights for the selector.
        light_entity_ids = _get_light_entity_ids(self.hass)

        if user_input is not None:
            entity_id: str = user_input[CONF_UNDERLYING_ENTITY_ID]

            # ── Validate ──────────────────────────────────────────────────────

            # 1. The chosen entity must be a light.
            if entity_id not in light_entity_ids:
                errors[CONF_UNDERLYING_ENTITY_ID] = "entity_not_found"

            # 2. No other instance already controls this entity.
            elif entity_id in _existing_underlying_ids(self.hass):
                errors[CONF_UNDERLYING_ENTITY_ID] = "already_configured"

            if not errors:
                # Derive a unique_id from the underlying entity so that HA can
                # detect if the user accidentally tries to add the same
                # physical light a second time.
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()

                _LOGGER.debug(
                    "Creating Accent & Signal Light entry: name=%r entity=%r",
                    user_input.get("name"), entity_id,
                )
                return self.async_create_entry(
                    title=user_input.get("name") or entity_id,
                    data={
                        CONF_UNDERLYING_ENTITY_ID: entity_id,
                        CONF_SIGNAL_WAKE_PRIORITY: user_input[
                            CONF_SIGNAL_WAKE_PRIORITY
                        ],
                    },
                )

        # ── Build the form schema ─────────────────────────────────────────────
        # Offer a friendly name field and a selector restricted to known lights.
        schema = vol.Schema(
            {
                vol.Optional("name", default=""): cv.string,
                vol.Optional(
                    CONF_SIGNAL_WAKE_PRIORITY,
                    default=DEFAULT_SIGNAL_WAKE_PRIORITY,
                ): vol.All(vol.Coerce(int), vol.Range(min=0)),
                vol.Required(CONF_UNDERLYING_ENTITY_ID): vol.In(light_entity_ids)
                if light_entity_ids
                else cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
