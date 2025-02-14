from apn_invariants import reorder_invariants
from apn_object import APN

def polynomial_to_str(univ_poly):
    # Convert a list of ([coefficient_exp, monomial_exp]) into a univariate polynomial string.
    # Example: [(1,9),(11,6),(0,3)] -> "a*x^9 + a^11*x^6 + x^3"
    if not univ_poly:
        return "0"

    parts = []
    for (coeff_exp, mon_exp) in univ_poly:
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
    for k, v in invariants.items():
        items.append(f"'{k}': {v!r}")  # !r to get repr(...) of v

    # After we find 'gamma_rank', we insert " => \n.
    result_pieces = []
    for i, pair_str in enumerate(items):
        if "'gamma_rank': " in pair_str:
            result_pieces.append(pair_str + ",\n  ")
        else:
            if i < len(items)-1:
                result_pieces.append(pair_str + ", ")
            else:
                # Last item => no trailing comma.
                result_pieces.append(pair_str)

    # Wrap them in a dictionary style.
    joined_str = "".join(result_pieces)
    return "{" + joined_str + "}"

def format_generic_apn(apn: APN, label: str) -> str:
    reorder_invariants(apn)
    poly_str = polynomial_to_str(apn.representation.univariate_polynomial)

    lines = []
    lines.append(f"{label}:")
    lines.append(f"  Univariate polynomial representation: {poly_str}, irreducible_poly='{apn.irr_poly}'")
    inv_str = _invariants_str_with_linebreak(apn.invariants)
    lines.append(f"  Invariants: {inv_str}")

    return "\n".join(lines)