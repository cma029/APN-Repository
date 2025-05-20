from representations.abstract_representation import Representation
from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
from computations.interpolation_helpers import truth_table_to_univariate_poly
from computations.poly_parse_utils import parse_irreducible_poly_str, bitmask_to_poly_str


class TruthTableRepresentation(Representation):
    # Represents the vectorial Boolean function as a truth table.

    def __init__(self, truth_table):
        self.truth_table = truth_table

    def to_univariate_polynomial(self, field_n, irr_poly):
        """
        Convert this TruthTableRepresentation into a UnivariatePolynomialRepresentation
        by performing Lagrange interpolation for finite fields over GF(2^n).
        """

        irr_int = parse_irreducible_poly_str(irr_poly)

        # Lagrange interpolation (poly_terms, used_irr).
        (poly_terms, used_irr_poly_int) = truth_table_to_univariate_poly(
            self.truth_table,
            field_n,
            irr_poly_int=irr_int
        )

        # Build a UnivariatePolynomialRepresentation.
        poly_rep = UnivariatePolynomialRepresentation(poly_terms)

        # If no irreducible polynomial is supplied, then _last_used_irr_poly_str = fallback.
        if not irr_poly:
            used_poly_str = bitmask_to_poly_str(used_irr_poly_int)
            poly_rep._last_used_irr_poly_str = used_poly_str

        return poly_rep

    def to_truth_table(self, field_n, irr_poly):
        return self

    def __repr__(self):
        return f"TruthTableRepresentation(size={len(self.truth_table)})"