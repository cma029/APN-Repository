import galois
from representations.abstract_representation import Representation
from apn_invariants import parse_irreducible_poly_str

class UnivariatePolynomialRepresentation(Representation):
    """
    APN function represented as a univariate polynomial over GF(2^n).
    The univariate polynomial is stored as a list of tuples: (coefficient_exponent, monomial_exponent).
    Example: [(1,9),(11,6),(0,3)] means a*x^9 + a^11*x^6 + x^3.
    """

    def __init__(self, univariate_polynomial):
        self.univariate_polynomial = univariate_polynomial
        self._last_used_irr_poly_str = None

    def to_univariate_polynomial(self):
        return self

    def to_truth_table(self, field_n, irr_poly):
        """
        Builds a galois.GF(2^field_n) using the user-supplied input irr_poly string 
        e.g. "x^6 + x^4 + x^3 + x + 1". If parse_irreducible_poly_str(...) returns 0,
        we issue a warning and fall back to Galois default polynomial for GF(2^n).
        """

        # Parse the textual polynomial string => integer bitmask.
        irr_int = parse_irreducible_poly_str(irr_poly)

        # If parse returns 0 => Galois' default polynomial (fallback).
        if irr_int == 0:
            print(f"Warning: Could not parse '{irr_poly}' as a polynomial string. "
                  f"Falling back to Galois' default polynomial for GF(2^{field_n}).")
            field = galois.GF(2**field_n)
            fallback_poly_obj = field.irreducible_poly
            self._last_used_irr_poly_str = _poly_obj_to_str(fallback_poly_obj)
        else:
            # Attempt to use irr_int with Galois. If reducible => Galois fallback.
            try:
                field = galois.GF(2**field_n, irreducible_poly=irr_int)
            except ValueError as exc:
                if "is reducible" in str(exc):
                    print(f"Warning: The user-specified polynomial '{irr_poly}' "
                          f"is not irreducible. Falling back to the default polynomial for GF(2^{field_n}).")
                    field = galois.GF(2**field_n)
                    fallback_poly_obj = field.irreducible_poly
                    self._last_used_irr_poly_str = _poly_obj_to_str(fallback_poly_obj)
                else:
                    raise
            else:
                # No Galois fallback needed, the user gave a valid polynomial.
                self._last_used_irr_poly_str = irr_poly

        a = field.primitive_element

        # Convert exponents of a primitive element to field elements for the coefficients.
        # After this conversion, each polynomial term is stored as (field_element, monomial_exponen).
        terms = []
        for (coeff_exp, mon_exp) in self.univariate_polynomial:
            coeff = a ** coeff_exp
            terms.append((coeff, mon_exp))

        # Compute the truth table.
        tt = []
        # Iterate over all integers from 0 to 2^n-1.
        for x_int in range(2**field_n):
            x = field(x_int)
            val = field(0)
            for (coeff, m_exp) in terms:
                val += coeff * (x ** m_exp)
            tt.append(int(val))

        from representations.truth_table_representation import TruthTableRepresentation
        return TruthTableRepresentation(tt)

    def __repr__(self):
        return f"UnivariatePolynomialRepresentation(univariate_polynomial={self.univariate_polynomial})"


def _poly_obj_to_str(poly_object):
    # Convert an integer bitmask or a galois.Poly object into a human-readable polynomial string.

    # If poly_object is an integer, handle as bitmask.
    if isinstance(poly_object, int):
        return _bitmask_to_poly_str(poly_object)

    raw_poly_str = str(poly_object)
    if raw_poly_str.startswith("Poly(") and ", GF(" in raw_poly_str:
        extracted_poly_str = raw_poly_str[5:]
        extracted_poly_str = extracted_poly_str.split(", GF(")[0]
        extracted_poly_str = extracted_poly_str.strip()
        if extracted_poly_str.endswith(")"):
            extracted_poly_str = extracted_poly_str[:-1].strip()
        return extracted_poly_str

    # If unable to parse, return the raw string.
    return raw_poly_str


def _bitmask_to_poly_str(poly_int: int) -> str:
    # Convert an integer bitmask (e.g. 0x5B) to "x^6 + x^4 + x^3 + x + 1".
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