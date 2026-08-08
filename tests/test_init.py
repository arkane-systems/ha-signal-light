"""Tests for the integration's setup/unload lifecycle and service schemas."""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.signal_light import (
    CLEAR_ACCENT_SCHEMA,
    CLEAR_SIGNAL_SCHEMA,
    SET_ACCENT_SCHEMA,
    SET_SIGNAL_SCHEMA,
)
from custom_components.signal_light.const import (
    DATA_COORDINATOR,
    DEFAULT_PRIORITY,
    DOMAIN,
)
from custom_components.signal_light.coordinator import SignalLightCoordinator

# ── Voluptuous schema validation (pure) ──────────────────────────────────────


def test_set_signal_schema_requires_signal_name() -> None:
    with pytest.raises(vol.Invalid):
        SET_SIGNAL_SCHEMA({})


def test_set_signal_schema_applies_default_priority() -> None:
    result = SET_SIGNAL_SCHEMA({"signal_name": "alarm"})
    assert result["priority"] == DEFAULT_PRIORITY


def test_set_signal_schema_rejects_invalid_priority_type() -> None:
    with pytest.raises(vol.Invalid):
        SET_SIGNAL_SCHEMA({"signal_name": "alarm", "priority": "not-a-number"})


def test_set_signal_schema_rejects_priority_below_minimum() -> None:
    with pytest.raises(vol.Invalid):
        SET_SIGNAL_SCHEMA({"signal_name": "alarm", "priority": 0})


def test_clear_signal_schema_requires_signal_name() -> None:
    with pytest.raises(vol.Invalid):
        CLEAR_SIGNAL_SCHEMA({})
    assert CLEAR_SIGNAL_SCHEMA({"signal_name": "alarm"}) == {"signal_name": "alarm"}


def test_set_accent_schema_requires_accent_name() -> None:
    with pytest.raises(vol.Invalid):
        SET_ACCENT_SCHEMA({})


def test_set_accent_schema_applies_default_priority() -> None:
    result = SET_ACCENT_SCHEMA({"accent_name": "mood"})
    assert result["priority"] == DEFAULT_PRIORITY


def test_clear_accent_schema_requires_accent_name() -> None:
    with pytest.raises(vol.Invalid):
        CLEAR_ACCENT_SCHEMA({})
    assert CLEAR_ACCENT_SCHEMA({"accent_name": "mood"}) == {"accent_name": "mood"}


# ── Setup/unload lifecycle (needs real hass) ─────────────────────────────────


async def test_setup_entry_creates_coordinator_and_forwards_platforms(
    hass, mock_config_entry, light_service_calls
) -> None:
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id][DATA_COORDINATOR]
    assert isinstance(coordinator, SignalLightCoordinator)

    entity_ids = hass.states.async_entity_ids()
    assert any(eid.startswith("light.") and eid != coordinator.underlying_entity_id for eid in entity_ids)
    assert any(eid.startswith("sensor.") for eid in entity_ids)


async def test_unload_entry_cleans_up_hass_data(
    hass, mock_config_entry, light_service_calls
) -> None:
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
