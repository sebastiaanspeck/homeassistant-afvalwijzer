"""Tests for deprecated collectors."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.afvalwijzer import async_setup_entry
from custom_components.afvalwijzer.config_flow import (
    ALL_COLLECTORS,
    COLLECTOR_CHOICES,
    _collector_selector,
    _reconfigure_schema_for,
    _resolve_collector,
)
from custom_components.afvalwijzer.const.const import (
    COLLECTOR_LABELS,
    CONF_COLLECTOR,
    DEPRECATED_COLLECTORS,
    SENSOR_COLLECTORS_OPZET,
)
from custom_components.afvalwijzer.const.municipalities import MUNICIPALITY_COLLECTORS


def test_deprecated_collectors_are_known_and_replaced_by_a_current_one():
    """Old and new collector exist, and a replacement is never deprecated itself."""
    for old, new in DEPRECATED_COLLECTORS.items():
        assert old in ALL_COLLECTORS
        assert new in ALL_COLLECTORS
        assert new not in DEPRECATED_COLLECTORS


def test_an_alias_uses_the_same_url_as_its_replacement():
    """Afvalstoffendienstkalender and suez are the same provider as their replacement."""
    assert (
        SENSOR_COLLECTORS_OPZET["afvalstoffendienstkalender"]
        == SENSOR_COLLECTORS_OPZET["afvalstoffendienst"]
    )
    assert SENSOR_COLLECTORS_OPZET["suez"] == SENSOR_COLLECTORS_OPZET["prezero"]


def test_no_municipality_points_to_a_deprecated_collector():
    """Municipality search never offers a deprecated collector."""
    assert set(MUNICIPALITY_COLLECTORS.values()).isdisjoint(DEPRECATED_COLLECTORS)


def test_deprecated_collectors_are_not_offered_for_new_setups():
    """The dropdown lists the replacement but not the deprecated collector."""
    assert "Suez" not in COLLECTOR_CHOICES
    assert "PreZero" in COLLECTOR_CHOICES
    assert "Westland" not in COLLECTOR_CHOICES
    assert "HVC" in COLLECTOR_CHOICES
    assert "Afvalstoffendienst kalender" not in COLLECTOR_CHOICES
    assert "Afvalstoffendienst" in COLLECTOR_CHOICES


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("suez", "prezero"),
        ("Suez", "prezero"),
        ("westland", "hvc"),
        ("Westland", "hvc"),
        ("afvalstoffendienstkalender", "afvalstoffendienst"),
        ("Afvalstoffendienst kalender", "afvalstoffendienst"),
        ("prezero", "prezero"),
    ],
)
def test_choosing_a_deprecated_collector_gives_its_replacement(choice, expected):
    """A deprecated collector resolves to its replacement."""
    assert _resolve_collector(choice) == expected


def test_a_deprecated_collector_in_use_is_kept():
    """Reconfiguring without changing the collector keeps the old key."""
    assert _resolve_collector("Suez", keep="suez") == "suez"
    assert _resolve_collector("suez", keep="suez") == "suez"
    assert _resolve_collector("PreZero", keep="suez") == "prezero"
    assert _resolve_collector("Suez", keep="prezero") == "prezero"


def test_reconfigure_lists_the_deprecated_collector_in_use():
    """Only the deprecated collector that is in use stays in the reconfigure dropdown."""
    in_use = {o["value"] for o in _collector_selector("suez").config["options"]}
    other = {o["value"] for o in _collector_selector("omrin").config["options"]}

    assert COLLECTOR_LABELS["suez"] in in_use
    assert COLLECTOR_LABELS["suez"] not in other


def test_reconfigure_is_prefilled_with_the_deprecated_collector_in_use():
    """The entry's own collector is shown, so submitting the form doesn't force a switch."""
    schema = _reconfigure_schema_for({CONF_COLLECTOR: "suez"})

    result = schema({"postal_code": "1234AB", "house_number": "1"})

    assert result[CONF_COLLECTOR] == "Suez"


@pytest.mark.parametrize(
    ("collector", "warned"),
    [("suez", True), ("prezero", False)],
)
async def test_setup_warns_about_a_deprecated_collector(collector, warned, caplog):
    """Setting up an entry with a deprecated collector logs a warning."""
    entry = MagicMock()
    entry.data = {CONF_COLLECTOR: collector}
    entry.options = {}
    hass = MagicMock()

    with (
        patch("custom_components.afvalwijzer._skip_runtime_setup", return_value=False),
        patch(
            "custom_components.afvalwijzer._migrate_options_if_needed",
            side_effect=RuntimeError("stop after the warning"),
        ),
        pytest.raises(RuntimeError),
    ):
        await async_setup_entry(hass, entry)

    assert ("is deprecated" in caplog.text) is warned
