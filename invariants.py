from __future__ import annotations
import importlib
import pkgutil
from typing import Any, Dict, Iterable
from registry import REG


try:
    # Rank-based invariants (Δ-rank / Γ-rank).
    from computations.rank import delta_rank as _imp_delta_rank
    from computations.rank import gamma_rank as _imp_gamma_rank
    # Ortho-derivative spectra invariants (ODDS / ODWS).
    from computations.spectra import od_differential_spectrum as _imp_odds
    from computations.spectra import od_walsh_spectrum as _imp_odws
    # Other invariants.
    import c_invariants_bindings as _imp_c_invariants
except Exception:
    pass


def _autoload_custom_invariants() -> None:
    # Auto-import every module under computations/invariants/*
    try:
        import computations.invariants as invpkg  # Package with user-added invariants.
    except Exception:
        return  # Package not present — nothing to autoload.

    for _, name, _ in pkgutil.iter_modules(invpkg.__path__):
        mod_name = f"{invpkg.__name__}.{name}"
        try:
            importlib.import_module(mod_name)
        except Exception as error:
            print(f"[WARNING] Could not import invariant module '{mod_name}': {error}")


def compute_all_invariants(vbf) -> None:
    # Compute all registered invariants on the given VBF object.
    _autoload_custom_invariants()

    # Pull all registered invariant keys.
    reg_keys: Iterable[str] = REG.keys("invariant")

    # First a preferred order, then append the rest.
    preferred_order = [
        "odds",
        "odws",
        "delta_rank",
        "gamma_rank",
        "algebraic_degree",
        "is_quadratic",
        "is_apn",
        "diff_uni",
        "is_monomial",
        "k_to_1",
        "citation",
    ]

    reg_keys_set = set(reg_keys)
    ordered: list[str] = [key for key in preferred_order if key in reg_keys_set]
    leftovers = sorted(key for key in reg_keys_set if key not in ordered)
    ordered.extend(leftovers)

    # Compute missing invariants only. Skip those already present.
    vbf.invariants = vbf.invariants or {}
    for key in ordered:
        if key in vbf.invariants:
            continue
        try:
            aggregator = REG.get("invariant", key)
        except Exception as error:
            print(f"[WARNING] invariant '{key}' not found in REG: {error}")
            continue

        try:
            aggregator(vbf)  # Aggregator mutates vbf.invariants in place.
        except Exception as error:
            print(f"[WARNING] invariant '{key}' failed: {error}")


def reorder_invariants(vbf) -> None:
    # Reorders the vbf_object.invariants dictionary into a preferred display order.
    invariants: Dict[str, Any] = vbf.invariants or {}
    if not invariants:
        return

    preferred_order = [
        "odds",
        "odws",
        "delta_rank",
        "gamma_rank",
        "algebraic_degree",
        "is_quadratic",
        "is_apn",
        "diff_uni",
        "is_monomial",
        "k_to_1",
        "citation",
    ]

    keys = list(invariants.keys())
    seen = set()
    ordered_keys = [key for key in preferred_order if key in invariants]
    seen.update(ordered_keys)
    ordered_keys.extend(sorted(key for key in keys if key not in seen))

    # Rebuild dictionary in this order.
    vbf.invariants = {key: invariants[key] for key in ordered_keys}