"""Checker for enforcing extended ``ConfigEntry`` aliases over the bare type.

When an integration defines a typed ``ConfigEntry`` alias (e.g.
``type FooConfigEntry = ConfigEntry[FooData]``), other modules in the same
integration should use that alias in type annotations instead of the bare
``ConfigEntry``.  Using the extended alias propagates the ``runtime_data``
type information and keeps the integration consistent.
"""

from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter

from pylint_home_assistant.helpers.integration import get_extended_config_entry_aliases
from pylint_home_assistant.helpers.module_info import parse_module


class HassEnforceExtendedConfigEntryChecker(BaseChecker):
    """Checker for extended ConfigEntry usage in annotations."""

    name = "home_assistant_enforce_extended_config_entry"
    priority = -1
    msgs = {
        "W7423": (
            "Use the integration's extended ConfigEntry alias (%s) "
            "instead of the bare ConfigEntry in type annotations",
            "home-assistant-use-extended-config-entry",
            "Used when a module in an integration that defines a typed "
            "ConfigEntry alias (e.g. ``type FooConfigEntry = ConfigEntry[...]``) "
            "annotates a value with the bare ``ConfigEntry``.  The extended "
            "alias should be used so that ``entry.runtime_data`` is typed.",
        ),
    }
    options = ()

    def visit_module(self, node: nodes.Module) -> None:
        """Cache the extended alias names for the current module."""
        self._aliases: frozenset[str] = frozenset()
        self._enabled: bool = False

        parsed = parse_module(node.name)
        if parsed is None:
            return

        aliases = get_extended_config_entry_aliases(parsed.domain, node)
        if not aliases:
            return

        self._aliases = aliases
        self._enabled = True

    def visit_arguments(self, node: nodes.Arguments) -> None:
        """Check function argument annotations."""
        if not self._enabled:
            return
        for annotation in (*node.annotations, *node.kwonlyargs_annotations):
            self._check_annotation(annotation)
        if node.varargannotation is not None:
            self._check_annotation(node.varargannotation)
        if node.kwargannotation is not None:
            self._check_annotation(node.kwargannotation)

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        """Check function return annotations."""
        if not self._enabled:
            return
        self._check_annotation(node.returns)

    visit_asyncfunctiondef = visit_functiondef

    def visit_annassign(self, node: nodes.AnnAssign) -> None:
        """Check variable annotation assignments."""
        if not self._enabled:
            return
        self._check_annotation(node.annotation)

    def _check_annotation(self, annotation: nodes.NodeNG | None) -> None:
        """Flag any bare ``ConfigEntry`` reference inside *annotation*."""
        if annotation is None:
            return
        for ref in _find_config_entry_refs(annotation):
            self.add_message(
                "home-assistant-use-extended-config-entry",
                node=ref,
                args=(", ".join(sorted(self._aliases)),),
            )


def _find_config_entry_refs(node: nodes.NodeNG) -> list[nodes.Name]:
    """Yield all ``ConfigEntry`` ``Name`` nodes inside *node*."""
    refs: list[nodes.Name] = []
    _collect_refs(node, refs)
    return refs


def _collect_refs(node: nodes.NodeNG, refs: list[nodes.Name]) -> None:
    """Recurse through *node* collecting bare ``ConfigEntry`` references."""
    match node:
        case nodes.Name(name="ConfigEntry"):
            refs.append(node)
            return
        case nodes.Const() | nodes.Name():
            return
    for child in node.get_children():
        _collect_refs(child, refs)


def register(linter: PyLinter) -> None:
    """Register the checker."""
    linter.register_checker(HassEnforceExtendedConfigEntryChecker(linter))
