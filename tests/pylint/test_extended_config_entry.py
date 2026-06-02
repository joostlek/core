"""Tests for pylint hass_enforce_extended_config_entry plugin."""

from pathlib import Path

import astroid
from pylint.checkers import BaseChecker
from pylint.testutils.unittest_linter import UnittestLinter
from pylint.utils.ast_walker import ASTWalker
import pytest

from . import assert_no_messages


def _setup_integration(tmp_path: Path, domain: str, *, with_alias: bool) -> Path:
    """Create a fake integration directory and return the __init__.py path."""
    integration_dir = tmp_path / "homeassistant" / "components" / domain
    integration_dir.mkdir(parents=True)
    init_file = integration_dir / "__init__.py"
    if with_alias:
        init_file.write_text(
            "from homeassistant.config_entries import ConfigEntry\n"
            f"type {domain.title()}ConfigEntry = ConfigEntry[object]\n"
        )
    else:
        init_file.touch()
    return init_file


@pytest.mark.parametrize(
    ("code", "module_basename"),
    [
        pytest.param(
            """
async def async_setup_entry(hass: HomeAssistant, entry: FooConfigEntry) -> bool:
    return True
""",
            "__init__",
            id="uses_alias",
        ),
        pytest.param(
            """
type FooConfigEntry = ConfigEntry[object]
""",
            "__init__",
            id="alias_definition_itself",
        ),
        pytest.param(
            """
def make() -> int:
    entry: int = 1
    return entry
""",
            "sensor",
            id="no_config_entry_reference",
        ),
        pytest.param(
            """
def helper(entry):
    return entry
""",
            "sensor",
            id="no_annotations",
        ),
    ],
)
def test_enforce_extended_config_entry(
    linter: UnittestLinter,
    enforce_extended_config_entry_checker: BaseChecker,
    tmp_path: Path,
    code: str,
    module_basename: str,
) -> None:
    """Good test cases."""
    init_file = _setup_integration(tmp_path, "foo", with_alias=True)
    module_path = init_file.parent / f"{module_basename}.py"
    if module_basename != "__init__":
        module_path.write_text(code)

    module_name = "homeassistant.components.foo"
    if module_basename != "__init__":
        module_name = f"{module_name}.{module_basename}"

    root_node = astroid.parse(code, module_name)
    root_node.file = str(module_path)

    walker = ASTWalker(linter)
    walker.add_checker(enforce_extended_config_entry_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)


@pytest.mark.parametrize(
    ("code", "module_basename"),
    [
        pytest.param(
            """
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
""",
            "__init__",
            id="bare_in_init",
        ),
        pytest.param(
            """
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
""",
            "sensor",
            id="bare_in_platform",
        ),
        pytest.param(
            """
def get_entry() -> ConfigEntry:
    return None
""",
            "sensor",
            id="bare_in_return",
        ),
        pytest.param(
            """
entry: ConfigEntry = some_value
""",
            "sensor",
            id="bare_in_annassign",
        ),
        pytest.param(
            """
def get_entries() -> list[ConfigEntry]:
    return []
""",
            "sensor",
            id="bare_in_generic",
        ),
        pytest.param(
            """
def get_entries(entries: list[ConfigEntry] | None = None) -> None:
    return None
""",
            "sensor",
            id="bare_in_nested_generic",
        ),
    ],
)
def test_enforce_extended_config_entry_bad(
    linter: UnittestLinter,
    enforce_extended_config_entry_checker: BaseChecker,
    tmp_path: Path,
    code: str,
    module_basename: str,
) -> None:
    """Bad test cases."""
    init_file = _setup_integration(tmp_path, "foo", with_alias=True)
    module_path = init_file.parent / f"{module_basename}.py"
    if module_basename != "__init__":
        module_path.write_text(code)

    module_name = "homeassistant.components.foo"
    if module_basename != "__init__":
        module_name = f"{module_name}.{module_basename}"

    root_node = astroid.parse(code, module_name)
    root_node.file = str(module_path)

    walker = ASTWalker(linter)
    walker.add_checker(enforce_extended_config_entry_checker)

    walker.walk(root_node)
    messages = linter.release_messages()
    assert len(messages) == 1
    assert messages[0].msg_id == "home-assistant-use-extended-config-entry"


def test_no_alias_defined_does_not_flag(
    linter: UnittestLinter,
    enforce_extended_config_entry_checker: BaseChecker,
    tmp_path: Path,
) -> None:
    """Integrations without an extended ConfigEntry alias are not flagged."""
    init_file = _setup_integration(tmp_path, "legacy", with_alias=False)

    code = """
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
"""
    root_node = astroid.parse(code, "homeassistant.components.legacy")
    root_node.file = str(init_file)

    walker = ASTWalker(linter)
    walker.add_checker(enforce_extended_config_entry_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)


def test_outside_integration_does_not_flag(
    linter: UnittestLinter,
    enforce_extended_config_entry_checker: BaseChecker,
) -> None:
    """Modules outside the integration root are not flagged."""
    code = """
def setup(entry: ConfigEntry) -> None:
    return None
"""
    root_node = astroid.parse(code, "some.other.module")

    walker = ASTWalker(linter)
    walker.add_checker(enforce_extended_config_entry_checker)

    with assert_no_messages(linter):
        walker.walk(root_node)
