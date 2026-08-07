"""Home Assistant integration setup for Accent & Signal Light.

This module contains the two entry-points that HA calls when managing a config
entry for this integration:

* :func:`async_setup_entry` — called when HA loads the entry (startup or after
  the user adds it via the UI).  Creates the coordinator, stores it in
  ``hass.data``, forwards setup to each platform, and registers the four
  domain-level services.

* :func:`async_unload_entry` — called when the user removes the entry.  Tears
  down the platforms and removes the coordinator.

Services registered here
------------------------
All four services are *entity services* registered on the ``light`` platform so
that HA automatically routes a service call to the correct coordinator based on
the ``entity_id`` (or ``device_id``) supplied by the caller.  Internally they
delegate to methods on :class:`~signal_light.coordinator.SignalLightCoordinator`.

``signal_light.set_signal(entity_id, signal_name, priority, …light attrs…)``
    Add or update a signal in the priority queue.

``signal_light.clear_signal(entity_id, signal_name)``
    Remove a signal from the priority queue.

``signal_light.set_accent(entity_id, accent_name, priority, …light attrs…)``
    Add or update an accent in the priority stack.

``signal_light.clear_accent(entity_id, accent_name)``
    Remove an accent from the priority stack.
"""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_ACCENT_NAME,
    ATTR_PRIORITY,
    ATTR_SIGNAL_NAME,
    DATA_COORDINATOR,
    DEFAULT_PRIORITY,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_ACCENT,
    SERVICE_CLEAR_SIGNAL,
    SERVICE_SET_ACCENT,
    SERVICE_SET_SIGNAL,
)
from .coordinator import SignalLightCoordinator

_LOGGER = logging.getLogger(__name__)

# ── Voluptuous schema shared by set_signal / set_accent ──────────────────────
# These are the light-attribute fields we accept in addition to the mandatory
# name and priority fields.  They mirror the kwargs accepted by light.turn_on
# so that callers can use any standard light parameter.

_LIGHT_ATTR_SCHEMA = {
    vol.Optional(ATTR_BRIGHTNESS):        vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional(ATTR_BRIGHTNESS_PCT):    vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
    vol.Optional(ATTR_COLOR_NAME):        cv.string,
    vol.Optional(ATTR_COLOR_TEMP_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
    vol.Optional(ATTR_HS_COLOR): vol.All(
        list,
        vol.ExactSequence([
            vol.All(vol.Coerce(float), vol.Range(min=0, max=360)),
            vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        ]),
    ),
    vol.Optional(ATTR_RGB_COLOR): vol.All(
        list,
        vol.ExactSequence([
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        ]),
    ),
    vol.Optional(ATTR_RGBW_COLOR): vol.All(
        list,
        vol.ExactSequence([
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        ]),
    ),
    vol.Optional(ATTR_RGBWW_COLOR): vol.All(
        list,
        vol.ExactSequence([
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        ]),
    ),
    vol.Optional(ATTR_XY_COLOR): vol.All(
        list,
        vol.ExactSequence([
            vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
            vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        ]),
    ),
    vol.Optional(ATTR_EFFECT):     cv.string,
    vol.Optional(ATTR_TRANSITION): vol.All(vol.Coerce(float), vol.Range(min=0)),
}

# Schema for set_signal — mandatory: signal_name + priority; optional: any
# standard light attribute.
SET_SIGNAL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SIGNAL_NAME): cv.string,
        vol.Optional(ATTR_PRIORITY, default=DEFAULT_PRIORITY): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        **_LIGHT_ATTR_SCHEMA,
    }
)

# Schema for clear_signal — only the signal name is required.
CLEAR_SIGNAL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SIGNAL_NAME): cv.string,
    }
)

# Schema for set_accent — same shape as set_signal.
SET_ACCENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCENT_NAME): cv.string,
        vol.Optional(ATTR_PRIORITY, default=DEFAULT_PRIORITY): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        **_LIGHT_ATTR_SCHEMA,
    }
)

# Schema for clear_accent — only the accent name is required.
CLEAR_ACCENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCENT_NAME): cv.string,
    }
)

# ── Integration lifecycle ──────────────────────────────────────────────────────


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Accent & Signal Light instance from a config entry.

    Creates the :class:`~signal_light.coordinator.SignalLightCoordinator` for
    this entry, stores it in ``hass.data``, and forwards setup to all
    platforms.  The four domain services are registered on the first call and
    are no-ops on subsequent calls (services are global, not per-entry).

    Args:
        hass:  The Home Assistant instance.
        entry: The config entry being loaded.

    Returns:
        True on success.
    """
    hass.data.setdefault(DOMAIN, {})

    # Create the coordinator for this config entry.
    coordinator = SignalLightCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = {DATA_COORDINATOR: coordinator}

    # Forward to the light and sensor platforms.
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.LIGHT, Platform.SENSOR]
    )

    _LOGGER.debug("Accent & Signal Light entry loaded: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Accent & Signal Light config entry.

    Unloads all platforms and removes the coordinator from ``hass.data``.

    Args:
        hass:  The Home Assistant instance.
        entry: The config entry being unloaded.

    Returns:
        True if all platforms unloaded successfully.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.LIGHT, Platform.SENSOR]
    )

    if unload_ok:
        coordinator: SignalLightCoordinator = hass.data[DOMAIN][entry.entry_id][
            DATA_COORDINATOR
        ]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.debug("Accent & Signal Light entry unloaded: %s (ok=%s)", entry.entry_id, unload_ok)
    return unload_ok
