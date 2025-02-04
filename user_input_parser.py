# user_input_parser.py
# Description: Parses user input into APN objects.

from apn_object import APN
import galois

class PolynomialParser:
    def parse_univariate_polynomial(self, univariate_polynomial, field_n, irr_poly):
        if field_n <= 1:
            raise ValueError("Field degree must be greater than 1.")

        if not irr_poly.strip():
            field = galois.GF(2**field_n)
            poly_int = field.irreducible_poly
            irr_poly = str(poly_int)

        return APN(univariate_polynomial, field_n, irr_poly)