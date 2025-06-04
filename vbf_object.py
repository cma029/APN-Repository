from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
from representations.truth_table_representation import TruthTableRepresentation
from representations.abstract_representation import Representation
from computations.poly_parse_utils import determine_irr_poly_str_for_polynomial
from computations.poly_parse_utils import parse_irreducible_poly_str, bitmask_to_poly_str
from computations.default_polynomials import DEFAULT_IRREDUCIBLE_POLYNOMIAL
from typing import List
import galois


class VBF:
    def __init__(self, uni_poly_data, field_n, irr_poly):
        """
        Builds a VBF object from a univariate polynomial list of tuples.
        """
        if not irr_poly:
            fallback_bits = DEFAULT_IRREDUCIBLE_POLYNOMIAL.get(field_n, 0)
            fallback_str = bitmask_to_poly_str(fallback_bits) if fallback_bits else ""
            self.irr_poly = fallback_str
        else:
            # If we do have an irr_poly string, then parse and check irreducibility.
            bits = parse_irreducible_poly_str(irr_poly)
            if bits == 0:
                print(f"Warning: Could not parse '{irr_poly}' as a valid polynomial. "
                      f"Falling back to default polynomial for GF(2^{field_n}).")
                fallback_bits = DEFAULT_IRREDUCIBLE_POLYNOMIAL.get(field_n, 0)
                fallback_str = bitmask_to_poly_str(fallback_bits) if fallback_bits else ""
                self.irr_poly = fallback_str
            else:
                # If we do have an irr_poly string, but its reducible, then fallback.
                try:
                    galois.GF(2**field_n, irreducible_poly=bits)
                    self.irr_poly = irr_poly
                except ValueError as exc:
                    if "is reducible" in str(exc).lower():
                        print(f"Warning: The user-specified polynomial '{irr_poly}' is not irreducible. "
                              f"Falling back to default polynomial for GF(2^{field_n}).")
                        fallback_bits = DEFAULT_IRREDUCIBLE_POLYNOMIAL.get(field_n, 0)
                        fallback_str = bitmask_to_poly_str(fallback_bits) if fallback_bits else ""
                        self.irr_poly = fallback_str
                    else:
                        raise

        self.field_n = field_n
        self.invariants = {}
        self._cached_tt_list = []

        if uni_poly_data:
            from representations.univariate_polynomial_representation import UnivariatePolynomialRepresentation
            self._representation = UnivariatePolynomialRepresentation(uni_poly_data)
        else:
            self._representation = None

    @classmethod
    def from_representation(cls, rep: Representation, field_n: int, irr_poly: str):
        if isinstance(rep, TruthTableRepresentation):
            poly_rep = rep.to_univariate_polynomial(field_n, irr_poly)
            vbf_object = cls(poly_rep.univariate_polynomial, field_n, irr_poly)
            
            # If aggregator used a fallback internally.
            fallback_str = getattr(poly_rep, "_last_used_irr_poly_str", None)
            if fallback_str:
                vbf_object.irr_poly = fallback_str
            
            vbf_object._cached_tt_list = rep.truth_table[:]

            # If the user did not provide irr_poly, we use the aggregator fallback.
            if not irr_poly and getattr(poly_rep, "_last_used_irr_poly_str", None):
                vbf_object.irr_poly = poly_rep._last_used_irr_poly_str

        elif isinstance(rep, UnivariatePolynomialRepresentation):
            # If user gave no irr_poly, then store the fallback.
            final_irr_str = irr_poly
            if not irr_poly:
                final_irr_str = determine_irr_poly_str_for_polynomial(field_n, irr_poly)

            vbf_object = cls(rep.univariate_polynomial, field_n, final_irr_str)
            fallback_str = getattr(rep, "_last_used_irr_poly_str", None)
            if fallback_str:
                vbf_object.irr_poly = fallback_str

        else:
            raise ValueError(f"Unrecognized representation type: {type(rep)}")

        return vbf_object

    @classmethod
    def from_cached_tt(cls, tt_list: List[int], field_n: int, irr_poly: str):
        tt_rep = TruthTableRepresentation(tt_list)
        return cls.from_representation(tt_rep, field_n, irr_poly)

    def _get_truth_table_list(self) -> List[int]:
        if self._cached_tt_list:
            return self._cached_tt_list
        if self._representation is None:
            raise ValueError("VBF has no representation to build a truth table.")
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
                fallback_str = getattr(poly_rep, "_last_used_irr_poly_str", None)
                if fallback_str:
                    self.irr_poly = fallback_str
            else:
                raise ValueError("No representation or cached truth table available.")
        return self._representation

    @representation.setter
    def representation(self, new_rep: Representation):
        if isinstance(new_rep, TruthTableRepresentation):
            poly_rep = new_rep.to_univariate_polynomial(self.field_n, self.irr_poly)
            self._representation = poly_rep
            self._cached_tt_list = new_rep.truth_table[:]
            fallback_str = getattr(poly_rep, "_last_used_irr_poly_str", None)
            if fallback_str:
                self.irr_poly = fallback_str

        elif isinstance(new_rep, UnivariatePolynomialRepresentation):
            self._representation = new_rep
            fallback_str = getattr(new_rep, "_last_used_irr_poly_str", None)
            if fallback_str:
                self.irr_poly = fallback_str

            elif not self.irr_poly:
                fallback_str = determine_irr_poly_str_for_polynomial(self.field_n, "")
                self.irr_poly = fallback_str
        else:
            raise ValueError(f"Unrecognized representation type: {type(new_rep)}")

    def get_truth_table(self):
        # Public wrapper around the private _get_truth_table_list().
        if not self._cached_tt_list:
            if self._representation is None:
                raise ValueError("VBF has no representation or cached TT to build from.")
            tt_rep = self._representation.to_truth_table(self.field_n, self.irr_poly)
            self._cached_tt_list = tt_rep.truth_table

        return TruthTableRepresentation(self._cached_tt_list)

    def __repr__(self):
        rep_type = self._representation.__class__.__name__ if self._representation else "None"
        return (f"VBF(field_n={self.field_n}, irr_poly={self.irr_poly}, "
                f"rep={rep_type}, invariants={self.invariants})")