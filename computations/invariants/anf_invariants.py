from registry import REG
from vbf_object import VBF
from c_invariants_bindings import (
    create_function_from_truth_table,
    create_function_from_truth_table_and_poly,
    destroy_function,
    function_algebraic_degree,
    function_is_monomial,
    function_is_quadratic
)
from computations.poly_parse_utils import parse_irreducible_poly_str

@REG.register("invariant", "anf_invariants")
def anf_invariants(vbf: VBF) -> None:
    """
    Aggregator that calls C++ routines and computes:
    algebraic_degree, is_monomial and is_quadratic.
    """
    # Check if already computed.
    needed = [
        "algebraic_degree",
        "is_monomial",
        "is_quadratic",
    ]
    if all(key in vbf.invariants for key in needed):
        return
    
    # Build the function pointer once from the truth table.
    representation = vbf.get_truth_table()
    tt_values = representation.truth_table
    if not vbf.irr_poly.strip():
        func_ptr = create_function_from_truth_table(tt_values)
    else:
        poly_bits = parse_irreducible_poly_str(vbf.irr_poly.strip())
        func_ptr = create_function_from_truth_table_and_poly(tt_values, poly_bits)

    try:
        # All three calls in a single pass.
        degree_value = function_algebraic_degree(func_ptr)
        monomial_flag = function_is_monomial(func_ptr)
        quadratic_flag = function_is_quadratic(func_ptr)
    finally:
        destroy_function(func_ptr)

    vbf.invariants.setdefault("algebraic_degree", degree_value)
    vbf.invariants.setdefault("is_monomial", bool(monomial_flag))
    vbf.invariants.setdefault("is_quadratic", bool(quadratic_flag))