from registry import REG
from vbf_object import VBF
from c_invariants_bindings import (
    create_function_from_truth_table,
    create_function_from_truth_table_and_poly,
    destroy_function,
    function_k_to_1
)
from computations.poly_parse_utils import parse_irreducible_poly_str


@REG.register("invariant", "k_to_1")
def k_to_1(vbf: VBF) -> str:
    # Computes the uniform 'k-to-1' using the C++ routine.

    if "k_to_1" in vbf.invariants:
        return vbf.invariants["k_to_1"]

    # Build a function pointer from the truth table.
    representation = vbf.get_truth_table()
    tt_values = representation.truth_table

    if not vbf.irr_poly.strip():
        func_ptr = create_function_from_truth_table(tt_values)
    else:
        poly_bits = parse_irreducible_poly_str(vbf.irr_poly.strip())
        func_ptr = create_function_from_truth_table_and_poly(tt_values, poly_bits)

    try:
        k_val = function_k_to_1(func_ptr)
    finally:
        destroy_function(func_ptr)

    if k_val == -1:
        # If not uniformly k-to-1.
        vbf.invariants["k_to_1"] = ""
    else:
        vbf.invariants["k_to_1"] = f"{k_val}-to-1"

    return vbf.invariants["k_to_1"]