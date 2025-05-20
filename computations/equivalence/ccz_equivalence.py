from __future__ import annotations
import math
from typing import List
from registry import REG
from computations.equivalence.base_equivalence import EquivalenceTest
from sage.all import GF, Matrix
from sage.coding.linear_code import LinearCode

"""
CCZ Equivalence implementations are adapted from the code provided in:
  L. Perrin, P. Q. Nguyen, E. B. Kavun, A. Biryukov, "sboxU: Tools for analyzing S-boxes,"
  https://github.com/lpp-crypto/sboxU
We do not claim authorship of the original math. Big thanks to the authors.
"""

def tobin(x: int, length: int = 0) -> List[int]:
    # Convert the integer x to a binary list of length 'length'.
    # The most significant bit is at index 0 of the returned list.
    bin_str = bin(x)[2:]  # Remove '0b' prefix
    bin_str = bin_str.zfill(length)
    return [int(bit) for bit in bin_str]


@REG.register("equivalence", "ccz")
class CCZEquivalenceTest(EquivalenceTest):
    """ 
    CCZ equivalence test expecting two vbf objects. Returns True if and only if the truth tables
    from functions f and g are CCZ-equivalent. Based on the Kazymyrov approach, which constructsa 
    linear code from the truth table and checks for permutation-equivalence.

    https://github.com/okazymyrov/sbox/blob/master/Sage/CSbox.sage#L624
    
    """
    name = "ccz"

    def are_equivalent(self, vbf_F, vbf_G) -> bool:
        # Extract truth tables from the APN objects.
        truth_table_f = vbf_F._get_truth_table_list()
        truth_table_g = vbf_G._get_truth_table_list()
        if len(truth_table_f) != len(truth_table_g):
            return ValueError("f and g have different sizes, cannot be CCZ tested.")

        N = int(math.log(len(truth_table_f), 2)) # Ensure len(f) is exactly 2^N.
        if 2 ** N != len(truth_table_f):
            raise ValueError("Length of truth table is not a power of 2.")

        mat_f = Matrix(
            GF(2), len(truth_table_f), 2 * N + 1,
            [[1] + tobin((x << N) | f_val, 2 * N) for x, f_val in enumerate(truth_table_f)],
        )
        mat_g = Matrix(
            GF(2), len(truth_table_g), 2 * N + 1,
            [[1] + tobin((x << N) | g_val, 2 * N) for x, g_val in enumerate(truth_table_g)],
        )

        # Create linear codes from these matrices (transpose for row->column basis).
        code_f = LinearCode(mat_f.transpose())
        code_g = LinearCode(mat_g.transpose())

        # Check if code_f is permutation-equivalent to code_g.
        return code_f.is_permutation_equivalent(code_g)