from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List
import importlib
import pkgutil

__all__ = ["REG", "Registry"]


class Registry:


    def __init__(self) -> None:
        # Example: _data["invariant"]["delta_rank"] for DeltaRankComputation.
        self._data: Dict[str, Dict[str, Any]] = defaultdict(dict)


    def register(self, category: str, key: str, object: Any | None = None) -> Any:
        category_low = category.lower()
        key_low = key.lower()

        def _decorator(target: Any) -> Any:
            self._data[category_low][key_low] = target
            return target

        return _decorator(object) if object is not None else _decorator
    

    # --------------------------------------------------------------------
    # Lookup helpers
    # --------------------------------------------------------------------

    def get(self, category: str, key: str) -> Any:
        # Return the registered object (raises KeyError if missing).
        return self._data[category.lower()][key.lower()]


    def list_keys(self, category: str) -> List[str]:
        # List all keys registered under *category*.
        return sorted(self._data[category.lower()])


    def keys(self, category: str) -> list[str]:
        # Return a sorted list of all registration keys in *category*.
        cat = category.lower()
        if cat not in self._data:
            return []
        return sorted(self._data[cat].keys())


# Global instance shared framework-wide.
REG = Registry()

# --------------------------------------------------------------------
# Automatic *plugin* discovery. Call REG.register(...) during import.
# --------------------------------------------------------------------

_PLUGIN_PACKAGES = [
    "computations.rank",
    "computations.spectra",
    "computations.equivalence",
    "computations.invariants",
]


def _import_submodules(package_name: str) -> None:
    # Recursively import packages and all their sub-modules.
    try:
        pkg = importlib.import_module(package_name)
    except ModuleNotFoundError:
        return

    pkg_path = getattr(pkg, "__path__", None)
    if not pkg_path:
        return

    for mod_info in pkgutil.walk_packages(pkg_path, package_name + "."):
        importlib.import_module(mod_info.name)


# Trigger the auto-load when registry.py is imported.
for _pkg in _PLUGIN_PACKAGES:
    _import_submodules(_pkg)