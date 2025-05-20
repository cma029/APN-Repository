from invariants import reorder_invariants
from typing import Dict, Any
from vbf_object import VBF
from registry import REG


def polynomial_to_str(univ_poly):
    # Convert a list of ([coefficient_exp, monomial_exp]) into a univariate polynomial string.
    # Example: [(1,9),(11,6),(0,3)] -> "a*x^9 + a^11*x^6 + x^3"
    if not univ_poly:
        return "0"

    # Sort by monomial_exp descending.
    sorted_poly = sorted(univ_poly, key=lambda t: t[1], reverse=True)

    parts = []
    for (coeff_exp, mon_exp) in sorted_poly:
        # Handle alpha part (a^coefficient_exp) but skip "^1".
        if coeff_exp == 0:
            alpha_part = ""
        elif coeff_exp == 1:
            alpha_part = "a"
        else:
            alpha_part = f"a^{coeff_exp}"

        # Handle x part (x^monomial_exp) but skip "^1".
        if mon_exp == 0:
            x_part = ""
        elif mon_exp == 1:
            x_part = "x"
        else:
            x_part = f"x^{mon_exp}"

        # Combine alpha_part and x_part.
        if alpha_part and x_part:
            part_str = alpha_part + "*" + x_part
        else:
            part_str = alpha_part + x_part
            if not part_str:
                part_str = "1"

        parts.append(part_str)

    return " + ".join(parts)


def _invariants_str_with_linebreak(invariants: dict) -> str:
    # Forced line break after 'gamma_rank'.
    if not invariants:
        return "{}"

    items = []
    for key, value in invariants.items():
        items.append(f"'{key}': {value!r}")

    # After we find 'gamma_rank', we insert \n.
    result_pieces = []
    for index, pair_str in enumerate(items):
        if "'gamma_rank': " in pair_str:
            result_pieces.append(pair_str + ",\n  ")
        else:
            if index < len(items)-1:
                result_pieces.append(pair_str + ", ")
            else:
                # Last item has no trailing comma.
                result_pieces.append(pair_str)

    # Wrap them in a dictionary style.
    joined_str = "".join(result_pieces)
    return "{" + joined_str + "}"


def format_generic_vbf(vbf: VBF, label: str) -> str:
    reorder_invariants(vbf)

    # Check if vbf.representation has univariate_polynomial.
    if hasattr(vbf.representation, "univariate_polynomial"):
        poly_str = polynomial_to_str(vbf.representation.univariate_polynomial)
    else:
        poly_str = "Truth Table based VBF"

    lines = []
    lines.append(f"{label}:")
    lines.append(f"  Univariate polynomial representation: {poly_str}, irreducible_poly='{vbf.irr_poly}'")
    inv_str = _invariants_str_with_linebreak(vbf.invariants)
    lines.append(f"  Invariants: {inv_str}")

    return "\n".join(lines)


def build_vbf_from_dict(vbf_dictionary: Dict[str, Any]) -> VBF:
    # Build (or reconstruct) a VBF from a dictionary.
    poly_list = vbf_dictionary.get("poly", [])
    field_n   = vbf_dictionary.get("field_n", 0)
    irr_poly  = vbf_dictionary.get("irr_poly", "")
    cached_tt = vbf_dictionary.get("cached_tt", [])

    if poly_list:
        vbf_object = VBF(poly_list, field_n, irr_poly)
        if cached_tt:
            vbf_object._cached_tt_list = cached_tt
    else:
        if cached_tt:
            vbf_object = VBF.from_cached_tt(cached_tt, field_n, irr_poly)
        else:
            # Fallback empty.
            vbf_object = VBF([], field_n, irr_poly)

    # Merge existing invariants if present.
    vbf_object.invariants = vbf_dictionary.get("invariants", {})

    return vbf_object


def get_custom_ordered_invariant_keys() -> list[str]:
    # Returns a list of invariant keys in a custom order.
    all_keys = REG.keys("invariant")
    all_key_set = set(all_keys)

    classic_invariants = [
        "odds",
        "odws",
        "delta_rank",
        "gamma_rank",
    ]

    final_list = []

    for invariant_key in classic_invariants:
        if invariant_key in all_key_set:
            final_list.append(invariant_key)

    leftover = all_key_set - set(final_list)
    leftover_sorted = sorted(leftover)
    final_list.extend(leftover_sorted)

    final_list.append("all")

    return final_list