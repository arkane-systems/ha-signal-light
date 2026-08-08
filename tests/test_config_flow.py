"""Tests for the Accent & Signal Light config flow."""

from __future__ import annotations

from homeassistant.data_entry_flow import FlowResultType

from custom_components.signal_light.const import (
    CONF_SIGNAL_WAKE_PRIORITY,
    CONF_UNDERLYING_ENTITY_ID,
    DEFAULT_SIGNAL_WAKE_PRIORITY,
    DOMAIN,
)
from custom_components.signal_light.config_flow import (
    _existing_underlying_ids,
    _get_light_entity_ids,
)

from .conftest import UNDERLYING_ENTITY_ID


async def test_user_step_shows_form_with_light_choices(hass, mock_underlying_light) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_step_creates_entry(hass, mock_underlying_light) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "My Signal Light",
            CONF_UNDERLYING_ENTITY_ID: mock_underlying_light,
            CONF_SIGNAL_WAKE_PRIORITY: DEFAULT_SIGNAL_WAKE_PRIORITY,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Signal Light"
    assert result["data"][CONF_UNDERLYING_ENTITY_ID] == mock_underlying_light
    assert result["data"][CONF_SIGNAL_WAKE_PRIORITY] == DEFAULT_SIGNAL_WAKE_PRIORITY


async def test_user_step_rejects_entity_not_a_light(hass) -> None:
    # No light entities registered, so the schema falls back to cv.string
    # and the manual "must be a known light" check in async_step_user runs.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "My Signal Light",
            CONF_UNDERLYING_ENTITY_ID: "light.not_a_real_light",
            CONF_SIGNAL_WAKE_PRIORITY: DEFAULT_SIGNAL_WAKE_PRIORITY,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_UNDERLYING_ENTITY_ID: "entity_not_found"}


async def test_user_step_rejects_already_configured_entity(
    hass, mock_config_entry
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Second Instance",
            CONF_UNDERLYING_ENTITY_ID: UNDERLYING_ENTITY_ID,
            CONF_SIGNAL_WAKE_PRIORITY: DEFAULT_SIGNAL_WAKE_PRIORITY,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_UNDERLYING_ENTITY_ID: "already_configured"}


# ── Module-level helper functions ────────────────────────────────────────────


def test_get_light_entity_ids_filters_non_light_domain(hass, mock_underlying_light) -> None:
    assert _get_light_entity_ids(hass) == [UNDERLYING_ENTITY_ID]


def test_existing_underlying_ids_reflects_configured_entries(
    hass, mock_config_entry
) -> None:
    assert _existing_underlying_ids(hass) == {UNDERLYING_ENTITY_ID}
