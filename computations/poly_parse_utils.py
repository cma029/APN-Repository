import re
from computations.default_polynomials import DEFAULT_IRREDUCIBLE_POLYNOMIAL

def parse_irreducible_poly_str(poly_str: str) -> int:
    """
    Parse a polynomial string like 'x^6 + x^4 + x^3 + x + 1' into an integer bitmask.
    Return 0 if the string is empty or parse fails.
    """
    if not poly_str:
        return 0

    tokens = [t.strip().lower() for t in poly_str.split('+')]
    result_mask = 0
    valid = False

    for token in tokens:
        if token == '1':
            # Constant, then exponent 0.
            result_mask |= 1
            valid = True
        elif token == 'x':
            # Edge case x^1.
            result_mask |= (1 << 1)
            valid = True
        else:
            # Maybe x^n.
            match = re.match(r"x\^(\d+)$", token)
            if match:
                exp_val = int(match.group(1))
                if exp_val < 0 or exp_val > 2000:
                    return 0
                result_mask |= (1 << exp_val)
                valid = True
            else:
                # If the parse failed, then return 0.
                return 0

    if not valid:
        return 0

    return result_mask


def bitmask_to_poly_str(poly_int: int) -> str:
    # Convert an integer bitmask to polynomial string, e.g. 0x5B => 'x^6 + x^4 + x^3 + x + 1'.
    if poly_int == 0:
        return "0"
    bits = []
    highest_power = poly_int.bit_length() - 1
    for exp in range(highest_power, -1, -1):
        if (poly_int >> exp) & 1:
            if exp == 0:
                bits.append("1")
            elif exp == 1:
                bits.append("x")
            else:
                bits.append(f"x^{exp}")
    return " + ".join(bits)


def determine_irr_poly_str_for_polynomial(field_n: int, user_irr_str: str) -> str:
    # If user_irr_str is non-empty and parseable, we accept it as-is.
    parse_int = parse_irreducible_poly_str(user_irr_str)
    if parse_int == 0:
        # If it's empty, we use the fallback.
        if field_n not in DEFAULT_IRREDUCIBLE_POLYNOMIAL:
            return "0"
        fallback_int = DEFAULT_IRREDUCIBLE_POLYNOMIAL[field_n]
        return bitmask_to_poly_str(fallback_int)
    else:
        return user_irr_str.strip()


def default_poly_str_for_n(field_n: int) -> str:
    if field_n not in DEFAULT_IRREDUCIBLE_POLYNOMIAL:
        return "0"
    
    fallback_int = DEFAULT_IRREDUCIBLE_POLYNOMIAL[field_n]
    return bitmask_to_poly_str(fallback_int)