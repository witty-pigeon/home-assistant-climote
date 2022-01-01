"""Tests for the config flow."""
from unittest import mock
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries, data_entry_flow
from custom_components.climote.const import DOMAIN

from custom_components.climote import config_flow
from custom_components.climote.const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID


MOCK_CONFIG = {
    CONF_USERNAME: "climote@example.com",
    CONF_PASSWORD: "hunter2",
    CONF_DEVICE_ID: "12345"
}

@patch("custom_components.climote.config_flow.ClimoteService")
async def test_options_flow_add_account(m_climote, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.populate = AsyncMock()
    m_instance.zones = [
        { "id": "1", "name": "Zone 1" },
        { "id": "2", "name": "Zone 2" },
        { "id": "3", "name": "Zone 3" },
    ]
    m_climote.return_value = m_instance

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    assert result["flow_id"]
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

@patch("custom_components.climote.config_flow.ClimoteService")
async def test_options_with_no_zones(m_climote, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.populate = AsyncMock()
    m_instance.zones = []
    m_climote.return_value = m_instance

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    assert result["flow_id"]
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG
    )

    assert result2["type"] == "form"
