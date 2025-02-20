from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
from representations.truth_table_representation import TruthTableRepresentation
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

        # Store the TT in a separate cached list.
        self._cached_tt_list = None

    @classmethod
    def from_representation(cls, representation, field_n, irr_poly):
        # Directly create an APN object from a given Representation.
        if not isinstance(representation, Representation):
            raise TypeError("representation must be an instance of Representation")

        apn = cls.__new__(cls)  # To bypass __init__
        apn.representation = representation
        apn.field_n = field_n
        apn.irr_poly = irr_poly
        apn.invariants = {}
        apn._cached_tt_list = None
        return apn

    @classmethod
    def from_cached_tt(cls, cached_tt, field_n, irr_poly):
        # Build an APN with Truth Table based representation.

        apn = cls.__new__(cls)
        apn.representation = TruthTableRepresentation(cached_tt)
        apn.field_n = field_n
        apn.irr_poly = irr_poly
        apn.invariants = {}
        apn._cached_tt_list = cached_tt
        return apn

    def get_truth_table(self):
        # Returns a new APN object with the truth table representation, without modifying the original.
        tt_repr = self.representation.to_truth_table(self.field_n, self.irr_poly)
        return APN.from_representation(tt_repr, self.field_n, self.irr_poly)

    def _get_truth_table_list(self):
        # Returns a Python list of length 2^n for the functions output.
        if self._cached_tt_list is not None:
            return self._cached_tt_list

        if hasattr(self.representation, "truth_table"):
            self._cached_tt_list = self.representation.truth_table
        else:
            # Univariate polynomial based, then compute Truth Table once and store in _cached_tt_list.
            tt_repr = self.representation.to_truth_table(self.field_n, self.irr_poly)
            self._cached_tt_list = tt_repr.truth_table

        return self._cached_tt_list

    def __repr__(self):
        return (f"APN(representation={self.representation}, field_n={self.field_n}, "
                f"irr_poly='{self.irr_poly}', invariants={self.invariants})")