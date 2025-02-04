# univariate_polynomial_representation.py

import galois
from representations.abstract_representation import Representation

class UnivariatePolynomialRepresentation(Representation):
    # APN function represented as a univariate polynomial over GF(2^n).
    def __init__(self, univariate_polynomial):
        self.univariate_polynomial = univariate_polynomial

    def to_univariate_polynomial(self):
        return self

    def to_truth_table(self, field_n, irr_poly):
        field = None
        # Try integer-based irreducible polynomial
        try:
            irr_int = int(irr_poly)
            field = galois.GF(2**field_n, irreducible_poly=irr_int)
        except ValueError:
            # If not parseable as integer, just use default or fallback
            field = galois.GF(2**field_n)

        a = field.primitive_element

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