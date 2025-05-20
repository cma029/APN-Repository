import galois
from representations.abstract_representation import Representation
from computations.poly_parse_utils import parse_irreducible_poly_str, bitmask_to_poly_str

class UnivariatePolynomialRepresentation(Representation):
    """
    A vectorial Boolean function represented as a univariate polynomial over GF(2^n).
    The univariate polynomial is stored as a list of tuples: (coefficient_exponent, monomial_exponent).
    Example: [(1,9),(11,6),(0,3)] means a*x^9 + a^11*x^6 + x^3.
    """

    def __init__(self, univariate_polynomial):
        self.univariate_polynomial = univariate_polynomial
        self._last_used_irr_poly_str = None

    def to_univariate_polynomial(self, field_n, irr_poly):
        return self

    def to_truth_table(self, field_n, irr_poly):
        """
        Builds a galois.GF(2^field_n) using the user-supplied input irr_poly string.
        If parse_irreducible_poly_str(...) returns 0, then the default polynomial is used.
        """

        # Parse the polynomial string into integer bitmask.
        irr_int = parse_irreducible_poly_str(irr_poly)

        # If parse returns 0, then we use the default polynomial for GF(2^n).
        used_poly_str = irr_poly
        if irr_int == 0:
            print(
                f"Warning: Could not parse '{irr_poly}' as a polynomial string. "
                f'Falling back to the default polynomial for GF(2^{field_n}).'
            )
            field = galois.GF(2**field_n)
            fallback_poly_obj = field.irreducible_poly
            # Convert fallback_poly_obj into string.
            used_poly_str = _poly_obj_to_str(fallback_poly_obj)
            self._last_used_irr_poly_str = used_poly_str
        else:
            # Make an attempt with the user-supplied polynomial.
            try:
                field = galois.GF(2**field_n, irreducible_poly=irr_int)
            except ValueError as exc:
                if "is reducible" in str(exc):
                    print(
                        f"Warning: The user-specified polynomial '{irr_poly}' "
                        f"is not irreducible. Falling back to default polynomial for GF(2^{field_n})."
                    )
                    field = galois.GF(2**field_n)
                    fallback_poly_obj = field.irreducible_poly
                    used_poly_str = _poly_obj_to_str(fallback_poly_obj)
                    self._last_used_irr_poly_str = used_poly_str
                else:
                    raise
            else:
                # Valid user-supplied polynomial.
                self._last_used_irr_poly_str = irr_poly

        a = field.primitive_element

        # Convert exponents of a primitive element to field elements for the coefficients.
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
        return bitmask_to_poly_str(poly_object)

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