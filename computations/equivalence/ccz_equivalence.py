# ccz_equivalence.py
# Description: Basic test with SAGE built-in linear code function.

import math
from computations.equivalence.base_equivalence import EquivalenceTest
from sage.all import GF, Matrix
from sage.coding.linear_code import LinearCode

def tobin(x, length=0):
    bin_str = bin(x)[2:]  # Remove '0b' prefix
    bin_str = bin_str.zfill(length)
    return [int(bit) for bit in bin_str]

def are_ccz_equivalent_lists(f, g):
    """ 
    Returns True if and only if the functions with LUT (look-up table) f and g
    are CCZ-equivalent. Based on the Kazymyrov approach, which constructs
    a linear code from the truth table and checks for permutation-equivalence.

    https://github.com/okazymyrov/sbox/blob/master/Sage/CSbox.sage#L624

    """
    if len(f) != len(g):
        raise ValueError("f and g are of different sizes!")

    N = int(math.log(len(f), 2))  # Ensure len(f) is exactly 2^N
    if 2**N != len(f):
        raise ValueError("Length of f is not a power of 2.")

    equivalent = False

    try:
        mat_f = Matrix(
            GF(2), len(f), 2*N + 1, [
                [1] + tobin((x << N) | g_val, 2*N) for x, g_val in enumerate(f)
            ]
        )

        mat_g = Matrix(
            GF(2), len(g), 2*N + 1, [
                [1] + tobin((x << N) | g_val, 2*N) for x, g_val in enumerate(g)
            ]
        )

        # Create linear codes from these matrices (transpose for row->column basis)
        code_f = LinearCode(mat_f.transpose())
        code_g = LinearCode(mat_g.transpose())

        # Check if code_f is permutation-equivalent to code_g
        equivalent = code_f.is_permutation_equivalent(code_g)

    finally:
        # Freed references if needed
        pass

    return equivalent

class CCZEquivalenceTest(EquivalenceTest):
    """
    CCZ equivalence test
    """

    def are_equivalent(self, apnF, apnG):
        # Obtain truth tables from the APN objects
        f = apnF._get_truth_table_list()
        g = apnG._get_truth_table_list()
        try:
            return are_ccz_equivalent_lists(f, g)
        except Exception:
            return False