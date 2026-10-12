"""The slot's gear screen offers a Force Unload: ACE_SMART_UNLOAD TOOL=<n>
behind KlipperScreen's Accept/Cancel dialog, for a filament the driver has
no tool on record for. It took the place of the "Empty" material, which
Save never accepted. Imported with GTK and KlipperScreen stubbed out.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PANEL_PATH = Path(__file__).resolve().parent.parent / "KlipperScreen" / "acepro.py"


@pytest.fixture(scope="module")
def acepro():
    screen_panel = types.ModuleType("ks_includes.screen_panel")
    screen_panel.ScreenPanel = type("ScreenPanel", (), {})
    stubs = {
        "gi": MagicMock(),
        "gi.repository": MagicMock(),
        "ks_includes": MagicMock(),
        "ks_includes.screen_panel": screen_panel,
        "ks_includes.widgets": MagicMock(),
        "ks_includes.widgets.keypad": MagicMock(),
    }
    spec = importlib.util.spec_from_file_location("acepro_force_unload", PANEL_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


def make_panel(acepro):
    panel = acepro.Panel.__new__(acepro.Panel)
    panel._screen = MagicMock()
    return panel


def test_force_unload_asks_first_then_sends_the_printer_tool(acepro):
    panel = make_panel(acepro)

    panel.confirm_force_unload(None, 5)

    (widget, text, method, params), _ = panel._screen._confirm_send_action.call_args
    assert "T5" in text
    assert method == "printer.gcode.script"
    assert params == {"script": "ACE_SMART_UNLOAD TOOL=5"}


def test_empty_is_no_longer_a_selectable_material(acepro):
    panel = make_panel(acepro)

    options = panel.material_options()

    assert "Empty" not in options
    assert options == list(acepro.Panel.FILAMENT_TEMP_DEFAULTS.keys())
