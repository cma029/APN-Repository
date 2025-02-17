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

    def to_univariate_polynomial(self):
        return self

    def to_truth_table(self, field_n, irr_poly):
        """
        Builds a galois.GF(2^field_n) using the user-supplied irr_poly string 
        e.g. "x^6 + x^4 + x^3 + x + 1". If parse_irreducible_poly_str(...) returns 0,
        we issue a warning and fall back to Galois' default polynomial for GF(2^n).
        """

        # Parse the textual polynomial string => integer bitmask.
        irr_int = parse_irreducible_poly_str(irr_poly)

        # If parse returns 0 => Galois' default polynomial (fallback).
        if irr_int == 0:
            print(f"Warning: Could not parse '{irr_poly}' as a polynomial string. "
                  f"Falling back to Galois' default polynomial for GF(2^{field_n}).")
            field = galois.GF(2**field_n)
        else:
            # Attempt to use irr_int with Galois. If reducible => Galois fallback.
            try:
                field = galois.GF(2**field_n, irreducible_poly=irr_int)
            except ValueError as exc:
                if "is reducible" in str(exc):
                    print(f"Warning: The user-specified polynomial '{irr_poly}' "
                          f"is not irreducible. Falling back to the default polynomial for GF(2^{field_n}).")
                    field = galois.GF(2**field_n)
                else:
                    raise

        a = field.primitive_element

        # Convert exponents of a primitive element to field elements for the coefficients
        # After this conversion, each polynomial term is stored as (field_element, monomial_exponen)
        terms = []
        for (coeff_exp, mon_exp) in self.univariate_polynomial:
            coeff = a ** coeff_exp
            terms.append((coeff, mon_exp))

        # Compute the truth table
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