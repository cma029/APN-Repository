from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
from representations.abstract_representation import Representation

class APN:
    def __init__(self, univariate_polynomial, field_n, irr_poly):
        # Initialize the APN object with a univariate polynomial representation of the function,
        # the field degree (int), and the irreducible polynomial (str).

        self.representation = UnivariatePolynomialRepresentation(univariate_polynomial)
        self.field_n = field_n
        self.irr_poly = irr_poly

        # Single dictionary for invariants.
        self.invariants = {}

    @classmethod
    def from_representation(cls, representation, field_n, irr_poly):
        # Directly create an APN object from a given Representation.
        if not isinstance(representation, Representation):
            raise TypeError("representation must be an instance of Representation")

        # Creates a new APN instance without calling the __init__ method.
        apn = cls.__new__(cls)  # To bypass __init__

        # Manually setting attributes
        apn.representation = representation
        apn.field_n = field_n
        apn.irr_poly = irr_poly

        # Single dictionary for invariants.
        apn.invariants = {}

        return apn

    def get_truth_table(self):
        # Returns a new APN object with the truth table representation, without modifying the original.
        tt_repr = self.representation.to_truth_table(self.field_n, self.irr_poly)
        return APN.from_representation(tt_repr, self.field_n, self.irr_poly)

    def _get_truth_table_list(self):
        # Internal helper method to obtain the raw list representing the truth table (2^n integers).
        if hasattr(self.representation, "truth_table"):
            return self.representation.truth_table
        else:
            tt_repr = self.representation.to_truth_table(self.field_n, self.irr_poly)
            return tt_repr.truth_table

    def __repr__(self):
        return (f"APN(representation={self.representation}, field_n={self.field_n}, "
                f"irr_poly='{self.irr_poly}', invariants={self.invariants})")