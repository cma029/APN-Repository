# truth_table_representation.py

from representations.abstract_representation import Representation

class TruthTableRepresentation(Representation):
    # Represents the APN function as a truth table.

    def __init__(self, truth_table):
        # truth_table: list of integers of length 2^n.
        self.truth_table = truth_table

    def to_univariate_polynomial(self):
        # NB! This is not implemented, raise an error for now
        raise NotImplementedError("Not Implemented: Conversion from truth table to univariate polynomial.")

    def to_truth_table(self, field_n, irr_poly):
        # Not sure if this method is needed. Already in truth table form.
        return self
    
    def __repr__(self):
        return f"TruthTableRepresentation(size={len(self.truth_table)})"