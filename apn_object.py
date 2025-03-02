from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
from representations.truth_table_representation import TruthTableRepresentation
from representations.abstract_representation import Representation
from computations.poly_parse_utils import determine_irr_poly_str_for_polynomial
from typing import List, Dict, Any

class APN:
    def __init__(self, uni_poly_data, field_n, irr_poly):
        """
        Builds an APN whose default representation is univariate polynomial,
        given 'uni_poly_data' as a list of (coefficient_exp, monomial_exp) tuples.
        """
        self.field_n = field_n
        self.irr_poly = irr_poly
        self.invariants: Dict[str, Any] = {}
        self._cached_tt_list: List[int] = []

        if uni_poly_data:
            self._representation: Representation = UnivariatePolynomialRepresentation(uni_poly_data)
        else:
            self._representation = None

        if uni_poly_data and not irr_poly:
            final_irr_str = determine_irr_poly_str_for_polynomial(field_n, "")
            self.irr_poly = final_irr_str

    @classmethod
    def from_representation(cls, rep: Representation, field_n: int, irr_poly: str):
        if isinstance(rep, TruthTableRepresentation):
            poly_rep = rep.to_univariate_polynomial(field_n, irr_poly)
            apn_obj = cls(poly_rep.univariate_polynomial, field_n, irr_poly)
            apn_obj._cached_tt_list = rep.truth_table[:]
            # If no irr_poly, then store the fallback from poly_rep.
            if not irr_poly and getattr(poly_rep, "_last_used_irr_poly_str", None):
                apn_obj.irr_poly = poly_rep._last_used_irr_poly_str

        elif isinstance(rep, UnivariatePolynomialRepresentation):
            # If user gave no irr_poly, then store the fallback.
            final_irr_str = irr_poly
            if not irr_poly:
                final_irr_str = determine_irr_poly_str_for_polynomial(field_n, irr_poly)
            apn_obj = cls(rep.univariate_polynomial, field_n, final_irr_str)
        else:
            raise ValueError(f"Unrecognized representation type: {type(rep)}")

        return apn_obj

    @classmethod
    def from_cached_tt(cls, tt_list: List[int], field_n: int, irr_poly: str):
        tt_rep = TruthTableRepresentation(tt_list)
        return cls.from_representation(tt_rep, field_n, irr_poly)

    def _get_truth_table_list(self) -> List[int]:
        if self._cached_tt_list:
            return self._cached_tt_list
        if self._representation is None:
            raise ValueError("APN has no representation to build a truth table.")
        tt_rep = self._representation.to_truth_table(self.field_n, self.irr_poly)
        self._cached_tt_list = tt_rep.truth_table
        return self._cached_tt_list

    @property
    def representation(self) -> Representation:
        if self._representation is None:
            # If we have a cached truth table but no representation, convert.
            if self._cached_tt_list:
                rep = TruthTableRepresentation(self._cached_tt_list)
                poly_rep = rep.to_univariate_polynomial(self.field_n, self.irr_poly)
                self._representation = poly_rep
                if not self.irr_poly and getattr(poly_rep, "_last_used_irr_poly_str", None):
                    self.irr_poly = poly_rep._last_used_irr_poly_str
            else:
                raise ValueError("No representation or cached truth table available.")
        return self._representation

    @representation.setter
    def representation(self, new_rep: Representation):
        if isinstance(new_rep, TruthTableRepresentation):
            poly_rep = new_rep.to_univariate_polynomial(self.field_n, self.irr_poly)
            self._representation = poly_rep
            self._cached_tt_list = new_rep.truth_table[:]
            if not self.irr_poly and getattr(poly_rep, "_last_used_irr_poly_str", None):
                self.irr_poly = poly_rep._last_used_irr_poly_str
        elif isinstance(new_rep, UnivariatePolynomialRepresentation):
            self._representation = new_rep
            if not self.irr_poly:
                fallback_str = determine_irr_poly_str_for_polynomial(self.field_n, "")
                self.irr_poly = fallback_str
        else:
            raise ValueError(f"Unrecognized representation type: {type(new_rep)}")

    def get_truth_table(self):
        # Public wrapper around the private _get_truth_table_list().
        if not self._cached_tt_list:
            if self._representation is None:
                raise ValueError("APN has no representation or cached TT to build from.")
            tt_rep = self._representation.to_truth_table(self.field_n, self.irr_poly)
            self._cached_tt_list = tt_rep.truth_table

        return TruthTableRepresentation(self._cached_tt_list)

    def __repr__(self):
        rep_type = self._representation.__class__.__name__ if self._representation else "None"
        return (f"APN(field_n={self.field_n}, irr_poly={self.irr_poly}, "
                f"rep={rep_type}, invariants={self.invariants})")