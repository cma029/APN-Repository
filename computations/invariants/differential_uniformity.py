from registry import REG
from vbf_object import VBF
from c_invariants_bindings import (
    create_function_from_truth_table,
    create_function_from_truth_table_and_poly,
    destroy_function,
    function_differential_uniformity
)
from computations.poly_parse_utils import parse_irreducible_poly_str

@REG.register("invariant", "diff_uni")
def differential_uniformity(vbf_object: VBF):
    # Computes the differential uniformity using the C++ routines.

    if "diff_uni" in vbf_object.invariants and "is_apn" in vbf_object.invariants:
        return vbf_object.invariants["diff_uni"]

    # Build a C function pointer handle from the VBF’s truth table.
    representation = vbf_object.get_truth_table()
    tt_values = representation.truth_table
    if not vbf_object.irr_poly.strip():
        func_ptr = create_function_from_truth_table(tt_values)
    else:
        poly_bits = parse_irreducible_poly_str(vbf_object.irr_poly.strip())
        func_ptr = create_function_from_truth_table_and_poly(tt_values, poly_bits)

    try:
        differential_uniformity = function_differential_uniformity(func_ptr)
    finally:
        destroy_function(func_ptr)

    # Store the differential uniformity integer in invariants["diff_uni"].
    vbf_object.invariants["diff_uni"] = differential_uniformity

    # Set is_apn based on differential uniformity == 2.
    if differential_uniformity == 2:
        vbf_object.invariants["is_apn"] = True
    else:
        vbf_object.invariants["is_apn"] = False

    return differential_uniformity