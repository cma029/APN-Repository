from typing import List
from registry import REG
from vbf_object import VBF


def compute_all_invariants(vbf_object: VBF) -> None:
    all_invariants = [
        "odds", 
        "odws",
        "delta_rank", 
        "gamma_rank",
        "algebraic_degree",
        "is_quadratic",
        "is_apn",
        "is_monomial",
        "k_to_1", 
        "diff_uni"
    ]

    for key in all_invariants:
        compute_missing(vbf_object, key)

    reorder_invariants(vbf_object)


def reorder_invariants(vbf_object: VBF) -> None:
    # Reorders the vbf_object.invariants dictionary into a preferred display order.
    desired_order = [
        "odds", 
        "odws",
        "delta_rank", 
        "gamma_rank",
        "algebraic_degree",
        "is_quadratic",
        "is_apn",
        "is_monomial",
        "k_to_1", 
        "diff_uni"
    ]

    old_map = vbf_object.invariants
    new_map = {}

    for key in desired_order:
        if key in old_map:
            new_map[key] = old_map[key]

    # Append leftover keys at the end (if any).
    for leftover_key in old_map:
        if leftover_key not in new_map:
            new_map[leftover_key] = old_map[leftover_key]

    vbf_object.invariants = new_map


def compute_selected(vbf_object: VBF, invariants_list: List[str]) -> None:
    for invariant_name in invariants_list:
        compute_missing(vbf_object, invariant_name)

    reorder_invariants(vbf_object)


def compute_missing(vbf_object: VBF, invariant_name: str) -> None:
    if invariant_name in vbf_object.invariants:
        return

    aggregator_function = REG.get("invariant", invariant_name)
    aggregator_function(vbf_object)