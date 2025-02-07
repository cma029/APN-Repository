# cli_utils.py
# Description: Provides utility functions for CLI commands.

from collections import OrderedDict

def polynomial_to_str(univ_poly):
    # Convert a list of ([coefficient_exp, monomial_exp]) into a univariate polynomial string.
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
    # Append any other invariants that are not in the desired_order
    for k in invariants:
        if k not in desired_order:
            reordered[k] = invariants[k]
    return dict(reordered)