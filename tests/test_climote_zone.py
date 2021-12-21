"""Tests for the climote zone."""
from unittest.mock import AsyncMock, MagicMock

from custom_components.climote import ClimoteZone

async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    climote = MagicMock()
    climoteZone = ClimoteZone(climote, "1", "Living Room", 1)
    await climoteZone.async_update()

    expected = {}
    assert expected == climoteZone.attrs
    assert expected == climoteZone.device_state_attributes
    assert climoteZone.available is True


async def test_async_update_failed():
    """Tests a failed async_update."""
    github = MagicMock()
    github.getitem = AsyncMock(side_effect=GitHubException)

    sensor = GitHubRepoSensor(github, {"path": "homeassistant/core"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"path": "homeassistant/core"} == sensor.attrs
