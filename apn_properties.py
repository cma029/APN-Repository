# apn_properties.py
# Description: Provides functions to compute or update the properties of an APN object.

import galois
from apn_test import DifferentialUniformityComputer
from apn_is_quadratic import is_quadratic_apn
from collections import Counter

def compute_apn_properties(apn):
    # Computes and appends polynomial-related properties to an APN object.
    if hasattr(apn.representation, "univariate_polynomial"):
        univ_poly = apn.representation.univariate_polynomial

        # 1) Build GF(2^n). If apn.irr_poly is parseable as an int, use that as irreducible_poly.
        try:
            irr_int = int(apn.irr_poly)
            field = galois.GF(2**apn.field_n, irreducible_poly=irr_int)
        except ValueError:
            field = galois.GF(2**apn.field_n)

        # 2) Construct the polynomial in GF(2^n)[x].
        poly_gf = _build_galois_polynomial(univ_poly, field)

        # 3) Algebraic degree
        algebraic_degree = poly_gf.degree
        apn.properties["algebraic_degree"] = algebraic_degree

        # 4) Find number_of_terms
        number_of_terms = len(univ_poly)
        apn.properties["number_of_terms"] = number_of_terms

        # 5) Check if APN is_monomial
        apn.properties["is_monomial"] = (number_of_terms == 1)

        # 6) Differential uniformity => is_apn
        diff_uni_comp = DifferentialUniformityComputer()
        differential_uniformity = diff_uni_comp.compute_du(apn)
        apn.properties["is_apn"] = (differential_uniformity == 2)
        if not apn.properties["is_apn"]:
            print(f"Warning: Function is not APN; differential uniformity = {differential_uniformity}")

        # 7) Check if APN is_quadratic
        try:
            tt_list = apn._get_truth_table_list()
            apn.properties["is_quadratic"] = is_quadratic_apn(tt_list, apn.field_n)
        except Exception:
            apn.properties["is_quadratic"] = False

        # 8) Compute the k_to_1 property
        # Build a frequency distribution of all outputs. For each nonzero output, check if freq is the same.
        tt = apn._get_truth_table_list()
        freq_counter = Counter(tt)
        # Exclude 0 from the analysis "each nonzero element has exactly k preimages"
        nonzero_out_freqs = [freq_counter[y] for y in freq_counter if y != 0]

        # If no nonzero outputs, it's degenerate. Set "non-uniform" for an all-zero map.
        if len(nonzero_out_freqs) > 0:
            unique_freqs = set(nonzero_out_freqs)
            if len(unique_freqs) == 1:
                # Exactly one frequency
                k = unique_freqs.pop()
                apn.properties["k_to_1"] = f"{k}-to-1"
            else:
                # More than one frequency => not uniform
                apn.properties["k_to_1"] = "non-uniform"
        else:
            # We use "non-uniform" as the placeholder.
            apn.properties["k_to_1"] = "non-uniform"

        # 9) If k_to_1 == "3-to-1", we check if it is a canonical triplicate (uniform)
        # using is_canonical_triplicate_python. Otherwise, set False.
        if apn.properties["k_to_1"] == "3-to-1":
            from computations.equivalence.lin_eq_2x_uniform_3to1 import is_canonical_triplicate_python
            tt_list = apn._get_truth_table_list()
            is_can = is_canonical_triplicate_python(tt_list, apn.field_n)
            apn.properties["uniformly_distributed"] = bool(is_can)
        else:
            apn.properties["uniformly_distributed"] = False

    else:
        print("No univariate polynomial found; skipping property calculations.")


def _build_galois_polynomial(univ_poly, field):
    from galois import Poly

    if not univ_poly:
        return Poly([field(0)], field=field, order="asc")

    max_exp = max(mon_exp for _, mon_exp in univ_poly)
    coeffs = [field(0)] * (max_exp + 1)

    for (coeff_exp, mon_exp) in univ_poly:
        c = field.primitive_element ** coeff_exp
        coeffs[mon_exp] += c  # addition in GF(2^n)

    return Poly(coeffs, field=field, order="asc")