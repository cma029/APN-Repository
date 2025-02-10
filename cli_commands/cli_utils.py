from collections import OrderedDict
from apn_object import APN

def polynomial_to_str(univ_poly):
    # Convert a list of ([coefficient_exp, monomial_exp]) into a univariate polynomial string.
    # Example: [(1,9),(11,6),(0,3)] -> "a^1*x^9 + a^11*x^6 + x^3"
    if not univ_poly:
        return "Not available. See cli_utils.py"
    parts = []
    for (coeff_exp, mon_exp) in univ_poly:
        alpha_part = f"a^{coeff_exp}" if coeff_exp != 0 else ""
        x_part = f"x^{mon_exp}" if mon_exp != 0 else ""
        if alpha_part and x_part:
            part_str = alpha_part + "*" + x_part
        else:
            part_str = alpha_part + x_part
            if not part_str:
                part_str = "1"
        parts.append(part_str)
    return " + ".join(parts)

def reorder_invariants(invariants: dict) -> dict:
    desired_order = ["odds", "odws", "gamma_rank", "delta_rank", "citation"]
    reordered = OrderedDict()
    for key in desired_order:
        if key in invariants:
            reordered[key] = invariants[key]
    # Append any other invariants not in desired_order.
    for k in invariants:
        if k not in desired_order:
            reordered[k] = invariants[k]
    return dict(reordered)

def format_generic_apn(apn: APN, label: str) -> str:
    poly_str = polynomial_to_str(apn.representation.univariate_polynomial)
    props_str = str(apn.properties)
    invs_str = str(reorder_invariants(apn.invariants))

    lines = []
    lines.append(f"{label}:")
    lines.append(f"  Univariate polynomial representation: {poly_str}, irreducible_poly='{apn.irr_poly}'")
    lines.append(f"  Properties: {props_str}")
    lines.append(f"  Invariants: {invs_str}")
    return "\n".join(lines)