from __future__ import annotations
from math import log2
from sage.all import Matrix, GF
from computations.rank.base_rank import RankComputation
from registry import REG

"""
Gamma Rank implementations are adapted from the code provided in:
  L. Perrin, P. Q. Nguyen, E. B. Kavun, A. Biryukov, "sboxU: Tools for analyzing S-boxes"
  https://github.com/lpp-crypto/sboxU
We do not claim authorship of the original math. Big thanks to the authors.
"""

def oplus(x: int, y: int) -> int:
    return x ^ y

class GammaRankComputation(RankComputation):
    """
    Implementation of the Gamma-rank.
    """
    def compute_rank(self, vbf) -> int:
        # Limit dimensions > 8 for safety (adjust at own risk).
        if vbf.field_n > 8:
            raise ValueError("gamma_rank is unsupported for dimension > 8")

        func_values = vbf._get_truth_table_list()
        n = vbf.field_n
        dimension = 1 << (2*n)

        # Build gamma set: gamma[x] = ( x << n ) | f[x].
        size = 1 << n
        gamma_list = [(x << n) | func_values[x] for x in range(size)]

        # # Build the binary matrix content.
        mat_content = []
        for x in range(dimension):
            row = [0]*dimension
            for y in gamma_list:
                row[oplus(x, y)] = 1
            mat_content.append(row)

        # Convert to Sage matrix over GF(2) and compute rank.
        mat_gf2 = Matrix(GF(2), dimension, dimension, mat_content)
        return mat_gf2.rank()


@REG.register("invariant", "gamma_rank")
def gamma_rank_aggregator(vbf):
    # Aggregator function for 'gamma_rank'. Store into vbf.invariants["gamma_rank"].

    # Limit dimensions > 8 for safety (adjust at own risk).
    if vbf.field_n > 8:
        vbf.invariants["gamma_rank"] = None
        return

    # Instantiate the internal class and compute the rank.
    g_rank = GammaRankComputation()
    computed_value = g_rank.compute_rank(vbf)
    vbf.invariants["gamma_rank"] = computed_value